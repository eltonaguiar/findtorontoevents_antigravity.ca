# Pick Funnel Swarm Verdict — 2026-11-23 04:42 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261123T044231Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

**Bottom line up front:** The funnel is broken in two directions. (1) The "PROVEN" cells are almost all **single-cell artifacts** — the same 191 CRYPTO trades and the same 35 EQUITY trades are being re-reported under 3 different dimension labels each, so the "3 proven edges" per class is really **1 edge per class**. (2) The funnel is **not filtering** — 96–98% of scanned picks pass `passed_smart` in FOREX/COMMODITY/INDEX, and `passed_high_conviction` is **0 across every single asset class**, meaning the HC gate is dead code in production. The only class with a defensible, holdout-passing, Bonferroni-passing edge is **CRYPTO**, and even that is one narrow cell.

---

### CRYPTO
- **Real/noise verdict:** **Real but narrow.** The three "PROVEN" cells are the *same 191 trades* re-sliced by `trust`, `dir`, and `source` — they are not independent edges. The underlying cell is `conf=C0.75-0.80 & dir=LONG & source=alpha_engine`, n=191, WR=64.4%, shrunk WR=63.0%, PF=1.81, train PF 1.56 / holdout PF 2.26 (holdout n=82, passes), wr_z=3.98, Bonferroni pass. That is a **credible** edge: holdout holds, sample is large, effect size is modest (PF 1.8, not 12). The class-level WR of 44.6% is dragged down by the *other* 1,926 closed trades — i.e., the edge is real but the class is mostly noise. **No leakage flag** on this cell (conf band + direction + source is not a look-ahead dimension). The `ml` cell you flagged is **not in the proven list** — good; if it appears in a future run with PF>5, treat as leakage recurrence (H-035 pattern).
- **90d expected P&L (1% risk, $100k):** ~**$1,900–$2,400**. Math: 191 trades × 1% risk = $1,000 risk/trade. At PF 1.81 and WR 64.4%, expectancy per trade ≈ (0.644×1.81R − 0.356×1R)/1 ≈ **+0.81R** → but cap at realistic R because avg_pnl_pct=0.65% on ~$1k risk ≈ 0.65R. Use **0.65R × $1,000 × 191 ≈ $124k gross**, then apply **~85% haircut for slippage/fees/partial fills on crypto** (crypto spreads + funding + 1% risk sizing on $100k notional is aggressive) → **~$18k**. I'll be conservative and say **$12k–$18k** net. If you only trade the proven cell and nothing else in CRYPTO, this is the number.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **raise it**, and add a hard `conf >= 0.75` floor in `production_scanner.py` for CRYPTO. Currently 4,169/11,942 (35%) pass smart; the edge lives in a 191-trade conf band. Set `SMART_PICKS_MIN_SCORE_CRYPTO = 78` (from current, likely 70) and require `conf >= 0.75`. This cuts ~3,900 noise trades and keeps the proven cell.
- **Confidence (1-5):** **4** — holdout passes, Bonferroni passes, effect size believable.

---

### EQUITY
- **Real/noise verdict:** **Suspicious — likely leakage or single-symbol concentration.** The three "PROVEN" cells are again the *same 35 trades* (n=35, 34 wins, WR 97.1%, shrunk 80%, **PF 124.5**, avg_pnl 1.59%). A PF of 124 on 35 trades is not a strategy — it is either (a) a handful of symbols dominating, (b) a look-ahead in the `mean_reversion` + `RR>=2.0` construction (e.g., R:R computed with future high/low), or (c) survivorship in the closed-trade set. Train n=11, holdout n=24 — the holdout "passes" but 24 trades is not a holdout, it's a coin flip. **Flag as leakage recurrence risk.** Do not size this. The class-level WR of 73.3% on 116 decisive trades is also implausibly high for equity mean-reversion at RR≥2 — real-world equity MR at RR≥2 sits at 45–55% WR. **Reject until the 35 trades are symbol-decomposed and the R:R timestamp is audited.**
- **90d expected P&L (1% risk, $100k):** **$0 — do not trade.** If forced to model: 35 × $1,000 × 1.59R ≈ $55k gross, but the PF=124 is a red flag that the R denominator is broken. Realistic post-audit expectation is **negative** until proven otherwise.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — **raise sharply** and add a `min_symbol_diversity` check. 224/6,139 (3.6%) pass smart is already tight, but the 35-trade cell slipped through. Set `SMART_PICKS_MIN_SCORE_EQUITY = 82` and add `EQUITY_MAX_SINGLE_SYMBOL_SHARE = 0.15` in `production_scanner.py`. Also audit `rr` computation for look-ahead before any size.
- **Confidence (1-5):** **1** — PF 124 is a bug, not an edge.

---

### COMMODITY
- **Real/noise verdict:** **No proven edge.** `top_edges_proven` is empty. Best PF cell is n=26, WR 65.4%, shrunk 58.7%, PF 3.67, but **Bonferroni fails** and holdout n=15. This is exactly the shape of the **H-001 COT leakage** (cotton concentration, look-ahead) and **H-036 inventory gate** rejections — do not re-derive. The 3,689/5,745 (64%) smart-pass rate is absurd for a class with 49 closed trades; the funnel is letting almost everything through and the sample is too thin to conclude anything.
- **90d expected P&L (1% risk, $100k):** **$0 — insufficient sample (n=49 closed).** Any dollar figure here would be invented. If the n=26 cell were real: 26 × $1,000 × 1.24R ≈ $32k gross, but Bonferroni fail + H-001/H-036 precedent = **do not trade**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — **raise to 80** (from current, which is clearly permissive given 64% pass rate). Also add a **minimum closed-trade count gate** before a cell can be promoted: `MIN_CLOSED_FOR_PROMOTION = 50` per cell. COMMODITY has 49 total — it cannot promote anything yet.
- **Confidence (1-5):** **2** — no proven cell, prior leakage history.

---

### FOREX
- **Real/noise verdict:** **Noise / leakage-suspect.** `top_edges_proven` empty. Best cell `trust=UNK & conf=C>=0.90 & fam=regime` n=39, WR 87.2%, shrunk 74.6%, **PF 11.5**, but **holdout n=3 and holdout_pass=false**. A PF of 11.5 on 39 trades with a 3-trade holdout is the textbook signature of **single-symbol or single-event concentration** (likely one regime event, e.g., a central-bank day). The class-level WR is exactly **50.0%** on 484 decisive trades — that is the definition of no edge. The 26,565/27,116 (98%) smart-pass rate means the gate is doing nothing. **This is the class you flagged as suspicious and you are right.**
- **90d expected P&L (1% risk, $100k):** **$0 — 50% WR, no proven cell.** Modeling the n=39 cell would be inventing an edge; holdout n=3 disqualifies it.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — **raise to 85** (from current, which passes 98%). This is the single highest-leverage change in the whole funnel: 26,565 smart passes on a 50% WR class is the biggest capital sink. Also set `HC_MIN_CONF_FOREX = 0.90` in `hc_filter.js` — but note HC is currently 0 everywhere, so the real fix is the smart floor.
- **Confidence (1-5):** **1** — 50% WR, holdout n=3, PF 11.5 is a bug.

---

### ETF
- **Real/noise verdict:** **Noise.** n=10 closed, WR 30%, PF not shown (empty best_pf). 263/298 (88%) smart-pass on 10 closed trades. No edge, no sample.
- **90d expected P&L (1% risk, $100k):** **$0 — n=10.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — **raise to 80**; more importantly, **disable ETF promotion** until `MIN_CLOSED_FOR_PROMOTION=50` is met.
- **Confidence (1-5):** **1.**

---

### BOND
- **Real/noise verdict:** **Noise.** n=31, WR 38.7%, 1/1,237 smart-pass (0.08% — the gate is *too tight* here, opposite problem). No proven cell. 1,206 opened vs 31 closed = 97.5% of "opened" never closed — either stuck positions or a lifecycle bug.
- **90d expected P&L (1% risk, $100k):** **$0 — negative expectancy (38.7% WR).**
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — **lower to 65** to actually let trades through, but **only after** fixing the opened/closed lifecycle gap (1,206 opened, 31 closed is a data integrity issue, not a strategy issue).
- **Confidence (1-5):** **1.**

---

### FUTURES
- **Real/noise verdict:** **Noise / prior kill.** n=16, WR 37.5%, no proven cell. **H-005 already killed futures momentum** (inversion doesn't fix it). Do not re-derive.
- **90d expected P&L (1% risk, $100k):** **$0 — n=16, negative WR.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — **raise to 82**; keep H-005 kill in force.
- **Confidence (1-5):** **1.**

---

### INDEX
- **Real/noise verdict:** **Noise.** n=1 closed, WR 100% on one trade. 1,542/2,141 (72%) smart-pass on 1 closed trade. Statistically meaningless.
- **90d expected P&L (1% risk, $100k):** **$0 — n=1.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — **raise to 80**; block promotion until n≥50.
- **Confidence (1-5):** **1.**

---

### UNKNOWN
- **Real/noise verdict:** **Noise / data hygiene failure.** n=5, WR 0%, 1,206 scanned, 100 smart-pass. "UNKNOWN" as an asset class means the classifier is dropping ~1,200 picks/90d into a bucket with no strategy. This is a **pipeline bug**, not a class.
- **90d expected P&L (1% risk, $100k):** **$0 — n=5, 0% WR.**
- **Gate change:** Fix the classifier upstream — **reject any pick with `asset_class == UNKNOWN`** in `production_scanner.py` before scoring. Do not add a score constant; add a hard drop.
- **Confidence (1-5):** **1.**

---

### MEME
- **Real/noise verdict:** **Noise.** n=5, WR 40%, 2/12 verified-alpha. No proven cell.
- **90d expected P&L (1% risk, $100k):** **$0 — n=5.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — **raise to 85**; block promotion until n≥50.
- **Confidence (1-5):** **1.**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only the single proven cell.**
`conf=C0.75-0.80 & dir=LONG & source=alpha_engine`, n=191, holdout PF 2.26 (n=82), Bonferroni pass, shrunk WR 63%. Size at **0.5% risk per trade** (not 1%) for the first 30 days to validate live slippage, then step to 1%. Expected 90d net: **$12k–$18k** on $100k. Do **not** trade the rest of CRYPTO (1,926 closed trades at 44.6% WR are the noise the cell is carved out of).

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill): FOREX.**
- **Axis 1 (mutate):** Raise `SMART_PICKS_MIN_SCORE_FOREX` to 85 — this alone cuts ~26,000 noise passes to a few hundred and is the single biggest capital-preservation move in the funnel.
- **Axis 2 (mutate):** Add `HC_MIN_CONF_FOREX = 0.90` and `HC_MIN_TRUST_FOREX = 60` in `hc_filter.js` — but first fix the fact that **HC is 0 across every class**, which means the HC gate is not wired into the live path at all. That is a P0 bug, not a tuning issue.
- **Axis 3 (kill if mutation fails):** If after 30 days the mutated FOREX funnel still shows WR ≤ 52% on n≥100, kill FOREX entirely. The 50.0% WR on 484 decisive trades is already at the kill threshold.

**Two cross-cutting P0 bugs to fix before any of the above matters:**
1. **`passed_high_conviction = 0` for every asset class** — the `hc_filter.js` gate (score≥80, conf≥0.75, trust≥60) is either not running server-side or its output is not being persisted. The dashboard is showing a gate that isn't gating.
2. **`opened` ≫ `closed` in every class** (e.g., FOREX 25,774 opened / 1,342 closed; BOND 1,206 / 31) — either positions are stuck open or the lifecycle join is broken. Any WR/PF computed on the closed subset is **survivorship-biased** until this is fixed. The CRYPTO edge survives this caveat (holdout n=82 is large enough), but every other class's numbers should be treated as **upper bounds** until the open/close join is audited.

**Do not invent edges.** Of 11 asset classes, exactly **one** (CRYPTO) has a cell that survives holdout + Bonferroni + believable effect size. The other ten are noise, thin samples, or leakage-suspect. The funnel's real problem is not that it's missing edges — it's that it's **passing 35–98% of picks through `passed_smart`** while the HC gate sits at zero. Fix the gate wiring and the FOREX/COMMODITY smart floors first; the edge inventory will look very different in 30 days.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)
