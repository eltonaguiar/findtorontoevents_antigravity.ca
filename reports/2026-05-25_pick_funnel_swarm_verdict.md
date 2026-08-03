# Pick Funnel Swarm Verdict — 2026-08-03 05:14 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260803T051357Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- **Real/noise verdict:** **Real edge** – Proven cells (3) each have **n ≈ 340**, **WR ≈ 65 % (shrunk ≈ 64 %)** and **PF ≈ 2.1**.  The win‑rate is far above the 50 % baseline, the shrinkage is modest, and the hold‑out set (≈ 216 trades) passes the “hold‑out pass” flag, indicating the signal survives out‑of‑sample testing.  No obvious leakage (the source is the internal `alpha_engine`, not an external data feed) and the trade‑size distribution is spread across many symbols (the 90‑day closed‑trade count is 2 817), so concentration risk is low.  

- **90d expected P&L (1 % risk, $100 k):**  
  *PF = 2.173 → expected return per trade = (PF‑1)/(PF+1) ≈ 0.3696*  
  *Risk per trade = $1 000*  
  *Expected profit per trade ≈ $369.6*  
  *Total trades in proven cell = 339* → **≈ $125 300** expected profit over the 90‑day window (assuming each trade sized to 1 % risk and ignoring slippage).  

- **Gate change:** `hc_filter.js` – lower the **SCORE_MIN** (or the combined “high‑conviction” score) from **80** to **50** (or lower the **TRUST_MIN** from 60 to 0). This would admit the proven S50/UNK‑trust picks that are currently filtered out.  

- **Confidence (1‑5):** **5** – strong statistical backing, large sample, out‑of‑sample pass.

---

### EQUITY
- **Real/noise verdict:** **Real edge** – Three Proven cells (identical composition) each have **n = 59**, **WR ≈ 98 % (shrunk ≈ 86 %)** and an **astronomical PF ≈ 159**.  The win‑rate is near‑perfect, the shrinkage is still very high, and the hold‑out set (44 trades) passes both the Z‑score and Bonferroni tests, so the result is not a statistical fluke.  The cell is defined by **trust=UNK**, **confidence < 0.60**, and **family=mean_reversion**, which are internal model attributes – no external data leakage.  Symbol‑level concentration is modest (the 59 trades span multiple equities).  

- **90d expected P&L (1 % risk, $100 k):**  
  *PF = 159.314 → expected return per trade = (PF‑1)/(PF+1) ≈ 0.9875*  
  *Risk per trade = $1 000*  
  *Expected profit per trade ≈ $987.5*  
  *Total trades in proven cell = 59* → **≈ $58 260** expected profit over 90 days.  

- **Gate change:** `hc_filter.js` – lower the **TRUST_MIN** from **60** to **0** (or remove the trust filter) for the EQUITY class. This would let the “trust‑UNK / low‑confidence / mean‑reversion” picks flow through the high‑conviction gate.  

- **Confidence (1‑5):** **5** – extremely high win‑rate, large PF, and out‑of‑sample validation.

---

### FOREX
- **Real/noise verdict:** **Noise** – No Proven cells; the best PF (9.66) fails the hold‑out test (hold‑out PF = 0, Bonferroni = false) and the win‑rate is only **≈ 2 %**.  The high PF is driven by a tiny training set (n = 127) and collapses on out‑of‑sample data, indicating severe over‑fit / look‑ahead bias.  

- **90d expected P&L (1 % risk, $100 k):** **$0** – no statistically reliable edge to size.  

- **Gate change:** Raising the **SMART_PICKS_MIN_CONFIDENCE_FOREX** (or tightening the confidence band) would prune the noisy high‑PF cells, but it would not create a real edge.  

- **Confidence (1‑5):** **1** – no credible edge.

---

### COMMODITY
- **Real/noise verdict:** **Noise** – No Proven cells; the top PF (≈ 3.86) comes from a training set of only **5** trades and fails hold‑out (PF ≈ 3.93 but hold‑out pass = false).  The win‑rate is ~52 % but the sample is too small and the PF is unstable.  

- **90d expected P&L (1 % risk, $100 k):** **$0** – no reliable edge.  

- **Gate change:** Increase the **SMART_PICKS_MIN_SCORE_COMMODITY** to filter out low‑confidence picks; this will reduce noise but will not generate a new edge.  

- **Confidence (1‑5):** **1**.

---

### ETF
- **Real/noise verdict:** **Noise** – Only one cell, n = 21, PF ≈ 0.02, win‑rate ≈ 9 %, and it fails hold‑out.  The PF is negative (loss‑heavy) and the win‑rate is far below random.  

- **90d expected P&L (1 % risk, $100 k):** **$0**.  

- **Gate change:** Tighten the **SMART_PICKS_MIN_SCORE_ETF** or the HC confidence threshold; the current edge is clearly unprofitable.  

- **Confidence (1‑5):** **1**.

---

### BOND
- **Real/noise verdict:** **Noise** – No Proven cells; best PF ≈ 0.47 with n = 23, win‑rate ≈ 13 %, and hold‑out fails.  The signal is loss‑biased and the sample is tiny.  

- **90d expected P&L (1 % risk, $100 k):** **$0**.  

- **Gate change:** Raise the **SMART_PICKS_MIN_SCORE_BOND** or require a minimum PF > 1.  

- **Confidence (1‑5):** **1**.

---

### FUTURES
- **Real/noise verdict:** **Noise** – No Proven cells; the best PF ≈ 1.64 (n = 21) fails hold‑out and the Z‑score is negative.  Sample is small and the edge does not survive out‑of‑sample.  

- **90d expected P&L (1 % risk, $100 k):** **$0**.  

- **Gate change:** Increase the **SMART_PICKS_MIN_CONFIDENCE_FUTURES** to eliminate the marginal cell.  

- **Confidence (1‑5):** **1**.

---

### INDEX, UNKNOWN, MEME
- **Real/noise verdict:** **Noise / No edge** – No Proven cells, negligible or zero win‑rates, and sample sizes far below the 20‑trade threshold for reliable inference.  

- **90d expected P&L (1 % risk, $100 k):** **$0**.  

- **Gate change:** No meaningful gate tweak; the classes simply lack sufficient volume to evaluate an edge.  

- **Confidence (1‑5):** **1**.

---

## SYSTEM‑WIDE CONCLUSION
**Scale‑up today:** **EQUITY** – the mean‑reversion, low‑confidence, trust‑UNK edge is statistically rock‑solid (PF ≈ 159, win‑rate ≈ 98 %). With a modest 59‑trade sample it already passes stringent out‑of‑sample tests, and the expected profit (~$58 k on a $100 k account) is compelling. Adjust the HC filter to allow unknown‑trust, low‑confidence picks and allocate capital.

**Demote / kill:** **FOREX**, **COMMODITY**, **ETF**, **BOND**, **FUTURES**, **INDEX**, **UNKNOWN**, **MEME** – all lack a proven edge; the observed high PFs are either over‑fit or arise from tiny training sets. According to the *MUTATION_THREE_AXIS_PROTOCOL*, these classes should be “mutated” (gate thresholds tightened) before any further resources are spent.  

**One gate change that unlocks the biggest upside:**  
- **File:** `audit_dashboard/hc_filter.js`  
- **Variable:** `TRUST_MIN` (currently 60) → **set to 0** (or remove the trust filter).  

Lowering the trust requirement admits the high‑conviction, proven cells for both **CRYPTO** (score = S50) and **EQUITY** (mean‑reversion, low‑confidence) that are presently being filtered out, delivering the largest incremental expected P&L across the portfolio.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT — 90-DAY EDGE ANALYSIS

### CRYPTO
- Real/noise verdict: **MIXED — 3 PROVEN cells are statistically real but fragile.** The `dir=LONG & score_dec=S50 & source=alpha_engine` cell (n=339, WR_shrunk=64.35%, PF=2.173, holdout_pass=true, bonferroni_pass=true) is the strongest signal in the entire system. However, the WR_z=5.594 is suspiciously high — this could indicate overfitting to a specific market regime (likely the Q1 2026 crypto bull run). The `trust=UNK` dimension adds nothing (same n=339, nearly identical stats), suggesting the trust gate is not discriminating. The PF=2.173 is plausible but not "too good to be true" — the avg_pnl_pct=0.94% per trade is reasonable for crypto with 1.5-2.0 R:R. **No leakage flags** — the train/holdout split (123/216) shows consistent performance (train PF=2.952, holdout PF=1.8), which argues against look-ahead bias. However, the 65% WR with PF=2.17 implies avg win ≈ 2.17× avg loss, which is internally consistent with R:R 1.5-2.0. **Verdict: REAL but regime-dependent.**
- 90d expected P&L (1% risk, $100k): **$18,900** (calculation: 339 trades × 1% risk × $1,000 = $3,390 risked; expected edge = 0.6519 × 1.5R − 0.3481 × 1R = 0.978R − 0.348R = 0.630R per trade; 339 × 0.630 × $30 avg risk = $6,407; but with PF=2.173 and avg_pnl=0.94%, more precisely: 339 × 0.94% × $1,000 = $3,187; however, with 1% risk sizing and avg_pnl_pct=0.94% on notional, actual P&L = 339 × 0.94% × $100,000 × (1% risk / 1% avg_pnl) = $3,187. **Wait — let me redo this properly.** With 1% risk per trade on $100k = $1,000 risk per trade. Expected value per trade = PF × win_prob × avg_win − (1−win_prob) × avg_loss. With PF=2.173 and WR=65.19%: avg_win/avg_loss = 2.173 × (0.3481/0.6519) = 1.16. So EV per trade = 0.6519 × 1.16R − 0.3481 × 1R = 0.756R − 0.348R = 0.408R. With R=$1,000: EV = $408/trade. 339 trades × $408 = **$138,312**. But this assumes all 339 trades were taken with 1% risk — the funnel shows only 2 passed_HC, so in practice only ~2 trades would have been taken. **If we scaled up to take all 339: $138,312.** With slippage (0.05% per trade): 339 × $50 = $16,950. Net: **$121,362.**)
- Gate change: **SMART_PICKS_MIN_SCORE_CRYPTO = 80** (currently likely lower — the HC gate at 80+ filters out 99.9% of signals; we need to lower the bar to capture this edge, OR raise the score threshold to 75 to capture the S50 decile while filtering noise)
- Confidence (1-5): **4** — strong statistical evidence, but the 65% WR in a bull market is concerning for regime shift

### FOREX
- Real/noise verdict: **NOISE — NO PROVEN EDGES.** The best_pf_overall cells are statistical artifacts. The `rr=RR1.5-2.0 & fam=momentum & dir=LONG` cell (n=127, WR=1.57%, PF=9.661) is a **RED FLAG for leakage**: 2 wins out of 127 trades with PF=9.661 means the 2 wins had enormous payouts (likely 50R+ each), which is either a data error, a single-symbol concentration (likely one massive EUR/USD move), or a look-ahead bias where the "win" was known before entry. The WR_z=-10.916 is catastrophic — this is 10.9 standard deviations BELOW the expected 50% WR, which is statistically impossible for a random process. **This is a data integrity issue, not an edge.** The `conf=C0.75-0.80 & dir=LONG & source=multi_asset_copytrader` cell (n=111, WR=34.23%, PF=4.705) has holdout_pass=true but WR_z=-3.323 — the PF is driven by a few large wins, not consistent edge. With 856 closed trades and ZERO proven cells, FOREX is a **net loser** (WR=28.04% overall). The 16,463 passed_smart vs 10 passed_verified_alpha shows the smart gate is not discriminating — it's passing everything.
- 90d expected P&L (1% risk, $100k): **-$14,280** (calculation: 856 closed trades, WR=28.04%, avg R:R ≈ 1.0 (typical for forex); EV per trade = 0.2804 × 1R − 0.7196 × 1R = −0.439R; with R=$1,000: −$439/trade; 856 × −$439 = −$375,784; but with 1% risk and only taking trades that pass HC (0 trades), actual P&L = $0. **If we forced all 856 trades: −$375,784.** With realistic slippage (0.1% per trade): 856 × $100 = $85,600 additional loss. **Net: −$461,384.** But since HC gate blocks everything, actual P&L = $0. The opportunity cost is the real loss.)
- Gate change: **SMART_PICKS_MIN_SCORE_FOREX = 95** (currently too low — we need to filter out the 16,463 passed_smart down to a handful of high-conviction signals; alternatively, set `FOREX_MIN_CONFIDENCE = 0.90` in quality_gates.py)
- Confidence (1-5): **1** — no edge exists; the data itself is suspect

### COMMODITY
- Real/noise verdict: **NOISE — NO PROVEN EDGES.** The best_pf_overall cell (`trust=UNK & score_dec=S50 & source=alpha_engine`, n=52, WR=51.92%, PF=3.861) has holdout_pass=false and WR_z=0.277 (not significant). The PF=3.861 with WR=51.92% implies avg_win/avg_loss = 3.861 × (0.4808/0.5192) = 3.58, which means the average win is 3.58× the average loss — this is plausible for commodity trends but the holdout failure kills it. The train_n=5 is far too small to be meaningful. **This is sample noise.** The overall WR=20.32% across 497 closed trades confirms COMMODITY is a net loser. The 6,121 passed_smart vs 0 passed_verified_alpha shows the smart gate is not working for this class.
- 90d expected P&L (1% risk, $100k): **-$5,880** (calculation: 497 closed trades, WR=20.32%, avg R:R ≈ 1.5 (commodity trends); EV per trade = 0.2032 × 1.5R − 0.7968 × 1R = 0.305R − 0.797R = −0.492R; with R=$1,000: −$492/trade; 497 × −$492 = −$244,524; but with 1% risk and HC gate blocking everything, actual P&L = $0. **If forced: −$244,524.** With slippage (0.1%): 497 × $100 = $49,700 additional. **Net: −$294,224.**)
- Gate change: **SMART_PICKS_MIN_SCORE_COMMODITY = 90** (raise threshold to eliminate the 6,121 false positives; the current gate is passing 73% of scanned signals, which is useless)
- Confidence (1-5): **1** — no edge, and the H-001 COT rejection confirms systematic issues

### EQUITY
- Real/noise verdict: **REAL BUT SUSPICIOUS — 3 PROVEN cells with identical stats.** The `trust=UNK & conf=C<0.60 & fam=mean_reversion` cell (n=59, WR_shrunk=86.08%, PF=159.314, holdout_pass=true, bonferroni_pass=true) is **statistically impossible to be real**. A PF of 159.314 means for every $1 lost, $159.31 was gained. With 58 wins out of 59 trades, this is either: (1) a data error where losses are not being recorded, (2) a single-symbol concentration (likely one stock that had a massive mean-reversion move), or (3) look-ahead bias where the "mean reversion" signal is actually predicting a known corporate event (earnings, buyout). The WR_z=7.422 is 7.4 standard deviations above expected — this is not a trading edge, it's a data artifact. **The fact that all 3 PROVEN cells have IDENTICAL stats (n=59, wins=58, PF=159.314) means they are the SAME 59 trades viewed through different dimension combinations — this is a single-symbol concentration, not a diversified edge.** The avg_pnl_pct=1.07% per trade is too low for a PF of 159 — this suggests the PF calculation is broken (likely dividing by near-zero losses).
- 90d expected P&L (1% risk, $100k): **$0** (cannot trust the data; if the PF=159 were real, 59 trades × 1% risk × 159 PF = $93,810, but this is clearly a data error. **Realistic assessment: the 412 closed trades with WR=46.12% and no proven edge would lose money.** With 1% risk and avg R:R=1.0: EV = 0.4612 − 0.5388 = −0.0776R; 412 × −$77.60 = −$31,971. **Net: −$31,971.**)
- Gate change: **Add a `MIN_TRADES_PER_SYMBOL` gate in quality_gates.py = 5** (to prevent single-symbol concentration from creating false edges; also add `MAX_PF_ANOMALY = 10` to flag cells with PF > 10 as data errors)
- Confidence (1-5): **1** — the edge is a data artifact, not a real signal

### ETF
- Real/noise verdict: **NOISE — NO PROVEN EDGES.** Only 25 closed trades total, and the best cell (n=21, WR=9.52%, PF=0.02) is a disaster. The WR_shrunk=29.27% shows the Bayesian shrinkage is pulling toward the mean, but the raw WR=9.52% is terrible. With only 25 trades, there's no statistical power to identify any edge. The overall WR=12.0% confirms ETF is a net loser.
- 90d expected P&L (1% risk, $100k): **-$1,560** (calculation: 25 closed trades, WR=12%, avg R:R=1.0; EV = 0.12 − 0.88 = −0.76R; 25 × −$760 = −$19,000; but with HC gate blocking everything, actual P&L = $0. **If forced: −$19,000.**)
- Gate change: **SMART_PICKS_MIN_SCORE_ETF = 85** (raise threshold to eliminate the 314 passed_smart; with only 539 scanned, this class should be nearly shut off)
- Confidence (1-5): **1** — no edge, insufficient data

### UNKNOWN
- Real/noise verdict: **NOISE — NO EDGE.** 10 closed trades, 0 wins, 10 losses. The class is undefined (no asset classification), so any signal is meaningless. The 848 opened vs 10 closed suggests trades are being opened but not closed (possibly stuck positions).
- 90d expected P&L (1% risk, $100k): **-$10,000** (10 trades × 100% loss rate × $1,000 risk = −$10,000)
- Gate change: **Add `UNKNOWN_CLASS_MIN_SCORE = 0` in quality_gates.py** (effectively disable this class — it should never trade)
- Confidence (1-5): **1** — no edge, should be disabled

### INDEX
- Real/noise verdict: **NOISE — NO PROVEN EDGES.** Only 7 closed trades, 3 wins, 4 losses. The WR=42.86% is within noise for n=7. The 908 passed_smart vs 0 passed_verified_alpha shows the smart gate is passing everything but nothing survives verification.
- 90d expected P&L (1% risk, $100k): **-$1,000** (7 trades, WR=42.86%, avg R:R=1.0; EV = 0.4286 − 0.5714 = −0.143R; 7 × −$143 = −$1,001)
- Gate change: **SMART_PICKS_MIN_SCORE_INDEX = 90** (raise threshold to eliminate the 908 false positives)
- Confidence (1-5): **1** — no edge, insufficient data

### FUTURES
- Real/noise verdict: **NOISE — NO PROVEN EDGES.** 24 closed trades, WR=45.83%, best cell (n=21, WR=42.86%, PF=1.641) has holdout_pass=false. The PF=1.641 is not compelling, and the WR_z=-0.654 is not significant. The H-005 rejection confirms futures momentum is dead.
- 90d expected P&L (1% risk, $100k): **-$1,000** (24 trades, WR=45.83%, avg R:R=1.0; EV = 0.4583 − 0.5417 = −0.083R; 24 × −$83 = −$1,992)
- Gate change: **SMART_PICKS_MIN_SCORE_FUTURES = 85** (raise threshold; the 95 passed_smart out of 150 scanned is too permissive)
- Confidence (1-5): **1** — no edge, H-005 confirms

### BOND
- Real/noise verdict: **NOISE — NO PROVEN EDGES.** 35 closed trades, WR=14.29%, best cell (n=23, WR=13.04%, PF=0.47) is a disaster. The WR_z=-3.545 is 3.5 standard deviations below expected — this is a systematically losing strategy. The `rr=RR>=2.0 & dir=LONG & source=bond_scanner` cell (n=21, WR=9.52%, PF=0.0) has ZERO wins — the PF=0.0 means every trade lost money.
- 90d expected P&L (1% risk, $100k): **-$3,000** (35 trades, WR=14.29%, avg R:R=1.0; EV = 0.1429 − 0.8571 = −0.714R; 35 × −$714 = −$24,990)
- Gate change: **SMART_PICKS_MIN_SCORE_BOND = 95** (effectively disable this class; the bond_scanner source is producing garbage)
- Confidence (1-5): **1** — no edge, systematically losing

### MEME
- Real/noise verdict: **NOISE — NO EDGE.** 1 closed trade, 1 win, 100% WR. This is meaningless with n=1. The 7 scanned signals over 90 days shows this class is nearly inactive.
- 90d expected P&L (1% risk, $100k): **$0** (1 trade, cannot draw conclusions)
- Gate change: **SMART_PICKS_MIN_SCORE_MEME = 90** (keep disabled; the 1 passed_smart is noise)
- Confidence (1-5): **1** — no data, no edge

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY:
**CRYPTO** — the only class with a statistically real, holdout-validated edge. The `dir=LONG & score_dec=S50 & source=alpha_engine` cell (n=339, WR=65.19%, PF=2.173, bonferroni_pass=true) is the single best signal in the system. However, I would NOT scale up at full size — the 65% WR in a bull market is concerning. **Recommendation: scale to 50% of target size, with a hard stop if the WR drops below 55% over the next 30 days.**

### DEMOTE (per MUTATION_THREE_AXIS_PROTOCOL):
1. **FOREX** — MUTATE FIRST: The smart gate is passing 84% of scanned signals (16,463/19,572), which is useless. The WR=28.04% is catastrophic. **Action: Set SMART_PICKS_MIN_SCORE_FOREX = 95, and if WR doesn't

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: CRYPTO proven cells (n=339, WR_shrunk 64%, PF 2.17) pass holdout + Bonferroni and look statistically credible; no obvious single-symbol concentration flagged.
- 90d expected P&L (1% risk, $100k): $2,850 (assume 1.2R avg winner, 0.6R loser after 0.15% slippage, ~110 trades at 1% risk).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 72
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: All cells noise; high PF driven by tiny WR and fails Bonferroni; no proven edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONFIDENCE = 0.82
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: All cells noise; holdout fails, low n, no proven edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_TRUST_COMMODITY = 55
- Confidence (1-5): 5

### EQUITY
- Real/noise verdict: Proven cells (n=59, WR_shrunk 86%, PF 159) are almost certainly leakage or single-symbol concentration; impossible real edge.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: EQUITY_MIN_MEAN_REVERSION_TRUST = 70
- Confidence (1-5): 5

### ETF
- Real/noise verdict: All cells noise; tiny n, negative expectancy, no proven edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_SCORE = 85
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: All cells noise; zero proven edges, negligible decisive trades.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: All cells noise; n=7 decisive, no proven edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONFIDENCE = 0.80
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: All cells noise; holdout fails, low n, no proven edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_TRUST_FUTURES = 60
- Confidence (1-5): 5

### BOND
- Real/noise verdict: All cells noise; negative expectancy, no proven edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: BOND_SCANNER_MIN_TRUST = 55
- Confidence (1-5): 5

### MEME
- Real/noise verdict: All cells noise; n=1, no proven edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 90
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with credible, Bonferroni-passed edge). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL (proven cells are leakage). All other classes have no usable edge.
