import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import rehypeSanitize from 'rehype-sanitize';

// Chronos site config.
// Bilingual under /[lang]/; static output; strict markdown sanitisation.
// Runtime CSP enforced by nginx (see infra/nginx/nginx.conf) — Astro
// emits hashed assets and bears no inline scripts so 'script-src self' holds.

export default defineConfig({
  site: process.env.SITE_BASE_URL || 'https://chronos.stratusfinance.co.za',
  output: 'static',
  trailingSlash: 'ignore',
  build: {
    inlineStylesheets: 'auto',
    format: 'directory',
  },
  integrations: [tailwind({ applyBaseStyles: false })],
  markdown: {
    rehypePlugins: [[rehypeSanitize, { /* default-safe schema; no raw HTML */ }]],
    shikiConfig: { theme: 'github-light' },
  },
  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'af'],
    routing: { prefixDefaultLocale: true },
  },
  vite: {
    server: { host: '127.0.0.1' },
  },
});
