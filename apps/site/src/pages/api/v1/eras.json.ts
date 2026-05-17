// Public read-only API: list of named eras for timeline-jump buttons.
// Bilingual labels inlined; no dependency on user locale at request time.
import type { APIRoute } from 'astro';

const ERAS = [
  { slug: 'patriarchs',  label_en: 'Patriarchs',  label_af: 'Aartsvaders',     start_year: -2200, end_year: -1500 },
  { slug: 'kingdoms',    label_en: 'Kingdoms',    label_af: 'Konings',         start_year: -1100, end_year: -500 },
  { slug: 'christ',      label_en: 'Christ',      label_af: 'Christus',        start_year: -50,   end_year: 100 },
  { slug: 'reformation', label_en: 'Reformation', label_af: 'Hervorming',      start_year: 1400,  end_year: 1700 },
  { slug: 'all',         label_en: 'All history', label_af: 'Hele geskiedenis', start_year: -4100, end_year: 600 },
];

export const GET: APIRoute = () => {
  return new Response(JSON.stringify(ERAS), {
    status: 200,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'public, max-age=300',
    },
  });
};
