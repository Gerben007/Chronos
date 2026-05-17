import { getCollection, type CollectionEntry } from 'astro:content';
import type { Lang } from './types';

let _cache: CollectionEntry<'wiki'>[] | null = null;

async function all(): Promise<CollectionEntry<'wiki'>[]> {
  if (_cache) return _cache;
  _cache = await getCollection('wiki');
  return _cache;
}

/**
 * Wiki entry slugs are derived from filename. A file at
 * `src/content/wiki/en/abraham.md` has slug `en/abraham`; the entry
 * portion is everything after the last slash.
 */
function entrySlug(e: CollectionEntry<'wiki'>): string {
  const s = e.slug;
  const i = s.lastIndexOf('/');
  return i >= 0 ? s.slice(i + 1) : s;
}

/** Returns the wiki entry for a (slug, lang) pair, or undefined if absent. */
export async function getWiki(
  slug: string,
  lang: Lang,
): Promise<CollectionEntry<'wiki'> | undefined> {
  const entries = await all();
  return entries.find((e) => entrySlug(e) === slug && e.data.lang === lang);
}

/** Does any wiki content (in any language) exist for this entry slug? */
export async function hasWiki(slug: string): Promise<boolean> {
  const entries = await all();
  return entries.some((e) => entrySlug(e) === slug);
}
