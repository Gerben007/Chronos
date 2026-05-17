import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { type Entry, EntriesFile, type Lane, LanesFile } from './types';

const here = dirname(fileURLToPath(import.meta.url));
const seedDir = resolve(here, '../../../../db/seed');

let _lanes: Lane[] | null = null;
let _entries: Entry[] | null = null;

export function loadLanes(): Lane[] {
  if (_lanes) return _lanes;
  const raw = JSON.parse(readFileSync(resolve(seedDir, 'lanes.json'), 'utf-8'));
  _lanes = LanesFile.parse(raw).sort((a, b) => a.sort_order - b.sort_order);
  return _lanes;
}

export function loadEntries(): Entry[] {
  if (_entries) return _entries;
  const raw = JSON.parse(readFileSync(resolve(seedDir, 'entries.json'), 'utf-8'));
  _entries = EntriesFile.parse(raw).sort((a, b) => a.start_year - b.start_year);
  return _entries;
}

export function getLaneBySlug(slug: string): Lane | undefined {
  return loadLanes().find((l) => l.slug === slug);
}

export function getEntryBySlug(slug: string): Entry | undefined {
  return loadEntries().find((e) => e.slug === slug);
}

export function getEntriesByLane(laneSlug: string): Entry[] {
  return loadEntries().filter((e) => e.lane_slug === laneSlug);
}
