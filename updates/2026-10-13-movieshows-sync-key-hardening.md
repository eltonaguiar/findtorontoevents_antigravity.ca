# 2026-10-13 — Remove credential literals from MOVIESHOWS sync gate + DB config

## What was broken

Three committed files compared against a literal credential instead of an
environment variable (values omitted from this doc and from the public page):

1. `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/fetch_new_content.php` — hardcoded
   sync-gate key literal in the auth comparison (and in the usage docblock).
2. `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/api/add-movies-batch.php` — same
   literal.
3. `scripts/api_integrations.py` — default DB password literal in the
   `os.getenv` fallback.

Found while building the public integrations page. Operator decision: remove
the hardcoding now; rotate the credential values later.

## What changed

### PHP sync gates (both files)

Auth now resolves the expected key at runtime, in this order:

1. `MS2_SYNC_KEY` environment variable (server/vhost config), else
2. `sync_key.local` — a single-line sidecar file next to the scripts
   (`MOVIESHOWS3/sync_key.local`; for `api/add-movies-batch.php` it resolves
   one directory up). The file is **gitignored** and uploaded by
   `tools/deploy_movieshows3.py` from the `MS2_SYNC_KEY` GitHub secret.

**Fails closed**: if neither is configured, every request gets a 403 with an
explicit "Sync key not configured on server" JSON error, so a misdeployed
server rejects everything instead of accepting anything. Still PHP 5.x-safe
constructs only (`getenv`, `is_readable`, `file_get_contents`, `trim`).

### `scripts/api_integrations.py`

- `DB_PASS = os.environ.get('DB_PASS', '')` (no default literal).
- `connect_db()` raises a clear `RuntimeError` when `DB_PASS` is unset.
- Module is standalone (only self-referenced, has `__main__`), so no importer
  is affected by the fail-fast.

### Supporting changes

- `tools/deploy_movieshows3.py` — after uploading the PHP files, uploads
  `sync_key.local` from the `MS2_SYNC_KEY` env var (new `_upload_bytes`
  helper; the sidecar never exists on local disk).
- `.github/workflows/fetch-movies-v3.yml` — the deploy step now passes
  `MS2_SYNC_KEY: ${{ secrets.MS2_SYNC_KEY }}` so each scheduled deploy keeps
  the server-side gate in sync with the secret.
- `.gitignore` — added `sync_key.local`.

## Rollback plan (per operator caution about separate hosting creds)

- This change touches **only** the 50webs host (`ftps2.50webs.com`,
  `findtorontoevents.ca/MOVIESHOWS3`). The GoDaddy credentials (tdotevent.ca)
  and `deploy_to_altsite.py` / `deploy-fc-api-env-godaddy.yml` are untouched.
- If the live TMDB fetch breaks after the next scheduled deploy of these PHP
  files: `git revert` this commit and either wait for the next
  `fetch-movies-v3.yml` run (it re-uploads the previous PHP from main) or run
  `python tools/deploy_movieshows3.py` manually.
- If only the key wiring is wrong (403 "not configured"), set the
  `MS2_SYNC_KEY` value server-side (env or re-upload `sync_key.local`) — no
  code change needed.

## Verification

- `python3 -m py_compile` on both changed Python files — OK.
- `yaml.safe_load` on `fetch-movies-v3.yml` — OK.
- Repo-wide search (`rg -l 'ms2_sync_2024'`) — **zero matches**; the literal
  no longer exists anywhere in the working tree.
- Default password literal gone from `scripts/api_integrations.py`.
- Auth logic reviewed against the PHP 5.x constraint set (no `??`, no short
  arrays, `getenv` returns `false` when unset — handled explicitly).
- **Not run locally:** `php -l` / live PHP execution (no PHP binary on this
  machine). Mitigated by: fail-closed behavior, the rollback path above, and
  the fact that the scheduled workflow already reports "Authentication
  failed" loudly if the endpoint starts rejecting.

## Follow-up for operator (not done here)

- Rotate the sync key value: update the `MS2_SYNC_KEY` GitHub secret; the
  next `fetch-movies-v3.yml` run re-uploads `sync_key.local` with the new
  value. Old value stays valid until rotation (code change only removed it
  from source).
- Rotate the `DB_PASS` value used by `scripts/api_integrations.py` consumers.
