# Chronology

Chronos uses **Ussher** dating (Creation 4004 BC) as the primary timeline.
Alternate chronologies (Masoretic, LXX) are carried per-entry in
`entries.start_year_alt_json` and surfaced in the entry detail page as a
small note, never as a swap of the headline year.

## Why Ussher

- Familiar to the conservative-Protestant homeschool audience.
- Self-consistent across the OT.
- Trivial to override per-entry where scholarly consensus differs
  meaningfully (e.g. Exodus 1446 BC vs 1290 BC date debate).

## Year representation

- Signed integers; BC is negative. AD is positive.
- There is no year 0; AD 1 is `1`, BC 1 is `-1`. Date helpers must respect
  this (see `apps/site/src/lib/dates.ts` once implemented).
- `display_dates_en` and `display_dates_af` are pre-formatted strings used
  by the UI; the integer columns drive sorting and placement only.

## Alternate-chronology payload

```json
{
  "masoretic": { "start_year": -1446, "source": "Kitchen" },
  "lxx":       { "start_year": -1280, "source": "Cassuto" }
}
```

`chronology_note_en` / `chronology_note_af` accompany the JSON with a
one-line summary suitable for inline rendering.

## Era boundaries (Phase 1)

| Era                | Approx range       | Notes |
|--------------------|--------------------|-------|
| Pre-Patriarchal    | 4004 – 2166 BC     | Adam → Abraham |
| Patriarchs         | 2166 – 1876 BC     | Abraham → Joseph |
| Egypt (sojourn)    | 1876 – 1446 BC     | Joseph → Exodus |
| Wilderness & Judges| 1446 – 1050 BC     | Sinai → Samuel |
| United Kingdom     | 1050 – 930 BC      | Saul → Rehoboam |
| Divided Kingdom    | 930 – 586 BC       | Schism → Babylon |
| Exile & Return     | 586 – 400 BC       | Babylon → Malachi |
| Inter-testamental  | 400 BC – 6 BC      | Maccabees → birth |
| Christ             | 6 BC – AD 33       | birth → resurrection |
| Apostolic          | AD 33 – AD 100     | Acts → John |

Era buttons in the timeline header jump to these ranges. Stored as
`type='period'` entries linked together via `parent_period_slug`.
