"""File safety pipeline — ClamAV scan + PDF JS strip + image re-encode.

Every uploaded file passes through `scan_file()` before any extraction
or classification work. Failures are loud and fail-closed: if the
scanner can't even reach ClamAV, the file is treated as suspicious.

The library imports (clamd, pikepdf, PIL) are kept lazy so unit tests
don't require the native deps installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SUPPORTED_PDF_SUFFIXES = {".pdf"}
SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


@dataclass(frozen=True)
class ScanResult:
    """Outcome of `scan_file`.

    `result` matches the `files.scan_result` column constraint:
      - 'clean'      : virus-free AND sanitisation succeeded
      - 'infected'   : ClamAV positive
      - 'suspicious' : scanner unreachable, or sanitisation failed
      - 'error'      : unexpected exception
    """

    result: str
    signatures: list[str]
    notes: str

    @property
    def is_clean(self) -> bool:
        return self.result == "clean"


# ── ClamAV ─────────────────────────────────────────────────────────────


def clamav_scan(path: Path, *, socket: Path) -> tuple[bool, list[str], str]:
    """Returns (is_clean, signatures, notes).

    is_clean=True only if ClamAV returns OK. Any other state — including
    socket errors — yields is_clean=False so the caller fails closed.
    """
    try:
        import clamd  # type: ignore[import-not-found]
    except ImportError:
        return False, [], "clamd library not installed"

    try:
        client = clamd.ClamdUnixSocket(path=str(socket))
        with open(path, "rb") as f:
            scan = client.instream(f)
    except FileNotFoundError:
        return False, [], f"clamav socket not present at {socket}"
    except Exception as e:  # noqa: BLE001
        return False, [], f"clamav scan error: {type(e).__name__}: {e}"

    result = scan.get("stream") if isinstance(scan, dict) else None
    if not result:
        return False, [], f"unexpected clamav response: {scan!r}"
    status, signature = result[0], result[1]
    if status == "OK":
        return True, [], ""
    if status == "FOUND":
        return False, [signature], f"clamav signature {signature}"
    return False, [], f"clamav status {status}"


# ── PDF sanitisation ──────────────────────────────────────────────────


def strip_pdf_js(path: Path) -> tuple[bool, str]:
    """Rewrites the PDF in place with JS / actions / external URIs stripped.

    Returns (ok, notes). On failure, the file is unchanged.
    """
    try:
        import pikepdf  # type: ignore[import-not-found]
    except ImportError:
        return False, "pikepdf not installed"

    try:
        with pikepdf.open(path, allow_overwriting_input=True) as pdf:
            root = pdf.Root
            # Strip document-level JS catalog entries.
            for key in ("/Names", "/OpenAction", "/AA"):
                if key in root:
                    del root[key]
            # Walk pages and strip any /AA (additional actions) on each.
            for page in pdf.pages:
                if "/AA" in page:
                    del page["/AA"]
                # Strip annotation actions (form fields, link annotations).
                if "/Annots" in page:
                    annots = page["/Annots"]
                    try:
                        for annot in annots:
                            for k in ("/A", "/AA", "/JS"):
                                if k in annot:
                                    del annot[k]
                    except Exception:  # noqa: BLE001
                        # Non-iterable annots: drop the whole list.
                        del page["/Annots"]
            pdf.save(path)
        return True, ""
    except Exception as e:  # noqa: BLE001
        return False, f"pikepdf strip failed: {type(e).__name__}: {e}"


# ── Image re-encoding ─────────────────────────────────────────────────


def reencode_image(path: Path) -> tuple[bool, str]:
    """Re-encodes the image, stripping EXIF (GPS) and non-pixel chunks.

    Format is preserved (JPEG → JPEG, PNG → PNG). Returns (ok, notes).
    """
    try:
        from PIL import Image  # type: ignore[import-not-found]
    except ImportError:
        return False, "Pillow not installed"

    try:
        with Image.open(path) as im:
            im.load()
            fmt = im.format or "JPEG"
            # Drop EXIF / ICC: re-create the image bypassing the info dict.
            mode = im.mode
            if mode == "P":
                im = im.convert("RGBA" if "transparency" in im.info else "RGB")
            elif mode not in ("RGB", "RGBA", "L"):
                im = im.convert("RGB")
            scrubbed = Image.new(im.mode, im.size)
            scrubbed.paste(im)
            scrubbed.save(path, format=fmt)
        return True, ""
    except Exception as e:  # noqa: BLE001
        return False, f"image re-encode failed: {type(e).__name__}: {e}"


# ── Composite entry point ─────────────────────────────────────────────


def scan_file(path: Path, *, clamav_socket: Path, skip: bool = False) -> ScanResult:
    """Runs ClamAV, then PDF/image sanitisation as applicable.

    The order matters: never sanitise (and therefore read) a file
    ClamAV flagged as infected.

    `skip=True` bypasses ClamAV entirely. Use only in dev or when scans
    happen out-of-band — production must keep this off.
    """
    if not skip:
        try:
            is_clean, sigs, notes = clamav_scan(path, socket=clamav_socket)
        except Exception as e:  # noqa: BLE001
            return ScanResult(result="error", signatures=[], notes=f"{type(e).__name__}: {e}")

        if not is_clean and sigs:
            return ScanResult(result="infected", signatures=sigs, notes=notes)
        if not is_clean:
            return ScanResult(result="suspicious", signatures=[], notes=notes or "clamav unreachable")

    suffix = path.suffix.lower()
    if suffix in SUPPORTED_PDF_SUFFIXES:
        ok, notes = strip_pdf_js(path)
        if not ok:
            return ScanResult(result="suspicious", signatures=[], notes=notes)
    elif suffix in SUPPORTED_IMAGE_SUFFIXES:
        ok, notes = reencode_image(path)
        if not ok:
            return ScanResult(result="suspicious", signatures=[], notes=notes)

    return ScanResult(result="clean", signatures=[], notes="")
