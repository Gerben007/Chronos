/**
 * Validates db/seed/*.json against the Zod schemas in src/lib/types.ts
 * and smoke-tests rehype-sanitize against hostile Markdown inputs.
 *
 * Exits non-zero on any failure — wired into CI (`npm run validate-schema`).
 */

import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkRehype from 'remark-rehype';
import rehypeSanitize from 'rehype-sanitize';
import rehypeStringify from 'rehype-stringify';
import { EntriesFile, LanesFile } from '../src/lib/types';

const here = dirname(fileURLToPath(import.meta.url));
const seedDir = resolve(here, '../../../db/seed');

let failures = 0;
function fail(label: string, err: unknown): void {
  failures += 1;
  console.error(`✗ ${label}`);
  console.error(err);
}
function ok(label: string): void {
  console.log(`✓ ${label}`);
}

// ── 1. Seed JSON ────────────────────────────────────────────────────────────
try {
  const lanes = JSON.parse(readFileSync(resolve(seedDir, 'lanes.json'), 'utf-8'));
  LanesFile.parse(lanes);
  ok(`db/seed/lanes.json — ${lanes.length} lanes`);
} catch (err) {
  fail('db/seed/lanes.json', err);
}

try {
  const entries = JSON.parse(readFileSync(resolve(seedDir, 'entries.json'), 'utf-8'));
  EntriesFile.parse(entries);
  ok(`db/seed/entries.json — ${entries.length} entries`);
} catch (err) {
  fail('db/seed/entries.json', err);
}

// ── 2. rehype-sanitize against hostile inputs ──────────────────────────────
const HOSTILE: Array<{ name: string; md: string; mustNotContain: string[] }> = [
  {
    name: 'raw <script> tag',
    md: '# heading\n\n<script>alert(1)</script>\n\nplain text',
    mustNotContain: ['<script', 'alert('],
  },
  {
    name: 'inline event handler',
    md: '[click](javascript:alert(1))',
    mustNotContain: ['javascript:'],
  },
  {
    name: 'iframe injection',
    md: '<iframe src="https://evil.example/"></iframe>',
    mustNotContain: ['<iframe'],
  },
  {
    name: 'img onerror',
    md: '<img src=x onerror="alert(1)">',
    mustNotContain: ['onerror'],
  },
  {
    name: 'data: URI',
    md: '[bait](data:text/html,<script>alert(1)</script>)',
    mustNotContain: ['data:text/html'],
  },
];

const processor = unified()
  .use(remarkParse)
  .use(remarkRehype, { allowDangerousHtml: true })
  .use(rehypeSanitize)
  .use(rehypeStringify);

for (const tc of HOSTILE) {
  try {
    const html = String(processor.processSync(tc.md));
    const bad = tc.mustNotContain.filter((s) => html.toLowerCase().includes(s.toLowerCase()));
    if (bad.length) {
      throw new Error(`sanitized output still contains: ${bad.join(', ')}\n--- output:\n${html}`);
    }
    ok(`rehype-sanitize blocks: ${tc.name}`);
  } catch (err) {
    fail(`rehype-sanitize: ${tc.name}`, err);
  }
}

if (failures > 0) {
  console.error(`\n${failures} validation failure(s).`);
  process.exit(1);
}
console.log(`\nall checks passed.`);
