# EQUITY — quick wins

## 1. Add `last_quote` timestamp + "last close" provenance (S / H)
- **Problem:** `make_long_term_value_pick()` emits `entry_price` only; `universal_price_enricher` fills `current_price` from yfinance `last_price` (last close, not live tick). When `current == entry` the UI shows "+0.00%" as if live.
- **Fix:** In `enrich_all_picks()` / `_fetch_yfinance_prices()` stamp `last_quote=now`, `price_source="yfinance"`, `price_asof=<hist date>`. In `make_long_term_value_pick()` add `entry_price_asof`/`last_quote`. In `template.html` (~:4722) render muted "last close · <asof>" when no fresh quote.
- **Targets:** `alpha_engine/universal_price_enricher.py`; `alpha_engine/long_term_pick_contract.py`; `audit_dashboard/template.html`.
- **Verify:** re-run enrich → `last_quote`/`price_source` present; dashboard shows "last close", not live 0%.

## 2. EQUITY headline: show `n` + Wilson 95% CI (S–M / H)
- **Problem:** "75% WR / PF 8.86" is computed from n=8 (flat trades excluded from denominator at `dashboard_generator.py:15483`); larger samples are 46–47% WR. Misleading.
- **Fix:** In `compute_asset_class_health()` add `wilson_ci_lo/hi` (reuse `tools/adaptive/strategy_trust.py::wilson_ci_95` or `benchmark_closed_ledger.py`). Render `WR 75% (n=8, 95% CI 39–97%)` + "thin sample" badge when `n < 100`.
- **Targets:** `audit_trail/dashboard_generator.py:5916`; `audit_dashboard/summary.html` (~:531–557) / `template.html`.
- **Verify:** `wilson_ci_95(6, 8)` → wide CI crossing 50%; headline renders n + CI.

## 3. (with ETF) Don't show "live 0%" — reuse last-close provenance
- Same as #1; renders "parked at last close" instead of "+0.00% live". See `by-asset-class/ETF.md`.
