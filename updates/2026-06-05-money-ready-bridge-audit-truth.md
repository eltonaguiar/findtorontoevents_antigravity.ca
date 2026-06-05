# Money-ready bridge — audit surface truth panel

**Date:** 2026-06-05

## Problem

Multiple `/audit` surfaces showed inflated WR/PF (Smart Picks, tournament models) while policy-clean verdict shows **0/9 money-ready** and CRYPTO ~36% WR — coin-flip class aggregates unsuitable for real money.

## Solution

- `tools/build_audit_surface_truth.py` → `audit_dashboard/data/audit_surface_truth.json`
- `audit_dashboard/audit_surface_truth_banner.js` on main audit, ai-tournament, ai_leaderboard
- Hourly `audit-dashboard.yml` step regenerates JSON

## Ground truth (2026-06-05 run)

- Money-ready classes: **0**
- CRYPTO: n=310, WR 36.1%, PF 0.995
- Tournament: MISPRICED_ENTRY ~59% of rows — research only
- Production: 923 resolved rows with NULL `pnl_pct` (fix: PR #537)

## Verify

```bash
python3 tools/build_audit_surface_truth.py
# After deploy: open /audit/, /audit/ai-tournament.html, /audit/ai_leaderboard.html
```