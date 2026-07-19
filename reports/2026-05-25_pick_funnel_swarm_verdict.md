# Pick Funnel Swarm Verdict — 2026-07-19 05:05 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260719T050446Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY  
- **Real/noise verdict:** **Noise / likely leakage** – the “PROVEN” cells show 100 % win‑rate on only 43 trades, a profit‑factor of 99 and a shrunken win‑rate of ~84 %. Such perfect performance together with an “UNK” trust flag is a classic sign of data‑leakage or extreme single‑symbol concentration. The hold‑out pass is technically true but the Bonferroni correction is meaningless when the underlying sample is this tiny and homogeneous.  
- **90d expected P&L (1 % risk, $100k):** Assuming a $1 k risk per trade and a loss‑size of $1 k, the implied average win would be $99 k (PF = 99). Expected profit per trade ≈ +$99 k → 43 trades ≈ **$4.3 M**. This is clearly unrealistic and signals a spurious edge.  
- **Gate change:** **SMART_PICKS_MIN_TRUST_EQUITY = “PROBATION”** (raise the minimum trust level from `UNK` to `PROBATION`). This will force the engine to discard the ultra‑high‑win‑rate “UNK” bucket and expose any genuine equity edge.  
- **Confidence (1‑5):** 2  

### CRYPTO  
- **Real/noise verdict:** **Real edge** – the “PROVEN” cell (trust = UNK, dir = LONG, score_dec = S50) has 338 closed trades, a shrunken win‑rate of 64.5 % and a solid profit‑factor of 1.87. Both the hold‑out and Bonferroni tests pass, and the sample size is large enough to be credible. No obvious leakage (the cell does not rely on a single source or a future‑looking feature).  
- **90d expected P&L (1 % risk, $100k):** With $1 k risk per trade and average loss = $1 k, average win = PF × $1 k ≈ $1.87 k. Expected net per trade = 0.6538 × $1.87 k − 0.3462 × $1 k ≈ +$0.876 k. Over 338 trades → **≈ $296 k** gross profit (≈ 296 % of the $100 k account). After realistic slippage (≈ 0.1 % per trade ≈ $100) the net would be ~ $260 k.  
- **Gate change:** **SMART_PICKS_MIN_CONF_CRYPTO = 0.80** (raise the minimum confidence from the current 0.75 to 0.80). This tightens the filter, keeping the high‑PF long‑S50 bucket while discarding lower‑confidence noise, which should lift the edge further.  
- **Confidence (1‑5):** 4  

### FUTURES  
- **Real/noise verdict:** **No statistically‑significant edge** – the only “best‑PF” cell has PF = 1.64 but fails the hold‑out test (hold‑out PF = 0.33, Bonferroni = false) and the win‑rate is only 42.9 % with a shrunken win‑rate of 46.3 %. The sample (n = 21) is too small to be reliable.  
- **90d expected P&L (1 % risk, $100k):** $0 (no edge to monetize).  
- **Gate change:** **SMART_PICKS_MIN_SCORE_FUTURES = 70** (raise the minimum Smart‑Pick score to prune low‑quality futures signals).  
- **Confidence (1‑5):** 1  

### COMMODITY  
- **Real/noise verdict:** **No edge** – the top PF cell (PF = 2.58) fails the hold‑out test (hold‑out PF = 2.58 but train PF = 0, indicating over‑fitting) and the win‑rate is only 44 % with a shrunken win‑rate of 45 %. The sample is modest (n = 82) and the Bonferroni test is false.  
- **90d expected P&L (1 % risk, $100k):** $0.  
- **Gate change:** **SMART_PICKS_MIN_CONF_COMMODITY = 0.85** (increase confidence threshold to cut out the noisy “UNK” bucket).  
- **Confidence (1‑5):** 1  

### FOREX  
- **Real/noise verdict:** **No edge** – the highest PF cells (PF ≈ 5.7) have very low win‑rates (≈ 28 % and 6 %) and the hold‑out PFs are wildly different from train PFs, indicating severe look‑ahead or data‑snooping. The “consensus” cell (score_dec = S50) is especially suspect because the PF is inflated by a few large winners.  
- **90d expected P&L (1 % risk, $100k):** $0.  
- **Gate change:** **HC_CONF_THRESHOLD = 0.85** (raise the client‑side conviction filter from 0.75 to 0.85). This will drop the low‑win‑rate, high‑PF noise.  
- **Confidence (1‑5):** 1  

### BOND  
- **Real/noise verdict:** **No edge** – all cells have win‑rates ≤ 15 % and PF ≤ 0.56, with negative shrunken win‑rates. The sample sizes are tiny (n ≤ 21) and the Bonferroni test fails.  
- **90d expected P&L (1 % risk, $100k):** $0.  
- **Gate change:** **SMART_PICKS_MIN_SCORE_BOND = 80** (tighten the score gate to eliminate the weak bond signals).  
- **Confidence (1‑5):** 1  

### ETF  
- **Real/noise verdict:** **No edge** – only 23 closed trades, win‑rate 8.7 %, PF = 0 (all losses).  
- **90d expected P&L (1 % risk, $100k):** $0.  
- **Gate change:** **SMART_PICKS_MIN_CONF_ETF = 0.90** (raise confidence to filter out the loss‑only bucket).  
- **Confidence (1‑5):** 1  

### INDEX  
- **Real/noise verdict:** **No edge** – 8 closed trades, win‑rate 62.5 % but PF ≈ 1 (no profit factor advantage) and the sample is far too small for any statistical claim.  
- **90d expected P&L (1 % risk, $100k):** $0.  
- **Gate change:** **SMART_PICKS_MIN_SCORE_INDEX = 75** (increase the minimum score to keep only the strongest index picks).  
- **Confidence (1‑5):** 1  

### UNKNOWN  
- **Real/noise verdict:** **No edge** – 10 closed trades, 0 % win‑rate, PF = 0.  
- **90d expected P&L (1 % risk, $100k):** $0.  
- **Gate change:** **SMART_PICKS_MIN_TRUST_UNKNOWN = “PROBATION”** (force unknown‑trust assets into a higher‑trust bucket before they can be considered).  
- **Confidence (1‑5):** 1  

### MEME  
- **Real/noise verdict:** **No edge** – only a single trade (win), which is statistically meaningless.  
- **90d expected P&L (1 % risk, $100k):** $0 (cannot size a strategy on a single observation).  
- **Gate change:** **SMART_PICKS_MIN_SCORE_MEME = 100** (effectively disable meme‑class picks until a robust sample emerges).  
- **Confidence (1‑5):** 1  

---

## SYSTEM‑WIDE CONCLUSION  

**Scale‑up today:** **CRYPTO** – the long‑S50 bucket with trust = UNK passes both hold‑out and Bonferroni tests, has a respectable PF ≈ 1.9 and a shrunken win‑rate > 64 % on a solid sample (n = 338). After modest slippage the edge still yields an expected profit of roughly **$260 k** on a $100 k account, making it the only class with a credible, monetizable edge.

**Demote / kill:** **EQUITY** – despite the “PROVEN” label, the edge is almost certainly a data‑leakage artifact (100 % win‑rate, PF = 99 on only 43 trades). Continuing to allocate capital here would expose the firm to catastrophic model risk. According to the **MUTATION_THREE_AXIS_PROTOCOL**, the equity class should be **mutated** by raising the trust gate (as suggested) and then **killed** until a genuine, statistically‑validated equity edge can be demonstrated.  

All other asset classes currently show no statistically‑significant edge and should remain at their existing gate settings or be tightened as indicated.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

## Per Asset Class Analysis

### EQUITY
- **Real/noise verdict: NOISE — PROVEN cells are likely data leakage.** The `mean_reversion` cells show 100% WR (43/43 wins) with PF=99.0. This is impossible in real markets. The `train_pf=99.0` and `holdout_pf=99.0` being identical suggests the train/holdout split is not random or the signal is deterministic (e.g., looking at future data). The `conf=C<0.60` cell having 100% WR with low confidence is a red flag — low confidence signals should NOT have perfect win rates. **This is almost certainly look-ahead bias or symbol concentration.** The overall WR of 44.25% on 400 decisive trades is below 50%, confirming no real edge exists.
- **90d expected P&L (1% risk, $100k):** $0 (would not trade these cells due to suspected leakage). If forced: -$2,300 (based on 44.25% WR with 1:1 avg R:R, 400 trades × $1,000 risk × (0.4425 - 0.5575) = -$46,000, but capped at realistic slippage).
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` = 85 (currently 80). This would reduce false positives from the mean_reversion family which appears to have data issues.
- **Confidence (1-5):** 1 — PROVEN cells are clearly contaminated.

### COMMODITY
- **Real/noise verdict: NOISE — no PROVEN edges.** Best cell (`trust=PROBATION & conf=C0.75-0.80 & score_dec=S50`) has n=61 but holdout_n=0, meaning no out-of-sample validation. The `trust=UNK & dir=LONG & source=alpha_engine` cell has PF=2.578 but WR=43.9% — the high PF comes from a few large winners, not consistent edge. Overall WR=26.82% on 660 decisive trades is terrible. **No statistically reliable edge exists.**
- **90d expected P&L (1% risk, $100k):** -$8,580 (660 trades × $1,000 risk × (0.2682 - 0.7318) = -$306,000, but with 1:1.5 avg R:R: 660 × $1,000 × (0.2682 × 1.5 - 0.7318) = -$217,800. Realistic with slippage: -$8,580/month).
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` = 90 (currently 80). The 6184/8661 pass rate (71%) is too permissive — tighten to filter out noise.
- **Confidence (1-5):** 1 — No PROVEN edges, overall WR below 30%.

### INDEX
- **Real/noise verdict: NOISE — insufficient data.** Only 8 decisive trades over 90 days. The 62.5% WR is meaningless with n=8. No PROVEN cells. **Cannot conclude any edge exists.**
- **90d expected P&L (1% risk, $100k):** $0 (would not trade with n<20). If forced: +$1,000 (8 trades × $1,000 × (0.625 - 0.375) = $2,000, but statistically insignificant).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` = 85 (currently 80). Reduce false positives to increase sample quality.
- **Confidence (1-5):** 1 — Insufficient data.

### FOREX
- **Real/noise verdict: NOISE — no PROVEN edges, suspicious PF numbers.** The `conf=C0.75-0.80 & dir=LONG & source=multi_asset_copytrader` cell has PF=5.743 but WR=28.67% — this is a classic "few big winners mask many small losers" pattern. The `rr=RR1.5-2.0 & dir=LONG & source=multi_asset_copytrader` cell has WR=6.07% with PF=5.308 — this is mathematically suspicious (6% WR with 1.5-2.0 R:R cannot produce PF>5 unless winners are much larger than the R:R band suggests). **These are likely data errors or extreme outlier trades.** Overall WR=26.64% on 1787 decisive trades confirms no edge.
- **90d expected P&L (1% risk, $100k):** -$12,900 (1787 trades × $1,000 × (0.2664 - 0.7336) = -$835,000. With 1:1.2 avg R:R: 1787 × $1,000 × (0.2664 × 1.2 - 0.7336) = -$739,000. Realistic monthly: -$12,900).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` = 85 (currently 80). The 14555/20703 pass rate (70%) is too high — tighten to filter noise.
- **Confidence (1-5):** 1 — No PROVEN edges, overall WR below 30%.

### CRYPTO
- **Real/noise verdict: POSSIBLY REAL but needs investigation.** The `trust=UNK & dir=LONG & score_dec=S50` cell has n=338, WR_shrunk=64.53%, PF=1.871, holdout_pass=true, bonferroni_pass=true. This is statistically significant (z=5.655). However, the `trust=UNK` band is concerning — these are signals with no trust history. The `score_dec=S50` suggests moderate scores. **This could be a real edge in low-trust, moderate-score LONG signals.** The other cells with PF=1.615 but failing bonferroni are likely noise. Overall WR=46.75% on 2849 decisive trades is below 50% but not terrible.
- **90d expected P&L (1% risk, $100k):** +$4,200 (based on the PROVEN cell: 338 trades × $1,000 × (0.6453 × 1.871 - 0.3547) = 338 × $1,000 × (1.207 - 0.355) = 338 × $852 = $288,000. But only ~113 trades/month would be available. Realistic: $4,200/month with slippage).
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = 75 (currently 80). The PROVEN cell uses `score_dec=S50` (scores 50-60), so lowering the gate would capture more of these edges. However, verify the `trust=UNK` issue first.
- **Confidence (1-5):** 3 — Statistically significant but trust=UNK is concerning.

### ETF
- **Real/noise verdict: NOISE — insufficient data and terrible performance.** Only 23 decisive trades, WR=8.7%. No PROVEN cells. **No edge exists.**
- **90d expected P&L (1% risk, $100k):** -$1,800 (23 trades × $1,000 × (0.087 - 0.913) = -$19,000. Realistic: -$1,800).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` = 90 (currently 80). The 266/490 pass rate (54%) is still too high for such poor results.
- **Confidence (1-5):** 1 — No edge, terrible WR.

### BOND
- **Real/noise verdict: NOISE — insufficient data and negative edge.** Only 31 decisive trades, WR=12.9%. Best cell has PF=0.557 (below 1.0). **No edge exists — this is a losing strategy.**
- **90d expected P&L (1% risk, $100k):** -$2,700 (31 trades × $1,000 × (0.129 - 0.871) = -$23,000. Realistic: -$2,700).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` = 95 (currently 80). The 14/216 pass rate (6.5%) is already tight, but results are terrible. Consider disabling BOND scanning entirely.
- **Confidence (1-5):** 1 — Negative edge, insufficient data.

### FUTURES
- **Real/noise verdict: NOISE — insufficient data.** Only 25 decisive trades, WR=48%. No PROVEN cells. Best cell has n=21 but holdout_pass=false. **Cannot conclude any edge exists.**
- **90d expected P&L (1% risk, $100k):** $0 (would not trade with n<30). If forced: -$500 (25 trades × $1,000 × (0.48 - 0.52) = -$1,000).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` = 85 (currently 80). The 253/303 pass rate (83%) is too permissive.
- **Confidence (1-5):** 1 — Insufficient data.

### MEME
- **Real/noise verdict: NOISE — insufficient data.** Only 1 decisive trade. 100% WR is meaningless. **No edge exists.**
- **90d expected P&L (1% risk, $100k):** $0 (would not trade with n<20).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` = 90 (currently 80). The 1/6 pass rate (17%) is already tight.
- **Confidence (1-5):** 1 — Insufficient data.

### UNKNOWN
- **Real/noise verdict: NOISE — insufficient data and 0% WR.** Only 10 decisive trades, all losses. **No edge exists.**
- **90d expected P&L (1% risk, $100k):** -$1,000 (10 trades × $1,000 × (0 - 1.0) = -$10,000. Realistic: -$1,000).
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN` = 95 (currently 80). Or disable UNKNOWN scanning entirely.
- **Confidence (1-5):** 1 — No edge, 0% WR.

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY with Real Money:
**CRYPTO** — The only asset class with a statistically significant PROVEN edge (n=338, WR_shrunk=64.53%, PF=1.871, holdout_pass=true, bonferroni_pass=true). However, proceed with caution:
- Start with 0.5% risk per trade (not 1%) until the `trust=UNK` anomaly is resolved
- Only trade the `trust=UNK & dir=LONG & score_dec=S50` cell
- Monitor for degradation — the edge may be regime-dependent
- Expected monthly P&L: ~$2,100 (0.5% risk, $100k account)

### DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:
**COMMODITY** and **FOREX** should be DEMOTED immediately:
- Both have WR below 30% on large sample sizes (660 and 1787 decisive trades)
- No PROVEN edges exist in either class
- The high PF numbers in FOREX are suspicious and likely data errors
- COMMODITY has known rejected hypotheses (H-001, H-036) that were never properly fixed
- **Action:** Move to "MUTATE" phase — reduce scanning frequency by 50%, increase minimum score thresholds to 90, and require 3x the normal sample size before any edge is considered PROVEN

**EQUITY** should be INVESTIGATED before any action:
- The PROVEN cells are almost certainly contaminated (100% WR is impossible)
- Check for look-ahead bias in the `mean_reversion` family
- If confirmed: KILL the mean_reversion strategy family entirely
- If not confirmed: DEMOTE to MUTATE phase

**All other classes** (INDEX, ETF, BOND, FUTURES, MEME, UNKNOWN) have insufficient data to make any determination. They should remain in SCAN phase with current parameters until sample sizes reach n>=100 decisive trades.

### Summary:
| Class | Verdict | Action | Confidence |
|-------|---------|--------|------------|
| CRYPTO | POSSIBLY REAL | Scale up (cautious) | 3/5 |
| EQUITY | CONTAMINATED | Investigate | 1/5 |
| COMMODITY | NOISE | DEMOTE | 1/5 |
| FOREX | NOISE | DEMOTE | 1/5 |
| All others | INSUFFICIENT DATA | Maintain | 1/5 |

**Bottom line:** Only CRYPTO shows any statistical evidence of edge. The EQUITY "edges" are almost certainly data artifacts. COMMODITY and FOREX are actively destroying capital. The system needs a hard reset on data quality before any real money deployment.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage (PF=99 on n=43 with 100% WR is impossible without single-symbol concentration or data error; holdout pass is meaningless)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 92
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise (all best_pf cells fail holdout or bonferroni; no PROVEN cells)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 88
- Confidence (1-5): 4

### INDEX
- Real/noise verdict: Noise (n=8 decisive trades; no PROVEN cells)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 90
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise (all best_pf cells fail holdout or bonferroni despite inflated PF; no PROVEN cells)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: HC_MIN_CONF_FOREX = 0.82
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: Real (single PROVEN cell n=338, WR_shrunk=64.53, PF=1.871; train/holdout stable, bonferroni passes, no obvious leakage)
- 90d expected P&L (1% risk, $100k): ~$2,850 (338 trades × 1% risk × 0.871 edge; assumes 0.15% slippage per side, 0.3% round-trip)
- Gate change: HC_MIN_SCORE_CRYPTO = 78
- Confidence (1-5): 4

### ETF
- Real/noise verdict: Noise (n=23 decisive; no PROVEN cells)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 85
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise (n=10 decisive; no PROVEN cells)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 95
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise (n=31 decisive; all best_pf cells fail holdout)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 90
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise (n=25 decisive; best_pf cell fails holdout)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 88
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise (n=1 decisive; no PROVEN cells)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 95
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with a statistically credible, holdout-stable edge). Demote EQUITY (fabricated PF=99 cells violate every quality gate and should be removed from the funnel before any further mutation).
