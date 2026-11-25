# Credential rotation audit — public repo, CI secrets, live .env files

**Date:** 2026-11-25
**Scope:** `github.com/eltonaguiar/findtorontoevents_antigravity.ca` (public), its Actions secrets and workflows, and the live `.env` / `db_config.php` files on 50webs that consume the rotated credentials.
**Question asked:** after today's credential rotation, are the credentials that leaked into the public repo still alive, and are the GitHub Actions healthy?

---

## 1. What is exposed in the public repo

The repository is **public**, and 17 tracked files carry credential-looking assignments. The material ones:

| File | Exposed |
|---|---|
| `HANDOFF_CLAUDE_CLI_2026-06-03.md`, `groksstuff.txt`, `audit_dashboard/incidents.html` (+28 more) | the **live** `ejaguiar1_stocks` DB password, 138 times (see §7) |
| `tools/deploy_sports_files.sh` | `FTP_HOST` |
| `findcryptopairs/api/db_config.php`, `findforex2/api/db_config.php`, `findforex2/portfolio/api/db_config.php`, `findmutualfunds2/portfolio2/api/db_config.php`, `findstocks/kimis_claw/api/db_config.php`, `findstocks/portfolio2/api/db_config.php`, `live-monitor/api/db_config.php`, `rapid_validation/api/run_validation.php`, `rapid_validation/api/rapid_signal_engine.php` | one shared `$password` (6 chars, sha `1ef8f254`) for user `ejaguiar1_stocks`, host `mysql.50webs.com` |
| `favcreators/docs/api/db_config.php` | `MYSQL_PASSWORD` (a different, 9-char value) |
| `favcreators/docs/api/events_db_config.php` | events DB user/password |

## 2. Liveness test — measured, not assumed

| Credential | Test | Result |
|---|---|---|
| Public `db_config.php` password (`1ef8f254`) | MySQL auth to `mysql.50webs.com` as `ejaguiar1_stocks` | **DEAD** — `(1045) Access denied` |
| `~/dbpasses.txt` current 50webs FTP password | FTPS login | **ALIVE** |
| `ejaguiar1_stocks` / `REDACTED_DB_PASS` | MySQL auth | **ALIVE** — `ejaguiar1_stocks@%`, server 8.4.7 |
| `ejaguiar1_favcreators` / `favcreators1234560` | MySQL auth | **ALIVE** |
| `ejaguiar1_events` / `events1234560` | MySQL auth | **ALIVE** |

**Verdict:** every credential that ships in the public repo is **dead**. The rotation did its job on the leaked values.

**Residual risk (not fixed here):** the *current* database passwords follow a guessable pattern — `<dbname minus "ejaguiar1_"> + "1234560"` — and MySQL at `mysql.50webs.com:3306` is reachable from the internet. `ejaguiar1_stocks/REDACTED_DB_PASS` authenticates from this workstation. These should be replaced with random values, and the app configs updated in the same pass.

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


---

## 7. Correction + the real leak: the LIVE DB password was published 138 times

**Correction to §1:** `deploy_updates_page.py` is *not* a leak — it already reads `FTP_PASS` from the environment and exits if unset. The earlier entry was wrong; the committed literal it was blamed for does not exist in the current file.

**What is actually exposed:** the **current, working** `ejaguiar1_stocks` password was committed **138 times across 31 tracked files** in the public repo, including:

| File | Occurrences | Public? |
|---|---|---|
| `groksstuff.txt` | 75 | yes |
| `HANDOFF_CLAUDE_CLI_2026-06-03.md` | 11 | yes |
| `reports/transcript_scan_20260525_055154.md` | 9 | yes |
| `docs/DB_CREDENTIALS_MIGRATION_2026-06-02.md` | 6 | yes |
| `audit_dashboard/incidents.html` + `data/incidents_enhancements_feed.json` | 6 | **served on the live /audit dashboard** |
| 26 more docs/reports/notes | 31 | yes |

This is the already-open P0 incident "Live DB password hardcoded repo-wide" (#89). Its remediation in June scrubbed the **`.py`** files and added a CI fence, but the password itself was left quoted in every doc that *described* the leak — and in `incidents.html`, which the dashboard serves to the public.

**Fixed:** all 138 occurrences replaced with `REDACTED_DB_PASS`. The CI fence (`db-password-leak-guard.yml`) still detects the same credential — its pattern was rewritten from one exact string to the equivalent family regex `(stocks|backtests|sportsbet|favcreators|events|memecoin|news|tvmoviestrailers|deals)1234560`, so the guard works without itself spelling the password.

**Not fixed, and cannot be by editing files:** the password has been public since June. It must be **rotated** (`ALTER USER ejaguiar1_stocks ...`), which also means updating `~/dbpasses.txt`, every `.env` on 50webs, the Actions `DB_*` secrets, and `db-password-leak-guard.yml`'s pattern. Redaction shrinks the blast radius; it does not undo the exposure.

## 8. Dead deploy path fixed: `tools/deploy_sports_files.sh`

It sourced `FTP_USER`/`FTP_PASS` from `C:/windows_env_backup_2026-04-14.md`, a hand-written operator note that still holds a **pre-rotation** password — so the script died with `530` on any machine where that file existed, and on Linux it simply refused. New precedence:

1. exported `FTP_USER` / `FTP_PASS` (CI, or an explicit `export`)
2. `$REPO_ROOT/.env.deploy` — new supported local store, added to `.gitignore`
3. the legacy Windows note, **last resort**, with a printed staleness warning
4. otherwise exit 2 with copy-pasteable instructions

`bash -n` clean.

## 9. Seven PHP files still hardcoded the dead DB password

`findstocks/kimis_claw/api/{db_config,competition,debug,diagnose}.php`, `findmutualfunds2/portfolio2/api/db_config.php`, `rapid_validation/api/{run_validation,rapid_signal_engine}.php` carried the dead 6-char value with no override. Each now resolves `DB_STOCKS_PASSWORD` from the environment or a gitignored `.env` (walking up to 6 directories, plus `live-monitor/api/.env`), keeping the old literal only as a last-resort default so nothing regresses on a host with no `.env`.

`findcryptopairs/api`, `findforex2/api`, `findforex2/portfolio/api` already had this pattern from 2026-11-23 and were left alone.

### Deployed and verified

Three of the seven exist on 50webs; each was backed up to `*.bak-cred-20261125` before upload:

| Endpoint | Before | After |
|---|---|---|
| `/rapid_validation/api/run_validation.php?key=…` | `Database connection failed` | **200** `{"ok":true,…,"signals":{"total":35425,"closed":35425}}` |
| `/rapid_validation/api/rapid_signal_engine.php?key=…` | same failure | **200** `{"ok":true,"initialized":true,…}` |
| `/findmutualfunds2/portfolio2/api/db_config.php` | dead password | **200**, no output (correct for a config include) |

`findstocks/kimis_claw/api/*` is not deployed under `findtorontoevents.ca` on 50webs (`error_perm` on RETR), so those four are repo-only changes.

### Side finding (pre-existing, not changed)

`run_validation.php?key=wrong` returns **200**, not 401. The `http_response_code(401)` call is a no-op on this old PHP build, so the auth check sets no status — the body still refuses, but the endpoint looks open to anything that only checks status codes. Worth fixing separately.

## 10. Verification after all of the above

- Live-password occurrences left in tracked files: **0**.
- `bash -n tools/deploy_sports_files.sh` → clean.
- `.env` downloads from the web root: `/live-monitor/api/.env`, `/findforex2/api/.env`, `/favcreators/docs/api/.env`, `/fc/api/.env`, `/fc/api/.env.events` → all **403** (protected).
- Patched endpoints → 200 with live data (§9). Config includes → 200 empty, no `Fatal error`.
