# INCIDENT_CRYPTO: claude_ml_moderate_mut outlier (2026-06-03)

## What

Seeded idempotent row in `INCIDENT_CRYPTO` via `tools/audit_pick_funnel/seed_incidents_enhancements.py` after PR #482 suspicious-PASS investigation.

## Finding

`claude_ml_moderate_mut`: bootstrap IS_PF≈310 driven by one JUPUSDT row (945× return); **pf_lo_95=1.31**. Do not promote. Legit forward-test candidates: `B_flip_PriceRocMeanReversion`, `inverse_ml_enhanced_BTCUSDT_15m_D`.

## Verified

```bash
python3 tools/audit_pick_funnel/seed_incidents_enhancements.py
python3 tools/audit_pick_funnel/render_incidents_page.py
```