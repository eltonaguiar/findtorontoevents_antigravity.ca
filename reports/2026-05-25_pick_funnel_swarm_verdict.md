# Pick Funnel Swarm Verdict — 2026-09-29 04:11 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260929T041054Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before the per-class verdicts, three system-wide red flags that color everything below:

1. **`passed_high_conviction = 0` across every single asset class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing on literally zero picks in 90 days. Either the gate is mis-wired, or the scoring pipeline never produces a pick that satisfies all three simultaneously. This is the single biggest finding in the dataset — the "HIGH CONVICTION" funnel is a dead branch.
2. **`passed_verified_alpha` is 0 for 7 of 10 classes.** Only CRYPTO (1791), FOREX (3), FUTURES (1), MEME (1) produce any. The verified-alpha gate is effectively a CRYPTO-only gate.
3. **`opened` >> `closed` everywhere.** CRYPTO 10267 opened / 2438 closed (24% closure). FOREX 21330/1292 (6%). EQUITY 5455/161 (3%). The 90-day WR numbers are computed on a tiny, non-random survivor subset — likely the fastest-resolving trades. **Every WR below is biased toward short-duration trades and should be treated as an upper bound on uncertainty, not a point estimate.**

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** 102 decisive trades total. Best cell (`trust=UNK & fam=mean_reversion & source=alpha_engine`) has n=33, holdout_n=7, `holdout_pass=false`, `bonferroni_pass=false`, wr_z=1.22. That is not an edge — that is a coin flip with a lucky tail. Class WR 44.1% is below breakeven for typical R:R. Note the H-001 (COT leakage) and H-036 (inventory gate) rejections — this class has a documented history of leakage-driven fake edges. The `mean_reversion + alpha_engine` cell smells like the same family of artifact.
- **90d expected P&L (1% risk, $100k):** **-$1,800 to -$3,500.** 102 decisive trades × 1% risk = ~$1,020 risked per trade × 102 = $104k gross risked. At 44% WR with ~1:1 R:R and 0.15% round-trip slippage on ~$100k notional per trade, expected loss ≈ -$2,400. Do not deploy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise from current floor to **≥ 75** (or add a hard `min_trust >= 40` requirement). Currently 3453/5997 = 58% of scans pass Smart, which is not a filter, it's a pass-through.
- **Confidence (1-5):** **4** (confident it's noise).

### EQUITY
- **Real/noise verdict:** **LEAKAGE — DO NOT TRUST.** The "PROVEN" cell `fam=mean_reversion & score_dec=S40` shows n=67, WR=98.51%, PF=214.55, wr_z=7.94. A 98.5% win rate on 67 trades is not a strategy — it is a data artifact. Three specific tells:
  - **PF=214** is physically implausible for any real strategy at n=67. Real edges top out around PF 3-5.
  - **`score_dec=S40`** (bottom decile of score) producing the *best* edge is inverted logic — it means the score is anti-predictive, which usually indicates the score is computed *after* the outcome (look-ahead).
  - **`trust=UNK`** dominating the top cells means the trust field is unpopulated for these trades — the gate isn't actually gating.
  - The three "different" top cells are the **same 67 trades** sliced three ways. That's not three edges, it's one suspicious cluster.
  - **This is a leakage recurrence pattern** matching the H-001 signature (look-ahead + single-cluster concentration). Flag for immediate investigation before any capital.
- **90d expected P&L (1% risk, $100k):** **$0 — do not deploy.** If the leakage were real (it isn't), 161 trades × 1% × 67% WR × ~1.5 R:R ≈ +$8k. But the headline 67.7% WR is driven by the 67-trade leakage cluster; strip it out and the remaining 94 trades are roughly 45% WR. Realistic expected P&L on the non-leakage subset: **-$1,500 to +$500**, i.e. zero edge.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — but more importantly, **add a `score_dec` sanity check**: reject any pick where `score_dec` is in the bottom 3 deciles AND `trust` is UNK. The current 246/5616 = 4.4% Smart pass rate is fine; the problem is *which* 246 pass.
- **Confidence (1-5):** **5** (confident this is leakage).

### FOREX
- **Real/noise verdict:** **NOISE, borderline leakage.** 481 decisive trades, WR 44.07%. Best cell `rr=RR1.0-1.5 & fam=mean_reversion & dir=LONG & source=multi_asset_copytrader` has n=44, holdout_n=17, `bonferroni_pass=false`, wr_z=1.21. **`multi_asset_copytrader` as a source is a red flag** — copytrader signals are notorious for survivorship bias (you only see the trades that got copied, not the ones that didn't). The 21641/22622 = 95.7% Smart pass rate means the Smart gate is doing nothing for FOREX. The 6% closure rate (1292/21330) means the WR is computed on the fastest-resolving 6% of trades.
- **90d expected P&L (1% risk, $100k):** **-$4,000 to -$7,000.** 481 decisive × 1% × 44% WR × ~1:1 R:R minus ~0.3% FX spread per round trip on $100k notional ≈ -$5,500. Do not deploy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **≥ 70** AND add `min_rr >= 1.5` (currently RR1.0-1.5 is the top cell, which is too tight for FX spreads). The 95.7% pass rate is the smoking gun.
- **Confidence (1-5):** **4**.

### CRYPTO
- **Real/noise verdict:** **PARTIALLY REAL — the only class with a defensible edge.** The top cell `conf=C0.75-0.80 & dir=LONG & score_dec=S50` has n=183, holdout_n=40, `holdout_pass=true`, `bonferroni_pass=true`, wr_z=6.14, PF=3.09, wr_shrunk=70.4%. That is a real, out-of-sample-validated edge. The second cell (`trust=UNK & conf=C0.75-0.80 & dir=LONG & score_dec=S50`) is the same 183 trades — not independent. The third (`conf=C0.75-0.80 & dir=LONG & source=alpha_engine`) is n=251, holdout_n=62, PF=2.49, also passes. **Caveats:**
  - The edge is concentrated in `conf=C0.75-0.80` — a narrow band. Below 0.75 and above 0.80, the edge likely disappears. This is fragile.
  - `dir=LONG` only. No SHORT edge. In a 90-day crypto window that was likely net-up, this could be beta, not alpha. **Check: what was BTC's 90d return?** If BTC was +40%, a 70% LONG WR is just leverage on beta.
  - `score_dec=S50` (middle decile) is the sweet spot — again, inverted from what you'd expect if score were predictive.
  - The `ml` source cells you flagged aren't in the top-3 shown, but if they exist with PF>5, treat them as leakage until proven otherwise.
- **90d expected P&L (1% risk, $100k):** **+$8,000 to +$14,000** on the 183-trade cell alone, IF the edge holds out-of-sample and IF the LONG-only bias isn't just beta. Math: 183 trades × 1% × $100k = $1,000 risked/trade × 183 = $183k gross risked. At PF 3.09 and avg_pnl 1.29%, expected gross ≈ $183k × (0.704 × 1.29% - 0.296 × 0.42%) ≈ +$14k. Subtract 0.1% round-trip slippage on $100k notional × 183 = -$18k... wait, that's wrong. Slippage is per-trade on notional, not on risk. At $100k notional × 0.1% = $100/trade × 183 = -$18,300. **That kills the edge.** Recompute with realistic crypto slippage (0.05% round trip on $100k = $50/trade × 183 = -$9,150). Net: **+$5,000 to +$8,000.** Still positive, but slippage-sensitive.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower to 60** (from current, which is passing 3290/12705 = 26%) AND add a hard `conf >= 0.75 AND conf <= 0.80` band filter for the LONG-only alpha_engine subset. The edge lives in a narrow band; widen the funnel elsewhere, narrow it here.
- **Confidence (1-5):** **3** (real but fragile, beta-contaminated, slippage-sensitive).

### FUTURES
- **Real/noise verdict:** **NOISE.** 18 decisive trades. WR 27.78%. No cells with n>=20. H-005 already killed the momentum inversion hypothesis. Nothing here.
- **90d expected P&L (1% risk, $100k):** **-$1,200.** 18 trades × 1% × 28% WR × 1:1 R:R ≈ -$1,300. Do not deploy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **≥ 80** (effectively disable until n>=100 decisive). 108/164 = 66% pass rate is absurd for a class with 18 closed trades.
- **Confidence (1-5):** **5**.

### BOND
- **Real/noise verdict:** **NOISE.** 32 decisive trades. Best cell n=20, holdout_n=12, `holdout_pass=false`, `bonferroni_pass=false`, wr_z=0.45. Train PF 0.348 vs holdout PF 4.202 — that's not an edge, that's a regime flip. 4/546 = 0.7% Smart pass rate is the only sane number here.
- **90d expected P&L (1% risk, $100k):** **-$600.** 32 trades × 1% × 44% WR × 1:1 ≈ -$600. Do not deploy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — keep at current (it's already filtering 99.3%). Add `min_n_decisive >= 100` before any BOND pick is allowed to open.
- **Confidence (1-5):** **5**.

### ETF
- **Real/noise verdict:** **NOISE.** 8 decisive trades. WR 25%. No cells. 293/335 = 87% Smart pass rate on a class with 8 closed trades is a joke.
- **90d expected P&L (1% risk, $100k):** **-$400.** 8 trades × 1% × 25% WR ≈ -$400. Do not deploy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **≥ 85** (effectively disable). 87% pass rate is the worst in the dataset.
- **Confidence (1-5):** **5**.

### UNKNOWN
- **Real/noise verdict:** **NOISE / DATA HYGIENE FAILURE.** 7 decisive trades, 0 wins. The fact that 1398 scans land in UNKNOWN and 1391 open means the classifier is broken. This isn't an asset class, it's a bug.
- **90d expected P&L (1% risk, $100k):** **-$700.** 7 trades × 1% × 0% WR = -$700. Do not deploy.
- **Gate change:** **Reject all UNKNOWN at the scanner level** — add `if asset_class == "UNKNOWN": return None` in `production_scanner.py`. This is a hygiene fix, not a gate tuning.
- **Confidence (1-5):** **5**.

### MEME
- **Real/noise verdict:** **NOISE.** 4 decisive trades. WR 25%. n=22 scanned. Not enough data to say anything.
- **90d expected P&L (1% risk, $100k):** **-$300.** 4 trades × 1% × 25% WR ≈ -$300. Do not deploy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **≥ 90** (effectively disable until n>=50 decisive).
- **Confidence (1-5):** **5**.

### INDEX
- **Real/noise verdict:** **NOISE.** 5 decisive trades. WR 20%. 1491/1691 = 88% Smart pass rate on 5 closed trades. Absurd.
- **90d expected P&L (1% risk, $100k):** **-$400.** 5 trades × 1% × 20% WR ≈ -$400. Do not deploy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **≥ 85** (effectively disable).
- **Confidence (1-5):** **5**.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only CRYPTO, and only the narrow `conf=C0.75-0.80 & dir=LONG & source=alpha_engine` cell.** It is the only cell in the entire dataset that passes holdout, Bonferroni, and has n>=100 with a plausible (not absurd) PF. Size it at **0.5% risk per trade, not 1%**, until you've confirmed the LONG-only bias isn't just BTC beta. Cap notional at $50k per trade to keep slippage under control. Expected 90d P&L on this cell alone: **+$5k to +$8k** net of realistic slippage.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

- **EQUITY** — mutate first. The 98.5% WR / PF 214 cell is almost certainly leakage (matches H-001 signature: look-ahead + single-cluster concentration + inverted score logic). Before killing the class, run the three-axis mutation: (1) recompute `score_dec` using only pre-trade data, (2) re-run with `trust` populated, (3) split by symbol to check concentration. If the edge survives all three, it's real. It won't.
- **FOREX** — mutate first. The `multi_asset_copytrader` source needs survivorship-bias correction. Re-run excluding copied trades that were closed by the source before the copy executed.
- **COMMODITY** — mutate first, but with low expectations. H-001 and H-036 already killed two hypotheses here. The `mean_reversion + alpha_engine` cell is the third strike candidate.
- **FUTURES, BOND, ETF, INDEX, MEME, UNKNOWN** — **kill outright.** n<35 decisive in every case. No mutation will rescue a class with 5-18 closed trades. Disable at the scanner level until n>=100 decisive.

**The single most important fix:** `passed_high_conviction = 0` across all 10 classes. The HC gate in `hc_filter.js` is either mis-wired or the scoring pipeline never produces a qualifying pick. **Debug this before any capital deployment** — if HC is supposed to be the "best of the best" funnel and it's empty, either the thresholds are wrong or the upstream scores are capped below 80. Check `production_scanner.py` for a hard cap on `score` and `trust` fields.

**Do not deploy capital to any class except CRYPTO's narrow cell.** The dataset is dominated by noise, leakage, and survivorship bias. The user's instruction — "do not invent edges to look as productive" — is the correct posture. There is exactly one defensible edge here, and it's fragile.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### COMMODITY
- Real/noise verdict: noise — no proven cells; best_pf cells have n=33, holdout fails, bonferroni fails, PF inflated by small sample.
- 90d expected P&L (1% risk, $100k): $0 (overall WR 44%, slippage + commissions erase edge).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 75
- Confidence (1-5): 5

### EQUITY
- Real/noise verdict: noise — the single proven cell (n=67, WR_shrunk 87%, PF 214) is statistically impossible without leakage or single-symbol concentration; identical stats across three overlapping dims confirm data artifact.
- 90d expected P&L (1% risk, $100k): -$1,200 (overall WR 68% on 161 trades but proven cell is fake; real edge absent after costs).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 85
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: noise — no proven cells; best_pf cells fail bonferroni, n=44-45, holdout marginal, PF driven by one source.
- 90d expected P&L (1% risk, $100k): $0 (overall WR 44% on 481 decisive trades).
- Gate change: HC_MIN_CONF_FOREX = 0.82
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: statistically real — two cells (n=183, WR_shrunk 70.4%, PF 3.09; n=251, PF 2.49) pass holdout, bonferroni, and show stable train/holdout; no obvious single-symbol leakage.
- 90d expected P&L (1% risk, $100k): +$8,400 (183 trades at 1% risk, avg 1.29% pnl, 0.15% slippage assumed, net ~8.4R).
- Gate change: HC_MIN_CONF_CRYPTO = 0.78
- Confidence (1-5): 4

### FUTURES
- Real/noise verdict: noise — n=18 total closed, no proven cells, best_pf empty.
- 90d expected P&L (1% risk, $100k): $0 (overall WR 28%).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 80
- Confidence (1-5): 5

### BOND
- Real/noise verdict: noise — n=32, best_pf cell fails holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): $0 (overall WR 44%).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 70
- Confidence (1-5): 5

### ETF
- Real/noise verdict: noise — n=8 closed, no edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 80
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: noise — n=7, WR 0%.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 5

### MEME
- Real/noise verdict: noise — n=4, no edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 85
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: noise — n=5, no edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 85
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with credible, holdout-validated edges). Demote EQUITY immediately (proven cell is leakage artifact per MUTATION_THREE_AXIS_PROTOCOL). All other classes have zero actionable edge.
