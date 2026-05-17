-- Chronos — initial schema. Matches PLAN.md §5.
-- Apply with: sqlite3 db/chronos.db < db/migrations/0001_init.sql
-- All writes happen from the ingest container only. Web is read-only.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ── Lanes ─────────────────────────────────────────────────────────────────────
CREATE TABLE lanes (
  id              INTEGER PRIMARY KEY,
  slug            TEXT NOT NULL UNIQUE,
  label_en        TEXT NOT NULL,
  label_af        TEXT,
  colour          TEXT NOT NULL,                  -- '#RRGGBB' label colour
  colour_soft     TEXT NOT NULL,                  -- '#RRGGBB' soft fill / strip
  group_label     TEXT NOT NULL,                  -- 'biblical','empires','church-history',
                                                  -- 'science','arts','modern'
  default_visible INTEGER NOT NULL DEFAULT 1,
  base_layer      INTEGER NOT NULL DEFAULT 0,    -- always on; never hideable
  sort_order      INTEGER NOT NULL DEFAULT 0
);

-- ── Entries ──────────────────────────────────────────────────────────────────
CREATE TABLE entries (
  id                  INTEGER PRIMARY KEY,
  slug                TEXT NOT NULL UNIQUE,
  type                TEXT NOT NULL CHECK (type IN ('person','event','period','prophecy')),
  lane_id             INTEGER NOT NULL REFERENCES lanes(id),
  start_year          INTEGER NOT NULL,           -- signed; BC is negative
  end_year            INTEGER,
  display_dates_en    TEXT NOT NULL,
  display_dates_af    TEXT,
  importance          INTEGER NOT NULL DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
  parent_period_slug  TEXT REFERENCES entries(slug),
  scripture_refs_json TEXT,
  artwork_url         TEXT,
  artwork_credit      TEXT,
  start_year_alt_json TEXT,                       -- Masoretic / LXX alternates to Ussher
  chronology_note_en  TEXT,
  chronology_note_af  TEXT,
  created_at          TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_entries_lane       ON entries(lane_id);
CREATE INDEX idx_entries_year       ON entries(start_year, end_year);
CREATE INDEX idx_entries_importance ON entries(importance);

-- ── Entry translations (one row per language) ────────────────────────────────
CREATE TABLE entry_translations (
  entry_id            INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
  lang                TEXT NOT NULL CHECK (lang IN ('en','af')),
  title               TEXT NOT NULL,
  summary             TEXT NOT NULL,
  wiki_md             TEXT,
  translation_status  TEXT NOT NULL DEFAULT 'authored'
                      CHECK (translation_status IN ('authored','ai_draft','reviewed','published')),
  source_lang         TEXT,                       -- 'en' when this is an AI translation from en
  ai_draft_at         TEXT,
  reviewed_at         TEXT,
  reviewed_by         TEXT,
  PRIMARY KEY (entry_id, lang)
);
CREATE INDEX idx_translations_status
  ON entry_translations(translation_status)
  WHERE translation_status IN ('ai_draft','reviewed');

-- ── Files (uploaded resources) ───────────────────────────────────────────────
CREATE TABLE files (
  id               INTEGER PRIMARY KEY,
  nextcloud_path   TEXT NOT NULL UNIQUE,
  public_url       TEXT,                          -- OCS share URL, permissions=1
  file_type        TEXT NOT NULL CHECK (file_type IN ('pdf','video','audio','image','doc')),
  title            TEXT NOT NULL,
  size_bytes       INTEGER,
  duration_seconds INTEGER,
  extracted_text   TEXT,
  ai_summary_en    TEXT,
  ai_summary_af    TEXT,
  cc_cycle         INTEGER,
  cc_week          INTEGER,
  age_min          INTEGER,
  age_max          INTEGER,
  scan_result      TEXT,                          -- 'clean','infected','suspicious','error'
  scan_signatures  TEXT,                          -- ClamAV signatures if flagged
  moderation_flag  INTEGER NOT NULL DEFAULT 0,    -- 1 if AI vision flagged
  processed_at     TEXT,
  status           TEXT NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending','processed','needs_review','quarantined','failed')),
  error_message    TEXT
);
CREATE INDEX idx_files_status ON files(status);
CREATE INDEX idx_files_type   ON files(file_type);

-- ── Links (file ↔ entry) ─────────────────────────────────────────────────────
CREATE TABLE links (
  id            INTEGER PRIMARY KEY,
  entry_id      INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
  file_id       INTEGER NOT NULL REFERENCES files(id)   ON DELETE CASCADE,
  confidence    REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  source        TEXT NOT NULL CHECK (source IN ('auto','manual')),
  reason        TEXT,
  needs_review  INTEGER NOT NULL DEFAULT 0,
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  confirmed_at  TEXT,
  confirmed_by  TEXT,
  UNIQUE (entry_id, file_id)
);
CREATE INDEX idx_links_entry  ON links(entry_id, confidence DESC);
CREATE INDEX idx_links_review ON links(needs_review) WHERE needs_review = 1;

-- ── Related entries (cross-links) ────────────────────────────────────────────
CREATE TABLE related_entries (
  entry_id          INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
  related_entry_id  INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
  relationship_type TEXT NOT NULL CHECK (relationship_type IN
                    ('parent','child','references','fulfils_prophecy','fulfilled_by')),
  PRIMARY KEY (entry_id, related_entry_id, relationship_type)
);

-- ── Bible verses (public-domain text store) ──────────────────────────────────
CREATE TABLE bible_verses (
  translation TEXT NOT NULL CHECK (translation IN ('kjv','esv','af1933')),
  book        TEXT NOT NULL,
  chapter     INTEGER NOT NULL,
  verse       INTEGER NOT NULL,
  text        TEXT NOT NULL,
  PRIMARY KEY (translation, book, chapter, verse)
);

-- ── Failed imports (retry / inspection) ──────────────────────────────────────
CREATE TABLE failed_imports (
  id             INTEGER PRIMARY KEY,
  nextcloud_path TEXT NOT NULL,
  error_message  TEXT NOT NULL,
  attempted_at   TEXT NOT NULL DEFAULT (datetime('now')),
  retry_count    INTEGER NOT NULL DEFAULT 0
);

-- ── Anthropic usage (daily budget guard) ─────────────────────────────────────
CREATE TABLE usage (
  id                  INTEGER PRIMARY KEY,
  day                 TEXT NOT NULL UNIQUE,       -- 'YYYY-MM-DD' UTC
  haiku_calls         INTEGER NOT NULL DEFAULT 0,
  haiku_input_tokens  INTEGER NOT NULL DEFAULT 0,
  haiku_output_tokens INTEGER NOT NULL DEFAULT 0,
  haiku_cost_usd      REAL    NOT NULL DEFAULT 0
);
