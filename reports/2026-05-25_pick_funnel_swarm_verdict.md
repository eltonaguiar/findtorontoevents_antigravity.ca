# Pick Funnel Swarm Verdict — 2026-09-07 04:11 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260907T041103Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE DIAGNOSTIC — CRITICAL DATA INTEGRITY ISSUES

Before per-class analysis, I must flag **systemic data integrity problems** that invalidate most conclusions:

1. **`opened` >> `passed_smart` for every class** — e.g., EQUITY: 235 passed_smart but 4,578 opened. This means **97% of trades bypass the Smart_Picks gate entirely**. The funnel is broken at the execution layer.

2. **`passed_high_conviction = 0` for ALL classes** — the HC filter (score>=80, conf>=0.75, trust>=60) has **never passed a single trade in 90 days**. Either the gate is impossibly strict or the scoring never reaches those thresholds.

3. **`passed_verified_alpha` is tiny** (EQUITY: 12, CRYPTO: 1855, others: 0-4) — the verification layer is barely engaged.

4. **The "PROVEN" cells show suspiciously perfect stats** — EQUITY mean_reversion at 98.53% WR with PF=214.8 is **impossible in live trading**. This is either look-ahead bias, survivorship bias, or a data pipeline error.

5. **CRYPTO `opened` (10,405) >> `passed_smart` (3,227)** — 69% of crypto trades bypass the gate.

---

### EQUITY
- **Real/noise verdict**: **LEAKAGE / DATA ERROR**. The "PROVEN" cell (mean_reversion, S40, n=68, WR=98.53%, PF=214.8) is **statistically impossible** in live markets. A 98.5% win rate with PF=214 means average win is ~215x average loss — this is not trading, this is a data pipeline artifact. The train/holdout split (28/40) shows holdout PF=124, which is equally absurd. **This is not a real edge; it is a bug.** The overall class WR of 62.95% (n=224) is plausible but the "PROVEN" cell is garbage.
- **90d expected P&L (1% risk, $100k)**: Cannot estimate from corrupted data. If we used the overall class stats (62.95% WR, assume avg RR=1.5): Expected = 224 × [0.6295×1.5% - 0.3705×1%] × $1,000 = 224 × [0.944% - 0.371%] × $1,000 = **$1,284**. But this is meaningless given the gate bypass.
- **Gate change**: `SMART_PICKS_MIN_SCORE_EQUITY` = 70 (currently likely ~50-60, allowing too many low-quality picks through). Also **fix the execution layer** — `opened` must equal `passed_smart` or lower.
- **Confidence (1-5)**: 1 — data integrity compromised.

---

### INDEX
- **Real/noise verdict**: **NOISE / INSUFFICIENT DATA**. Only 6 decisive trades in 90 days. WR=33.33% (2W/4L) is meaningless at n=6. No PROVEN cells exist. The 1,351 opened vs 1,207 passed_smart shows the gate is barely filtering (89% pass rate).
- **90d expected P&L (1% risk, $100k)**: Cannot estimate — n=6 is statistically void. Even if we used the 33% WR: Expected = 6 × [0.333×1.5% - 0.667×1%] × $1,000 = 6 × [-0.167%] × $1,000 = **-$10** (negligible, meaningless).
- **Gate change**: `SMART_PICKS_MIN_SCORE_INDEX` = 75 (raise from current to reduce the 89% pass rate). But more importantly, **stop opening trades that don't pass the gate**.
- **Confidence (1-5)**: 1 — no signal, no data.

---

### FOREX
- **Real/noise verdict**: **NOISE / NO PROVEN EDGE**. The best cell (conf=C0.75-0.80, rr=RR1.0-1.5, dir=LONG, n=41, WR=70.73%, PF=3.967) **fails Bonferroni correction** (bonferroni_pass=false). The wr_z=2.655 is marginal. With 524 decisive trades across thousands of cells, finding one cell at 70% WR is **expected by chance alone**. The overall class WR of 43.51% (n=524) is **below breakeven** for typical RR. **No edge exists here.**
- **90d expected P&L (1% risk, $100k)**: Using overall stats (43.51% WR, assume avg RR=1.0): Expected = 524 × [0.4351×1% - 0.5649×1%] × $1,000 = 524 × [-0.13%] × $1,000 = **-$681**. You are **losing money** on FOREX.
- **Gate change**: `SMART_PICKS_MIN_SCORE_FOREX` = 85 (raise dramatically — currently 22,804 of 23,954 scanned pass, a 95% pass rate that means the gate is useless). Also consider **killing FOREX entirely** per mutation protocol.
- **Confidence (1-5)**: 2 — clear negative edge, no PROVEN cells.

---

### CRYPTO
- **Real/noise verdict**: **MIXED — ONE REAL EDGE, BUT DATA INTEGRITY CONCERN**. The PROVEN cell (conf=C0.75-0.80, score_dec=S50, source=alpha_engine, n=217, WR=76.96%, PF=3.99) passes all statistical tests: wr_z=7.943, bonferroni_pass=true, holdout_pass=true. The train/holdout consistency (train PF=3.353, holdout PF=5.277) is **actually improving** out-of-sample. However: **trust=UNK for all these trades** — meaning the trust score is not being computed or is defaulting to unknown. This is a red flag. Also, 1,855 passed_verified_alpha but 0 passed_high_conviction suggests the HC filter is broken. The overall class WR of 46.93% (n=2,489) is below the PROVEN cell's performance, confirming the gate is not capturing the edge.
- **90d expected P&L (1% risk, $100k)**: If we ONLY traded the PROVEN cell (n=217, WR=76.96%, PF=3.99, avg win ≈ 1.44%): Expected = 217 × [0.7696×1.44% - 0.2304×(1.44%/3.99)] × $1,000 = 217 × [1.108% - 0.083%] × $1,000 = 217 × 1.025% × $1,000 = **$2,224**. But this assumes perfect execution of only that cell.
- **Gate change**: `HC_FILTER_MIN_SCORE` in `hc_filter.js` = 75 (lower from 80 to actually pass trades). Also fix `trust` scoring — all PROVEN cells show trust=UNK, meaning the trust dimension is not being computed.
- **Confidence (1-5)**: 3 — one real edge exists but system can't capture it.

---

### COMMODITY
- **Real/noise verdict**: **NOISE / NO PROVEN EDGE**. Best cell (rr=RR>=2.0, source=alpha_engine, n=38, WR=71.05%, PF=7.199) **fails Bonferroni** (bonferroni_pass=false). n=38 is small. Overall WR=36.27% (n=204) is **terrible** — below breakeven for any reasonable RR. **No edge.**
- **90d expected P&L (1% risk, $100k)**: Using overall stats (36.27% WR, assume avg RR=1.5): Expected = 204 × [0.3627×1.5% - 0.6373×1%] × $1,000 = 204 × [-0.093%] × $1,000 = **-$190**. Losing money.
- **Gate change**: `SMART_PICKS_MIN_SCORE_COMMODITY` = 80 (raise from current — 4,962 of 7,341 pass, a 68% pass rate that's too loose). Consider demoting per mutation protocol.
- **Confidence (1-5)**: 1 — clear negative edge.

---

### ETF
- **Real/noise verdict**: **NOISE / INSUFFICIENT DATA**. Only 9 decisive trades. WR=11.11% (1W/8L). No PROVEN cells. n=9 is statistically void. The 285 passed_smart vs 316 opened shows gate bypass.
- **90d expected P&L (1% risk, $100k)**: Expected = 9 × [0.111×1.5% - 0.889×1%] × $1,000 = 9 × [-0.722%] × $1,000 = **-$65**. Meaningless at n=9.
- **Gate change**: `SMART_PICKS_MIN_SCORE_ETF` = 75. But honestly, **kill ETF** — 325 scanned in 90 days is too few to ever find an edge.
- **Confidence (1-5)**: 1 — no data, no edge.

---

### UNKNOWN
- **Real/noise verdict**: **NOISE / DATA QUALITY ISSUE**. 0% WR (0W/9L) at n=9. The fact that we have 1,444 "UNKNOWN" assets means the classification layer is broken. No PROVEN cells.
- **90d expected P&L (1% risk, $100k)**: Expected = 9 × [0×1.5% - 1.0×1%] × $1,000 = 9 × [-1%] × $1,000 = **-$90**. Meaningless.
- **Gate change**: Fix asset classification. `UNKNOWN` should never reach the trading layer. Set `MIN_ASSET_CLASS_CONFIDENCE` = 0.8 in classification.
- **Confidence (1-5)**: 1 — data pipeline failure.

---

### MEME
- **Real/noise verdict**: **NOISE / INSUFFICIENT DATA**. Only 4 decisive trades. WR=25% (1W/3L). n=4 is meaningless. No PROVEN cells.
- **90d expected P&L (1% risk, $100k)**: Expected = 4 × [0.25×1.5% - 0.75×1%] × $1,000 = 4 × [-0.375%] × $1,000 = **-$15**. Meaningless.
- **Gate change**: `SMART_PICKS_MIN_SCORE_MEME` = 85. But honestly, **kill MEME** — 21 scanned in 90 days is nothing.
- **Confidence (1-5)**: 1 — no data.

---

### FUTURES
- **Real/noise verdict**: **NOISE / NO EDGE**. Best cell (n=21, WR=42.86%, PF=1.616) **fails holdout** (holdout_pass=false) and has negative wr_z (-0.654). Overall WR=42.86% (n=21) is below breakeven. **No edge.**
- **90d expected P&L (1% risk, $100k)**: Expected = 21 × [0.4286×1.5% - 0.5714×1%] × $1,000 = 21 × [0.071%] × $1,000 = **$15**. Negligible, within noise.
- **Gate change**: `SMART_PICKS_MIN_SCORE_FUTURES` = 80. Consider demoting.
- **Confidence (1-5)**: 1 — no edge, failing validation.

---

### BOND
- **Real/noise verdict**: **NOISE / NEGATIVE EDGE**. WR=21.74% (5W/18L) at n=23. No PROVEN cells. This is **catastrophically bad** — worse than random.
- **90d expected P&L (1% risk, $100k)**: Expected = 23 × [0.2174×1.5% - 0.7826×1%] × $1,000 = 23 × [-0.456%] × $1,000 = **-$105**. Losing money.
- **Gate change**: `SMART_PICKS_MIN_SCORE_BOND` = 90 (or kill entirely). **Demote BOND** per mutation protocol.
- **Confidence (1-5)**: 1 — clear negative edge.

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY:
**CRYPTO** — but ONLY the specific PROVEN cell (conf=C0.75-0.80, score_dec=S50, source=alpha_engine). This is the only statistically validated edge in the entire system. However, I must flag:
- All trades show `trust=UNK` — the trust dimension is broken
- 0 passed_high_conviction means the HC filter is preventing execution
- The edge may be concentrated in specific symbols (need to verify)

**Action**: Fix the HC filter to pass these trades, verify no single-symbol concentration, then scale.

### DEMOTE (per MUTATION_THREE_AXIS_PROTOCOL):
1. **BOND** — WR=21.74%, PF<0.5. **KILL** — no path to profitability.
2. **ETF** — n=9 in 90 days. **KILL** — insufficient data, no edge.
3. **UNKNOWN** — 0% WR. **KILL** — classification failure, should never trade.
4. **INDEX** — n=6, 33% WR. **DEMOTE to paper trading** — insufficient data.
5. **FOREX** — WR=43.51%, negative expectancy. **DEMOTE to paper trading** — no PROVEN cells after Bonferroni.
6. **COMMODITY** — WR=36.27%, negative expectancy. **DEMOTE to paper trading** — no PROVEN cells.
7. **FUTURES** — WR=42.86%, fails validation. **DEMOTE to paper trading**.
8. **MEME** — n=4. **KILL** — insufficient data.

### CRITICAL SYSTEM FIXES (before any scaling):
1. **Execution layer**: `opened` must NEVER exceed `passed_smart`. Currently 97% of trades bypass the gate. This is the #1 issue.
2. **HC filter**: 0 trades passed in 90 days means the filter is broken. Either lower thresholds or fix the scoring.
3. **Trust scoring**: All PROVEN cells show `trust=UNK`. The trust dimension is not being computed.
4. **EQUITY "PROVEN" cell**: PF=214.8 is impossible. Investigate data pipeline for look-ahead bias or symbol concentration.

### Honest Assessment:
The system is **not ready for real money** in its current state. The only statistically valid edge (CRYPTO C0.75-0.80/S50) is real but the infrastructure cannot execute it. The EQUITY "edge" is a data artifact. Most classes are net negative. **Fix the pipeline before scaling anything.**

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — n=68, WR_shrunk=87.5, PF=214.825 is statistically impossible in live markets; mean_reversion cell shows clear data bug or look-ahead.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65.
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: No edge — n_closed=6, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80.
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise — n=41 cells fail bonferroni; PF~3.97 does not survive correction and shows no stability.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: HC_MIN_CONF = 0.82.
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: Real — n=216-217, WR_shrunk~74.7-75, PF=3.99, holdout_pass=true, bonferroni_pass=true, wr_z>7.9; no obvious leakage.
- 90d expected P&L (1% risk, $100k): ~$28,400 (216 trades × $1000 risk × 1.44% avg_pnl, 0.15% slippage, 0.8 fill rate).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 48.
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: Noise — n=38 cells fail bonferroni; PF=7.2 collapses out-of-sample.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 70.
- Confidence (1-5): 4

### ETF
- Real/noise verdict: No edge — n_closed=9, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 75.
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: No edge — n_closed=9, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80.
- Confidence (1-5): 5

### MEME
- Real/noise verdict: No edge — n_closed=4, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 85.
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: No edge — n=21 cell fails holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 75.
- Confidence (1-5): 5

### BOND
- Real/noise verdict: No edge — n_closed=23, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 80.
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with verified, multi-window edge). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL (mean_reversion cell is leakage recurrence). All other classes have zero actionable edge.
