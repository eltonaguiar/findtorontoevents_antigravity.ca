# Pick Funnel Swarm Verdict — 2026-07-10 05:21 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260710T052035Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- **Real/noise verdict:** **Real** – 278 closed trades, Bayesian‑shrunk win‑rate ≈ 65 % and PF ≈ 1.9.  Z‑score = 5.5 and Bonferroni‑adjusted test passed, so the edge survives multiple‑testing correction.  No obvious single‑symbol concentration (trust = UNK, direction = LONG, score‑decile = S50) and the hold‑out set (245 trades) also meets the pass criteria, so leakage / look‑ahead bias is unlikely.
- **90d expected P&L (1 % risk, $100 k):**  
  *Risk per trade* = 1 % of $100 k = **$1 000**.  
  *Average net P&L per trade* = 0.7369 % of $1 000 ≈ **$7.37**.  
  *Total expected profit* = 278 × $7.37 ≈ **$2 050** (before slippage).  
  *Assumptions*: 0.1 % slippage per trade (≈ $1), flat commission $0.05 per trade, no position‑size scaling beyond the 1 % rule.
- **Gate change:** **`SMART_PICKS_MIN_SCORE_CRYPTO`** → lower from **80** to **70** (or equivalently broaden the `score_dec` band from `S50` to `S40‑S60`). This will admit more of the same “trust‑UNK / LONG / mid‑score” picks, raising n while preserving the statistically‑significant win‑rate.
- **Confidence (1‑5):** **4**  

### EQUITY
- **Real/noise verdict:** **Real** – three independent proven cells, each with > 78 % shrunk win‑rate, PF ranging from 7.9 to 31.4, Z‑scores > 5, and Bonferroni‑adjusted passes.  The mean‑reversion family cell (n = 38) shows an extraordinary PF ≈ 31.4, but the sample is modest; the other two cells (n ≈ 40) confirm the signal across slightly different dimension slices, reducing the risk of single‑symbol over‑fit.  Hold‑out performance is strong, and no leakage flags appear.
- **90d expected P&L (1 % risk, $100 k):**  
  Using the strongest cell (mean‑reversion):  
  *Risk per trade* = $1 000.  
  *Avg net P&L per trade* = 1.1056 % of $1 000 ≈ **$11.06**.  
  *Total expected profit* = 38 × $11.06 ≈ **$420**.  
  (If we combine the two “trust‑UNK / conf < 0.60 / alpha_engine” cells, the aggregate n ≈ 78, avg pnl ≈ 0.99 % → ≈ $770 total – still modest.)  
  *Assumptions*: 0.1 % slippage per trade, flat $0.05 commission, no scaling beyond the 1 % rule.
- **Gate change:** **`HC_CONFIDENCE_THRESHOLD`** in `audit_dashboard/hc_filter.js` → lower from **0.75** to **0.60** for EQUITY (or add a special‑case for `source=alpha_engine` with `conf<C0.60`). This unlocks the high‑performing “low‑confidence” cells that already proved superior in hold‑out.
- **Confidence (1‑5):** **5**  

### FOREX
- **Real/noise verdict:** **Noise** – no proven cells; the best PF (≈ 5.1) comes from a low‑win‑rate (≈ 9 %) segment and fails Bonferroni correction.  The high PF is driven by a handful of large‑gain outliers; the Z‑score is strongly negative, indicating the edge is not statistically reliable.
- **90d expected P&L (1 % risk, $100 k):** **$0** (no actionable edge).
- **Gate change:** No single gate appears to unlock a statistically‑significant edge; lowering the confidence threshold would merely increase noise.
- **Confidence (1‑5):** **1**  

### COMMODITY
- **Real/noise verdict:** **Noise** – no proven cells; the top PF (≈ 1.2) is barely above breakeven and the hold‑out fails Bonferroni.  The win‑rate hovers 50 % and the Z‑score is near zero, consistent with random chance.
- **90d expected P&L (1 % risk, $100 k):** **$0**.
- **Gate change:** None – any relaxation would admit more random picks.
- **Confidence (1‑5):** **1**  

### ETF
- **Real/noise verdict:** **Noise** – zero proven cells; win‑rate 8.7 % and PF ≈ 0. No statistical support.
- **90d expected P&L (1 % risk, $100 k):** **$0**.
- **Gate change:** Not applicable.
- **Confidence (1‑5):** **1**  

### UNKNOWN
- **Real/noise verdict:** **Noise** – only 8 closed trades, 0 % win‑rate; no proven edge.
- **90d expected P&L (1 % risk, $100 k):** **$0**.
- **Gate change:** N/A.
- **Confidence (1‑5):** **1**  

### FUTURES
- **Real/noise verdict:** **Noise** – no proven cells; tiny sample (n = 21) with PF = 0.
- **90d expected P&L (1 % risk, $100 k):** **$0**.
- **Gate change:** N/A.
- **Confidence (1‑5):** **1**  

### INDEX
- **Real/noise verdict:** **Noise** – no proven cells; win‑rate 62.5 % but n = 8, PF ≈ 0, fails statistical thresholds.
- **90d expected P&L (1 % risk, $100 k):** **$0**.
- **Gate change:** N/A.
- **Confidence (1‑5):** **1**  

### BOND
- **Real/noise verdict:** **Noise** – no proven cells; PF ≈ 0, win‑rate 10 %, Z‑scores strongly negative.
- **90d expected P&L (1 % risk, $100 k):** **$0**.
- **Gate change:** N/A.
- **Confidence (1‑5):** **1**  

### MEME
- **Real/noise verdict:** **Noise** – single trade, 100 % win but n = 1, no statistical power.
- **90d expected P&L (1 % risk, $100 k):** **$0**.
- **Gate change:** N/A.
- **Confidence (1‑5):** **1**  

---

## SYSTEM‑WIDE Conclusion
**Scale‑up candidate:** **EQUITY** – the mean‑reversion family cell delivers an extraordinary profit factor (≈ 31) with a robust, Bonferroni‑adjusted win‑rate (> 80 %) and a clean hold‑out validation.  Even though the sample is modest (n = 38), the statistical safeguards (Z‑score > 5, Bonferroni pass) give confidence that the edge is not noise.  Adjusting the HC confidence threshold to 0.60 will unlock the full set of these high‑quality picks without sacrificing statistical rigor.

**Demote / de‑prioritize:** **FOREX** – despite a relatively large volume of closed trades (2 575), every candidate cell fails multiple‑testing correction, and the best PF is driven by a sub‑10 % win‑rate with negative Z‑scores.  Continuing to allocate capital here would likely erode performance; the class should be moved to the “mutation” queue for further research or outright removal per the **MUTATION_THREE_AXIS_PROTOCOL**.  

All other classes (COMMODITY, ETF, UNKNOWN, FUTURES, INDEX, BOND, MEME) show no statistically‑significant edge and should remain excluded from live allocation until a new, validated signal emerges.  

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

## SYSTEM-WIDE OBSERVATIONS BEFORE PER-CLASS ANALYSIS

The funnel data reveals a **severe disconnect** between scanning volume and edge quality:

- **CRYPTO**: 16,239 scanned → 0 passed HIGH CONVICTION gate, yet 3,337 decisive trades with 47.23% WR
- **FOREX**: 20,557 scanned → 0 passed HIGH CONVICTION, 2,575 decisive trades at 29.32% WR
- **COMMODITY**: 8,708 scanned → 0 passed HIGH CONVICTION, 891 decisive trades at 31.31% WR
- **EQUITY**: 4,822 scanned → 2 passed HIGH CONVICTION, 386 decisive trades at 43.78% WR

The `passed_high_conviction` column being near-zero across all classes while `opened` trades are 2-10x higher than `passed_smart` suggests **the funnel stages are not sequential** — trades are being opened without passing through the quality gates. This is a critical architectural issue.

---

### CRYPTO
- **Real/noise verdict**: **REAL but fragile** — The single PROVEN cell (`trust=UNK & dir=LONG & score_dec=S50`, n=278, WR_shrunk=65.44%, PF=1.905) passes Bonferroni and holdout. However, this is the **only** PROVEN cell out of thousands of scanned signals. The 47.23% overall WR on 3,337 decisive trades is below breakeven for most R:R profiles. The `best_pf_overall` shows two additional cells with PF>1.5 but **both fail Bonferroni** (wr_z=0.948, p>0.05). The PROVEN cell's train_n=33 vs holdout_n=245 is suspicious — the train set is too small for reliable shrinkage. **No leakage detected** but the edge is concentrated in a single dimension combination.
- **90d expected P&L (1% risk, $100k)**: **$2,947** — Calculation: 278 trades × 1% risk × $100k = $278,000 total risk. Wins: 185 × $1,000 × 0.7369% avg_win = $1,363; Losses: 93 × $1,000 × 0.5% avg_loss (assuming 1:1 R:R) = -$465. Net: $898. However, the PROVEN cell's PF=1.905 implies better: 278 × $1,000 × (0.6655 × 1.905 - 0.3345 × 1.0) / (0.6655 × 1.905 + 0.3345) ≈ $2,947. **Assumes 0.1% slippage, fills at signal price ±0.5%**.
- **Gate change**: `SMART_PICKS_MIN_SCORE_CRYPTO` in `audit_trail/quality_gates.py` = **65** (currently likely 50 based on `score_dec=S50` being the only passing cell). This would filter out the 80% of scanned signals that are noise while keeping the S50+ LONG edge.
- **Confidence (1-5)**: **3** — Single-cell edge, small train set, but holdout validates.

---

### EQUITY
- **Real/noise verdict**: **REAL but suspiciously high** — Three PROVEN cells with WR_shrunk 78-81% and PF 7.9-31.4. The `fam=mean_reversion & dir=LONG & source=alpha_engine` cell (n=38, WR=97.37%, PF=31.44) is **statistically impossible** in efficient markets. Train_n=15, holdout_n=23, holdout_pass=true — but PF=99.0 on holdout means **zero losses in 23 trades**. This is either: (a) a look-ahead bias where the signal uses future data, (b) a single-stock concentration (e.g., repeated trades on one ticker with a structural arbitrage), or (c) a data error where wins/losses are mislabeled. The `conf=C<0.60` cells (n=40, WR=92.5%) are similarly extreme. **Flagged for immediate investigation** — these are likely leakage or data corruption, not genuine alpha.
- **90d expected P&L (1% risk, $100k)**: **$23,400** — If real: 38 trades × $1,000 × (0.9737 × 31.444 - 0.0263 × 1.0) / (0.9737 × 31.444 + 0.0263) ≈ $23,400. **However, I assign 90% probability this is a data error**, so expected P&L is actually **-$1,200** (using the class-level 43.78% WR on 386 trades: 386 × $1,000 × (0.4378 × 1.5 - 0.5622 × 1.0) = -$1,200 assuming 1.5:1 avg R:R).
- **Gate change**: **HARD REJECT** — Do not change gates until the `mean_reversion` cell is audited. Add `EQUITY_MAX_WR_PER_CELL = 0.80` as a sanity cap in `hc_filter.js` to flag impossible performance.
- **Confidence (1-5)**: **1** — The PROVEN cells are too good to be true. Likely data corruption.

---

### FOREX
- **Real/noise verdict**: **NOISE** — Zero PROVEN cells out of 2,575 decisive trades. The `best_pf_overall` shows PF>3.8 on three cells, but **all have negative WR_z scores** (-6.35 to -18.50), meaning they lose more often than they win. The high PF comes from a few large winners masking many small losers — this is **lottery-ticket bias**, not edge. The 29.32% overall WR confirms the system is directionally wrong. The `multi_asset_copytrader` source shows PF=5.117 on n=489 with WR=8.18% — this is a **death by a thousand cuts** strategy that would bankrupt any account. **No leakage detected** — the system simply doesn't work for FOREX.
- **90d expected P&L (1% risk, $100k)**: **-$12,875** — 2,575 trades × $1,000 × (0.2932 × 1.5 - 0.7068 × 1.0) = -$12,875 assuming 1.5:1 avg R:R. Using actual cell data: the best cell (RR1.5-2.0 & LONG & multi_asset) has PF=5.117 but WR=8.18% — expected value per trade = 0.0818 × 5.117 - 0.9182 × 1.0 = -0.499, so 489 trades × $1,000 × (-0.499) = -$244,011 if traded at full size. **Catastrophic**.
- **Gate change**: `SMART_PICKS_MIN_SCORE_FOREX` = **90** (currently likely 50). This would kill 99% of signals. Alternatively, set `FOREX_ENABLED = False` in `production_scanner.py`.
- **Confidence (1-5)**: **5** — Definitive noise. No edge exists.

---

### COMMODITY
- **Real/noise verdict**: **NOISE** — Zero PROVEN cells. 31.31% overall WR on 891 decisive trades. The `best_pf_overall` cells all have PF<1.21, WR<51%, and **zero holdout validation** (holdout_n=0 for the top cell). The `trust=PROBATION` cell (n=107, WR=50.47%, PF=1.207) fails holdout because there's no holdout data — this is **in-sample overfitting**. The `conf=C0.75-0.80` cell (n=93, WR=50.54%, PF=0.932) has PF<1.0, meaning it loses money. **No leakage detected** — the system simply lacks predictive power for commodities.
- **90d expected P&L (1% risk, $100k)**: **-$4,455** — 891 trades × $1,000 × (0.3131 × 1.2 - 0.6869 × 1.0) = -$4,455 assuming 1.2:1 avg R:R. Using actual best cell: 107 trades × $1,000 × (0.5047 × 1.207 - 0.4953 × 1.0) = $12,200 — but this is in-sample only and would likely revert to -$5,000 out-of-sample.
- **Gate change**: `SMART_PICKS_MIN_SCORE_COMMODITY` = **80** (currently likely 50). This would reduce scanned volume from 8,708 to ~200, eliminating the noise.
- **Confidence (1-5)**: **5** — Definitive noise. No edge exists.

---

### ETF
- **Real/noise verdict**: **NOISE** — 23 decisive trades, 8.7% WR. Zero PROVEN cells. The sample is too small (n=23) for any statistical conclusion, but the 8.7% WR is so far below 50% that it suggests **systematic directional bias** (likely always going long in a down market). **No leakage detected** — just insufficient data and poor performance.
- **90d expected P&L (1% risk, $100k)**: **-$1,150** — 23 trades × $1,000 × (0.087 × 1.5 - 0.913 × 1.0) = -$1,150. Negligible in absolute terms but -50% return on risk capital.
- **Gate change**: `ETF_ENABLED = False` in `production_scanner.py`. The asset class has insufficient volume (466 scanned in 90 days) to develop meaningful signals.
- **Confidence (1-5)**: **4** — Small sample but directionally wrong.

---

### UNKNOWN
- **Real/noise verdict**: **NOISE** — 8 decisive trades, 0% WR. Zero PROVEN cells. The `opened=500` vs `closed=8` suggests **most trades are still open** or the classification is broken. This class should not exist in production.
- **90d expected P&L (1% risk, $100k)**: **-$800** — 8 trades × $1,000 × (0.0 × 1.0 - 1.0 × 1.0) = -$800. Trivial.
- **Gate change**: Remove `UNKNOWN` class entirely from `quality_gates.py`. Force classification before trading.
- **Confidence (1-5)**: **5** — Broken classification, not a trading strategy.

---

### FUTURES
- **Real/noise verdict**: **INCONCLUSIVE** — 21 decisive trades, 52.38% WR. Zero PROVEN cells (n<20 threshold). The WR is above 50% but the sample is too small (n=21) for statistical significance. **No leakage detected** but cannot confirm edge.
- **90d expected P&L (1% risk, $100k)**: **$50** — 21 trades × $1,000 × (0.5238 × 1.2 - 0.4762 × 1.0) = $50. Essentially breakeven.
- **Gate change**: No change needed. Monitor for 90 more days to accumulate n>100.
- **Confidence (1-5)**: **2** — Too small to judge.

---

### INDEX
- **Real/noise verdict**: **INCONCLUSIVE** — 8 decisive trades, 62.5% WR. Zero PROVEN cells (n<20). The WR looks promising but n=8 is meaningless. **No leakage detected**.
- **90d expected P&L (1% risk, $100k)**: **$20** — 8 trades × $1,000 × (0.625 × 1.2 - 0.375 × 1.0) = $20. Trivial.
- **Gate change**: No change. Increase scanning volume (currently 665 in 90 days) to get more data.
- **Confidence (1-5)**: **1** — Insufficient data.

---

### BOND
- **Real/noise verdict**: **NOISE** — 30 decisive trades, 10% WR. Zero PROVEN cells. The `best_pf_overall` cells all have PF<0.56 and negative WR_z scores (-3.13 to -3.71), meaning **statistically significant losses**. The `bond_scanner` source is systematically wrong. **No leakage detected** — the signal is simply inverted.
- **90d expected P&L (1% risk, $100k)**: **-$2,700** — 30 trades × $1,000 × (0.10 × 1.0 - 0.90 × 1.0) = -$2,700. Using actual best cell: 20 trades × $1,000 × (0.15 × 0.557 - 0.85 × 1.0) = -$15,329 if traded at full size.
- **Gate change**: `BOND_SCANNER_INVERT_SIGNAL = True` in `production_scanner.py`. The 10% WR suggests the signal is anti-correlated with the market — inverting would give 90% WR. Alternatively, set `BOND_ENABLED = False`.
- **Confidence (1-5)**: **4** — Small sample but directionally consistent losses.

---

### MEME
- **Real/noise verdict**: **INCONCLUSIVE** — 1 decisive trade, 100% WR. Zero PROVEN cells. n=1 is meaningless. **No leakage detected**.
- **90d expected P&L (1% risk, $100k)**: **$0** — 1 trade is not statistically meaningful.
- **Gate change**: No change. MEME is a curiosity, not a strategy.
- **Confidence (1-5)**: **1** — Insufficient data.

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY with Real Money:
**NONE** — No asset class has a statistically validated, robust edge suitable for real-money deployment.

- **CRYPTO** has one PROVEN cell but it's fragile (single dimension combination, small train set). Could deploy **$10,000** (10% of notional) on the `trust=UNK & dir=LONG & score_dec=S50` cell with strict stop-losses, but expect high variance.
- **EQUITY** would be the candidate IF the PROVEN cells are real, but I assign 90% probability they are data errors. **Do not deploy until audited.**

### Demote per MUTATION_THREE_AXIS_PROTOCOL:
**FOREX** and **COMMODITY** should be **KILLED** immediately:
- **FOREX**: 20,557 scans, 0 PROVEN cells, 29.32% WR, negative expected value. This is consuming 40% of scanning resources for guaranteed losses.
- **COMMODITY**: 8,708 scans, 0 PROVEN cells, 31.31% WR. Same story.

**BOND** should be **MUTATED** (invert signal) or killed.

**ETF** and **UNKNOWN** should be **KILLED** due to insufficient volume and negative performance.

### Recommended Immediate Actions:
1. **Audit EQUITY `mean_reversion` cell** — check for single-stock concentration, look-ahead bias, or data corruption
2. **Kill FOREX and COMMODITY** in `production_scanner.py` — redirect scanning resources to CRYPTO and EQUITY
3. **Fix funnel architecture** — ensure `opened` trades cannot bypass `passed_smart` and `passed_high_conviction` gates
4. **Increase CRYPTO scanning** — the single PROVEN cell suggests there may be more edges at higher score thresholds
5. **Implement position sizing** — current data suggests 1% risk per trade would have lost $22,000 across all classes in 90 days

**Bottom line**: The system is generating 51,000+ scans per quarter but producing zero reliable edges. The funnel is a leaky pipe — trades are being opened without passing quality gates. Fix the architecture before adding more signals.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real (n=278, WR_shrunk=65.44, PF=1.905, holdout_pass=true, bonferroni_pass=true; no obvious leakage flags).
- 90d expected P&L (1% risk, $100k): $2,180 (278 trades, ~1.9R avg winner net of 0.5% slippage, 1% risk per trade).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 50
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Noise (n=38-40 cells show extreme PF 7.9-31.4 and WR_shrunk 78-81; likely single-symbol concentration or leakage given tiny train/holdout splits).
- 90d expected P&L (1% risk, $100k): $0 (no reliable edge after shrinkage and holdout scrutiny).
- Gate change: HC_MIN_TRUST_EQUITY = 70
- Confidence (1-5): 3

### COMMODITY
- Real/noise verdict: Noise (no proven cells; all best_pf cells have holdout_pass=false, PF<=1.21, WR_shrunk<=50.4).
- 90d expected P&L (1% risk, $100k): -$890 (realized WR 31.31% on 891 decisive trades at 1% risk).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 65
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise (no proven cells; best_pf cells show WR_shrunk 9.8-31.2, multiple holdout_pass=false, negative WR_z).
- 90d expected P&L (1% risk, $100k): -$2,575 (realized WR 29.32% on 2575 decisive trades).
- Gate change: HC_MIN_CONF_FOREX = 0.82
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise (no proven or best_pf cells; realized WR 8.7% on 23 trades).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 70
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise (no proven or best_pf cells; realized WR 0% on 8 trades).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise (no proven or best_pf cells; n=21 too small for any claim).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 75
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise (no proven or best_pf cells; n=8 too small).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 75
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise (no proven cells; best_pf cells show PF<=0.56, negative WR_z, holdout failures).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 70
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise (n=1; no usable edge).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 90
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with a statistically defensible proven cell). Demote FOREX and COMMODITY per MUTATION_THREE_AXIS_PROTOCOL (mutate filters before any kill step) as both show persistent sub-50% WR and zero proven edges. All other classes have no actionable edge.
