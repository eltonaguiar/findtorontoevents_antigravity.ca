# WIRED_IN: scratch-hippodraco Research & Findings

**Date-time:** 2026-11-15T0657Z  
**Worktree:** scratch-hippodraco  
**Branch:** main (committed to origin/main)  
**Status:** Complete research audit — no profitable asset class found without further validation

---

## Folder Structure

| Subfolder | Contents |
|-----------|----------|
| `spec/` | Algorithmic code: PnL pipeline, QA validator, MF screener, simulation monitor, E2E integration test, benchmark builders |
| `picks/` | Pick justification documents (empty — no picks passed all gates) |
| `research/` | Backtesting methodology, MF screening results, audit reports, update summaries |
| `elimination/` | Elimination rationale per asset class (from prior peer session) |
| `peers/` | Peer-reviewed scratch-hippodraco session notes (from `2026-11-15T0130Z_scratch-hippodraco`) |

---

## Executive Summary

**No asset class in this repository currently passes all statistical validity gates for profitable trading.** After comprehensive review of all committed code, audit data, and peer-reviewed sessions:

| Asset Class | n | WR | PF | MDD | Status | Primary Blocker |
|-------------|-----|-----|-----|-----|--------|-----------------|
| EQUITY | 250 | 59.2% | 0.94 | 33.04% | NOT_READY | PF < 1.5; MDD > 20%; bootstrap CI crosses zero |
| CRYPTO | 3,705 | 35.9% | 0.92 | N/A | NOT_READY | WR < 50%; PF < 1.5 |
| FOREX | 612 | 32.2% | 0.66 | N/A | NOT_READY | WR < 50%; PF < 1.5 |
| COMMODITY | 229 | 40.2% | 1.03 | N/A | WATCH | n < 100; PF < 1.5 |
| FUTURES | 52 | 42.3% | 1.09 | N/A | INSUFFICIENT_DATA | n < 100 |
| BOND | 1 | 0.0% | 0.0 | N/A | INSUFFICIENT_DATA | n = 1 |
| ETF | 45 | 2.2% | 0.02 | N/A | INSUFFICIENT_DATA | n < 100; PF ≈ 0 |
| MUTUAL_FUNDS | - | - | - | N/A | NOT_A_CLASS | Not registered (class id = -1) |
| PENNY_STOCK | 4 | 0.0% | 0.18 | N/A | INSUFFICIENT_DATA | n = 4 |
| MEME | 10 | 0.0% | 0.02 | N/A | INSUFFICIENT_DATA | n = 10 |

**Key finding:** EQUITY has the highest win rate (59.2%) but fails on PF (0.94 < 1.5), MDD (33.04% > 20%), and bootstrap CI crossing zero. No class passes all T2 gates.

---

## Root Causes Identified

1. **851 active picks have no current_price** → shows as 0% PnL, corrupting aggregate metrics
2. **25.5% of EQUITY picks have pnl_pct=0** → missing exit prices or stale data
3. **CRYPTO has genuine negative expectancy** (61.4% losses) — strategy issue, not data issue
4. **No class has n ≥ 100 AND PF ≥ 1.5 AND WR ≥ 50%** simultaneously
5. **Multiple testing not corrected** — 27+ parameter combos tested without Bonferroni correction
6. **No walk-forward out-of-sample validation** on any strategy

---

## Key Files in This Folder

### `spec/` — Production Code

| File | Purpose |
|------|---------|
| `pick_pipeline.py` | Per-asset-class pick generation with cost model, resolver integration |
| `risk_qa_validator.py` | QA validation: PnL=0% detection, blank-field flags, reasonability checks |
| `mf_screener.py` | Mutual fund passive allocation screener (9 hard gates) |
| `run_simulation_monitor.py` | Live simulation candidate monitoring |
| `e2e_integration_test.py` | End-to-end integration test (pick → QA → forward test) |
| `build_benchmark_prices.py` | Benchmark price builder |
| `build_forward_clock.py` | Forward clock builder |
| `pick_excess.py` | Pick excess analysis |
| `pm_binary.py` | Prediction market binary classifier |

### `research/` — Analysis Outputs

| File | Contents |
|------|----------|
| `profitability-plan-execution.md` | Session summary: all code, tests, conclusions |
| `mf_screening_results.json` | MF screener results (2/8 funds pass) |
| `mf_screening_report.html` | HTML screening report |
| `mutual_fund_metadata_sample.json` | Sample MF metadata (8 funds) |
| `forward_tracker.py` | Forward-test tracker (QA-gated pick logging) |

### `peers/` — Prior Peer Session (2026-11-15T0130Z)

Copied from `WIRED_IN/2026-11-15T0130Z_scratch-hippodraco/`:
- `spec/` — Per-asset-class specifications (EQUITY, ETF, CRYPTO, FOREX, COMMODITY_FUTURES, BOND, MUTUAL_FUNDS)
- `picks/` — Pick justification document
- `research/` — Backtesting methodology and results
- `elimination/` — Elimination rationale per asset class

---

## Recommended Next Steps

### Immediate (P0 — 1–3 days)
1. **Fix data integrity**: Backfill `current_price` for 851 active picks; resolve `exit_price` for 49 zombie rows
2. **Run full QA validator** on all 3,500 recent closed picks
3. **Run equity momentum strategy** (`stocks_rsi2_pullback`) through full pipeline: QA → forward test → monitor

### Short-term (P1 — 1–2 weeks)
1. **Expand ETF universe** (XLF, XLE, XLK) to reach n ≥ 100
2. **Backfill CRYPTO OHLCV** to ≥180 days 1h bars for intrabar replay
3. **Run walk-forward analysis** on EQUITY strategies with proper multiple-testing correction

### Medium-term (P2 — 2–4 weeks)
1. **Promote only classes that clear T2 gates** on fresh OOS data (≥6 months, ≥100 trades)
2. **Size at ¼ Kelly** with DD-halt rules
3. **Monitor via separate risk dashboard** (separate from picks dashboard)

---

## Success Criteria (T2 Gates — ALL must pass)

| Metric | Threshold |
|--------|-----------|
| Profit Factor (post-cost) | ≥ 1.5 |
| Win Rate (EXPIRED-inclusive) | ≥ 50% |
| Max Drawdown | ≤ 20% |
| n resolved (forward/OOS) | ≥ 100 |
| Sharpe (annualized) | ≥ 1.0 |
| Beat SPY total return | Yes |

---

## Files NOT in This Folder (Separate Commits)

- `tools/e2e_integration_test.py` — End-to-end integration test
- `tools/run_simulation_monitor.py` — Simulation candidate monitor
- `alpha_engine/pick_pipeline.py` — Per-asset-class pick pipeline (modified)
- `alpha_engine/risk_qa_validator.py` — QA validator (modified)
- `alpha_engine/mf_screener.py` — Mutual fund screener (modified)
- `updates/2026-11-15-profitability-plan-execution.md` — Full session summary

---

**Bottom line:** No statistically valid, costed, out-of-sample profitable edge exists in any asset class today. EQUITY is the closest candidate but requires significant data remediation and forward validation before any capital deployment.
