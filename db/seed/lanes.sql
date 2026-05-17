-- Chronos — lane seed.
-- Colours sourced from docs/design-tokens.md (lane palette table).
-- Bible-Events and Bible-People are merged into a single `bible` lane
-- (decision from the design session — distinguished by a card prefix
-- `BIBLE · PERSON|EVENT`, not by lane).
-- Reserved lanes (church-history / science / arts / reformation) are seeded
-- with their locked colours but default_visible=0 until Phase 2/3 content arrives.

INSERT INTO lanes (slug, label_en, label_af, colour, colour_soft, group_label, default_visible, base_layer, sort_order) VALUES
  ('bible',           'Biblical history', 'Bybelse geskiedenis', '#1F2A44', '#DAD4BE', 'biblical',       1, 1, 1),
  ('egypt',           'Egypt',            'Egipte',              '#A88E3A', '#E8DCB2', 'empires',        1, 0, 2),
  ('rome',            'Rome',             'Rome',                '#8B3A1F', '#E4C8B8', 'empires',        1, 0, 3),
  ('church-history',  'Church history',   'Kerkgeskiedenis',     '#5B4A6E', '#DCD2E0', 'church-history', 0, 0, 10),
  ('science',         'Science',          'Wetenskap',           '#4F7A3E', '#DDE5CC', 'science',        0, 0, 11),
  ('arts',            'Arts',             'Kunste',              '#9A4225', '#ECD4C4', 'arts',           0, 0, 12),
  ('reformation',     'Reformation',      'Hervorming',          '#2F5A6B', '#CDD9DD', 'church-history', 0, 0, 13);
