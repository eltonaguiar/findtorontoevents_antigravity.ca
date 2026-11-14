# EQUITY (Stocks) Quick Wins
Audit: §4.1 — published `performance` PF **8.86 on n=8** vs recomputed window PF 1.15 (n=738, WR 47.0%, +238.3) vs intrabar PF 0.94 / WR 59.2% (n=250) **NOT_READY**. Equity is the closest class to viable — and the most misreported.

## QW-EQUITY-1 · Kill the n=8 PF 8.86 headline (S, <2h) — do first
- **Problem:** `performance.by_asset_class.EQUITY.closed=8` feeds a PF that contradicts the 738-row window and the 250-row intrabar ledger. Three ledgers, three answers (also BOND, ETF).
- **Fix:** Minimum-n rule at render: class cards with closed n<30 show `INSUFFICIENT_DATA` instead of PF/WR (the `money_ready_verdicts` logic already knows how); point the card at the intrabar ledger as primary.
- **Verify:** Equity card shows intrabar n=250 PF 0.94 (or INSUFFICIENT_DATA), never 8.86.

## QW-EQUITY-2 · One stats module, one ledger (M)
- **Problem:** `performance`, `asset_class_summary` and `recent_closed` are computed by independent paths in `dashboard_generator.py` (summary ~:14787-14902, per-class panels elsewhere) — they cannot reconcile by construction.
- **Fix:** Single per-class stats function fed by the canonical valid-closed list (`_filter_valid_resolved_picks`), used by every surface; delete independent recounts. Include n, WR, PF, expectancy, and the ledger name on every card.
- **Verify:** Contract test: card PF == recomputed PF from the same payload's closed rows (tolerance 0.01) for every class.

## QW-EQUITY-3 · Equity price-cache TTL (S)
- **Problem:** `stock_prices.json` cache has **no age check** (generator `:1505-1615`); if `fetch_stock_prices.py` CI dies, prices are silently days old; fallback is FMP `apikey=demo`; prices rounded to 2dp (`fetch_stock_prices.py:21-23`) destroying penny-stock precision.
- **Fix:** Stamp cache with `fetched_at`; generator ignores entries older than 1 trading day and marks picks `price_stale:true` (excluded from live PnL, shown as `—` per QW-ALL-7); keep full float precision.
- **Verify:** Fixture cache aged 3d → picks render `—`, not stale PnL; penny ticker retains >2dp.

## QW-EQUITY-4 · Dividends/distributions in equity PnL (M, after QW-ALL-2)
- **Problem:** Price-only PnL (`forward_validator.py:1376-1378`) understates long equity holds (and BOND/ETF — shared fix). With expectancy near zero, distributions decide sign for dividend names.
- **Fix:** Quick subset: for holds spanning an ex-div date, add cash dividend per share to exit proceeds (yfinance dividend history already available in the equity lane); flag `pnl_includes_distributions:true`.
- **Verify:** Known dividend payer fixture spanning ex-date matches total-return calc.

## Subagent-refined (verified file:line, supersedes estimates above where they differ)
- **QW-EQUITY-1 mechanics:** in `ac_breakdown` finalisation (`dashboard_generator.py:15482-15492`) add `closed_n` + `stats_basis`, null PF/WR when `closed<100` (matches existing `min_stable_n=100` at `:5935-5937`); stamp intrabar from `enrich_health_with_intrabar_sizing` (`:6051-6111`, preferred at `ib_n>=30` `:6093`); same rule in `_registry_backed_ac_breakdown` (`:5826-5913`). Verify with `tools/build_intrabar_truth_by_class.py --stdout` vs payload.
- **QW-EQUITY-3 cache TTL concretised:** cache writer already stamps `updated_at` (`fetch_stock_prices.py:101-105`) — enforce 4h max age in `_fetch_equity_prices` (`dashboard_generator.py:1505-1539`), fall through to yfinance; stamp `price_stale:true` at the `continue` (`:1752-1755`). The writing CI step is `.github/workflows/audit-dashboard.yml:163-168`.
- **Remove `apikey=demo` FMP fallback (S, 1h):** `dashboard_generator.py:1599` hardcodes `apikey=demo`; mirror `fetch_stock_prices.py:31-33` (`FMP_API_KEY` env, skip when unset). Verify: `grep -rn "apikey=demo" audit_trail/ alpha_engine/` = 0.
- **Price precision (S, 1h):** `fetch_stock_prices.py:23` `round(...,2)` → `round(...,4)` (resolver already keeps 8dp at `universal_pick_resolver.py:876-884`). A $0.35 stock at 2dp carries ~1.4% price error straight into PnL.
- **Classifier parity contract test (M, 1–2d):** three classifiers (`asset_class.py:130-260`, `config.py:1087-1134`, generator `_derive_asset_class :3407`). Add `tests/test_asset_class_parity.py` pinning AAPL/SPY/TLT/EURUSD/ZN=F/VFIAX→UNKNOWN; make `detect_asset_class` delegate known-symbol branches and end at `unknown`, not equity-by-shape (`config.py:1127,1131`). Run with `tests/test_dashboard_asset_class_hints.py`, `test_derive_asset_class_precedence.py`, `test_outcome_resolver_asset_class_persist.py`.

## QW-EQUITY-5 · Significance honesty (S)
- **Problem:** Equity edge z≈1.39 (<1.96) in prior statistical audit; `backtest_vs_forward` shows backtest heroes with `fwd_trades=0` (e.g. `connors_rsi2` BT WR 68.8%).
- **Fix:** Class card displays forward n + a plain `edge not statistically significant (z=…)` line until z≥1.96 on intrabar data; backtest verdicts hidden when fwd_trades=0.
- **Verify:** Card shows z and forward n; zero-forward strategies carry no SURVIVOR badge.
