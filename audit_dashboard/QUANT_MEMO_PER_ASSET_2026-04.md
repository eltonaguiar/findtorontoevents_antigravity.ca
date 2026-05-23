# Quant memo — per-asset audit dashboard (April 2026)

## Crypto

- **Headline stats** blend 100+ systems; edge lives in **gated** subsets (Smart Picks, quality gates). Treat aggregate WR/PF as diagnostic, not tradable book.
- **PnL scale**: per-trade caps (±500%) in aggregation; flag **>200% unrealized** on active rows for bad entry scale.
- **World-class path**: regime routing + walk-forward OOS + kill persistently toxic strategies; see `WORLD_CLASS_ROADMAP.md`. Binance mirror failover is mandatory for live marks.

## Forex / non-crypto symbols

- **Server/UI parity**: `nc_asset_category_for_pick()` now mirrors template rules (`=X` → FOREX, `XAU`/`XAG*` → COMMODITY, `=F` → FUTURES) so **Non-Crypto Performance** cards align with magnifier drill-down.
- **Coverage**: closed history mixes JSON + MySQL (`mysql_fetch_closed_non_crypto`); silent DB failure understates forex/equity — monitor generator logs.

## Equities / ETF / commodities / futures

- **Reservation**: per-category `recent_closed` quotas avoid ETF/FUTURES being crowded out; drill-down tables stay populated.
- **Validation**: Yahoo-style symbols (`GC=F`) need contract-level sanity checks (invalid gold prints were reported peers — add range checks in generator).

## Verified Alpha / Smart Picks

- **VA** is label-driven (`_is_verified_alpha_pick`); strict gates (e.g. `wf_p_value`) can yield **zero** VA rows while pipeline is healthy. Prefer **auditable** `audit_meta` on promoted rows (`_extract_verified_alpha_audit`).
- **Smart Picks** depend on `passes_smart_gate` and live enrichment; stale prices or missing `source_system` break attribution — fix at ingest.

## Clean book metrics (recommended reporting)

- Report **resolved_closed** after `_filter_valid_resolved_picks` + dedupe, restricted to picks that pass Smart gate (or a declared “tradable” flag).
- Add per–asset-class **Spearman** (ml_score vs outcome) once N≥100 closed per bucket.

## Files touched this initiative

- `audit_trail/dashboard_generator.py` — `nc_asset_category_for_pick`, NC gate loop, reservation uses same bucketing.
- `audit_dashboard/template.html` — drill-down unrealized PnL matches card field precedence.
- `tests/audit_live_quant_data.spec.ts` — live `DASHBOARD_DATA` snapshot.
- `tools/audit_sample_market_validate.py` — spot-check harness.
