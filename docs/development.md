# Development setup

This guide gets a clean machine to a running Chronos dev environment.
Primary target: VS Code (desktop) + Claude Code extension on a laptop;
the homelab runs the same compose file unchanged in production.

## Prerequisites

| Tool          | Version            | Install                                   |
|---------------|--------------------|-------------------------------------------|
| Node          | 20.x LTS           | <https://nodejs.org/> or `nvm install 20` |
| Python        | 3.11.x             | <https://www.python.org/downloads/>       |
| SQLite CLI    | ≥ 3.40             | usually bundled; `sqlite3 --version`      |
| Docker Desktop| current            | <https://www.docker.com/products/docker-desktop/> |
| Git           | ≥ 2.40             | <https://git-scm.com/>                    |
| VS Code       | current            | <https://code.visualstudio.com/>          |
| Claude Code   | latest             | `npm install -g @anthropic-ai/claude-code` + VS Code extension |

GPG required only when working on backup tooling.

## First run

```bash
git clone https://github.com/gerben007/chronos.git
cd chronos
git checkout claude/new-session-5fOED      # current dev branch
./scripts/dev.sh                            # bootstraps .env, db, deps
code .                                      # opens VS Code
```

`scripts/dev.sh`:
- copies `.env.example` → `.env` if missing (you fill in secrets),
- creates `db/chronos.db` with the migration + lane seed,
- installs `apps/site` npm deps,
- creates `apps/ingest/.venv` and installs Python deps with `[dev]`.

## Day-to-day

```bash
# Astro dev server (port 4321)
cd apps/site && npm run dev

# Ingest virtualenv
cd apps/ingest && . .venv/bin/activate

# Typecheck site
cd apps/site && npm run typecheck

# Lint + type ingest
cd apps/ingest && ruff check . && mypy chronos_ingest
```

## Environment

Production env vars live in `.env` on the homelab (chmod 600).
For local dev, only a handful are needed:

| Var                  | Local value                        |
|----------------------|------------------------------------|
| `SQLITE_PATH`        | `./db/chronos.db`                  |
| `DEFAULT_LANG`       | `en`                               |
| `ENGLISH_BIBLE`      | `kjv`                              |
| `ANTHROPIC_API_KEY`  | a low-budget personal key          |
| `ANTHROPIC_MODEL`    | `claude-haiku-4-5-20251001`        |
| `DAILY_HAIKU_BUDGET_USD` | `0.20` for safety while iterating |

Everything else can stay blank during Phase 1; ingest skips paths whose
required env vars are missing.

## Working with the Claude Code extension

Once VS Code is open with the repo:

1. Open Claude Code (Cmd/Ctrl+Esc by default).
2. Suggested first message for a fresh session:

   > Read `PLAN.md`, `docs/design-brief.md`, and `docs/design-tokens.md`.
   > We're on Phase 1 of Chronos. Begin implementing per the locked
   > tokens — start with `apps/site` layout + components. Stay on
   > branch `claude/new-session-5fOED`.

3. Claude will follow the plan and the locked tokens. Push back on it
   like a colleague — the brief explicitly invites pushback.

Commit cadence: small commits, descriptive messages, push to the dev
branch when a unit of work is coherent. Production deploy is `git pull
&& docker compose up -d` on the homelab.

## Database

```bash
# Open the local DB
sqlite3 db/chronos.db

# Re-seed lanes (idempotent only with DELETE first)
sqlite3 db/chronos.db < db/seed/lanes.sql

# Wipe and rebuild
rm db/chronos.db && ./scripts/dev.sh
```

The web container is read-only against the DB; only the ingest container
writes. Local dev follows the same convention — avoid hand-editing data
the ingest service is responsible for.

## Compose (full local stack)

```bash
docker compose up -d --build
docker compose logs -f ingest
docker compose down
```

Requires ClamAV image pull on first run (~250 MB) and an initial
signature database download (~120 MB) — give it 2 minutes before the
`clamav` healthcheck goes green.

## Troubleshooting

- **`sqlite3` says `database is locked`** — another process holds the DB.
  WAL mode allows readers + one writer; only the ingest service writes.
- **`npm audit` fails CI** — bump the offending package; if no upgrade,
  document in `docs/security.md` with rationale and a re-check date.
- **Astro build slow** — fast-path is your friend; full builds happen only
  on entry/wiki/code changes (see `docs/content-pipeline.md`).
