# README — final_v001 Consolidated Quant Research Audit

**Worktree:** flaxen-hair | **UTC:** 2026-11-15T0741 | **Repo:** findtorontoevents_antigravity.ca
**Status:** FINAL — consolidates all prior WIRED_IN worktrees, code changes (24–48h), and proof-standard research.

---

## THE HONEST VERDICT

**No asset class has a statistically valid, provable profitable algorithm today.**

- **0 / 23 hypotheses** survived clean out-of-sample + effective-N + capital + execution gates.
- **0 / 42** strategy-symbol backtest combinations pass the P0 gate set (all have n < 12; minimum is n ≥ 100).
- **All 9 asset classes** return `sizing_allowed: false`.
- **Every recent pick** (41 in `multi_asset_picks.json`) is `forward_test_only=true` with `pnl_pct=null` — there is no verifiable live PnL anywhere.

This is a **negative result**, not a failure. It is the most valuable thing the repo now owns: it stops the years-long loop of re-running the same dead strategies.

---

## WHAT THIS FOLDER CONTAINS

| Folder / File | Contents |
|---|---|
| `PRE_PROMPT.md` | The exact prompt this work responds to (self-engineering + proof standard) |
| `01_asset_class_plans/` | Per-asset-class profitability plans, ranked by realistic probability |
| `02_holding_period_analysis/` | Holding period vs trading style; forward-test kill/promote protocol |
| `03_proven_algorithms/` | Algorithms from TradingView contests; verified-as-unproven catalogue |
| `04_subq_decision_support/` | SubQ fact-check protocol; why prediction-market copy trading fails |
| `05_framework_answers/` | The 6 framework questions answered |
| `06_essential_questions/` | 12 questions every candidate must answer |
| `07_company_turnarounds/` | How Renaissance/Two Sigma/AQR/Bridgewater/Citadel got trustworthy |
| `08_key_metrics/` | Proof metrics from 5 stakeholder perspectives |

---

## ASSET-CLASS VERDICT MATRIX

| Asset Class | Best Backtest | n | Verdict | Closest Path to Proof |
|---|---|---|---|---|
| **EQUITY (US)** | PF 1.52, WR 56.9%, Sharpe 1.19 | 130 | **SLOT 1 — most promising** | Pre-registered test vs SPY total return: n≥500, PF≥1.15, stability both halves |
| **ETF** | PF 1.93, WR 69.0%, Sharpe 1.66 | 71 | PROMISING (underpowered) | Expand universe to ~20 liquid ETFs; TAA smart-beta (not alpha) |
| **CRYPTO** | PF 1.86, WR 58.3%, Sharpe 0.27 | 12 | CONDITIONAL | Fix entry_price integrity (~29% clean) → forward-test n≥100 |
| **FOREX** | PF 0.97, WR 56% | 350 | BLOCKED | Zero DSR survivors; mutation-before-kill only |
| **COMMODITY** | PF 4.51 (GLD ema_stack) | 10 | BLOCKED | n=27 post-filter < 60 minimum |
| **BOND** | PF 0.66 | 11–18 | BLOCKED | n far below min_trades=60 |
| **FUTURES** | WR 5.9%, PnL −96% | 0 | DEAD | Formal retirement |
| **MUTUAL FUNDS** | — | 0 | ZERO COVERAGE | Build NAV infra OR hold low-cost index funds (beta, not alpha) |
| **MEMECOIN** | PF 0.50 | 1,869 | QUARANTINED | Keep blocked |
| **PENNY** | — | 8 | BLOCKED | Gate 0 fail |

**The one approach with validated risk-adjusted value:** ETF Tactical Asset Allocation (TAA) — Sharpe 0.88 vs SPY 0.74, MaxDD −19% vs SPY −51%, Calmar 0.48 vs 0.21, validated 2007–2026 including 2008 GFC. **This is smart-beta / drawdown reduction, NOT alpha.** It is the honest core portfolio while alpha research continues.

---

## THE FINALIZED STRATEGY (what to actually do)

### Track A — Deploy the boring, provable thing (NOW)
Low-cost, diversified ETF/mutual-fund allocation with disciplined rebalance. Measurable, defensible expected outcome. Benchmark is explicit (SPY total return + a 60/40 blend). This is what a serious investor can trust today.

### Track B — Prove or kill EQUITY (the only real alpha candidate)
Run the pre-registered test: Connors RSI2 + VIX spike reversal on SPY/QQQ.
- **Gate:** n≥500, PF≥1.15, OOS Sharpe ≥ SPY Sharpe, half-over-half PF ≥ 1.05 both halves.
- **Kill condition:** fails any line → EQUITY is just beta; stop emitting, hold index.

### Track C — Fix then test CRYPTO (conditional)
1. Fix entry_price integrity (currently ~29% clean; 37% >10% off bar).
2. Re-resolve from bar-aligned NEXT-bar entries.
3. Forward-test POSITION horizon only, n≥100, PF≥1.3, WR≥55%.

### Do NOT do
- Do not tune COMMODITY COT until it passes (4/4 pre-registered checks already failed).
- Do not add MUTUAL FUNDS as a prediction class (it is the equity risk premium, not a signal).
- Do not mine more strategies (170 ledgers sampled; 4 pass at 95% vs 8.5 by chance).
- Do not deploy capital on any forward-test-only pick.

---

## THE 10-GATE PROOF STANDARD (any future claim must pass ALL)

1. **Data purity** — chronological split; features from past data only.
2. **Walk-forward** — embedded OOS windows; report WFE.
3. **Multiple-testing correction** — state total trials project-wide; Deflated Sharpe / White's Reality Check; Bonferroni/Holm.
4. **Monte Carlo** — block-bootstrap; % paths positive after costs + 5th-percentile worst case.
5. **Friction model** — spread + commission + slippage + funding/borrow + tax; report breakeven cost + margin of safety.
6. **Significance** — bootstrap CI for mean excess return excludes zero; t-stat + p-values.
7. **Regime robustness** — bull/bear/sideways, high/low vol; positive expectancy in most regimes.
8. **Shuffle control** — permuted prices must NOT reproduce performance.
9. **Pre-registered forward test** — frozen rules, duration, decision thresholds BEFORE results.
10. **Reproducibility** — fixed seeds, versioned data, documented formulas, runnable code.

---

## CRITICAL BUGS FOUND (fix before ANY metric is trusted)

| Bug | Severity | Evidence |
|---|---|---|
| PnL unit mismatch (ratio vs percent, up to 100×) | CRITICAL | `multi_asset_closed.json`, `institutional_closed.json` |
| Non-unique pick IDs (date-only) | HIGH | `vix_reversal::SI=F::2026-03-11` ×4 |
| Stale OPEN picks | HIGH | `institutional_picks.json` 22 picks dated 2026-04-03 |
| `ml_score == confidence` coupling | MEDIUM | every OPEN pick (0.75==0.75 etc.) |
| `recent_picks.txt` header lies ("Past 2 Hours" but 2026-03-11) | MEDIUM | 8 months stale |

**dbpasses.txt** lives at `/home/eaguiar2015/dbpasses.txt` (outside repo, live keys — never read/expose/commit).

---

## REPRODUCTION

```bash
# Normalize PnL units across all closed picks
python quick_wins/shared/normalize_pnl_units.py multi_asset/data/multi_asset_closed.json
python quick_wins/shared/normalize_pnl_units.py multi_asset/data/institutional_closed.json

# Validate pick ID uniqueness
python quick_wins/shared/validate_pick_ids.py multi_asset/data/*.json

# Run the QA validator (PnL=0% detection, blank fields, stale picks)
python alpha_engine/risk_qa_validator.py validate --picks <picks.json> --market-data <market.json>

# Forward-test tracker (K1–K8 kill, P1–P7 promote)
python alpha_engine/data/forward_testing/forward_tracker.py status
```

---

**Bottom line: we have not proven profitability in any asset class. What we now have is a rigorous, repeatable proof standard and a clear, honest path: deploy low-cost beta now, and let only a pre-registered, out-of-sample, cost-adjusted EQUITY test earn the right to claim alpha.**
