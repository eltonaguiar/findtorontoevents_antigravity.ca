# Pick Funnel Swarm Verdict — 2026-08-29 04:09 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260829T040926Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT — 90-DAY EDGE ANALYSIS

### EQUITY
- **Real/noise verdict**: **NOISE — LEAKAGE SUSPECTED**. The "PROVEN" cell (mean_reversion, S40, n=74, WR=98.65%, PF=225.8) is statistically impossible in live trading. A 98.65% win rate with PF=225.8 means you're capturing ~1.2% avg win vs ~0.005% avg loss — this is either (a) look-ahead bias in signal generation, (b) survivorship bias in closed trades, or (c) the "closed" trades are being cherry-picked. The train/holdout split (21/53) with holdout PF=160.6 confirms this isn't generalizing — it's memorizing. **This is a leakage red flag, not an edge.**
- **90d expected P&L (1% risk, $100k)**: **-$4,200** (assuming 50% of the 352 closed trades are real, WR drops to ~50%, PF~1.0, avg P&L ~0%)
- **Gate change**: `SMART_PICKS_MIN_SCORE_EQUITY = 85` (raise from current to filter out the mean_reversion/S40 garbage)
- **Confidence (1-5)**: **1** — this is fabricated by data leakage, not real alpha

---

### COMMODITY
- **Real/noise verdict**: **NOISE — NO EDGE**. Zero PROVEN cells. Best cell (n=23, WR=69.57%, PF=14.79) fails holdout (holdout_pass=false), fails Bonferroni, and has train_n=8 — statistically meaningless. The 35.4% overall WR with 291 decisive trades confirms this class is a net loser. The "best" cells are all conf=C<0.60 which is the OPPOSITE of high conviction — this is noise chasing.
- **90d expected P&L (1% risk, $100k)**: **-$8,700** (291 closed trades, 35.4% WR, avg loss ~0.3% per trade, PF~0.85)
- **Gate change**: `SMART_PICKS_MIN_SCORE_COMMODITY = 90` (effectively kill all commodity picks until the scanner is fixed)
- **Confidence (1-5)**: **1** — no edge exists, and the "best" cells are statistical artifacts

---

### FOREX
- **Real/noise verdict**: **NOISE — LEAKAGE SUSPECTED**. Zero PROVEN cells. The best cell (conf=C0.75-0.80, rr=RR1.0-1.5, LONG, n=39, WR=69.23%, PF=3.696) fails holdout (holdout_pf=1.036, holdout_pass=false). The suspicious part: 21,164 of 22,266 scanned passed Smart_Picks (95.1% pass rate) — this means the Smart_Picks gate is NOT filtering anything for FOREX. The 42.46% WR with 537 decisive trades confirms this is a coin flip at best. The "consensus" source cells you flagged are NOT in the top edges — they're even worse.
- **90d expected P&L (1% risk, $100k)**: **-$5,100** (537 closed trades, 42.46% WR, avg loss ~0.2% per trade, PF~0.95)
- **Gate change**: `SMART_PICKS_MIN_SCORE_FOREX = 75` (raise from current ~50 to actually filter the 95% pass rate)
- **Confidence (1-5)**: **1** — no real edge, and the gate is completely broken for this class

---

### CRYPTO
- **Real/noise verdict**: **REAL EDGE — BUT NARROW**. The PROVEN cell (conf=C0.75-0.80, LONG, S50, n=235, WR=78.72%, PF=4.241) passes all statistical tests: holdout_pass=true, Bonferroni_pass=true, wr_z=8.805. The train/holdout split (142/93) with holdout PF=5.34 confirms generalization. However, this is ONE cell out of thousands tested — the 46.34% overall WR with 2,663 decisive trades shows the base rate is poor. The edge is concentrated in a specific confidence band (0.75-0.80) and score decile (S50) — this is a real but narrow signal. **The "ml" cells you flagged are NOT in the proven list — they're noise.**
- **90d expected P&L (1% risk, $100k)**: **+$18,300** (235 trades at 1% risk, 78.72% WR, avg win 1.4%, avg loss 0.33%, PF=4.24 → net ~$78/trade × 235 = $18,330)
- **Gate change**: `HC_FILTER_MIN_CONFIDENCE_CRYPTO = 0.75` (in `hc_filter.js`, raise from current 0.75 to 0.78 to narrow into the proven band)
- **Confidence (1-5)**: **4** — statistically robust, but narrow; needs live monitoring for regime shift

---

### FUTURES
- **Real/noise verdict**: **NOISE — INSUFFICIENT DATA**. Only 25 closed trades, 48% WR, PF=1.753 but holdout_pf=0.558 (fails). The n=24 cell with WR=45.83% is statistically meaningless. This class has too few trades to draw ANY conclusion. The rejected H-005 hypothesis (futures_momentum_anti_signal) confirms this class has known issues.
- **90d expected P&L (1% risk, $100k)**: **-$300** (25 trades, 48% WR, ~0% net — noise)
- **Gate change**: `SMART_PICKS_MIN_SCORE_FUTURES = 80` (raise to reduce false positives)
- **Confidence (1-5)**: **1** — no data, no edge, no signal

---

### ETF
- **Real/noise verdict**: **NOISE — NO EDGE**. 10% WR with 20 decisive trades. Zero PROVEN cells. The 2 wins vs 18 losses is statistically significant in the WRONG direction (p<0.01 that this is worse than random). This class is actively destroying capital.
- **90d expected P&L (1% risk, $100k)**: **-$1,600** (20 trades, 10% WR, avg loss ~0.8% per trade)
- **Gate change**: `SMART_PICKS_MIN_SCORE_ETF = 95` (effectively kill — this class has no edge)
- **Confidence (1-5)**: **1** — no edge, actively harmful

---

### UNKNOWN
- **Real/noise verdict**: **NOISE — NO EDGE**. 0% WR with 11 decisive trades. All 11 closed trades were losses. This class should be eliminated entirely — the "UNKNOWN" asset class is a data quality failure, not a trading opportunity.
- **90d expected P&L (1% risk, $100k)**: **-$1,100** (11 trades, 0% WR, avg loss ~1% per trade)
- **Gate change**: `SMART_PICKS_MIN_SCORE_UNKNOWN = 100` (kill — no legitimate trades should be in this class)
- **Confidence (1-5)**: **1** — no edge, data quality issue

---

### BOND
- **Real/noise verdict**: **NOISE — NO EDGE**. 28% WR with 25 decisive trades. Zero PROVEN cells. Best cell (n=20, WR=25%, PF=0.728) is actively losing money. The bond_scanner source is producing garbage.
- **90d expected P&L (1% risk, $100k)**: **-$1,800** (25 trades, 28% WR, avg loss ~0.7% per trade)
- **Gate change**: `SMART_PICKS_MIN_SCORE_BOND = 90` (kill — no edge)
- **Confidence (1-5)**: **1** — no edge, actively harmful

---

### INDEX
- **Real/noise verdict**: **NOISE — INSUFFICIENT DATA**. 30% WR with only 10 decisive trades. Zero PROVEN cells. The n=10 sample is too small for any conclusion, but the direction (30% WR) is concerning.
- **90d expected P&L (1% risk, $100k)**: **-$400** (10 trades, 30% WR, avg loss ~0.4% per trade)
- **Gate change**: `SMART_PICKS_MIN_SCORE_INDEX = 85` (raise to reduce false positives)
- **Confidence (1-5)**: **1** — no data, no edge

---

### MEME
- **Real/noise verdict**: **NOISE — INSUFFICIENT DATA**. 25% WR with only 4 decisive trades. Zero PROVEN cells. The n=4 sample is meaningless. This class should be monitored but not traded.
- **90d expected P&L (1% risk, $100k)**: **-$100** (4 trades, 25% WR, ~0% net — noise)
- **Gate change**: `SMART_PICKS_MIN_SCORE_MEME = 80` (raise to reduce false positives)
- **Confidence (1-5)**: **1** — no data, no edge

---

## SYSTEM-WIDE CONCLUSION

### SCALE UP TODAY: **CRYPTO** (narrowly)
The CRYPTO conf=C0.75-0.80 & LONG & S50 cell is the ONLY statistically validated edge in the entire system. With n=235, WR=78.72%, PF=4.241, holdout_pass=true, and Bonferroni_pass=true, this is real alpha. However, it's NARROW — only 235 trades in 90 days, and the edge is concentrated in a specific confidence band. **Scale up with 1% risk per trade, but cap total CRYPTO exposure at 30% of the portfolio.** Monitor for regime shift — if the WR drops below 65% over the next 30 days, cut exposure in half.

### DEMOTE PER MUTATION_THREE_AXIS_PROTOCOL: **ETF, BOND, UNKNOWN**
These three classes have WR < 30% with sufficient sample sizes (20+, 25+, 11+ respectively) to conclude they are actively destroying capital. Per the protocol, they should be **MUTATED** (not killed) — the scanner logic needs fundamental changes, not parameter tweaks. Specifically:
- **ETF**: The 10% WR suggests the scanner is picking the WRONG direction. Mutate the signal logic, not the threshold.
- **BOND**: The 28% WR with bond_scanner source suggests the source itself is broken. Mutate the source.
- **UNKNOWN**: This class should not exist. Mutate the asset classification logic to eliminate it.

### CRITICAL WARNINGS:
1. **EQUITY mean_reversion/S40 cell is LEAKAGE, not edge**. PF=225.8 is impossible in live trading. Investigate the data pipeline for look-ahead bias.
2. **FOREX Smart_Picks gate is broken** — 95.1% pass rate means it's not filtering anything. Fix the gate before trusting any FOREX signal.
3. **The "PROVEN" definition is too lenient** — requiring only WR>=55% and PF>=1.5 allows noise cells through. Tighten to WR>=65% and PF>=2.0 with holdout_pass=true AND Bonferroni_pass=true.

### FINAL VERDICT:
**Only 1 of 10 asset classes has a real edge (CRYPTO).** The system is generating 90% noise. The EQUITY "edge" is a data leakage artifact. The FOREX gate is broken. The COMMODITY, ETF, BOND, and UNKNOWN classes are actively losing money. **Do not scale up anything except CRYPTO, and even then, with tight risk controls and continuous monitoring.**

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — 98.65% WR and PF=225 on n=74 mean_reversion S40 is statistically impossible without single-symbol concentration or look-ahead; WR_shrunk 88.3 still extreme.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise — no proven cells; best_pf_overall fail holdout and bonferroni; all n<25.
- 90d expected P&L (1% risk, $100k): -$4200 (baseline WR 35%).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 80
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: Noise — no proven cells; best_pf_overall fail holdout; n=39 too small for claimed PF=3.7.
- 90d expected P&L (1% risk, $100k): -$1800 (baseline WR 42%).
- Gate change: HC_MIN_CONF_FOREX = 0.82
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: Real — n=235, WR_shrunk 76.5, PF 4.24, holdout_pass true, bonferroni true, train/holdout stable; no obvious leakage.
- 90d expected P&L (1% risk, $100k): $18400 (assume 1.4% avg win, 235 trades, 1% risk sizing, 0.15% slippage).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 55
- Confidence (1-5): 4

### FUTURES
- Real/noise verdict: Noise — no proven cells; best_pf_overall fails holdout, n=25 too small.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 70
- Confidence (1-5): 3

### ETF
- Real/noise verdict: Noise — no proven cells, n=20, WR 10%.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 75
- Confidence (1-5): 3

### UNKNOWN
- Real/noise verdict: Noise — no proven cells, n=11, WR 0%.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 3

### BOND
- Real/noise verdict: Noise — no proven cells; best_pf_overall fails all checks, n=20.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 75
- Confidence (1-5): 3

### INDEX
- Real/noise verdict: Noise — no proven cells, n=10.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 75
- Confidence (1-5): 3

### MEME
- Real/noise verdict: Noise — no proven cells, n=4.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 80
- Confidence (1-5): 3

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with verified, holdout-stable edge). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md (mutate the mean_reversion S40 path before full kill). All other classes have zero actionable edge.
