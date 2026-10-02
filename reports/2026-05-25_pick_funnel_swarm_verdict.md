# Pick Funnel Swarm Verdict — 2026-10-02 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261002T041037Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before the per-class breakdown, three system-wide red flags that dominate everything below:

1. **`passed_high_conviction = 0` across every single asset class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing on literally zero picks in 90 days. That is not a filter — that is a dead gate. Either the thresholds are miscalibrated against the actual score distribution, or `trust>=60` is unreachable because most picks are `trust=UNK`. This is the single most important finding in the dataset.
2. **`passed_verified_alpha` is near-zero everywhere except CRYPTO (1801).** FOREX: 3. COMMODITY: 0. EQUITY: 0. INDEX: 0. So the "verified alpha" tier is effectively a CRYPTO-only construct right now.
3. **Opened >> closed in every class.** FOREX opened 21,514 / closed 1,347 (6.3%). CRYPTO 10,196 / 2,444 (24%). COMMODITY 5,733 / 95 (1.7%). The funnel is not a funnel — it's a firehose with a pinhole exit. Any WR computed on the closed subset is subject to **massive survivorship/selection bias** because we don't know why 94% of FOREX picks never closed (timeout? still open? silently dropped?).

---

### FOREX
- **Real/noise verdict:** **NOISE.** The three "best PF" cells all fail holdout (`holdout_pass: false`), fail Bonferroni, and have `wr_z` between 1.2 and 2.6 — well below the ~3.5 threshold you'd need after multiple-testing correction across ~10 classes × dozens of cells. The `regime_terminal` cell (n=33, WR 72.7%) has `train_pf: 0.0` on n=7 — that's a degenerate train split, not an edge. The `multi_asset_copytrader` cell has holdout PF 1.096 vs train 4.91 — classic overfit collapse. **Zero PROVEN cells.** The 43.79% decisive WR is below coin-flip after costs. This class has no edge.
- **90d expected P&L (1% risk, $100k):** **Negative.** 507 decisive trades × 1% risk = ~$5,070 at risk per unit of R. At 43.79% WR with typical 1:1 R:R, expectancy ≈ −0.12R/trade → **≈ −$600 to −$1,200** after ~0.5 pip slippage + spread on 507 trades. Do not deploy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise aggressively. Currently passing 21,890/22,861 (95.8%) of scans. That is not a gate. Set to a value that passes ≤5% of scans (calibrate to the 95th percentile of the score distribution; if unknown, start at **85** and re-measure). Also: the `trust>=60` HC requirement is unreachable for FOREX because most picks are `trust=UNK` — either fix trust scoring or drop the trust dimension from HC for FOREX.
- **Confidence (1-5):** **1**

### CRYPTO
- **Real/noise verdict:** **PARTIALLY REAL, but the headline PF is inflated.** The `conf=C0.75-0.80 & dir=LONG & score_dec=S50` cell (n=183, WR 71.6%, shrunk 69.5%, PF 3.01, holdout PF 3.34 on n=41, Bonferroni pass, wr_z 5.84) is the **only cell in the entire dataset that survives every test.** That is a genuine signal. **However:** (i) the `trust=UNK` variant is the *same 183 trades* — trust is not adding information, it's just an unpopulated dimension; (ii) the `source=alpha_engine` variant (n=251) overlaps heavily with the first cell, so these are not three independent edges — they're one edge viewed three ways. The `ml` cell you flagged isn't in the top-3 shown, but if it exists with PF > 5, treat it as **leakage until proven otherwise** — ML cells with n<100 and PF>5 in crypto are almost always feature leakage (future returns in features, or same-bar close used for entry). **Demand a feature-importance audit and a strict time-split retrain before trusting any `ml` cell.**
- **90d expected P&L (1% risk, $100k):** Using the proven cell (n=183, avg_pnl 1.26%, WR 71.6%): 183 trades × 1% risk × (0.716 × 1.26 − 0.284 × ~1.0) ≈ 183 × $1,000 × 0.62 ≈ **+$113,000 gross**. Apply 30% haircut for slippage/funding on crypto (perp funding ~0.01%/8h, slippage 5–15 bps on alts): **≈ +$75,000–$85,000.** But this assumes you could actually *take* all 183 — in practice you'd size down on correlated longs. Realistic deployable: **+$40,000–$60,000** on the proven cell alone.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower it slightly** to admit more `conf=0.75-0.80 LONG` picks, OR (better) add an explicit **direction+confidence override** in `production_scanner.py`: if `conf ∈ [0.75, 0.80] AND direction == LONG AND score_decile == S50`, bypass the score floor. The current gate is passing 3,315/12,640 (26%) — it's not the bottleneck; the bottleneck is that the HC gate (`score>=80`) is killing the very picks that work. **Fix `hc_filter.js`: lower `score>=80` to `score>=70` for CRYPTO only, keep conf>=0.75 and trust>=60.** This is the highest-leverage single change in the whole system.
- **Confidence (1-5):** **4** (on the proven cell; 2 on anything labeled `ml`)

### COMMODITY
- **Real/noise verdict:** **NOISE, and likely a leakage recurrence.** The top cell (`trust=UNK & rr=RR1.5-2.0 & fam=mean_reversion`, n=20, WR 60%, PF 4.6) has `holdout_n: 2` — that is not a holdout, that is two trades. `holdout_pass: false`, Bonferroni fail, wr_z 0.89. The `alpha_engine` mean-reversion cell (n=32, PF 3.97) has holdout n=5. **These are not edges.** Given [H-001] and [H-036] were both COMMODITY leakage kills, and this dataset shows the same signature (small n, huge PF, tiny holdout), **flag this as a potential leakage recurrence** — check whether `mean_reversion` on commodities is using same-bar or next-bar-open fills. The 48.94% decisive WR on n=94 is the honest number, and it's a coin flip.
- **90d expected P&L (1% risk, $100k):** **≈ $0 to −$200.** 94 decisive trades, WR 48.9%, roughly 1:1 → expectancy ≈ −0.02R → **−$200**. Not deployable.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — currently passing 3,312/5,828 (56.8%). Raise to pass ≤10%. But more importantly: **add a `MIN_HOLDOUT_N` constant to the edge-promotion logic** (e.g. `MIN_HOLDOUT_N = 20`) so cells like the n=2 holdout never get labeled "best PF" again. That's a reporting bug masquerading as an edge.
- **Confidence (1-5):** **1**

### EQUITY
- **Real/noise verdict:** **LEAKAGE. Do not trade this.** The `mean_reversion & score_dec=S40` cell shows **WR 98.51% (66/67), PF 214.55, holdout PF 99.0 on n=30.** A 98.5% win rate with PF >200 is not an edge — it is a **data integrity failure.** Possible causes: (i) same-bar entry/exit using close prices (look-ahead); (ii) `score_dec=S40` is a post-hoc label derived from outcome; (iii) the "loss" definition excludes scratched/breakeven trades so 66/67 is really 66/200; (iv) single-symbol concentration (one ticker that gapped up repeatedly). **This cell must be quarantined and audited before any capital touches it.** The honest number is the class-level 68.9% WR on n=164 — which is *also* suspiciously high for equity mean-reversion and probably shares the same bug.
- **90d expected P&L (1% risk, $100k):** **Cannot estimate — the input is corrupted.** If the 68.9% class WR is real (it isn't), 164 trades × 1% × (0.689×1.0 − 0.311×1.0) ≈ +$6,200. But I do not believe the 68.9%. **Assume $0 until the leakage audit clears.**
- **Gate change:** **Do not change a gate — change the harness.** Add a `MAX_PLAUSIBLE_PF = 10.0` assertion in the edge-reporting code that flags (not promotes) any cell exceeding it. Then audit the `mean_reversion` equity strategy for same-bar fills. The gate constant is irrelevant while the data is wrong.
- **Confidence (1-5):** **1** (that it's real); **5** (that it's leakage)

### INDEX
- **Real/noise verdict:** **NOISE / insufficient data.** n_closed = 5. WR 20%. Nothing to say. The 1,569/1,779 (88%) smart-pass rate is a gate that isn't gating.
- **90d expected P&L (1% risk, $100k):** **−$300** (5 trades, 20% WR, ~1:1). Statistically meaningless.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to pass ≤10%. Or **disable INDEX picks entirely** until n_closed ≥ 100.
- **Confidence (1-5):** **1**

### BOND
- **Real/noise verdict:** **NOISE.** n_closed = 32. Best cell has holdout n=7 with PF 34.3 — that's one lucky trade. `holdout_pass: false`, Bonferroni fail. 43.75% WR. No edge.
- **90d expected P&L (1% risk, $100k):** **≈ −$150** (32 trades, 43.75% WR, ~1:1).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — currently passing 3/533 (0.6%). This gate is *already* tight; the problem is the 501 opened trades that bypassed it. **Audit why 501 bonds opened when only 3 passed smart.** That's a routing bug, not a threshold bug.
- **Confidence (1-5):** **1**

### ETF
- **Real/noise verdict:** **NOISE.** n_closed = 9. WR 22%. No cells. Nothing.
- **90d expected P&L (1% risk, $100k):** **−$500** (9 trades, 22% WR). Meaningless.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to pass ≤10%. Or disable until n≥100.
- **Confidence (1-5):** **1**

### FUTURES
- **Real/noise verdict:** **NOISE, and consistent with [H-005].** n_closed = 18, WR 27.8%. The prior hypothesis that futures momentum is an anti-signal was already falsified as *not invertible* — meaning it's just noise, not a reliable short either. Nothing here contradicts that.
- **90d expected P&L (1% risk, $100k):** **−$800** (18 trades, 27.8% WR, ~1:1). Meaningless sample.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to pass ≤10%. Or disable.
- **Confidence (1-5):** **1**

### UNKNOWN
- **Real/noise verdict:** **DATA HYGIENE FAILURE.** 1,387 scans, 1,380 opened, 0 wins, 7 losses. The fact that 1,380 picks have no asset class is a routing bug. **This is not a class — it's a bug report.**
- **90d expected P&L (1% risk, $100k):** **−$700** (7 trades, 0% WR). But the real cost is the 1,380 unclassified opens polluting every downstream metric.
- **Gate change:** Add a hard `REQUIRE_ASSET_CLASS = True` assertion in `production_scanner.py` — reject any pick without a class before it reaches the funnel. This is the highest-ROI hygiene fix.
- **Confidence (1-5):** **5** (that it's a bug)

### MEME
- **Real/noise verdict:** **NOISE.** n_closed = 4. WR 25%. Nothing.
- **90d expected P&L (1% risk, $100k):** **−$200**. Meaningless.
- **Gate change:** Disable MEME picks until n_closed ≥ 100. `SMART_PICKS_MIN_SCORE_MEME = 999` (effectively off).
- **Confidence (1-5):** **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only CRYPTO, and only the `conf=0.75-0.80 & dir=LONG & score_dec=S50` cell.**

That cell is the only one in the entire 90-day dataset that passes holdout, Bonferroni, and has a plausible (not absurd) PF of 3.0 with n=183. Everything else is either noise (FOREX, COMMODITY, BOND, INDEX, ETF, FUTURES, MEME, UNKNOWN) or leakage (EQUITY). The `trust=UNK` and `source=alpha_engine` variants are the same trades re-sliced — do not treat them as independent confirmation.

**Demote per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

- **EQUITY** — demote immediately, but the mutation axis is **not** the strategy; it's the **harness**. The 98.5% WR / PF 214 cell is a data-integrity failure. Mutate the fill model (force next-bar-open), re-run, and only then decide whether the class lives. Do not kill the class on corrupted data.
- **FOREX** — demote. Mutate the `trust` dimension (it's `UNK` for nearly everything, so it's carrying no signal) and the score floor. If after mutation the class still shows <50% decisive WR on n>500, kill it.
- **COMMODITY** — demote. Mutate the `mean_reversion` family's fill timing (leakage recurrence risk given [H-001]/[H-036]). If PF collapses to <1.2, kill.
- **INDEX, ETF, FUTURES, BOND, MEME, UNKNOWN** — these have n_closed < 35 each. They are not classes; they are **sampling noise**. Do not mutate — **suppress** them at the scanner level until they accumulate n≥100 closed, then re-evaluate. UNKNOWN additionally needs a routing fix, not a strategy fix.

**The single most important action item, above all gate tuning:** `passed_high_conviction = 0` across all 10 classes means the HC gate in `hc_filter.js` is dead. Fix it (lower `score>=80` to `score>=70` for CRYPTO, and resolve the `trust>=60` unreachability for everything else) before you tune any other constant. Right now the dashboard is showing users a "HIGH CONVICTION" tab that has never fired in 90 days — that is a product bug, not a strategy bug.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real (n=183/251 cells pass holdout + Bonferroni; WR_shrunk 63-69%, PF 2.5-3.0 stable across splits). No obvious leakage flagged in listed dims.
- 90d expected P&L (1% risk, $100k): $8,400 (183 trades at ~$1k risk each, 1.26% avg win, 0.42% avg loss, net +8.4% after 0.1% slippage).
- Gate change: SMART_PICKS_MIN_CONF_CRYPTO = 0.75
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Noise (PF=214 on n=67 is statistically impossible without single-symbol concentration or label leakage; rejected hypotheses H-009/H-011 already killed similar equity signals).
- 90d expected P&L (1% risk, $100k): $0 (edge is artifact; live deployment would revert to ~45% WR).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 85
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise (no proven cells; best_pf cells fail holdout and Bonferroni; n small and regime-specific).
- 90d expected P&L (1% risk, $100k): -$1,200 (random walk around 44% WR after costs).
- Gate change: SMART_PICKS_MIN_TRUST_FOREX = 70
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: Noise (no proven cells; best_pf cells fail holdout; H-001/H-036 already rejected similar commodity signals).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_RR_COMMODITY = 2.0
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise (n=32 total, no proven cells, best_pf fails holdout and Bonferroni).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: HC_MIN_CONF_BOND = 0.80
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise (n=5 closed, zero proven cells).
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 90
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise (n=9 closed, zero proven cells).
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 85
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise (n=18 closed, zero proven cells; H-005 already rejected futures momentum variants).
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 80
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise (n=7 closed, zero proven cells).
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise (n=4 closed, zero proven cells).
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 85
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically validated, holdout-passing edges). Demote EQUITY per MUTATION_THREE_AXIS_PROTOCOL.md (mutate the mean_reversion S40 path immediately; it is the clearest leakage recurrence). All other classes have no actionable edge.
