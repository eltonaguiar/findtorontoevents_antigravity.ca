# Antigravity Stock Critique Response Plan - Phase 2 (ChatGPT Feedback)
**Date:** 2026-01-28
**Time:** 08:38 EST
**Branch:** ANTIGRAVITY_STOCK_CRITIQUE_2026-01-28

## 🧐 Analysis of ChatGPT Critiques
This feedback is extremely technical and actionable. It points out structural flaws (normalization, de-duping, data integrity) rather than just philosophical ones.

### 1. Duplicate Handling & Score Normalization
**Critique:** Picks are pushed per-algorithm, leading to duplicates (e.g., GM in both "Technical Momentum" and "Alpha Predator"). Scores are not comparable.
**Action:**
- In `generate-daily-stocks.ts` (or `stocks-scorers.ts`):
    - Implement a de-duping step. If a symbol appears multiple times, KEEP the highest score.
    - Concatenate algorithm names (e.g., "Alpha Predator + Technical Momentum").
    - Normalize scores? (Might be too complex for now, but de-duping is critical).

### 2. Explicit Entry Price Recording (Critical Bug)
**Critique:** `verify-picks.ts` relies on `pick.metrics.price` which might not exist for all strategies.
**Action:**
- Ensure `generate-daily-stocks.ts` (or the scorer) explicitly adds an `entryPrice` field to the root of the pick object at generation time.
- Update `verify-picks.ts` to use this explicit `entryPrice` as the source of truth BEFORE simulate slippage.

### 3. Universe Expansion
**Critique:** 101 tickers is a "Watchlist Scorer", not a "Stock Picker".
**Action:**
- We cannot easily fetch the whole Russell 3000 API-free, but we CAN expand the `stock-universe.ts` significantly.
- **Task:** Add ~50-100 more diverse tickers (ETFs? different sectors?) to `stock-universe.ts` to show we are listening.

### 4. "Scientific CAN SLIM" Misnomer
**Critique:** It's missing quarterly earning growth, etc.
**Action:** Rename algorithm? Or just add disclaimer.
- **Decision:** Rename "CAN SLIM" to **"Growth Trend (Simplified CAN SLIM)"** in UI to be honest. Update `PerformanceDashboard.tsx` label map.

## 📋 Task List (Immediate Fixes)
- [ ] **Data Integrity:** Update `generate-daily-stocks.ts` to dedupe picks and merge algorithm tags.
- [ ] **Data Integrity:** Ensure `entryPrice` is hard-coded in the JSON output.
- [ ] **UI:** Rename "CAN SLIM" to "Growth Trend" in `PerformanceDashboard.tsx`.
- [ ] **Docs:** Update Critique section in README with these new points.
