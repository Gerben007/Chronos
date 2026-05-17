import { z } from 'zod';

export const Lang = z.enum(['en', 'af']);
export type Lang = z.infer<typeof Lang>;

export const LANGS: readonly Lang[] = ['en', 'af'] as const;

export const Lane = z.object({
  slug: z.string().min(1),
  label_en: z.string().min(1),
  label_af: z.string().min(1).nullable(),
  colour: z.string().regex(/^#[0-9A-Fa-f]{6}$/),
  colour_soft: z.string().regex(/^#[0-9A-Fa-f]{6}$/),
  group_label: z.string().min(1),
  default_visible: z.boolean(),
  base_layer: z.boolean(),
  sort_order: z.number().int(),
});
export type Lane = z.infer<typeof Lane>;

const Translation = z.object({
  title: z.string().min(1),
  display_dates: z.string().min(1),
  summary: z.string().min(1),
  wiki_md: z.string().optional(),
});
export type Translation = z.infer<typeof Translation>;

export const Entry = z.object({
  slug: z.string().min(1),
  type: z.enum(['person', 'event', 'period', 'prophecy']),
  lane_slug: z.string().min(1),
  start_year: z.number().int(),
  end_year: z.number().int().optional(),
  importance: z.number().int().min(1).max(5),
  parent_period_slug: z.string().optional(),
  scripture_refs: z.array(z.string()).optional(),
  artwork_url: z.string().url().optional(),
  artwork_credit: z.string().optional(),
  start_year_alt: z.record(z.unknown()).optional(),
  translations: z.record(Lang, Translation),
});
export type Entry = z.infer<typeof Entry>;

export const LanesFile = z.array(Lane);
export const EntriesFile = z.array(Entry);

export const Resource = z.object({
  file_id: z.number().int(),
  title: z.string(),
  file_type: z.enum(['pdf', 'video', 'audio', 'image', 'doc']),
  public_url: z.string().url(),
  summary_en: z.string().nullable(),
  summary_af: z.string().nullable(),
  cc_cycle: z.number().int().nullable(),
  cc_week: z.number().int().nullable(),
  age_min: z.number().int().nullable(),
  age_max: z.number().int().nullable(),
  confidence: z.number(),
  needs_review: z.boolean(),
});
export type Resource = z.infer<typeof Resource>;

export const ResourcesFile = z.record(z.string(), z.array(Resource));
