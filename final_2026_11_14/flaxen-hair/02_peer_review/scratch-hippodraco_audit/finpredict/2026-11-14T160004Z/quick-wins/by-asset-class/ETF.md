# ETF — quick wins

## 1. "Parked at last close" label for frozen ETF rows (S / M, folded into EQUITY #1)
- **Problem:** ~50% of 30 OPEN ETF picks show `current == entry` → visually identical to a live unchanged price.
- **Fix:** Reuse the `last_quote`/`price_asof` provenance added in EQUITY #1 — when `current_price == entry_price` and `price_source == "yfinance_close"`, render "parked at last close" instead of a live PnL figure. Pure frontend.
- **Targets:** `audit_dashboard/template.html` (ETF card).

## 2. Hide empty UEPS Swing / Closed-Holds sub-tabs (S / M)
- **Problem:** `run_ueps_pickers.py::run_screeners()` hardcodes `swing_picks = []` (deferred, :138–142) and no `long_term_value` closed trades exist (n<100); `render_ueps_section()` always emits 3 tab buttons, so users click into dead Swing/Closed-Holds tabs.
- **Fix:** In `render_ueps_section()` only emit a tab when its bucket is non-empty; otherwise a muted "coming soon — n=N/100" chip. `render_empty_state()` already exists for the panel body.
- **Targets:** `audit_dashboard/ueps_section_renderer.py:909`; `tests/test_ueps_section_renderer.py`.
- **Verify:** update test to assert Swing/Closed-Holds tabs are hidden/absent when buckets empty.

## 3. ETF "frozen" flag on the pick card
- Same provenance as #1; renders "last close" instead of "+0.00% live" on the /audit ETF tab.
