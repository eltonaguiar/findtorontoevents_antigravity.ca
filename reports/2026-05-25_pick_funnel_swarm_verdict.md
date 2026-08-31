# Pick Funnel Swarm Verdict — 2026-08-31 04:12 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260831T041138Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT: 90-DAY EDGE ANALYSIS

### EQUITY
- Real/noise verdict: **LIKELY LEAKAGE / LOOK-AHEAD BIAS** — The `mean_reversion & score_dec=S40` cell shows WR=98.61% (71/72 wins), PF=226.6, avg_pnl=1.25%. This is statistically impossible in live trading. The train/holdout split (20/52) with holdout PF=158.1 confirms the signal persists, but the magnitude is absurd. This pattern (near-100% WR with tiny avg_pnl) is classic look-ahead bias — likely the score_dec=S40 bucket is capturing post-hoc information (e.g., the score was computed after the trade closed). The `trust=UNK` dimension is also suspicious — unknown trust should not produce 98% WR. **DO NOT TRADE THIS.**
- 90d expected P&L (1% risk, $100k): **$0** — Cannot size into a suspected leakage cell. If forced: 72 trades × 1% × $100k × 1.25% avg_pnl = **$900** (but this is fake money).
- Gate change: `SMART_PICKS_MIN_SCORE_EQUITY = 80` (raise from current) to filter out S40 low-score signals that are likely overfit.
- Confidence (1-5): **1** — This is not a real edge.

### INDEX
- Real/noise verdict: **NOISE** — n=10 closed trades, WR=30%, PF=0.43. Sample too small, performance negative. No PROVEN cells. This class has no edge.
- 90d expected P&L (1% risk, $100k): **-$700** (10 trades × 1% × $100k × -0.70% avg_pnl)
- Gate change: `SMART_PICKS_MIN_SCORE_INDEX = 85` (raise to kill most signals) or **DEMOTE** per MUTATION_THREE_AXIS_PROTOCOL.
- Confidence (1-5): **2** — Clear underperformance, but small sample.

### COMMODITY
- Real/noise verdict: **NOISE** — n=283 closed, WR=36.04%, PF=0.56. Best cell (n=23, WR=69.57%, PF=14.79) fails holdout (holdout_pass=false) and bonferroni. The high PF is driven by 2-3 outlier trades (avg_pnl=4.6% vs typical <1%). This is variance, not edge. Note: H-001 (COT leakage) was already rejected — this looks like a similar pattern.
- 90d expected P&L (1% risk, $100k): **-$1,800** (283 trades × 1% × $100k × -0.64% avg_pnl)
- Gate change: `SMART_PICKS_MIN_SCORE_COMMODITY = 75` (raise from current) to reduce noise trades.
- Confidence (1-5): **2** — Negative expectancy, no proven cells.

### FOREX
- Real/noise verdict: **NOISE / POSSIBLE LEAKAGE** — n=537 closed, WR=42.46%, PF=0.74. Best cell (n=39, WR=69.23%, PF=3.70) fails holdout (holdout_pass=false, holdout PF=1.036). The `conf=C0.75-0.80 & rr=RR1.0-1.5 & dir=LONG` cell looks suspicious — 69% WR with 1.0-1.5 R:R should produce PF>2.0, but holdout collapses to 1.036. This is overfitting to the 90-day window. The `consensus` source cells mentioned in the prompt are NOT in the top edges — good, they were likely rejected. **NO PROVEN EDGE.**
- 90d expected P&L (1% risk, $100k): **-$1,400** (537 trades × 1% × $100k × -0.26% avg_pnl)
- Gate change: `SMART_PICKS_MIN_SCORE_FOREX = 80` (raise from current) to filter low-conviction trades.
- Confidence (1-5): **2** — Negative expectancy, no proven cells.

### CRYPTO
- Real/noise verdict: **REAL EDGE (with caveats)** — The `conf=C0.75-0.80 & dir=LONG & score_dec=S50` cell (n=228, WR_shrunk=76.21%, PF=4.39) passes all tests: holdout_pass=true, bonferroni_pass=true, wr_z=8.61. Train PF=3.46, holdout PF=6.24 — the edge IMPROVES out-of-sample. However, the `trust=UNK` dimension is redundant (same n=228) — this means trust is not a differentiating factor. The `source=alpha_engine` variant (n=223) is nearly identical, confirming the signal comes from the alpha engine scoring. **CAVEAT:** The avg_pnl=1.46% with PF=4.39 implies avg_loss≈0.33% — this is tight risk management, not a free lunch. The `ml` cells mentioned in the prompt are NOT in top edges — good, they were likely rejected for leakage.
- 90d expected P&L (1% risk, $100k): **+$3,300** (228 trades × 1% × $100k × 1.46% avg_pnl = $3,329, minus ~$30 slippage = **$3,300**)
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO = 80` (keep current) but add `HC_FILTER_MIN_CONFIDENCE_CRYPTO = 0.75` in `hc_filter.js` to ensure only C0.75+ signals pass.
- Confidence (1-5): **4** — Strong statistical evidence, but 90d is short. Monitor for regime change.

### FUTURES
- Real/noise verdict: **NOISE** — n=25 closed, WR=48%, PF=0.92. Best cell (n=24, WR=45.83%, PF=1.75) fails holdout (holdout PF=0.558). Sample too small, no proven edge. H-005 already rejected momentum inversion.
- 90d expected P&L (1% risk, $100k): **-$200** (25 trades × 1% × $100k × -0.08% avg_pnl)
- Gate change: `SMART_PICKS_MIN_SCORE_FUTURES = 85` (raise to kill most signals) or **DEMOTE**.
- Confidence (1-5): **2** — No edge, small sample.

### ETF
- Real/noise verdict: **NOISE** — n=16 closed, WR=6.25% (1 win / 15 losses), PF=0.07. Catastrophic performance. No PROVEN cells. This class is actively destroying capital.
- 90d expected P&L (1% risk, $100k): **-$1,400** (16 trades × 1% × $100k × -0.88% avg_pnl)
- Gate change: `SMART_PICKS_MIN_SCORE_ETF = 90` (effectively kill) or **DEMOTE** per MUTATION_THREE_AXIS_PROTOCOL.
- Confidence (1-5): **1** — Clear negative edge, should be killed.

### UNKNOWN
- Real/noise verdict: **NOISE** — n=11 closed, WR=0% (0 wins / 11 losses). No edge, no PROVEN cells. This class should be killed immediately.
- 90d expected P&L (1% risk, $100k): **-$1,100** (11 trades × 1% × $100k × -1.00% avg_pnl)
- Gate change: `SMART_PICKS_MIN_SCORE_UNKNOWN = 95` (effectively kill) or **DEMOTE**.
- Confidence (1-5): **1** — Zero wins, clear kill.

### BOND
- Real/noise verdict: **NOISE** — n=24 closed, WR=25%, PF=0.33. No PROVEN cells. Negative expectancy.
- 90d expected P&L (1% risk, $100k): **-$1,200** (24 trades × 1% × $100k × -0.50% avg_pnl)
- Gate change: `SMART_PICKS_MIN_SCORE_BOND = 85` (raise to kill most signals) or **DEMOTE**.
- Confidence (1-5): **2** — Negative edge, small sample.

### MEME
- Real/noise verdict: **NOISE** — n=4 closed, WR=25%, PF=0.33. Sample too small to conclude anything. No PROVEN cells.
- 90d expected P&L (1% risk, $100k): **-$100** (4 trades × 1% × $100k × -0.25% avg_pnl)
- Gate change: `SMART_PICKS_MIN_SCORE_MEME = 80` (keep current, but monitor).
- Confidence (1-5): **1** — Too few trades to assess.

---

## SYSTEM-WIDE CONCLUSION

### SCALE UP TODAY: **CRYPTO** (LONG, conf≥0.75, score_dec=S50)
- **Why:** Only class with statistically proven edge (WR_shrunk=76.21%, PF=4.39, holdout_pass=true, bonferroni_pass=true). The edge is consistent across train/holdout and improves out-of-sample (holdout PF=6.24 vs train PF=3.46). The signal is specific (LONG, conf 0.75-0.80, score_dec=S50) and actionable.
- **Sizing:** 1% risk per trade, $100k notional → 228 trades over 90d → expected +$3,300 (3.3% return on notional).
- **Risk:** 90d is short. Monitor for regime change. The `trust=UNK` dimension suggests trust scoring is not adding value — consider removing it from the gate.

### DEMOTE / MUTATE BEFORE KILL: **ETF, UNKNOWN, INDEX, BOND**
- **ETF (WR=6.25%, PF=0.07):** Actively destroying capital. Per MUTATION_THREE_AXIS_PROTOCOL, mutate the signal (try different strategy families) before killing. If no improvement in 30d, kill.
- **UNKNOWN (WR=0%, n=11):** Zero wins. Kill immediately — no mutation can save a class with 0% WR.
- **INDEX (WR=30%, PF=0.43):** Negative expectancy. Mutate (try different direction/score_dec combos) before killing.
- **BOND (WR=25%, PF=0.33):** Negative expectancy. Mutate before kill.

### WATCHLIST (MUTATE, NOT KILL): **COMMODITY, FOREX, FUTURES, MEME**
- **COMMODITY (WR=36%, PF=0.56):** Best cell fails holdout. Mutate the signal (try different conf bands) before killing.
- **FOREX (WR=42%, PF=0.74):** Best cell fails holdout. Mutate (try different R:R bands) before killing.
- **FUTURES (WR=48%, PF=0.92):** Near breakeven. Mutate before killing.
- **MEME (n=4):** Too few trades. Keep monitoring.

### CRITICAL WARNING: **EQUITY**
The EQUITY `mean_reversion & score_dec=S40` cell (WR=98.61%, PF=226.6) is **NOT REAL**. This is either:
1. **Look-ahead bias** — the score_dec=S40 bucket may be computed using future data.
2. **Single-symbol concentration** — check if 70+ of the 72 trades are the same ticker.
3. **Data leakage** — the `trust=UNK` dimension suggests the signal is not properly attributed.

**DO NOT TRADE THIS CELL.** If you see similar patterns in production, flag them as potential leakage recurrence per the rejected hypotheses list.

### FINAL VERDICT
- **Real edge to scale:** CRYPTO LONG (conf≥0.75, score_dec=S50) — but size conservatively (0.5% risk initially) until 180d of data confirms.
- **Kill immediately:** UNKNOWN (0% WR), ETF (6% WR).
- **Mutate before kill:** INDEX, BOND, COMMODITY, FOREX, FUTURES.
- **Investigate for leakage:** EQUITY (98% WR is not real).
- **Overall system health:** 1 of 11 asset classes has a proven edge. The system is over-trading (opened 45,000+ trades vs 4,000+ closed) — most signals are noise. Tighten gates aggressively.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real. n=228, WR_shrunk=76.21, PF=4.393 with clean holdout pass + bonferroni pass; no obvious leakage flags.
- 90d expected P&L (1% risk, $100k): $12400 (assumes 1% risk/trade, 0.15% slippage on entries, 0.8R avg winner, 0.4R avg loser, ~75 trades from the cell).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 50
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Noise/leakage. n=72 but WR=98.61% (shrunk 88%) and PF=226.6 screams single-symbol concentration or look-ahead; impossible in live mean-reversion without data snooping.
- 90d expected P&L (1% risk, $100k): $0 (edge is not real; do not size).
- Gate change: SMART_PICKS_MIN_TRUST_EQUITY = 70
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise. No proven cells; best_pf_overall fails holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): -$1800 (random walk around 36% WR on closed trades).
- Gate change: HC_MIN_CONF = 0.80
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise. No proven cells; best_pf_overall fails holdout.
- 90d expected P&L (1% risk, $100k): -$2100 (42% WR on 537 closed).
- Gate change: HC_MIN_SCORE = 55
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise. No proven cells; best_pf_overall fails holdout.
- 90d expected P&L (1% risk, $100k): $0 (n too low, no edge).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 60
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise. No proven cells, tiny n.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_TRUST = 75
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise. No proven cells, 6.25% WR.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 65
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise. No proven cells, 30% WR.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONF = 0.80
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise. No proven cells, 0% WR.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 70
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise. No proven cells, n=4.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_SCORE = 55
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with verified, holdout-passed edge). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md — its "proven" cell is almost certainly leakage and should be mutated (add symbol-level dedup + stricter trust floor) before any further allocation. All other classes have zero actionable edge.
