from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from chronos_ingest import classify
from chronos_ingest.classify import (
    CONFIDENCE_AUTO_LINK,
    CONFIDENCE_REVIEW_MIN,
    LinkSuggestion,
    build_classification,
    build_entry_context,
    parse_cc_from_filename,
    parse_response,
)


def test_parse_cc_from_filename_cycle_only() -> None:
    assert parse_cc_from_filename("CC2 - Augustus.pdf") == (2, None)
    assert parse_cc_from_filename("cycle_3_overview.pdf") == (3, None)


def test_parse_cc_from_filename_cycle_and_week() -> None:
    assert parse_cc_from_filename("CC1-Wk5 timeline.pdf") == (1, 5)
    assert parse_cc_from_filename("cc2 week 12.pdf") == (2, 12)


def test_parse_cc_from_filename_invalid() -> None:
    assert parse_cc_from_filename("random.pdf") == (None, None)
    assert parse_cc_from_filename("CC4-Wk1.pdf") == (None, None)


def test_link_review_thresholds() -> None:
    auto = LinkSuggestion(entry_slug="a", confidence=0.85, reason="r")
    review = LinkSuggestion(entry_slug="a", confidence=0.6, reason="r")
    discard = LinkSuggestion(entry_slug="a", confidence=0.3, reason="r")
    assert auto.needs_review is False
    assert review.needs_review is True
    assert discard.is_keepable is False
    assert review.is_keepable is True
    assert CONFIDENCE_AUTO_LINK == 0.70
    assert CONFIDENCE_REVIEW_MIN == 0.50


def test_build_entry_context_layout() -> None:
    block = build_entry_context([
        {
            "slug": "abraham",
            "lane_slug": "bible",
            "type": "person",
            "start_year": -2000,
            "end_year": None,
            "title_en": "Abraham",
        },
        {
            "slug": "rome",
            "lane_slug": "rome",
            "type": "period",
            "start_year": -753,
            "end_year": 476,
            "title_en": "Roman Empire",
        },
    ])
    assert block.splitlines()[0] == "slug | lane | type | years | title"
    assert "abraham | bible | person | -2000 | Abraham" in block
    assert "rome | rome | period | -753 to 476 | Roman Empire" in block


def test_parse_response_handles_fences() -> None:
    raw = '```json\n{"a": 1}\n```'
    assert parse_response(raw) == {"a": 1}


def test_parse_response_raises_on_no_json() -> None:
    with pytest.raises(ValueError):
        parse_response("hello world")


def test_build_classification_drops_unknown_slugs_and_low_confidence() -> None:
    response = (
        '{"links": ['
        '{"entry_slug": "abraham", "confidence": 0.9, "reason": "match"},'
        '{"entry_slug": "made-up", "confidence": 0.95, "reason": "x"},'
        '{"entry_slug": "abraham", "confidence": 0.3, "reason": "weak"}'
        '], "summary_en": "A short summary.", "cc_cycle": 1, "cc_week": 3, '
        '"age_min": 6, "age_max": 10, "moderation_flag": false}'
    )
    c = build_classification(
        response_text=response,
        input_tokens=200,
        output_tokens=150,
        valid_slugs={"abraham", "rome"},
    )
    assert len(c.links) == 1
    assert c.links[0].entry_slug == "abraham"
    assert c.links[0].confidence == 0.9
    assert c.cc_cycle == 1
    assert c.cc_week == 3
    assert c.age_min == 6
    assert c.age_max == 10
    assert c.moderation_flag is False
    assert c.cost_usd > 0


def test_build_classification_clamps_confidence() -> None:
    response = (
        '{"links": [{"entry_slug": "rome", "confidence": 1.7, "reason": "r"}], '
        '"summary_en": "", "cc_cycle": null, "cc_week": null, '
        '"age_min": null, "age_max": null, "moderation_flag": true}'
    )
    c = build_classification(
        response_text=response,
        input_tokens=100,
        output_tokens=50,
        valid_slugs={"rome"},
    )
    assert c.links[0].confidence == 1.0
    assert c.moderation_flag is True


# ── End-to-end classify_file with mocked Anthropic ─────────────────────


@dataclass
class _FakeUsage:
    input_tokens: int = 230
    output_tokens: int = 90


@dataclass
class _FakeBlock:
    text: str


@dataclass
class _FakeResponse:
    content: list[_FakeBlock]
    usage: _FakeUsage


class _FakeAnthropic:
    """Minimal stand-in capturing the request and returning a canned reply."""

    def __init__(self, reply_text: str) -> None:
        self.reply_text = reply_text
        self.captured: dict[str, Any] | None = None

        class _Messages:
            def __init__(inner_self) -> None:
                inner_self.parent = self

            def create(inner_self, **kwargs: Any) -> _FakeResponse:
                inner_self.parent.captured = kwargs
                return _FakeResponse(
                    content=[_FakeBlock(text=inner_self.parent.reply_text)],
                    usage=_FakeUsage(),
                )

        self.messages = _Messages()


def test_classify_file_passes_cached_entry_block() -> None:
    fake = _FakeAnthropic(
        reply_text=(
            '{"links": [{"entry_slug": "abraham", "confidence": 0.8, "reason": "r"}], '
            '"summary_en": "x", "cc_cycle": null, "cc_week": null, '
            '"age_min": null, "age_max": null, "moderation_flag": false}'
        )
    )
    out = classify.classify_file(
        anthropic_client=fake,
        model="claude-haiku-4-5-20251001",
        title="Abraham notes",
        file_type="pdf",
        size_bytes=12345,
        extracted_text="Abram was called by God...",
        filename="CC1-Wk3 abraham.pdf",
        entries=[{
            "slug": "abraham",
            "lane_slug": "bible",
            "type": "person",
            "start_year": -2000,
            "end_year": None,
            "title_en": "Abraham",
        }],
    )
    assert isinstance(out, classify.Classification)
    assert len(out.links) == 1
    assert out.links[0].entry_slug == "abraham"
    assert fake.captured is not None
    sys = fake.captured["system"]
    assert len(sys) == 2
    assert sys[1]["cache_control"] == {"type": "ephemeral"}
    assert "abraham | bible" in sys[1]["text"]
