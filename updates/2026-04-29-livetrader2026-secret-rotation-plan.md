# Rotation Plan — `livetrader2026` Hardcoded API Key

**Status:** TRACKING DOC ONLY (no code change in this PR)
**Severity:** CRITICAL (repo is **PUBLIC** — secret is already leaked)
**Owner:** awaiting user approval for Stage 2 rotation
**Source finding:** `reports/round3_bugs_qa_briefing_2026_04_29.md` (Finding F7)

---

## Background

- The literal string `'livetrader2026'` is committed in **9 production PHP files** under `live-monitor/api/`, plus referenced in tooling/workflows.
- Used as: a **shared admin API key** that gates write/maintenance/admin actions on the public 50webs-hosted endpoints (archive picks, update outcomes, run scanners, settle bets, ensure schema, etc.).
- Repo visibility: **PUBLIC** (`gh repo view` → `"visibility":"PUBLIC"`, owner `eltonaguiar`). The key is not just at-rest in the repo — it is **already discoverable on github.com**, full git history.
- Blast radius if leaked (i.e. *now*): any unauthenticated attacker on the public internet who reads the repo can:
  - Hit `goldmine_tracker.php?action=archive&key=livetrader2026` to write fake pick rows into the unified ledger.
  - Hit `goldmine_tracker.php?action=update_outcomes&key=livetrader2026` to overwrite TP/SL outcome state across all systems.
  - Hit `sports_arb_scanner.php?action=run&key=livetrader2026` and `spike_scanner.php` to force expensive scans on demand (compute DoS / cost amplification on the 50webs shared host).
  - Hit `ensure_sports_bets_cohort.php?key=livetrader2026` to mutate sports DB schema.
  - Settle bets / force pick generation on demand via `sports_picks.php`, `sports_bets.php`, `sports_odds.php`, `sports_steam_detector.php`, `pair_fingerprint.php`.
- This is a **shared secret**, so a single string compromise unlocks every admin endpoint at once.

## Affected files (production PHP, the actual gates)

| File | Line(s) | Usage |
|---|---|---|
| `live-monitor/api/sports_picks.php` | 15 | `function sports_picks_key_ok($k) { return ($k === 'livetrader2026'); }` |
| `live-monitor/api/sports_odds.php` | 12 | Inline equality check in admin guard function |
| `live-monitor/api/sports_bets.php` | 14 | Inline equality check in admin guard function |
| `live-monitor/api/goldmine_tracker.php` | 9-11, 29 | `$admin = ($key === 'livetrader2026');` plus three usage docstrings |
| `live-monitor/api/pair_fingerprint.php` | 47 | `$PF_ADMIN_KEY = 'livetrader2026';` |
| `live-monitor/api/spike_scanner.php` | 46 | `$SS_ADMIN_KEY = 'livetrader2026';` |
| `live-monitor/api/ensure_sports_bets_cohort.php` | 4, 9 | `if ($key !== 'livetrader2026') { ... }` (gates schema migration) |
| `live-monitor/api/sports_arb_scanner.php` | 19, 47 | `if (sas_param('key', '') !== 'livetrader2026') { ... }` |
| `live-monitor/api/sports_steam_detector.php` | 17, 57 | `if ($key !== 'livetrader2026') { ... }` |

**Out-of-band callers** (these will need to be updated when the key rotates — they're **not** production gates, but they ship requests with the key):
- `tools/redis_bus_post_sports_hf_next.py`
- `KIMI_RISEOFTHECLAW/live_scanner.py`
- `smart_money/scanner.py`
- `scripts/penny_stock_picks.py`
- `scripts/worldclass/config.py`
- `scripts/config.py`
- `rapid_validation/api/run_validation.php`
- 12+ `.github/workflows/*.yml` files (sports-betting-refresh, goldmine-tracker, spike-scanner, sec-edgar-fetch, smart-money-tracker, regime-detector, daily-picks-snapshot, live-monitor-refresh, penny-stock-picks, rapid-validation, worldclass-pipeline, worldclass-intelligence, torontoevent-{spike-scanner,rapid-validation})

## Threat model

### Pre-leak (current state — **the leak has already happened**)
- Repo is public on GitHub. The key is in the working tree AND in git history. A `git log -p -S 'livetrader2026'` from any clone reveals it.
- Anyone running a GitHub secret-scanner (TruffleHog, GitGuardian, GitHub's native push-protection on private fork-pulls) has likely already flagged it.
- The DB credentials `ejaguiar1_stocks / stocks` and `ejaguiar1_sportsbet / eltonsportsbets` in `live-monitor/api/db_config.php` (lines 8-9, 25-26) are **also** committed in the same public file, plus `FREECRYPTO_API_KEY`, `FINNHUB_API_KEY`, `THE_ODDS_API_KEY`, `FMP_API_KEY`, `MASSIVE_API_KEY`. **Those should be rotated alongside the admin key** (out of scope for this PR but listed here so we don't ship a half-fix).

### Post-rotation (target state)
- The PHP admin key lives in a **gitignored** file on the FTP server only (`live-monitor/api/auth_secret.php`). Repo contains only `live-monitor/api/auth_secret.example.php` with the constant name and a placeholder value.
- All 9 PHP gate files `require_once 'auth_secret.php';` and compare against `ADMIN_API_KEY` constant.
- All workflow callers and Python tooling read the key from `ADMIN_API_KEY` env var (via GitHub Actions secrets / local `.env`).

## Proposed mitigation (urgency order)

### Stage 1 — Hours (cannot break prod, reversible)
**Goal: indirection only — no key change yet.**

1. Create `live-monitor/api/auth_secret.example.php` (committed) with:
   ```php
   <?php
   // Production deploy: copy to auth_secret.php on FTP; never commit.
   define('ADMIN_API_KEY', 'REPLACE_WITH_ROTATED_VALUE');
   ?>
   ```
2. Create `live-monitor/api/auth_secret.php` (NOT committed) with the **current** value `livetrader2026` so prod keeps working during the cutover.
3. Add to `.gitignore`:
   ```
   live-monitor/api/auth_secret.php
   ```
4. Edit each of the 9 PHP gate files: replace the literal `'livetrader2026'` with `ADMIN_API_KEY` and add `require_once dirname(__FILE__) . '/auth_secret.php';` near the top.
5. FTP-upload (per CLAUDE.md `tools/deploy_sports_files.sh` flow) the 10 PHP files (9 modified + 1 new `auth_secret.php` that lives only on the server).
6. Run `tools/deploy_sports_files.sh` smoke tests (pre+post diff) and the hourly `sports-smoke-and-e2e.yml` deploy-guard.

**Verification:**
- `grep -rln "livetrader2026" live-monitor/api/*.php` → zero matches.
- All 9 admin endpoints still return 200 with `?key=livetrader2026` (because `auth_secret.php` on the server still has that value).

### Stage 2 — Day (after Stage 1 ships and bakes for ≥6h)
**Goal: replace the leaked value.**

1. Generate a new 32-byte URL-safe key:
   ```bash
   openssl rand -base64 32 | tr -d '=' | tr '+/' '-_'
   ```
2. Update `auth_secret.php` on the FTP server with the new value (single FTP `put`).
3. Update **GitHub Actions secrets** (`ADMIN_API_KEY` org/repo secret) to the new value.
4. Update each of the 12+ workflow YAML files to read from `${{ secrets.ADMIN_API_KEY }}` instead of `livetrader2026`.
5. Update Python tooling (`scripts/config.py`, `scripts/worldclass/config.py`, `tools/redis_bus_post_sports_hf_next.py`, `KIMI_RISEOFTHECLAW/live_scanner.py`, `smart_money/scanner.py`, `scripts/penny_stock_picks.py`) to read `os.environ['ADMIN_API_KEY']`.
6. Update any out-of-tree consumers (mobile/desktop tooling, browser bookmarks, manual cURL aliases — **user must enumerate these**).
7. Smoke test: `?key=<new>` → 200; `?key=livetrader2026` → 401/403.

**Rollback:** restore old `auth_secret.php` via FTP. Repo / workflow YAML changes are revertible via `git revert`.

### Stage 3 — Week (defense-in-depth)
1. **Per-endpoint scoping.** Split into `SPORTS_ADMIN_KEY`, `GOLDMINE_ADMIN_KEY`, `SCANNER_ADMIN_KEY`. A leak of one no longer unlocks all.
2. **IP allowlist** for admin actions, if 50webs `.htaccess` permits (`Require ip ...`).
3. **Action-specific HMAC.** Replace static keys with HMAC(secret, action+timestamp), 5-minute window. Eliminates replay attack vector.
4. **Rotate the rest of `db_config.php`.** DB password, FREECRYPTO, FINNHUB, ODDS_API, FMP, MASSIVE — all currently committed to this public repo; same exposure profile.
5. **Audit access logs** on 50webs from the date the key was first committed (`git log -S 'livetrader2026' --diff-filter=A` to find the introduction commit) for any unauthorized usage.

## Rollback (Stage 1)

If Stage 1 breaks production (PHP fatal because `auth_secret.php` is missing on the server, syntax error in `require_once`, etc.):

1. Re-upload the **original** PHP files via FTP from the `git show HEAD~1:live-monitor/api/<file>.php` snapshot.
2. Confirm endpoints return 200.
3. Re-investigate failure.

The `tools/deploy_sports_files.sh` script supports a quick revert by uploading the previous git ref.

## Requires user approval

The **Stage 2 rotation cannot be fully automated** because it touches production infrastructure outside the repo. The user must:

1. Generate the new key (`openssl rand -base64 32`) and stash it in 1Password / OS keychain.
2. SFTP/FTP-upload the new `auth_secret.php` to `/findtorontoevents.ca/live-monitor/api/auth_secret.php` on `ftps2.50webs.com`.
3. Set the `ADMIN_API_KEY` GitHub Actions secret in the repo settings.
4. Manually update any **out-of-tree** consumers (browser bookmarks, mobile tooling, manual cURL/Postman saved requests, third-party uptime monitors hitting these endpoints).
5. Confirm via `curl https://findtorontoevents.ca/live-monitor/api/sports_picks.php?action=today&key=<NEW>` → 200, and `?key=livetrader2026` → 401.

## Recommended user action — order of operations

1. **Immediate (today):** assume the key is leaked. If you see weird writes in the `goldmine_picks` / `sports_bets` tables, treat them as untrusted and back up the DB.
2. **This week:** approve Stage 1 (PR to extract literal → constant). Low risk, fully revertible.
3. **Next week:** approve Stage 2 (rotate the value). Requires FTP coordination per `tools/deploy_sports_files.sh`.
4. **Within a month:** rotate the OTHER secrets in `live-monitor/api/db_config.php` (DB password is `stocks`, also literally committed). Same gitignore + FTP pattern.

## References

- Source finding: `reports/round3_bugs_qa_briefing_2026_04_29.md` (Finding F7)
- Deploy contract: `CLAUDE.md` → "After merging any sports-PR to main, run `tools/deploy_sports_files.sh`"
- Last sports-deploy outage from skipping the FTP step: PR #399 (squash → conflict markers), PR #415 (missing require_once)
- Related: `live-monitor/api/db_config.php:8-9,25-26` (committed DB credentials — same exposure class)
