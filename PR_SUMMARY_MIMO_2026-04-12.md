# PR summary — MIMO 2026-04-12

## Purpose

Deliver rehabilitation-first **baby strategies** for asset classes with weak aggregate stats (FOREX, COMMODITY/gold), align the **HIGH CONVICTION** dashboard preset with multi-asset `hc_filter.js` behavior, document the wiring, and add a **Hyro → audit** navigation hint for short-term entries.

## Changes by file

| File | Why | Expected benefit |
|------|-----|------------------|
| `baby_strategies/forex_bb_mr_rehab_v1.py` | Bollinger MR rehab on EUR/GBP/AUD USDT proxies | More testable FOREX-side signals without blocking on survivor validation |
| `baby_strategies/paxg_bollinger_mr_rehab.py` | Gold proxy MR on PAXGUSDT | Increases commodity-style coverage using one liquid pair |
| `incubator/backtest_team/forward_signal_scanner.py` | Registers both strategies (`survivor_validated: false`) | Scanner / backtest team can include them in forward experiments |
| `tools/mimo_strategy_validation_smoke.py` | Import + synthetic signal + Monte Carlo bootstrap smoke | Fast regression check per TESTING_PROTOCOL Layer 5 |
| `audit_dashboard/template.html` | HC preset uses **All** assets; clearer hero tooltip | Equities/FX/commodity HC rows visible; less confusion vs crypto-only |
| `audit_dashboard/hyrotrader/index.html` | “Short-term entry radar” card | Operators jump from Hyro research to gated audit picks |
| `docs/HIGH_CONVICTION_FILTER.md` | Documents `hc_filter.js` + All-assets preset | Single source of truth for support questions |
| `docs/ALL_STRATEGIES.md` | Indexes new baby rehab strategies | Discoverability |
| `MIMO_2026-04-12T180000Z.MD` | Edge + strategy narrative | Audit trail for this session |

## Testing performed

- `python -m py_compile` on new Python modules  
- `python tools/mimo_strategy_validation_smoke.py` (exit 0 expected)

## Not in scope

- No change to `alpha_engine/smart_picks_engine.py` or `check_active_picks.py` (per project policy).  
- No live deploy; merge then run your usual `audit_trail` / dashboard generator if you regenerate `index.html` from `template.html`.
