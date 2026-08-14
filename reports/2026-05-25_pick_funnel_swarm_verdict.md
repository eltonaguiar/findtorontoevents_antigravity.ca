# Pick Funnel Swarm Verdict — 2026-08-14 04:35 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260814T043459Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO  
- **Real/noise verdict:** **Real edge** – 232 closed trades, WR ≈ 77 % (shrunk ≈ 77 %), PF ≈ 4.1, hold‑out pass = true, Bonferroni = true.  The cell uses only the confidence band (0.75‑0.80) and score‑decile S50; no “trust” filter is applied, so there is no obvious leakage or look‑ahead.  The PF is high but consistent across three almost‑identical cells, and the hold‑out sample (≈ 130 trades) still delivers a PF ≈ 2.9, which argues the signal is not pure sample‑noise.  

- **90d expected P&L (1 % risk, $100 k):**  
  *Base calculation*: E[net/$risk] = WR × PF − (1‑WR) ≈ 0.77 × 4.14 − 0.23 ≈ 2.96 $ per $1 risk.  
  *Assumptions*: 10 % PF degradation & 5 % win‑rate hit from slippage/transaction cost. Adjusted PF ≈ 3.73, WR ≈ 0.73 → E[net/$risk] ≈ 2.46.  
  *Result*: $2,460 profit per $1 k risk → **$2,460 × 232 ≈ $569 k** over the 90‑day window.  

- **Gate change:** lower the score‑decile threshold for crypto picks.  
  ```python
  # audit_trail/quality_gates.py
  SMART_PICKS_MIN_SCORE_CRYPTO = 50   # current 80 → allow S50 cells that proved profitable
  ```  

- **Confidence (1‑5):** **4** – strong statistical backing, but still a single‑cell concentration (all trades in the same confidence band), so keep a modest confidence rating.  

---

### EQUITY  
- **Real/noise verdict:** **Likely noise / over‑fit** – 67 closed trades, WR ≈ 99 % (shrunk ≈ 87 %), PF ≈ 182.  The PF is astronomically high and driven by a tiny training sample (17 trades).  Although the hold‑out (50 trades) passes, the win‑rate is near‑perfect, which is a classic sign of look‑ahead or data‑snooping.  The same cell appears under three different dimension sets, suggesting the model is “gaming” the mean‑reversion family rather than capturing a robust market effect.  Treat this as a statistical fluke.  

- **90d expected P&L (1 % risk, $100 k):**  
  *Base*: E[net/$risk] ≈ 0.985 × 182 − 0.015 ≈ 179 $ per $1 risk → $179 k per trade.  
  *Adjusted for realistic execution*: assume a 30 % PF cut (to ~128) and a 10 % win‑rate reduction (WR ≈ 0.89).  Then E[net/$risk] ≈ 0.89 × 128 − 0.11 ≈ 113 $ per $1 risk → $113 k per trade.  
  *Result*: $113 k × 67 ≈ $7.6 M – clearly implausible for a 90‑day sample; the edge is not trustworthy.  

- **Gate change:** none recommended – the current “high‑conviction” gate already filters out low‑confidence equity picks; the observed edge is almost certainly a data artefact.  

- **Confidence (1‑5):** **2** – statistical significance is dubious; keep the gate as‑is and do not allocate capital.  

---

### FOREX  
- **Real/noise verdict:** **Real edge** – 113 closed trades, WR ≈ 68 % (shrunk ≈ 65 %), PF ≈ 3.0, hold‑out pass = true, Bonferroni = true.  The cell combines confidence 0.75‑0.80, RR 1.0‑1.5 and a mean‑reversion family – a sensible risk‑reward profile that survives out‑of‑sample testing.  No single‑symbol concentration is evident (forex pairs are diversified).  

- **90d expected P&L (1 % risk, $100 k):**  
  *Base*: E[net/$risk] ≈ 0.68 × 3.03 − 0.32 ≈ 1.75 $ per $1 risk → $1,750 per trade.  
  *Assumptions*: 10 % PF drop & 5 % win‑rate hit → PF ≈ 2.73, WR ≈ 0.65 → E[net/$risk] ≈ 1.41 → $1,410 per trade.  
  *Result*: $1,410 × 113 ≈ $159 k** over the 90‑day period.  

- **Gate change:** relax the trust‑level filter for forex picks (the proven cell uses “trust=UNK”).  
  ```javascript
  // audit_dashboard/hc_filter.js
  const HC_TRUST_MIN = 0;   // current 60 → allow UNK‑trust picks that have shown real edge
  ```  

- **Confidence (1‑5):** **3** – solid statistical evidence, but the edge lives in a relatively narrow confidence band; a modest confidence rating is appropriate.  

---

### COMMODITY  
- **Real/noise verdict:** **No edge** – no PROVEN cells; best PF cell fails hold‑out (PF ≈ 6.1, WR ≈ 62 % but hold‑out PF = 2.5, fail).  The sample is small (n = 34) and the win‑rate is modest.  

- **90d expected P&L (1 % risk, $100 k):** **$0** – no statistically validated edge to size.  

- **Gate change:** none – tightening the RR or confidence thresholds would only reduce noise further, but there is no profitable signal to amplify.  

- **Confidence (1‑5):** **1**.  

---

### FUTURES  
- **Real/noise verdict:** **No edge** – top PF cells fail hold‑out (PF ≈ 1.6, win‑rate ≈ 46 %, hold‑out PF ≈ 0.2).  Sample size tiny (n ≈ 24).  

- **90d expected P&L:** **$0**.  

- **Gate change:** none.  

- **Confidence:** **1**.  

---

### ETF  
- **Real/noise verdict:** **No edge** – only one cell, PF ≈ 0.02, win‑rate ≈ 9 %, hold‑out fails.  

- **90d expected P&L:** **$0**.  

- **Gate change:** none.  

- **Confidence:** **1**.  

---

### BOND  
- **Real/noise verdict:** **No edge** – best PF ≈ 0.47, win‑rate ≈ 13 %, hold‑out fails.  

- **90d expected P&L:** **$0**.  

- **Gate change:** none.  

- **Confidence:** **1**.  

---

### INDEX, MEME, UNKNOWN, ETF (other classes)  
- **Real/noise verdict:** **No edge** – either zero or single‑digit closed trades, no PROVEN cells, and all hold‑out tests fail.  

- **90d expected P&L:** **$0**.  

- **Gate change:** none.  

- **Confidence:** **1**.  

---

## SYSTEM‑WIDE Conclusion  

**Scale‑up today:** **CRYPTO** – the only class with a statistically robust, hold‑out‑validated edge that survives realistic slippage assumptions and delivers an expected ~ $570 k profit on a $100 k account (≈ 570 % ROI). Adjusting the score‑decile gate to 50 unlocks this edge without compromising quality.

**Secondary candidate:** **FOREX** – a solid edge with ~ $160 k expected profit; lowering the trust filter will admit the proven cell while keeping the confidence band unchanged.

**Demote / de‑prioritize:** **EQUITY** – despite a dazzling PF, the signal is almost certainly a statistical artefact (tiny training sample, near‑perfect win‑rate). Remove or heavily tighten the equity confidence/mean‑reversion gate to prevent leakage. All other asset classes (COMMODITY, FUTURES, ETF, BOND, INDEX, MEME, UNKNOWN) should be **mutated out** per the `MUTATION_THREE_AXIS_PROTOCOL.md` – i.e., set their gate thresholds to the most restrictive values (e.g., `SMART_PICKS_MIN

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT — 90-DAY EDGE ANALYSIS

### COMMODITY
- **Real/noise verdict:** NOISE. Zero PROVEN cells. Best cell (RR>=2.0, n=34) fails holdout (holdout_pf=2.5, holdout_pass=false), fails Bonferroni (wr_z=1.371), and train_n=6 is far too small. The 28.31% WR on 332 decisive trades is below breakeven for typical R:R. This class is actively destroying capital.
- **90d expected P&L (1% risk, $100k):** -$4,120 (2150 closed, 332 decisive, 28.31% WR at avg R:R ~1.2:1 → EV = 0.2831×1.2 - 0.7169×0.8 = -0.237 per trade × 332 × $1,000)
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY = 85` (from current ~70) — kill the noise floor
- **Confidence (1-5):** 5 — this is definitively negative EV

### EQUITY
- **Real/noise verdict:** REAL but SUSPICIOUS. The mean_reversion/S40 cell (n=67, WR=98.51%, PF=181.66) is statistically significant (wr_z=7.941, Bonferroni pass) and holdout-validated (holdout_pf=143.575). BUT: 98.51% WR with PF=181.66 is either (a) a genuine micro-edge with tiny avg_pnl (1.08%) or (b) a data artifact. The train_n=17 vs holdout_n=50 split is concerning — the train set is too small to establish the pattern. This smells like single-symbol concentration or a look-ahead in the mean_reversion family.
- **90d expected P&L (1% risk, $100k):** +$4,550 (422 decisive, 47.87% WR at avg R:R ~1.5:1 → EV = 0.4787×1.5 - 0.5213×0.8 = +0.301 per trade × 422 × $1,000)
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY = 75` (from current ~60) — but add `MIN_TRADES_PER_SYMBOL = 5` to prevent single-symbol concentration
- **Confidence (1-5):** 3 — real signal but need to verify no leakage

### FOREX
- **Real/noise verdict:** REAL but WEAK. The mean_reversion/conf=C0.75-0.80/RR1.0-1.5 cell (n=113, WR=68.14%, PF=3.031) passes holdout (holdout_pf=2.808) and Bonferroni (wr_z=3.857). But the PF=3.031 is modest, and the avg_pnl_pct=0.30% is thin. The broader cell (n=121, WR=67.77%, PF=2.887) is consistent. This is a genuine but low-margin edge. The suspiciously high PF numbers you flagged are NOT in the PROVEN list — the consensus/ml cells you're worried about are not showing up as proven, which is good.
- **90d expected P&L (1% risk, $100k):** +$2,310 (637 decisive, 34.54% WR at avg R:R ~1.8:1 → EV = 0.3454×1.8 - 0.6546×0.8 = +0.098 per trade × 637 × $1,000)
- **Gate change:** `SMART_PICKS_MIN_CONFIDENCE_FOREX = 0.75` (from current ~0.60) — only trade the high-confidence band
- **Confidence (1-5):** 4 — real edge, modest magnitude

### CRYPTO
- **Real/noise verdict:** REAL and STRONG. The conf=C0.75-0.80/LONG/S50 cell (n=232, WR=79.31%, PF=4.139) is the strongest edge in the entire funnel. Holdout-validated (holdout_pf=2.913), Bonferroni-passing (wr_z=8.929), and the train/holdout split (102/130) is healthy. The source=alpha_engine variant (n=225, WR=80.0%, PF=4.124) confirms this is not a data artifact. The suspiciously high PF numbers you flagged (11.109 train, 2.913 holdout) are actually CONSISTENT — the train PF is inflated by small n, but the holdout PF of 2.913 is still excellent. This is the real deal.
- **90d expected P&L (1% risk, $100k):** +$14,390 (2878 decisive, 46.46% WR at avg R:R ~1.6:1 → EV = 0.4646×1.6 - 0.5354×0.8 = +0.315 per trade × 2878 × $1,000)
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO = 80` (from current ~70) — but more importantly, add `HIGH_CONVICTION_MIN_CONFIDENCE_CRYPTO = 0.75` in hc_filter.js to route the proven cell into HC
- **Confidence (1-5):** 5 — this is the strongest, most validated edge in the system

### BOND
- **Real/noise verdict:** NOISE. Zero PROVEN cells. Best cell (n=23, WR=13.04%, PF=0.47) is catastrophically negative. The 14.29% WR on 35 decisive trades is a disaster. This class should be killed, not mutated.
- **90d expected P&L (1% risk, $100k):** -$2,100 (90 closed, 35 decisive, 14.29% WR at avg R:R ~1.5:1 → EV = 0.1429×1.5 - 0.8571×0.8 = -0.471 per trade × 35 × $1,000)
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND = 95` (effectively disable)
- **Confidence (1-5):** 5 — definitively negative EV

### ETF
- **Real/noise verdict:** NOISE. Zero PROVEN cells. Best cell (n=21, WR=9.52%, PF=0.02) is a disaster. The 12.0% WR on 25 decisive trades is below random. This class is broken.
- **90d expected P&L (1% risk, $100k):** -$1,500 (312 closed, 25 decisive, 12.0% WR at avg R:R ~1.5:1 → EV = 0.12×1.5 - 0.88×0.8 = -0.524 per trade × 25 × $1,000)
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF = 95` (effectively disable)
- **Confidence (1-5):** 5 — definitively negative EV

### UNKNOWN
- **Real/noise verdict:** NOISE. Zero PROVEN cells, zero closed trades with any edge. The 0.0% WR on 10 decisive trades is meaningless but directionally terrible. This class is a data-quality problem — UNKNOWN assets should be routed to their proper class or dropped.
- **90d expected P&L (1% risk, $100k):** -$800 (10 closed, 10 decisive, 0.0% WR → EV = -0.8 per trade × 10 × $1,000)
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN = 95` (effectively disable) — or better, fix the asset classification
- **Confidence (1-5):** 4 — small sample but directionally clear

### INDEX
- **Real/noise verdict:** NOISE. Zero PROVEN cells. The 30.0% WR on 10 decisive trades is below breakeven. Sample too small to conclude anything, but directionally negative.
- **90d expected P&L (1% risk, $100k):** -$200 (239 closed, 10 decisive, 30.0% WR at avg R:R ~1.5:1 → EV = 0.30×1.5 - 0.70×0.8 = -0.11 per trade × 10 × $1,000)
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX = 85` (tighten)
- **Confidence (1-5):** 3 — small sample, directionally negative

### MEME
- **Real/noise verdict:** NOISE. Only 2 closed trades, zero PROVEN cells. The 50.0% WR on 2 trades is meaningless. This class is too small to evaluate.
- **90d expected P&L (1% risk, $100k):** $0 (2 decisive, 50.0% WR → EV ≈ 0)
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME = 90` (effectively disable until volume justifies)
- **Confidence (1-5):** 2 — insufficient data

### FUTURES
- **Real/noise verdict:** NOISE. Zero PROVEN cells. Best cell (n=24, WR=45.83%, PF=1.558) fails holdout (holdout_pf=0.194) and has negative wr_z (-0.409). The 48.15% WR on 27 decisive trades is below breakeven for typical R:R. This class is not ready.
- **90d expected P&L (1% risk, $100k):** -$100 (60 closed, 27 decisive, 48.15% WR at avg R:R ~1.2:1 → EV = 0.4815×1.2 - 0.5185×0.8 = -0.007 per trade × 27 × $1,000)
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES = 85` (tighten)
- **Confidence (1-5):** 3 — small sample, marginal negative

---

## SYSTEM-WIDE CONCLUSION

### SCALE UP TODAY: **CRYPTO**
The conf=C0.75-0.80/LONG/S50 cell is the single strongest, most validated edge in the entire system:
- n=232, WR=79.31%, PF=4.139
- Holdout-validated (holdout_pf=2.913, holdout_pass=true)
- Bonferroni-passing (wr_z=8.929)
- Healthy train/holdout split (102/130)
- Consistent across source=alpha_engine variant

**Action:** Route all CRYPTO signals meeting conf>=0.75, dir=LONG, score_dec=S50 into HIGH CONVICTION. Set `HIGH_CONVICTION_MIN_CONFIDENCE_CRYPTO = 0.75` in hc_filter.js. This should lift HC pass-through from 0 to ~200+ signals/90d.

### DEMOTE (MUTATE BEFORE KILL): **BOND, ETF, UNKNOWN**
Per MUTATION_THREE_AXIS_PROTOCOL, these classes are not just underperforming — they are actively destroying capital:
- **BOND:** 14.29% WR, PF=0.47 best cell, all cells fail validation
- **ETF:** 12.0% WR, PF=0.02 best cell, all cells fail validation
- **UNKNOWN:** 0.0% WR, data-quality problem

**Mutation path:** Before killing, try:
1. **BOND:** Restrict to `source=bond_scanner` AND `rr=RR>=2.0` only, with `MIN_CONFIDENCE=0.80`. If WR doesn't exceed 40% in next 30d, kill.
2. **ETF:** Restrict to `fam=mean_reversion` only, with `MIN_SCORE=80`. If WR doesn't exceed 45% in next 30d, kill.
3. **UNKNOWN:** Fix asset classification first. If UNKNOWN persists >5% of scans, kill the class entirely.

### WATCHLIST (MUTATE, DON'T KILL YET):
- **EQUITY:** The mean_reversion/S40 cell is promising but needs verification. Add `MIN_TRADES_PER_SYMBOL=5` to prevent concentration risk. If the 98.51% WR drops below 70% in next 30d, investigate for leakage.
- **FOREX:** The mean_reversion/conf=C0.75-0.80 cell is real but thin. Consider raising `SMART_PICKS_MIN_CONFIDENCE_FOREX` to 0.75 to focus on the proven band.
- **FUTURES:** Too small to evaluate. Keep at current gates, revisit in 90d.

### CRITICAL WARNING:
The EQUITY mean_reversion cell (WR=98.51%, PF=181.66) is statistically significant but physically implausible. A PF of 181.66 means you're making $181 for every $1 lost — this is either a once-in-a-decade anomaly or a data artifact. The train_n=17 is too small to establish this pattern. **Do NOT scale EQUITY until this is verified with fresh data.** The CRYPTO edge (PF=4.139) is much more believable and should be the primary focus.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Likely sample-noise/leakage (PF>4 on n=232 with holdout_pass but extreme train/holdout gap and user-flagged ml cells; violates stability seen in rejected H-035).
- 90d expected P&L (1% risk, $100k): -$420 (negative after 0.15% slippage + 0.08% spread on 2878 closed trades).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 72
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Noise (98.51% WR / PF=181 on n=67 is impossible without single-symbol concentration or look-ahead; matches pattern of killed hypotheses).
- 90d expected P&L (1% risk, $100k): -$680 (realized loss trajectory on 422 decisive trades).
- Gate change: HC_MIN_TRUST = 75
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise (PF~3 on n=113-121 fails bonferroni in best_pf list; consensus cells flagged as suspiciously high).
- 90d expected P&L (1% risk, $100k): -$310
- Gate change: HC_MIN_CONF = 0.82
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: Noise (no proven cells; best_pf failed holdout + bonferroni; matches rejected H-001/H-036 patterns).
- 90d expected P&L (1% risk, $100k): -$890
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 65
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise (no proven cells; all best_pf negative PF and failed holdout).
- 90d expected P&L (1% risk, $100k): -$410
- Gate change: HC_MIN_SCORE = 85
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise (no proven cells; best_pf PF=0.02 with catastrophic WR).
- 90d expected P&L (1% risk, $100k): -$520
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 70
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise (no proven cells; best_pf failed holdout + negative WR_z).
- 90d expected P&L (1% risk, $100k): -$180
- Gate change: HC_MIN_TRUST = 70
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise (n=10 decisive; no edges).
- 90d expected P&L (1% risk, $100k): -$95
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise (n=2 decisive; no edges).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 90
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise (n=10 decisive; no edges).
- 90d expected P&L (1% risk, $100k): -$40
- Gate change: HC_MIN_SCORE = 85
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up TODAY: none (zero classes show stable, leakage-free edge after scrutiny).  
Demote per MUTATION_THREE_AXIS_PROTOCOL.md: EQUITY and CRYPTO first (highest leakage risk), followed by FOREX and COMMODITY. All others already at noise floor.
