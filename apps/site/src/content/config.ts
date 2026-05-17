// Astro content collection for wiki Markdown.
// Files live at: src/content/wiki/<lang>/<slug>.md
// Body is sanitised via rehype-sanitize (configured in astro.config.mjs);
// no raw HTML reaches the rendered page.

import { defineCollection, z } from 'astro:content';

const wiki = defineCollection({
  type: 'content',
  // `slug` is reserved by Astro for filename-derived IDs — we derive it
  // from the filename via parseSlug() in the entry page instead.
  schema: z.object({
    lang: z.enum(['en', 'af']),
    // Optional citation list — keeps source attribution close to the prose.
    sources: z.array(z.string()).optional(),
    // Translation-pipeline metadata; mirrors entry_translations columns.
    translation_status: z
      .enum(['authored', 'ai_draft', 'reviewed', 'published'])
      .default('authored'),
    source_lang: z.enum(['en', 'af']).optional(),
    reviewed_at: z.string().optional(),
    reviewed_by: z.string().optional(),
  }),
});

export const collections = { wiki };
