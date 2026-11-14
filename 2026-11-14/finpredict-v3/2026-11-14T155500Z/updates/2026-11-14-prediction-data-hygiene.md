# Prediction-System Data-Hygiene Audit + Remediation Plan (2026-11-14)

## What was broken (verified against live payload `dashboard_data.json`, generated 2026-11-14T14:30Z)

| # | Defect | Evidence (live) | Root cause |
|---|--------|------------------|------------|
| 1 | **Crypto prices pinned to entry (STALE)** | `XRPUSDT`, `BTCUSDT` have `current_price == entry_price` exactly while 24/7 market moved +0.9% / +1.3% (Binance live). Only `NEARUSDT` carries a live quote. | Active-crypto `current_price` is not being refreshed at payload generation. `universal_price_enricher.py` exists to do this but is not effectively populating the dashboard crypto rows. |
| 2 | **UI "1.9h ago" is signal age, not price freshness** | Newest crypto signal = 2026-11-14T13:53Z (1.9h before 15:50Z). XRP/BTC were never re-quoted at the 14:30Z build. | Banner is computed from `signal_time`; it does not reflect the last price-quote time. |
| 3 | **11 frozen closed FOREX phantoms** | `recent_closed` rows with `pnl_pct=0.0`, `exit_reason=UNKNOWN`, `exit_price==entry_price`, dated March 2026 (EURUSD, USDCHF, USDJPY, AUDUSD, GBPUSD, NZDUSD, SOFI). | Resolver never actually resolved these; exit forced to entry (0%) with reason UNKNOWN. |
| 4 | **Futures/placeholder `no date`** | `ES=F` active pick has `signal_time`/`entry_time` as bare `"2026-11-14"` (date-only string) → UI datetime-parse renders blank. It is gated (`_gate_passed=false`), trust LOW, 0 closed history. | Seed emitter serializes a date-only string for futures; not a monitored live position. |
| 5 | **Bond picks unmarked / dead class** | Open bond seeds signal Nov 13 (~1d) but most `current_price=null`; only settled bond trade closed Nov 10 ("4 days ago"); class `n=1` closed, status insufficient_data. | Bond signals emitted without price backfill; class effectively inactive. |
| 6 | **Survivorship in headline stats** | Only 7,914 / 16,126 closed picks (49%) pass integrity gates; 8,888 auto-expired removed before resolution. Headline WR 41.8% / PF 0.94 computed on survivors. | Integrity/expiry exclusions overlap and are excluded from headline performance. |
| 7 | **Metrics not alive** | `edge_ratio`/`strategy_scores` absent from main dashboard JSON; `backtest_vs_forward` FWD populated for only 48% (111/255 zero-forward); `strong_signals.json` 404; kalshi on-disk snapshot ~7 months old with null prices; walkforward/analyst sections months old; several sections empty. | FWD/source strategies lack forward trade volume; kalshi/strong-signals snapshots not refreshed. |

## What I changed

Added an additive, read-only **data-hygiene guardian** (no changes to the live pipeline):

- `tools/pi_data_hygiene.py` — flags `STALE_CRYPTO_PRICE`, `FROZEN_CLOSED_PHANTOM`, `DATE_ONLY_SEED`, `NULL_PRICE`, `PLACEHOLDER_ENTRY`, and prints TRUE per-class recency (signal age vs whether a live quote exists).
- `tests/test_pi_data_hygiene.py` — 11 unit/intgration tests, all passing.

Run:
```
python tools/pi_data_hygiene.py --json audit_dashboard/data/dashboard_data.json --asof 2026-11-14T15:50:00+00:00 --show
```

Live result (2026-11-14): 2 stale crypto prices, 11 frozen phantoms, 3 date-only seeds. Exit code 1 when findings exist (CI-gateable).

## Per-asset-class remediation plan

| Class | Fix | Target code |
|---|---|---|
| CRYPTO | Refresh `current_price`/`pnl_pct` from live Binance at generation time for all 24/7 symbols; skip "pinned" rows from the active PnL display until quoted. Gate: if `current==entry`, label `UNQUOTED`, never "live". | `alpha_engine/universal_price_enricher.py` (Binance batch), `alpha_engine/active_picks_sync.py:131` (`compute_verdict`). Wire the enricher into the dashboard build step so crypto rows are re-quoted before `dashboard_data.json` is emitted. |
| EQUITY / ETF | No price bug (verified vs Yahoo Friday close). Add a `last_quote` timestamp and show "last close Fri 11/13", so 0% PnL is understood as parked, not live. Re-quote at next session open. | EN generator / frontend freshness display (`audit_dashboard/dashboard_freshness.js`). |
| FOREX | Do not emit `FROZEN_CLOSED_PHANTOM` rows: add a resolver sweep that either resolves them properly or purges them. Fix batch-identical `closed_at` timestamps (USDJPY/AUDUSD same second). | `alpha_engine/forced_resolution.py`, `audit_trail/dashboard_generator.py` (closed pick query). |
| FUTURES | Emit full ISO timestamps (never date-only) for `signal_time`/`entry_time`; do not list gated/placeholder rows (`_gate_passed=false`, 0 closed history) as active picks — filter them out or mark `PLACEHOLDER`. | Futures seed emitter (e.g. `copy_trader_intel/multi_asset_copytrader_scraper.py`), and the active-picks filter used by `dashboard_generator.py`. |
| BOND | Backfill `current_price` for bond seeds or do not emit unquoted signals; route bond class through the same price enricher (yfinance). Until a real closed sample exists, keep class `INSUFFICIENT_DATA` (already true). | `alpha_engine/bond_data_fred.py`, `alpha_engine/universal_price_enricher.py` (yfinance path). |
| All classes (survivorship) | Show headline metrics with the excluded count and the honesty-cleaned metrics (intrabar). Add n + binomial CI next to every WR. Cap/flag ±500%/−99% outlier PnL artifacts. | `audit_trail/dashboard_generator.py`, `alpha_engine/money_ready_verdict.py`. |
| Metrics/sources | Refresh kalshi snapshot from live API (or drop/re-label if stale); regenerate `strong_signals.json` (currently 404); populate FWD columns (or label `INSUFFICIENT` when `fwd_trades==0`); add `edge_ratio` back to main JSON or remove the UI element that reads it. | `alpha_engine/prediction_market_signals.py` (kalshi), `alpha_engine/strong_signals` builder, `audit_dashboard/` frontend. |
| Scheduling | Dashboard JSON regenerates on a cadence with `payload_lag_seconds≈4586`; the 5-min HTML meta-refresh reloads the same data. Align the build schedule to the price-quote refresh so "live" is actually fresh. | `.github/workflows/audit-dashboard.yml`, `audit-hourly-update.yml`. |

## Peer cross-validation (2026-11-14)

Converged with the peer audit (`audit/live-audit-2026-11-14`). Key additions now folded in:
- Crypto headline PF 9–18/WR 78–88% inflated by `claude_gainer_st` EXPIRED→WON mislabels;
  honest = pf_registry policy-clean-net PF 0.98/WR 39.7%, money_ready PF 0.96/WR 31.3%.
- Multiple-testing: 361 families + 285 baby + mutation lab ⇒ ~260 lucky PF>1.5 survivors expected
  at p=5%; anti-overfit 31/38 (82%) OVERFIT_LIKELY; CRYPTO z=−7.1, EQUITY z=1.39.
- `prediction_market_consensus` emitted XRPUSDT SHORT entry=0.0 (2026-11-14T13:54) — garbage row;
  kalshi snapshot ~7mo stale with null prices.
- Mutual funds unbuilt (`mutual_fund_ranker.py` / `mutual-funds.html` absent).
- Frozen scope: 1,147/1,882 closed dropped as spot-flicker artifacts; 3,509 FORCE_CLOSED_TOXIC;
  57 RESOLVE_FAILED_MAX_RETRIES; incubator BTC picks stuck at 0.

Tool upgraded: added `ACTIVE_RAW ZOMBIE SCAN` (per-class rows older than 7d / null price).
Live result: CRYPTO raw n=3,577 → 3,085 older than 7d, 3,170 null-price; FUTURES 10/13 old;
BOND 9/15 null-price.

## Verification

- `python3 -m pytest tests/test_pi_data_hygiene.py -q` → 12 passed.
- Guardian dry-run on live payload reproduces the audited defects (2 stale crypto, 11 phantoms, 3 date-only seeds) + zombie scan.
- No live pipeline files were modified; this change is additive tooling + docs.
