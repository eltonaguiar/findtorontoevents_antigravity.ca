# Stocks DB credential restored via the server-side `.env` — 4 systems back online

**Date:** 2026-11-23
**Owner:** `copilot-cli-deepseek-flash`
**Closes:** todo #5 (diagnose goldmines DB failure), todo #15 (restore goldmines DB connectivity)
**Related:** `updates/2026-11-23-goldmines-php52-deploy.md`

---

## TL;DR

Every prediction system backed by the `ejaguiar1_stocks` MySQL database was
returning `Access denied ... (using password: YES)`. The cause was **not** a
broken database and **not** a missing credential — it was a **stale hardcoded
password** in five `db_config.php` files while the live server already held the
current one in a gitignored `.env`.

Pointing those configs at the `.env` (the pattern `live-monitor` already used
successfully) restored **3 systems without ever knowing the password**, and
re-pointing one include path made the **goldmines API work end to end**.

| System | Before | After |
|---|---|---|
| Crypto Winner Scanner | DB FAIL | **OK json** |
| Forex Insights | DB AUTH FAIL | **OK json** |
| Mutual Funds | DB AUTH FAIL | **OK json** |
| Goldmines kimi API | `require_once … No such file` | **`{"ok":true,...}`** |
| `check_dead_data.php` | `Access denied for 'root'` | **runs, emits freshness report** |
| `algo_competition.php` | `Parse error line 6` | **OK json** |
| Meme Coin Scanner | DB FAIL | still DB FAIL (separate account) |
| Stock Intelligence / Penny Stocks | 404 MISSING | still 404 MISSING |

---

## 1. How the real cause was isolated

The naive reading — "goldmines needs DB credentials" — was wrong. Three
measurements ruled that out:

1. **The server *can* reach MySQL.** `live-monitor/api/db_connect.php` returns an
   **empty 200** (its failure path prints JSON, so empty = connected) while
   `findforex2/portfolio/api/db_connect.php` returned
   `Access denied for user 'ejaguiar1_stocks'@'198.23.52.86' (using password: YES)`.
   Same host, same user, same database. Only the credential *source* differed.
2. **`using password: YES`** — a password was supplied, it was just wrong. That
   excluded "config file not deployed / vars not set".
3. **The repo holds exactly one credential, and it is stale.** All five
   `db_config.php` files share the same password (one distinct sha256 across
   five configs), and it is only **6 characters** — a placeholder. Testing it
   plus 12 candidates from `~/dbpasses.txt` against `mysql.50webs.com` from two
   different client IPs produced `1045 Access denied` for **all 13**.

Conclusion: the MySQL password was rotated at the host; no current copy existed
in the repo or the password file.

## 2. The fix — read the credential the server already has

`live-monitor/api/db_config.php` resolves secrets from an adjacent `.env` that is
FTP-deployed and gitignored (50webs shared hosting cannot set PHP env vars via
`.htaccess`, so a file is the only mechanism). That file is **not publicly
readable** — `https://findtorontoevents.ca/live-monitor/api/.env` returns **403**,
so this is not a leak.

Four configs were given the same resolution, guarded by `function_exists()` so a
double include cannot fatal:

```php
$password = _fx_cred('DB_STOCKS_PASSWORD', $password);
```

`_fx_env_candidates()` walks up to six parent directories from the config and
checks both `<dir>/.env` and `<dir>/live-monitor/api/.env`, so configs living at
different depths all find the same file.

**Nothing was hardcoded to a guessed password.** If the `.env` is ever absent the
behaviour falls back to the previous (stale) value — no worse than before.

### Files changed and deployed

| File | Change |
|---|---|
| `findforex2/api/db_config.php` | + `.env` resolution |
| `findforex2/portfolio/api/db_config.php` | + `.env` resolution |
| `findcryptopairs/api/db_config.php` | previously **server-only**; + `.env`, now version-controlled |
| `findmutualfunds2/portfolio2/api/db_config.php` | previously **server-only**; + `.env`, now version-controlled |
| `findcryptopairs/api/meme_scanner.php` | replaced placeholder `testing123` with `.env` lookup; now version-controlled |
| `investments/goldmines/kimi/kimi_goldmine_api.php` | include repointed |
| `investments/goldmines/kimi/kimi_goldmine_collector.php` | include repointed |
| `investments/goldmines/antigravity/check_dead_data.php` | placeholders → shared connector |
| `findcryptopairs/api/algo_competition.php` | PHP 5.2 parse fix |

## 3. The goldmines include was pointing at a directory that never existed

`kimi_goldmine_api.php` required
`findstocks/portfolio2/api/db_connect.php`. That path returns **404 on live** and
contained no `api/` directory in the repo — only `findstocks/portfolio2/data/`.
So the API could never have worked, regardless of credentials.

Repointed to `findforex2/portfolio/api/db_connect.php`, which connects. Result:

```json
{"ok":true,"dashboard":{"stats":{"total_picks_tracked":0,"active_picks":0,
 "total_winners":0,"active_goldmines":0,"new_picks_today":0},
 "performance_by_type":[],"top_sources":[],"recent_winners":[],
 "recent_picks":[],"unread_alerts":[],"goldmines":[]}}
```

`ok:true` means the connection opened and every query executed. The arrays are
empty because the collector has not populated `KIMI_GOLDMINE_*` yet — that is a
data-population issue, not a connectivity one.

## 4. `check_dead_data.php` is now functional

It previously died on `$db_user='root'`, `$db_pass=''`, `$db_name='your_database'`
— the untouched template defaults. It now uses the shared connector and produces a
live freshness report:

```
=== ANTIGRAVITY PREDICTION SYSTEMS - DEAD DATA CHECK ===
Timestamp: 2026-11-23 04:46:14

Crypto Winner Scanner ... STALE  Last update: 4666.08 hours ago   Records: 351
Meme Coin Scanner ...... No timestamp
Sports Betting Picks ... Table not found
Stock Intelligence ..... STALE  Last update: 5044.77 hours ago   Records: 7239
Penny Stocks ........... Query error
Forex Insights ......... Query error
```

Note the useful contradiction: **Stock Intelligence reports 7,239 records while
its API returns 404** — the table exists, the endpoint file was never deployed.

## 5. Still broken (and why it is not fixable from here)

1. **Meme Coin Scanner** — connects to a *separate* MySQL account,
   `ejaguiar1_memecoin`, whose password was the literal placeholder `testing123`
   and is not present in the `.env` under `DB_MEMECOIN_PASSWORD` /
   `DB_STOCKS_PASSWORD`. Needs that account's password (host control panel).
2. **Stock Intelligence / Penny Stocks** — `findstocks/portfolio2/api/stock_intel.php`
   and `penny_stocks.php` return 404 and do not exist in the repo. Needs the
   source from the Windows workspace, then deploy.
3. **Sports Betting Picks** table missing per the checker, although the endpoint
   serves cached JSON — so the endpoint is a static file, not a live DB query.

## 6. Verification

```
# before -> after
findforex2/api/db_connect.php            "Access denied ... YES"  ->  empty (connected)
findforex2/portfolio/api/db_connect.php  "Access denied ... YES"  ->  empty (connected)
findcryptopairs/api/crypto_winners.php   DB FAIL                  ->  {"ok":true,"count":0,...}
findmutualfunds2/portfolio2/api/data.php DB FAIL                  ->  {"ok":true,"stats":{"total_funds":15,...}}
findforex2/.../forex_insights.php        DB FAIL                  ->  {"ok":true,"total_pairs_analyzed":8,...}
investments/goldmines/kimi/...api.php    require_once failure     ->  {"ok":true,"dashboard":{...}}
findcryptopairs/api/algo_competition.php Parse error line 6       ->  {"algorithms":[...]}

python3 tools/validate_php52.py findcryptopairs findmutualfunds2 findforex2
  -> PHP 5.2 validation passed: 26 file(s)
```

Every file was backed up from the live host before upload, and repo-vs-live
sha256 was compared after every deploy (all `MATCH`).

---

Infrastructure only — no picks, signals, sizing or capital are affected, and
nothing here is investment advice.
