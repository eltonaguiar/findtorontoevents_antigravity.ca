# GHA Fix Batch 1 — duplicate/dead workflow removal (2026-11-15 ~21:00 EST)

Companion to `GHA_TRIAGE_ANALYSIS.md` (same folder family). Follows the "Document Every Fix" rule:
what was broken → what changed → how it is verified.

## What was broken

A family-by-family duplication audit (full comparison of cron, invoked scripts, and output
side-effects per workflow) found nine workflow files with zero unique value:

| Removed file | Why (evidence) |
|---|---|
| `cross-db-consistency.yml` ("Cross-DB consistency guardian (M-005)") | TRUE-REDUNDANT with `cross-db-audit.yml`: same `tools/cross_db_consistency.py`, same real output `cross_db_audit.json`. Its only unique step (commit `cross_db_report.json`) is **provably dead** — the script never writes that filename ("No cross_db_report.json produced"). 1 run/day of no-op. |
| `db-freshness-check.yml` ("DB Freshness Check (Legacy Manual)") | TRUE-REDUNDANT with `db-freshness-guardian.yml`: same `tools/db_freshness_check.py`, same `DB_FRESHNESS_OUTPUT`. Also Bucket-1 broken: never passed in its life (last attempt 2026-05-23), so nothing can depend on its commit step. |
| `live_trading_canada_free.yml` ("Live Trading Bot – Canada Edition (FREE Data)") | TRUE-REDUNDANT with `autonomous_trading.yml`: identical `live_trading_bot_canada.py` in identical `FREE_DATA`/paper mode on identical `0 */4` cron, writing the same `trading_results.json`/`trading_bot.log` — double-writing/clobbering the same files 6×/day. `autonomous_trading.yml` is the superset (adds performance report + path trigger). |
| `meme-scanner-fixed.yml` ("Meme Coin Scanner – Fixed with Monitoring") | Self-labeled `DEPRECATED`, schedule already stripped (manual-only, 0 runs ever), superseded by `meme-scanner-v2.yml`. |
| `ml-battleground-{d,e,ensemble,monitor}.yml.retired` ×4 | Inert `.retired` files (cron commented out; systems killed for 1.9% WR). Zero runs; pure clutter in a 389-file workflow dir. |
| `daily-price-refresh.yml.disabled` | Superseded by `daily-prices-yf-refresh.yml`; calls the documented-dead `fetch_prices.php` endpoint (HTTP 404 that once froze `daily_prices` for 7 weeks). Inert on main (its ~50 branch copies never run schedules). |

Estimated saving: ~71–75 scheduled runs/day removed (plus removal of the clobbering double-writes
in the trading results files and the dead-step noise).

**Not changed (deliberately):**
- `meme-scanner-v2.yml` `*/10` cadence (~144 runs/day) — it drives live meme-coin scan/resolve
  frequency; cadence is a trading-behavior knob, not CI hygiene. Needs an explicit product decision.
- `meme-scanner.yml` → merge into v2 first (v2 lacks the `data/meme_scanner_active.json` export
  consumed by `dashboard_generator.py`, `universal_pick_resolver.py`, `cross_aggregation/aggregator.py`).
- `claude-gainer-ml-live.yml` (48 runs/day) — true overlap with `claude-gainer-tracker.yml`
  (both run `live_scanner.py` and both write `updates/data/antigravity_ml_performance.json`,
  clobbering each other). Merge-first decision needed (which schedule should own the scan?).
- `deploy-fte-events-json.yml` / `deploy-fte-index.yml` — both upload `next/events.json` +
  `last_update.json` to the same FTP paths on every "Scrape events" run, and the `fte-ftp-deploy`
  concurrency serialization is half-wired (index deploy declares no group). Narrowing needs an
  FTP-owner decision.

## What changed

`git rm` of the 9 files above (all removals are version-controlled and trivially revertible).
No surviving workflow's behavior changed.

## How it is verified (subsequent-run inspection)

| Removed workflow | Cadence | Verification check |
|---|---|---|
| Cross-DB consistency guardian (M-005) | daily `0 2 * * *` | **2026-11-16 02:00 UTC tick must produce NO run** (checked 02:05 UTC). Its sibling `Cross-DB Strategy Consistency Audit` (06:00 UTC) must still run — unaffected survivor. |
| Live Trading Bot – Canada Edition (FREE Data) | `0 */4` | 2026-11-16 04:00 UTC tick must produce NO run; `Autonomous Trading Bot` at the same tick MUST still run (the survivor). |
| DB Freshness Check (Legacy Manual) | manual | never fires again; `DB Freshness Guardian` hourly runs unaffected. |
| Meme Coin Scanner – Fixed with Monitoring | manual | never fires again. |
| `.retired` ×4, `.disabled` ×1 | inert | no-op removal (nothing to verify beyond compile health of remaining files). |

Post-landing state checks (every 4h monitoring cron + ad-hoc): workflow names of removed files
must not appear in fresh run lists; no new bucket-1 failures among the survivors.

## Verification note on the earlier dup-guard fix (commit a174e2d00c2)

`branch-large-file-dup-guard.yml` is `on: push` — GitHub executes the workflow definition **from
the pushed ref**, not from main. The `cancel-in-progress: false` fix therefore only takes effect
on branches after they rebase/merge main (or new branches cut from main). Until then, branch
copies keep the 100%-cancel behavior. Verification therefore tracks the completed:cancelled ratio
**per branch containing a174e2d00c2+**, and the old ratio on pre-fix branch copies is expected
to persist short-term. (Baseline: 0 completed / 15 cancelled across all branches.)
