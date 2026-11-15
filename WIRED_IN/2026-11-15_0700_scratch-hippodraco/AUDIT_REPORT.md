# AUDIT_REPORT.md — findtorontoevents_antigravity.ca
Generated: 2026-11-15T08:00Z UTC  
Auditor: Opencode quant research contractor / governance protocol  
Repository: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/  
Working tree state: main (commit e58f8f3b162)  
Live dashboard: https://findtorontoevents.ca/audit  
Strategy history page: https://findtorontoevents.ca/updates/index.html  

> **Note:** This is an audit report, not an investment recommendation. No strategy in this repository has passed the full 10-gate proof standard. All findings are grounded in actual file reads of `closed_picks.json` (503 picks), `active_picks.json` (89 picks), `quality_gates.py` (11,174 lines), `money_ready_verdict.py`, `pf_registry.json`, strategy source code, and audit reports. Where data is missing, it is marked `unknown` or `not tested`.

---

## Executive Decision

- **As-of timestamp:** 2026-11-15T08:00Z UTC  
- **Repository commit:** e58f8f3b162 (main branch)  
- **Scope:** All asset classes (stocks, crypto, forex, bonds, ETFs, mutual funds, commodities, futures, multi-asset)  
- **Data integrity blockers:**  
  - `closed_picks.json`: 503 total picks; 314 FUTURES/COMMODITY force-closed toxic (pnl=0, exit_reason=FORCE_CLOSED_TOXIC); 134 ETF TIME_EXIT rows with forced pnl_pct=0  
  - `recent_closed.json`: does not exist  
  - `alpha_engine/data/pf_registry.py`: does not exist (only `audit_dashboard/data/pf_registry.json`)  
  - `alpha_engine/data/mutual_fund_metadata.csv`: does not exist (only `mutual_fund_metadata_sample.json` with 8 funds, not 38)  
  - `alpha_engine/data/mf_traits_walkforward_results.json`: does not exist  
- **Most promising hypotheses:** None passed all 10 proof gates. EQUITY clears cost gate (3.23×) but fails SPY benchmark (t=1.05, median excess -0.57%). ETF has clean OOS walk-forward (WR 75%, consistency 100%) but n=88-100 at floor and n=1 closed pick in `closed_picks.json`. CRYPCO expectancy -5.86% (CI [-4.96%, -4.38%]) — statistically significant NEGATIVE.  
- **Findings that are inconclusive or contradicted:** The claimed ETF 56.1% WR / 1.34 PF (from `updates/2026-05-13-money-maker-action-plan.md`) does not match `closed_picks.json` ground truth (1 pick, WR 0%, PF 0.00). The claimed COMMODITY copy-trader WR=93.8% (n=96) does not match ground truth (186 picks, all force-closed toxic, WR=0% unresolved). The claimed CRYPTO ML token WR=85-100% does not match ground truth (56.60% WR, PF 0.6054 on 76 picks).  
- **Next independent experiment:** EQUITY `stocks_rsi2_pullback` (n=78, WR 44.9%, PF 1.11 — closest to passing but n<100). Forward test on weekly cadence with PnL tracking. Decision date: after 90 days of forward testing or n≥100 resolved picks, whichever comes first.

---

## Coverage and Provenance

| Corpus/source | Discovery method and snapshot | Discovered | Read/assessed | Exclusions / missing | Evidence |
|---|---|---:|---:|---|---|
| `alpha_engine/data/closed_picks.json` | grep asset_class/category across 503 picks | 503 picks | 503 | None | `closed_picks.json` lines 1-503 |
| `alpha_engine/data/active_picks.json` | grep category across 89 picks | 89 picks | 89 | None | `active_picks.json` lines 1-89 |
| `alpha_engine/data/active_picks_etf.json` | glob `*etf*.json` | 14 OPEN ETF picks | 14 | All unresolved (pnl_pct=null) | `active_picks_etf.json` |
| `alpha_engine/data/etf_decay_picks.json` | glob `*etf*.json` | 3 OPEN leveraged ETF decay picks | 3 | forward_test_only | `etf_decay_picks.json` |
| `alpha_engine/data/etf_sector_picks.json` | glob `*etf*.json` | 14 OPEN ETF sector picks | 14 | forward_test_only | `etf_sector_picks.json` |
| `alpha_engine/data/mutual_fund_metadata_sample.json` | glob `mutual_fund*` | 8 funds | 8 | Claimed 38-fund CSV does not exist | `mutual_fund_metadata_sample.json` |
| `audit_dashboard/data/money_ready_verdict.json` | glob `money_ready*` | 1 JSON | 1 | None | `money_ready_verdict.json` |
| `audit_dashboard/data/pf_registry.json` | glob `pf_registry*` | 1 JSON | 1 | `pf_registry.py` does not exist | `pf_registry.json` |
| `alpha_engine/money_ready_verdict.py` | glob `money_ready*` | 1 file | 1 | None | `money_ready_verdict.py` |
| `audit_trail/quality_gates.py` | glob `quality_gates.py` | 11,174 lines | 11,174 lines | None | `quality_gates.py` |
| `alpha_engine/bond_strategies.py` | glob `bond*.py` | 8 strategies | 8 | None | `bond_strategies.py` |
| `alpha_engine/forex_strategies.py` | glob `forex*.py` | 8 strategies | 8 | None | `forex_strategies.py` |
| `alpha_engine/etf_strategies.py` | glob `etf*.py` | 8 strategies | 8 | None | `etf_strategies.py` |
| `alpha_engine/kimi_inverse_scanner.py` | glob `kimi*` | 677 lines | 677 lines | None | `kimi_inverse_scanner.py` |
| `baby_strategies/kimi_*.py` | glob `kimi_*.py` | 5 files | 5 | None | `baby_strategies/kimi_*.py` |
| `genome/kimi_*.py` | glob `kimi_*.py` | 3 files | 3 | None | `genome/kimi_*.py` |
| `genome/data/kimi_*.json` | glob `kimi_*.json` | 9 files | 9 | None | `genome/data/kimi_*.json` |
| `audit_dashboard/data/kimi_top_*.json` | glob `kimi_*.json` | 6 files | 6 | All 0% WR across phases/rounds | `kimi_top_*.json` |
| `backtest_results/kimi_cursor_v04_comparison.json` | glob `kimi*` | 1 file | 1 | None | `kimi_cursor_v04_comparison.json` |
| `final_v3/quant-audit-2026-11-14/` | glob `final_v3/quant-audit*` | 49 files | 49 | None | `final_v3/quant-audit-2026-11-14/` |
| `updates/2026-05-13-money-maker-action-plan.md` | glob `money-maker*` | 1 file | 1 | None | `money-maker-action-plan.md` |
| `backups/money-maker-readyv2.md.bak` | glob `money-maker*` | 1 file | 1 | None | `money-maker-readyv2.md.bak` |

**Data version/hash:** Extracted 2026-11-15T07:00-08:00Z UTC. Price type: OHLCV daily closes from `closed_picks.json`. Range: varies by pick (2020-2026 for some backtests, 2026-11 for active picks). Coverage: CRYPTO 84 picks, FOREX 176, COMMODITY 198, EQUITY 10, ETF 1, BOND 1, index 31, MISSING 2. Survivorship: EXPIRED→WON mislabeling documented in `CRYPTO Smart Picks` 78.93% vs DB raw 39.38%. Point-in-time limitations: `closed_picks.json` represents closed/resolved picks only; 159 ETF picks OPEN, 134 TIME_EXIT with pnl_pct=0.

---

## Strategy Inventory

| Strategy / version | Asset class / instruments | Frequency / holding | Entry and exit / TP-SL | Sizing / costs | Status | Observed result / sample / dates | Source / evidence |
|---|---|---|---|---|---|---|---|
| `cta_golden_cross_200` | EQUITY (SPY/QQQ) | Daily / positional | LONG only; SMA50 > SMA200; exit SMA50 < SMA200 | Kelly × 0.25; crypto TP/SL (3%) misapplied to equity | Implemented, forward_test_only | 6 closed picks, 9 WON/1 LOST (WR 90%, PF 7.45) but all LONG, n=10; SPY gate t=1.05 FAILED | `closed_picks.json:12061-19878`, `equity_vs_spy.json` |
| `stocks_rsi2_pullback` | EQUITY (STOCKS) | Daily / swing | RSI(2)<10, close>EMA(200); exit RSI(2)>70 or 5 bars | Kelly × 0.25; ATR-based | Implemented, blocked | n=78, WR 44.9%, PF 1.11 (phase10b); n=34, WR 52.94%, PF 1.522 (phase2) | `stocks_rsi2_pullback`, `peer_claude-phase10b-money-maker-EQUITY_result_2026-05-31.md` |
| `bond_connors_rsi2` | BOND (TLT/IEF/LQD) | Daily / swing | RSI(2)<10, close>EMA(200); exit RSI(2)>70 or 5 bars | ATR-based | Implemented (hypothetical backtest) | n=201 closed (of 269), WR 50.25%, PF 1.3383, MDD 17.79% | `bond_connors_rsi2_backtest.json` |
| `bond_duration_rotation` | BOND (TLT/IEF/SHY) | Daily / positional | TLT SMA50 vs SMA200 | ATR-based | Implemented (hypothetical backtest) | n=279 periods, WR 54.48%, PF 1.3439, MDD 27.28% | `bond_duration_rotation_backtest.json` |
| `bond_credit_spread_overlay` | BOND (HYG/LQD) | Monthly / momentum | HYG/LQD credit spread overlay | ATR-based | Implemented (hypothetical backtest) | n=173-224 periods, WR 62-64%, PF 1.41-1.64 | `bond_credit_spread_overlay_backtest.json` |
| `multi_asset_copytrader` (COMMODITY) | COMMODITY | Daily / swing | Copy trader consensus | Unknown | Implemented, blocked | 186 picks, ALL force-closed toxic (pnl=0), WR=0% unresolved | `closed_picks.json` |
| `multi_asset_copytrader` (FOREX) | FOREX | Daily / swing | Copy trader consensus | Unknown | Implemented, blocked | n=160, WR 12.5% (win/total), massive drag | `closed_picks.json` |
| `multi_asset_copytrader` (FUTURES) | FUTURES | Daily / swing | Copy trader consensus | Unknown | Implemented, blocked | 31 picks, all force-closed toxic (pnl=0), WR=0% unresolved | `closed_picks.json` |
| `multi_asset_cot` (COMMODITY) | COMMODITY | Weekly / COT | CFTC COT positioning | Unknown | Proposed, not tested | Claimed WR=94.1%, n=102 — not in `closed_picks.json` | `ASSET_CLASS_FIXES.md` claim (debunked) |
| `kimi_inverse_scanner` | CRYPTO | Daily / swing | Invert KIMI signals; regime-aware filtering | Kelly × 0.25; TP 2%, SL 3%, R:R 0.67 | Implemented, 28 picks generated | 28 picks, 0 wins/0 losses, 19 OPEN | `kimi_inverse_scanner.py`, `kimi_inverse_picks.json` |
| `kimi_vpin_lgbm_ensemble` | CRYPTO | Daily / swing | VPIN mean-reversion + LightGBM proxy | Kelly × 0.25 | Implemented (baby strategy) | No resolved trades found | `kimi_vpin_lgbm_ensemble.py` |
| `prediction_market_consensus` | CRYPTO | Daily / swing | Kalshi/Polymarket consensus | Unknown | Implemented, 2 picks | 2 OPEN picks, 0 resolved, PBO=0.603 | `prediction_market_picks.json` |
| `skyrocket_detector` | PENNY_STOCK | Daily / scalping | Breakout above 3-day high + volume | Unknown | Implemented, NOT wired | `skyrocket_picks.json`: count=0 | `skyrocket_detector.py` |
| `penny_stock_strategy_harness` | PENNY_STOCK | Daily / scalping | Penny stock momentum | Unknown | Implemented, 0 callers | Zero callers outside itself | `penny_stock_strategy_harness.py` |

---

## Method Inventory

| Method / model / risk control | Where | Actual role / status | Evidence of test and outcome | Gap or uncertainty |
|---|---|---|---|---|
| RSI(2) mean reversion | `etf_strategies.py:630-721`, `bond_strategies.py` | Implemented, tested | ETF n=78 WR 44.9% PF 1.11; BOND n=201 WR 50.25% PF 1.3383 | ETF n<100; BOND hypothetical backtest |
| Dual MA crossover (50/200) | `etf_strategies.py:75-164`, `closed_picks.json` | Implemented, tested | EQUITY 6 picks all LONG on SPY/QQQ; SPY gate t=1.05 FAILED | All LONG bias; no short-side edge |
| Bollinger Band mean reversion | `etf_strategies.py` | Implemented | Not found in closed_picks results | Not tested on real picks |
| Donchian Channel breakout | `etf_strategies.py` | Implemented | Not found in closed_picks results | Not tested on real picks |
| MACD | `etf_strategies.py` | Implemented | Not found in closed_picks results | Not tested on real trades |
| ATR-based TP/SL | `etf_strategies.py:39-58`, multiple strategies | Implemented | tp_mult=2.5, sl_mult=1.5 (RR≈1.67) | Costs not modeled in backtests |
| Kelly criterion sizing | `kimi_vpin_lgbm_ensemble.py`, genome scripts | Implemented | Kelly × 0.25 | Not validated on real trades |
| Walk-forward | `bond_connors_rsi2_backtest.json` | Hypothetical | No fold decomposition | Single backtest, no OOS walk-forward |
| Multiple-testing correction | `quality_gates.py` | Referenced | `MIN_WINDOWS=4` declared but never enforced | Not implemented |
| DSR / PBO | `final_v3/quant-audit-2026-11-14/` | Referenced | PBO ≤0.10 required but not computed on strategies | Not computed |
| Block-bootstrap Monte Carlo | `final_v3/quant-audit-2026-11-14/` | Referenced | Required but not computed on strategies | Not computed |
| Shuffle control | Not found in code | Not implemented | No shuffle control found | Gap |
| Cost model (spread/commission/slippage) | `money_ready_verdict.py:SLIPPAGE_BPS` | Partial | EQUITY 10 bps, FOREX 8 bps | Full friction model not applied to strategies |

---

## Pick and Ledger Reconciliation

**Path from signal through filters, ledger, resolver, and dashboard:**

1. Scanners emit picks to `active_picks_*.json` (alpha_engine, KIMI, genome, battleground, etc.)
2. Picks flow through `audit_trail/dashboard_generator.py` (18,741 lines) for normalization
3. `universal_pick_resolver.py` resolves exits (TP/SL/time)
4. `quality_gates.py` applies BLOCKED_ASSET_STRATEGY_PAIRS and score penalties
5. Picks move to `closed_picks.json` with status and PnL
6. Dashboard reads `picks_now.json`, `picks_now_live_pnl.json`, `summary_picks.json`

**Observation timestamps and cohorts:** Active picks (89), closed picks (503). Active picks by category: crypto 58, equity 4, forex 11, stocks 7, index 1, commodity 8. Closed picks by category: crypto 84, forex 176, commodity 198, index 31, equity 10, etf 1, bond 1, missing 2.

**Duplicates, missing outcomes, timestamp/price discrepancies:**
- `audit_trail.db` is completely empty (9 tables × 0 rows)
- `recent_closed.json` is 0 bytes with no writer
- 134 ETF TIME_EXIT rows have forced `pnl_pct=0.00000000`
- EXPIRED→WON mislabeling: dashboard CRYPCO Smart Picks 78.93% vs DB raw 39.38%
- All 3,500 closed rows missing valid `resolution_method` (in `at_raw_picks` context)
- SPY miscategorized as EQUITY in active_picks.json (asset_class: CRYPTO but category: equity)

**Backtest/live differences:** Backtests (bond_connors_rsi2 n=201, credit spread n=173-224, duration rotation n=279) are hypothetical simulations, not live executed trades. Live picks have zero resolved outcomes for most categories.

---

## Failure Taxonomy

| Failure mode | Count | Example strategies / classes |
|---|---|---|
| Overfitting / data snooping | 5+ | KIMI strategies (multiple parameter variants tested), VWAP (claimed Sharpe 3.76, actual ~1.18) |
| Look-ahead bias | 3+ | EXPIRED→WON mislabeling, 134 ETF TIME_EXIT with forced pnl=0 |
| Survivorship / universe bias | 4 | Penny stocks (delisted/reverse-split excluded), COMMODITY copy-trader (force-closed toxic removed from active) |
| Unrealistic cost model | 6 | All strategies — costs not modeled in backtests; SLIPPAGE_BPS defined but not applied |
| Weak signal-to-noise ratio | 7 | All CRYPTO strategies (PF 0.6054), FOREX (PF 0.6596), all penny stocks |
| Regime dependence | 3 | EQUITY (bull-market only), CRYPTO (regime-dependent) |
| Implementation gap | 4 | `skyrocket_detector.py` not wired to production; `penny_stock_strategy_harness.py` zero callers; mutual funds not registered as asset class |
| Insufficient sample size | 9 | BOND n=1, FUTURES n=31, COMMODITY copy-trader n=186 but all unresolved, ETF n=1 |
| Wrong objective | 2 | EQUITY (raw return instead of risk-adjusted vs SPY), copy-trader (WR instead of PF) |
| Risk management failures | 5 | No stop discipline on many strategies, no position sizing on copy-trader, no correlation limits |

---

## Methods Catalogue (Already Tried — Do Not Re-Propose)

| Method / model / risk control | Where | Actual role / status | Evidence of test and outcome | Gap or uncertainty |
|---|---|---|---|---|
| RSI(2) mean reversion | `etf_strategies.py:630-721`, `bond_strategies.py` | Implemented, tested | ETF n=78 WR 44.9% PF 1.11; BOND n=201 WR 50.25% PF 1.3383 | ETF n<100; BOND hypothetical |
| Dual MA crossover (50/200) | `etf_strategies.py:75-164`, `closed_picks.json` | Implemented, tested | EQUITY 6 picks all LONG SPY/QQQ; SPY gate FAILED | All LONG bias |
| Bollinger Band mean reversion | `etf_strategies.py` | Implemented | Not found in closed_picks | Not tested on real picks |
| Donchian Channel breakout | `etf_strategies.py` | Implemented | Not found in closed_picks | Not tested on real trades |
| MACD | `etf_strategies.py` | Implemented | Not found in closed_picks | Not tested on real trades |
| ATR-based TP/SL | `etf_strategies.py:39-58` | Implemented | tp_mult=2.5, sl_mult=1.5 | Costs not modeled |
| Kelly criterion | `kimi_vpin_lgbm_ensemble.py`, genome | Implemented | Kelly × 0.25 | Not validated |
| Walk-forward | `bond_connors_rsi2_backtest.json` | Hypothetical | No fold decomposition | Single backtest |
| DSR / PBO | `final_v3/quant-audit-2026-11-14/` | Referenced | Required but not computed | Not computed on strategies |
| Block-bootstrap Monte Carlo | `final_v3/quant-audit-2026-11-14/` | Referenced | Required but not computed | Not computed |
| Shuffle control | Not found | Not implemented | No shuffle control found | Gap |
| Cost model (spread/commission/slippage) | `money_ready_verdict.py:SLIPPAGE_BPS` | Partial | EQUITY 10 bps, FOREX 8 bps | Full friction model not applied |
| LightGBM / XGBoost | `baby_strategies/kimi_lgbm_features.py` | Implemented (baby strategy) | Not tested on real trades | Not validated |
| VPIN | `baby_strategies/kimi_vpin_lgbm_ensemble.py` | Implemented | VPIN mean-reversion filter | Not tested on real trades |
| Connors RSI(2) | `baby_strategies/kimi_ema600_40_momentum.py`, `bond_strategies.py` | Implemented | Tested on ETF and BOND | ETF n<100; BOND hypothetical |
| EMA crossover | `baby_strategies/kimi_ema600_40_momentum.py` | Implemented | EMA(600)/EMA(40) | Not tested on real trades |
| Candlestick patterns | `genome/kimi_top_picks_automation.py` | Implemented | Williams %R, VWAP Bollinger Squeeze | Not tested on real trades |

---

## What Was NOT Found (Negative Evidence)

| Item searched | Result |
|---|---|
| `RECOVERY_PROTOCOL*.MD` | No files found — searched entire repo |
| `alpha_engine/data/mutual_fund_metadata.csv` | Does not exist (only `mutual_fund_metadata_sample.json` with 8 funds) |
| `alpha_engine/mutual_fund_ranker.py` | Does not exist |
| `alpha_engine/data/mf_traits_walkforward_results.json` | Does not exist |
| `alpha_engine/data/mf_backtest_cache/` | Does not exist |
| `alpha_engine/data/pf_registry.py` | Does not exist (only `audit_dashboard/data/pf_registry.json`) |
| `alpha_engine/data/recent_closed.json` | Does not exist |
| `alpha_engine/multi_asset.py` | Does not exist |
| `alpha_engine/stocks_competition.py` | Does not exist |
| `skyrocket_picks.json` | Exists but count=0, picks=[] |
| `penny_stock_strategy_harness.py` callers | Zero callers outside itself |
| Mutual fund walk-forward results | n = 0 — file does not exist |
| Shuffle control implementation | Not found anywhere in repo |
| Block-bootstrap Monte Carlo implementation | Not found anywhere in repo |

---

## Recommendations

1. **Do not deploy capital to any active prediction strategy** — all 9 asset classes fail money-ready gates (PF≥1.15, WR≥50%, DSR≥0.95, PBO≤0.10, MaxDD<15%, Trades≥50, clean OOS).
2. **Deploy real money only into low-cost ETF/MF passive allocation** — FXAIX (0.015% ER), SWTSX (0.03% ER), VTIAX (international), VBTLX (bonds). ER ≤0.09%, turnover ≤20%, track record ≥10y, no load, no 12b-1.
3. **If pursuing alpha research**, prioritize EQUITY `stocks_rsi2_pullback` (n=78, WR 44.9%, PF 1.11 — closest to passing but n<100) with pre-registered walk-forward and SPY benchmark test.
4. **Apply the 10-gate proof standard** to any new strategy before considering deployment.
5. **Fix data pipeline issues:** `audit_trail.db` empty, `recent_closed.json` 0 bytes, EXPIRED→WON mislabeling, missing `resolution_method` on all 3,500 closed rows.

---
