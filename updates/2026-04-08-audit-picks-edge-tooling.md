# Audit picks edge — observability & tooling (2026-04-08)

**NFA:** Research and software documentation only — not investment advice.

**Reference snapshot:** See `docs/AUDIT_PICKS_EDGE_ANALYSIS_2026-04-06.md` — dashboard `generated_at` **2026-04-06T20:11:17Z**. Re-run tools on a fresh `dashboard_data.json` for current numbers.

## What exactly changed

- **Live JSON snapshot:** `tools/fetch_audit_dashboard_snapshot.py` pulls production `/audit/data/dashboard_data.json` so offline analysis matches the live audit page.
- **Active book analyzer:** `tools/analyze_audit_active_book.py` — by `asset_class`, unrealized aggregates (excluding flagged rows), score vs unrealized correlations, VA tagging share, strategy joins to `recent_closed` with 30d/90d closed counts, `payload_systems_unrealized` echo.
- **Chained analyzers:** `tools/analyze_audit_scores_vs_pnl.py`, `tools/analyze_asset_class_edge_flaws.py` on the same dashboard path.
- **Outputs:** `tools/data/audit_active_book_analysis.json`, `score_pnl_analysis.json`, `asset_class_edge_flaws_analysis.json`; snapshots under `tools/data/snapshots/` (gitignored, `.gitkeep` tracked).
- **Docs:** `docs/AUDIT_PICKS_EDGE_ANALYSIS_2026-04-06.md`, cross-asset review + flaw MDs, `TRACE_LOG.MD`, `docs/REDIS_BUS_CHANGELOG.md`.
- **Bus:** `tools/bus_post_trace_log.py`, `tools/bus_post_audit_picks_edge.py` → topic `AUDIT_PICKS_EDGE_ANALYSIS`.
- **Exports caveat:** CSV/SQL exports can disagree with live audit if timestamps differ; JSON snapshot is the reconciliation source of truth.

## Benefits by asset class (observability)

| Class | Benefit |
|--------|---------|
| **CRYPTO** | Closed-book IC favors `smart_score`; VA concentration visible; positive mean closed PnL at scale in reference run — supports data-driven crypto calibration. |
| **EQUITY** | Surfaces low VA tag rate vs many actives and negative closed means — highlights universe/gate issues beyond score weighting. |
| **FOREX** | Small active n + weak discrimination in reviews — honest experimental tiering. |
| **COMMODITY / ETF / FUTURES** | Small-n buckets labeled; avoids overinterpretation. |
| **SPORTS** | Same audit pipeline as other classes; sparse in reference snapshot. |

**Full write-up:** [docs/AUDIT_PICKS_EDGE_ANALYSIS_2026-04-06.md](../docs/AUDIT_PICKS_EDGE_ANALYSIS_2026-04-06.md)

**Public HTML:** [/updates/2026-04-08-audit-picks-edge-tooling.html](https://findtorontoevents.ca/updates/2026-04-08-audit-picks-edge-tooling.html)
