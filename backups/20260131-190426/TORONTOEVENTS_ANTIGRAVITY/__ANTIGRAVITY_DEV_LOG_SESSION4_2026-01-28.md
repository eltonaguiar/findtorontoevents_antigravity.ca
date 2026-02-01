# Antigravity Development Log - Session 4: Earnings & Risk Management
**Branch:** ANTIGRAVITY_STOCK_SESSION4_2026-01-28
**Started:** 2026-01-28 09:40 EST
**Status:** PLANNING

---

## 🚀 Session 4 Objective: Event Risk Awareness (Earnings)
After establishing **Macro Context** (Session 3), we now tackle **Event Risk**. The "V2.2 Engine" must not recommend stocks that are about to report earnings within 3-5 days, as this is a "binary event" (gambling), not investing.

### 📋 Task List

#### **Task 1: Earnings Date Data Pipeline** 📅
**Goal:** Enhance the data fetcher to include `earningsDate` or `daysToEarnings`.
- [ ] Update `StockData` interface in `scripts/lib/stock-data-fetcher-enhanced.ts`.
- [ ] Modify `fetchFromYahoo` to parse `earningsTimestamp` or `earningsDate` from `quoteSummary` (usually in `calendarEvents`).
- [ ] Ensure valid fallback (null/undefined) if data is missing.

#### **Task 2: "Earnings Risk" Filter in Scorers** 🛡️
**Goal:** Penalize or flag stocks with imminent earnings.
- [ ] Update `scripts/lib/stock-scorers.ts`.
- [ ] Logic:
    - If earnings in < 3 days: **DISQUALIFY** (or massive penalty).
    - If earnings in < 7 days: **WARNING** (High Risk Flag).
- [ ] This applies specifically to `scoreCANSLIM` and `scoreAlphaPredator` (Trend following shouldn't face binary events).

#### **Task 3: UI Countdown Indicator** ⏳
**Goal:** Show the user *when* the next event is.
- [ ] Update `PerformanceDashboard.tsx` or `VerifiedPickDetailModal.tsx`.
- [ ] Display "Earnings: 14 days" or "Earnings: TOMORROW (⚠️)".

---

## 📝 Notes
- Yahoo Finance `calendarEvents` module usually has the next earnings date.
- We need to be careful with "Estimated" vs "Confirmed" dates, but for safety, we treat estimated dates as risk zones too.

## 🚀 Execution Strategy
1. **Branch:** Create `ANTIGRAVITY_STOCK_SESSION4_2026-01-28`.
2. **Backend:** Update fetcher & scorers.
3. **Frontend:** Update UI.
