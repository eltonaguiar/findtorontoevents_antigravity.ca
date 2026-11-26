# `movies.php` verdict + MOVIESHOWS2 deploy workflow (2026-11-26)

## The question

The drift audit found `movieshows2/api/movies.php` live at **19,500 B** against
**7,950 B** in the repo. Which one is authoritative?

## Verdict: the repository copy

| Evidence | Live | Repo |
|---|---|---|
| PHP 5.2 constructs | **60 findings** (short arrays, `??`, others) | 0 |
| Can it run on 50webs (5.2.17)? | **No** — short array syntax is a *parse* error, so the file dies before executing | Yes |
| Header intent | none | `Movies API - supports actions needed by db-connector.js`, `Compatible with PHP 5.2+` |
| DB credentials | hardcoded plaintext in `db-config.php` | `getenv()` / private `require` |
| Actions implemented | `list, random, search, stats, add, get, sync` | `list, random, search, stats, top_by_genre` |

The live file is the **legacy monolith**, not a newer version: it is bigger because it
predates the 5.2 rewrite, and it cannot parse on the host it is deployed to. That also
explains the 404/301 seen on `/movieshows2/` — nothing there can execute.

Accuracy on the trade-off: the repo rewrite does **not** implement `add`, `get` or
`sync`, while the legacy file did. Those three are lost either way, because the legacy
file cannot run at all. If a caller needs them, they should be re-added to the repo
version deliberately — not by shipping a file that cannot parse.

## Deploy workflow

`.github/workflows/deploy-movieshows2.yml` (manual dispatch) publishes **two** files to
`findtorontoevents.ca/movieshows2/api`:

- `api/movies.php` — the 5.2 rewrite
- `api/get-movies.php` — the OPTIONS preflight fix that had never been deployed

It skips uploads whose sha256 already matches, so re-running is a no-op.

Deliberately excluded, and why:

| File | Reason |
|---|---|
| ~~`api/db-config.php`~~ | **Reversed after live evidence.** The first deploy left both endpoints answering `{"success":false,"error":"Database connection failed"}`. A throwaway probe showed the *repo* config resolves the same shared private credentials file MOVIESHOWS3 already uses (`{"connected":true}`), so the live 683-byte copy with hardcoded values was the stale one. It is now **included** in the deploy. |
| `api/sync-providers.php` | 176-byte divergence with no explanation yet — needs a human diff. |
| `api/test-db.php`, `api/freestyle-search.php` | not currently served; exposing new public endpoints is a product decision. |

## Also worth knowing

The live `movieshows2/api/db-config.php` (683 B) contains a **plaintext database
password**. The repo version is the correct pattern. Treat that credential as exposed
to anyone with FTP access or a backup of that directory and rotate it when convenient.

## Correction: db-config.php is part of the fix

The first dispatch uploaded `movies.php` and `get-movies.php` only, and both then
returned `500 {"success":false,"error":"Database connection failed"}`. That message is
`getDbConnection()` returning null, i.e. the **live** `db-config.php` (683 B, hardcoded
values) holds credentials the database no longer accepts.

Verified before changing anything: the repo `db-config.php` derives its private config
path from `dirname(dirname(dirname(__FILE__)))`, which is identical for
`MOVIESHOWS3/api/` and `movieshows2/api/` because both sit at the same depth. Uploading
it under a throwaway name plus a one-line probe returned `{"connected":true}`, and both
probe files were deleted immediately.

So the deploy list is now three files, and `db-config.php` is the one that makes the
other two work.
