// Public read-only API: just the resources list for one entry.
// Mirrors /data/resources.json[slug] but is publicly versioned and stable.
import type { APIRoute } from 'astro';
import { loadEntries, getResourcesForEntry } from '../../../../../lib/data';

export function getStaticPaths() {
  return loadEntries().map((entry) => ({ params: { slug: entry.slug } }));
}

export const GET: APIRoute = ({ params }) => {
  const slug = params.slug as string;
  return new Response(JSON.stringify(getResourcesForEntry(slug)), {
    status: 200,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'public, max-age=300',
    },
  });
};
