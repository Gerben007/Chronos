# JSON API (Phase 2)

Read-only, static JSON at `/api/v1/*`. Generated at build time and
refreshed by the fast-path during ingest. CORS-open for GET; cached at
the Cloudflare edge.

## Versioning

`/v1` is a commitment. Breaking changes go to `/v2`; `/v1` stays alive
for at least one major version of any downstream client (Kodi addon,
TV mode, etc.).

Within `/v1`, **additive changes only** (new fields, new endpoints).
Field removals or type changes are breaking and require `/v2`.

## Endpoints

### `GET /api/v1/lanes.json`

Returns the lane catalogue.

```json
[
  {
    "slug": "bible",
    "label": { "en": "Biblical history", "af": "Bybelse geskiedenis" },
    "colour": "#1F2A44",
    "colour_soft": "#DAD4BE",
    "group_label": "biblical",
    "default_visible": true,
    "base_layer": true,
    "sort_order": 1
  }
]
```

### `GET /api/v1/entries.json`

Compact list of every published entry. Suitable for full-timeline
rendering on clients.

```json
[
  {
    "slug": "abraham",
    "type": "person",
    "lane_slug": "bible",
    "start_year": -2166,
    "end_year": -1991,
    "importance": 5,
    "title": { "en": "Abraham", "af": "Abraham" },
    "display_dates": { "en": "2166–1991 BC", "af": "2166–1991 v.C." }
  }
]
```

### `GET /api/v1/entries/{slug}.json?lang=en`

Full entry including wiki Markdown and resource list.

### `GET /api/v1/entries/{slug}/resources.json`

Resource list only (driven by `links` joined to `files`). Refreshed on
fast-path rewrites.

### `GET /api/v1/eras.json`

`type='period'` entries flagged as eras. Drives era jump buttons on
downstream clients.

### `GET /api/v1/search.json?q=...&lang=en`  *(Phase 3)*

FTS5-backed search across titles, summaries, wiki Markdown, and file
summaries. Returns highlighted snippets.

## CORS + caching

- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Methods: GET, OPTIONS`
- `Cache-Control: public, max-age=60` (with Cloudflare edge cache)
- Rate-limited at Cloudflare WAF: 1000 req/h per IP.

## Clients

- Phase 1: in-process site fetcher only.
- Phase 2: public consumption (any browser, any TV browser).
- Phase 3: `chronos-kodi` addon — pins `/api/v1/`.
