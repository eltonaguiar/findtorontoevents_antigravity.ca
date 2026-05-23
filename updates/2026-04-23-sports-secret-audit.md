# Secret-exposure audit — sports failover branches / `main` (2026-04-23)

## Scope

- `live-monitor/api/db_config.php` and workflow-generated config patterns  
- Grep for `THE_ODDS`, `ODDS_API`, 32+ hex substrings in `live-monitor/` and `.github/workflows/`

## Findings

1. **Deploy workflow** ([`torontoevent-deploy-live-monitor.yml`](../.github/workflows/torontoevent-deploy-live-monitor.yml)) — **no longer embeds** a literal primary Odds API key; both `THE_ODDS_API_KEY` and `ODDS_API_IO_KEY` are passed from **GitHub Actions secrets** into the generated `db_config.php` on **both** deploy targets. Good.

2. **Committed `db_config.php`** in the repo (local dev / fallback) still contains a **hex-formatted** `$THE_ODDS_API_KEY` assignment. This predates the workflow change and **may match** historical git history. **Action:** rotate the key at the-odds-api if exposure is a concern; production FTP deploy **overwrites** this file from CI when the workflow runs.

3. **PR branches (historical):** `git grep` on `origin/main` for odds-related symbols is limited to expected PHP consumers + the workflow. No new accidental paste of `ODDS_API_IO_KEY` literal values in app code on `main` beyond `db_config.php` and variable **names** in `sports_odds.php` (reads from `db_config`).

4. **Runtime / PHP 5.2 on 50webs (not a key leak; production incident):** `sports_failover_proxy.php` (from #342) uses **`??`**, **`[]`**, and **closures** (PHP 7+ / 5.4+), which **do not parse on PHP 5.2** (findtorontoevents.ca/50webs). **torontoevent.net** runs PHP 8.x and is fine. **Fix (2026-04-24):** [`torontoevent-deploy-live-monitor.yml`](../.github/workflows/torontoevent-deploy-live-monitor.yml) no longer deploys the repo’s proxy or `sports_failover_config.php` to 50webs; it uploads small **PHP-5.2-safe stubs** and JSON indicating the real endpoint on torontoevent.net. See [2026-04-24-50webs-sports-failover-php52-stub.md](2026-04-24-50webs-sports-failover-php52-stub.md).

## Verdict

- **No additional secret strings** to strip from the workflow YAML on current `main`.  
- **Rotate** legacy committed key in `db_config.php` on next credential rotation.  
- **Done:** 50webs no longer runs the unparseable proxy file; use torontoevent.net for the full API surface.
