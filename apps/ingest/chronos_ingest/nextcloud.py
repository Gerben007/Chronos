"""Nextcloud WebDAV + OCS share client.

Two surfaces:
  - WebDAV (`/remote.php/dav/files/USER/...`): list, download, move.
  - OCS shares API (`/ocs/v2.php/apps/files_sharing/api/v1/shares`):
    public read-only links with `permissions=1`. No folder shares.

We use httpx directly rather than webdavclient3 — fewer moving parts,
explicit error handling, and we don't need full WebDAV feature parity.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from urllib.parse import quote, urljoin

import httpx


WEBDAV_NS = "DAV:"
OC_NS = "http://owncloud.org/ns"
NC_NS = "http://nextcloud.org/ns"


class NextcloudError(Exception):
    """Raised when Nextcloud returns an unexpected response."""


@dataclass(frozen=True)
class RemoteFile:
    """A file discovered via PROPFIND."""

    path: str             # absolute path inside the user's WebDAV root, e.g. "/CC-Library/_inbox/foo.pdf"
    name: str             # leaf filename
    size: int
    content_type: str
    etag: str
    is_dir: bool


class NextcloudClient:
    """Thin Nextcloud client. Construct once per ingest tick."""

    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        app_password: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not base_url or not username or not app_password:
            raise ValueError("NextcloudClient requires base_url, username, app_password")
        self._base = base_url.rstrip("/") + "/"
        self._user = username
        self._dav_root = f"remote.php/dav/files/{quote(username)}/"
        self._client = httpx.Client(
            auth=(username, app_password),
            timeout=timeout_seconds,
            follow_redirects=False,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> NextcloudClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ── WebDAV ─────────────────────────────────────────────────────────

    def list_dir(self, remote_path: str) -> list[RemoteFile]:
        """Returns the files (not subdirs) inside the given remote path.

        `remote_path` is absolute within the user root, e.g. "/CC-Library/_inbox".
        """
        url = self._dav_url(remote_path)
        body = (
            '<?xml version="1.0"?>'
            '<d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">'
            "<d:prop>"
            "<d:displayname/>"
            "<d:getcontentlength/>"
            "<d:getcontenttype/>"
            "<d:getetag/>"
            "<d:resourcetype/>"
            "</d:prop>"
            "</d:propfind>"
        )
        r = self._client.request(
            "PROPFIND",
            url,
            content=body,
            headers={"Depth": "1", "Content-Type": "application/xml"},
        )
        if r.status_code == 404:
            return []
        if r.status_code != 207:
            raise NextcloudError(f"PROPFIND {remote_path} → {r.status_code}: {r.text[:200]}")
        return self._parse_propfind(r.text, parent_path=remote_path)

    def download_to(self, remote_path: str, dest: BinaryIO) -> int:
        """Streams the file body into `dest`. Returns bytes written."""
        url = self._dav_url(remote_path)
        total = 0
        with self._client.stream("GET", url) as r:
            if r.status_code != 200:
                raise NextcloudError(f"GET {remote_path} → {r.status_code}")
            for chunk in r.iter_bytes():
                dest.write(chunk)
                total += len(chunk)
        return total

    def download_to_path(self, remote_path: str, local: Path) -> int:
        local.parent.mkdir(parents=True, exist_ok=True)
        with open(local, "wb") as f:
            return self.download_to(remote_path, f)

    def move(self, src: str, dest: str, *, overwrite: bool = False) -> None:
        """MOVE within the user's WebDAV root. Creates parent dirs if needed."""
        # Ensure parent of dest exists.
        parent = "/".join(dest.rstrip("/").split("/")[:-1])
        if parent:
            self._ensure_dir(parent)
        src_url = self._dav_url(src)
        dest_url = self._dav_url(dest)
        r = self._client.request(
            "MOVE",
            src_url,
            headers={
                "Destination": dest_url,
                "Overwrite": "T" if overwrite else "F",
            },
        )
        if r.status_code not in (201, 204):
            raise NextcloudError(f"MOVE {src} → {dest}: {r.status_code} {r.text[:200]}")

    def _ensure_dir(self, remote_path: str) -> None:
        """Walks the path components and MKCOLs missing ones (idempotent).

        Existing directories return 405 from MKCOL — that's fine.
        """
        parts = [p for p in remote_path.split("/") if p]
        accum = ""
        for p in parts:
            accum = f"{accum}/{p}"
            url = self._dav_url(accum)
            r = self._client.request("MKCOL", url)
            if r.status_code not in (201, 405):
                raise NextcloudError(f"MKCOL {accum}: {r.status_code} {r.text[:200]}")

    # ── OCS shares ─────────────────────────────────────────────────────

    def create_public_share(
        self,
        remote_path: str,
        *,
        password: str | None = None,
        hide_download: bool = False,
    ) -> str:
        """Creates a public read-only share link.

        permissions=1 → read only, no upload, no re-share.
        shareType=3   → public link.
        Returns the share URL.
        """
        url = urljoin(self._base, "ocs/v2.php/apps/files_sharing/api/v1/shares")
        data: dict[str, str] = {
            "path": remote_path,
            "shareType": "3",
            "permissions": "1",
            "hideDownload": "1" if hide_download else "0",
        }
        if password:
            data["password"] = password
        r = self._client.post(
            url,
            data=data,
            headers={"OCS-APIRequest": "true", "Accept": "application/json"},
        )
        if r.status_code not in (200, 201):
            raise NextcloudError(f"OCS share create: {r.status_code} {r.text[:300]}")
        payload = r.json()
        ocs = payload.get("ocs", {})
        meta = ocs.get("meta", {})
        if meta.get("status") != "ok":
            raise NextcloudError(f"OCS share create: {meta}")
        share_url = ocs.get("data", {}).get("url")
        if not isinstance(share_url, str):
            raise NextcloudError(f"OCS share missing url: {payload}")
        return share_url

    # ── Internals ──────────────────────────────────────────────────────

    def _dav_url(self, remote_path: str) -> str:
        """Builds a full WebDAV URL for a path inside the user's root."""
        path = remote_path.lstrip("/")
        return urljoin(self._base, self._dav_root + quote(path, safe="/"))

    def _parse_propfind(self, body: str, *, parent_path: str) -> list[RemoteFile]:
        root = ET.fromstring(body)
        files: list[RemoteFile] = []
        parent_prefix = self._dav_root + parent_path.strip("/").rstrip("/")
        for resp in root.findall(f"{{{WEBDAV_NS}}}response"):
            href = resp.findtext(f"{{{WEBDAV_NS}}}href") or ""
            propstat = resp.find(f"{{{WEBDAV_NS}}}propstat")
            if propstat is None:
                continue
            prop = propstat.find(f"{{{WEBDAV_NS}}}prop")
            if prop is None:
                continue
            rtype = prop.find(f"{{{WEBDAV_NS}}}resourcetype")
            is_dir = rtype is not None and rtype.find(f"{{{WEBDAV_NS}}}collection") is not None

            # Skip the parent dir entry itself.
            normalized_href = href.rstrip("/")
            normalized_parent = parent_prefix.rstrip("/")
            if normalized_href.endswith(normalized_parent):
                continue
            if is_dir:
                continue

            name = normalized_href.rsplit("/", 1)[-1]
            try:
                from urllib.parse import unquote
                name = unquote(name)
            except Exception:
                pass

            size_str = prop.findtext(f"{{{WEBDAV_NS}}}getcontentlength") or "0"
            ctype = prop.findtext(f"{{{WEBDAV_NS}}}getcontenttype") or "application/octet-stream"
            etag = (prop.findtext(f"{{{WEBDAV_NS}}}getetag") or "").strip('"')

            files.append(
                RemoteFile(
                    path=f"{parent_path.rstrip('/')}/{name}",
                    name=name,
                    size=int(size_str) if size_str.isdigit() else 0,
                    content_type=ctype,
                    etag=etag,
                    is_dir=False,
                )
            )
        return files


# ── Filename → file_type ──────────────────────────────────────────────


_EXT_TO_TYPE: dict[str, str] = {
    ".pdf": "pdf",
    ".mp4": "video",
    ".mkv": "video",
    ".mov": "video",
    ".webm": "video",
    ".mp3": "audio",
    ".m4a": "audio",
    ".wav": "audio",
    ".ogg": "audio",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".gif": "image",
    ".webp": "image",
    ".doc": "doc",
    ".docx": "doc",
    ".odt": "doc",
    ".txt": "doc",
    ".md": "doc",
}


def classify_filetype(name: str) -> str | None:
    """Returns the schema's file_type label, or None if unsupported."""
    suffix = Path(name).suffix.lower()
    return _EXT_TO_TYPE.get(suffix)
