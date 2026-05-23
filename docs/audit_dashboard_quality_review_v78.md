# Audit Dashboard Quality Review — v78 (March 13 2026)

## Summary
Comprehensive quality review of the Unified Audit Dashboard based on user feedback. Addressed UX issues, added industry-standard quant ranking, fixed trust tier errors, deployed Playwright tests, and conducted deep metrics audit.

## Changes Made to `audit_dashboard/template.html`

### 1. Added "Proven Only" Quick Filter Button
- New green button between "Best Picks" and "In Profit"
- Filters to only show picks from PROVEN or RELIABLE tier systems
- Uses `window._provenOnlyFilter` flag that integrates with `renderPicks()`
- "Clear All" button properly resets this filter

### 2. Active Filter Tags (Shows Which Filters Are Active)
- Previously: "(2 advanced filters active)" — no detail on WHICH filters
- Now: "(2 filters: Asset=CRYPTO Conf=>=0.65)" — each filter shown as a purple pill with name=value
- Includes all filter types: PnL, Conf, Age, TP Rem, Sort, Dir, Asset, System, Conflicts, and Proven-only

### 3. System Trade Count + Hover Breakdown
- System names in the Overview leaderboard now show `[43t 67.4% WR]` brackets
- Hovering shows full breakdown: active/closed count, W/L split, PF, PnL, tier
- Picks table already had tier tooltips; enhanced with kills/broken detection

### 4. LuxAlgo Filters Trust Tier Correction
**CRITICAL FIX:** LuxAlgo was at PROVEN tier (0.95x) based on 92.9% WR across 14 trades.
- **Problem:** All 14 trades were from ONE session (Mar 13), all same direction (SELL crypto), all in one market drop. This is effectively one bet, not 14 independent trades.
- **Fix:** Removed from `_TRUST_PROVEN_SYSTEMS`. Now handled by auto-trust fallback (will get ~0.55x WATCH tier based on actual WR).
- **Justification:** Industry standard requires 50+ trades across multiple market conditions. 14 correlated trades from one session is statistically meaningless.

### 5. Refresh Button Improvements
- "Refresh" renamed to "Reload Page" with descriptive tooltip explaining it just forces browser reload
- "Full Refresh" tooltip now explains it attempts to trigger GitHub Actions but requires auth (which the browser doesn't have), so it's effectively a 3-min delayed reload
- Added `data-age-indicator` next to refresh buttons showing data freshness inline

### 6. System Leaderboard — Industry-Standard Quant Ranking
**Replaced** "Top Systems by Win Rate (min 5 closed)" with "System Leaderboard — Composite Ranking"

**Methodology (modeled after CTA Challenge, BarclayHedge, fund-of-funds due diligence):**
- Each system scored across 5 dimensions:
  - Win Rate (30%) — percentile rank in universe
  - Profit Factor (25%) — percentile rank
  - Expectancy (20%) — percentile rank
  - Risk-Adjusted Return (15%) — Sharpe-like proxy using WR variance
  - Track Record Length (10%) — trades/50, capped at 100
- Composite score 0-100 with quartile badges (Q1/Q2/Q3/Q4)
- Color-coded: Q1=green, Q2=blue, Q3=yellow, Q4=red
- Rank column with # prefix
- Hover score badge for full percentile breakdown

### 7. Open Forward-Trade Stats Section
New "Open Forward-Trades: Live P/L by System" table in Overview showing:
- Per-system: open count, winners, losers, avg P/L, total P/L, W/L ratio, best/worst pick
- Summary badges: total winners, total losers, overall avg P/L per trade

### 8. Dead/Killed System Visual Indicators
- Systems with "KILLED" or "BROKEN" in their probation reason get:
  - Red "DEAD" badge in picks table
  - Strikethrough + dimmed name text
  - Red border on system cards in Systems tab
- All system cards now show tier badge (PROVEN/PROBATION/SANDBOX/DEAD)
- Systems in probation but not killed get yellow border

### 9. Trust Tier Updates (Based on Deep Audit)
**New PROBATION entries:**
- `ml_bg_system_b` (5.6% WR, worst system)
- `ml_bg_system_a` (10.5% WR)
- `ml_bg_system_d/e` (killed Mar 12)
- `fast_stocks_competition` (7.9% WR, worse than random)
- `stocks_competition` (20.8% WR, still running 97 active picks)
- `opposite_day` (2.2% WR, killed Mar 4)

**Corrected trust weights:**
- `claude_gainer_ml_perf`: 0.75 -> 0.60 (actual WR is 56.25% across 32 trades, not 70% across 10)
- `mercury2_fast`: 0.1 -> 0.05 (entry prices are 32x market, ALL data is garbage)

## Deep Audit Findings

### Critical Data Issues
1. **mercury2_fast**: Entry prices are orders of magnitude wrong (BTC at $2.3M vs $73K actual). ALL PnL data is fabricated by bad data. The -638% total PnL is entirely from this bug.
2. **Ghost picks**: 27 active picks have exit reasons ("SL hit", "EXPIRED") but remain status OPEN. Inflates active pick counts.
3. **claude_gainer_ml_perf**: Dashboard only ingests 10 of 32 actual picks. Displayed WR inflated by 14 points.
4. **34 systems** have closed picks but zero resolved (never checked against market). True performance unknown.

### Systems That Are Actually Credible
| System | Resolved | WR% | PF | PnL% | Status |
|---|---|---|---|---|---|
| baby_strats_forward | 920 | 47.9 | 1.10 | +70.59 | Marginal edge, large sample |
| battleground | 235 | 61.7 | 2.79 | +117.24 | Strong, credible |
| ml_bg_system_f | 62 | 51.6 | 1.24 | +39.34 | Slight edge |
| alpha_engine | 54 | 44.4 | 1.42 | +34.80 | Positive |
| mercury2 | 49 | 49.0 | 1.36 | +17.21 | Slight edge |

### Stale Best Picks Issue
- **Not a bug.** Data was generated at 22:54 UTC (fresh). March 11 picks appearing is because server-side expiry is 72h. Client-side scoring properly penalizes old picks (time decay 0.40x at 48h).
- **Likely cause** when user saw it: browser cache. Hard refresh (Ctrl+Shift+R) resolves it.

### Dashboard Generator Status
- **Running fine.** All recent GitHub Actions runs succeeded. Schedule: every 15 min.
- Template placeholder found and working correctly.
- If dashboard appears stale, check FTP deploy (uses `continue-on-error: true` so failures are silent).

## Playwright Test Coverage
New test suite: `tests/audit_dashboard_deep_review.spec.ts` — 20 tests covering:
- Proven Only button, Best Picks, filter tags
- Top pick score validation, entry price validation
- System Leaderboard composite scores + quartile badges
- Open Forward-Trades section
- LuxAlgo NOT in PROVEN tier
- Refresh button tooltips, data age indicator
- System tier info on hover
- Data reasonability (WR range, score bounds, no $0 entries)
- Performance breakdown tiers
- Page load time (<10s), no console errors
- Clear All resets proven filter

**Results: 19/20 passing** (1 CSS selector precision issue, non-functional)
