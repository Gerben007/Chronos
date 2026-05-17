# Content pipeline

How content reaches readers, from author intent to rendered page.

## Three input surfaces

1. **Google Sheet** — `entries` and `lanes` tabs. Authoritative for entry
   metadata: slug, lane, dates, importance, scripture refs, artwork URL.
2. **Markdown files** — `apps/site/src/content/wiki/{en,af}/{slug}.md`.
   Long-form prose. Human-authored in English; AI-drafted + reviewed in
   Afrikaans (see `docs/translation-pipeline.md`).
3. **Nextcloud uploads** — `_inbox/` folder. Mothers drop files; ingest
   picks them up within 15 min.

## Pull from sheet

`apps/site/scripts/pull-sheet.ts` (Phase 1):
- Uses service-account creds (`GOOGLE_SHEETS_SA_JSON`).
- Pulls both tabs.
- Validates via Zod (`scripts/validate-schema.ts`).
- Writes to SQLite (`entries`, `entry_translations` with `translation_status='authored'`).
- Triggers full Astro rebuild.

## Webhook from sheet edit

`onEdit` Apps Script trigger fires HMAC-signed POST to ingest webhook.
Ingest re-pulls and rebuilds. Idempotent on `entries.slug`.

## Nextcloud upload

See `docs/security.md` § "File pipeline". Successful processing:
- writes a `files` row,
- writes one or more `links` rows (auto or `needs_review=1`),
- rewrites only the affected `dist/data/entries/{slug}.json`.

## Rebuild matrix

| Trigger                       | What runs                              | Latency target |
|-------------------------------|----------------------------------------|----------------|
| Code change (push to main)    | Full Astro build via CI                | ~5 min         |
| Sheet edit                    | Pull + full rebuild                    | ~5 min         |
| Wiki Markdown change          | Full rebuild                           | ~5 min         |
| New file in `_inbox/` (clean) | Fast-path JSON rewrite, no Astro build | ≤15 min        |
| Translation approval          | Fast-path JSON rewrite                 | ≤15 min        |
| Nightly                       | Full rebuild + backup                  | overnight      |

## Fast-path JSON rewrite

`apps/ingest/chronos_ingest/rebuild.py` (Phase 2). Reads the affected
`entries.slug`, regenerates `/api/v1/entries/{slug}.json` and
`/data/entries/{slug}.json`, writes atomically (temp file + rename),
no nginx reload required.

## Validation

- Zod schemas in `apps/site/scripts/validate-schema.ts` reject malformed
  sheet rows (bad date, missing required field, unknown lane).
- CI fails on schema errors so bad data never reaches a build.
- The fast-path also validates before writing JSON; failures are logged
  to `failed_imports`.
