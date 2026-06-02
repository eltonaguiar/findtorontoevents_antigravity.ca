# EAGLE2 next steps — nav matrix, strategy_admit, pf banner, monitoring

**Date:** 2026-06-02  
**Goal:** #1 audit honesty + research-to-production bridge

## Shipped

1. **`tools/strategy_admit.py`** — B1 unified admissibility CLI (`--strategy`, `--write`).
2. **`tools/emitter_census.py`** — C1 top sources per class → `reports/emitter_census_latest.json`.
3. **`tools/audit_pick_funnel/build_nav_surface_matrix.py`** — A2 overlays `money_ready_verdict` (no `is_edge` unless class `MONEY_READY`); Smart CRYPTO DISPUTED tag.
4. **`audit_dashboard/pf.html`** — D2 research-tier banner + live money-ready strip.
5. **`tools/pick_quality_pulse.py`** — HHI proxy + concentration alerts on MR fields.
6. **`reports/EAGLE_REVIEW_2026-06-02_GROK.md`** — review of all recent EAGLE*.MD files.
7. Regenerated **`nav_surface_edge_matrix.json`** from live `dashboard_data.json` — all surfaces `no-edge`.

## Verify

```bash
python3 tools/emitter_census.py
python3 tools/strategy_admit.py --strategy etf_dual_momentum --asset-class ETF
python3 tools/audit_pick_funnel/build_nav_surface_matrix.py
python3 tools/pick_quality_pulse.py
```

## Deploy

```bash
python3 tools/deploy_audit_files.py --only pick_funnel,ai_portfolios
```

Refs: `reports/EAGLE2_2026-06-02_GROK.md`, `reports/EAGLE_2026-06-02_GROK.md`, `reports/EAGLE_REVIEW_2026-06-02_GROK.md`.