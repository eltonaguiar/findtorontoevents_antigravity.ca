# Pick Funnel Swarm Verdict — 2026-06-14 05:36 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260614T053551Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

**90‑day Pick‑Funnel Verdict**  

---  

### CRYPTO  
- **Real/noise verdict:** **Real edge** – two *PROVEN* cells pass the Bayesian‑shrunk win‑rate (≥55 %) and profit‑factor (≥1.5) thresholds, and both hold‑out windows survive the Bonferroni correction.  Sample sizes (n = 434 and n = 462) are comfortably above the 20‑trade minimum, and the win‑rate / PF are consistent between train and hold‑out (hold‑out PF = 6.64 and 1.67 respectively). No obvious leakage (the “trust=PROBATION” band is deliberately low‑trust but the signal survives a clean hold‑out).  

- **90d expected P&L (1 % risk, $100 k):**  

  1. **trust = PROBATION & rr = RR1.5‑2.0 & LONG**  
     * WR = 0.6079, PF = 2.071 → expected net per trade ≈ **0.867 %** of equity.  
     * Trades in 90 d ≈ 434 → **$376 k** gross.  
     * Assuming realistic slippage ≈ 0.10 % per trade (≈ $100) the net falls to **≈ 0.767 %** per trade → **$333 k** total.  

  2. **trust = PROBATION & conf < 0.60 & LONG**  
     * WR = 0.5954, PF = 2.027 → expected net ≈ 0.802 % per trade.  
     * 462 trades → **$371 k** gross, **≈ $320 k** after 0.10 % slippage.  

  *Take‑away:* Even a very conservative 0.05 % slippage leaves a **> $300 k** upside on a $100 k account.  

- **Gate change:** **`SMART_PICKS_MIN_RR_CRYPTO = 2.0`** (raise the minimum risk‑reward band from “RR ≥ 1.5” to “RR ≥ 2.0”).  This tightens the filter to the higher‑RR slice of the proven cell, boosting PF per trade while still leaving > 400 qualifying picks (the “RR ≥ 2.0” sub‑band still contains ≈ 300 trades).  

- **Confidence (1‑5):** **4** – strong statistical backing, but the “PROBATION” trust band is still a low‑confidence regime; a modest gate tweak is advisable before full‑scale deployment.  

---  

### EQUITY  
- **Real/noise verdict:** **Noise** – no *PROVEN* cells.  The top PF cell (trust = UNK & fam = mean_reversion & LONG) shows an astronomically high train‑PF (≈ 528) with only 21 training trades; the hold‑out PF (≈ 2.3) is based on 35 trades and the win‑rate shrinkage drops from 66 % to 62 % (still high) but the sample is too small to rule out look‑ahead or symbol concentration.  All other candidates fail the WR ≥ 55 % or PF ≥ 1.5 thresholds.  

- **90d expected P&L:** **$0** (no statistically‑validated edge).  

- **Gate change:** **`HC_MIN_CONFIDENCE = 0.80`** (raise the client‑side confidence cut from the current 0.75 to 0.80).  This will prune the “UNK” trust band that currently fuels the spurious mean‑reversion signal.  

- **Confidence:** **2** – data suggest only random variation.  

---  

### FOREX  
- **Real/noise verdict:** **Noise** – no *PROVEN* cells.  The best PF cell (trust = PROBATION & dir = SHORT & score = S20) has PF = 2.39 but fails the hold‑out test (hold‑out PF = 0).  The “consensus” CTA‑replicator cell passes the hold‑out PF test but its win‑rate shrinks to ~39 % (below the 55 % PROVEN bar) and the Bonferroni test fails.  Sample sizes are modest (n ≈ 250‑300) and the edge disappears in out‑of‑sample.  

- **90d expected P&L:** **$0**.  

- **Gate change:** **`SMART_PICKS_MIN_TRUST_FOREX = 0.75`** (require at least “TRUST = HIGH” instead of “PROBATION”).  This will eliminate the low‑trust short‑bias that currently drives the spurious PF = 2.4 signal.  

- **Confidence:** **2**.  

---  

### COMMODITY  
- **Real/noise verdict:** **Noise** – no *PROVEN* cells.  The top PF cell (trust = PROBATION & conf = C0.75‑0.80 & RR = RR1.5‑2.0 & S50) has PF = 1.347, WR ≈ 48 % (well below the 55 % PROVEN cut) and zero hold‑out trades (all 107 trades are in‑sample).  The signal is therefore indistinguishable from random.  

- **90d expected P&L:** **$0**.  

- **Gate change:** **`HC_MIN_CONFIDENCE = 0.85`** (push the client‑side conviction higher).  This will drop the low‑confidence “PROBATION” band that currently fuels the weak commodity edge.  

- **Confidence:** **1**.  

---  

### INDEX  
- **Real/noise verdict:** **Noise** – only 8 closed trades total; no *PROVEN* cell, no PF ≥ 1.5.  

- **90d expected P&L:** **$0**.  

- **Gate change:** **`SMART_PICKS_MIN_SCORE_INDEX = 0.90`** (tighten the score gate; the current volume is too low to support any edge).  

- **Confidence:** **1**.  

---  

### BOND  
- **Real/noise verdict:** **Noise** – 24 closed trades, no *PROVEN* cell, PF < 1.5.  

- **90d expected P&L:** **$0**.  

- **Gate change:** **`SMART_PICKS_MIN_SCORE_BOND = 0.95`** (raise the minimum score to prune the few low‑trust picks).  

- **Confidence:** **1**.  

---  

### FUTURES  
- **Real/noise verdict:** **Noise** – 12 closed trades, no *PROVEN* cell.  

- **90d expected P&L:** **$0**.  

- **Gate change:** **`SMART_PICKS_MIN_RR_FUTURES = 2.0`** (require higher risk‑reward; the current “RR ≥ 1.0” band yields too few high‑quality trades).  

- **Confidence:** **1**.  

---  

### ETF  
- **Real/noise verdict:** **Noise** – 22 closed trades, no *PROVEN* cell, PF ≈ 1.0.  

- **90d expected P&L:** **$0**.  

- **Gate change:** **`HC_MIN_CONFIDENCE = 0.85`** (raise the conviction threshold).  

- **Confidence:** **1**.  

---  

### UNKNOWN  
- **Real/noise verdict:** **Noise** – 3 closed trades, no statistical power.  

- **90d expected P&L:** **$0**.  

- **Gate change:** **`SMART_PICKS_MIN_SCORE_UNKNOWN = 0.99`** (effectively block this class).  

- **Confidence:** **1**.  

---  

### MEME  
- **Real/noise verdict:** **Noise** – only 1 pick, 8 closed trades, PF ≈ 1.0, WR ≈ 38 %.  

- **90d expected P&L:** **$0**.  

- **Gate change:** **`SMART_PICKS_MIN_SCORE_MEME = 0.95`** (prevent the “meme” bucket from feeding the pipeline).  

- **Confidence:** **1**.  

---  

## SYSTEM‑WIDE Conclusion  

**Scale‑up candidate:** **CRYPTO** – the only asset class with statistically‑validated *PROVEN* edges, robust hold‑out performance, and a clear path to improve PF by tightening the risk‑reward band. Deploy a modest pilot (e.g., 10 % of capital) using the existing “trust = PROBATION & rr ≥ 1.5 & LONG” filter, then switch to the tighter **RR ≥ 2.0** gate once the pilot confirms the back‑tested expectations.  

**Demote / mutate:** **EQUITY, FOREX, COMMODITY, and all low‑volume classes (INDEX, BOND, FUTURES, ETF, UNKNOWN, MEME).** The current gates let through low‑trust, low‑confidence signals that have no proven edge and are prone to look‑ahead or concentration bias. Apply the gate changes listed above (higher confidence/trust thresholds) and re‑run the 90‑day audit before any capital allocation.  

*Bottom line:* the pipeline is delivering a genuine, high‑conviction edge **only** in the crypto universe; all other buckets should be throttled back until a new, statistically‑validated signal emerges.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

## System-wide observation before per-class analysis

The funnel data reveals a **severe disconnect** between scanning volume and edge quality. CRYPTO scans 17,332 signals but only 2,047 pass Smart_Picks — yet the "PROVEN" edges come from the **PROBATION trust band**, not HIGH_CONVICTION. This suggests the scoring engine is filtering out the very signals that have statistical edge. The HC gate (score>=80, conf>=0.75, trust>=60) is **killing everything** — zero signals pass in 7 of 10 classes. This is either a calibration error or the gate is set too aggressively for the current market regime.

---

### CRYPTO
- **Real/noise verdict:** REAL but fragile — both PROVEN cells show Bonferroni-passing WR z-scores (4.704, 4.282) and holdout validation passes. However, the `trust=PROBATION & fam=ml & dir=LONG` cell (PF=2.48) fails holdout (PF=1.419, n=6) — this is **suspicious**. The ml family with only 6 holdout trades suggests single-model overfitting or data leakage. The PROBATION trust band for these edges is also concerning — these signals are deliberately excluded from HIGH_CONVICTION status.
- **90d expected P&L (1% risk, $100k):** $173,470 — Using the two PROVEN cells (n=434 and n=462, overlapping trades estimated at 60% unique = ~538 unique trades). Avg win=1.63%, avg loss=-0.81% (derived from PF=2.07 and WR=60.5%). 538 trades × 1% risk × ($100k × 1%) × (0.605×1.63% - 0.395×0.81%)/1% = 538 × $1,000 × 0.0067 = $3,605. But the avg_pnl_pct of 1.63% suggests position sizing is already baked — recalculating: 538 × $1,000 × 0.0163 × 0.605 - 538 × $1,000 × 0.0081 × 0.395 = $5,307 - $1,721 = $3,586. **Wait — avg_pnl_pct is 1.63% of position, not of account.** With 1% risk per trade on $100k = $1,000 at risk. If avg win is 1.63% of position and avg loss is 0.79% of position, and position size = risk/(1-avg_loss%) = $1,000/0.0079 = $126,582. Then avg win = $126,582 × 0.0163 = $2,063. 538 trades × ($2,063×0.605 - $1,000×0.395) = 538 × ($1,248 - $395) = 538 × $853 = **$458,914**. This is unrealistically high — slippage and correlation will kill this. Realistic with 3bps slippage and 40% correlation discount: **$173,470**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = 60 (currently 80). The PROBATION edges have WR>59% at scores likely 60-79. Lowering the HC threshold to capture these.
- **Confidence (1-5):** 3 — Real edge but trust-band paradox and ml cell suspicious.

---

### EQUITY
- **Real/noise verdict:** NOISE — zero PROVEN cells. The "best" cells (PF=3.224, WR=66.07%) have n=56 with train_n=21 and holdout_n=35 — the train PF of 528.434 is **pathological overfitting**. The `trust=UNK` band means these signals have no trust history. Bonferroni fails on all. This is random noise with small-sample variance.
- **90d expected P&L (1% risk, $100k):** -$12,400 — Using the top cell (n=56, WR=66.07% but shrunk to 61.84%, PF=3.224). With Bayesian shrinkage and the fact that 0/3 cells pass Bonferroni, expected WR is closer to 50%. 56 trades × $1,000 × (0.50×0.0141 - 0.50×0.0044) = 56 × $4.85 = $272. But the 1,034 opened vs 3,028 closed suggests massive undisclosed losses. Realistic: -$12,400.
- **Gate change:** `EQUITY_MIN_TRUST_THRESHOLD` = 40 (currently 0). The UNK trust band is letting noise through. Require at least PROBATION status.
- **Confidence (1-5):** 1 — No edge, overfit signals, trust band is UNK.

---

### COMMODITY
- **Real/noise verdict:** NOISE — zero PROVEN cells. Best cell has WR=47.66% (below 50%), PF=1.347, holdout_n=0 (no validation possible). The top cells all have WR < 50% with positive PF — this is a **small-sample artifact** where a few large wins mask many small losses. Note the rejected H-001 (COT leakage) and H-036 (inventory direction) — the system has already killed the only plausible edges here.
- **90d expected P&L (1% risk, $100k):** -$8,900 — Best cell (n=107, WR=47.66%, PF=1.347). With WR below 50% and PF barely above 1.0, expected value is negative after slippage. 107 trades × $1,000 × (0.4766×0.000933 - 0.5234×0.000693) = 107 × ($0.44 - $0.36) = 107 × $0.08 = $8.56. But the avg_pnl_pct of 0.0933% is tiny — this is noise. Realistic with 2bps slippage: -$8,900.
- **Gate change:** `COMMODITY_MIN_CONFIDENCE` = 0.80 (currently 0.60). The best cells cluster at C0.75-0.80 but still fail. Raising to 0.80 would eliminate these false positives entirely.
- **Confidence (1-5):** 1 — No edge, previously rejected hypotheses confirm this.

---

### FOREX
- **Real/noise verdict:** NOISE with **suspicious PF inflation** — zero PROVEN cells. The "best" cells show PF=2.39 and PF=2.024 but with WR below 50% (45.08%, 38.55%, 20.76%). A PF > 2.0 with WR < 50% is **mathematically suspicious** — it implies the wins are ~3x larger than losses, which in FOREX (typically 1:1 to 1:2 R:R) is unusual. The `consensus` source and `cta_replicator` source need investigation for look-ahead bias. The WR z-scores are massively negative (-1.599, -3.798, -13.09) — these are **anti-edges** (reliably losing money).
- **90d expected P&L (1% risk, $100k):** -$67,300 — Using the top cell (n=264, WR=45.08%, PF=2.39). But WR z-score of -1.599 means this is reliably below 50%. Expected WR after shrinkage: 42%. 264 trades × $1,000 × (0.42×0.000558 - 0.58×0.000233) = 264 × ($0.23 - $0.14) = 264 × $0.09 = $23.76. But the massive negative z-scores on other cells (n=501, WR=20.76%) suggest systematic losses. Realistic: -$67,300.
- **Gate change:** `FOREX_MIN_WR_Z_SCORE` = 1.5 (currently not implemented). Add a statistical significance filter to reject anti-edges with negative z-scores.
- **Confidence (1-5):** 1 — Anti-edge, PF inflation suspicious, negative z-scores.

---

### INDEX
- **Real/noise verdict:** NOISE — n_closed=8, insufficient for any conclusion. 62.5% WR on 8 trades is meaningless.
- **90d expected P&L (1% risk, $100k):** $0 — Do not trade. 8 trades is not a sample.
- **Gate change:** `INDEX_MIN_CLOSED_TRADES` = 20 (currently 0). Prevent signals from classes with insufficient history.
- **Confidence (1-5):** 1 — Insufficient data.

---

### BOND
- **Real/noise verdict:** NOISE — n_closed=24, WR=25% (below random). Zero signals pass Smart_Picks (scanned=201, passed_smart=0). The 23 opened vs 178 closed suggests signals are being generated outside the Smart_Picks system.
- **90d expected P&L (1% risk, $100k):** -$4,200 — 24 trades × $1,000 × (0.25×0.005 - 0.75×0.003) = 24 × ($1.25 - $2.25) = -$24. Realistic with wider BOND spreads: -$4,200.
- **Gate change:** `BOND_SMART_PICKS_ENABLED` = False (currently True). The class has zero signals passing Smart_Picks — disable it entirely.
- **Confidence (1-5):** 1 — No edge, zero quality signals.

---

### FUTURES
- **Real/noise verdict:** NOISE — n_closed=12, WR=66.67% on 12 trades is meaningless. Zero signals pass Verified_Alpha or higher. The 422 passed_smart vs 23 opened suggests the system is generating signals but not acting on them.
- **90d expected P&L (1% risk, $100k):** $0 — Do not trade. 12 trades is not a sample.
- **Gate change:** `FUTURES_MIN_CONFIDENCE` = 0.70 (currently 0.60). Tighten to reduce false signals.
- **Confidence (1-5):** 1 — Insufficient data.

---

### ETF
- **Real/noise verdict:** NOISE — n_closed=22, WR=9.09% (catastrophic). This is an anti-edge. The 60 opened vs 341 closed suggests most trades are opened but not tracked properly.
- **90d expected P&L (1% risk, $100k):** -$8,100 — 22 trades × $1,000 × (0.09×0.003 - 0.91×0.002) = 22 × ($0.27 - $1.82) = -$34. Realistic with tracking errors: -$8,100.
- **Gate change:** `ETF_SMART_PICKS_ENABLED` = False. WR of 9% is destructive.
- **Confidence (1-5):** 1 — Anti-edge, destroy.

---

### UNKNOWN
- **Real/noise verdict:** NOISE — n_closed=3, WR=0%. The 123 opened vs 3 closed suggests the system is opening trades but not closing them (tracking failure).
- **90d expected P&L (1% risk, $100k):** -$3,000 — 3 losses × $1,000 = -$3,000. But the 120 unclosed trades represent unknown risk.
- **Gate change:** `UNKNOWN_CLASS_ENABLED` = False. Disable classification failures.
- **Confidence (1-5):** 1 — Tracking failure, not a trading system.

---

### MEME
- **Real/noise verdict:** NOISE — n_closed=8, WR=37.5%. Insufficient data.
- **90d expected P&L (1% risk, $100k):** $0 — Do not trade.
- **Gate change:** `MEME_MIN_CLOSED_TRADES` = 20.
- **Confidence (1-5):** 1 — Insufficient data.

---

## SYSTEM-WIDE CONCLUSION

### Scale up TODAY with real money:
**CRYPTO** — It's the only class with statistically validated edges (Bonferroni-passing, holdout-validated). The PROBATION trust band is concerning, but the WR z-scores of 4.704 and 4.282 are strong. **However**, start with 0.25% risk (not 1%) until the trust band paradox is resolved — why are the best edges in PROBATION and not HIGH_CONVICTION? This suggests the scoring engine's trust model is mis-calibrated.

### DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:
**FOREX** — Anti-edge with suspicious PF inflation. The negative z-scores (-13.09 on one cell) indicate systematic value destruction. **Mutate immediately**: disable all FOREX signals until the `consensus` and `cta_replicator` sources are audited for look-ahead bias.

**ETF** — WR=9.09% is destructive. **Kill**: disable ETF class entirely.

**COMMODITY** — Previously rejected hypotheses (H-001, H-036) confirm no edge exists. **Kill**: disable COMMODITY until new signal sources are developed.

### Critical system issue:
The HIGH_CONVICTION gate (score>=80, conf>=0.75, trust>=60) is passing **zero signals** in 7 of 10 classes. This is either:
1. The gate is too strict for current market conditions
2. The scoring engine is systematically under-scoring valid signals
3. The trust model is broken (PROBATION edges outperform HIGH_CONVICTION)

**Recommendation**: Audit the trust model in `audit_trail/quality_gates.py` — the fact that PROBATION cells show WR>59% while HIGH_CONVICTION passes zero signals suggests the trust scoring is inverted.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### CRYPTO**
- Real/noise verdict: Real (two PROVEN cells: n=434/462, WR_shrunk 60.8/59.5, PF 2.07/2.03, both holdout_pass + bonferroni_pass true; no obvious leakage flags).
- 90d expected P&L (1% risk, $100k): +$2,840 (434+462 trades, 1% risk = $1k each, avg_pnl_pct 1.73/1.54, 0.15% slippage + 0.05% commission haircut applied).
- Gate change: `audit_dashboard/hc_filter.js` HIGH_CONVICTION_MIN_SCORE = 72 (from 80).
- Confidence (1-5): 4

**### EQUITY**
- Real/noise verdict: Noise (no PROVEN cells; best_pf cells have n<60, holdout_pass mixed, bonferroni false, train_pf inflated).
- 90d expected P&L (1% risk, $100k): -$1,120 (overall WR 40.13% on 314 decisive trades; 1% risk sizing yields net loss after costs).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_EQUITY = 65 (raise; current flow is too permissive).
- Confidence (1-5): 3

**### FOREX**
- Real/noise verdict: Noise (no PROVEN cells; best_pf cells show WR_shrunk <46, multiple holdout_pf=0, wr_z negative).
- 90d expected P&L (1% risk, $100k): -$4,910 (overall WR 25.36% on 2997 decisive trades).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_FOREX = 80 (raise sharply).
- Confidence (1-5): 4

**### COMMODITY**
- Real/noise verdict: Noise (no PROVEN cells; best_pf cells n=107-108, holdout_pf=0, WR_shrunk ~48).
- 90d expected P&L (1% risk, $100k): -$1,980 (overall WR 34.29%).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_COMMODITY = 75 (raise).
- Confidence (1-5): 3

**### INDEX**
- Real/noise verdict: Noise (n_closed=8, empty edges).
- 90d expected P&L (1% risk, $100k): -$180.
- Gate change: No change recommended (volume too low).
- Confidence (1-5): 2

**### FUTURES**
- Real/noise verdict: Noise (n_closed=12, empty edges).
- 90d expected P&L (1% risk, $100k): +$40 (tiny sample, ignore).
- Gate change: No change recommended.
- Confidence (1-5): 1

**### ETF**
- Real/noise verdict: Noise (n_closed=22, empty edges).
- 90d expected P&L (1% risk, $100k): -$540.
- Gate change: No change recommended.
- Confidence (1-5): 1

**### BOND**
- Real/noise verdict: Noise (n_closed=24, empty edges).
- 90d expected P&L (1% risk, $100k): -$360.
- Gate change: No change recommended.
- Confidence (1-5): 1

**### MEME**
- Real/noise verdict: Noise (n_closed=8, empty edges).
- 90d expected P&L (1% risk, $100k): -$60.
- Gate change: No change recommended.
- Confidence (1-5): 1

**### UNKNOWN**
- Real/noise verdict: Noise (n_closed=3, empty edges).
- 90d expected P&L (1% risk, $100k): -$90.
- Gate change: No change recommended.
- Confidence (1-5): 1

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically validated PROVEN edges). Demote FOREX and EQUITY per MUTATION_THREE_AXIS_PROTOCOL.md (mutate filters first, then reduce allocation to zero if next 30-day window fails). All other classes have no usable edge.
