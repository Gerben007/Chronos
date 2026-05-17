// Public read-only API: full entry by slug, with wiki Markdown and
// the latest resources list inlined.
import type { APIRoute } from 'astro';
import {
  loadEntries, getResourcesForEntry, getLaneBySlug,
} from '../../../../lib/data';
import { getWiki } from '../../../../lib/wiki';

export function getStaticPaths() {
  return loadEntries().map((entry) => ({ params: { slug: entry.slug }, props: { entry } }));
}

export const GET: APIRoute = async ({ props }) => {
  const entry = (props as { entry: ReturnType<typeof loadEntries>[number] }).entry;
  const lane = getLaneBySlug(entry.lane_slug);
  const wiki_en = (await getWiki(entry.slug, 'en'))?.body ?? null;
  const wiki_af = (await getWiki(entry.slug, 'af'))?.body ?? null;
  return new Response(JSON.stringify({
    ...entry,
    lane: lane ? { slug: lane.slug, label_en: lane.label_en, label_af: lane.label_af } : null,
    wiki: { en: wiki_en, af: wiki_af },
    resources: getResourcesForEntry(entry.slug),
  }), {
    status: 200,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'public, max-age=300',
    },
  });
};
