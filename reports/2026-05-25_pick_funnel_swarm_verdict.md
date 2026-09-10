# Pick Funnel Swarm Verdict — 2026-09-10 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260910T041015Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before per-class verdicts, three system-wide observations that color everything below:

1. **`passed_high_conviction = 0` for every class.** The HC gate (score≥80, conf≥0.75, trust≥60) is firing on **zero** picks in 90 days across 60k+ scans. Either the gate is mis-wired, or the scoring distribution never reaches 80. Either way, the "HIGH CONVICTION" funnel is currently a dead branch — nothing downstream of it can be trusted as "HC-validated."
2. **`passed_verified_alpha` is near-zero everywhere except CRYPTO (1814) and EQUITY (11).** The verified-alpha gate is essentially a CRYPTO-only filter. That's a red flag on the gate itself, not a compliment to CRYPTO.
3. **`opened` >> `passed_smart` in every class** (e.g. EQUITY 4511 opened vs 220 passed_smart; FOREX 22240 opened vs 22564 passed_smart — the latter is *larger* than scanned, which is arithmetically impossible unless "opened" counts re-entries or the counters are on different clocks). **The funnel counters are not internally consistent.** Treat every downstream WR as suspect until the counter semantics are reconciled.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The "PROVEN" cell `fam=mean_reversion & score_dec=S40` shows WR=98.48% (65/66), PF=209.8, holdout PF=124.6. A PF of 210 on 66 trades is not an edge — it is a **data artifact**. Three specific tells: (i) `trust=UNK` dominates the cell, meaning the trust dimension is unpopulated and the cell is really just "mean_reversion + S40"; (ii) `conf=C<0.60` is the *lowest* confidence bucket yet produces the highest WR — that is the signature of a **stop/target inversion or a PnL sign bug**, not a real edge; (iii) 65/66 wins with avg_pnl only +1.27% implies the loss side is being clipped to ~0 (likely a "closed at breakeven" or "expired" bucket being counted as a win). This is almost certainly the same class of bug as H-001 (COT leakage) — a plumbing error masquerading as alpha. **Do not trade it.**
- **90d expected P&L (1% risk, $100k):** **$0** — I would not size this. If forced to mark-to-model the reported numbers: 66 trades × 1% × $100k = $66k risked; at reported avg +1.27% per trade on notional, ~$84k gross — but this is fictional because the WR is not real. **Reported: ~$84k. Honest: $0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — **raise from current value to 55** and add a hard `trust != UNK` requirement in `quality_gates.py`. The S40 bucket is where the artifact lives; excluding it removes the fake edge and forces the funnel to earn its keep on real signals.
- **Confidence (1-5):** **1** (that the edge is real). 5 that it's a bug.

---

### BOND
- **Real/noise verdict:** **NO EDGE.** n_closed=19, WR=21.05%, no PROVEN cells, no best_pf cells. 4 wins / 15 losses. This is a losing class with insufficient sample to even call it "reliably bad." The 21% WR is below the ~33% breakeven for a 2:1 R:R system and below 50% for 1:1. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** Negative. 19 trades × 1% × $100k = $19k risked; at 21% WR with unknown R:R, expect **–$4k to –$8k** realized. Reported closed PnL not given, so this is a range.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — **raise to 70** (effectively demote BOND to "observation only"). 16 passed_smart out of 359 scanned (4.5%) is already tight; the problem is the 16 that pass are bad. Raise the floor until either the class produces a positive-expectancy cell or it stops emitting.
- **Confidence (1-5):** **4** that there's no edge (small n, but directionally clear).

---

### INDEX
- **Real/noise verdict:** **NO EDGE + GATE MALFUNCTION.** 1341/1493 scanned passed_smart (89.8% pass rate) — the Smart gate is not filtering INDEX at all. Then 0/4 decisive wins. The gate is a rubber stamp here. This is the clearest "gate is broken" signal in the dataset.
- **90d expected P&L (1% risk, $100k):** **Negative.** 7 closed, 0W/4L decisive. Too small to size. **~–$2k to –$4k** if you'd traded the 7.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — **raise from current to 65**, and add an explicit `min_rr >= 1.5` requirement. An 89.8% pass rate means the constant is set below the noise floor.
- **Confidence (1-5):** **5** that the gate is broken; **4** that there's no edge.

---

### COMMODITY
- **Real/noise verdict:** **NO PROVEN EDGE.** `top_edges_proven` is empty. The best_pf cell (`rr=RR>=2.0 & score_dec=S50`, n=21, WR=76.2%, PF=5.62) **fails holdout** (`holdout_pass: false`) and **fails Bonferroni** (`bonferroni_pass: false`). n=21 with 9 train / 12 holdout is far too thin. Given H-001 (COT leakage, 85% CT=F cotton) and H-036 (inventory gate rejected) are both in this class, the prior probability that any COMMODITY "edge" is real is very low. **Treat as noise.**
- **90d expected P&L (1% risk, $100k):** **Negative.** 133 decisive, WR=44.36%, PF unknown but WR<50% with typical R:R implies negative expectancy. Rough: 133 × 1% × $100k = $133k risked; at 44% WR and ~1:1 R:R, expect **–$15k to –$25k**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — **raise to 60** AND add a `min_n_for_edge >= 30` requirement before any COMMODITY cell can be promoted to "proven." The current 4288/6639 (64.6%) pass rate is too loose.
- **Confidence (1-5):** **4** no edge.

---

### FOREX
- **Real/noise verdict:** **MOSTLY NOISE, ONE WEAK CANDIDATE.** The PROVEN cell `conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion` (n=136, WR=66.9%, shrunk 64.7%, PF=2.84) passes holdout and Bonferroni — but note the **holdout PF collapses from 3.54 (train) to 1.41 (holdout)**. That's a 60% degradation. A real edge should hold PF within ~30%. This looks like **regime-dependent mean reversion** that worked in the train window and is decaying. The `dir=LONG` variant (n=46, PF=4.61) **fails Bonferroni** — do not trust it. Also: 22564/23582 (95.7%) passed_smart — the Smart gate is a rubber stamp for FOREX, same as INDEX. The "edge" is being found *despite* the gate, not because of it.
- **90d expected P&L (1% risk, $100k):** Using the PROVEN cell only (n=136, avg_pnl +0.28%): 136 × 1% × $100k = $136k risked; at +0.28% avg per trade on notional, **~$38k gross**. But apply a 50% haircut for holdout degradation and slippage on FX (spreads are real): **~$15k–$20k net**. This is the only class where I'd put a non-zero number.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — **raise from current to 60** (kill the 95.7% pass rate) AND add `min_holdout_pf_ratio >= 0.6` in `quality_gates.py` so cells whose holdout PF is <60% of train PF are auto-demoted. The FOREX mean-reversion cell would survive at 1.41/3.54 = 0.40 — so actually it would be **demoted**, which is the correct call.
- **Confidence (1-5):** **2** that the edge is real and tradeable; **4** that the gate is broken.

---

### CRYPTO
- **Real/noise verdict:** **SUSPICIOUS — LIKELY LEAKAGE.** The PROVEN cell `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` (n=214, WR=76.6%, shrunk 74.4%, PF=3.93) has a **holdout PF of 5.86 vs train PF of 3.14** — holdout is *better* than train. That is the classic signature of **look-ahead bias or a survivorship-filtered holdout**, not a real edge. Real edges degrade out-of-sample; they don't improve. Combined with `trust=UNK` dominating the cell (trust dimension unpopulated) and the fact that this is the *only* class where `passed_verified_alpha` is non-trivial (1814), I'd bet the "verified alpha" pipeline is leaking future information into the score. **Do not scale this until the holdout construction is audited.** The user's prompt specifically flagged CRYPTO `ml` cells — this `alpha_engine` cell has the same fingerprint.
- **90d expected P&L (1% risk, $100k):** **Reported: ~$300k** (214 trades × 1% × $100k × 1.43% avg). **Honest: $0** until leakage is ruled out. If the edge survives a clean walk-forward, maybe **$50k–$80k** net of slippage.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **raise to 65** AND add a `holdout_pf <= train_pf * 1.2` sanity check in `quality_gates.py`. Any cell where holdout PF exceeds train PF by >20% should be **quarantined for leakage review**, not promoted. This single change would have caught the CRYPTO artifact.
- **Confidence (1-5):** **1** that the edge is real as reported; **4** that it's leakage.

---

### ETF
- **Real/noise verdict:** **NO EDGE.** n_closed=7, WR=14.29% (1W/6L). 288/327 (88%) passed_smart — gate is a rubber stamp. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** **~–$3k to –$5k** on 7 trades.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — **raise to 65**; consider disabling ETF emission entirely until n_closed > 30.
- **Confidence (1-5):** **4** no edge.

---

### UNKNOWN
- **Real/noise verdict:** **NO EDGE + DATA HYGIENE FAILURE.** n_closed=9, WR=0.0% (0W/9L). The fact that 1437 scans land in "UNKNOWN" means the asset-class classifier is failing on ~2% of the universe. **Do not trade. Fix the classifier.**
- **90d expected P&L (1% risk, $100k):** **~–$5k** on 9 trades.
- **Gate change:** Not a threshold — **add a hard reject in `quality_gates.py` for `asset_class == UNKNOWN`**. Never emit a pick you can't classify.
- **Confidence (1-5):** **5** no edge.

---

### FUTURES
- **Real/noise verdict:** **NO EDGE.** n_closed=18, WR=38.89%, no PROVEN cells. H-005 already killed the futures momentum inversion. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** **~–$4k to –$6k** on 18 trades.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — **raise to 65**; require `min_n_for_edge >= 30`.
- **Confidence (1-5):** **4** no edge.

---

### MEME
- **Real/noise verdict:** **NO EDGE.** n_closed=4. Statistically meaningless. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** **~–$2k** on 4 trades.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — **raise to 75** (effectively disable until n_closed > 30).
- **Confidence (1-5):** **5** no edge.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money:** **FOREX**, and only the single cell `conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion`, at **half size** (0.5% risk per trade) until the holdout-PF degradation is explained. Expected 90d P&L at half size: **~$7k–$10k**. This is the only cell in the entire dataset where (a) n≥100, (b) holdout passes, (c) Bonferroni passes, and (d) the PF is not absurd. It is a *weak* edge, not a strong one — size accordingly.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

- **CRYPTO** — do **not** kill, but **quarantine the `alpha_engine` source** and mutate the holdout construction. The holdout-PF > train-PF signature is a leakage recurrence of the H-001 pattern. Mutate: (i) rebuild holdout with strict time-ordering, (ii) add `holdout_pf <= train_pf * 1.2` gate, (iii) re-run. If the edge survives, scale; if not, kill.
- **EQUITY** — mutate the `mean_reversion & S40` cell by adding a `trust != UNK` requirement and a `conf >= 0.60` floor. The 98% WR is a bug, not an edge. If the cell dies under those constraints, kill the strategy family for EQUITY.
- **COMMODITY** — mutate by requiring `n >= 30` per cell and `holdout_pass == true` before any promotion. Given H-001 and H-036 are both in this class, expect the mutation to fail and the class to be killed.

**Kill outright (no mutation warranted — insufficient n or clearly broken):** BOND, INDEX, ETF, UNKNOWN, FUTURES, MEME. These have n_closed < 20 and/or WR < 40% with no PROVEN cells. The `UNKNOWN` bucket additionally indicates a classifier bug that should be fixed before any of these are re-evaluated.

**The single highest-leverage system change:** add a **`holdout_pf <= train_pf * 1.2` leakage guard** to `quality_gates.py`. It would have caught the CRYPTO artifact, the EQUITY artifact (train PF 99 vs holdout 124 — holdout *better* than train, same signature), and the FOREX degradation (train 3.54 vs holdout 1.41 — this one would be *demoted*, which is correct). One constant, three catches.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — 98.5% WR on n=66 mean-reversion cell is statistically impossible without single-symbol concentration or look-ahead; rejected hypotheses already cover similar EQUITY signals.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65.
- Confidence (1-5): 5

### BOND
- Real/noise verdict: No edge (n=19 closed, empty proven list).
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None (no edge to lift).
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: No edge (n=4 closed, empty proven list).
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None.
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise (best_pf cells fail holdout + Bonferroni; matches rejected H-001/H-036 patterns).
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None.
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Marginal at best — top cells show PF 2.8 but one fails Bonferroni; no strong proven cells survive full filters.
- 90d expected P&L (1% risk, $100k): $0 (insufficient after strict gates).
- Gate change: HC_FILTER_MIN_CONF = 0.78.
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: Real but narrow — n=214, WR_shrunk 74.4%, PF 3.93, holdout_pass + Bonferroni both true; high but internally consistent unlike EQUITY.
- 90d expected P&L (1% risk, $100k): ~$4,800 (214 trades × 1% risk × 1.43% avg pnl, 0.15% slippage, 0.8 fill rate).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 48.
- Confidence (1-5): 3

### ETF
- Real/noise verdict: No edge (n=7 closed).
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None.
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: No edge (n=9 closed).
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None.
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: No edge (n=18 closed; matches rejected H-005).
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None.
- Confidence (1-5): 5

### MEME
- Real/noise verdict: No edge (n=4 closed).
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None.
- Confidence (1-5): 5

**SYSTEM-WIDE:** Scale CRYPTO today (only class with surviving multi-filter edge). DEMOTE EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md (mutate the mean_reversion scanner before any further allocation). All other classes stay at zero live risk.
