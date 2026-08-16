# Pick Funnel Swarm Verdict — 2026-08-16 04:14 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260816T041355Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- **Real/noise verdict:** *Mostly real but high‑risk.*  
  The “trust=UNK & fam=unknown & dir=LONG” cell shows **n = 217**, **WR ≈ 84 % (shrunk ≈ 81 %)**, **PF ≈ 9.7** and passes both hold‑out and Bonferroni tests.  The numbers are very strong, but the PF is unusually large for a diversified crypto basket and the “unknown” family suggests the signal may be driven by a handful of coins (possible concentration/leakage).  Treat as a **real but fragile** edge –‑‑ confidence **3/5**.  

- **90d expected P&L (1 % risk, $100 k):** ≈ **$87 k**  
  *Assumptions*: 1 % risk = $1 k per trade, stop‑loss set at the observed loss magnitude (≈ 0.94 % of notional).  This yields an average trade size of ≈ $106 k and an expected net profit of ≈ $401 per trade.  217 closed trades × $401 ≈ **$87 k**.  Slippage is ignored (assume execution at model price).  

- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO = 0.85` (raise the minimum Smart‑Pick score for crypto).  Tightening this gate should keep the high‑PF “unknown” cell while discarding lower‑quality noise, likely raising the overall PF further.  

- **Confidence (1‑5):** **3**  

---

### BOND
- **Real/noise verdict:** *No statistically‑significant edge.*  
  The best cell has **n = 23**, **WR ≈ 13 %**, **PF ≈ 0.47**, and fails the hold‑out test.  The signal is weak

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

**SYSTEM-WIDE VERDICT: This funnel is catastrophically broken. The "PROVEN" edges are statistical artifacts of a leaky pipeline, and the live trading behavior is disconnected from the scoring gates entirely.**

---

### CRYPTO
- Real/noise verdict: **NOISE / LEAKAGE.** The "PROVEN" cells (WR 79-84%, PF 4-9) are impossible. The `trust=UNK` dimension is a red flag—it means the system has no idea who generated the signal, which is a classic symptom of a data pipeline bug (e.g., look-ahead bias, stale timestamps, or a single-symbol concentration). The `holdout_pf` of 16.69 vs `train_pf` of 6.65 is a 2.5x jump—this is not a stable edge; it's a leak that got worse over time. The `wr_z` of 9.98 is beyond the realm of realistic trading (a z-score that high implies a 1-in-10^23 event). **This is not an edge; it is a bug.**
- 90d expected P&L (1% risk, $100k): **$0.00** (Do not trade. The edge is not real; any P&L estimate is fiction.)
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO` = **95** (Raise the bar so high that only a handful of trades pass, forcing a manual review of every single one. The current 2717 "passed_smart" is a firehose of garbage.)
- Confidence (1-5): **1** (Zero confidence in the edge; high confidence in the leak.)

---

### BOND
- Real/noise verdict: **NOISE.** WR 15.62% on n=32 decisive trades is a disaster. The `best_pf_overall` cell (PF 0.47) is negative expectancy. The `holdout_pf` of 0.0 confirms the signal died out-of-sample. This class is actively destroying capital.
- 90d expected P&L (1% risk, $100k): **-$1,800** (32 trades * 1% risk * (0.13 win rate * 2R avg win - 0.87 loss rate * 1R avg loss) ≈ -$1,800. Slippage on bonds is minimal, but the edge is so negative it doesn't matter.)
- Gate change: `BOND_MIN_SCORE` = **100** (Effectively kill the class. The scanner is producing 16 "smart" picks out of 298 scans, and they are all losers. The signal is not there.)
- Confidence (1-5): **1** (High confidence it's a loser.)

---

### FOREX
- Real/noise verdict: **NOISE / LEAKAGE.** The "PROVEN" cells (WR 68%, PF 3.0) are suspicious. The `trust=UNK` dimension again flags a pipeline issue. The `conf=C0.75-0.80` band is the *lowest* confidence band, yet it produces the "best" results—this is inverted logic and a classic sign of overfitting to a specific bucket. The `holdout_pass: true` is misleading because the train/holdout split is likely not chronological (it's random), so it doesn't test for temporal stability. **The 34% overall WR on 641 decisive trades is the real story: this class is a coin flip with bad odds.**
- 90d expected P&L (1% risk, $100k): **-$2,100** (641 trades * 1% risk * (0.34 * 1.5R - 0.66 * 1R) ≈ -$2,100. Slippage on forex is ~0.5 pips, but the negative expectancy dominates.)
- Gate change: `SMART_PICKS_MIN_SCORE_FOREX` = **85** (The current gate passes 92% of scans (18901/20549). This is a filter that filters nothing. Raise it to 85 to cut the noise floor dramatically.)
- Confidence (1-5): **1** (High confidence the "edge" is a leak; low confidence in any positive outcome.)

---

### EQUITY
- Real/noise verdict: **NOISE / LEAKAGE.** The "PROVEN" cell (WR 98.51%, PF 181) is an absurdity. A PF of 181 means you make $181 for every $1 you risk. This is not trading; this is a data error. The `train_n` of 17 is tiny, and the `holdout_n` of 50 is still small. The `fam=mean_reversion` with `score_dec=S40` is likely a single stock (e.g., a ticker that had a 40% drop and then a dead-cat bounce, captured by a stale price feed). **This is a single-symbol concentration artifact, not a repeatable edge.**
- 90d expected P&L (1% risk, $100k): **$0.00** (Do not trade. The "edge" is a phantom. The real WR of 47.75% on 423 decisive trades is the truth, and it's below breakeven after costs.)
- Gate change: `SMART_PICKS_MIN_SCORE_EQUITY` = **90** (Force the system to only pick the absolute highest-conviction names. The current 241 "passed_smart" is still too loose.)
- Confidence (1-5): **1** (Zero confidence in the "edge"; high confidence in the leak.)

---

### COMMODITY
- Real/noise verdict: **NOISE.** No PROVEN cells. The `best_pf_overall` (PF 6.1) fails the holdout test (`holdout_pass: false`). The `train_n` of 6 is statistically meaningless. The overall WR of 28.31% on 332 decisive trades is a disaster. **This class is a proven loser.**
- 90d expected P&L (1% risk, $100k): **-$4,200** (332 trades * 1% risk * (0.28 * 2R - 0.72 * 1R) ≈ -$4,200. Commodity slippage is high, making this worse.)
- Gate change: `COMMODITY_MIN_SCORE` = **100** (Kill it. The scanner is producing 6302 "smart" picks out of 8358 scans—a 75% pass rate. It is not discriminating. The edge is not there.)
- Confidence (1-5): **1** (High confidence it's a loser.)

---

### FUTURES
- Real/noise verdict: **NOISE.** n=27 decisive trades is far too small to conclude anything. The `best_pf_overall` (PF 1.55) fails the holdout test (`holdout_pass: false`). The WR of 48.15% is a coin flip. **Insufficient data, no edge.**
- 90d expected P&L (1% risk, $100k): **$0.00** (Too few trades to matter. The expected value is roughly zero, but the variance is huge.)
- Gate change: `FUTURES_MIN_SCORE` = **90** (Raise the bar to ensure only the most extreme setups are taken. The current 108 "passed_smart" is too loose for a class with such low volume.)
- Confidence (1-5): **2** (Low confidence in any edge; high confidence in the lack of data.)

---

### UNKNOWN
- Real/noise verdict: **NOISE.** WR 0% on 10 decisive trades. The class is a catch-all for misclassified assets. **It is a garbage bin, and it should be emptied.**
- 90d expected P&L (1% risk, $100k): **-$1,000** (10 trades * 1% risk * (0% win rate) = -$1,000. It's a guaranteed loss.)
- Gate change: `UNKNOWN_MIN_SCORE` = **100** (Kill it. No trade should ever be taken on an asset we cannot classify.)
- Confidence (1-5): **5** (High confidence this is a loser.)

---

### ETF
- Real/noise verdict: **NOISE.** WR 12% on 25 decisive trades. The `best_pf_overall` (PF 0.02) is a catastrophic negative expectancy. **This class is a capital incinerator.**
- 90d expected P&L (1% risk, $100k): **-$2,200** (25 trades * 1% risk * (0.12 * 1R - 0.88 * 1R) ≈ -$2,200. The avg_pnl_pct of -1.54% confirms the bleed.)
- Gate change: `ETF_MIN_SCORE` = **100** (Kill it. The scanner is producing 354 "smart" picks out of 561 scans, and they are all garbage.)
- Confidence (1-5): **5** (High confidence it's a loser.)

---

### MEME
- Real/noise verdict: **NOISE.** n=2 decisive trades. Statistically meaningless. The 50% WR is a coin flip on a sample size of two. **No data, no edge.**
- 90d expected P&L (1% risk, $100k): **$0.00** (Too few trades to matter.)
- Gate change: `MEME_MIN_SCORE` = **100** (Kill it. The volatility is not worth the risk with no proven edge.)
- Confidence (1-5): **1** (No confidence in anything.)

---

### INDEX
- Real/noise verdict: **NOISE.** n=10 decisive trades. WR 30% is bad, but the sample size is too small to be conclusive. **Insufficient data, likely a loser.**
- 90d expected P&L (1% risk, $100k): **-$700** (10 trades * 1% risk * (0.30 * 1R - 0.70 * 1R) ≈ -$700. The negative expectancy is clear.)
- Gate change: `INDEX_MIN_SCORE` = **100** (Kill it. The scanner is passing 978 out of 1209 scans—an 80% pass rate. It is not a filter.)
- Confidence (1-5): **2** (Low confidence in the edge; moderate confidence in the negative expectancy.)

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY:** **NOTHING.** There is not a single asset class with a statistically valid, holdout-passing, non-leaking edge. The "PROVEN" cells are artifacts of a broken pipeline (likely look-ahead bias in the `trust=UNK` data or single-symbol concentration). The live trading behavior (opened/closed counts) is completely disconnected from the scoring gates—we are opening 7147 CRYPTO trades but only 2717 passed the "smart" gate. **The gates are not being enforced in production.**

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:** **BOND, COMMODITY, ETF, UNKNOWN.** These four classes have decisively negative WRs (15.62%, 28.31%, 12%, 0%) with sufficient sample sizes (n>25) to be statistically significant. They are not "underperforming"; they are **proven capital destroyers**. Per the protocol, they should be **mutated** (e.g., completely rewrite the scoring logic) before being **killed**. The current gates are not just failing to find an edge; they are actively selecting for losers.

**The #1 action item is not a gate change; it is a pipeline audit.** The `trust=UNK` dimension appearing in every "PROVEN" cell is a smoking gun. Fix the data ingestion and timestamping bugs first. Then, and only then, can we trust any gate change.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Noise/leakage (PF 9.678 and 4.158 with WR_shrunk 81%/77% on n=217-236 is statistically impossible in live markets; holdout_pass and bonferroni flags do not override extreme values consistent with single-symbol concentration or timestamp leakage).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge; any sizing produces drawdown).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 85
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise (no proven cells; all best_pf_overall failed holdout and bonferroni with WR_shrunk ~30%).
- 90d expected P&L (1% risk, $100k): -$1,200 (negative expectancy on decisive trades).
- Gate change: None (disable BOND path)
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Marginal noise (two proven cells with n=113-121, WR_shrunk 65%, PF~3, holdout_pass true, but flagged consensus-style cells historically leak and PF remains elevated vs. real retail execution).
- 90d expected P&L (1% risk, $100k): $180 (tiny positive after 0.2% slippage assumption on 121 trades).
- Gate change: HC_MIN_CONF = 0.82
- Confidence (1-5): 3

### EQUITY
- Real/noise verdict: Noise/leakage (PF 181 on n=67 with WR_shrunk 87% is data error or single-name concentration; violates all realistic market bounds).
- 90d expected P&L (1% risk, $100k): $0 (edge does not exist).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 90
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise (no proven cells; best_pf_overall failed holdout and bonferroni).
- 90d expected P&L (1% risk, $100k): -$950 (negative on decisive trades).
- Gate change: None (disable COMMODITY path)
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise (no proven cells; best_pf_overall failed holdout with negative WR_z).
- 90d expected P&L (1% risk, $100k): -$400.
- Gate change: None (disable FUTURES path)
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise (no proven cells; zero wins on decisive trades).
- 90d expected P&L (1% risk, $100k): -$300.
- Gate change: None (drop UNKNOWN)
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise (no proven cells; best_pf_overall failed holdout with WR 9.5%).
- 90d expected P&L (1% risk, $100k): -$1,100.
- Gate change: None (disable ETF path)
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise (n=2 decisive; no proven cells).
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None (disable MEME path)
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise (n=10 decisive; no proven cells).
- 90d expected P&L (1% risk, $100k): -$150.
- Gate change: None (disable INDEX path)
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up TODAY: none (zero classes pass leakage and stability filters).  
Demote per MUTATION_THREE_AXIS_PROTOCOL.md: EQUITY and CRYPTO first (proven cells are leakage recurrences), followed by BOND/COMMODITY/ETF/FUTURES (zero edge). FOREX is the only marginal survivor but still requires gate tightening before any capital.
