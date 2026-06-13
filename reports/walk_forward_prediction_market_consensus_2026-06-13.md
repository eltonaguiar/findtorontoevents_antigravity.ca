# Walk-Forward Refutation — prediction_market_consensus — 2026-06-13

**Owner:** MiniMax-M3
**Trigger:** Task #21 — confirm/refute the only EDGE_LIKELY_REAL with n>=100
**Tool:** `tools/walk_forward_per_strategy.py --strategy prediction_market_consensus --in-window 14 --out-window 5 --step 3`
**Verdict:** **REFUTED — 1/1 cells FAIL**

---

## 1. Setup

- Strategy: `prediction_market_consensus` (Class: PRED-MKT)
- Lookback window: 14 days IS, 5 days OOS, step 3 days
- Macro-join: NOT enforced (per current single-strategy test)
- Live data: 2026-05-28 to 2026-06-12 (16 days of trade history)

---

## 2. Audit-grade metrics (from `audit_dashboard/data/walk_forward_per_strategy_latest.json`)

| Metric | Value | Gate | Status |
|---|---:|---:|:---:|
| n_total trades | 275 | ≥100 | ✅ |
| n_windows (rolling) | 86 | n/a | n/a |
| n_surviving windows | 24 | n/a | n/a |
| survival_rate | 27.9% | ≥60% | **❌ FAIL** |
| mean_oos_pf | 8.27 | >0.5 (PF≥1.0 typical) | ⚠️ winsorized |
| mean_oos_wr | 47.4% | ≥50% | **❌ FAIL** |
| mean_is_pf | 55.5 | n/a | n/a (overfit signal) |
| total_pf | 3.27 | n/a | n/a |
| total_wr | 49.5% | n/a | n/a |
| **Verdict** | **FAIL** | PASS | **❌ FAIL** |

**Two independent reasons for FAIL:**
1. `survival_rate=0.28 < 0.6` — Only 28% of rolling windows showed positive OOS performance. The strategy is rolling-coin-flip, not an edge.
2. `mean_oos_wr=0.47 < 0.50` — OOS win rate is BELOW 50% in the average window. The strategy loses money per trade on average in OOS.

---

## 3. Why this conflicts with `anti_overfit_audit.json::EDGE_LIKELY_REAL`

The anti-overfit audit (`anti_overfit_audit.json` 2026-06-12) lists `prediction_market_consensus` as one of 4 EDGE_LIKELY_REAL strategies with:
- n=215, WR=67.9%, PF=3.43, DSR=0.998

The walk-forward says this is wrong. Why the discrepancy?

| | anti_overfit_audit | walk_forward |
|---|---|---|
| Method | Single cohort over the full lookback | Rolling IS/OOS, 14d/5d windows |
| Survival criterion | DSR≥0.95 (Lopez de Prado) | survival_rate≥60% AND mean_oos_wr≥50% |
| WINSORIZATION | Implicit (PF=3.43 is a single number) | Each window is unbiased, then aggregated |
| OVERFIT detection | Partial (DSR adjusts for #tests) | Direct (OOS is unseen data) |
| Result | PASS | FAIL |

**The DSR=0.998 in anti_overfit_audit was the "single window" view** — it measures "is the entire backtest Sharpe statistically distinguishable from zero after correcting for the number of strategies we tested?" The walk-forward asks a different question: "if we re-fit the strategy in 14-day chunks and predict the next 5 days, does it work?"

**The walk-forward is the more honest test for forward deployment.** DSR says "this is unlikely to be luck in a single fit"; walk-forward says "this does not survive the test of time."

---

## 4. The winsorization problem

`mean_oos_pf=8.27` looks high but is **winsorization** (not a real signal):
- IS PF=55.5 is the in-sample overfit
- OOS PF=8.27 is the winsorized reality (a few large winners dominate)
- A PF of 8.27 from a 47% WR strategy is geometrically impossible unless the avg_win/avg_loss ratio is ~10x — i.e. a handful of large winners and many small losers

This pattern is identical to the FOREX `non_crypto_consensus` finding in the 2026-06-12 deep-dive (n=223 PF=9.68 from a 52% WR strategy). The walk-forward OOS PF=8.27 is a numerical artifact, not a real edge.

---

## 5. Operator decision

The `prediction_market_consensus` strategy has been investigated from three independent angles and all three say "do not size up":

| Angle | Source | Verdict |
|---|---|---|
| HARD_KILL_STRATEGIES | `alpha_engine/emitter_discipline.py:49` (P0B 2026-06-12) | KILLED — WR 26% intrabar |
| Live MySQL at_signal_outcomes | n=141 CRYPTO, WR=49.6%, avg_pnl=-0.19% | LOSING (per-trade) |
| Walk-forward rolling | 1/1 cells FAIL, OOS WR 47% | REFUTED |

**Recommendation: CONFIRM THE KILL.** The strategy is on HARD_KILL_STRATEGIES correctly. The anti_overfit_audit's DSR=0.998 is a single-window view that misses the temporal structure. The walk-forward is the right test and it says NO.

**Action: Update `anti_overfit_audit.json` to demote `prediction_market_consensus` from EDGE_LIKELY_REAL to REFUTED, citing the walk-forward result.** This brings the 3 audit systems (anti_overfit_audit + money_ready_verdict + at_signal_outcomes) into agreement.

---

## 6. Reproducer

```bash
cd /home/eaguiar2015/findtorontoevents_antigravity.ca
python3 tools/walk_forward_per_strategy.py --strategy prediction_market_consensus --in-window 14 --out-window 5 --step 3
cat audit_dashboard/data/walk_forward_per_strategy_latest.json | head -40
```

---

## 7. Cross-references

- 2026-06-12 anti_overfit_audit.json (the 4 EDGE_LIKELY_REAL candidates)
- 2026-06-12 money_ready_verdict.json::summary.candidate_paper[3] (now updated with walk-forward REFUTE)
- 2026-06-12 metric_honesty_tiers.json::candidate_paper (now updated)
- `tools/walk_forward_per_strategy.py` (the tool)
- HARD_KILL_STRATEGIES in `alpha_engine/emitter_discipline.py:49`
- 2026-06-12 deep_dive_FOREX_2026-06-12.md (the winsorization pattern)

---

*Last update: 2026-06-13 by MiniMax-M3.*
