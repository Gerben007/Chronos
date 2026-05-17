// Public read-only API: compact list of entries (no wiki body).
// Designed for clients that render the timeline themselves and want a
// lightweight payload. Use /api/v1/entries/{slug}.json for full content.
import type { APIRoute } from 'astro';
import { loadEntries } from '../../../lib/data';

export const GET: APIRoute = () => {
  const compact = loadEntries().map((e) => ({
    slug: e.slug,
    type: e.type,
    lane_slug: e.lane_slug,
    start_year: e.start_year,
    end_year: e.end_year ?? null,
    importance: e.importance,
    scripture_refs: e.scripture_refs ?? [],
    translations: Object.fromEntries(
      Object.entries(e.translations).map(([lang, t]) => [
        lang, { title: t.title, display_dates: t.display_dates, summary: t.summary },
      ]),
    ),
  }));
  return new Response(JSON.stringify(compact), {
    status: 200,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'public, max-age=300',
    },
  });
};
