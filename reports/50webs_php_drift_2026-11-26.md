# 50webs PHP drift audit — 2026-11-26

Goal: find the same class of fault that broke the movie refresh, where the live file
on 50webs is not the file in the repo. Method: `tools/php52_drift_check.py` logs into
`ftps2.50webs.com` over FTP and compares **sha256 of every deployed `.php`** against
its repo counterpart, per directory.

## Result

| Directory | Live | In repo | Identical | Drifted | Live-only | Repo-only |
|---|---|---|---|---|---|---|
| `MOVIESHOWS3` | 17 | 1 | 1 | 0 | 16 | 0 |
| `MOVIESHOWS3/api` | 43 | 7 | 7 | 0 | 36 | 0 |
| `MOVIESHOWS3/log` | 1 | 1 | 1 | 0 | 0 | 0 |
| `movieshows2` | 6 | 0 | 0 | 0 | 6 | 0 |
| `movieshows2/api` | 13 | 6 | 3 | **3** | 10 | **3** |
| `fc/api` | 226 | 85 | 85 | 0 | 141 | 0 |

**94 files byte-identical, 3 drifted, 209 live-only orphans, 3 repo-only.**

## The 3 drifted files (all `movieshows2/api`)

| File | Live | Repo | Reading |
|---|---|---|---|
| `db-config.php` | 683 B | 2,886 B | Live is a **stub/short config**, repo is the full one. This is the hazard that prints a raw SQLSTATE: a stale inline PDO config proves itself when the error text is not the friendly `DB connection failed`. |
| `movies.php` | 19,500 B | 7,950 B | Live is **2.4× larger** than the repo file. The deployed copy has code the repo does not, so deploying the repo version would delete live behaviour. Not auto-fixed. |
| `sync-providers.php` | 6,912 B | 6,736 B | Small divergence (176 B), most likely an older revision. |

## Repo files that are not deployed

`movieshows2/api/`: `freestyle-search.php` (26 KB), **`get-movies.php`** (2,025 B),
`test-db.php` (542 B).

`get-movies.php` matters: it is one of the two files fixed for PHP 5.2 in PR #1206,
and MOVIESHOWS2 has no deploy workflow, so the fix exists only in git. The OPTIONS
preflight on `/movieshows2/` therefore still runs the old code.

## Orphans (live-only)

209 `.php` files exist on the host with no repo counterpart: 52 under `MOVIESHOWS3`
and `MOVIESHOWS3/api` (admin/populate/debug scripts), 16 under `movieshows2`, and
141 under `fc/api`. These are not drift in the harmful sense — nothing in the repo
will overwrite them — but they are unreviewed, undeployable, publicly reachable PHP
(several are `debug_*.php`, `test_*.php`, `diagnose_*.php`) on a host running
PHP 5.2. Worth a separate cleanup decision.

## What was NOT done, deliberately

- **No deploy of `movieshows2/api/movies.php`** — replacing a live 19.5 KB file with
  a 7.95 KB one destroys unknown production behaviour. This needs a human diff.
- **No deletion of orphans** — they may be load-bearing for cron jobs or external
  callers.

## How to re-run

```
python3 tools/php52_drift_check.py            # summary, exit 1 if any drift
python3 tools/php52_drift_check.py --report reports/drift.md
```
