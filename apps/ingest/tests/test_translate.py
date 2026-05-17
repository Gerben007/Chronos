from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from chronos_ingest import translate
from chronos_ingest.translate import parse_response


@dataclass
class _Usage:
    input_tokens: int = 400
    output_tokens: int = 600


@dataclass
class _Block:
    text: str


@dataclass
class _Response:
    content: list[_Block]
    usage: _Usage


class _FakeAnthropic:
    def __init__(self, reply: str) -> None:
        self.reply = reply

        class _Messages:
            def create(inner_self, **kwargs: Any) -> _Response:  # noqa: ARG002
                return _Response(content=[_Block(text=self.reply)], usage=_Usage())

        self.messages = _Messages()


def test_parse_response_strips_fences() -> None:
    raw = '```\n{"title_af": "Abram", "summary_af": "Vader", "wiki_md_af": null}\n```'
    assert parse_response(raw)["title_af"] == "Abram"


def test_translate_entry_happy_path() -> None:
    fake = _FakeAnthropic(
        '{"title_af": "Abram", '
        '"summary_af": "Vader van nasies.", '
        '"wiki_md_af": "## Abram\\n\\n..."}'
    )
    out = translate.translate_entry(
        anthropic_client=fake,
        model="claude-haiku-4-5-20251001",
        title_en="Abraham",
        summary_en="Father of nations.",
        wiki_md_en="## Abraham\n\n...",
    )
    assert out.title_af == "Abram"
    assert out.summary_af == "Vader van nasies."
    assert out.wiki_md_af is not None
    assert out.wiki_md_af.startswith("## Abram")
    assert out.input_tokens == 400
    assert out.output_tokens == 600


def test_translate_entry_no_wiki() -> None:
    fake = _FakeAnthropic(
        '{"title_af": "Augustus", "summary_af": "Keiser.", "wiki_md_af": null}'
    )
    out = translate.translate_entry(
        anthropic_client=fake,
        model="claude-haiku-4-5-20251001",
        title_en="Augustus",
        summary_en="Emperor.",
        wiki_md_en=None,
    )
    assert out.wiki_md_af is None


def test_translate_entry_missing_required_field_raises() -> None:
    fake = _FakeAnthropic('{"title_af": "", "summary_af": "x"}')
    with pytest.raises(ValueError):
        translate.translate_entry(
            anthropic_client=fake,
            model="claude-haiku-4-5-20251001",
            title_en="X",
            summary_en="Y",
            wiki_md_en=None,
        )
