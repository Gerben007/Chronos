"""Haiku classification for an uploaded file.

One API call per file:
  - System prompt + (cached) entry list block describing every Chronos entry.
  - User message containing the file's title, type, extracted text, and any
    parsed CC cycle/week hints from the filename.

Haiku returns a structured JSON blob naming up to N entries with confidence
and reason, plus the file's CC cycle/week, age range, an English summary,
and a moderation flag.

Confidence thresholds (Decision §7):
  - ≥0.7  → auto-link (links.needs_review = 0)
  - 0.5-0.7 → suggest, needs admin review (links.needs_review = 1)
  - <0.5 → discard
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


# ── Pricing (used for budget.may_call estimates) ──────────────────────
# Source: anthropic.com/pricing. Adjusted per million tokens.
HAIKU_INPUT_PER_MTOK_USD = 0.80
HAIKU_OUTPUT_PER_MTOK_USD = 4.00
HAIKU_CACHE_HIT_PER_MTOK_USD = 0.08
HAIKU_CACHE_WRITE_PER_MTOK_USD = 1.00


CONFIDENCE_AUTO_LINK = 0.70
CONFIDENCE_REVIEW_MIN = 0.50


@dataclass(frozen=True)
class LinkSuggestion:
    entry_slug: str
    confidence: float
    reason: str

    @property
    def needs_review(self) -> bool:
        return self.confidence < CONFIDENCE_AUTO_LINK

    @property
    def is_keepable(self) -> bool:
        return self.confidence >= CONFIDENCE_REVIEW_MIN


@dataclass(frozen=True)
class Classification:
    """Structured classifier output."""

    links: list[LinkSuggestion]
    summary_en: str
    cc_cycle: int | None
    cc_week: int | None
    age_min: int | None
    age_max: int | None
    moderation_flag: bool
    raw_response: str
    input_tokens: int
    output_tokens: int

    @property
    def cost_usd(self) -> float:
        return (
            (self.input_tokens / 1_000_000) * HAIKU_INPUT_PER_MTOK_USD
            + (self.output_tokens / 1_000_000) * HAIKU_OUTPUT_PER_MTOK_USD
        )


_FILENAME_CC_RE = re.compile(
    r"(?:^|[\W_])(?:cc|cycle)\s*[-_]?\s*(\d)(?:[\W_].*?(?:wk|week)\s*[-_]?\s*(\d{1,2}))?",
    re.IGNORECASE,
)


def parse_cc_from_filename(name: str) -> tuple[int | None, int | None]:
    """Heuristic — many mother-uploaded filenames carry `CC1-Wk3` patterns.

    Returns (cycle, week) — either may be None.
    """
    m = _FILENAME_CC_RE.search(name)
    if not m:
        return None, None
    cycle = int(m.group(1))
    week = int(m.group(2)) if m.group(2) else None
    if cycle not in (1, 2, 3):
        return None, None
    if week is not None and not 1 <= week <= 24:
        week = None
    return cycle, week


# ── Prompt construction ────────────────────────────────────────────────


SYSTEM_PROMPT = """You classify Christian-classical homeschool resource files for a children's history timeline called Chronos. Output is consumed by code, so you MUST respond with a single JSON object and nothing else.

For every file, decide:
  - Which timeline entries (by slug) it relates to, with a confidence 0.0-1.0 and a one-sentence reason.
  - The Classical Conversations cycle (1, 2, or 3) and week (1-24), if discernible.
  - The intended age range (age_min, age_max).
  - A short English summary (<=300 chars), neutral and factual.
  - A moderation flag set to true only if the file appears age-inappropriate for children, contains gratuitous violence/nudity, or is otherwise unsuitable for primary-school use.

Conservative bias: if unsure about a link, lower the confidence rather than fabricate. Never invent slugs that aren't in the entry list. Confidence below 0.5 means the link is likely wrong; we will discard those."""


def build_entry_context(entries: list[dict[str, Any]]) -> str:
    """Compact one-line-per-entry table for the cached context block.

    Format:  slug | lane_slug | type | start_year [to end_year] | English title
    """
    lines = ["slug | lane | type | years | title"]
    for e in entries:
        years = str(e["start_year"])
        if e.get("end_year") is not None:
            years += f" to {e['end_year']}"
        lines.append(
            f"{e['slug']} | {e['lane_slug']} | {e['type']} | {years} | {e['title_en']}"
        )
    return "\n".join(lines)


def build_user_message(
    *,
    title: str,
    file_type: str,
    size_bytes: int | None,
    extracted_text: str | None,
    path_cycle: int | None = None,
    path_stage: str | None = None,
    path_week: int | None = None,
    filename_cc_cycle: int | None = None,
    filename_cc_week: int | None = None,
) -> str:
    parts: list[str] = []
    parts.append(f"Title: {title}")
    parts.append(f"File type: {file_type}")
    if size_bytes is not None:
        parts.append(f"Size bytes: {size_bytes}")
    # Path-derived hints are stronger than filename hints — the folder
    # structure is authoritative for CC cycle/stage/week.
    path_hints: list[str] = []
    if path_cycle is not None:
        path_hints.append(f"cycle {path_cycle}")
    if path_stage is not None:
        path_hints.append(f"{path_stage} stage")
    if path_week is not None:
        path_hints.append(f"week {path_week}")
    if path_hints:
        parts.append("Authoritative folder metadata: " + ", ".join(path_hints))
    elif filename_cc_cycle is not None:
        hint = f"Filename suggests CC cycle {filename_cc_cycle}"
        if filename_cc_week is not None:
            hint += f", week {filename_cc_week}"
        parts.append(hint)
    if extracted_text:
        parts.append("Extracted text (truncated):\n" + extracted_text[:3000])
    parts.append(
        "\nReply with JSON of shape: "
        '{"links": [{"entry_slug": str, "confidence": float, "reason": str}], '
        '"summary_en": str, "cc_cycle": int|null, "cc_week": int|null, '
        '"age_min": int|null, "age_max": int|null, "moderation_flag": bool}'
    )
    return "\n\n".join(parts)


def parse_response(text: str) -> dict[str, Any]:
    """Pulls the first JSON object out of Haiku's reply.

    Models sometimes wrap JSON in ``` fences despite instructions. Strip
    them defensively.
    """
    s = text.strip()
    if s.startswith("```"):
        # Strip leading ``` or ```json
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"no JSON object in response: {text[:200]}")
    return json.loads(s[start : end + 1])


def build_classification(
    *,
    response_text: str,
    input_tokens: int,
    output_tokens: int,
    valid_slugs: set[str],
) -> Classification:
    """Parses Haiku's response and drops any link to a slug that doesn't exist."""
    parsed = parse_response(response_text)
    raw_links = parsed.get("links") or []
    links: list[LinkSuggestion] = []
    for item in raw_links:
        slug = item.get("entry_slug")
        if not isinstance(slug, str) or slug not in valid_slugs:
            continue
        try:
            conf = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            continue
        conf = max(0.0, min(1.0, conf))
        reason = str(item.get("reason") or "")[:300]
        sugg = LinkSuggestion(entry_slug=slug, confidence=conf, reason=reason)
        if sugg.is_keepable:
            links.append(sugg)

    return Classification(
        links=links,
        summary_en=str(parsed.get("summary_en") or "")[:600],
        cc_cycle=_int_or_none(parsed.get("cc_cycle")),
        cc_week=_int_or_none(parsed.get("cc_week")),
        age_min=_int_or_none(parsed.get("age_min")),
        age_max=_int_or_none(parsed.get("age_max")),
        moderation_flag=bool(parsed.get("moderation_flag", False)),
        raw_response=response_text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def _int_or_none(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# ── Anthropic call wrapper ────────────────────────────────────────────


def classify_file(
    *,
    anthropic_client: Any,  # anthropic.Anthropic
    model: str,
    title: str,
    file_type: str,
    size_bytes: int | None,
    extracted_text: str | None,
    filename: str,
    entries: list[dict[str, Any]],
    path_cycle: int | None = None,
    path_stage: str | None = None,
    path_week: int | None = None,
) -> Classification:
    """Single Haiku call. Caller is responsible for budget check.

    Path hints (cycle/stage/week derived from the folder structure) take
    precedence over filename hints when both are present.
    """
    cycle_hint, week_hint = parse_cc_from_filename(filename)
    user_msg = build_user_message(
        title=title,
        file_type=file_type,
        size_bytes=size_bytes,
        extracted_text=extracted_text,
        path_cycle=path_cycle,
        path_stage=path_stage,
        path_week=path_week,
        filename_cc_cycle=cycle_hint,
        filename_cc_week=week_hint,
    )
    valid_slugs = {e["slug"] for e in entries}
    entry_block = build_entry_context(entries)

    # The entry list is hashed into a cache_control breakpoint so subsequent
    # calls within a 5-minute window pay the cache-hit rate.
    response = anthropic_client.messages.create(
        model=model,
        max_tokens=1024,
        system=[
            {"type": "text", "text": SYSTEM_PROMPT},
            {
                "type": "text",
                "text": f"Chronos entry catalogue (authoritative slug list):\n{entry_block}",
                "cache_control": {"type": "ephemeral"},
            },
        ],
        messages=[{"role": "user", "content": user_msg}],
    )

    content_blocks = getattr(response, "content", [])
    text_parts: list[str] = []
    for block in content_blocks:
        t = getattr(block, "text", None)
        if t:
            text_parts.append(t)
    response_text = "".join(text_parts)

    usage = getattr(response, "usage", None)
    in_tok = int(getattr(usage, "input_tokens", 0) or 0)
    out_tok = int(getattr(usage, "output_tokens", 0) or 0)

    return build_classification(
        response_text=response_text,
        input_tokens=in_tok,
        output_tokens=out_tok,
        valid_slugs=valid_slugs,
    )
