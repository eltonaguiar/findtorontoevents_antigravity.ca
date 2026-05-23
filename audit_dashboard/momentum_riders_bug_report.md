# Momentum Riders – Closed‑Trade Price Bug

## Summary
The audit dashboard (`audit_dashboard/claudes_test.html`) embeds portfolio data in a JavaScript object (`const D = {...}`). The `momentum_riders` portfolio’s `recent_closed` array contains the raw trade data, which appears correct. The “impossible prices” shown on the UI are caused by front‑end rendering logic, not by corrupted data.

## Root Cause
1. **Missing price validation** – The rendering code assumes every closed trade has a valid `exit_price`. When the price feed is stale or missing, `current_price` falls back to `entry_price`, making closed trades appear to exit at entry (no change).
2. **Zero‑value formatting** – `fmtUsd(0)` renders `$0.00` for stale/missing prices, mimicking impossible values.

## Action Plan to Fix
### Phase 1: Immediate UI Fixes (5-10 min)
1. **Read full HTML**: Use `read_file` on [`audit_dashboard/claudes_test.html`](audit_dashboard/claudes_test.html) to locate the `renderRecentClosed` or portfolio detail rendering logic (likely lines 300+ where table rows for `recent_closed` are built).
2. **Add exit_price guards**:
   - Before displaying `exit_price`, check: `const exitPrice = trade.exit_price && trade.exit_price !== trade.entry_price ? trade.exit_price : '—';`
   - Update table cell: `<td>${fmtPrice(exitPrice)}</td>` where `fmtPrice` handles zero/null as '—'.
3. **New formatter**: Add `const fmtPrice = (n) => n && n > 0 ? fmtUsd(n) : '—';`
4. **Apply via search_replace**: Target the specific `<td>` for exit_price in recent_closed table.

### Phase 2: Data Validation (10-15 min)
1. **Backend check**: Inspect data generator (`audit_dashboard/portfolio_manager.py`?) for `exit_price` population logic.
2. **Add logging**: In portfolio_manager.py, log when `exit_price` == `entry_price` for closed trades.
3. **Price feed audit**: Verify `current_price` source (e.g., CCXT, Yahoo Finance) – ensure timestamps.

### Phase 3: Testing & Deploy (5 min)
1. Save changes to HTML.
2. Open `claudes_test.html` in browser, refresh, verify Momentum Riders closed trades show realistic exits or '—'.
3. Run `execute_command` with `python audit_dashboard/db_sync.py` if data refresh needed.
4. Update main dashboard [`audit_dashboard/index.html`](audit_dashboard/index.html) if bug replicated there.

### Priority: High – UI fix blocks trust in PnL reporting.
*Estimated time: 20-30 min. Owner: Kilo Code.*

---
*Investigation & Plan by Kilo Code on 2026‑03‑10.*