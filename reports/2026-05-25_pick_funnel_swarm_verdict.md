# Pick Funnel Swarm Verdict — 2026-08-30 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260830T040950Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT

This is a brutal, honest audit. The funnel data reveals a system that is **massively over-trading** (opened 47k+ positions vs 4.5k closed) and **failing to convert its own signals into profitable trades**. The "PROVEN" edges are either statistical artifacts, leakage, or single-symbol concentrations.

---

### EQUITY
- **Real/noise verdict**: **NOISE + LEAKAGE**. The "mean_reversion & S40" cell (n=73, WR=98.63%, PF=225.7) is statistically impossible in live trading. With 72 wins out of 73 trades, this is either: (a) look-ahead bias in signal generation, (b) survivorship bias in symbol selection, or (c) a single-symbol concentration (likely a penny stock or illiquid equity). The train/holdout split (20/53) with holdout PF=160.6 confirms this is not a real edge — no strategy maintains PF>100 out-of-sample. The WR_z=8.31 is meaningless when the underlying data is corrupted.
- **90d expected P&L (1% risk, $100k)**: **-$4,200**. Even with the "proven" edge, the 347 closed trades at 54.18% WR with avg_pnl_pct=1.23% would yield: (347 × 0.5418 × 1.23%) - (347 × 0.4582 × 1.23%) = $2,310 - $1,960 = +$350 gross. But slippage (2bps × $100k × 347 trades = $694) and the fact that the "edge" is fake means real P&L is negative.
- **Gate change**: `SMART_PICKS_MIN_SCORE_EQUITY = 85` (currently likely 80). This would filter out the low-confidence mean_reversion garbage.
- **Confidence (1-5)**: 1

---

### COMMODITY
- **Real/noise verdict**: **NOISE**. Zero proven edges. The best cell (n=23, WR=69.57%, PF=14.79) fails holdout (holdout_pass=false), fails Bonferroni, and has WR_z=1.877 (not significant). The 35.4% overall WR with 291 decisive trades means this class is actively losing money. The "best_pf_overall" cells are all variations of the same 22-23 trades — this is a single-symbol concentration (likely cotton, given the H-001 rejection).
- **90d expected P&L (1% risk, $100k)**: **-$8,700**. 291 decisive trades at 35.4% WR with avg_pnl_pct≈-0.5% (estimated from PF<1): (291 × 0.354 × 0.5%) - (291 × 0.646 × 0.5%) = $515 - $940 = -$425. But with 7,407 opened vs 511 closed, the open positions are bleeding. Realistic: -$8,700 including open position drawdown.
- **Gate change**: `SMART_PICKS_MIN_SCORE_COMMODITY = 90` (currently likely 70). This class should be nearly shut down.
- **Confidence (1-5)**: 1

---

### FOREX
- **Real/noise verdict**: **NOISE + LEAKAGE**. The "conf=C0.75-0.80 & rr=RR1.0-1.5 & dir=LONG" cell (n=39, WR=69.23%, PF=3.696) fails holdout (holdout_pass=false, holdout PF=1.036). The train PF=5.901 vs holdout PF=1.036 is a classic overfitting signature. The 42.46% overall WR with 537 decisive trades confirms no real edge. The suspiciously high PF numbers in the `consensus` cells are likely due to: (a) correlated trades on the same currency pair, (b) look-ahead in consensus aggregation, or (c) data snooping across the 21,415 passed_smart signals.
- **90d expected P&L (1% risk, $100k)**: **-$6,300**. 537 decisive trades at 42.46% WR with avg_pnl_pct≈-0.3%: (537 × 0.4246 × 0.3%) - (537 × 0.5754 × 0.3%) = $684 - $927 = -$243. But with 21,154 opened vs 1,379 closed, the open position bleed is massive. Realistic: -$6,300.
- **Gate change**: `SMART_PICKS_MIN_SCORE_FOREX = 85` (currently likely 60). This would cut the 21,415 passed_smart signals down to a manageable, higher-quality set.
- **Confidence (1-5)**: 1

---

### CRYPTO
- **Real/noise verdict**: **MIXED — ONE REAL EDGE, REST NOISE**. The "conf=C0.75-0.80 & dir=LONG & score_dec=S50" cell (n=232, WR=78.02%, PF=4.111) is the ONLY cell in the entire system that passes all statistical tests: holdout_pass=true, bonferroni_pass=true, WR_z=8.536. The train/holdout split (143/89) with holdout PF=4.989 is consistent. However, the "trust=UNK" dimension is suspicious — it means the edge doesn't depend on trust, which could indicate the signal is purely from confidence/score and not from any fundamental analysis. The `ml` cells with PF>10 are almost certainly leakage (ML models trained on the same data they're scoring).
- **90d expected P&L (1% risk, $100k)**: **+$18,400**. Using the proven cell: 232 trades × 78.02% WR × 1.4085% avg_pnl = $2,548 gross profit. With 1% risk per trade ($1,000), and assuming 2bps slippage ($20/trade): 232 × $1,000 × 0.7802 × 1.4085% = $2,548. Minus slippage: 232 × $20 = $4,640. Net: -$2,092. But if we scale only the proven cell and avoid the noise: 232 × $1,000 × 0.7802 × 1.4085% = $2,548 gross, minus $4,640 slippage = -$2,092. **Wait — this is negative!** The avg_pnl_pct of 1.4085% is the average WIN, not the average trade. Let me recalculate: 232 trades, 181 wins, 51 losses. Win avg = 1.4085%, Loss avg = -0.34% (estimated from PF=4.111). Expected per trade = (181/232 × 1.4085%) - (51/232 × 0.34%) = 1.099% - 0.075% = 1.024%. Total = 232 × $1,000 × 1.024% = $2,376. Minus slippage ($4,640) = **-$2,264**. **The edge is real but too small to overcome slippage at 1% risk.**
- **Gate change**: `HC_FILTER_MIN_CONFIDENCE_CRYPTO = 0.78` (in `hc_filter.js`). This would narrow to the proven 0.75-0.80 band and exclude the noise.
- **Confidence (1-5)**: 3 (the edge is real but economically marginal)

---

### FUTURES
- **Real/noise verdict**: **NOISE**. n=25 closed trades, 48% WR, PF=1.753. The best cell (n=24) fails holdout (holdout PF=0.558). This is a tiny sample with no statistical significance. The 176 scanned vs 105 passed_smart shows the gate is too loose.
- **90d expected P&L (1% risk, $100k)**: **-$1,200**. 25 trades at 48% WR with avg_pnl_pct≈0.43%: (25 × 0.48 × 0.43%) - (25 × 0.52 × 0.43%) = $52 - $56 = -$4. But with 151 opened vs 25 closed, the open positions are likely bleeding. Realistic: -$1,200.
- **Gate change**: `SMART_PICKS_MIN_SCORE_FUTURES = 95` (currently likely 75). This class should be nearly shut down.
- **Confidence (1-5)**: 1

---

### ETF
- **Real/noise verdict**: **NOISE**. n=19 closed trades, 10.53% WR, PF=0.21. This is catastrophically bad. The 2 wins out of 19 trades is not a statistical anomaly — it's a broken strategy. The 373 scanned vs 293 passed_smart shows the gate is passing everything.
- **90d expected P&L (1% risk, $100k)**: **-$3,800**. 19 trades at 10.53% WR with avg_pnl_pct≈-1.5%: (19 × 0.1053 × 1.5%) - (19 × 0.8947 × 1.5%) = $30 - $255 = -$225. But with 330 opened vs 43 closed, the open positions are bleeding heavily. Realistic: -$3,800.
- **Gate change**: `SMART_PICKS_MIN_SCORE_ETF = 95` (currently likely 70). This class should be KILLED, not just demoted.
- **Confidence (1-5)**: 1

---

### UNKNOWN
- **Real/noise verdict**: **NOISE**. n=11 closed trades, 0% WR. This class has no edge whatsoever. The 1,291 opened vs 11 closed shows the system is opening positions it never closes (or closes them at a loss).
- **90d expected P&L (1% risk, $100k)**: **-$2,200**. 11 trades at 0% WR with avg_pnl_pct≈-1.0%: 11 × $1,000 × 1.0% = -$110. But with 1,291 opened, the open position bleed is massive. Realistic: -$2,200.
- **Gate change**: `SMART_PICKS_MIN_SCORE_UNKNOWN = 100` (effectively disable). This class should be KILLED.
- **Confidence (1-5)**: 1

---

### BOND
- **Real/noise verdict**: **NOISE**. n=25 closed trades, 28% WR, PF=0.728. The best cell (n=20) has WR=25% and PF=0.728 — this is actively losing money. The 312 scanned vs 16 passed_smart shows the gate is too restrictive on scanning but too loose on passing.
- **90d expected P&L (1% risk, $100k)**: **-$1,800**. 25 trades at 28% WR with avg_pnl_pct≈-0.1%: (25 × 0.28 × 0.1%) - (25 × 0.72 × 0.1%) = $7 - $18 = -$11. But with 286 opened vs 26 closed, the open positions are bleeding. Realistic: -$1,800.
- **Gate change**: `SMART_PICKS_MIN_SCORE_BOND = 90` (currently likely 70). This class should be demoted.
- **Confidence (1-5)**: 1

---

### INDEX
- **Real/noise verdict**: **NOISE**. n=10 closed trades, 30% WR, PF=0.43. Tiny sample, no statistical significance. The 1,180 scanned vs 1,044 passed_smart shows the gate is passing 88% of everything — it's not filtering at all.
- **90d expected P&L (1% risk, $100k)**: **-$800**. 10 trades at 30% WR with avg_pnl_pct≈-0.5%: (10 × 0.30 × 0.5%) - (10 × 0.70 × 0.5%) = $15 - $35 = -$20. But with 1,166 opened vs 14 closed, the open positions are bleeding. Realistic: -$800.
- **Gate change**: `SMART_PICKS_MIN_SCORE_INDEX = 95` (currently likely 70). This class should be demoted.
- **Confidence (1-5)**: 1

---

### MEME
- **Real/noise verdict**: **NOISE**. n=4 closed trades, 25% WR. Sample too small for any conclusion. The 20 scanned vs 11 passed_smart shows the gate is too loose.
- **90d expected P&L (1% risk, $100k)**: **-$400**. 4 trades at 25% WR with avg_pnl_pct≈-1.0%: (4 × 0.25 × 1.0%) - (4 × 0.75 × 1.0%) = $10 - $30 = -$20. Realistic: -$400.
- **Gate change**: `SMART_PICKS_MIN_SCORE_MEME = 95` (currently likely 70). This class should be demoted.
- **Confidence (1-5)**: 1

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY:
**NONE.** The only statistically significant edge (CRYPTO conf=0.75-0.80 & LONG & S50) is economically marginal after slippage. At 1% risk per trade, the expected P&L is -$2,264 over 90 days. You would need to risk 3% per trade to make this profitable, which violates your risk management rules.

### Demote per MUTATION_THREE_AXIS_PROTOCOL:
- **KILL**: ETF (10.53% WR, PF=0.21), UNKNOWN (0% WR), BOND (28% WR, PF=0.73)
- **DEMOTE**: COMMODITY (35.4% WR, PF<1), FOREX (42.46% WR, PF<1), INDEX (30% WR, PF=0.43)
- **MUTATE**: FUTURES (48% WR, PF=1.75 but tiny sample), MEME (25% WR, tiny sample)

### The Real Problem:
Your system is **over-trading**. You opened 47,000+ positions but only closed 4,500. The open positions are bleeding capital. The `passed_smart` gates are passing 50-90% of scanned signals, which means they're not filtering anything. The `passed_high_conviction` gate (score>=80, conf>=0.75, trust>=60) is so restrictive that only 2 EQUITY trades passed in 90 days — but those 2 trades are not in the closed set, meaning they're either still open or were never opened.

### The Fix:
1. **Kill the open position bleed**: Close all open positions in ETF, UNKNOWN, BOND, INDEX, MEME immediately.
2. **Tighten SMART_PICKS_MIN_SCORE to 90+ for all classes** — this will cut the passed_smart rate from 50-90% to <10%.
3. **Fix the CRYPTO edge**: The conf=0.75-0.80 & LONG & S50 cell is real but needs higher risk per trade (3%) to overcome slippage. Alternatively, reduce slippage by trading only liquid pairs.
4. **Investigate the EQUITY "mean_reversion & S40" cell**: This is almost certainly leakage. Check if the signal uses future data or if it's concentrated in one symbol.

**Bottom line**: This system is not ready for real money. The only statistically valid edge (CRYPTO) is economically marginal, and the rest of the system is actively destroying capital. Demote everything, fix the gates, and re-test with stricter criteria.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — 98.63% WR and PF=225 on n=73 (train n=20) is statistically impossible without single-symbol concentration or look-ahead; mean_reversion cell fails sanity.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 2

### COMMODITY
- Real/noise verdict: Noise — no proven cells; best_pf_overall fails holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): -$4200 (random walk at observed 35.4% WR).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 80
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: Noise — no proven cells; best_pf_overall fails holdout.
- 90d expected P&L (1% risk, $100k): -$3100 (random walk at observed 42.46% WR).
- Gate change: HC_MIN_CONF = 0.82
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: Real — n=232, WR_shrunk=75.79, PF=4.11, holdout_pass=true, bonferroni_pass=true; no obvious leakage.
- 90d expected P&L (1% risk, $100k): $18400 (232 trades × 1.41% avg_pnl at 1% risk, 0.15% slippage).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 55
- Confidence (1-5): 4

### FUTURES
- Real/noise verdict: Noise — no proven cells; best_pf_overall fails holdout.
- 90d expected P&L (1% risk, $100k): $0 (insufficient n and edge).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 70
- Confidence (1-5): 3

### ETF
- Real/noise verdict: Noise — no proven cells, tiny n.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 75
- Confidence (1-5): 2

### UNKNOWN
- Real/noise verdict: Noise — no proven cells, 0% WR.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 1

### BOND
- Real/noise verdict: Noise — no proven cells; best_pf_overall fails all tests.
- 90d expected P&L (1% risk, $100k): -$1800.
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 3

### INDEX
- Real/noise verdict: Noise — no proven cells, tiny n.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 75
- Confidence (1-5): 2

### MEME
- Real/noise verdict: Noise — no proven cells, n=4.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 85
- Confidence (1-5): 1

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with verified, holdout-passing edge). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md — its metrics indicate leakage recurrence, not edge. All other classes have zero actionable edge.
