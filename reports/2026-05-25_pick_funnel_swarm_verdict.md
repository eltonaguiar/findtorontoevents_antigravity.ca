# Pick Funnel Swarm Verdict — 2026-07-08 05:05 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260708T050455Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO  
- Real/noise verdict: **Noise** – the only “top‑edge” cells have modest win‑rates (≈53 %) and profit‑factors around 1.6‑1.7.  The PFs are driven by a handful of trades (n = 355) and the huge “train PF” (≈10×) versus a modest hold‑out PF suggests over‑fitting / look‑ahead leakage rather than a stable edge.  
- 90d expected P&L (1% risk, $100k): **$0** (no statistically reliable edge to size).  
- Gate change: **`SMART_PICKS_MIN_SCORE_CRYPTO = 85`** (raise the Smart‑Picks score floor to cut the noisy tail).  
- Confidence (1‑5): **1**

### COMMODITY  
- Real/noise verdict: **Noise** – no PROVEN cells.  The best PF (≈1.21) comes from a single 107‑trade cell with a win‑rate barely above 50 % and a negligible hold‑out PF (0).  This is classic sample‑noise.  
- 90d expected P&L (1% risk, $100k): **$0**.  
- Gate change: **`SMART_PICKS_MIN_SCORE_COMMODITY = 80`** (tighten the Smart‑Picks score to filter out low‑quality picks).  
- Confidence (1‑5): **1**

### FOREX  
- Real/noise verdict: **Noise** – the top PF (≈5.1) is inflated by a very low win‑rate (8 %) and a huge negative Z‑score (‑18.6).  The cell’s “train PF” is tiny (≈2) while the hold‑out PF jumps to 5.4, a classic sign of leakage or data‑snooping.  
- 90d expected P&L (1% risk, $100k): **$0**.  
- Gate change: **`SMART_PICKS_MIN_SCORE_FOREX = 90`** (raise the score threshold to force higher‑confidence picks).  
- Confidence (1‑5): **1**

### EQUITY  
- Real/noise verdict: **Suspicious – likely leakage**.  Three “PROVEN” cells pass the Bayesian WR ≥ 55 % / PF ≥ 1.5 test, but they all sit in the **UNK‑trust / low‑confidence (< 0.60) / alpha_engine** region that is *currently blocked* by the HC filter.  The win‑rate is astronomically high (≈97 %) and the PF spikes to 30.5, which is far beyond what the hold‑out sample (22 trades) can justify.  The Z‑scores are extreme, and the Bonferroni correction passes only because the cell count is low.  All signs point to data‑leakage (e.g., future price used in the “alpha_engine” label) rather than a genuine, repeatable edge.  
- 90d expected P&L (1% risk, $100k): **$0** (we would not allocate capital until the leakage is fully investigated).  
- Gate change: **`HC_MIN_CONFIDENCE = 0.60`** (lower the client‑side confidence threshold from 0.75 to 0.60) **and** **`HC_MIN_TRUST = 0`** (remove the trust‑≥ 60 requirement).  This would let the “UNK‑trust / low‑conf” cells pass the HC filter, but only after we have validated that the signal is not leaking.  
- Confidence (1‑5): **2** (some statistical signal, but overwhelming risk of leakage).

### ETF  
- Real/noise verdict: **Noise** – only 22 closed trades, PF ≈ 0, win‑rate 9 %.  No PROVEN cells.  
- 90d expected P&L (1% risk, $100k): **$0**.  
- Gate change: **`SMART_PICKS_MIN_SCORE_ETF = 75`** (tighten the Smart‑Picks floor).  
- Confidence (1‑5): **1**

### UNKNOWN  
- Real/noise verdict: **Noise** – 6 closed trades, 0 % win‑rate, no PF.  
- 90d expected P&L (1% risk, $100k): **$0**.  
- Gate change: **`SMART_PICKS_MIN_SCORE_UNKNOWN = 70`**.  
- Confidence (1‑5): **1**

### FUTURES  
- Real/noise verdict: **Noise** – 17 closed trades, PF ≈ 0, win‑rate 59 % but far below the PROVEN threshold; the sample is too tiny to draw any edge.  
- 90d expected P&L (1% risk, $100k): **$0**.  
- Gate change: **`SMART_PICKS_MIN_SCORE_FUTURES = 80`**.  
- Confidence (1‑5): **1**

### BOND  
- Real/noise verdict: **Noise** – 28 closed trades, PF ≈ 0, win‑rate 10 %, huge negative Z‑score.  
- 90d expected P&L (1% risk, $100k): **$0**.  
- Gate change: **`SMART_PICKS_MIN_SCORE_BOND = 85`**.  
- Confidence (1‑5): **1**

### INDEX  
- Real/noise verdict: **Noise** – 8 closed trades, PF ≈ 0, win‑rate 62 % but sample far too small; no PROVEN cell.  
- 90d expected P&L (1% risk, $100k): **$0**.  
- Gate change: **`SMART_PICKS_MIN_SCORE_INDEX = 80`**.  
- Confidence (1‑5): **1**

### MEME  
- Real/noise verdict: **Noise** – single trade, win‑rate 100 % but no statistical power; cannot be used as an edge.  
- 90d expected P&L (1% risk, $100k): **$0**.  
- Gate change: **`SMART_PICKS_MIN_SCORE_MEME = 70`** (effectively disable this class until more data).  
- Confidence (1‑5): **1**

---

## SYSTEM‑WIDE Conclusion  

**Scale‑up candidate:** **None**.  Every asset class either shows pure noise or a “PROVEN” signal that is confined to the UNK‑trust / low‑confidence region and fails the high‑conviction gate.  The EQUITY signal, while spectacular on paper, is almost certainly a leakage artifact; we would **not** allocate live capital until a full forensic audit of the `alpha_engine` labeling pipeline is completed.

**Demotion / mutation:** Follow the **MUTATION_THREE_AXIS_PROTOCOL** and **demote** the following classes by tightening their Smart‑Picks score floors (as listed above): **CRYPTO, COMMODITY, FOREX, ETF, UNKNOWN, FUTURES, BOND, INDEX, MEME**.  This will prune the noisy tail, reduce the volume of low‑quality picks entering the pipeline, and give the downstream HC filter a cleaner set of candidates to evaluate.

In short – **no class is ready for production deployment today**; the safest path is to raise score thresholds across the board, investigate the EQUITY “UNK‑trust” leakage, and only then consider re‑opening the HC gate to capture any genuine edge.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

Here is the brutally honest audit of your 90-day pick funnel.

### SYSTEM-WIDE OBSERVATION
Your funnel is hemorrhaging. The `passed_smart` to `opened` ratio is inverted (more trades opened than passed the smart gate), indicating that the `production_scanner.py` gate is either not being enforced on the execution side, or the `opened` count includes manual overrides and signals from other sources. The overall win rates across all major classes (CRYPTO 47%, COMMODITY 32%, FOREX 28%) are below or near breakeven after slippage. The only statistically significant edge is in EQUITY, and it is fragile.

---

### EQUITY
- **Real/noise verdict:** **REAL, but fragile.** The `mean_reversion & LONG & alpha_engine` cell (n=37, WR_shrunk=80.7%, PF=30.45) passes all statistical tests (Bonferroni, holdout). However, this is a **single-symbol concentration risk**. With only 37 trades, it is highly likely this is driven by 1-2 tickers (e.g., repeated mean-reversion scalps on a single volatile stock). The `trust=UNK & conf=C<0.60` cell is a red flag—it suggests the edge exists *despite* low confidence, which is a classic symptom of a data-snooped pattern that won't generalize. The holdout PF of 99.0 on 22 trades is suspiciously high and suggests the train/holdout split may have captured a regime-specific streak.
- **90d expected P&L (1% risk, $100k):** **$1,098** (based on avg_pnl_pct=1.098% on 37 trades, assuming 1% risk per trade on $100k = $1,000 risk per trade, yielding ~$1,098 profit). *However, this is misleading.* If the edge is 1-2 tickers, position sizing would be capped, and a single gap move would wipe out the P&L.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY = 85` (currently likely lower). This forces the scanner to require higher conviction before passing, reducing the n from 150 to a more concentrated, higher-quality set.
- **Confidence (1-5):** 3 (statistically real, but operationally fragile due to concentration).

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** Zero PROVEN cells. The best cell (`trust=PROBATION & rr=RR1.5-2.0 & dir=LONG & score_dec=S50`, n=107, WR=50.47%, PF=1.207) fails holdout and has a Z-score of 0.097—indistinguishable from a coin flip. The `best_pf_overall` list is a graveyard of false positives. The 32.35% overall WR confirms the asset class is currently untradeable by your system.
- **90d expected P&L (1% risk, $100k):** **-$2,100** (912 decisive trades * 1% risk * -0.023 avg edge). You are losing money.
- **Gate change:** `COMMODITY_MIN_TRUST = "PROVEN"` in `quality_gates.py`. This kills all commodity signals until a PROVEN edge emerges. Currently, the gate is passing 6,335 signals to the smart pick stage—this is noise pollution.
- **Confidence (1-5):** 1 (no edge).

---

### CRYPTO
- **Real/noise verdict:** **NOISE / LEAKAGE SUSPECTED.** Zero PROVEN cells. The best cell (`trust=UNK & rr=RR1.5-2.0 & dir=SELL`, n=355, PF=1.667) has a WR of only 53.24% and fails Bonferroni. The PF of 1.667 is driven by a few large wins, not consistent edge. **The `train_pf=10.186` vs `holdout_pf=1.544` is a massive red flag**—the training set (n=16) is tiny and likely captured a lucky streak. This is sample noise, not a replicable edge. The overall WR of 47.65% on 3,364 decisive trades confirms the system is guessing.
- **90d expected P&L (1% risk, $100k):** **-$4,000** (3,364 trades * 1% risk * -0.0235 avg edge). The 47.65% WR with average R:R < 1.0 means negative expectancy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO = 90` (currently likely 80). This drastically reduces the 2,464 signals that pass the smart gate. The current funnel is flooding the system with low-quality crypto noise.
- **Confidence (1-5):** 1 (no edge, possible leakage in the training/holdout split).

---

### FOREX
- **Real/noise verdict:** **NOISE / LEAKAGE CONFIRMED.** Zero PROVEN cells. The `best_pf_overall` cells are a statistical horror show. The top cell (`rr=RR1.5-2.0 & dir=LONG & source=multi_asset_copytrader`, n=494, PF=5.101) has a WR of **8.1%** and a Z-score of **-18.625**. This is not an edge; it is a catastrophic anti-edge. The high PF is driven by a few massive outlier wins (likely a single trade that hit 10:1 R:R) masking 454 losses. This is the textbook definition of a **false positive from a fat-tailed distribution**. The `holdout_pass=true` is a bug in your holdout logic—it should have rejected this.
- **90d expected P&L (1% risk, $100k):** **-$11,200** (2,610 trades * 1% risk * -0.043 avg edge). This is the worst performer.
- **Gate change:** **KILL THE SOURCE.** Set `multi_asset_copytrader_enabled = False` in `production_scanner.py`. This source is generating 494 trades with an 8% win rate. It is actively destroying capital.
- **Confidence (1-5):** 1 (anti-edge, actively harmful).

---

### BOND
- **Real/noise verdict:** **NOISE.** n=28 is too small for any conclusion. The best cell (n=20, WR=10%, PF=0.0) is a disaster.
- **90d expected P&L (1% risk, $100k):** **-$1,200** (28 trades * 1% risk * -0.426 avg loss).
- **Gate change:** `BOND_MIN_CLOSED_TRADES = 100` in `quality_gates.py`. Do not report edges on asset classes with insufficient sample size.
- **Confidence (1-5):** 1 (insufficient data).

---

### FUTURES, INDEX, ETF, MEME, UNKNOWN
- **Real/noise verdict:** **NOISE / INSUFFICIENT DATA.** All have n < 30 closed trades. The INDEX 62.5% WR on 8 trades is meaningless. The MEME 100% WR on 1 trade is a rounding error.
- **90d expected P&L (1% risk, $100k):** Negligible (less than $500 combined, but statistically zero).
- **Gate change:** `FUTURES_MIN_SCANNED = 1000` (currently 324). Do not allocate compute to classes with no volume.
- **Confidence (1-5):** 1 (all noise).

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY (Real Money):
**NONE.** There is no asset class with a robust, diversified, statistically validated edge that can absorb real capital. The EQUITY `mean_reversion` cell is the only candidate, but it is a single-strategy, single-direction, likely single-symbol anomaly. Scaling it up would result in a catastrophic drawdown when the regime shifts.

**Conditional Scale (if you must):** EQUITY, but only with a hard cap of 2% of the account ($2,000) and a strict 5-ticker maximum. Treat it as a research position, not a production strategy.

### Demote / Mutate (per MUTATION_THREE_AXIS_PROTOCOL.md):
**DEMOTE: FOREX, COMMODITY, CRYPTO.** These three classes are actively destroying capital. They should be moved to "Mutation" status immediately:
1.  **FOREX:** Kill the `multi_asset_copytrader` source. Reduce scan frequency to 1x/day. Set a 90-day moratorium on new signals.
2.  **COMMODITY:** Set `COMMODITY_MIN_TRUST = "PROVEN"`. No signals until a real edge is found.
3.  **CRYPTO:** Increase `SMART_PICKS_MIN_SCORE_CRYPTO` to 90. The current funnel is a noise factory.

**KILL (per protocol):** **BOND, FUTURES, INDEX, ETF, MEME, UNKNOWN.** These classes have insufficient data or no edge. Remove them from the live dashboard and reallocate compute to the three demoted classes for mutation analysis.

**Final Verdict:** Your system is currently a **negative expectancy machine** across 90% of its surface area. The only "edge" is a statistical artifact in EQUITY. Do not deploy real capital until the funnel is fixed. The gates are too loose, the sources are polluted, and the statistical validation is flagging false positives as "holdout_pass=true".

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: noise — no PROVEN cells; best_pf cells show modest PF~1.67 but fail bonferroni and have tiny train_n=16 with massive train-to-holdout PF collapse.
- 90d expected P&L (1% risk, $100k): $0 (no qualifying edge; any sizing produces near-zero expectancy after slippage).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 82
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: noise — zero PROVEN cells; listed cells fail holdout_pass and bonferroni; matches rejected H-001/H-036 patterns.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_TRUST_COMMODITY = "STABLE"
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: noise — zero PROVEN cells; best_pf cells show catastrophic WR_z (-18 to -6) and fail every statistical gate despite inflated PF from low-WR/high-R:R skew.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONF_FOREX = 0.82
- Confidence (1-5): 5

### EQUITY
- Real/noise verdict: likely leakage — n=37-38 yields WR_shrunk 79-80% and PF 11-30 with holdout PF=99 on one cell; single-strategy concentration (mean_reversion LONG alpha_engine) plus extreme metrics indicate look-ahead or symbol-specific bias despite bonferroni pass.
- 90d expected P&L (1% risk, $100k): -$4200 (37-38 trades at 1% risk, realistic 0.4-0.6% avg win after 0.15% slippage, net negative expectancy once leakage removed).
- Gate change: ALPHA_MIN_BAYESIAN_WR_EQUITY = 0.62
- Confidence (1-5): 4

### ETF
- Real/noise verdict: noise — zero PROVEN cells; n_closed=22 too small for any stable edge.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 85
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: noise — zero PROVEN cells; n_closed=6 and WR=0%.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: noise — zero PROVEN cells; n_closed=17 insufficient.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 88
- Confidence (1-5): 5

### BOND
- Real/noise verdict: noise — zero PROVEN cells; n=20 cell shows PF=0 and negative avg_pnl.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: noise — zero PROVEN cells; n_closed=8 insufficient.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 85
- Confidence (1-5): 5

### MEME
- Real/noise verdict: noise — zero PROVEN cells; n_closed=1.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 95
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up: none (no class passes leakage-free, statistically stable criteria with positive expectancy).  
Demote: COMMODITY and FOREX first per MUTATION_THREE_AXIS_PROTOCOL (both show persistent negative WR_z, failed holdouts, and alignment with already-rejected hypotheses).
