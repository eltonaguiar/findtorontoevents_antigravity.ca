# Pick Funnel Swarm Verdict — 2026-08-10 04:32 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260810T043237Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

**NOTE:** All calculations assume a flat‑$100 k “notional” account, 1 % risk per trade (≈ $1 k at risk), and that the profit‑factor (PF) is expressed in units of risk‑per‑trade (i.e. PF = average‑win / average‑loss).  Expected profit per trade is therefore  

\[
E[\$] = \bigl(\text{Win Rate}\times\text{PF} - (1-\text{Win Rate})\bigr)\times\$1{,}000
\]

and is multiplied by the number of closed trades that belong to the edge‑cell.  Slippage and transaction costs are ignored (they are small relative to the huge PFs we see).

---

### CRYPTO
- **Real/noise verdict:** **Real edge** – three “PROVEN” cells each have n ≥ 235, WR ≈ 66 % (shrunken), PF ≈ 2.1‑2.5, and both hold‑out and Bonferroni tests pass.  No obvious single‑symbol concentration (the cells are defined by direction = LONG, score‑decile = S50 and source = alpha_engine), so leakage is unlikely.
- **90d expected P&L (1 % risk, $100 k):**  
  - rr = RR1.5‑2.0 & dir = LONG & score_dec = S50 → $313 k  
  - dir = LONG & score_dec = S50 & source = alpha_engine → $384 k  
  - conf = C0.75‑0.80 & dir = LONG & source = alpha_engine → $293 k  
  **Total ≈ $990 k** over the 90‑day window (≈ $3.3 k per day).
- **Gate change:** **Lower the HC confidence threshold** – change `HC_CONF_MIN_CRYPTO` in `audit_dashboard/hc_filter.js` from **0.75** to **0.70**.  This admits the proven cells that sit just below the current cut‑off while still keeping the high‑conviction filter.
- **Confidence (1‑5):** **4** – strong statistical backing, but the edge is confined to LONG‑only, mid‑score deciles.

---

### FOREX
- **Real/noise verdict:** **Real edge** – two “PROVEN” cells (n = 113, 121) with WR ≈ 65‑68 % and PF ≈ 2.9‑3.0 pass hold‑out and Bonferroni.  The “best‑PF” cells that show PF > 5 fail hold‑out (zero out‑of‑sample trades) and are pure noise.
- **90d expected P&L (1 % risk, $100 k):**  
  - trust = UNK & conf = C0.75‑0.80 & rr = RR1.0‑1.5 & fam = mean_reversion → $183 k  
  - trust = UNK & conf = C0.75‑0.80 & rr = RR1.0‑1.5 → $186 k  
  **Total ≈ $369 k** (≈ $4.1 k per day).
- **Gate change:** **Relax the confidence floor** – set `HC_CONF_MIN_FOREX` from **0.75** to **0.70** (same file).  This captures the proven cells without opening the door to the noisy high‑PF, low‑confidence groups.
- **Confidence (1‑5):** **4** – robust out‑of‑sample performance, but only a handful of cells; widening the confidence band yields the biggest upside.

---

### EQUITY
- **Real/noise verdict:** **Highly suspicious – likely leakage / concentration**.  The three “PROVEN” cells have WR ≈ 98 % (shrunken ≈ 87 %) and an astronomic PF ≈ 175.5 on only **n = 65** closed trades (train = 16, hold‑out = 49).  Such PFs are rarely sustainable and usually indicate a single‑ticker or data‑leakage effect (e.g., a hidden “look‑ahead” flag in the `trust=UNK` band).  The fact that the confidence band is **C < 0.60** (very low) further suggests the model is over‑fitting to a tiny, high‑signal slice.
- **90d expected P&L (1 % risk, $100 k):**  
  Using the same PF‑based formula gives an absurd **≈ $9.9 M** (≈ $110 k per day).  Because the edge is almost certainly spurious, we treat the expected P&L as **$0** for practical purposes.
- **Gate change:** **Raise the minimum confidence for equity** – change `HC_CONF_MIN_EQUITY` from **0.60** to **0.80** (or simply disable the `conf<C0.60` band).  This will filter out the ultra‑low‑confidence slice that is currently generating the implausible edge.
- **Confidence (1‑5):** **1** – the statistical signal fails sanity checks; we consider it noise.

---

### COMMODITY
- **Real/noise verdict:** **No proven edge** – there are no cells meeting the “PROVEN” criteria (n ≥ 20, WR ≥ 55 %, PF ≥ 1.5).  The best PF cell fails hold‑out (PF = 6.1 but only 6 training trades, hold‑out PF = 2.5, Bonferroni fail).  This aligns with the earlier rejected hypothesis H‑001.
- **90d expected P&L (1 % risk, $100 k):** **$0** – no statistically valid edge.
- **Gate change:** **Tighten the risk‑reward gate** – increase `SMART_PICKS_MIN_RR_COMMODITY` from its current floor (≈ RR1.5) to **RR2.0**.  This will prune the noisy low‑RR picks and may surface a cleaner high‑RR subset for future testing.
- **Confidence (1‑5):** **2** – modest tightening may help, but no edge exists now.

---

### INDEX
- **Real/noise verdict:** **No edge** – zero “PROVEN” cells, and only 10 closed trades total.
- **90d expected P&L:** **$0**
- **Gate change:** **None needed** – the class is too thin to benefit from any gate tweak.
- **Confidence:** **1**

---

### FUTURES
- **Real/noise verdict:** **No edge** – no “PROVEN” cells; best PF cells fail hold‑out (PF ≈ 1.5, negative Z‑scores).  This mirrors the previously killed hypothesis H‑005.
- **90d expected P&L:** **$0**
- **Gate change:** **Raise the minimum win‑rate** – set `SMART_PICKS_MIN_WR_FUTURES` from the default (≈ 0.45) to **0.55** to force only higher‑quality picks into the funnel.
- **Confidence:** **2**

---

### ETF
- **Real/noise verdict:** **No edge** – only one cell with n = 21, PF ≈ 0.02, WR ≈ 9 %; fails all statistical tests.
- **90d expected P&L:** **$0**
- **Gate change:** **Increase the minimum PF** – change `SMART_PICKS_MIN_PF_ETF` from **0.5** to **1.0** to discard the current loss‑making slice.
- **Confidence:** **1**

---

### BOND
- **Real/noise verdict:** **No edge** – no “PROVEN” cells; best PF cells have PF < 1 and fail hold‑out.
- **90d expected P&L:** **$0**
- **Gate change:** **Raise the confidence floor** – set `HC_CONF_MIN_BOND` from **0.60** to **0.75** to eliminate the low‑confidence, low‑PF picks.
- **Confidence:** **1**

---

### UNKNOWN
- **Real/noise verdict:** **No edge** – only 10 closed trades, 0 % win‑rate.
- **90d expected P&L:** **$0**
- **Gate change:** **Disable the UNKNOWN class** in `audit_trail/quality_gates.py` (remove it from the asset‑class map) to avoid polluting the funnel.
- **Confidence:** **1**

---

### MEME
- **Real/noise verdict:** **No edge** – single trade, 100 % win‑rate but n = 1, no statistical power.
- **90d expected P&L:** **$0** (cannot size a strategy on a single observation).
- **Gate change:** **Exclude MEME** from the pipeline (set `SMART_PICKS_ENABLE_MEME = False`).
- **Confidence:** **1**

---

## SYSTEM‑WIDE CONCLUSION
**Scale‑up today:** **FOREX** – it has a clean, statistically validated edge (PF ≈ 3, WR ≈ 66 %) on a decent sample size (≈ 230 trades) and the

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

Looking at this data with brutal honesty, the picture is grim. The funnel shows a catastrophic disconnect between signals and outcomes. Let me break down each class.

### CRYPTO
- Real/noise verdict: **REAL but fragile.** The PROVEN cells (n=235, WR_shrunk=66.27%, PF=2.52) are statistically significant (z=5.414, Bonferroni pass). However, the holdout PF drops from 3.99 to 1.47 — a 63% decay. This is a real edge but heavily regime-dependent. The `trust=UNK` dimension in the top cell is a red flag — it means the edge exists despite unknown trust, not because of it. The `score_dec=S50` suggests the scoring model's 50th percentile is the sweet spot, which is counterintuitive and could indicate the model is calibrated wrong.
- 90d expected P&L (1% risk, $100k): **$2,507** (235 trades × 1% risk × 0.6766 WR × 2.52 PF × $1,000 risk per trade = $2,507 gross, minus ~$500 slippage = ~$2,000 net)
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO = 50` (currently likely higher, but the edge is at S50, not S70+)
- Confidence (1-5): **3** — real but decaying

### COMMODITY
- Real/noise verdict: **NOISE.** Zero PROVEN cells. The best PF (6.114) has n=34, train_n=6, holdout_pass=false, z=1.371. This is textbook overfitting — 6 training trades cannot support a PF of 60. The 25.74% WR on 373 decisive trades is catastrophic. The `rr=RR>=2.0` cell is a mirage created by 6 lucky trades.
- 90d expected P&L (1% risk, $100k): **-$1,860** (373 trades × 1% risk × 0.2574 WR × 0.51 PF × $1,000 = -$1,860)
- Gate change: `SMART_PICKS_MIN_SCORE_COMMODITY = 80` (raise to kill most signals, or kill the class entirely)
- Confidence (1-5): **1** — no edge, actively harmful

### FOREX
- Real/noise verdict: **MIXED — one real cell, rest noise.** The `trust=UNK & conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion` cell (n=113, WR_shrunk=65.41%, PF=3.031) is real — holdout PF=2.672, z=3.857, Bonferroni pass. But the `best_pf_overall` cells are garbage — PF=5.486 with WR=30.67% and z=-3.348 is a negative-WR cell with a high PF because of a few massive winners. That's not an edge, that's a lottery ticket. The `trust=PROBATION` dimension in the best-PF cells is a red flag — probation trust means the model itself doesn't trust these signals.
- 90d expected P&L (1% risk, $100k): **$1,208** (113 trades × 1% risk × 0.6814 WR × 3.031 PF × $1,000 = $2,331 gross, minus ~$1,123 for the noise trades = ~$1,208 net)
- Gate change: `SMART_PICKS_MIN_CONFIDENCE_FOREX = 0.75` (currently likely 0.60, which lets in the garbage)
- Confidence (1-5): **2** — one real cell buried in noise

### FUTURES
- Real/noise verdict: **NOISE.** n=26 total, zero PROVEN cells. The best cell (PF=1.551) has holdout_pass=false and z=-0.625. The `fam=momentum` cell has PF=0.909 — negative edge. This class has too few trades to conclude anything, but what little data exists is negative.
- 90d expected P&L (1% risk, $100k): **-$260** (26 trades × 1% risk × 0.4615 WR × 0.91 PF × $1,000 = -$260)
- Gate change: `SMART_PICKS_MIN_SCORE_FUTURES = 70` (raise to reduce noise)
- Confidence (1-5): **1** — insufficient data, negative trend

### ETF
- Real/noise verdict: **NOISE.** n=25, zero PROVEN cells. The best cell has PF=0.02 — that's not an edge, that's a black hole. WR=12% on 25 trades. This class is actively destroying capital.
- 90d expected P&L (1% risk, $100k): **-$220** (25 trades × 1% risk × 0.12 WR × 0.02 PF × $1,000 = -$220)
- Gate change: `SMART_PICKS_MIN_SCORE_ETF = 90` (or kill the class)
- Confidence (1-5): **1** — no edge, actively harmful

### EQUITY
- Real/noise verdict: **SUSPICIOUSLY REAL — likely leakage.** The `trust=UNK & conf=C<0.60 & fam=mean_reversion` cell (n=65, WR_shrunk=87.06%, PF=175.514) is statistically impossible. PF=175 means you're making $175 for every $1 risked. The holdout PF=140.85 confirms it's not just in-sample. But WR=98.46% with n=65 and train_n=16? This smells like look-ahead bias or single-symbol concentration. The `conf=C<0.60` dimension is the smoking gun — the edge exists at LOW confidence, which means the model is systematically mispricing risk. This is either a data leak or a single stock that moved 100% in one day.
- 90d expected P&L (1% risk, $100k): **$11,400** (65 trades × 1% risk × 0.9846 WR × 175.514 PF × $1,000 = $11,400 — but this is fantasy if leakage)
- Gate change: `SMART_PICKS_MIN_CONFIDENCE_EQUITY = 0.60` (raise to kill the low-confidence leak)
- Confidence (1-5): **1** — this is not a real edge, it's a bug

### UNKNOWN
- Real/noise verdict: **NOISE.** n=10, 0% WR, zero PROVEN cells. This class is a catch-all for misclassified assets and should be killed.
- 90d expected P&L (1% risk, $100k): **-$100** (10 trades × 1% risk × 0% WR × 0 PF × $1,000 = -$100)
- Gate change: `SMART_PICKS_MIN_SCORE_UNKNOWN = 100` (kill the class)
- Confidence (1-5): **1** — no edge

### BOND
- Real/noise verdict: **NOISE.** n=35, zero PROVEN cells. WR=14.29%, best PF=0.47. The `source=bond_scanner` cells are all negative. This class is a capital incinerator.
- 90d expected P&L (1% risk, $100k): **-$350** (35 trades × 1% risk × 0.1429 WR × 0.47 PF × $1,000 = -$350)
- Gate change: `SMART_PICKS_MIN_SCORE_BOND = 90` (or kill)
- Confidence (1-5): **1** — no edge, actively harmful

### MEME
- Real/noise verdict: **NOISE.** n=1. Cannot conclude anything. The 100% WR is meaningless.
- 90d expected P&L (1% risk, $100k): **$0** (insufficient data)
- Gate change: `SMART_PICKS_MIN_SCORE_MEME = 80` (raise to reduce noise)
- Confidence (1-5): **1** — insufficient data

### INDEX
- Real/noise verdict: **NOISE.** n=10, zero PROVEN cells. WR=30%. The `best_pf_overall` is empty — no cell even meets the n>=20 threshold.
- 90d expected P&L (1% risk, $100k): **-$100** (10 trades × 1% risk × 0.30 WR × 0.5 PF × $1,000 = -$100)
- Gate change: `SMART_PICKS_MIN_SCORE_INDEX = 80` (raise to reduce noise)
- Confidence (1-5): **1** — no edge

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY:** CRYPTO — but only the `rr=RR1.5-2.0 & dir=LONG & score_dec=S50` cell. This is the only cell with statistical significance, holdout validation, and a reasonable PF (2.52). Even then, the decay from train to holdout (3.99 → 1.47) means you should size at half the Kelly criterion.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:** 
1. **EQUITY** — the PF=175.514 cell is a leakage red flag. Per the protocol, this should be mutated (investigate the data source) before killing. The `conf=C<0.60` dimension is the smoking gun.
2. **COMMODITY** — kill. The COT_positioning hypothesis was already rejected (H-001), and this data confirms no edge exists. The 25.74% WR is worse than random.
3. **ETF** — kill. PF=0.02 is not an edge, it's a bug.
4. **BOND** — kill. 14.29% WR with negative PF across all cells.
5. **FOREX** — mutate. The one real cell (`mean_reversion` at conf 0.75-0.80) is worth keeping, but the `trust=PROBATION` cells are noise. Raise the confidence floor to 0.75 and see if the edge survives.

**The elephant in the room:** The `opened` numbers are 2-3x the `passed_smart` numbers for every class. You're opening trades that never passed the smart filter. That's not a funnel problem, that's a discipline problem. Fix the execution layer before touching any gates.

**Sizing assumptions:** 1% risk per trade, $100k notional, $10 slippage per trade (0.01% on $100k), no compounding. The P&L figures above are gross estimates — real results will be worse due to spread, funding, and partial fills.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real edge on the three listed cells (n=235–393, WR_shrunk 62–66%, PF 2.16–2.52, all holdout_pass + bonferroni_pass). No obvious leakage flags in the provided cells.
- 90d expected P&L (1% risk, $100k): $2,850 (assumes ~300 trades at 1% risk, avg 0.95% edge after 0.15% slippage/commissions).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 50
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: Marginal real edge on the two mean_reversion cells (n=113–121, WR_shrunk ~65%, PF 2.89–3.03, holdout_pass). Other cells are noise or failed holdout.
- 90d expected P&L (1% risk, $100k): $680 (assumes ~110 trades at 1% risk, avg 0.62% edge after slippage).
- Gate change: HC_FILTER_MIN_CONF = 0.75
- Confidence (1-5): 3

### EQUITY
- Real/noise verdict: Likely sample-noise / single-symbol concentration (n=65 but train_n=16, PF=175 is unrealistic and screams leakage or one dominant ticker).
- 90d expected P&L (1% risk, $100k): -$420 (edge collapses out-of-sample).
- Gate change: QUALITY_GATES_MIN_TRUST_EQUITY = 70
- Confidence (1-5): 2

### COMMODITY
- Real/noise verdict: No proven edges; all best_pf_overall cells fail holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 65
- Confidence (1-5): 1

### FUTURES
- Real/noise verdict: No proven edges; all cells fail holdout.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: QUALITY_GATES_MIN_N_CLOSED = 50
- Confidence (1-5): 1

### ETF
- Real/noise verdict: No proven edges; all cells fail holdout with negative expectancy.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: HC_FILTER_MIN_SCORE = 80
- Confidence (1-5): 1

### INDEX
- Real/noise verdict: No proven edges (n_closed=10 total).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: QUALITY_GATES_MIN_N_CLOSED = 50
- Confidence (1-5): 1

### BOND
- Real/noise verdict: No proven edges; all cells fail holdout with negative expectancy.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 60
- Confidence (1-5): 1

### UNKNOWN / MEME
- Real/noise verdict: No proven edges (n_closed ≤10).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: QUALITY_GATES_MIN_N_CLOSED = 50
- Confidence (1-5): 1

**SYSTEM-WIDE CONCLUSION**  
Scale up TODAY: CRYPTO (only class with multiple holdout-validated cells).  
Demote per MUTATION_THREE_AXIS_PROTOCOL: EQUITY (high risk of leakage/concentration; mutate filters before any further allocation). All other classes have zero deployable edge.
