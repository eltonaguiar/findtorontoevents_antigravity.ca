# 2026-06-02 — EAGLE-6 v2 Windowed HHI gate: PASS=0, FAIL=17 — backtest self-confirmation

## TL;DR
Implements **ENHANCEMENT_OVERALL #108** (windowed-HHI). For each of the 19 WF OOS + bootstrap CI candidates, computes HHI over a rolling 50-pick window of `source_system` labels. **Verdict: PASS=0, BORDERLINE=0, FAIL=17, INSUFFICIENT=2.**

**None of the 9 bootstrap CI PASS strategies survive the 4-gate cascade.** They are all reflections of a single `alpha_engine` system — the same code that produces the picks is also validating them. This is the classic backtest self-confirmation failure.

## What was generated
- `tools/build_windowed_hhi_results.py` (new, ~165 lines) — standalone, consumes WF OOS or bootstrap CI results
- `tools/windowed_hhi_results.json` (new, 453 lines) — per-strategy whole-HHI, rolling HHI pass%, max window HHI, verdict
- **PR #485** opened: `docs/windowed-hhi-results-2026-06-02` branch, 2 files, all mine

## Method
- For each candidate strategy, query the `source_system` label for every closed pick, ordered by `closed_at`
- Compute HHI = `sum(share^2)` over a moving window of last 50 picks
- Verdict: **PASS if HHI<0.20 in ≥80% of windows**; BORDERLINE 50-80%; FAIL <50%; INSUFFICIENT if n<50

## Result
**EAGLE-6 v2 Windowed HHI gate: PASS=0, BORDERLINE=0, FAIL=17, INSUFFICIENT=2 (total=19)**

### Whole-history HHI distribution
| HHI bucket | Strategies |
|---|---|
| 1.0 (single source) | 14 — all 100% from `alpha_engine` |
| 0.84–0.92 (`alpha_engine` + `battleground`, `alpha` dominates) | 5 — `crypto_liquidity_wick_reversal_v1`, `ensemble` (x2), `drawdown_recovery_rsi_xrp` |
| INSUFFICIENT (n<50) | 2 — `reddit:Gr33nHatt3R`, `rsi_vwap_contrarian` |

### Bootstrap CI PASS strategies — all FAIL windowed HHI
| Strategy | n | sources | whole HHI | pass% (HHI<0.20) |
|---|---|---|---|---|
| `crypto_liquidity_wick_reversal_v1` | 4718 | 2 | 0.9176 (α 95.7%, bg 4.3%) | 0.0% |
| `prediction_market_consensus` | 620 | 1 | 1.0 | 0.0% |
| `drawdown_recovery_rsi_xrp` | 442 | 2 | 0.9054 (α 95%, bg 5%) | 0.0% |
| `rsi_overbought` | 295 | 1 | 1.0 | 0.0% |
| `B_flip_PriceRocMeanReversion` | 157 | 1 | 1.0 | 0.0% |
| `fx_smart_carry_trade_momentum` | 134 | 1 | 1.0 | 0.0% |
| `ml_crypto_pred` | 79 | 1 | 1.0 | 0.0% |
| `claude_ml_moderate_mut` | 67 | 1 | 1.0 | 0.0% |
| `inverse_ml_enhanced_BTCUSDT_15m_D` | 65 | 1 | 1.0 | 0.0% |

## 4-gate cascade final
| Gate | Result | Threshold | PR |
|---|---|---|---|
| PBO (portfolio-level) | PBO=1.0 FAIL | <0.5 | #471 ✅ |
| WF OOS (per-strat robustness) | 18 PASS | OOS_PF ≥ 0.8 × IS_PF, folds≥3 | #473 ✅ |
| Bootstrap CI (per-strat statistical) | 9 PASS | pf_lo_95 > 1.0 | #481 ⏳ |
| **Windowed HHI (per-strat diversification)** | **0 PASS** | HHI<0.20 in ≥80% of 50-pick windows | #485 ⏳ |

## Why v1 missed this
EAGLE-6 v1's HHI (`_compute_source_hhi` in `alpha_engine/eagle_gates.py`) is computed over the **active pick universe** (`hhi_universe = list(picks)` at line 324). If the active universe has 50 strategies, HHI is computed across those 50 — even if each individual strategy's history is 100% from one source. v2 measures each strategy's own source concentration over time, which catches the backtest self-confirmation pattern.

## Implication
**The bootstrap CI PASS list is statistically sound but undiversified.** The right action is to either:
1. Get a 2nd independent source_system generating signals (highest priority)
2. Add cross-validation by holding out source_system during WF
3. Accept that the strategies are reflections of one codebase and size accordingly (no 2nd-source diversification benefit)

**Forward-test list revision**: zero strategies should be promoted to live trading without a 2nd source_system. The previous list of 5 (PR #482) is now demoted to **'paper-watch only'** until a 2nd source is in place.

## Reproduce
```bash
DB_PASS_STOCKS=$DB_PASS_STOCKS python3 tools/build_windowed_hhi_results.py
# -> PASS=0 BORDERLINE=0 FAIL=17 INSUFFICIENT=2 -> tools/windowed_hhi_results.json
```

## Refs
- `ENHANCEMENT_OVERALL #85` (EAGLE-6 v2 gates), `#108` (windowed HHI)
- `alpha_engine/eagle_gates.py:235-252` (`_compute_source_hhi`)
- PR #471 (PBO=1.0), #473 (WF OOS 18 PASS), #481 (bootstrap CI 9 PASS), #482 (suspicious pass investigation), #485 (this)

## Action items
- [ ] **Highest priority**: integrate a 2nd independent source_system (different codebase, different data feed). Until then, NO live trading on these strategies.
- [ ] Update `ENHANCEMENT_OVERALL #85` with 4-gate cascade result: only strategies that pass ALL 4 (PBO<0.5, WF OOS, bootstrap CI, windowed HHI) should be promoted. Currently 0/56.
- [ ] Update `ENHANCEMENT_OVERALL #108` status: IMPLEMENTED, with `linked_pr=#485`.
