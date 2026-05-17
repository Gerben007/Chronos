import type { Lang } from './types';

/**
 * Date-handling boundary.
 *
 * vis-timeline (and the browser's Date object generally) does not love BC
 * dates. All conversions between our integer year domain and JS Date objects
 * MUST go through these helpers — no `new Date(year, ...)` elsewhere in
 * the codebase.
 *
 * Convention: signed integers; BC is negative; there is no year 0;
 * AD 1 is 1, BC 1 is -1.
 */

export function yearToTimelineDate(year: number, month = 0, day = 1): Date {
  // setUTCFullYear handles years < 100 correctly, unlike the Date constructor
  // which silently maps "year 0050" to 1950. This is the single safe path.
  const d = new Date(0);
  d.setUTCFullYear(year, month, day);
  d.setUTCHours(0, 0, 0, 0);
  return d;
}

export function timelineDateToYear(d: Date): number {
  return d.getUTCFullYear();
}

export function formatYear(y: number, lang: Lang): string {
  if (lang === 'af') return y < 0 ? `${-y} v.C.` : `n.C. ${y}`;
  return y < 0 ? `${-y} BC` : `AD ${y}`;
}

export function formatYearRange(start: number, end: number | undefined, lang: Lang): string {
  if (end === undefined) return formatYear(start, lang);
  // Range with same era: drop the era suffix from the first year.
  const sameEra = (start < 0) === (end < 0);
  if (sameEra) {
    const startBare = Math.abs(start).toString();
    return `${startBare}–${formatYear(end, lang)}`;
  }
  return `${formatYear(start, lang)} – ${formatYear(end, lang)}`;
}
