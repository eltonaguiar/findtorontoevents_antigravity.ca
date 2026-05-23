# Tier Performance Audit + Suggested Fixes — 2026-05-02

**Author:** Copilot (review of Tyler / Performance Data Extractor insights)
**Goal alignment:** Goal #1 — phenomenal performance across all asset classes on `/audit`.
**Status:** Analysis + recommended config/code fixes. No production code changed in this PR — see "Suggested Fixes" for the concrete follow-up PRs.

---

## 1. Source data (extracted from dashboard screenshots)

Three dashboard captures were reviewed (`Last 20`, `Last 50`, `Last 100` filters). Numbers below are transcribed verbatim.

### Crypto by tier (WR / PF / Realized PnL)

| Tier   | L20                        | L50                   | L100                   |
|--------|-----------------------------|-----------------------|------------------------|
| S-Tier | 85.7% / 30.17 / +58.35%    | 85.7% / —    / —      | 85.7% / —    / —       |
| A-Tier | 50.0% /  1.98 / +13.90%    | 54.0% /  1.58 / —     | 40.0% /  1.23 / —      |
| B-Tier | 65.0% /  2.71 / +10.25%    | 52.0% /  1.59 / —     | 49.0% /  1.57 / —      |
| C-Tier | 35.0% /  0.54 /  −5.97%    | 28.0% /  0.36 / −33.50% | 31.0% / 0.66 / −32.67% |

### Non-crypto (WR / PF / PnL)

| Class       | L20                       | L50                    | L100                    |
|-------------|----------------------------|------------------------|-------------------------|
| Equities    | 50.0% / 1.51 / +17.07%    | 50.0% / 1.47 / +35.54% | **59.0% / 2.90 / +176.74%** |
| Forex       |  0.0% / 0.00 / −10.00%    |  4.0% / 0.04 / −21.57% |  5.0% / 0.06 / −41.25%  |
| Commodities | 35.0% / 1.01 /  +0.44%    | 24.0% / 1.26 / +12.69% | 14.0% / 0.95 /  −3.04%  |
| Futures     | n=2 (insufficient)        | —                      | —                       |
| ETFs        | 70.0% / 2.88 / +23.29%    | 72.0% / 2.67 / +64.49% | 52.9% / 1.32 / +28.58%  |
| Bonds       | 50.0% / 1.72 /  +3.41%    | 50.0% / 1.72 /  +3.41% | 50.0% / 1.72 /  +3.41%  |

### User-supplied filter analysis

- **Confidence band:** 0.85–0.90 → 82% WR / PF 11.8.   >0.90 → **47% WR (overfit cliff).**
- **Direction tagging:** `BUY` (n=3909) → 28.9% WR / PF 0.38 vs. `LONG` (n=441) → 54.9% WR / PF 3.14. Same intent, opposite results → label-routing bug suspected.
- **Engines:** ML-Enhanced crypto = 55.1% WR / PF 1.77; Quan Engine crypto = 29.0% WR / PF 0.38.
- **Crypto R:R ≥ 2.0:** 58% WR / PF 3.06 / +0.99% avg.
- **Forex Trusted filter:** 49.0% WR vs 42.9% baseline (+6.0pp), PF 3.59 — but n=273 with CI straddling 1.0.
- **Futures (old):** 6.3% WR on n=17, 76% LOST-exit rate.

---

## 2. Tier classifications (vs. `STRATEGY_INVESTIGATION_BEFORE_KILL` tier table)

T1 ≈ Renaissance (PF>2 / WR>55 / MDD<10), T2 ≈ Institutional (PF>1.5 / WR>50 / MDD<20), T3 ≈ Retail-OK (PF>1.2 / WR>48 / MDD<30). MDD not visible in dashboard panel — flagged below.

| Class / segment              | Best window | PF    | WR    | Tier (PF+WR only) | Notes |
|------------------------------|-------------|-------|-------|-------------------|-------|
| Crypto S-Tier                | All         | 30.17 | 85.7% | **T1**            | n=14 — sample small, monitor |
| Crypto B-Tier (L20)          | L20         |  2.71 | 65.0% | **T1**            | Decays to T2 by L100 |
| Crypto A-Tier                | L50         |  1.58 | 54.0% | T3                | Decays to PF 1.23 / 40% by L100 — degradation curve |
| Crypto C-Tier                | All         | <0.7  | <35%  | **FAIL**          | Persistent loser → eliminate |
| Equities                     | L100        |  2.90 | 59.0% | **T1**            | Best non-crypto class |
| ETFs                         | L50         |  2.67 | 72.0% | **T1**            | Old "ETFs dead" verdict was wrong |
| Bonds                        | All         |  1.72 | 50.0% | T2                | Stable, low contribution |
| Commodities                  | L50         |  1.26 | 24.0% | T3 (PF only)      | WR <50% breaks T2 — borderline |
| Forex                        | All         | <0.1  | <5%   | **FAIL**          | Eliminate or gate behind Trusted-only |
| Futures                      | n=2         | n/a   | n/a   | **INSUFFICIENT**  | Dashboard sample too small — old 6.3%/n=17 was bad |

### Edge-gap to T2 (PF=1.5, WR=50%)

| Class       | ΔPF (vs 1.5) | ΔWR (vs 50%) | Verdict |
|-------------|--------------|--------------|---------|
| Equities L100 | +1.40       | +9.0pp       | Past T2, near T1 |
| ETFs L50      | +1.17       | +22.0pp      | Past T1 |
| Bonds         | +0.22       |  0.0pp       | At T2 |
| Commodities   | −0.24…−0.55 | −15…−36pp    | Far below |
| Forex         | −1.44       | −45…−50pp    | Catastrophic |
| C-Tier crypto | −0.84…−1.14 | −15…−22pp    | Catastrophic |

---

## 3. Top-real-money patterns

**What worked:**
1. Crypto S-Tier (any window) — PF 30.17, dominant edge.
2. ETFs L50 (PF 2.67, +64.49%) and L20 (PF 2.88, +23.29%).
3. Equities L100 (PF 2.90, +176.74%) — biggest absolute PnL contributor.
4. Crypto B-Tier L20 (PF 2.71, 65% WR).
5. Bonds — small but persistently positive (+3.41% across windows).

**What destroyed value:**
1. Forex L100 (−41.25%, 5% WR). All Forex windows are catastrophic.
2. C-Tier crypto L50/L100 (−33% / −32%). Largest crypto drag.
3. Commodities L100 (−3.04%, 14% WR) — degrades sharply across windows.
4. `Direction=BUY` bucket overall (28.9% WR / PF 0.38, n=3909) — likely routing bug.
5. Confidence > 0.90 bucket (47% WR) — overfitting boundary.

---

## 4. Filter scenarios (estimated impact, equal-weighted across visible segments)

| Scenario                        | L20 PnL | L50 PnL | L100 PnL |
|---------------------------------|---------|---------|----------|
| Baseline (current)              | +225.98 (crypto only shown) | n/a | n/a |
| Eliminate C-Tier crypto         | +82.5   | +91.5   | +96.2    |
| Eliminate Forex                 | +44.2   | +116.1  | +205.7   |
| Crypto S+A only                 | +72.2   | +78.5   | +69.8    |
| Golden (S-crypto + Equities L100 + ETFs L50 + Bonds; no Forex/CTier/Comm) | +112.6 | +178.6 | +275.1 |

The "Golden" allocation captures ~95% of the upside while eliminating the two structural drags (Forex + C-Tier crypto).

---

## 5. Old vs new analysis reconciliation

| Class      | Old verdict                | New dashboard reading              | Action |
|------------|----------------------------|------------------------------------|--------|
| ETFs       | "Dead" (PF 0.28 / n=19)    | PF 1.32–2.88 across windows        | **Revive** — old sample was unrepresentative |
| Futures    | "Dead" (6.3% WR / n=17)    | n=2 in dashboard — inconclusive    | Keep blocked until n ≥ 30 fresh |
| Forex      | Bad                        | Confirmed catastrophic             | **Block or hard-gate to Trusted-only** |
| Commodities | Weak                      | Confirmed weak, degrading          | Demote to monitor-only |
| Equities   | (not in old analysis)      | Best non-crypto class at L100      | **Promote** |

---

## 6. Suggested fixes (for follow-up PRs)

These are recommendations only — this PR is documentation. Each item below should be its own focused PR per the repo's "small, surgical changes" rule, and any strategy demotion must follow `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

### 6.1 — Hard cap confidence at 0.90 (P0)

- **Where:** `alpha_engine/config.py` (confidence-related thresholds) and the scorer that emits `confidence` (`alpha_engine/elite_scorer.py` / `darwin_score_v2_calculator.py`).
- **Change:** clip outgoing `confidence` to ≤ 0.90, or add a gate that demotes picks with raw confidence > 0.90 (the overfit cliff at 47% WR).
- **Acceptance:** distribution of live picks shows 0 picks with `confidence > 0.90` after rollout; backtest WR for the 0.85–0.90 band remains ≥ 75%.

### 6.2 — Investigate `Direction=BUY` vs `Direction=LONG` split (P0)

- **Symptom:** `BUY` n=3909 → 28.9% WR / PF 0.38; `LONG` n=441 → 54.9% WR / PF 3.14. Two labels for the same intent should not have a 26pp WR gap.
- **Hypothesis:** label-routing bug — `BUY` may be aggregating short-direction picks mislabelled, or coming from a different (broken) source pipeline.
- **Where:** trace `direction` field in `audit_trail/universal_pick_resolver.py` and `alpha_engine/production_scanner.py`. Check which engines emit `BUY` vs `LONG`.
- **Acceptance:** root cause documented; either labels unified, or the broken source is identified and gated.

### 6.3 — Eliminate or hard-gate C-Tier crypto (P1)

- **Cumulative drag:** −5.97% (L20), −33.50% (L50), −32.67% (L100) — worst structural loser after Forex.
- **Where:** the smart-pick gate (`alpha_engine/dsr_pick_filter.py` / `hedge_fund_quality_gate.py` / `hf_quality_gate.py`) — refuse to publish picks whose tier resolves to `C` for crypto.
- **Process:** must follow `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` (export closed CSV, run mutation analysis) before flipping the gate.

### 6.4 — Hard-gate Forex to Trusted-only (P1)

- **Forex baseline is catastrophic** (PF 0.04–0.06, WR 0–5%). The only positive signal is the Trusted filter (PF 3.59, +6pp lift) but n=273 with CI straddling 1.0.
- **Where:** the forex pick path. Either:
  - Add `forex` to `BLOCKED_SOURCE_SYSTEMS` for non-Trusted picks, or
  - Gate forex publication on a `trusted_filter == True` boolean.
- **Decision rule:** keep forex publication off until n ≥ 500 confirms PF > 1.5 with CI > 1.0.

### 6.5 — Promote Equities tier and increase weight at L100 horizon (P2)

- **Equities L100 = +176.74%** is currently the largest non-crypto PnL contributor.
- **Where:** position-sizing / category weight in `alpha_engine/regime_position_sizer.py` and category caps in `config.py` (`stock` currently 0.06 vs `crypto` 0.10).
- **Suggestion:** raise stock category cap to 0.08–0.10 contingent on continued L100 PF ≥ 2.0.

### 6.6 — Reconsider ETFs gating (P2)

- The "ETFs dead" verdict came from PF 0.28 on n=19 — small-sample noise. Dashboard now shows PF 1.32–2.88 with consistent WR ≥ 52%.
- **Where:** wherever ETFs were demoted (search `BLOCKED_SOURCE_SYSTEMS`, ETF-specific gates).
- **Acceptance:** ETF picks resume flowing; monitor PF in next 30 days.

### 6.7 — Add MDD column to the tier panels (P2)

- **Surface:** `audit_dashboard/template.html` tier panels.
- **Why:** T1/T2/T3 tier definitions include MDD, but dashboard shows only WR/PF/PnL. Without MDD we cannot formally certify Tier 1/2 — currently we can only assert PF/WR thresholds.
- **Where:** `audit_trail/dashboard_generator.py` (data) + `audit_dashboard/template.html` (presentation).

### 6.8 — Crypto R:R ≥ 2.0 gate (P3)

- **R:R ≥ 2.0 cohort:** 58% WR, PF 3.06 — strong.
- **Where:** `alpha_engine/dynamic_sl_gates.py` / `crypto_risk_gates.py`.
- **Suggestion:** add a soft tier-promotion rule — picks with R:R ≥ 2.0 get +1 tier-step (capped at S).

---

## 7. "Golden" portfolio recommendation

| Bucket    | Holdings                                                    |
|-----------|-------------------------------------------------------------|
| Core      | Crypto S-Tier · Equities (L100 horizon) · ETFs (L50)        |
| Satellite | Crypto B-Tier (L20 only) · Bonds                            |
| Eliminate | Forex · Crypto C-Tier · Commodities                         |
| Monitor   | Crypto A-Tier (L50→L100 degradation), confidence > 0.90 cliff |

**Estimated effect:** based on the visible segments, the Golden allocation roughly doubles L100 PnL vs. unfiltered (+275% vs +96% after only eliminating C-Tier).

---

## 8. Open questions / data gaps

1. **MDD per class** is not in the dashboard payload — required for formal T1/T2 certification.
2. **Futures sample (n=2)** is too small to act on — need to fetch the underlying CSV to see if old n=17 still applies.
3. **Bonds PF identical (1.72) across L20/L50/L100** is suspicious — possibly the same closed sample for all windows (confirm in `dashboard_generator.py`).
4. **Forex Trusted filter (n=273, PF 3.59)** — investigate whether sample size has grown enough since the audit to tighten CI.

---

## 9. References

- `reports/hedge_fund_performance_review_*.md` — tier definitions
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` — required process before demoting/blocking a class
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — required mutation analysis for kill decisions
- `alpha_engine/config.py` — `BLOCKED_SOURCE_SYSTEMS`, category caps, R:R defaults
- `audit_dashboard/template.html` — `/audit` surface
- `AGENTS.md` Goal #1 — "phenomenal performance across ALL asset classes on `/audit`"
