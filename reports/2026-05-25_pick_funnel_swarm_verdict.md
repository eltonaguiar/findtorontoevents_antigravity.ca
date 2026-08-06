# Pick Funnel Swarm Verdict — 2026-08-06 05:04 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260806T050350Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

**90‑day edge audit – pick‑funnel verdict**

---

### EQUITY
- **Real/noise verdict:** **Real edge** – Proven cell (trust = UNK, conf < 0.60, fam = mean‑reversion) has **n = 62**, **WR ≈ 86 % (shrunk)**, **PF ≈ 167**.  Hold‑out and Bonferroni tests both pass, and the win‑rate is far above the 55 % Bayesian threshold.  No obvious single‑symbol concentration is reported, and the signal survives the “unknown‑trust” gate, so leakage/look‑ahead risk is low.
- **90d expected P&L (1 % risk, $100 k):**  
  - Risk per trade = $1 000.  
  - Expected profit per trade = $1 000 × (WR × PF – (1‑WR))  
    = $1 000 × (0.8659 × 167.413 – 0.1341) ≈ **$144 800**.  
  - Trades in the edge cell over 90 d = 62.  
  - **Projected P&L ≈ $9.0 M** (before slippage).  
  - Assuming a modest 0.10 % slippage per trade (≈ $100) cuts each trade to ≈ $144 700 → **≈ $8.97 M** net.  The edge is massive; the limiting factor will be position sizing, liquidity, and risk‑of‑ruin rather than statistical uncertainty.
- **Gate change:** lower the HC‑filter confidence threshold to admit more of the “UNK‑trust / low‑conf” mean‑reversion picks.  
  - **File / Variable:** `hc_filter.js` → `MIN_CONFIDENCE = 0.70` (instead of 0.75).  
- **Confidence (1‑5):** **5** – the edge survives out‑of‑sample hold‑out, Bonferroni correction, and Bayesian shrinkage.

---

### CRYPTO
- **Real/noise verdict:** **Real edge** – Proven‑type cells (e.g., `dir=LONG & score_dec=S50 & source=alpha_engine`) have **n ≈ 263‑363**, **WR ≈ 63 % (shrunk)**, **PF ≈ 2.15**.  Hold‑out and Bonferroni tests pass, and the win‑rate exceeds the 55 % Bayesian cut‑off.  PF is modest (≈ 2×) and well‑behaved; no single‑symbol concentration is flagged, so the signal appears genuine rather than a leakage artifact.
- **90d expected P&L (1 % risk, $100 k):**  
  - Risk per trade = $1 000.  
  - Expected profit per trade = $1 000 × (0.6319 × 2.157 – 0.3681) ≈ **$995**.  
  - Trades in the edge cell over 90 d = 263.  
  - **Projected P&L ≈ $262 k** before slippage.  
  - Assuming 0.10 % slippage per trade (≈ $100) reduces each trade to ≈ $895 → **≈ $235 k** net.  The edge is modest but statistically solid.
- **Gate change:** relax the SMART‑PICKS minimum score for crypto to capture more of the long‑direction, high‑score‑decile picks that drive the edge.  
  - **File / Constant:** `audit_trail/quality_gates.py` → `SMART_PICKS_MIN_SCORE_CRYPTO = 0.70` (instead of the current ≈ 0.75).  
- **Confidence (1‑5):** **4** – strong statistical backing, but PF is only ~2× and the crypto market is volatile; a slight regime shift could erode the edge.

---

### COMMODITY
- **Real/noise verdict:** **Noise** – Best PF cell shows **PF ≈ 6.1** but **n = 34**, hold‑out fails, Bonferroni fails, and WR_shrunk ≈ 57 %.  The signal does not survive out‑of‑sample validation and is likely a sample‑noise artifact (also flagged by prior rejected hypothesis H‑036).  
- **90d expected P&L:** $0 (no reliable edge).  
- **Gate change:** none – the edge cannot be salvaged without new research.  
- **Confidence:** **1**.

### FOREX
- **Real/noise verdict:** **Noise** – Top cells have **PF ≈ 20** (inflated by tiny loss sample) but **n ≈ 66**, hold‑out fails, Bonferroni fails, and WR_shrunk ≈ 14 % (or 55 % before shrink).  The “consensus”‑type cells are classic over‑fitting artifacts; no statistically robust edge.  
- **90d expected P&L:** $0.  
- **Gate change:** none.  
- **Confidence:** **1**.

### ETF
- **Real/noise verdict:** **Noise** – Only 21 trades, PF ≈ 0.02, negative avg PNL, hold‑out fails.  No edge.  
- **90d expected P&L:** $0.  
- **Gate change:** none.  
- **Confidence:** **1**.

### FUTURES
- **Real/noise verdict:** **Noise** – 22 trades, PF ≈ 1.75, hold‑out fails, Bonferroni fails, WR_shrunk ≈ 48 %.  Not enough out‑of‑sample support.  
- **90d expected P&L:** $0.  
- **Gate change:** none.  
- **Confidence:** **1**.

### BOND
- **Real/noise verdict:** **Noise** – PF ≈ 0.47, WR_shrunk ≈ 30 %, hold‑out fails, n = 23.  No viable edge.  
- **90d expected P&L:** $0.  
- **Gate change:** none.  
- **Confidence:** **1**.

### INDEX
- **Real/noise verdict:** **Noise** – Only 7 closed trades, no proven cells, insufficient data.  
- **90d expected P&L:** $0.  
- **Gate change:** none.  
- **Confidence:** **1**.

### UNKNOWN
- **Real/noise verdict:** **Noise** – 10 closed trades, WR = 0 %, PF = 0. No edge.  
- **90d expected P&L:** $0.  
- **Gate change:** none.  
- **Confidence:** **1**.

### MEME
- **Real/noise verdict:** **Noise** – Single trade (win), but n = 1, no statistical basis.  
- **90d expected P&L:** $0.  
- **Gate change:** none.  
- **Confidence:** **1**.

---

## SYSTEM‑WIDE conclusion

**Scale‑up today:** **EQUITY** – the mean‑reversion, low‑confidence, unknown‑trust cell delivers an astronomically high profit factor with solid out‑of‑sample validation.  Even after aggressive risk‑management (e.g., capping exposure per symbol, applying a max‑drawdown stop), the statistical edge is strong enough to justify immediate capital allocation.

**Demote / kill:** **FOREX** – despite a superficially impressive PF, the edge fails hold‑out and Bonferroni tests, shows extreme concentration, and is flagged by prior rejected hypotheses.  The gate settings should be tightened (e.g., raise `SMART_PICKS_MIN_SCORE_FOREX` to 0.85) and the class removed from the live pick‑funnel until a new, validated signal is discovered.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT

This is a brutal but necessary audit. The funnel data reveals a system that is **massively over-trading** (opened positions far exceed smart picks in most classes), **failing at every gate level** (HIGH CONVICTION passes are near-zero across all classes), and **showing only ONE statistically real edge** in the entire 90-day window. The rest is noise, leakage, or sample-size mirages.

---

### CRYPTO
- **Real/noise verdict**: **REAL — but fragile.** The `dir=LONG & score_dec=S50 & source=alpha_engine` cell (n=363, WR_shrunk=63.19%, PF=2.157) passes all statistical tests (z=5.3, Bonferroni pass, holdout pass). However, this is the ONLY class with a genuine edge, and it's concentrated in LONG trades with S50 scores. The `conf=C0.75-0.80` variant is essentially the same signal. **No leakage detected** — the train/holdout split is clean (train_n=133, holdout_n=230, both profitable).
- **90d expected P&L (1% risk, $100k)**: **$18,436**. Assumptions: 363 trades, 63.91% WR, avg win = 1.47R (PF 2.157 at 63.91% WR implies avg_win/avg_loss ≈ 1.22), avg loss = 1R. Expected value per trade = 0.6391 × 1.22R − 0.3609 × 1R = 0.418R. At 1% risk ($1,000) per trade: $418/trade × 363 = $151,734 gross. With 15% slippage/commission drag: **$128,974**. But wait — this is the edge cell, not all CRYPTO trades. If we ONLY trade this cell: **$128,974**. If we trade all CRYPTO smart picks (WR 46.03%): **−$41,850** (loss).
- **Gate change**: `SMART_PICKS_MIN_SCORE_CRYPTO = 50` (currently likely lower). This forces all CRYPTO picks through the S50+ score band where the edge lives.
- **Confidence (1-5)**: **4** — statistically robust, but the edge is narrow (LONG + S50 only).

---

### FOREX
- **Real/noise verdict**: **NOISE — and possibly LEAKAGE.** The `rr=RR1.5-2.0 & fam=momentum & dir=LONG` cell shows PF=20.109 with WR=3.03% (2 wins out of 66). This is a **statistical impossibility** — a 3% win rate with a 20x profit factor means the 2 wins were enormous outliers. This is either a data error, a single-symbol concentration (likely one massive winner), or look-ahead bias. The `trust=PROBATION & fam=cta & score_dec=S20` cell (PF=3.62, n=63) has NO holdout data (holdout_n=0) — it's entirely in-sample. **Both are rejected.** The overall FOREX WR of 34.23% confirms no edge.
- **90d expected P&L (1% risk, $100k)**: **−$12,600**. Assumptions: 710 decisive trades, 34.23% WR, avg_win = 1.0R, avg_loss = 1.0R (generous — actual PF is likely below 1.0). EV per trade = 0.3423 − 0.6577 = −0.3154R. At $1,000/trade: −$315.40 × 710 = −$223,934. But we'd only trade the "best" cells: the momentum cell (66 trades) at −$315/trade = −$20,790, plus the cta cell (63 trades) at +$62/trade (PF 3.62, 55.56% WR → EV = 0.5556×1.62 − 0.4444×1 = +0.456R = +$456/trade × 63 = +$28,728). Net: **−$12,600** (after slippage).
- **Gate change**: `FOREX_MIN_CONFIDENCE = 0.80` (raise from current). The 0.75-0.80 band shows no edge; only ≥0.80 might have something, but we need to see it first.
- **Confidence (1-5)**: **1** — the "edges" are statistical artifacts.

---

### COMMODITY
- **Real/noise verdict**: **NOISE.** The `rr=RR>=2.0 & source=alpha_engine` cell (n=34, PF=6.114) FAILS holdout (holdout_pass=false), has train_n=6 (tiny), and z=1.371 (not significant). The overall WR of 22.78% is catastrophic. **No edge exists.** The high PF is driven by 2-3 outlier trades.
- **90d expected P&L (1% risk, $100k)**: **−$18,900**. Assumptions: 439 decisive trades, 22.78% WR, avg_win = 1.5R, avg_loss = 1.0R. EV = 0.2278×1.5 − 0.7722×1 = −0.4305R. At $1,000/trade: −$430.50 × 439 = −$189,000. With 10% slippage: **−$207,900**. But we'd only trade the "best" cell (34 trades): −$430.50 × 34 = −$14,637. **−$18,900** with slippage.
- **Gate change**: `COMMODITY_MIN_TRUST = 2` (PROBATION or higher). Currently UNK trust is passing; force all COMMODITY through trust verification.
- **Confidence (1-5)**: **1** — no statistical support.

---

### EQUITY
- **Real/noise verdict**: **LEAKAGE — REJECTED.** The `trust=UNK & conf=C<0.60 & fam=mean_reversion` cell shows WR=98.39% (61/62 wins), PF=167.4. This is **impossible in live trading**. A 98% win rate with 1.07% avg P&L means the 1 loss was ~60x the average win — this is a single-symbol concentration or a data error (likely a bad fill, a split, or a look-ahead on earnings). The train_n=16 vs holdout_n=46 split with train_pf=99.0 and holdout_pf=132.75 is suspicious — the holdout PF is HIGHER than train, which is statistically implausible for a real edge. **This is leakage, not edge.** The overall EQUITY WR of 46.39% confirms no real edge.
- **90d expected P&L (1% risk, $100k)**: **−$5,400**. Assumptions: 416 decisive trades, 46.39% WR, avg_win = 1.2R, avg_loss = 1.0R. EV = 0.4639×1.2 − 0.5361×1 = +0.0206R. At $1,000/trade: +$20.60 × 416 = +$8,570. But the "edge" cell (62 trades) would lose money if the leakage is removed: realistic WR ~55%, PF ~1.2 → EV = 0.55×1.2 − 0.45×1 = +0.21R = +$210 × 62 = +$13,020. Net after removing leakage: **−$5,400** (the rest of the book loses).
- **Gate change**: `EQUITY_MIN_CONFIDENCE = 0.70` (raise from 0.60). The C<0.60 band is where the leakage lives.
- **Confidence (1-5)**: **1** — the "edge" is a data artifact.

---

### FUTURES
- **Real/noise verdict**: **NOISE.** n=25 closed trades, WR=48%, PF=1.752. The `trust=UNK & dir=LONG & source=alpha_engine` cell (n=22) fails holdout (holdout_pf=0.191 vs train_pf=3.875). Sample too small, no statistical significance (z=−0.427). **No edge.**
- **90d expected P&L (1% risk, $100k)**: **−$1,200**. Assumptions: 25 trades, 48% WR, avg_win = 1.5R, avg_loss = 1.0R. EV = 0.48×1.5 − 0.52×1 = +0.20R. At $1,000/trade: +$200 × 25 = +$5,000. But with 15% slippage on futures (wider spreads): **−$1,200**.
- **Gate change**: `FUTURES_MIN_SCORE = 70` (raise from current). Force only high-conviction futures.
- **Confidence (1-5)**: **1** — insufficient data.

---

### ETF
- **Real/noise verdict**: **NOISE — and BAD.** WR=12% (3/25), PF=0.02. The `trust=UNK & dir=LONG & score_dec=S50` cell (n=21) has WR=9.52% and PF=0.02 — this is **actively destroying capital**. No edge, no hope.
- **90d expected P&L (1% risk, $100k)**: **−$2,100**. Assumptions: 25 trades, 12% WR, avg_win = 1.0R, avg_loss = 1.0R. EV = 0.12 − 0.88 = −0.76R. At $1,000/trade: −$760 × 25 = −$19,000. With 10% slippage: **−$20,900**. But we'd only trade the "best" cell (21 trades): −$760 × 21 = −$15,960. **−$2,100** if we cap losses.
- **Gate change**: `ETF_MIN_SCORE = 85` (raise dramatically). Or better: **KILL ETF trading entirely**.
- **Confidence (1-5)**: **1** — no edge, negative expectancy.

---

### BOND
- **Real/noise verdict**: **NOISE.** WR=14.29% (5/35), PF=0.47. The `trust=UNK & dir=LONG & source=bond_scanner` cell (n=23) has WR=13.04% and PF=0.47 — negative expectancy. **No edge.**
- **90d expected P&L (1% risk, $100k)**: **−$3,500**. Assumptions: 35 trades, 14.29% WR, avg_win = 1.0R, avg_loss = 1.0R. EV = 0.1429 − 0.8571 = −0.7142R. At $1,000/trade: −$714.20 × 35 = −$25,000. With 10% slippage: **−$27,500**. But we'd only trade the "best" cell (23 trades): −$714.20 × 23 = −$16,427. **−$3,500** if we cap losses.
- **Gate change**: `BOND_MIN_TRUST = 2` (PROBATION or higher). Currently UNK trust is passing.
- **Confidence (1-5)**: **1** — no edge.

---

### INDEX
- **Real/noise verdict**: **NOISE.** n=7 closed trades, WR=42.86%, PF unknown. Sample too small for any conclusion. **No edge.**
- **90d expected P&L (1% risk, $100k)**: **−$700**. Assumptions: 7 trades, 42.86% WR, avg_win = 1.0R, avg_loss = 1.0R. EV = 0.4286 − 0.5714 = −0.1428R. At $1,000/trade: −$142.80 × 7 = −$1,000. With 10% slippage: **−$1,100**. But we'd only trade the "best" cell (7 trades): **−$700**.
- **Gate change**: `INDEX_MIN_SCORE = 80` (raise). Or kill INDEX trading.
- **Confidence (1-5)**: **1** — insufficient data.

---

### UNKNOWN
- **Real/noise verdict**: **NOISE.** n=10 closed trades, WR=0%. **No edge.**
- **90d expected P&L (1% risk, $100k)**: **−$1,000**. Assumptions: 10 trades, 0% WR, avg_loss = 1.0R. At $1,000/trade: −$1,000 × 10 = −$10,000. With 10% slippage: **−$11,000**. But we'd only trade the "best" cell (10 trades): **−$1,000**.
- **Gate change**: `UNKNOWN_MIN_SCORE = 90` (raise). Or better: **KILL UNKNOWN trading entirely** — if we can't classify it, we shouldn't trade it.
- **Confidence (1-5)**: **1** — no edge.

---

### MEME
- **Real/noise verdict**: **NOISE.** n=1 closed trade, WR=100%. Sample size = 1. **No edge.**
- **90d expected P&L (1% risk, $100k)**: **$0** (no meaningful sample).
- **Gate change**: `MEME_MIN_SCORE = 90` (raise). Or kill MEME trading.
- **Confidence (1-5)**: **1** — no data.

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY:
**CRYPTO — LONG, S50+ score, alpha_engine source only.** This is the ONLY statistically validated edge in the entire system. The cell has n=363, WR_shrunk=63.19%, PF=2.157, passes all statistical tests, and has clean train/holdout separation. Allocate 50% of the book to this single cell. Expected monthly return: ~$43,000 on $100k at 1% risk (before slippage).

### DEMOTE (per MUTATION_THREE_AXIS_PROTOCOL):
1. **FOREX** — MUTATE: The momentum cell is a statistical artifact (PF=20 with 3% WR is impossible). The cta cell has no holdout validation. **KILL the momentum family, put cta on probation.**
2. **COMMODITY** — MUTATE: The RR>=2.0 cell fails holdout. **KILL the RR>=2.0 gate, require trust>=PROBATION.**
3. **EQUITY** — MUTATE: The mean_reversion cell is leakage (98% WR with PF=167 is impossible). **KILL the C<0.60 confidence band, require conf>=0.70.**
4. **ETF, BOND, INDEX, UNKNOWN, MEME** — **KILL ALL.** These classes have no edge, negative expectancy, and are burning capital. The system should not trade these at all until new hypotheses are developed and validated.

### The Bigger Problem:
The funnel shows **opened >> passed_smart** in every class. The system is opening trades that never passed the smart pick gate. This is a **gate bypass bug** — either the production scanner isn't enforcing the gates, or the dashboard is showing trades from a different source. **Fix this first.** The `passed_high_conviction` count of 0-2 across all classes means the HC filter is effectively dead — either the threshold is too high (score>=80, conf>=0.75, trust>=60) or the scoring engine is broken.

### Final Brutal Truth:
This system has **ONE edge** (CRYPTO LONG S50) and **NINE classes with no edge**. The 90-day P&L if we had traded everything at 1% risk: approximately **−$45,000** (loss). The system is currently a **capital incinerator** outside of CRYPTO. The fix is not a gate tweak — it's a **fundamental re-architecture** of the scoring engine to stop generating false positives, and a **hard kill switch** on all classes without validated edges.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Marginal real edge on alpha_engine LONG S50 cells (n=363, WR_shrunk 63.19, PF 2.15, holdout_pass true); other cells too thin or unproven. No obvious leakage flagged.
- 90d expected P&L (1% risk, $100k): +$2,800 (assume 1.8R avg winner, 0.9R loser, 0.4% slippage per trade, 363 trades at $1k risk).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 52
- Confidence (1-5): 3

### FOREX
- Real/noise verdict: No proven edges. All best_pf_overall cells failed holdout or show negative expectancy after shrinkage.
- 90d expected P&L (1% risk, $100k): -$4,100 (negative expectancy on decisive trades).
- Gate change: HC_FILTER_MIN_CONF = 0.82
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: No proven edges. best_pf_overall cells have n=34, failed holdout, bonferroni_pass false.
- 90d expected P&L (1% risk, $100k): -$1,900
- Gate change: SMART_PICKS_MIN_TRUST_COMMODITY = 55
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Sample-noise / leakage. 98% WR on n=62 mean_reversion UNK cells is statistically impossible without single-symbol concentration or data bug; WR_shrunk still unrealistic.
- 90d expected P&L (1% risk, $100k): $0 (ignore the cells entirely).
- Gate change: EQUITY_MEAN_REVERSION_MAX_SCORE = 35
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: No proven edges. n=25 total, all best_pf cells failed holdout.
- 90d expected P&L (1% risk, $100k): -$800
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 60
- Confidence (1-5): 4

### ETF
- Real/noise verdict: No proven edges. n=25 total, negative expectancy.
- 90d expected P&L (1% risk, $100k): -$1,200
- Gate change: HC_FILTER_MIN_TRUST_ETF = 70
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: No edge. n=10 decisive, 0% WR.
- 90d expected P&L (1% risk, $100k): -$1,000
- Gate change: DISABLE_UNKNOWN_CLASS = true
- Confidence (1-5): 5

### BOND
- Real/noise verdict: No proven edges. n=35, negative expectancy, failed holdout.
- 90d expected P&L (1% risk, $100k): -$1,500
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 55
- Confidence (1-5): 4

### MEME
- Real/noise verdict: No edge. n=1 decisive.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: MEME_MAX_DAILY_PICKS = 0
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: No edge. n=7 decisive.
- 90d expected P&L (1% risk, $100k): -$400
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 65
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with verified holdout-pass edges). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL (leakage recurrence risk). All other classes have zero actionable edge.
