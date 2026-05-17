from __future__ import annotations

import pytest

from chronos_ingest.nextcloud import (
    NextcloudClient,
    classify_filetype,
    parse_path_metadata,
)


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


def test_parse_propfind_recursive_filters_dirs() -> None:
    """Recursive PROPFIND returns files at arbitrary depth; dirs are dropped."""
    body = """<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:">
  <d:response>
    <d:href>/remote.php/dav/files/gerben/Chronos/</d:href>
    <d:propstat><d:prop>
      <d:resourcetype><d:collection/></d:resourcetype>
    </d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>
  </d:response>
  <d:response>
    <d:href>/remote.php/dav/files/gerben/Chronos/Cycle%201/1.%20Foundations%20(Grammar%20Stage)/Week%205/abraham.pdf</d:href>
    <d:propstat><d:prop>
      <d:displayname>abraham.pdf</d:displayname>
      <d:getcontentlength>1234</d:getcontentlength>
      <d:getcontenttype>application/pdf</d:getcontenttype>
      <d:getetag>"abc123"</d:getetag>
      <d:resourcetype/>
    </d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>
  </d:response>
  <d:response>
    <d:href>/remote.php/dav/files/gerben/Chronos/Cycle%201/1.%20Foundations%20(Grammar%20Stage)/Week%205/</d:href>
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
        files = c._parse_propfind(body, parent_path="/Chronos")
    finally:
        c.close()
    assert len(files) == 1
    f = files[0]
    assert f.name == "abraham.pdf"
    assert f.path == "/Chronos/Cycle 1/1. Foundations (Grammar Stage)/Week 5/abraham.pdf"
    assert f.size == 1234
    assert f.is_dir is False


def test_parse_path_metadata_full() -> None:
    p = "/Chronos/Cycle 2/2. Essentials (Dialectic Stage)/Week 12/foo.pdf"
    m = parse_path_metadata(p)
    assert m.cycle == 2
    assert m.stage == "essentials"
    assert m.week == 12


def test_parse_path_metadata_alternate_stage_keywords() -> None:
    m = parse_path_metadata("/Chronos/Cycle 1/Grammar/Week 3/foo.pdf")
    assert m.stage == "foundations"
    m = parse_path_metadata("/Chronos/Cycle 3/Rhetoric/Week 1/foo.pdf")
    assert m.stage == "challenge"


def test_parse_path_metadata_missing() -> None:
    m = parse_path_metadata("/Chronos/loose-file.pdf")
    assert m.cycle is None
    assert m.stage is None
    assert m.week is None


def test_parse_path_metadata_out_of_range() -> None:
    m = parse_path_metadata("/Chronos/Cycle 7/Week 99/foo.pdf")
    assert m.cycle is None
    assert m.week is None
