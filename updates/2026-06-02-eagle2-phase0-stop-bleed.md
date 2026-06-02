# EAGLE2 Phase 0 — stop the bleed (2026-06-02)

## What changed

Implements **Phase 0** from `reports/EAGLE2_2026-06-02_COMPOSER.md`:

1. **Depromote loss sources** — `regime_terminal`, `incubator_gainer`, `mercury2_fast` volume caps → **0%** intake (`per_source_volume_cap.py`); `incubator_gainer` added to `BLOCKED_SOURCE_SYSTEMS`; CRYPTO/FOREX `regime_terminal` + CRYPTO `incubator_gainer` in `BLOCKED_ASSET_STRATEGY_PAIRS`.
2. **Smart Picks allowlist** — removed `regime_terminal` from EQUITY/FOREX allowlists (already blocked for EQUITY at quality gate).
3. **60% single-source cap** — new `alpha_engine/eagle2_class_source_cap.py`, wired in `smart_picks_engine.py` after per-source caps.
4. **Concentration probation** — `config/risk_policy.json`: `enable_concentration_probation_v2=true`, mode `exclude`.
5. **Dashboard honesty strip** — `dashboard_enhancements.js` loads `strategy_admissibility.json` and shows policy-clean PF/WR by class.

## Verification

```bash
pytest tests/test_eagle2_phase0_gates.py -q
python3 -c "import py_compile; py_compile.compile('alpha_engine/eagle2_class_source_cap.py', doraise=True)"
```

## Not in scope (Phase 1+)

Resolver EXPIRED→WON fix, academic_backtest_bridge, ETF forward promotion.
