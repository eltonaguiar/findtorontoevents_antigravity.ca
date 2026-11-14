# Pick Funnel Swarm Verdict — 2026-11-14 04:06 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261114T040619Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before per-class verdicts, three structural facts that dominate everything below:

1. **The funnel is inverted.** `passed_smart` ≈ `opened` for every class (FOREX 25,146 → 24,521; COMMODITY 3,683 → 5,764; EQUITY 229 → 5,740; INDEX 1,615 → 2,113; CRYPTO 3,633 → 9,893). The "Smart" gate is not filtering — it is a pass-through. The only real filter in the stack is `passed_verified_alpha` (CRYPTO 2,219, everything else ~0–3) and `passed_high_conviction` (**0 across all 10 classes**). The HC gate at score≥80 / conf≥0.75 / trust≥60 is **dead code** — it has never fired in 90 days. That is the single biggest finding in this dataset.
2. **`trust=UNK` dominates every "proven" cell.** Every PROVEN cell in FOREX, EQUITY, and the only near-proven cell in CRYPTO is `trust=UNK`. That means the trust dimension is not populated for the trades that are actually winning — the trust gate is either not being computed or is being bypassed. Any "edge" that lives entirely in the UNK bucket is not a validated edge; it's an un-audited bucket.
3. **Closed counts are tiny relative to opened.** FOREX 1,295/24,521 (5.3%), COMMODITY 37/5,764 (0.6%), EQUITY 106/5,740 (1.8%), INDEX 1/2,113 (0.05%). Only CRYPTO (23%) and BOND (2.7%) have meaningful closure rates. Every non-CRYPTO "WR" is computed on a sample that is 1–5% of the opened book — that is not a 90-day edge, that is a 90-day *snapshot of the survivors*.

---

### FOREX
- **Real/noise verdict:** **NOISE / LEAKAGE-SUSPECT.** The PROVEN cell `trust=UNK & conf=C>=0.90 & fam=regime` (n=38, WR 89.5%, shrunk 75.9%, PF 14.4) is the textbook signature of a leakage recurrence, not an edge. Three red flags: (i) `trust=UNK` — the winning trades are precisely the ones the trust gate did not score; (ii) `fam=regime` + `source=regime_terminal` — a single strategy family and single source, so this is one signal, not a cross-section; (iii) PF 14.4 on n=38 with holdout n=10 and holdout PF "99.0" (capped) — a holdout of 10 trades cannot validate a PF of 14. The `wr_z=4.87` is inflated by the tiny n and the near-deterministic win pattern. This is the same shape as **H-001 (COT look-ahead)** and **H-036 (inventory direction)** — a single-source, single-family, high-WR cell that collapses when timestamps are fixed. **Treat as a leakage recurrence until proven otherwise.** The class-level WR of 51.5% on 435 decisive trades is the honest number: coin-flip. The 24,521 opened vs 1,295 closed means 95% of the book is unresolved — the 51.5% is a survivor sample, not a WR.
- **90d expected P&L (1% risk, $100k):** **≈ $0 to −$400.** At 51.5% WR on 435 decisive trades with 1% risk ($1,000/trade), gross edge is ~1.5% × 435 × $1,000 ≈ +$6,500 *if* the 51.5% is real and R:R is symmetric — but it is not symmetric (regime cells have RR≥2.0, the rest are mixed), and slippage on 24.5k opened FX trades at even 0.5 pip round-trip on a $100k notional is ~$5/trade × 24.5k = **−$122k in friction alone**. Net: **negative**. Do not deploy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — currently effectively 0 (25,146/25,816 pass). Set to **75** and require `trust != UNK` as a hard precondition. This alone would cut the opened book by ~95% and force the trust dimension to actually populate.
- **Confidence (1-5):** **1**

### COMMODITY
- **Real/noise verdict:** **NO EDGE.** 37 closed trades total. The "best" cell (`trust=UNK & dir=LONG & source=alpha_engine`, n=28, WR 64.3%, PF 2.14) **fails holdout** (holdout PF 1.14, holdout_pass=false) and fails Bonferroni. `wr_z=1.51` is not significant. This is the same shape as **H-001** (single-source, single-direction, UNK trust) and **H-036** (direction-only signal, WR 46% on n=1051 when properly tested). The 70.3% class WR is on **37 trades** — statistically meaningless. The 5,764 opened vs 37 closed (0.6%) means the book is essentially unmeasured.
- **90d expected P&L (1% risk, $100k):** **≈ $0.** 37 trades × 1% × $100k = $37k at risk; at 70% WR with symmetric R:R the *point estimate* is +$15k, but the 95% CI on 37 trades spans roughly −$8k to +$38k. **Not distinguishable from zero.** Do not deploy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — currently 3,683/5,801 pass (63%). Set to **80** and add a hard `source != alpha_engine OR trust != UNK` requirement, which kills the only "edge" cell (which is the leakage-shaped one).
- **Confidence (1-5):** **1**

### EQUITY
- **Real/noise verdict:** **LEAKAGE — DO NOT TRADE.** The PROVEN cell `trust=UNK & rr=RR>=2.0 & fam=mean_reversion` (n=38, WR **97.4%**, shrunk 81.0%, **PF 135.0**, holdout PF 99.0, Bonferroni pass) is the most suspicious number in the entire dataset. A PF of 135 on mean-reversion equity trades is not an edge — it is a **data artifact**. The signature is unmistakable: (i) `trust=UNK` again; (ii) `rr=RR>=2.0` — the R:R is being *computed* from the outcome, not set ex-ante (classic look-ahead: if R:R is derived from realized max-favorable/max-adverse excursion, then high-R:R trades are by construction the winners); (iii) 37/38 wins with only 1 loss — no real strategy produces that; (iv) holdout n=22 with PF 99.0 (capped) — the cap itself is a tell that the metric is saturating. This is **H-001-shaped leakage** (look-ahead in the R:R or in the mean-reversion entry timestamp). The class-level 72.6% WR on 106 trades is also suspect for the same reason. **Flag as leakage recurrence.**
- **90d expected P&L (1% risk, $100k):** **$0 — do not deploy.** The point estimate from the "proven" cell would be absurd (+$37k on 38 trades), which is exactly why it must be rejected. The honest number is **unknown and probably negative** once the R:R leakage is fixed.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — currently 229/5,846 pass (3.9%), which is the *only* class where the Smart gate is actually filtering. But the 5,740 opened vs 229 passed_smart means **the opened book is bypassing the Smart gate entirely** — the gate is being applied to a different population than the one that trades. Fix the wiring first: `SMART_PICKS_MIN_SCORE_EQUITY = 70` **and** enforce that `opened ⊆ passed_smart`. Also add `rr_source == "ex_ante"` as a hard precondition — reject any trade where R:R is computed post-hoc.
- **Confidence (1-5):** **1** (the "edge" is leakage; the class has no verified edge)

### INDEX
- **Real/noise verdict:** **NO DATA.** 1 closed trade, 100% WR. n=1 is not a sample. 2,113 opened vs 1 closed (0.05%) means the closure pipeline is broken for INDEX. Cannot assess.
- **90d expected P&L (1% risk, $100k):** **$0** (n=1, no estimate possible).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — 1,615/2,114 pass (76%). Set to **80** and **fix the closure pipeline** before any gate tuning is meaningful. Gate tuning on an unclosed book is noise-fitting.
- **Confidence (1-5):** **1**

### CRYPTO
- **Real/noise verdict:** **NO PROVEN EDGE — but the closest thing to a real signal in the dataset.** No cell passes the PROVEN bar (Bayesian-shrunk WR≥55% AND PF≥1.5 AND Bonferroni). The best cell `trust=UNK & rr=RR1.5-2.0 & source=alpha_engine` (n=197, WR 59.4%, shrunk 58.5%, PF 2.02, holdout PF 1.32, holdout_pass=true, **bonferroni_pass=false**) is the only cell in the entire dataset that (a) has n≥100, (b) passes holdout, and (c) has a plausible (not absurd) PF. But it **fails Bonferroni** — with ~dozens of cells tested, a wr_z of 2.64 is expected by chance. The `trust=UNK` again undermines it. The class-level 44.8% WR on 2,291 decisive trades is the honest number: **losing**. The 2,219 `passed_verified_alpha` is the only meaningful filter in the stack, and it is still producing a 44.8% WR — so verified_alpha is not actually verifying alpha. **No edge. Do not deploy.** The `ml` cells the prompt flags are not in the top-3 shown, but the pattern (UNK trust, single source, high PF, fails Bonferroni) is the same leakage shape as FOREX/EQUITY.
- **90d expected P&L (1% risk, $100k):** **≈ −$8,000 to −$12,000.** 2,291 decisive trades × 1% × $100k = $2.29M at risk; at 44.8% WR with typical crypto R:R ~1.5, expected loss ≈ −0.5% × 2,291 × $1,000 ≈ **−$11k**, before slippage. Crypto slippage at 10–20 bps round-trip on $100k notional = $100–$200/trade × 2,291 = **−$230k to −$460k in friction**. The class is a money-loser at this WR. **Do not deploy.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — currently 3,633/12,197 pass (30%), but 9,893 opened means **the opened book is 2.7× the passed_smart book** — the gate is being bypassed. Fix the wiring: enforce `opened ⊆ passed_smart`, set `SMART_PICKS_MIN_SCORE_CRYPTO = 70`, and add `trust != UNK` as a hard precondition. The single highest-leverage change is **`hc_filter.js` `MIN_TRUST = 60` → enforce it** (currently 0 HC passes, so the gate is either mis-wired or the trust scores never reach 60 — either way, fix before tuning).
- **Confidence (1-5):** **2** (the only class with enough closed trades to say anything; the answer is "no edge")

### ETF
- **Real/noise verdict:** **NO EDGE — actively negative.** 10 closed, 1 win, 9 losses, WR 10%. n=10 is too small to be significant, but 1/10 is not a fluke you'd bet on. 309 opened vs 10 closed (3.2%).
- **90d expected P&L (1% risk, $100k):** **≈ −$8,000** (10 trades × 1% × $100k × −80% net = −$8k point estimate; CI spans −$15k to +$2k). Do not deploy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — 278/319 pass (87%). Set to **80** and **halt ETF trading** until closure rate >20%.
- **Confidence (1-5):** **1**

### UNKNOWN
- **Real/noise verdict:** **NO EDGE — 0/3 wins.** 3 closed, 0 wins. 1,301 opened vs 3 closed (0.2%). This bucket should not exist — it means the classifier is failing on 1,304 scans. The 0% WR is not a signal, it's a data-quality alarm.
- **90d expected P&L (1% risk, $100k):** **≈ −$3,000** (3 trades × 1% × $100k × −100% = −$3k; n=3, meaningless).
- **Gate change:** **Do not tune a score gate — fix the classifier.** Add a hard reject in `quality_gates.py`: `if asset_class == "UNKNOWN": reject`. This is not a threshold change, it's a routing fix.
- **Confidence (1-5):** **1**

### BOND
- **Real/noise verdict:** **NO EDGE — negative.** 31 closed, 12W/19L, WR 38.7%. n=31 is small but the direction is clear and consistent with the class-level number. 1,148 opened vs 31 closed (2.7%).
- **90d expected P&L (1% risk, $100k):** **≈ −$7,000** (31 trades × 1% × $100k × −22% net = −$6.8k; CI −$15k to +$1k). Do not deploy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — 1/1,179 pass (0.08%), which is the *only* gate that is actually filtering hard. But 1,148 opened vs 1 passed_smart means **the opened book is 1,148× the passed book** — the gate is completely bypassed. Fix the wiring: enforce `opened ⊆ passed_smart`. Then set `SMART_PICKS_MIN_SCORE_BOND = 70`.
- **Confidence (1-5):** **1**

### FUTURES
- **Real/noise verdict:** **NO EDGE.** 16 closed, 6W/10L, WR 37.5%. n=16 is too small. 156 opened vs 16 closed (10%). Consistent with **H-005** (futures momentum anti-signal — inversion does not fix it) and **H-001** (COT leakage). No cell qualifies.
- **90d expected P&L (1% risk, $100k):** **≈ −$4,000** (16 trades × 1% × $100k × −25% net = −$4k; CI −$10k to +$2k). Do not deploy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — 123/172 pass (72%). Set to **80** and require `trust != UNK`.
- **Confidence (1-5):** **1**

### MEME
- **Real/noise verdict:** **NO EDGE.** 7 closed, 3W/4L, WR 42.9%. n=7 is not a sample. 15 opened vs 7 closed (47% — the only class with a sane closure rate, ironically because the book is tiny).
- **90d expected P&L (1% risk, $100k):** **≈ −$1,500** (7 trades × 1% × $100k × −21% net = −$1.5k; n=7, meaningless).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — 10/22 pass (45%). Set to **80** and require `trust != UNK`. Or **halt MEME entirely** — 22 scans in 90 days is not a strategy, it's a rounding error.
- **Confidence (1-5):** **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: NONE.** There is not a single asset class in this dataset with a statistically defensible edge. Every "PROVEN" cell is either (a) `trust=UNK` (un-audited bucket), (b) single-source/single-family (not a cross-section), (c) fails holdout or Bonferroni, or (d) has a PF so high (14.4, 135.0) that it is a leakage signature, not an edge. The three classes with the most closed trades — CR

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### FOREX
- Real/noise verdict: noise — n=38 regime cell has extreme PF=14.4 and WR_shrunk=75.86 but tiny holdout (n=10) and bonferroni_pass=true only on one narrow slice; classic small-sample blow-up, not stable.
- 90d expected P&L (1% risk, $100k): $0 (no reliable edge; any live deployment would be pure variance).
- Gate change: SMART_PICKS_MIN_SCORE_FOREX = 82
- Confidence (1-5): 2

### COMMODITY
- Real/noise verdict: noise — all best_pf cells fail holdout_pass; n<=28 and PFs collapse out-of-sample.
- 90d expected P&L (1% risk, $100k): -$420 (expected negative drift once slippage applied).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 85
- Confidence (1-5): 1

### EQUITY
- Real/noise verdict: noise — mean_reversion cell shows PF=135 / WR=97% on n=38; impossible without single-symbol concentration or leakage (mean_reversion on equities rarely sustains that).
- 90d expected P&L (1% risk, $100k): $0 (do not trade; flagged as potential leakage recurrence).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 90
- Confidence (1-5): 1

### INDEX
- Real/noise verdict: noise — n_closed=1, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 95
- Confidence (1-5): 1

### CRYPTO
- Real/noise verdict: noise — best_pf cells reach PF=2.016 but bonferroni_pass=false and holdout PF drops to 1.316; no PROVEN cells survived.
- 90d expected P&L (1% risk, $100k): $0 (edge not statistically real).
- Gate change: HC_MIN_CONF_CRYPTO = 0.82
- Confidence (1-5): 2

### ETF
- Real/noise verdict: noise — n_closed=10, empty edge lists.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 88
- Confidence (1-5): 1

### UNKNOWN
- Real/noise verdict: noise — n_closed=3, zero edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 95
- Confidence (1-5): 1

### BOND
- Real/noise verdict: noise — n_closed=31, no proven or best_pf survivors.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 92
- Confidence (1-5): 1

### FUTURES
- Real/noise verdict: noise — n_closed=16, empty lists.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 90
- Confidence (1-5): 1

### MEME
- Real/noise verdict: noise — n_closed=7, empty lists.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 95
- Confidence (1-5): 1

**SYSTEM-WIDE CONCLUSION**  
Scale up: none. Demote: CRYPTO and EQUITY (highest scanned volume but zero surviving proven edges after shrinkage/holdout; route to MUTATION_THREE_AXIS_PROTOCOL review before any further allocation). All other classes already effectively zero-edge.
