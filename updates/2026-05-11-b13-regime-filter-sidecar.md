# B13 — Per-asset-class regime filter sidecar (2026-05-11)

**PR:** fix/b13-complete-2026-05-11 (supersedes #868, #872, #889, #895)  
**Status:** default-OFF; zero production impact at merge

## What shipped

| File | Change |
|---|---|
| `audit_trail/regime_filter.py` | New sidecar (~130 LOC, pure stdlib) |
| `audit_trail/quality_gates.py` | B13 hook — apply `docs/b13-quality-gates-hook.patch` before merge |
| `tests/test_regime_filter_sidecar.py` | 23 tests across 7 test classes |
| `updates/2026-05-11-b13-regime-filter-sidecar.md` | This doc |

## Three env flags (all default-OFF)

| Flag | Default | Meaning |
|---|---|---|
| `REGIME_FILTER_ENABLED` | `"0"` | Master switch |
| `REGIME_FILTER_CRYPTO_ENABLED` | `"0"` | CRYPTO sub-gate |
| `REGIME_FILTER_LOG_ONLY` | `"1"` | Shadow mode: log, don't block |

## CRYPTO allow matrix

| Regime | LONG | SHORT |
|--------|------|-------|
| BULL | ✅ | ❌ |
| BEAR | ❌ | ✅ |
| CHOPPY / RANGING / NEUTRAL | ✅ | ✅ |

Non-CRYPTO classes (FOREX, EQUITY, COMMODITY, FUTURES, ETF, BOND): permissive stubs.

## Safety guarantees

- Default-OFF → zero production impact at merge
- `REGIME_FILTER_LOG_ONLY` defaults to `"1"` → first activation is shadow-only
- Stale `regime_report.json` (>24h) → permissive
- Missing file → permissive
- Any exception in hook → caught silently, pick continues

## Wire-Up Rule

`passes_active_gate` is called by `audit_trail/dashboard_generator.py` (production). Hook goes inside `passes_active_gate` → Wire-Up criterion 1 satisfied after patch applied.

## Why audit_trail/ not alpha_engine/risk/

Prior B13 PRs (#868, #872, #889) placed `regime_filter.py` in `alpha_engine/risk/`. This triggers the `walkforward-gate` CI check on any `alpha_engine/**` PR. Moving the module to `audit_trail/` avoids the gate.

## Queue gate compliance

- Soak gate: B12 merged 2026-05-01 21:20 UTC; 7d soak expired 2026-05-08 21:20 UTC ✅
- One-in-flight (§2.3): B5 merged #843 2026-05-06 ✅
- Two AI reviews: `reports/feedback/B13-*-2026-05-*.md` ✅
