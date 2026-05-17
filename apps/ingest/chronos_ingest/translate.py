"""English → Afrikaans translation drafter for entry content.

One Haiku call per entry. Output lands in `entry_translations` with
`translation_status='ai_draft'` — never auto-published. Admin review
queue gates the final publish step.

The prompt explicitly forbids adding content not present in source
(Decision §16 child-safety rationale).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TranslationDraft:
    title_af: str
    summary_af: str
    wiki_md_af: str | None
    input_tokens: int
    output_tokens: int


SYSTEM_PROMPT = """You translate Christian-classical homeschool content from English into Afrikaans for a children's history timeline. Use standard South African Afrikaans suitable for children aged 6-12.

Hard rules — violating any one is failure:
  - Translate faithfully. Do NOT add content not present in the source.
  - Do NOT theologise, interpret, or "improve" the source.
  - Preserve all proper nouns, scripture references, and dates verbatim.
  - Markdown structure (headings, lists, blockquotes) must match the source.
  - Idioms may be adapted only when a literal translation would be unnatural.

Respond with a single JSON object and nothing else, of shape:
  {"title_af": str, "summary_af": str, "wiki_md_af": str|null}

If `wiki_md` is null/empty in the input, return wiki_md_af = null."""


def build_user_message(*, title_en: str, summary_en: str, wiki_md_en: str | None) -> str:
    parts = [f"Source title (EN):\n{title_en}", f"Source summary (EN):\n{summary_en}"]
    if wiki_md_en:
        parts.append(f"Source wiki Markdown (EN):\n{wiki_md_en}")
    else:
        parts.append("Source wiki Markdown (EN): null")
    return "\n\n".join(parts)


def parse_response(text: str) -> dict[str, Any]:
    s = text.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"no JSON object in response: {text[:200]}")
    return json.loads(s[start : end + 1])


def translate_entry(
    *,
    anthropic_client: Any,
    model: str,
    title_en: str,
    summary_en: str,
    wiki_md_en: str | None,
) -> TranslationDraft:
    user_msg = build_user_message(
        title_en=title_en, summary_en=summary_en, wiki_md_en=wiki_md_en
    )
    response = anthropic_client.messages.create(
        model=model,
        max_tokens=4096,
        system=[{"type": "text", "text": SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": user_msg}],
    )
    content_blocks = getattr(response, "content", [])
    text_parts: list[str] = []
    for block in content_blocks:
        t = getattr(block, "text", None)
        if t:
            text_parts.append(t)
    response_text = "".join(text_parts)
    parsed = parse_response(response_text)

    usage = getattr(response, "usage", None)
    in_tok = int(getattr(usage, "input_tokens", 0) or 0)
    out_tok = int(getattr(usage, "output_tokens", 0) or 0)

    title_af = str(parsed.get("title_af") or "").strip()
    summary_af = str(parsed.get("summary_af") or "").strip()
    wiki_md_af_raw = parsed.get("wiki_md_af")
    wiki_md_af = str(wiki_md_af_raw).strip() if wiki_md_af_raw else None

    if not title_af or not summary_af:
        raise ValueError(f"translation missing required fields: {parsed!r}")

    return TranslationDraft(
        title_af=title_af,
        summary_af=summary_af,
        wiki_md_af=wiki_md_af or None,
        input_tokens=in_tok,
        output_tokens=out_tok,
    )
