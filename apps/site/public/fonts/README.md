# Self-hosted fonts

Strict CSP (`font-src 'self'`) forbids loading Google Fonts at runtime,
so we host the woff2 files ourselves. This directory is intentionally
empty in the repo; production builds drop the actual font files in
during the image build step.

Required files (referenced by `src/styles/global.css`):

- `Lora-Variable.woff2`        — Lora upright, weights 400–700
- `Lora-Italic-Variable.woff2` — Lora italic, weights 400–700
- `Inter-Variable.woff2`       — Inter upright, weights 400–700

Sources (both SIL Open Font License 1.1):

- Lora:  https://github.com/cyrealtype/Lora-Cyrillic/tree/master/fonts/variable
- Inter: https://github.com/rsms/inter/releases (use `Inter-Variable.woff2`)

Admin route additionally needs:

- `JetBrainsMono-Variable.woff2` — when the admin UI ships in Phase 2

When you drop new font files here:

1. Update the integrity reference in this README.
2. Recompute the build's font cache key.
3. Smoke-test the page renders Lora (serif headings) and Inter (UI chrome).
