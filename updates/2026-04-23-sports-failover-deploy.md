# Sports failover + settle bundle — deploy record (2026-04-23)

## Shipped to `main`

1. **CI: deploy workflow** — [`.github/workflows/torontoevent-deploy-live-monitor.yml`](../.github/workflows/torontoevent-deploy-live-monitor.yml) now injects `THE_ODDS_API_KEY` and `ODDS_API_IO_KEY` from GitHub Actions secrets into **both** generated `db_config.php` blocks (GoDaddy + 50webs). Removes hardcoded primary key from YAML (rotate key at the-odds-api if that hex was ever public).

2. **PR #342 merged** — Multi-key odds failover, `sports_failover_proxy.php`, `sports_failover_config.php`, `odds_api_fetch.php`, `nba_odds_scraper.py`, `sports-failover.js`, updates to `sports-betting.*`, `sports_odds.php`, etc.

3. **PR #343** — Closed as superseded (empty diff vs #342 on `sports_odds.php`). See [2026-04-23-sports-failover-pr-diff-audit.md](2026-04-23-sports-failover-pr-diff-audit.md).

4. **PR #349 merged** — Atomic settle bundle: `sports_scores_settle_lib.php` + `sports_bets.php` + `sports_picks.php` (port from codex/345, **not** that branch’s `odds_api_fetch.php`). See [2026-04-23-sports-settle-lib-bundle.md](2026-04-23-sports-settle-lib-bundle.md).

5. **PR #345** — Closed; scope split between #342 and #349. Optional ESPN/third-provider follow-up is **not** tracked as GitHub issue #350 (that number does not resolve to an open issue/PR); open a new issue when scoped.

## GitHub Actions

- `gh run list --workflow=torontoevent-deploy-live-monitor.yml` showed deploys **in progress** for: workflow commit, #342, #349 (2026-04-23 ~03:37–03:38 UTC).

## Live smoke (read-only)

- `https://findtorontoevents.ca/live-monitor/api/sports_odds.php?action=credit_usage` — HTTP 200, JSON `ok: true` (post-deploy check).
- `?action=sports` — 200, six active sports (NBA, NCAAB, NHL, …).

## Manual follow-ups (not automated here)

- **E2E failover:** In a safe window, temporarily set an invalid **primary** key in a **staging** or one-off `db_config` test and confirm the **secondary** `ODDS_API_IO_KEY` path serves requests; then restore. This proves failover beyond “CI wrote both variables.” (Plan item; **not** run in CI here — needs host access / maintenance window.)
- **Key rotation** if the old hardcoded `THE_ODDS` hex was exposed in git history: rotate at the-odds-api.com; update GitHub secret `THE_ODDS_API_KEY`. See [2026-04-23-sports-secret-audit.md](2026-04-23-sports-secret-audit.md).
- **PHP 5.2 on 50webs / proxy:** `sports_failover_proxy.php` (from #342) requires **PHP 7+** (`??`, `[]`, closures). **findtorontoevents.ca** was serving a **parse error** for that file; **torontoevent.net** is PHP 8.x and healthy. The live-monitor deploy workflow now **does not** upload the repo’s proxy/config to 50webs and instead deploys small **PHP-5.2-safe stubs** that return JSON pointing clients at torontoevent.net. See [2026-04-24-50webs-sports-failover-php52-stub.md](2026-04-24-50webs-sports-failover-php52-stub.md). `tools/validate_php52.py` is still not a repo gate; [2026-04-23-sports-secret-audit.md](2026-04-23-sports-secret-audit.md) remains the static review record.

## Rollback (plan checklist)

- **Code:** `git revert <merge-commit>`, push `main`, let `[torontoevent.net] Deploy Live Monitor APIs` run.
- **Config-only:** Re-upload last-known-good `db_config.php` to both FTP roots if only secrets broke.
- **Queue:** Before future high-risk merges, `gh run list --workflow=torontoevent-deploy-live-monitor.yml --limit 5` to avoid overlapping deploys.

## Rollback (reference)

- Revert: `git revert <merge-commit>`, push `main`, let deploy workflow run.
- **Secrets:** `THE_ODDS_API_KEY`, `ODDS_API_IO_KEY` must be set in repo Settings → Actions secrets for the workflow to emit non-empty keys.
