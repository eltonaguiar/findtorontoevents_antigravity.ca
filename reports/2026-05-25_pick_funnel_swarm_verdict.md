# Pick Funnel Swarm Verdict — 2026-10-01 04:11 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261001T041134Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

Before the per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) has never fired in 90 days. The dashboard's "HIGH CONVICTION" tab is empty. That is itself the single biggest finding.
2. **`passed_verified_alpha` is 0 for INDEX, FOREX, COMMODITY, EQUITY, BOND, ETF, UNKNOWN** — only CRYPTO (1793) and a trickle of FOREX/FUTURES/MEME pass. The verified-alpha gate is effectively a CRYPTO-only gate.
3. **`opened` ≈ `scanned` in every class** (e.g. INDEX 1740/1748, FOREX 21412/22733, UNKNOWN 1384/1391). The funnel is not filtering — it is a pass-through. `passed_smart` is also ~90%+ of scanned in most classes. The "Smart per-class floor map" is not doing work.

Any "edge" claim has to survive those three facts. Most don't.

---

### INDEX
- **Real/noise verdict:** **Noise / no edge.** n_closed=5, WR=20%, PF not reported (n<20). `passed_smart`=1542/1748 (88%) but only 8 closed — the class is essentially unmeasured. The 1W/4L sample is statistically meaningless (95% CI on 20% WR with n=5 spans roughly 0.5%–71%). Do not trade this.
- **90d expected P&L (1% risk, $100k):** $0 (do not size; n=5 is below any defensible minimum).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise until `passed_smart/scanned < 0.30`. Current 88% pass rate means the floor is below the noise band. Set to the 70th percentile of the INDEX score distribution (empirically ~+15 pts above current).
- **Confidence (1-5):** 5 (confident there is no edge).

### FOREX
- **Real/noise verdict:** **Noise, and the "best PF" cell is a textbook leakage flag.** The `trust=UNK & fam=regime & dir=LONG` cell shows `train_pf=0.0, train_n=7, holdout_pf=19.705, holdout_n=25`. A train PF of exactly 0.0 with 7 trades means **all 7 train trades lost**, then 25 holdout trades won at 75%. That is not an edge — that is a temporal split that put all the losers on one side. `holdout_pass=false`, `bonferroni_pass=false`. The 43.47% decisive WR on n=490 is below coin-flip and consistent with fees/slippage eating a zero-edge signal. `passed_smart`=21748/22733 = **95.7% pass rate** — the gate is not filtering.
- **90d expected P&L (1% risk, $100k):** **Negative.** At 43.47% WR with typical 1.5R winners and 1R losers, expectancy ≈ 0.4347×1.5 − 0.5653×1.0 = **−0.043R per trade**. Over 490 decisive trades at 1% risk = **−$2,100** before slippage; with 0.5 pip FX slippage on ~21k opens, add roughly **−$3,000 to −$8,000**. Net: **−$5k to −$10k**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise so pass rate drops from 95.7% to ≤40%. Also add a hard `MIN_TRAIN_N=30` requirement before any cell is allowed to influence scoring (the regime cell with train_n=7 should never have been surfaced).
- **Confidence (1-5):** 5 (confident it's noise/negative).

### CRYPTO
- **Real/noise verdict:** **The one cell that looks real — with caveats.** `conf=C0.75-0.80 & dir=LONG & source=alpha_engine`: n=249, WR=65.06%, WR_shrunk=63.94%, PF=2.548, train_pf=2.801 (n=183), holdout_pf=2.108 (n=66), `holdout_pass=true`, `bonferroni_pass=true`, wr_z=4.75. This survives the standard battery. **However:** (i) the cell is defined by `trust=UNK` in two of three variants — meaning the trust dimension is not actually discriminating, it's just "everything is UNK"; (ii) `source=alpha_engine` is the only source, so this is a single-source edge, not a cross-source one; (iii) conf band 0.75–0.80 is narrow — check whether adjacent bands (0.70–0.75, 0.80–0.85) also show edge or whether this is a lucky bin. If adjacent bins are flat, it's a binning artifact. **The `ml` cell you flagged is not in the data provided** — if it exists elsewhere with PF>5, treat it as leakage until proven otherwise (likely target leakage in the ML feature set or a label that includes future bars). The `consensus` cell is also not in the provided data.
- **90d expected P&L (1% risk, $100k):** Using the proven cell only: 249 trades × 1% risk × avg_pnl_pct 1.1161% ≈ **+$2,780 gross** on the cell. But the class as a whole is 45.55% WR on 2406 decisive trades — the proven cell is a small island in a losing sea. If you traded **only** the proven cell: **+$2,500 to +$3,000** after ~0.1% slippage per side on crypto. If you traded the whole class: **negative**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — but the higher-leverage change is in `hc_filter.js`: the HC gate requires `trust>=60`, and **every CRYPTO edge cell is `trust=UNK`**. That means the HC gate structurally cannot fire on the only proven CRYPTO edge. Either (a) fix the trust computation so `alpha_engine` picks get a real trust score, or (b) lower `HC_TRUST_MIN` from 60 to 0 for `source=alpha_engine` and compensate with a stricter score floor. I'd do (a) — the trust field is broken, not the threshold.
- **Confidence (1-5):** 3 (the cell is real-ish; the class is not).

### COMMODITY
- **Real/noise verdict:** **Noise.** Best cell `trust=UNK & rr=RR1.5-2.0 & fam=mean_reversion`: n=20, WR=60%, WR_shrunk=55%, PF=4.601, but `holdout_n=2`, `holdout_pass=false`, `bonferroni_pass=false`, wr_z=0.894. n=20 with 2 holdout trades is not evidence. The `fam=mean_reversion & source=alpha_engine` cell (n=32, PF=3.971) has `holdout_n=5` — same problem. Class WR 48.94% on n=94 is coin-flip. **Also note H-001 and H-036 are both COMMODITY kills** — this class has a documented history of leakage and harness rejection. Treat any COMMODITY "edge" as guilty until proven innocent.
- **90d expected P&L (1% risk, $100k):** **~$0 to slightly negative.** 48.94% WR × 94 trades at 1% risk ≈ −0.01R/trade × 94 = **−$100** before slippage; with commodity slippage, **−$500 to −$1,500**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to cut pass rate from 3342/5873 (57%) to ≤25%. Also add a `MIN_HOLDOUT_N=20` requirement for any cell to be labeled PROVEN (currently 2 and 5 pass).
- **Confidence (1-5):** 5 (confident it's noise).

### EQUITY
- **Real/noise verdict:** **Almost certainly leakage or a data artifact.** `fam=mean_reversion & score_dec=S40`: n=67, WR=98.51%, PF=214.55, train_pf=99.05, holdout_pf=99.0, wr_z=7.94, bonferroni_pass=true. **A PF of 214 is not a trading edge — it is a bug.** Possible causes: (i) `score_dec=S40` is a decile that correlates with a look-ahead feature (e.g. score computed after the fact); (ii) the "loss" definition is wrong for this cell (e.g. trades that hit a tiny stop are being counted as wins because of a sign error); (iii) single-symbol concentration — 67 trades in one decile of one family is plausibly 1–3 tickers. **Do not trade this.** The class-level 68.9% WR on n=164 is also suspiciously high for equity mean-reversion and likely inherits the same artifact. **Flag as potential leakage recurrence** per your instructions.
- **90d expected P&L (1% risk, $100k):** **$0 — do not size.** If the PF=214 were real, 67 trades × 1% × 1.27% avg = **+$850**, but the number is not real.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` is already tight (242/5600 = 4.3% pass). The real fix is upstream: add a **`MAX_CELL_PF=10.0` sanity cap** in the edge-detection code — any cell with PF>10 is auto-flagged as leakage and excluded from PROVEN. This is a code change, not a constant, but it's the one gate change that matters most here.
- **Confidence (1-5):** 5 (confident it's leakage).

### BOND
- **Real/noise verdict:** **Noise.** n=29 closed, best cell n=20 with `holdout_n=11`, `holdout_pass=false`, `bonferroni_pass=false`, wr_z=0.447. 48.28% WR is coin-flip. `passed_smart`=3/535 = 0.6% pass rate — the gate is either correctly rejecting everything or the scoring is broken for bonds. Either way, no edge.
- **90d expected P&L (1% risk, $100k):** **~$0.** 29 trades × 1% × ~0 expectancy = **−$50 to +$50**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — leave as-is (already restrictive) but **investigate why only 3/535 pass**; if the scoring is broken, fix it before tuning the threshold.
- **Confidence (1-5):** 5 (confident it's noise).

### ETF
- **Real/noise verdict:** **Noise.** n_closed=9. WR=22.22%. `best_pf_overall=[]` — no cell even qualifies. `passed_smart`=293/338 = 86.7% pass rate with 9 closes. Unmeasurable.
- **90d expected P&L (1% risk, $100k):** **$0** (n=9).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to cut pass rate from 87% to ≤30%.
- **Confidence (1-5):** 5 (confident it's noise).

### FUTURES
- **Real/noise verdict:** **Noise.** n_closed=18, WR=27.78%, `best_pf_overall=[]`. **H-005 already killed the futures momentum signal** (inversion doesn't fix it). Do not re-derive.
- **90d expected P&L (1% risk, $100k):** **Negative.** 18 trades × 1% × (0.278×1.5 − 0.722×1.0) = 18 × 1% × (−0.305R) = **−$55** before slippage; with futures slippage, **−$200 to −$500**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to cut pass rate from 111/168 (66%) to ≤20%.
- **Confidence (1-5):** 5 (confident it's noise).

### UNKNOWN
- **Real/noise verdict:** **Noise, and a data-quality red flag.** n_closed=7, WR=0%. `passed_smart`=171/1391 = 12.3% pass rate but `opened`=1384/1391 = 99.5% — meaning 1213 picks that failed Smart still got opened. The UNKNOWN bucket is where misclassified instruments go to die. **Fix the classifier before trading anything here.**
- **90d expected P&L (1% risk, $100k):** **$0** (n=7, and 0% WR means don't).
- **Gate change:** Not a threshold — fix the asset-class classifier so UNKNOWN shrinks to near-zero. If forced to name a constant: `SMART_PICKS_MIN_SCORE_UNKNOWN` = 999 (hard-block until classifier is fixed).
- **Confidence (1-5):** 5 (confident it's noise).

### MEME
- **Real/noise verdict:** **Noise.** n_closed=4. Unmeasurable. `passed_verified_alpha`=1 is a rounding error.
- **90d expected P&L (1% risk, $100k):** **$0** (n=4).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to cut pass rate from 11/22 (50%) to ≤10%.
- **Confidence (1-5):** 5 (confident it's noise).

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money:** **CRYPTO, and only the single proven cell** — `conf=C0.75-0.80 & dir=LONG & source=alpha_engine`, n=249, WR_shrunk=63.94%, PF=2.548, holdout_pass=true, bonferroni_pass=true. Size at 0.5% risk (not 1%) until you've verified adjacent confidence bins (0.70–0.75, 0.80–0.85) also show edge — if they don't, this is a binning artifact and you should halve again. Expected 90d P&L on this cell alone: **+$2,500 to +$3,000**. Do **not** scale the CRYPTO class as a whole — 45.55% class WR means the non-proven cells are bleeding.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**
- **EQUITY** — the PF=214 cell is leakage, not edge. Mutate the `score_dec` feature (it's the common dimension across all three PROVEN cells) before killing the class. If the mutated feature still shows PF>10, kill.
- **FOREX** — 95.7% Smart pass rate + 43.47% WR + a train_pf=0.0/holdout_pf=19.7 split is the signature of a broken temporal split. Mutate the train/holdout boundary logic before killing.
- **COMMODITY** — already has two kills (H-001, H-036). Mutate the `mean_reversion` family definition (it's the common dim in both "best" cells) before killing.

**Do not trade at all:** INDEX, BOND, ETF, FUTURES, UNKNOWN, MEME. All have n_closed < 30 and no qualifying cells.

**The single most important fix:** `passed_high_conviction = 0` across all 10 classes. The HC gate is dead code. Either the trust field is never ≥60 (likely — every CRYPTO edge is `trust=UNK`), or the score never reaches 80. Fix the trust computation first; then re-tune `HC_TRUST_MIN` in `hc_filter.js`. Until that's fixed, the dashboard's headline feature is a lie.

**Brutally honest summary:** Of 10 asset classes, **1 has a real edge (CRYPTO, one cell), 1 has a probable leakage bug (EQUITY), and 8 have no measurable edge.** The funnel is a pass-through, not a filter. The HC gate has never fired. The verified-alpha gate is CRYPTO-only. If you put real money behind the class-level WRs shown here, you would lose money in 7 of 10 classes.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### INDEX
- Real/noise verdict: noise — n=5 closed, no proven cells, WR 20%.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 85
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: noise — top cells have holdout_pass=false, tiny train n=7, bonferroni fails; no proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: HC_MIN_CONF_FOREX = 0.82
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: real — n=249-250, WR_shrunk 63.7-63.94, PF 2.55, holdout_pass=true, bonferroni_pass=true, stable across dims.
- 90d expected P&L (1% risk, $100k): ~$2,780 (250 trades × 1.11% avg_pnl × 1% risk sizing, 0.2% slippage).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 72
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: noise — no proven cells, best_pf cells have holdout_pass=false and n<=32.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 80
- Confidence (1-5): 5

### EQUITY
- Real/noise verdict: noise/leakage — 98.5% WR / PF 214 on n=67 screams single-symbol concentration or look-ahead; reject despite bonferroni.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 90
- Confidence (1-5): 5

### BOND
- Real/noise verdict: noise — no proven cells, best_pf n=20 with holdout_pass=false.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: HC_MIN_TRUST_BOND = 70
- Confidence (1-5): 5

### ETF
- Real/noise verdict: noise — n=9 closed, empty edge lists.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 85
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: noise — n=18 closed, no proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 82
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: noise — n=7 closed, WR 0%, no edges.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 5

### MEME
- Real/noise verdict: noise — n=4 closed, no proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 88
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with verified, holdout-stable edge). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL (high risk of leakage recurrence). All other classes have no actionable edge.
