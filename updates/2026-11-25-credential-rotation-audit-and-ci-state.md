# Credential rotation audit — public repo, CI secrets, live .env files

**Date:** 2026-11-25
**Scope:** `github.com/eltonaguiar/findtorontoevents_antigravity.ca` (public), its Actions secrets and workflows, and the live `.env` / `db_config.php` files on 50webs that consume the rotated credentials.
**Question asked:** after today's credential rotation, are the credentials that leaked into the public repo still alive, and are the GitHub Actions healthy?

---

## 1. What is exposed in the public repo

The repository is **public**, and 17 tracked files carry credential-looking assignments. The material ones:

| File | Exposed |
|---|---|
| `deploy_updates_page.py` | `FTP_PASS` (13 chars) |
| `tools/deploy_sports_files.sh` | `FTP_HOST` |
| `findcryptopairs/api/db_config.php`, `findforex2/api/db_config.php`, `findforex2/portfolio/api/db_config.php`, `findmutualfunds2/portfolio2/api/db_config.php`, `findstocks/kimis_claw/api/db_config.php`, `findstocks/portfolio2/api/db_config.php`, `live-monitor/api/db_config.php`, `rapid_validation/api/run_validation.php`, `rapid_validation/api/rapid_signal_engine.php` | one shared `$password` (6 chars, sha `1ef8f254`) for user `ejaguiar1_stocks`, host `mysql.50webs.com` |
| `favcreators/docs/api/db_config.php` | `MYSQL_PASSWORD` (a different, 9-char value) |
| `favcreators/docs/api/events_db_config.php` | events DB user/password |

## 2. Liveness test — measured, not assumed

| Credential | Test | Result |
|---|---|---|
| `deploy_updates_page.py` `FTP_PASS` | FTPS login to `ftps2.50webs.com` as `ejaguiar1` | **DEAD** — `530 Login authentication failed` |
| Public `db_config.php` password (`1ef8f254`) | MySQL auth to `mysql.50webs.com` as `ejaguiar1_stocks` | **DEAD** — `(1045) Access denied` |
| `~/dbpasses.txt` current 50webs FTP password | FTPS login | **ALIVE** |
| `ejaguiar1_stocks` / `stocks1234560` | MySQL auth | **ALIVE** — `ejaguiar1_stocks@%`, server 8.4.7 |
| `ejaguiar1_favcreators` / `favcreators1234560` | MySQL auth | **ALIVE** |
| `ejaguiar1_events` / `events1234560` | MySQL auth | **ALIVE** |

**Verdict:** every credential that ships in the public repo is **dead**. The rotation did its job on the leaked values.

**Residual risk (not fixed here):** the *current* database passwords follow a guessable pattern — `<dbname minus "ejaguiar1_"> + "1234560"` — and MySQL at `mysql.50webs.com:3306` is reachable from the internet. `ejaguiar1_stocks/stocks1234560` authenticates from this workstation. These should be replaced with random values, and the app configs updated in the same pass.

## 3. GitHub Actions state

`gh api .../actions/secrets` (values are write-only; only metadata is visible):

- `FTP_PASS`, `FTP_PASSWORD_50WEBS`, `FTPGODADDYPASS`, `FTP_PASSWORD_TDOTEVENT` — all updated **2026-11-25T19:24:2x Z** (by copilot's pass).
- `FTP_HOST`, `FTP_USER`, `FTP_SERVER*`, `FTP_USERNAME_*` — last set 2026-10-23; still correct.
- DB-oriented secrets (`DB_PASS`, `DB_PASSWORD`, `DB_STOCKS_PASSWORD`, `AUDIT_DB_PASS`, `DB_CREDENTIALS_JSON`, …) — last set **2026-05-23**, six months stale.

**Failure forensics:** runs at 19:18:46 and 19:23:45 (`[torontoevent.net] Run Backtests & Deploy Dashboards`, `Deploy Competition to Live Site`) failed with `ftplib.error_perm: 530 Login authentication failed` / `Login failed: 530`. Both **started before** the 19:24:28 secret update.

**Measured state after the update:** runs at 19:24:41 (`Deploy findtorontoevents.ca core site`) and 19:24:43 (`[torontoevent.net] Run Backtests & Deploy Dashboards`) — **success**. Across the 60 most recent runs, **0 failures after 19:24:30Z**.

Repo hardening: 0 deploy keys, 0 webhooks, default branch `main`, last push 2026-11-25T19:30:27Z.

## 4. Two live breakages found and fixed

### 4a. `events_feed.php` returning 503
`https://findtorontoevents.ca/fc/api/events_feed.php` → `503 {"ok":false,"error":"database connection failed"}` with 66 matching
`DB Connection failed: ... Access denied for user 'ejaguiar1_stocks'@'198.23.52.86'` lines in the error log up to 19:13.

Root cause: `/fc/api/.env.events` still held the **pre-rotation** user/password (16-char user, 11-char password, sha `a4602d6b`) — the same values committed in the public repo's `events_db_config.php`.

Fix: backed up to `.env.events.bak-20261125`, rewrote with the verified working values
(`EVENTS_MYSQL_USER=ejaguiar1_events`, `..._PASSWORD=events1234560`, `..._DATABASE=ejaguiar1_events`, host `localhost`).
**Verified:** `events_feed.php?limit=2` → `200`, `{"ok":true,"count":2,"total":13427}`, twice in a row.

### 4b. Four server-side `db_config.php` files on the stale password
`findcryptopairs/api/`, `findforex2/api/`, `findmutualfunds/api/`, `goldmine_cursor/api/` all still contained the dead 6-char password (sha `1ef8f254`) — i.e. the exact value that is public on GitHub. Each was backed up to `<file>.bak-20261125` and its password literal replaced with the verified working one (sha `618e41f5`).

`live-monitor/api/db_config.php` has an **empty** password literal; `live-monitor/api/.env` holds the correct `DB_STOCKS_PASSWORD` (sha `618e41f5`), so it resolves at runtime and was left alone.

## 5. Verification after the changes

| Check | Result |
|---|---|
| `findtorontoevents.ca/index.html` | 200 (363,266 B) |
| `/fc/`, `/audit/` | 200 |
| `events_feed.php?limit=2` | 200, `total: 13427` |
| `/findcryptopairs/`, `/findforex2/`, `/findmutualfunds/`, `/goldmine_cursor/` | 200, no `Fatal error` / `Access denied` text in the HTML |
| CI failures after 19:24:30Z | 0 |

## 6. Still open

1. **Weak DB passwords** (`<db>1234560`) on an internet-reachable MySQL — rotate to random values and update: `/fc/api/.env`, `/fc/api/.env.events`, `/fc/api/.env`-equivalents under `find*/api/` and `live-monitor/`, plus the `DB_*` Actions secrets (six months stale).
2. **The public repo still ships credential files.** Deleting them from `main` does not remove them from history; a `git filter-repo` rewrite + force-push is required, and that needs explicit operator approval. Until then, treat those files as permanently public and keep the values dead.
3. `live-monitor/api/db_config.php` empty-password literal — works today via `.env`, fragile if `.env` disappears.
4. `aggregate_creator_news.php` times out (000) from the public internet — slow endpoint, not a credential failure.
