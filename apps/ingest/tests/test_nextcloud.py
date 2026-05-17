from __future__ import annotations

import pytest

from chronos_ingest.nextcloud import NextcloudClient, classify_filetype


def test_classify_filetype_known() -> None:
    assert classify_filetype("foo.pdf") == "pdf"
    assert classify_filetype("FOO.PDF") == "pdf"
    assert classify_filetype("clip.mp4") == "video"
    assert classify_filetype("song.mp3") == "audio"
    assert classify_filetype("pic.JPG") == "image"
    assert classify_filetype("notes.md") == "doc"


def test_classify_filetype_unknown() -> None:
    assert classify_filetype("archive.zip") is None
    assert classify_filetype("noext") is None


def test_client_requires_credentials() -> None:
    with pytest.raises(ValueError):
        NextcloudClient(base_url="", username="u", app_password="p")
    with pytest.raises(ValueError):
        NextcloudClient(base_url="https://x", username="", app_password="p")


def test_dav_url_quoting() -> None:
    c = NextcloudClient(
        base_url="https://nc.example.com",
        username="gerben",
        app_password="secret",
    )
    try:
        url = c._dav_url("/CC-Library/_inbox/foo bar.pdf")
        assert url == (
            "https://nc.example.com/remote.php/dav/files/gerben/"
            "CC-Library/_inbox/foo%20bar.pdf"
        )
    finally:
        c.close()


def test_parse_propfind_filters_dirs_and_self() -> None:
    """Smoke-test the response parser with a hand-rolled XML payload."""
    body = """<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:">
  <d:response>
    <d:href>/remote.php/dav/files/gerben/CC-Library/_inbox/</d:href>
    <d:propstat><d:prop>
      <d:resourcetype><d:collection/></d:resourcetype>
    </d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>
  </d:response>
  <d:response>
    <d:href>/remote.php/dav/files/gerben/CC-Library/_inbox/a.pdf</d:href>
    <d:propstat><d:prop>
      <d:displayname>a.pdf</d:displayname>
      <d:getcontentlength>1234</d:getcontentlength>
      <d:getcontenttype>application/pdf</d:getcontenttype>
      <d:getetag>"abc123"</d:getetag>
      <d:resourcetype/>
    </d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>
  </d:response>
  <d:response>
    <d:href>/remote.php/dav/files/gerben/CC-Library/_inbox/subdir/</d:href>
    <d:propstat><d:prop>
      <d:resourcetype><d:collection/></d:resourcetype>
    </d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>
  </d:response>
</d:multistatus>
"""
    c = NextcloudClient(
        base_url="https://nc.example.com",
        username="gerben",
        app_password="secret",
    )
    try:
        files = c._parse_propfind(body, parent_path="/CC-Library/_inbox")
    finally:
        c.close()
    assert len(files) == 1
    f = files[0]
    assert f.name == "a.pdf"
    assert f.path == "/CC-Library/_inbox/a.pdf"
    assert f.size == 1234
    assert f.content_type == "application/pdf"
    assert f.etag == "abc123"
    assert f.is_dir is False
