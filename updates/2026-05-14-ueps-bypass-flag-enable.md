# UEPS Long-Horizon Gate Bypass — Enabled (2026-05-15)

**Date:** 2026-05-14  
**PR type:** Infrastructure / feature flag  
**Risk:** LOW (scoped bypass, all real safety gates remain active)

## What changed

Added `UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED: '1'` to the `Generate dashboard payload
and build HTML` step env block in `.github/workflows/audit-dashboard.yml`.

## Why

UEPS (Undervalued Equity Pick System) picks use a float 0–1 confidence score and the
`POSITION` timeframe. The standard dashboard quality gate rejects them because:

1. Their normalized score (0–1 float) is incompatible with the `ACTIVE_DISPLAY_NON_CRYPTO_MIN_RAW_SCORE=55` floor (expects an integer 0–100 score).
2. Several UEPS target symbols appear in `BLOCKED_SYMBOLS` (data-feed blacklist for
   short-term strategies — irrelevant to a 1-year value horizon).
3. The `elite_grade D` momentum filter is calibrated for short-term trades, not 12-month holding periods.

B28 (merged PR #582 on 2026-05-01) registered `ueps_picks.json` directly in
`JSON_PICK_SOURCES`. The bypass gate in `quality_gates.py:_ueps_long_horizon_bypass_active()`
was designed to be enabled after a 14-day shadow run to confirm no non-UEPS pick leaks.

**14-day shadow period:** 2026-05-01 → 2026-05-15 ✅ (complete at PR merge time)

## What the bypass does NOT change

- All real safety gates remain active for UEPS picks:
  - `trust_score` floor
  - `status` field validity
  - `wf_verdict` walkforward gate
  - `forward_wr` floor (when sufficient closed history exists)
  - `jpy_cross_buy_kill` rule
  - `healthcare_long_momentum_blacklist`
  - `entry_price` sanity check
- Zero impact on any non-UEPS pick. The bypass function at `quality_gates.py:2054-2058`
  gates on `source_system="ueps"` AND `trade_timeframe="POSITION"` — both conditions
  must hold.
- Zero impact on CRYPTO, FOREX, COMMODITY, ETF, or BOND picks.

## Acceptance criteria

After the dashboard cron rebuilds with this flag enabled:

```python
python -c "
import json
d = json.load(open('audit_dashboard/data/dashboard_data.json'))
active = d['picks']['active']
ueps = [p for p in active if p.get('source_system','').startswith('ueps')]
print(f'UEPS active: {len(ueps)}/{len(active)}')
"
```

Expected: ≥1 UEPS pick in `picks.active` (22 picks are in `ueps_picks.json` generated
2026-05-14T02:24 UTC; some will clear safety gates, some may not if trust_score or
wf_verdict rejects).

## What comes next (B10 — UEPS KPI Panel)

Once ≥10 UEPS picks close (estimated ~2026-05-22):

- `audit_trail/dashboard_generator.py`: add `picks.ueps_kpi` payload section
- `audit_dashboard/template.html`: render "UEPS Strategy Performance" KPI panel
- Tests: pytest for aggregation + Playwright snapshot

## Rollback

Remove the `UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED: '1'` line from
`.github/workflows/audit-dashboard.yml`. Default behavior (bypass=OFF) restores on
next dashboard rebuild.

## Related

- B28 (UEPS JSON_PICK_SOURCES registration): merged PR #582 — 2026-05-01
- B10 (UEPS KPI panel): ⏳ blocked on n≥10 UEPS closes — unblocks ~2026-05-22
- `quality_gates.py:_ueps_long_horizon_bypass_active()` — bypass scope definition
- `reports/REMAINING_ACTION_ITEMS_2026_04_30.md` — queue row 22 (B10)
