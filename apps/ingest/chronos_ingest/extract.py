"""Best-effort text + metadata extraction.

Whatever each backend (pdfplumber, Pillow, ffprobe) gives us is wrapped
in a typed dataclass and capped in size. The classifier only needs a
few thousand chars to make a confident decision.

All native libraries are imported lazily so unit tests run without them.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


MAX_TEXT_CHARS = 3000


@dataclass(frozen=True)
class ExtractResult:
    text: str | None
    duration_seconds: int | None
    width: int | None
    height: int | None
    notes: str = ""


def extract_pdf_text(path: Path, *, max_chars: int = MAX_TEXT_CHARS) -> str | None:
    """Returns the first `max_chars` of concatenated page text, or None."""
    try:
        import pdfplumber  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        chunks: list[str] = []
        used = 0
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                if used >= max_chars:
                    break
                t = page.extract_text() or ""
                if not t:
                    continue
                room = max_chars - used
                chunks.append(t[:room])
                used += len(t[:room])
        out = "\n".join(chunks).strip()
        return out or None
    except Exception:  # noqa: BLE001
        return None


def extract_image_meta(path: Path) -> tuple[int | None, int | None]:
    """Returns (width, height), or (None, None) on failure."""
    try:
        from PIL import Image  # type: ignore[import-not-found]
    except ImportError:
        return None, None
    try:
        with Image.open(path) as im:
            return im.width, im.height
    except Exception:  # noqa: BLE001
        return None, None


def ffprobe_duration(path: Path) -> int | None:
    """Returns the duration in whole seconds, or None.

    Shells out to ffprobe with a strict argv (no shell=True).
    """
    binary = shutil.which("ffprobe")
    if not binary:
        return None
    try:
        proc = subprocess.run(  # noqa: S603 - argv is fixed
            [
                binary,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                str(path),
            ],
            capture_output=True,
            timeout=20,
            check=False,
        )
        if proc.returncode != 0:
            return None
        data = json.loads(proc.stdout.decode("utf-8", errors="replace"))
        dur = data.get("format", {}).get("duration")
        if dur is None:
            return None
        return int(float(dur))
    except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError):
        return None


def extract(path: Path, *, file_type: str) -> ExtractResult:
    """Dispatches to the right extractor based on file_type.

    Always returns a result — extractor failures collapse to empty fields,
    not exceptions. The pipeline can still classify on title + size alone.
    """
    if file_type == "pdf":
        return ExtractResult(
            text=extract_pdf_text(path),
            duration_seconds=None,
            width=None,
            height=None,
        )
    if file_type == "image":
        w, h = extract_image_meta(path)
        return ExtractResult(text=None, duration_seconds=None, width=w, height=h)
    if file_type in ("video", "audio"):
        return ExtractResult(
            text=None,
            duration_seconds=ffprobe_duration(path),
            width=None,
            height=None,
        )
    return ExtractResult(text=None, duration_seconds=None, width=None, height=None)
