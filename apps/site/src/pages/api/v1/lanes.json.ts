// Public read-only API: list of timeline lanes.
// Static — written once at build time. Versioning lives in the path (/v1/).
import type { APIRoute } from 'astro';
import { loadLanes } from '../../../lib/data';

export const GET: APIRoute = () => {
  return new Response(JSON.stringify(loadLanes()), {
    status: 200,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'public, max-age=300',
    },
  });
};
