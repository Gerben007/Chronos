# Security — threat model & controls

Canonical reference is `PLAN.md` §14. This file expands the operational
runbooks. Update whenever a control changes.

## Trust boundaries

| Boundary                           | Who / what crosses                    | Control                                     |
|------------------------------------|---------------------------------------|---------------------------------------------|
| Internet ↔ Cloudflare edge         | Anyone                                | CF WAF + TLS + caching                      |
| Cloudflare ↔ homelab               | CF tunnel only                        | `cloudflared` token; no inbound ports       |
| Public ↔ admin path                | Allowlisted emails only               | Cloudflare Access OTP + in-app JWT verify   |
| Mothers' phones ↔ Nextcloud        | Authenticated upload                  | Nextcloud auth; app passwords; quotas       |
| Nextcloud ↔ ingest container       | WebDAV poll, OCS API                  | Read-only app password; rotated quarterly   |
| Ingest ↔ Anthropic                 | Outbound HTTPS                        | API key (server-side only); rate + budget   |
| Web container ↔ DB                 | Read-only                             | Read-only volume mount                      |
| Ingest container ↔ DB              | Sole writer                           | Read-write volume; parameterised queries    |

## File pipeline (highest-risk surface)

1. **Discover** — WebDAV list `_inbox/`.
2. **Download** — to `ingest-tmp` writable volume only.
3. **Scan** — `clamd` on Unix socket. Infected → `_quarantine/`, DB
   `status='quarantined'`, never shared.
4. **Sanitise** — PDFs through `pikepdf` (strip `/JS`, `/JavaScript`,
   `/OpenAction`, external `/URI`). Images re-encoded via Pillow (strips
   EXIF inc. GPS, drops non-pixel chunks).
5. **Extract** — text (pdfplumber, ~3000 chars), thumbnail, ffprobe.
6. **Moderate** — AI vision call carries a moderation directive. Flagged →
   `moderation_flag=1`, surfaces in admin quarantine even if ClamAV cleared.
7. **Classify** — Haiku with prompt-cached entry list. Confidence
   thresholds: ≥0.7 auto, 0.5–0.7 review, <0.5 discard.
8. **Share** — Nextcloud OCS `permissions=1` (read-only, no upload, no
   re-share). Folder shares disabled.
9. **Publish** — fast-path rewrite of `dist/data/entries/{slug}.json`.

## Headers (web container)

Defined in `infra/nginx/nginx.conf` (production) and mirrored as a
`<meta http-equiv="Content-Security-Policy">` in BaseLayout for dev
parity. CSP is `default-src 'self'`, `script-src 'self'` (no inline;
Astro emits hashed external modules; our public/js/ scripts are
referenced with `<script is:inline src="...">` so they stay external).

CI enforces both invariants:
- `scripts/check-no-inline-scripts.mjs` fails the build if any HTML
  file in `dist/` contains an inline `<script>` body.
- The workflow greps every built HTML for the CSP meta tag.

Updates require:
- update `infra/nginx/nginx.conf` AND `BaseLayout.astro` (keep in sync),
- redeploy `web`,
- spot-check via <https://securityheaders.com>.

## Secrets

| Secret                       | Storage         | Rotation cadence | Rotation runbook |
|------------------------------|-----------------|------------------|------------------|
| `ANTHROPIC_API_KEY`          | `.env` (600)    | quarterly        | TBD              |
| `NEXTCLOUD_APP_PASSWORD`     | `.env` (600)    | quarterly        | TBD              |
| `CLOUDFLARE_TUNNEL_TOKEN`    | `.env` (600)    | quarterly        | TBD              |
| `WEBHOOK_HMAC_SECRET`        | `.env` (600)    | annually         | TBD              |
| `BACKUP_GPG_RECIPIENT` key   | offline media   | (private key)    | TBD              |

Calendar reminders required.

## Backup & restore

- Nightly `scripts/backup-db.sh` runs on the homelab via cron.
- Encrypted to `BACKUP_GPG_RECIPIENT`; plaintext shredded.
- Local 30-day retention; offsite weekly rsync.
- Quarterly `scripts/restore-drill.sh` verifies a real backup decrypts
  and passes `PRAGMA integrity_check;`.

## Dependency hygiene

- Dependabot weekly PRs (npm, pip, Actions, Docker).
- CI: `npm audit --audit-level=high`, `pip-audit --strict`.
- Docker images pinned by SHA-256 digest; no `latest`; Watchtower disabled.

## Disclosure

See `SECURITY.md` at repo root.
