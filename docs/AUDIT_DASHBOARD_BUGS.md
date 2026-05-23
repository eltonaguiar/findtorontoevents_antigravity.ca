# Audit Dashboard Bugs & Planned Fixes
**Created:** 2026-03-13 ~19:28 EST by [ANTIGRAVITY]
**File:** `audit_dashboard/template.html` → compiles to `audit_dashboard/index.html`

## Bug 1: "Proven Only" / "Best Picks" Don't Update Header KPI Stats

**What happens:** When clicking "★ Proven Only" or "★ Best Picks", the picks table filters correctly, but the header KPI stats (Active Picks, Closed Picks, Win Rate, Total PnL, Profit Factor) remain unchanged — they still show the ALL data totals.

**Root cause:** The `renderSummary()` function computes KPIs from ALL picks in `D.picks.active` and `D.picks.recent_closed` without applying the current filter state. The filter only applies in `renderPicks()` which renders the table, but the summary cards are computed independently.

**Fix:** In `renderSummary()`, check if `window._provenOnlyFilter` is set and, if so, filter the picks before computing KPI stats. Also check `getFilters()` to respect current dropdown filters. The filtered subset should be used for:
- Active Picks count
- Closed Picks count  
- Win Rate
- Total PnL
- Profit Factor
- Expectancy
- Avg Win / Loss
- W/L count

**Location in template.html:** Search for `renderSummary` function. The summary stats section uses `allActive` and `allClosed` arrays — these need to be filtered when a preset filter is active.

**Estimated fix:** ~20 lines changed in `renderSummary()`.

---

## Bug 2: Profit Factor Shows "∞" (Infinity)

**What happens:** When filtering to show only profitable picks (e.g., "In Profit" preset), if ALL visible closed picks are winners (0 losses), PF = grossWin / 0 = Infinity, displayed as "∞".

**Root cause:** Division by zero in PF calculation: `grossWin / Math.abs(grossLoss)` when `grossLoss === 0`.

**Fix:** Cap PF display at 99.99 when losses = 0:
```javascript
const pf = grossLoss > 0 ? (grossWin / grossLoss).toFixed(2) : grossWin > 0 ? '99.99+' : '—';
```

**Location in template.html:** Search for `profit_factor` or `profitFactor` in the summary/KPI rendering section.

---

## Bug 3: "Proven Only" Filter Shows All 603 Active Picks in Count

**What happens:** After clicking "★ Proven Only", the header still shows "603 Active Picks" (the unfiltered total). The "43 proven / 548 sandbox" breakdown text also doesn't update.

**Root cause:** Same as Bug 1 — the header summary is rendered independently of the pick filter. The "X proven / Y sandbox" text is generated once on page load and never re-rendered when filters change.

**Fix:** After any filter change (including preset buttons), re-render the summary section with the filtered subset. The breakdown badge should show "Showing X of Y active picks" with the filtered count.

---

## Bug 4: Crypto "Best Picks" Shows 4.1% PnL with 45.2% WR

**What the user sees:** After clicking Best Picks → selecting Crypto asset → sees mediocre stats.

**Analysis:** This may be ACCURATE for the current proven crypto picks. The 45.2% WR is slightly below 50%, but PnL can still be positive if avg win > avg loss (positive expectancy). However, with WR < 50% and only 4.1% total PnL, this suggests the system is marginally profitable at best.

**Action needed:** Not necessarily a bug — but the header should clearly indicate this is FILTERED data ("Showing Crypto picks from Proven systems only") so the user understands the context.

---

## Bug 5: Idle/Disabled Systems Not Visually Flagged

**What the user wants:** Systems with 0 active picks that haven't produced a signal in 7+ days should be shown in red or with a "DISABLED" badge on the systems table.

**Fix:** In the systems table rendering, add a condition:
```javascript
const isIdle = s.active_picks === 0 && s.closed_picks >= 5;
const daysSinceSignal = s.last_signal_at ? Math.floor((Date.now() - new Date(s.last_signal_at).getTime()) / 86400000) : 999;
const isStale = daysSinceSignal > 7;
// Add red badge:
if (isIdle && isStale) {
  html += '<span class="badge" style="background:#ef444422;color:#ef4444">IDLE ' + daysSinceSignal + 'd</span>';
}
```

**Location:** Search for system row rendering in the "Systems" tab section.

---

## Priority Order
1. **Bug 1+3** (header stats not updating on filter) — most confusing to users
2. **Bug 2** (infinite PF) — cosmetic but looks broken
3. **Bug 5** (idle system badges) — important for trust
4. **Bug 4** (context label) — nice to have
