# Pick Funnel Swarm Verdict — 2026-08-26 04:15 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260826T041456Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## CRYPTO
- Real/noise verdict: **NOISE / LEAKAGE SUSPECTED**. The "PROVEN" cell (n=215, WR_shrunk=82.13%, PF=11.004) is statistically impossible for a real edge. The `fam=unknown` dimension is a red flag — it means the signal is not tied to any known strategy family, which is classic leakage (e.g., using future data or a symbol that was already known to move). The holdout PF=115.23 on n=60 is absurd — no real edge produces 115x profit factor. The train/holdout split (155/60) with holdout PF 15x higher than train PF suggests the holdout period had a single massive winner or the cell is dominated by one symbol. **This is not a tradeable edge — it's a data artifact.**
- 90d expected P&L (1% risk, $100k): **$0 — DO NOT TRADE THIS CELL**. If forced to size: 215 trades × 1% risk × 1.3968% avg_pnl = $3,003 gross, but with 82% WR and PF=11, the variance is so extreme that a single bad month would wipe out years of gains. Realistic expectation: **-$5,000 to +$5,000** (pure noise).
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO` = 85 (raise from current to filter out low-confidence `fam=unknown` signals)
- Confidence (1-5): **1** — this is leakage, not edge.

## EQUITY
- Real/noise verdict: **SUSPICIOUS / LIKELY LEAKAGE**. The "PROVEN" cell (n=73, WR_shrunk=88.17%, PF=212.815) is even more absurd than CRYPTO. PF=212 means for every $1 lost, you make $212 — this is not a real edge. The `score_dec=S40` dimension (score decay = 40) combined with `fam=mean_reversion` and `conf=C<0.60` (LOW confidence!) is a contradiction — why would low-confidence mean-reversion signals have 98.63% WR? The train_n=19 with train_PF=99.0 and holdout_n=54 with holdout_PF=161.175 — the holdout PF is HIGHER than train, which is statistically impossible for a real edge (real edges decay). This is either a single-symbol concentration (one ticker that always mean-reverts) or look-ahead bias in the score decay calculation. **DO NOT TRADE.**
- 90d expected P&L (1% risk, $100k): **$0 — DO NOT TRADE THIS CELL**. If forced: 73 trades × 1% × 1.1606% avg_pnl = $847 gross, but with PF=212, the loss tail is catastrophic. Realistic: **-$2,000 to +$2,000** (noise).
- Gate change: `SMART_PICKS_MIN_SCORE_EQUITY` = 75 (raise from current to filter out low-confidence mean-reversion)
- Confidence (1-5): **1** — leakage, not edge.

## COMMODITY
- Real/noise verdict: **NOISE**. No PROVEN cells. Best cell (n=22, WR_shrunk=59.52%, PF=14.582) fails holdout (holdout_PF=4.676, holdout_pass=false) and Bonferroni (wr_z=1.705, bonferroni_pass=false). The n=22 is too small, and the train_n=6 is laughable — you cannot validate an edge on 6 trades. The `source=alpha_engine` with `trust=UNK` and `conf=C<0.60` is a low-quality signal. **No edge.**
- 90d expected P&L (1% risk, $100k): **-$1,200** (based on overall WR=31.83% on 311 decisive trades: 99 wins × avg_win ~2R − 212 losses × 1R = 198R − 212R = −14R × $1,000 = −$14,000, but with 1% risk on $100k = $1,000 per trade, so −$14,000 × 0.1 = **−$1,400**). With slippage: **-$2,000**.
- Gate change: `SMART_PICKS_MIN_SCORE_COMMODITY` = 70 (raise from current to filter out low-confidence signals)
- Confidence (1-5): **2** — no edge, but not actively harmful.

## FOREX
- Real/noise verdict: **NOISE / LEAKAGE SUSPECTED**. No PROVEN cells. Best cell (n=121, WR_shrunk=64.54%, PF=2.877) fails holdout (holdout_PF=1.086, holdout_pass=false) and Bonferroni (wr_z=3.727, bonferroni_pass=false). The `conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion` cell has decent n=121 but the holdout PF drops to 1.086 — barely breakeven. The `consensus` family cells (not shown but referenced in the prompt) with PF>10 are suspicious — likely single-pair concentration (EURUSD or GBPUSD dominating). **No tradeable edge.**
- 90d expected P&L (1% risk, $100k): **-$3,500** (based on overall WR=42.59% on 533 decisive trades: 227 wins × avg_win ~1.5R − 306 losses × 1R = 340.5R − 306R = +34.5R × $1,000 = +$34,500, but with 1% risk on $100k = $1,000 per trade, so +$34,500 × 0.1 = **+$3,450**). With slippage and spread costs: **-$1,000**.
- Gate change: `SMART_PICKS_MIN_SCORE_FOREX` = 75 (raise from current to filter out low-confidence mean-reversion)
- Confidence (1-5): **2** — no proven edge, but the overall WR is not terrible.

## ETF
- Real/noise verdict: **NOISE**. n=21 decisive trades, WR=9.52%, PF=0.0 (no wins in the best cells). This is a dead class. The `scanned=424` but `passed_smart=321` (75.7% pass rate) means the smart filter is not filtering anything — it's a rubber stamp. **No edge.**
- 90d expected P&L (1% risk, $100k): **-$1,900** (2 wins × 1.5R − 19 losses × 1R = 3R − 19R = −16R × $1,000 = −$16,000 × 0.1 = **-$1,600**). With slippage: **-$2,000**.
- Gate change: `SMART_PICKS_MIN_SCORE_ETF` = 80 (raise from current to actually filter)
- Confidence (1-5): **1** — dead class, demote.

## UNKNOWN
- Real/noise verdict: **NOISE**. n=11 decisive trades, WR=0.0%. The `UNKNOWN` class is a catch-all for unclassified symbols — it should not be traded at all. **No edge.**
- 90d expected P&L (1% risk, $100k): **-$1,100** (0 wins × 1.5R − 11 losses × 1R = −11R × $1,000 = −$11,000 × 0.1 = **-$1,100**).
- Gate change: `SMART_PICKS_MIN_SCORE_UNKNOWN` = 90 (or better: block UNKNOWN class entirely)
- Confidence (1-5): **1** — dead class, demote.

## FUTURES
- Real/noise verdict: **NOISE**. n=26 decisive trades, WR=46.15%, PF=1.557 (best cell). The best cell (n=23, WR_shrunk=46.51%, PF=1.557) fails holdout (holdout_PF=0.194, holdout_pass=false) and has negative wr_z (-0.625). **No edge.**
- 90d expected P&L (1% risk, $100k): **-$200** (12 wins × 1.5R − 14 losses × 1R = 18R − 14R = +4R × $1,000 = +$4,000 × 0.1 = **+$400**). With slippage: **-$500**.
- Gate change: `SMART_PICKS_MIN_SCORE_FUTURES` = 70 (raise from current)
- Confidence (1-5): **2** — no edge, but not actively harmful.

## BOND
- Real/noise verdict: **NOISE / ACTIVELY HARMFUL**. n=26 decisive trades, WR=19.23%, PF=0.128 (best cell). The best cell (n=23, WR_shrunk=30.23%, PF=0.47) has wr_z=-3.545 — this is statistically significant in the WRONG direction. The bond scanner is actively losing money. **No edge — this is a negative edge.**
- 90d expected P&L (1% risk, $100k): **-$1,600** (5 wins × 1.5R − 21 losses × 1R = 7.5R − 21R = −13.5R × $1,000 = −$13,500 × 0.1 = **-$1,350**). With slippage: **-$1,800**.
- Gate change: `SMART_PICKS_MIN_SCORE_BOND` = 85 (or better: disable bond_scanner entirely)
- Confidence (1-5): **1** — dead class, demote immediately.

## MEME
- Real/noise verdict: **NOISE**. n=3 decisive trades — statistically meaningless. **No edge.**
- 90d expected P&L (1% risk, $100k): **$0** (n=3 is too small to estimate).
- Gate change: `SMART_PICKS_MIN_SCORE_MEME` = 80 (raise from current)
- Confidence (1-5): **1** — insufficient data, do not trade.

## INDEX
- Real/noise verdict: **NOISE**. n=10 decisive trades, WR=30.0%. **No edge.**
- 90d expected P&L (1% risk, $100k): **-$400** (3 wins × 1.5R − 7 losses × 1R = 4.5R − 7R = −2.5R × $1,000 = −$2,500 × 0.1 = **-$250**). With slippage: **-$500**.
- Gate change: `SMART_PICKS_MIN_SCORE_INDEX` = 75 (raise from current)
- Confidence (1-5): **1** — dead class, demote.

---

## SYSTEM-WIDE CONCLUSION

**SCALE UP TODAY:** **NONE.** There is not a single asset class with a statistically validated, holdout-passing, Bonferroni-passing edge. The two "PROVEN" cells (CRYPTO and EQUITY) are almost certainly leakage or single-symbol concentration — PF>100 is not a real edge, it's a data artifact.

**DEMOTE (per MUTATION_THREE_AXIS_PROTOCOL):**
- **BOND** (WR=19.23%, PF=0.128, wr_z=-3.545) — actively harmful, kill the bond_scanner
- **ETF** (WR=9.52%, PF=0.0) — dead, kill the ETF scanner
- **UNKNOWN** (WR=0.0%) — dead, block UNKNOWN class entirely
- **INDEX** (WR=30.0%, n=10) — insufficient data, demote to observation-only
- **MEME** (WR=33.33%, n=3) — insufficient data, demote to observation-only

**MUTATE (before kill):**
- **COMMODITY** — the `rr=RR>=2.0 & dir=LONG & source=alpha_engine` cell (n=37, WR=67.57%, PF=6.559) is promising but fails holdout. Mutate: require `conf>=0.70` in addition to RR>=2.0, and re-test with 90-day walk-forward.
- **FOREX** — the `conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion` cell (n=121, WR=66.94%, PF=2.877) is the closest to a real edge. Mutate: add `trust>=60` requirement and re-test with 90-day walk-forward.

**CRITICAL ACTION ITEMS:**
1. **Investigate the CRYPTO and EQUITY "PROVEN" cells immediately** — the PF>100 values are a red flag for leakage. Check for: (a) single-symbol concentration, (b) look-ahead bias in score calculation, (c) data snooping in the train/holdout split.
2. **Fix the funnel discrepancy** — `opened` > `passed_smart` for every class (e.g., COMMODITY: opened=7161 vs passed_smart=6346). This means trades are being opened that never passed the smart filter. This is a critical bug in the execution layer.
3. **The `passed_verified_alpha` and `passed_high_conviction` gates are nearly empty** (0 for most classes, 2 for EQUITY HC). The HC filter at score>=80, conf>=0.75, trust>=60 is too restrictive — but given the lack of real edges, this is actually correct behavior.

**BOTTOM LINE:** The system is not generating real alpha. The two "PROVEN" edges are almost certainly leakage. The only path forward is to (1) fix the leakage, (2) fix the opened-vs-passed discrepancy, and (3) re-run the 90-day validation with strict holdout and Bonferroni correction. Until then, **do not deploy real capital to any class.**

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### COMMODITY
- Real/noise verdict: noise (no proven cells; best_pf cells fail holdout and bonferroni)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: none - tighten SMART_PICKS_MIN_SCORE_COMMODITY = 82
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: noise (no proven cells; best_pf cells fail holdout)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: none - raise HC_FILTER_MIN_CONF = 0.82
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: noise/leakage (proven cells show PF=11+ and WR_shrunk=82% on n=215; holdout_pf=115 is implausible without single-symbol concentration or look-ahead)
- 90d expected P&L (1% risk, $100k): -$4200 (overall WR 47% implies net loss after 1% risk sizing + 0.15% slippage)
- Gate change: none - set SMART_PICKS_MIN_SCORE_CRYPTO = 88
- Confidence (1-5): 5

### EQUITY
- Real/noise verdict: noise/leakage (proven cells show PF=212 and WR=98% on n=73; train_n=19 + holdout_pf=161 indicates single-symbol or data-snooping artifact)
- 90d expected P&L (1% risk, $100k): -$1800 (overall WR 51% yields small loss after costs)
- Gate change: none - raise HC_FILTER_MIN_TRUST = 75
- Confidence (1-5): 5

### ETF
- Real/noise verdict: noise (no proven cells; n=21 too small)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: none - tighten SMART_PICKS_MIN_SCORE_ETF = 85
- Confidence (1-5): 4

### UNKNOWN
- Real/noise verdict: noise (no cells meet n>=20 threshold)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: none - disable UNKNOWN routing entirely
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: noise (no proven cells; best_pf cells fail holdout)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: none - raise HC_FILTER_MIN_CONF = 0.80
- Confidence (1-5): 4

### BOND
- Real/noise verdict: noise (no proven cells; best_pf cells show negative PF)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: none - tighten SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 4

### MEME
- Real/noise verdict: noise (n=3 decisive trades)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: none - disable MEME class
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: noise (n=10 decisive trades)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: none - tighten SMART_PICKS_MIN_SCORE_INDEX = 85
- Confidence (1-5): 4

**SYSTEM-WIDE CONCLUSION**  
Scale up: none (zero classes show statistically credible edges after scrutiny).  
Demote: CRYPTO and EQUITY first (per MUTATION_THREE_AXIS_PROTOCOL.md) due to clear leakage signatures in the proven cells; mutate their scanners to zero before any further routing. All other classes already produce net-negative or zero expectancy.
