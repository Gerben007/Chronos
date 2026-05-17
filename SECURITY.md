# Security policy

Chronos is a self-hosted site serving learning resources to children. Security
is a first-class concern. See `docs/security.md` for the full threat model,
controls, and operational runbooks.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security concerns.

Email: `security@stratusfinance.co.za`
GPG: *(fingerprint pending — added before first public deployment)*

Include:

- A description of the issue and its potential impact.
- Steps to reproduce or a proof-of-concept.
- Your name and affiliation if you'd like credit.

We aim to acknowledge within 72 hours and to patch high/critical issues
within 14 days.

## Scope

In scope:

- The public site at `chronos.stratusfinance.co.za`.
- The admin review API (behind Cloudflare Access).
- The Python ingest pipeline.
- This repository's CI workflows.

Out of scope:

- Cloudflare itself (report to Cloudflare's program).
- Nextcloud itself (report upstream).
- Third-party content linked from entries (we link, we do not host).
- Denial-of-service against the homelab.

## Safe harbour

Good-faith research that follows this policy will not result in legal
action. Please give us a reasonable window to fix before public disclosure.

## Hardening summary

- No public authentication anywhere (no credential abuse surface).
- Admin path gated by Cloudflare Access with email OTP; JWT verified in-app.
- All uploaded files scanned by ClamAV; PDFs JS-stripped; images re-encoded.
- Strict CSP; `rehype-sanitize` on all Markdown; no raw HTML in wiki content.
- Containers run as UID 1000, read-only root filesystem, all caps dropped,
  `no-new-privileges`, pinned by SHA-256 digest.
- Nightly SQLite backup, gpg-encrypted, offsite weekly, quarterly restore drill.
- Dependabot + `npm audit` + `pip-audit` fail CI on high/critical.

Full detail in `docs/security.md`.
