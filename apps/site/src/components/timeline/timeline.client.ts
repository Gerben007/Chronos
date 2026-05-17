/**
 * Chronos — timeline canvas client.
 *
 * Mounts vis-timeline against a server-rendered config blob. Keeps the
 * BC/AD date-helper boundary by reading integer years and constructing
 * Date objects only through yearToTimelineDate().
 *
 * URL state:
 *   ?from=YYYY        timeline window start (signed year)
 *   ?to=YYYY          timeline window end
 *   ?lanes=a,b,c      visible lane slugs (default = config.defaultLanes)
 */

import { Timeline, type TimelineOptions, type DataItem, type DataGroup } from 'vis-timeline';
import { DataSet } from 'vis-data';
import { yearToTimelineDate, timelineDateToYear, formatYear } from '../../lib/dates';
import type { Lang } from '../../lib/types';

import 'vis-timeline/styles/vis-timeline-graph2d.css';

export interface TimelineLane {
  slug: string;
  label: string;
  colour: string;
  colour_soft: string;
  default_visible: boolean;
  base_layer: boolean;
}

export interface TimelineEntry {
  slug: string;
  lane_slug: string;
  type: 'person' | 'event' | 'period' | 'prophecy';
  start_year: number;
  end_year?: number;
  importance: number;
  title: string;
  display_dates: string;
}

export interface TimelineEra {
  slug: string;
  label: string;
  start_year: number;
  end_year: number;
}

export interface TimelineConfig {
  lang: Lang;
  lanes: TimelineLane[];
  entries: TimelineEntry[];
  eras: TimelineEra[];
  defaultFrom: number;
  defaultTo: number;
  minYear: number;
  maxYear: number;
}

const URL_PARAMS = { from: 'from', to: 'to', lanes: 'lanes' } as const;

export function mountTimeline(host: HTMLElement, config: TimelineConfig): Timeline {
  const url = new URL(location.href);
  const initialFrom = parseInt(url.searchParams.get(URL_PARAMS.from) ?? '', 10);
  const initialTo = parseInt(url.searchParams.get(URL_PARAMS.to) ?? '', 10);
  const initialLanes = (url.searchParams.get(URL_PARAMS.lanes) ?? '').split(',').filter(Boolean);

  const visibleLanes = new Set<string>(
    initialLanes.length ? initialLanes : config.lanes.filter((l) => l.default_visible).map((l) => l.slug),
  );
  // Base layers are always visible.
  for (const l of config.lanes) if (l.base_layer) visibleLanes.add(l.slug);

  const groups = new DataSet<DataGroup>(
    config.lanes
      .filter((l) => visibleLanes.has(l.slug))
      .map((l) => ({
        id: l.slug,
        content: l.label,
        className: `lane lane-${l.slug}`,
      })),
  );

  const items = new DataSet<DataItem>(
    config.entries
      .filter((e) => visibleLanes.has(e.lane_slug))
      .map((e) => buildItem(e, config.lanes)),
  );

  const fromYear = Number.isFinite(initialFrom) && initialFrom !== 0 ? initialFrom : config.defaultFrom;
  const toYear = Number.isFinite(initialTo) && initialTo !== 0 ? initialTo : config.defaultTo;

  const options: TimelineOptions = {
    start: yearToTimelineDate(fromYear),
    end: yearToTimelineDate(toYear),
    min: yearToTimelineDate(config.minYear),
    max: yearToTimelineDate(config.maxYear),
    stack: true,
    stackSubgroups: true,
    zoomMin: 1000 * 60 * 60 * 24 * 365 * 50,        // 50 years
    zoomMax: 1000 * 60 * 60 * 24 * 365 * 9000,      // 9000 years
    orientation: { axis: 'top', item: 'top' },
    showCurrentTime: false,
    margin: { item: { horizontal: 4, vertical: 6 } },
    horizontalScroll: true,
    zoomKey: 'ctrlKey',
    selectable: true,
    multiselect: false,
    tooltip: { followMouse: true, overflowMethod: 'flip' },
    cluster: {
      titleTemplate: '+{count}',
      maxItems: 3,
      clusterCriteria: (a, b) =>
        // Cluster items only within the same lane.
        String((a as DataItem).group) === String((b as DataItem).group),
    },
    format: {
      minorLabels: { year: 'YYYY', month: 'MMM YYYY' },
      majorLabels: { year: '', month: 'YYYY' },
    },
  };

  const timeline = new Timeline(host, items, groups, options);

  // ── Custom BC/AD axis labels via MutationObserver ──────────────────────
  // vis-timeline emits raw moment-formatted years like "-2000" / "0050".
  // We post-process the rendered axis-text nodes into "2000 BC" / "AD 50".
  rewireAxisLabels(host, config.lang);

  // ── Click → navigate to entry ──────────────────────────────────────────
  timeline.on('click', (props: { item?: string | number }) => {
    if (props.item == null) return;
    const slug = String(props.item);
    location.assign(`/${config.lang}/entry/${slug}`);
  });

  // ── Rangechange → URL state + label density ───────────────────────────
  let rangeTimer = 0;
  function applyDensity(start: Date, end: Date) {
    const span = timelineDateToYear(end) - timelineDateToYear(start);
    // Threshold ladder: tighter zoom → more labels visible.
    //   < 200 yrs: importance ≥ 1  (everything)
    //   200–800:   importance ≥ 2
    //   800–2000:  importance ≥ 3
    //   > 2000:    importance ≥ 4  (only the headlines)
    const threshold =
      span < 200 ? 1 : span < 800 ? 2 : span < 2000 ? 3 : 4;
    host.dataset.densityThreshold = String(threshold);
    host.classList.remove('density-1', 'density-2', 'density-3', 'density-4');
    host.classList.add(`density-${threshold}`);
  }
  applyDensity(yearToTimelineDate(fromYear), yearToTimelineDate(toYear));
  timeline.on('rangechange', (props: { start: Date; end: Date }) => {
    applyDensity(props.start, props.end);
    window.clearTimeout(rangeTimer);
    rangeTimer = window.setTimeout(() => {
      const url = new URL(location.href);
      url.searchParams.set(URL_PARAMS.from, String(timelineDateToYear(props.start)));
      url.searchParams.set(URL_PARAMS.to, String(timelineDateToYear(props.end)));
      history.replaceState(null, '', url.toString());
    }, 200);
  });

  // ── Lane toggles ───────────────────────────────────────────────────────
  host.closest('.ch-timeline-shell')
    ?.querySelectorAll<HTMLInputElement>('[data-lane-toggle]')
    .forEach((cb) => {
      cb.checked = visibleLanes.has(cb.value);
      cb.disabled = config.lanes.find((l) => l.slug === cb.value)?.base_layer ?? false;
      cb.addEventListener('change', () => {
        if (cb.checked) visibleLanes.add(cb.value);
        else visibleLanes.delete(cb.value);
        rebuild(timeline, items, groups, config, visibleLanes);
        const url = new URL(location.href);
        url.searchParams.set(URL_PARAMS.lanes, [...visibleLanes].join(','));
        history.replaceState(null, '', url.toString());
      });
    });

  // ── Era jump buttons ───────────────────────────────────────────────────
  host.closest('.ch-timeline-shell')?.querySelectorAll<HTMLButtonElement>('[data-era-jump]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const fromAttr = btn.dataset.eraFrom;
      const toAttr = btn.dataset.eraTo;
      if (!fromAttr || !toAttr) return;
      const start = yearToTimelineDate(parseInt(fromAttr, 10));
      const end = yearToTimelineDate(parseInt(toAttr, 10));
      timeline.setWindow(start, end, { animation: true });
    });
  });

  // ── Zoom buttons (vis-timeline-native) ─────────────────────────────────
  host.closest('.ch-timeline-shell')?.querySelectorAll<HTMLButtonElement>('[data-zoom]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const action = btn.dataset.zoom;
      if (action === 'in')   timeline.zoomIn(0.5);
      if (action === 'out')  timeline.zoomOut(0.5);
      if (action === 'fit')  timeline.fit({ animation: true });
    });
  });

  return timeline;
}

function buildItem(e: TimelineEntry, lanes: TimelineLane[]): DataItem {
  const lane = lanes.find((l) => l.slug === e.lane_slug);
  const colour = lane?.colour ?? '#1F2A44';
  const isRange = e.end_year !== undefined && e.end_year !== e.start_year;
  const start = yearToTimelineDate(e.start_year);
  const end = isRange ? yearToTimelineDate(e.end_year!) : undefined;
  const labelHtml = `<span class="ch-label">${escapeHtml(e.title)}</span>` +
    `<span class="ch-date">${escapeHtml(e.display_dates)}</span>`;

  return {
    id: e.slug,
    group: e.lane_slug,
    start,
    end,
    type: isRange ? 'range' : 'point',
    content: labelHtml,
    className: [
      'ch-item',
      `ch-type-${e.type}`,
      `ch-importance-${e.importance}`,
      isRange ? 'ch-period' : 'ch-point',
    ].join(' '),
    style: isRange
      ? `background:${colour}22;border-color:${colour};color:${colour};`
      : `--dot:${colour};`,
    title: `${e.title} · ${e.display_dates}`,
  };
}

function rebuild(
  timeline: Timeline,
  items: DataSet<DataItem>,
  groups: DataSet<DataGroup>,
  config: TimelineConfig,
  visibleLanes: Set<string>,
) {
  const nextGroups = config.lanes
    .filter((l) => visibleLanes.has(l.slug))
    .map((l) => ({ id: l.slug, content: l.label, className: `lane lane-${l.slug}` }));
  groups.clear();
  groups.add(nextGroups);

  const nextItems = config.entries
    .filter((e) => visibleLanes.has(e.lane_slug))
    .map((e) => buildItem(e, config.lanes));
  items.clear();
  items.add(nextItems);

  timeline.redraw();
}

function rewireAxisLabels(host: HTMLElement, lang: Lang) {
  const yearRe = /^-?\d{1,5}$/;
  const transform = (el: HTMLElement) => {
    const txt = el.textContent?.trim() ?? '';
    if (!yearRe.test(txt)) return;
    const y = parseInt(txt, 10);
    if (!Number.isFinite(y) || y === 0) return;
    el.textContent = formatYear(y, lang);
  };
  const scan = () => host.querySelectorAll<HTMLElement>('.vis-text').forEach(transform);

  const obs = new MutationObserver(scan);
  obs.observe(host, { childList: true, subtree: true, characterData: true });
  scan();
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!,
  );
}
