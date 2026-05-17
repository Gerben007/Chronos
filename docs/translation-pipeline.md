# Translation pipeline

Chronos is bilingual (English + Afrikaans). English is the source of
truth; Afrikaans is produced by Claude Haiku draft + admin review.

## Lifecycle

```
authored (en)
    │   translate.py
    ▼
ai_draft (af)         ← visible only in admin review queue
    │   admin clicks "approve" (or edits + approve)
    ▼
reviewed (af)         ← still not public
    │   publish (fast-path rewrite)
    ▼
published (af)        ← visible to readers
```

`translation_status` lives on `entry_translations(entry_id, lang)`.

## What gets translated

- `entries.display_dates_*`         — short string, manual translation.
- `entry_translations.summary`      — Haiku draft, reviewed.
- `entry_translations.wiki_md`      — Haiku draft, reviewed.
- `files.ai_summary_af`             — Haiku draft, reviewed via quarantine queue.

## What does NOT get translated by AI

- Scripture text. Always loaded from the appropriate translation in
  `bible_verses` (KJV / ESV / af1933).
- Filenames, slugs, URLs.
- Anything inside a markdown code block.

## Prompt directive (key rules)

The Haiku translation prompt explicitly:

- Forbids inserting content not present in the source.
- Forbids theological speculation or doctrinal commentary.
- Preserves scripture references verbatim.
- Maintains 1933/53 Afrikaans register (formal, traditional, not modern OAB).
- Returns valid Markdown structurally identical to the source.

## Reviewer responsibilities

The admin reviewer:

- Confirms theological correctness for a conservative-Protestant audience.
- Adjusts register / idiom where the AI was too literal.
- Sets `reviewed_at` and `reviewed_by` (audit trail in-DB).
- May reject and request re-draft (cycles back to `ai_draft`).

## "Translation pending" badge

When an entry has `wiki_md` in English but no `published` Afrikaans
version, the AF view shows the English content with a visible
`Afrikaans translation pending review` badge — never silently falls
back, never shows the unreviewed draft.

## Budget

Translation calls share the daily `DAILY_HAIKU_BUDGET_USD` ceiling with
file classification. Translation defers when the budget is exhausted;
resumes at midnight UTC.
