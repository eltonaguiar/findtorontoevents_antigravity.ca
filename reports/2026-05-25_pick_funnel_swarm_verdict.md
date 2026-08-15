# Pick Funnel Swarm Verdict — 2026-08-15 04:11 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260815T041028Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- **Real/noise verdict:** **Real** – Proven cells have n ≈ 220‑236, WR shrunk ≈ 81‑82 % and PF ≈ 4‑10. Hold‑out and Bonferroni tests pass, and there is no known leakage (the “trust=UNK” flag simply means the model could not assign a trust band, not that future data was used).  
- **90d expected P&L (1 % risk, $100 k):** ≈ $2,860  (217 trades × 1.317 % × $1,000).  
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` → **70** (lower the minimum Smart‑Pick score from the default 80 to 70 so more of the high‑PF “trust=UNK & conf=0.75‑0.80” picks survive the Smart gate).  
- **Confidence (1‑5):** 4  

### EQUITY
- **Real/noise verdict:** **Real but fragile** – Proven cells (n = 67) show WR shrunk ≈ 87 % and an astronomic PF ≈ 182, with hold‑out and Bonferroni passes. The sample is small and the edge lives in a low‑confidence band (C < 0.60), so concentration risk and over‑fit are possible, but the statistical tests deem it real.  
- **90d expected P&L (1 % risk, $100 k):** ≈ $723  (67 trades × 1.079 % × $1,000).  
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` → **55** (current threshold is ~80; dropping it lets the low‑confidence mean‑reversion S40 picks pass the Smart gate, unlocking the huge PF).  
- **Confidence (1‑5):** 3  

### FOREX
- **Real/noise verdict:** **Real** – Two Proven cells (n ≈ 113‑121) have WR shrunk ≈ 65‑67 % and PF ≈ 3.0, with both hold‑out and Bonferroni passes. No known leakage; the edge is spread across many symbols (the “mean_reversion” family appears in many pairs).  
- **90d expected P&L (1 % risk, $100 k):** ≈ $415  (121 trades × 0.343 % × $1,000 – using the higher‑average‑PNL cell).  
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` → **70** (current default ~80; a lower score admits more of the “trust=UNK & conf=0.75‑0.80 & rr=1.0‑1.5” picks).  
- **Confidence (1‑5):** 4  

### COMMODITY
- **Real/noise verdict:** **Noise** – No Proven cells. The best PF ≈ 6.1 fails hold‑out and Bonferroni; the edge is not statistically reliable and the earlier COT‑timing hypothesis (H‑001) already ruled out a similar signal.  
- **90d expected P&L (1 % risk, $100 k):** $0 (no statistically‑valid edge).  
- **Gate change:** *None recommended* – tightening the “RR≥2.0” requirement would only prune more noise.  
- **Confidence (1‑5):** 2  

### FOREX (duplicate – already covered)  

### FUTURES
- **Real/noise verdict:** **Noise** – No Proven cells; best PF ≈ 1.56 fails hold‑out. The earlier “futures_momentum_anti_signal” (H‑005) was killed, and the remaining patterns do not survive statistical tests.  
- **90d expected P&L (1 % risk, $100 k):** $0.  
- **Gate change:** *None recommended* – lowering the trust threshold would admit many low‑quality picks without improving PF.  
- **Confidence (1‑5):** 2  

### ETF
- **Real/noise verdict:** **Noise** – No Proven cells; PF ≈ 0.02, WR shrunk ≈ 29 % – clearly a loss‑making signal.  
- **90d expected P&L (1 % risk, $100 k):** $0.  
- **Gate change:** *None recommended*.  
- **Confidence (1‑5):** 1  

### BOND
- **Real/noise verdict:** **Noise** – No Proven cells; all PF < 1, hold‑out fails.  
- **90d expected P&L (1 % risk, $100 k):** $0.  
- **Gate change:** *None recommended*.  
- **Confidence (1‑5):** 1  

### MEME
- **Real/noise verdict:** **Noise** – Only 2 closed trades, no Proven cell; statistical power insufficient.  
- **90d expected P&L (1 % risk, $100 k):** $0.  
- **Gate change:** *None recommended*.  
- **Confidence (1‑5):** 1  

### UNKNOWN
- **Real/noise verdict:** **Noise** – No Proven cells; WR = 0 %.  
- **90d expected P&L (1 % risk, $100 k):** $0.  
- **Gate change:** *None recommended*.  
- **Confidence (1‑5):** 1  

### INDEX
- **Real/noise verdict:** **Noise** – No Proven cells; PF ≈ 0, WR ≈ 30 % but fails the Bayesian‑shrunk WR ≥ 55 % rule.  
- **90d expected P&L (1 % risk, $100 k):** $0.  
- **Gate change:** *None recommended*.  
- **Confidence (1‑5):** 1  

---

## SYSTEM‑WIDE Conclusion
- **Scale‑up today:** **CRYPTO** – It has the largest statistically‑validated edge (high PF, solid win‑rate, >200 closed trades) and a modest gate change can unlock many more of the same high‑PF picks, giving an estimated $2.9 k profit on a $100 k account at 1 % risk per trade.  
- **Demote / kill:** **COMMODITY** – No proven edge, prior leakage hypothesis already rejected, and the remaining signal fails hold‑out tests. It should be removed from the production pipeline per the *MUTATION_THREE_AXIS_PROTOCOL* before any further resources are spent.  

*All other classes either have very small real edges (EQUITY, FOREX) that require careful risk management, or have no statistically‑valid edge and should remain out of the live allocation.*

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT

Before per-class analysis, the most glaring issue: **the funnel is broken**. Look at EQUITY: 5,690 scanned → 235 passed_smart → 16 passed_verified_alpha → 2 passed_high_conviction → 3 passed_proven. But **4,043 opened** — that's 71% of ALL scanned signals got opened, including 3,808 that FAILED the smart gate. The HC filter (score>=80, conf>=0.75, trust>=60) passed only 2 EQUITY signals, yet 4,043 trades were opened. **The gates are not being enforced on live trades.** This is either a data pipeline bug or the dashboard is showing theoretical gates while the execution layer ignores them.

---

### EQUITY
- **Real/noise verdict**: The "PROVEN" cells (WR 98.5%, PF 181.7) are **statistical artifacts, not edges**. n=67 with 66 wins, but train_n=17 and holdout_n=50 — the train/holdout split is 25/75, not 50/50, suggesting the split is not chronological. PF=181.7 with avg_pnl=1.08% means the single loss was ~0.5% and wins averaged ~1.1% — this is a **mean_reversion S40 LONG** cell that is almost certainly **single-symbol concentration** (likely one ticker that mean-reverted consistently). The shrunk WR of 87.4% is still absurdly high for 67 trades. **This is leakage or overfitting to a single symbol's regime.** The 423 decisive trades overall have WR=47.75% — the base rate is coin-flip. The 3 "proven" cells are all the SAME cell with different dimension subsets (trust=UNK & fam=mean_reversion & score_dec=S40 = conf=C<0.60 & fam=mean_reversion & score_dec=S40 = fam=mean_reversion & dir=LONG & score_dec=S40). **This is one edge, not three, and it's not real.**
- **90d expected P&L (1% risk, $100k)**: If we traded ALL 423 decisive signals at 1% risk: 202 wins × $1,000 × avg_win_pct + 221 losses × $1,000 × avg_loss_pct. With WR=47.75% and typical R:R ~1:1, expected P&L ≈ **-$18,000** (negative expectancy). If we ONLY traded the "proven" cell (67 trades, 98.5% WR): 66 × $1,000 × 1.08% + 1 × $1,000 × 0.5% ≈ **$712.80** — but this is fake money from a fake edge.
- **Gate change**: `SMART_PICKS_MIN_SCORE_EQUITY = 85` (raise from current ~70). This would kill the mean_reversion S40 noise. But the REAL fix is enforcing the gate — 4,043 opened vs 235 passed_smart means the gate isn't being applied.
- **Confidence (1-5)**: 1 — the "edge" is a mirage.

---

### FOREX
- **Real/noise verdict**: The two "PROVEN" cells (WR 68%, PF 3.03) are **borderline real but fragile**. n=113 and n=121 are decent sample sizes. Shrunk WR 65.4% and 65.3% are credible. Holdout PF 3.23 and 2.88 both pass. BUT: the cells are `trust=UNK & conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion` and the same minus fam. **trust=UNK means the trust score is unknown/zero** — this is a red flag. The `consensus` source you flagged is NOT in these cells (source is not a dimension), so the suspiciously-high PF you mentioned is not here. However, the base rate for FOREX is WR=34.27% across 642 decisive trades — the overall class is a **loser**. The edge is confined to a narrow band (conf 0.75-0.80, RR 1.0-1.5, mean_reversion) and may be **regime-dependent** — 90 days of mean-reversion in FX could be one market regime. The train/holdout split (49/64 and 52/69) is roughly chronological and both pass, which is encouraging. **Verdict: possibly real, but fragile and narrow.**
- **90d expected P&L (1% risk, $100k)**: Trading ONLY the proven cell (121 trades): 82 wins × $1,000 × 0.28% avg_win + 39 losses × $1,000 × 0.28% avg_loss ≈ 82×$2.80 + 39×$2.80 ≈ **$338.80** — but this ignores that avg_pnl_pct=0.2834% is the NET, so it's 121 × $1,000 × 0.2834% ≈ **$342.91**. If we traded ALL 642 decisive signals: 220 wins, 422 losses, WR=34.27%, avg_pnl is negative (PF<1 implied) → **-$15,000 to -$20,000**.
- **Gate change**: `SMART_PICKS_MIN_CONF_FOREX = 0.75` (enforce the confidence floor). Currently the gate passes 18,864 of 20,648 scanned (91%) — the gate is a sieve. Set `SMART_PICKS_MIN_SCORE_FOREX = 75` to cut the noise.
- **Confidence (1-5)**: 2 — the edge is narrow and the class base rate is negative.

---

### CRYPTO
- **Real/noise verdict**: The "PROVEN" cells (WR 83.9%, PF 9.68) are **statistically significant but suspicious**. n=217 and n=236 are solid. Bonferroni_pass=true and holdout_pass=true. BUT: `trust=UNK & fam=unknown & dir=LONG` — **fam=unknown means the strategy family is not classified**. This is a **catch-all bucket** that is likely absorbing multiple unrelated signals. PF=9.68 with avg_pnl=1.32% means the average win is ~1.4% and average loss is ~0.15% — this is a **very tight stop-loss profile** that could be **stop-hunting or data artifact** (e.g., trades that hit a 0.1% stop are recorded as losses, but the win distribution is fat-tailed). The `ml` cells you flagged are NOT in the proven list — the proven cells are `trust=UNK & fam=unknown` and `conf=C0.75-0.80 & dir=LONG & score_dec=S50`. The score_dec=S50 means the score's decimal is 50 (i.e., score is X.50) — this is a **rounding artifact**, not a real signal. **Verdict: the edge is real in-sample but the dimensions are suspicious (fam=unknown, score_dec=S50). Likely overfit to a specific score range that won't generalize.**
- **90d expected P&L (1% risk, $100k)**: Trading the proven cell (236 trades): 187 × $1,000 × 1.21% + 49 × $1,000 × 1.21% ≈ 236 × $12.10 ≈ **$2,855.60**. Trading ALL 2,883 decisive: 1,350 wins, 1,533 losses, WR=46.83%, avg_pnl is slightly positive (PF≈1.1) → **+$5,000 to +$8,000**.
- **Gate change**: `SMART_PICKS_MIN_SCORE_CRYPTO = 75` (raise from current). Also add a **family classification requirement** — reject `fam=unknown` signals. This kills the suspicious catch-all bucket.
- **Confidence (1-5)**: 2 — the edge is real but the dimensions are noise-like.

---

### COMMODITY
- **Real/noise verdict**: **NO EDGE.** Zero proven cells. Best PF=6.11 but holdout_pass=false, bonferroni_pass=false, wr_z=1.37 (not significant). The base rate is WR=28.31% across 332 decisive trades — **catastrophically bad**. The best cell (RR>=2.0, LONG, alpha_engine) has n=34, WR=61.76% but train_n=6 and holdout_n=28 — the train set is too small to validate. This is **sample noise**. The rejected H-001 (COT look-ahead) and H-036 (inventory direction) confirm this class has been repeatedly falsified.
- **90d expected P&L (1% risk, $100k)**: Trading ALL 332 decisive: 94 wins, 238 losses, WR=28.31%. With avg_loss likely ~1% and avg_win ~1.5% (typical commodity R:R), expected P&L ≈ 94×$15 + 238×$10 ≈ **-$980**. Trading the best cell (34 trades): 21×$33.70 + 13×$33.70 ≈ **$1,145.80** — but this is noise.
- **Gate change**: `SMART_PICKS_MIN_SCORE_COMMODITY = 90` (effectively kill the class). Or set `COMMODITY_ENABLED = False` in the scanner config.
- **Confidence (1-5)**: 1 — no edge, repeatedly falsified.

---

### MEME
- **Real/noise verdict**: **NO EDGE.** n=2 closed trades. Statistically meaningless. WR=50% on 2 trades is a coin flip.
- **90d expected P&L (1% risk, $100k)**: **$0** — cannot compute with n=2.
- **Gate change**: `SMART_PICKS_MIN_SCORE_MEME = 95` (kill the class — 16 scanned signals is not a viable universe).
- **Confidence (1-5)**: 1 — no data.

---

### BOND
- **Real/noise verdict**: **NO EDGE — ACTIVELY LOSING.** WR=14.29% across 35 decisive trades. Best cell has WR=13.04%, PF=0.47, wr_z=-3.545 (significantly NEGATIVE). This is not noise — this is a **reliably losing signal**. The bond_scanner is picking losers.
- **90d expected P&L (1% risk, $100k)**: Trading ALL 35 decisive: 5 wins, 30 losses. With avg_pnl=-0.243% on the best cell, expected P&L ≈ 35 × $1,000 × (-0.24%) ≈ **-$84**. But the full class is worse — likely **-$500 to -$1,000**.
- **Gate change**: `SMART_PICKS_MIN_SCORE_BOND = 95` (kill the class). Or `BOND_SCANNER_ENABLED = False`.
- **Confidence (1-5)**: 1 — reliably negative.

---

### ETF
- **Real/noise verdict**: **NO EDGE — ACTIVELY LOSING.** WR=12% across 25 decisive trades. Best cell has WR=9.52%, PF=0.02, wr_z=-3.71 (significantly negative). The ETF scanner is picking losers with near-certainty.
- **90d expected P&L (1% risk, $100k)**: Trading ALL 25 decisive: 3 wins, 22 losses. avg_pnl=-1.54% on the best cell → 25 × $1,000 × (-1.54%) ≈ **-$385**. Full class likely **-$800 to -$1,500**.
- **Gate change**: `SMART_PICKS_MIN_SCORE_ETF = 95` (kill the class). Or `ETF_SCANNER_ENABLED = False`.
- **Confidence (1-5)**: 1 — reliably negative.

---

### UNKNOWN
- **Real/noise verdict**: **NO EDGE.** WR=0% across 10 decisive trades. All losses. But n=10 is too small to be conclusive — it's just noise in the wrong direction.
- **90d expected P&L (1% risk, $100k)**: 10 × $1,000 × (-1%) ≈ **-$100**.
- **Gate change**: `SMART_PICKS_MIN_SCORE_UNKNOWN = 95` (kill the class — UNKNOWN assets should never be traded).
- **Confidence (1-5)**: 1 — no data.

---

### FUTURES
- **Real/noise verdict**: **NO EDGE.** WR=48.15% across 27 decisive trades — coin flip. Best cell has WR=45.83%, PF=1.558 but holdout_pass=false, wr_z=-0.409 (not significant). The rejected H-005 (futures_momentum_anti_signal) confirms this class has been falsified.
- **90d expected P&L (1% risk, $100k)**: 13 wins, 14 losses. With avg_pnl=0.32% on the best cell, expected P&L ≈ 27 × $1,000 × 0.32% ≈ **$86.40** — but this is noise.
- **Gate change**: `SMART_PICKS_MIN_SCORE_FUTURES = 90` (effectively kill).
- **Confidence (1-5)**: 1 — no edge.

---

### INDEX
- **Real/noise verdict**: **NO EDGE.** WR=30% across 10 decisive trades. n=10 is too small. Best cell is empty (no cells with n>=20).
- **90d expected P&L (1% risk, $100k)**: 3 wins, 7 losses. Expected P&L ≈ **-$200 to -$400** (no reliable avg_pnl data).
- **Gate change**: `SMART_PICKS_MIN_SCORE_INDEX = 90` (effectively kill).
- **Confidence (1-5)**: 1 — no data.

---

## SYSTEM-WIDE CONCLUSION

### Scale up TODAY:
**NONE.** There is no asset class with a statistically robust, holdout-validated, non-leakage edge that justifies real money. The closest candidates are:
- **FOREX** (n=121, WR=67.8%, PF=2.89, holdout_pass=true) — but trust=UNK and the class base rate is 34% WR. This is a narrow band edge that could be regime-dependent.
- **CRYPTO** (n=236, WR=79.2%, PF=4.16, holdout_pass=true) — but fam=unknown and score_dec=S50 are suspicious dimensions.

**If forced to pick one**: FOREX with the narrow gate (conf 0.75-0.80, RR 1.0-1.5, mean_reversion, LONG only) at 0.5% risk (half-size due to fragility). Expected 90d P&L: ~$170 on $100k. This is not worth the operational overhead.

### DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:
- **KILL**: BOND (WR=14%, PF<0.5, significantly negative), ETF (WR=12%, PF=0.02, significantly negative), COMMODITY (WR=28%, repeatedly falsified H-001/H-036), MEME (n=2, no data), UNKNOWN (WR=0%).
- **MUTATE**: EQUITY (the mean_reversion S40 cell needs investigation for single-symbol concentration before any further use), FUTURES (n=27, insufficient data — mutate to require n>=50 before trading), INDEX (n=10, insufficient data).

### The REAL problem:
**The funnel is not being enforced.** EQUITY: 4,043 opened vs 235 passed_smart. FOREX: 18,201 opened vs 18,864 passed_smart (this one is consistent). CRYPTO: 7,051 opened vs 2,791 passed_smart (2.5x over-trading). COMMODITY: 6,231 opened vs 6,284 passed_smart (consistent). **The HC filter (score>=80, conf>=0.75, trust>=60) passed 2 EQUITY signals, yet 4,043 trades were opened.** Either the dashboard is showing theoretical gates while execution ignores them, or there's a data pipeline bug where `opened` counts include signals that never went through the gate. **Fix the pipeline before tuning any constants.**

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: noise (PF=181 on n=67 with train_n=17 screams single-symbol concentration or leakage; WR_shrunk inflated)
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge)
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 2

### FOREX
- Real/noise verdict: marginal real (n=113 cell passed holdout + bonferroni, PF~3.0 reasonable; other cells weaker)
- 90d expected P&L (1% risk, $100k): $420 (assume ~80 qualifying trades at 0.3% avg edge after 0.05% slippage)
- Gate change: HC_MIN_CONF = 0.78
- Confidence (1-5): 3

### CRYPTO
- Real/noise verdict: noise (PF 9.678 and 4.158 on "unknown" fam + trust=UNK cells are statistically impossible without leakage or single-venue concentration)
- 90d expected P&L (1% risk, $100k): $0 (do not deploy)
- Gate change: SMART_PICKS_MIN_TRUST_CRYPTO = 40
- Confidence (1-5): 1

### COMMODITY
- Real/noise verdict: noise (all best_pf cells failed holdout + bonferroni; n=34 too small)
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge)
- Gate change: SMART_PICKS_MIN_RR_COMMODITY = 2.5
- Confidence (1-5): 1

### MEME
- Real/noise verdict: noise (n_closed=2, zero proven cells)
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge)
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 80
- Confidence (1-5): 1

### BOND
- Real/noise verdict: noise (all cells failed holdout + bonferroni, negative expectancy)
- 90d expected P&L (1% risk, $100k): -$180 (expected loss on any volume)
- Gate change: HC_MIN_TRUST = 70
- Confidence (1-5): 1

### ETF
- Real/noise verdict: noise (PF=0.02, WR_shrunk 29%, failed every test)
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge)
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 70
- Confidence (1-5): 1

### UNKNOWN
- Real/noise verdict: noise (n=10, zero edges)
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge)
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 75
- Confidence (1-5): 1

### FUTURES
- Real/noise verdict: noise (all cells failed holdout + bonferroni, negative holdout PF)
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge)
- Gate change: SMART_PICKS_MIN_TRUST_FUTURES = 50
- Confidence (1-5): 1

### INDEX
- Real/noise verdict: noise (n_closed=10, zero edges)
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge)
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 75
- Confidence (1-5): 1

**SYSTEM-WIDE CONCLUSION**  
Scale up TODAY: FOREX (only class with any statistically defensible cell).  
Demote per MUTATION_THREE_AXIS_PROTOCOL: CRYPTO and EQUITY (both show clear leakage signatures; mutate filters before any further capital allocation). All other classes already have no usable edge.
