# PR: Dashboard Edge Truth — Fix Misleading Claims & Add Deep-Dive Research

**Branch:** `fix/dashboard-edge-truth-2026-04-19`  
**Date:** 2026-04-19  
**Scope:** `audit_dashboard/template.html` corrections + comprehensive quantitative research on edge, filters, regimes, and non-crypto viability.

---

## Why This PR Exists

The audit dashboard contained significant factual errors in its `? Guide` overlay, decile-test panel, and predictor-ranking table. These errors were not cosmetic — they actively misdirected users toward losing filters (e.g., wide R:R 1.5–2.0) and away from the few verified edges (e.g., tight R:R < 1.5 + high confidence). 

We deployed a subagent swarm to:
1. Audit every button, filter, tooltip, and overlay claim against `closed_picks.json` (4,503 records).
2. Hunt for any non-crypto strategy with genuine, symbol-agnostic edge.
3. Profile specific filter combinations (score + track, smart picks, high-grade, etc.).
4. Analyze performance by market regime (trending vs choppy vs bear vs bull).
5. Identify common factors in best vs worst picks via correlation and decile analysis.
6. Assess whether more backtests would fix non-crypto performance.

This PR applies the most urgent UI fixes and bundles the research deliverables.

---

## Code Changes

### `audit_dashboard/template.html`

#### 1. `? Guide` Overlay — R:R Sweet Spot Correction
**Before:** "1.5–2.0 is the only profitable band (55.8% WR, PF 3.15, +0.05% avg)"  
**Reality:** R:R 1.5–2.0 is actually **49.1% WR, PF 0.41, -0.06% avg**. The real (barely) profitable band is **R:R < 1.5** (58.0% WR, PF 1.06, n=243). R:R ≥ 2.0 is catastrophic (29.1% WR, -0.17% avg, n=3,931).  
**Fix:** Swapped the colors and claims. The overlay now correctly identifies tight R:R as the only viable band and wide R:R as the single biggest edge killer.

#### 2. `? Guide` Overlay — Non-Crypto Honesty
**Before:** "For non-crypto, be aware that tile PnL is now cost-adjusted (net), which can flip the sign on thin edges."  
**Reality:** Non-crypto has **6 closed trades total** in `closed_picks.json`, all losing. There is no thin edge to flip.  
**Fix:** Replaced with: "**Non-crypto has zero verified edge** (only 6 closed trades, all losing) — size to zero or avoid entirely."

#### 3. High Conviction Button Tooltip
**Before:** "RECOMMENDED (all asset classes): ... Does not restrict to crypto"  
**Reality:** The `passesValidatedEdgePerClass` gate in the code explicitly rejects COMMODITY, BOND, ETF, and FUTURES.  
**Fix:** Changed to "RECOMMENDED (crypto / equity / forex only): ... Strict mode explicitly blocks COMMODITY, BOND, ETF, and FUTURES."

#### 4. Decile Test Panel — Smart Picks Banner
**Before:** Top 20% ml_score = "60% WR, +4.2% avg PnL" vs Bottom 20% = "22% WR, -8.14% avg PnL"  
**Reality (n=472):** Top 20% = **67.4% WR, +0.073% avg**; Bottom 20% = **64.9% WR, +0.009% avg**. The bottom 20% is positive, not a kill zone.  
**Fix:** Updated numbers and added a note that the relationship is non-monotonic/noisy.

#### 5. Decile Test Panel — Predictor Power Ranking
**Before:**
- ml_score +0.33 BEST
- confidence +0.27 STRONG  
- elite_score +0.012 WEAK

**Reality (Spearman on 4,503 picks):**
- elite_score **+0.127** (n=3,942, p<0.0001)
- ml_score **+0.087** (n=472, p=0.058)
- confidence **-0.006** (n=4,404, p=0.68) — effectively random

**Fix:** Reordered and corrected the entire table. `confidence` is now labeled **RANDOM** because higher confidence does not predict higher PnL in this dataset.

#### 6. Decile Test Panel — Actionable Cutoffs
**Before:** Kill Zone claimed ml_score < 0.50 had 22% WR / -8.14% avg. Sweet Spot claimed confidence 0.60-0.70 was the empirical sweet spot.  
**Fix:** 
- Replaced Kill Zone with **"R:R ≥ 2.0"** (the actual verified kill zone: 29.1% WR, PF 0.39, n=3,931).
- Replaced Sweet Spot with **"R:R < 1.5 AND confidence > 0.75"** — the only empirically-verified filter combo in the data (68.8% WR, PF 4.96, n=48).

#### 7. Decile Test Panel — Dataset Size Header
**Before:** "Backtested on 1,927 closed picks"  
**Fix:** Updated to **"4,503 closed picks"** with a note that n varies by predictor.

---

## Research Deliverables (No Code Changes)

These files contain the full quantitative analysis. They are documentation-only and safe to merge.

| File | What It Covers |
|------|----------------|
| `updates/2026-04-19-dashboard-ui-edge-audit.md` | Control-by-control audit of every button/filter in `template.html`. Identifies misleading vs honest claims. |
| `updates/2026-04-19-noncrypto-edge-hunter.md` | Only 6 non-crypto closed trades exist (0.13%), all from scrapers, all losing. Zero strategies meet edge bar. `production_scanner.py` never imports the dedicated `equity_strategies.py` / `forex_strategies.py` modules. |
| `updates/2026-04-19-filter-combination-profiler.md` | Most requested combos (AGV>80+score=100+trust>7, smart picks+score>100, track>70%+score>80) are **untestable** because those fields are absent from historical closed picks. The only verified combo is `risk_reward < 1.5 AND confidence > 0.75` (68.8% WR, PF 4.96). |
| `updates/2026-04-19-market-regime-analysis.md` | `panic` (trending/bear) slightly beats `caution` (choppy), but neither is profitable overall. `quan_engine_swing` is the most regime-robust strategy. |
| `updates/2026-04-19-feature-correlation-analysis.md` | Best predictors of PnL: `hold_days` (+0.134), `ml_score` (+0.232 Pearson), `elite_score` (+0.067). Worst structural factor: `risk_reward` (-0.137 Spearman). `quan_engine_scalp` is a structural loser at scale (PF 0.39, n=3,805). |
| `updates/2026-04-19-backtest-gap-analysis.md` | More backtests will **not** fix non-crypto. The problem is orphaned strategies and structurally flawed scrapers, not insufficient simulations. |

---

## Direct Answers to User Questions

> **Is there a strategy that performs amazing regardless of symbol for non-crypto?**
> **No.** There is no non-crypto strategy with PF>1.5, WR>50%, and n≥15. The 6 non-crypto trades in the ledger are all losses from `multi_asset_copytrader`.

> **Do we need more backtests on non-crypto?**
> **No.** The dedicated strategy files (`equity_strategies.py`, `forex_strategies.py`, etc.) are orphaned — `production_scanner.py` never calls them. More backtests on code that never runs is pointless.

> **What happens if AGV > 80 and score = 100 and trust > 7?**
> **Untestable.** `AGV`, `score`, and `trust` do not exist in `closed_picks.json` (0/4,503 records).

> **What about smart picks + score > 100?**
> **Untestable.** `smart_score` is not persisted in historical closed picks.

> **What about crypto "high-grade"?**
> **Untestable.** `elite_grade` is missing on 462 of 467 crypto records.

> **Do we perform better on trending vs choppy markets?**
> `panic` (proxy for trending/bear) is slightly better than `caution` (choppy), but **neither is profitable overall**. No regime is consistently green.

> **Common factors in super low performance?**
> - `risk_reward >= 2.0` (29.1% WR, PF 0.39)
> - `quan_engine_scalp` strategy
> - Short hold duration
> - SL exits

> **Common factors in positive performance?**
> - `risk_reward < 1.5` + `confidence > 0.75` (68.8% WR, PF 4.96)
> - Higher `ml_score` / `elite_score`
> - Longer `hold_days`
> - ML-enhanced 1d/4h strategies

---

## Safety & Verification

- `template.html` div balance checked: 19 opens vs 19 closes in the modified overlay region.
- No JavaScript function names were broken.
- All changes are text/tooltip updates; no backend logic was modified.
- No push to `main` was performed.

---

## Files Changed

| File | Action |
|------|--------|
| `audit_dashboard/template.html` | Corrected misleading R:R, non-crypto, High Conviction, ml_score decile, predictor-ranking, and actionable-cutoff claims |
| `updates/2026-04-19-dashboard-ui-edge-audit.md` | New — full UI audit |
| `updates/2026-04-19-noncrypto-edge-hunter.md` | New — non-crypto edge hunt |
| `updates/2026-04-19-filter-combination-profiler.md` | New — filter combo profiling |
| `updates/2026-04-19-market-regime-analysis.md` | New — regime performance |
| `updates/2026-04-19-feature-correlation-analysis.md` | New — correlation & decile analysis |
| `updates/2026-04-19-backtest-gap-analysis.md` | New — backtest gap assessment |
| `updates/2026-04-19-PR-dashboard-edge-truth-fixes.md` | New — this PR document |
