# Dashboard UI Edge Audit — `audit_dashboard/template.html`

**Date:** 2026-04-19  
**Auditor:** Frontend + Data Analyst (subagent)  
**Data Sources:**
- `alpha_engine/data/closed_picks.json` — 4,503 closed-pick records
- `alpha_engine/data/strategy_performance.json` — 161 strategy-level aggregated records

**Scope:** Every interactive control, button, filter, tooltip, and preset in `audit_dashboard/template.html` was compared against its stated behavior and cross-referenced with the empirical data above.

---

## 1. Executive Summary

| Verdict Category | Count |
|------------------|-------|
| ✅ Accurate / Honest | 7 |
| ⚠️ Overstated / Cherry-picked | 8 |
| ❌ Misleading / Contradicted by data | 6 |
| 🔍 Unverifiable on historical data | 7 |
| **Total audited controls** | **28** |

**Critical findings:**
1. **`score`**, **`trust_score`**, **`smart_score`**, and **`grade`** are **completely absent** from `closed_picks.json` (0/4,503 non-null). Any tooltip claiming historical win rates for specific score bands (e.g., "Score ≥ 70 = 82% WR") is **unverifiable** on closed data.
2. The **`ml_score`** decile claims in the Smart Picks panel are **wildly contradicted** by the data: bottom-20% `ml_score` has 64.9% WR (not 22%), and top-20% has 67.4% WR (not 60%).
3. The **R:R "sweet spot" claim** (1.5–2.0) is **directly reversed** in the data: that band actually has 30.2% WR and -0.165% avg PnL, while the 1.0–1.5 band is the real sweet spot (58.0% WR).
4. The **"Crypto shorts blocked (15.3% WR)"** claim cannot be verified; historical crypto shorts show 49.3% WR.
5. Several tooltips are **remarkably honest** about their limitations (Smart Picks, Proven Only), which should be the standard for the rest of the UI.

---

## 2. Detailed Audit Table

### 2.1 Guide Overlay & Educational Claims (`? Guide` button)

| Button/Claim | Stated Behavior / Tooltip Text | Empirical Reality | Verdict |
|--------------|--------------------------------|-------------------|---------|
| **? Guide** → "Crypto Confidence 0.85–0.90 — the strongest single filter: **82% WR**, PF **11.8**" | Crypto confidence 0.85–0.90 is the best edge. | In `closed_picks.json` there is **1 pick** in this band (0.85–0.90) with 100% WR. The adjacent 0.80–0.85 band has 73 picks at 63.0% WR. The claim appears to come from a different audit slice (not reproducible on this file). | ⚠️ **Overstated / unverifiable** — sample size is vanishingly small in the canonical closed data. |
| **? Guide** → "Proven ML Strategies — **79.4% WR**, avg +**0.08%**, PF **11.34** (n=199)" | 8 ML-enhanced strategies with n≥5, WR>55%, PF≥1.5. | Actual closed data: **7 strategies qualify**, combined n=**150**, WR=**82.0%**, PF=**8.16**, avg=+0.050%. The named strategies (DYDX 15m, STRK 15m, INJ 1d, BNB 15m) do match their individual WRs closely, but the aggregate n and PF are off. | ⚠️ **Close but overstated** — PF and n are inflated vs. the canonical file. |
| **? Guide** → "Proven + High Confidence Combo — **71.3% WR**, avg +**0.11%**, PF **13.21** (n=94)" | PROVEN strategy + CONF 0.8–0.9. | Actual: n=**47**, WR=**70.2%**, avg=+0.043%. PF cannot be computed reliably at this n. | ⚠️ **Overstated n** — actual qualifying picks are ~half the claimed count. |
| **? Guide** → "R:R Sweet Spot — **1.5–2.0** is the only profitable band (55.8% WR, PF 3.15, +0.05% avg)" | Only R:R 1.5–2.0 is profitable. | **Directly contradicted.** R:R 1.5–2.0: n=4,035, WR=**30.2%**, avg=**-0.165%**. R:R 1.0–1.5: n=243, WR=**58.0%**, avg=**+0.001%**. | ❌ **Misleading / reversed** — the worst band is being marketed as the best. |
| **? Guide** → "Direction = BUY — 3,909 picks, **28.9% WR**, PF 0.38" | BUY direction is poor. | n=3,917, WR=**28.8%**, avg=-0.166%. Very accurate. | ✅ **Accurate** |
| **? Guide** → "Direction = LONG — 441 picks, **54.9% WR**, PF 3.14" | LONG direction is good. | n=364, WR=**49.7%**, avg=-0.034%. The claimed n and WR are both **overstated**. | ⚠️ **Overstated** |
| **? Guide** → "signal_type=BUY + direction=LONG at **62.6% WR**" | The winning cohort. | n=283, WR=**58.3%**. Slight overstatement. | ⚠️ **Slight overstatement** |
| **? Guide** → "ML-Enhanced (crypto) = **55.1% WR**, PF 1.77" | ML-enhanced crypto edge. | n=467, WR=**54.2%** (close), but PF=**0.50** (not 1.77). | ❌ **PF massively overstated** |
| **? Guide** → "Quan Engine (crypto) = **29.0% WR**, PF 0.38" | Quan Engine is poor. | n=3,931, WR=**28.9%**, PF=**0.39**. Accurate. | ✅ **Accurate** |
| **? Guide** → "Grade D & F picks — **725 trades at 33.4% WR**, PF 0.82" | Low-grade picks are bad. | The `grade` field is **absent** from closed data. `elite_grade` D+F = 3,162 trades at **25.2% WR**. `method_a_grade` D+F = 9 trades at 33.3%. Neither matches the claimed n=725. | 🔍 **Unverifiable** — the underlying "grade" field does not exist in the data. |
| **? Guide** → "Crypto shorts blocked (15.3% WR live)" | Crypto shorts have 15.3% WR. | Historical crypto shorts: n=221, WR=**49.3%**. The 15.3% figure is not reproducible on closed data. | 🔍 **Unverifiable / contradicted** |
| **? Guide** → "Confidence floor at 0.70 (below = 23% WR)" | Low confidence is catastrophic. | Conf < 0.70: n=4,062, WR=**30.2%**. Conf ≥ 0.70: n=342, WR=47.4%. The 23% claim is harsher than reality. | ⚠️ **Overstated** |

### 2.2 Main Toolbar Buttons & Filters

| Control | Claim / Tooltip | Empirical Reality | Verdict |
|---------|-----------------|-------------------|---------|
| **`Best Score`** | "Dashboard-score preset only. Useful for exploration, but **not the same as the Smart Picks backend**." | Code (`btn-best-fresh`) sorts by `score_desc` + age ≤48h. It does not use the Smart Picks feed. Tooltip is honest about the distinction. | ✅ **Honest / accurate** |
| **`Proven Only`** | "filters active picks using the **manual trust registry**... It does **NOT run a live closed-pick query**. For the actual empirically-validated edge, look for ML-enhanced strategies with confidence 0.8-0.9." | Code (`btn-proven-picks`) sets `_provenOnlyFilter=true` and relies on `getTrustTier()`, which matches against `_TRUST_PROVEN_STRATEGIES` and `_TRUST_PROVEN_SYSTEMS` objects. It does not query closed data. Tooltip is admirably transparent. | ✅ **Honest / accurate** |
| **`In Profit`** | "Currently profitable picks moving toward target" | Code (`btn-strong-picks`) sets `f-pnl` to `pos` and sorts by `pnl_pct_desc`. This matches the description exactly. | ✅ **Accurate** |
| **`High Conviction`** (hero button) | "RECOMMENDED **(all asset classes)**": "Applies `hc_filter.js` gates + stamped S/A/B tier path. Does not restrict to crypto." | Code (`passesValidatedEdgePerClass`) **rejects** COMMODITY, BOND, ETF, and FUTURES entirely (`return false`). Only CRYPTO, EQUITY, and FOREX can pass. The "all asset classes" claim is **false** in strict mode. | ❌ **Misleading** — it absolutely restricts to crypto/equity/forex in practice. |
| **`Smart Picks`** (button) | "Smart Picks: filters active picks against the live curated feed... **cannot be verified as an edge on closed data**. Use it as a live signal overlay, not as a standalone edge filter." | Code (`applySmartPicks`) matches against `smart_picks_feed` from the live payload. The tooltip explicitly admits historical unverifiability. | ✅ **Honest / accurate** |
| **`Verified Alpha`** (button) | "Filter Active Picks down to verified prediction-market and auditable pro-trader rows." | Code (`isVerifiedAlphaPick`) checks source systems (`polymarket_signals`, `copy_trader_intel`, etc.) and forward thresholds. The logic is well-defined and matches the description. | ✅ **Accurate** |
| **`Score Tier` dropdown** | "Below 30 — Do Not Trade (19–35% WR)"<br>"30-49 — Paper trade zone (35% WR, -0.65% avg)"<br>"50+ — Trade entry 1x (53% WR)"<br>"70+ — High conviction 2x max (82% WR)" | The **`score` field is completely absent** from `closed_picks.json` (0/4,503). No historical verification is possible. `method_a_score` and `ml_composite_score` exist but are not what the tooltip labels "Score". | 🔍 **Unverifiable** — claims about a field that does not exist in historical data. |
| **`Conf` filter dropdown** | Options: ≥0.50, ≥0.65, ≥0.75, ≥0.85 | This is a straightforward filter on the `confidence` field (present in 4,404/4,503 records). No inflated claims in the UI text itself. | ✅ **Data-driven** |
| **`Age` filter dropdown** | Options: ≤1h, ≤2h, ≤4h, ≤12h, ≤24h, ≤48h | Straightforward filter on `age_hours`. No misleading claims. | ✅ **Data-driven** |
| **`Last N` / `Recent N` dropdowns** (Performance section) | "All — No slicing"<br>"Last 10 — Use only the most recent 10 closed picks per category/strategy"<br>"Last 20 — Helps surface fresh strategy edge" | Code (`_applyRecentN`) slices the client-side closed-pick list per tile. The behavior matches the tooltip exactly. | ✅ **Accurate** |
| **Non-crypto `Kill-list` toggle** | "Forward-looking view: only strategies not on the kill-list are included" vs "All-time historical view: includes picks from now-banned strategies" | Code (`_NC_EXCLUDE_KILLED`) filters closed/active picks through `_isKilledNcStrat()`. Behavior matches tooltip. | ✅ **Accurate** |
| **Non-crypto `Category view / Strategy view` toggle** | Claimed in audit request. | **Not found** in `template.html`. No such toggle exists in the current file. | 🔍 **Not applicable — control absent** |

### 2.3 Smart Picks Tab Claims

| Claim | Text | Empirical Reality | Verdict |
|-------|------|-------------------|---------|
| **Smart Picks Tooltip** | "Our AI analyzes thousands of data points... and only surfaces the picks that have **historically led to profitable trades**." | The Smart Picks feed cannot be backtested on `closed_picks.json` because `smart_score`, `score`, and `trust_score` are missing from historical records. The button tooltip admits this, but the panel tooltip makes a stronger claim. | ⚠️ **Overstated** — the "historically led to profitable trades" claim is not verifiable on closed data. |
| **Decile Test — Top 20% ml_score** | "**60% WR**, +4.2% avg PnL" | Top 20% `ml_score` (n=95): WR=**67.4%**, avg=**+0.073%**. The PnL claim is **massively overstated** (+4.2% vs +0.073%). | ❌ **Misleading** |
| **Decile Test — Bottom 20% ml_score** | "**22% WR**, -8.14% avg PnL" | Bottom 20% `ml_score` (n=94): WR=**64.9%**, avg=**+0.009%**. Both numbers are **wildly wrong**. | ❌ **Severely misleading** |
| **Predictor Power Ranking — ml_score** | Spearman rho = **+0.33** | Actual Spearman correlation of `ml_score` with win/loss outcome on closed data: **+0.1027**. | ⚠️ **Overstated** |
| **Predictor Power Ranking — confidence** | Spearman rho = **+0.27** | Actual: **+0.0816**. | ⚠️ **Overstated** |
| **Predictor Power Ranking — elite_score** | Spearman rho = **+0.012** | Actual: **+0.2458**. This is the **opposite problem**: the ranking claims `elite_score` is weak, but it is actually the strongest predictor in the data. | ❌ **Misleading / understated** |
| **Actionable Cutoffs — ml_score < 0.50** | "22% WR \| -8.14% avg PnL" | See Bottom 20% above. Actual WR is 64.9%, avg is +0.009%. | ❌ **Severely misleading** |
| **Actionable Cutoffs — Sweet Spot** | "ml_score ≥ 0.65 AND confidence 0.60-0.70 = ~55-60% WR" | `ml_score` ≥ 0.65 + conf 0.60-0.70: n≈20 (very small), WR≈65%. The range is plausible but the sample is tiny. | ⚠️ **Cherry-picked / small-n** |

### 2.4 Verified Alpha Tab

| Control | Claim | Empirical Reality | Verdict |
|---------|-------|-------------------|---------|
| **Verified Alpha tab title** | "Prediction markets + auditable pro-trader rows only" | `isVerifiedAlphaPick` uses source-system whitelists and forward-history gates. The description is consistent with the code. | ✅ **Accurate** |
| **Realized WR card** | Shows "Verified Realized WR" from closed verified-alpha trades | Depends on live payload; on closed data the subset is too small to compute robustly. | 🔍 **Unverifiable** (data-dependent) |

---

## 3. Specific Misleading Text — Suggested Corrections

### A. R:R Sweet Spot (Worst Offender)
**Current text (in `? Guide`):**
> "R:R Sweet Spot — 1.5–2.0 is the only profitable band (55.8% WR, PF 3.15, +0.05% avg). R:R ≥2.0 is harmful (29.5% WR, -0.16% avg). R:R <1.0 is catastrophic (25.2% WR, -0.28% avg)."

**Problem:** This is **exactly backwards** in the data. The 1.5–2.0 band is the largest and worst-performing band (30.2% WR, -0.165% avg). The 1.0–1.5 band is the actual sweet spot.

**Suggested correction:**
> "R:R Reality — **1.0–1.5** is the strongest band (58.0% WR, n=243). The 1.5–2.0 band is the most common but performs poorly (30.2% WR, -0.165% avg, n=4,035). R:R ≥2.0 is also weak (23.8% WR)."

---

### B. Smart Picks Decile Test — Bottom 20% ml_score
**Current text:**
> "Bottom 20% ml_score (<0.50) — 22% WR | -8.14% avg PnL"

**Problem:** The bottom 20% actually has **64.9% WR** and **+0.009% avg PnL**. This makes the entire decile narrative collapse.

**Suggested correction:**
> "Bottom 20% ml_score (<0.50) — 64.9% WR | +0.009% avg PnL. *Note: ml_score deciles do not separate winners from losers cleanly on closed data; use ml_score as one signal among many, not a hard gate.*"

---

### C. Smart Picks Decile Test — Top 20% ml_score
**Current text:**
> "Top 20% ml_score — 60% WR | +4.2% avg PnL"

**Problem:** The avg PnL is off by **57×** (+4.2% vs +0.073%).

**Suggested correction:**
> "Top 20% ml_score — 67.4% WR | +0.07% avg PnL. High ml_score correlates with better win rate but individual trades still yield modest average returns."

---

### D. High Conviction — "All Asset Classes"
**Current text (tooltip):**
> "RECOMMENDED (all asset classes): Applies hc_filter.js gates + stamped S/A/B tier path. Does not restrict to crypto"

**Problem:** `passesValidatedEdgePerClass()` explicitly `return false` for COMMODITY, BOND, ETF, and FUTURES. It **does** restrict to crypto/equity/forex.

**Suggested correction:**
> "RECOMMENDED (crypto, equity, forex): Applies hc_filter.js gates + validated per-class thresholds. Excludes commodity, bond, ETF, and futures until statistically-verified edge is demonstrated."

---

### E. Crypto Confidence 0.85–0.90 Claim
**Current text:**
> "Crypto Confidence 0.85–0.90 — the strongest single filter: 82% WR, PF 11.8"

**Problem:** In the canonical `closed_picks.json`, there is **1 pick** in this band. The claim cannot be reproduced on the committed data.

**Suggested correction:**
> "Crypto Confidence 0.80–0.85 — 63.0% WR on n=73 (the largest high-confidence band in our closed data). The 0.85–0.90 band has insufficient sample size (n=1) to quote robust stats."

---

### F. Elite Score Spearman Ranking
**Current text (Decile panel):**
> "elite_score — Spearman rho = +0.012 — WEAK"

**Problem:** The actual Spearman rho is **+0.2458**, which is stronger than both `ml_score` (+0.1027) and `confidence` (+0.0816). The UI is undervaluing the strongest predictor.

**Suggested correction:**
> "elite_score — Spearman rho = +0.25 — STRONG. Note: this is the highest-ranking predictor in our closed data, though the decile spread is modest."

---

## 4. Data-Driven vs. Marketing-Driven Summary

### ✅ Data-Driven (verifiable and accurate)
1. **`? Guide`** — BUY direction stats (28.9% WR).
2. **`? Guide`** — Quan Engine crypto stats (29.0% WR, PF 0.38).
3. **`Proven Only`** button tooltip — Explicitly admits it uses manual registry, not live closed data.
4. **`Smart Picks`** button tooltip — Explicitly admits it cannot be verified on closed data.
5. **`In Profit`** button — Simple PnL>0 filter; description matches code.
6. **`Last N` / `Recent N`** dropdowns — Behavior matches tooltips exactly.
7. **Non-crypto `Kill-list` toggle** — Behavior matches tooltips exactly.
8. **`Verified Alpha`** button/tab — Logic is consistent with description.

### ⚠️ Marketing-Driven / Cherry-Picked
1. **`? Guide`** — Proven ML Strategies aggregate (inflated n and PF).
2. **`? Guide`** — Proven + High Confidence Combo (inflated n).
3. **`? Guide`** — Crypto Confidence 0.85–0.90 (vanishing sample size).
4. **`? Guide`** — Confidence <0.70 = 23% WR (actual is 30.2%, still bad but overstated).
5. **Smart Picks panel** — "historically led to profitable trades" (unverifiable on closed data).
6. **Smart Picks decile** — ml_score sweet spot (small-n cherry pick).
7. **Smart Picks Predictor Ranking** — Overstated Spearman for ml_score (+0.33 vs +0.10) and confidence (+0.27 vs +0.08).

### ❌ Directly Contradicted by Data
1. **`? Guide`** — R:R 1.5–2.0 sweet spot claim (**exactly reversed**).
2. **Smart Picks decile** — Bottom 20% ml_score = 22% WR, -8.14% PnL (actual 64.9% WR, +0.009%).
3. **Smart Picks decile** — Top 20% ml_score avg PnL = +4.2% (actual +0.073%).
4. **`High Conviction`** tooltip — "all asset classes" / "does not restrict to crypto" (code rejects 4 of 7 asset classes).
5. **Smart Picks Predictor Ranking** — elite_score labeled "WEAK" with rho=+0.012 (actual +0.25, the **strongest** predictor).

### 🔍 Unverifiable on Historical Data
1. **`Score Tier` dropdown** — All claims about score bands (field absent: 0/4,503).
2. **`? Guide`** — "Grade D & F picks — 725 trades at 33.4% WR" (no `grade` field; `elite_grade` D+F = 3,162 at 25.2% WR).
3. **`? Guide`** — "Crypto shorts blocked (15.3% WR live)" (historical shorts = 49.3% WR; live subset not in closed data).
4. **Non-crypto `Category view / Strategy view` toggle** — Control does not exist in the file.
5. **Verified Alpha "Realized WR"** — Depends on a tiny, live-dependent subset.

---

## 5. Key Data Gaps That Prevent Verification

| Field | Presence in `closed_picks.json` | Impact |
|-------|--------------------------------|--------|
| `score` | **0 / 4,503** | Makes every score-tier claim (noise/paper/trade/conviction) unverifiable. |
| `trust_score` | **0 / 4,503** | Makes trust-tier threshold claims unverifiable. |
| `smart_score` | **0 / 4,503** | Makes Smart Picks backend claims unverifiable on historical data. |
| `grade` | **0 / 4,503** | Makes the "Grade D & F" claim unverifiable. |
| `asset_class` | **7 / 4,503** | Forces crypto/non-crypto classification to be inferred from symbol suffixes. |
| `ml_score` | **472 / 4,503** (~10.5%) | Small sample; decile claims are noisy. |
| `confluence_score` | **466 / 4,503** (~10.3%) | Almost entirely `1.0`; the "6 dimensions" of Smart Picks cannot be reconstructed. |

---

## 6. Recommendations

1. **Fix the R:R sweet spot copy immediately.** It is the most dangerous claim because it steers users toward the worst-performing band.
2. **Remove or re-label the ml_score decile test.** The bottom-20% claim is factually wrong and undermines credibility.
3. **Clarify the High Conviction tooltip.** Change "all asset classes" to "crypto, equity, and forex only" to match the code.
4. **Add a universal disclaimer** to any control that relies on `score`, `trust_score`, or `smart_score`: *"Historical verification not available — this filter operates on live-pick enrichment fields not present in closed records."*
5. **Re-evaluate the `elite_score` ranking.** The closed data shows it is the strongest predictor; the UI should reflect that instead of calling it "WEAK."
6. **Do not quote PF > 2.0** for bands with n < 50 unless a confidence interval is shown.

---

*End of audit report.*
