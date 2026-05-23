# PR: MIMO expansion — more rehab strategies + unified copy-trade JSON

## Summary

Adds **two** additional crypto rehabilitation baby strategies (vol-spike capitulation long, stoch pullback in trend), a **merge script** that builds `unified_copytrade_candidates.json` from existing repo data (HL + Polymarket + trusted registry), and documentation for operators.

## Files changed

| Path | Reason | Expected benefit |
|------|--------|------------------|
| `baby_strategies/vol_spike_capitulation_long_rehab.py` | Short-term reversal after volatile bear bar | Research path for low-PF chop regimes |
| `baby_strategies/stoch_pullback_trend_long_rehab.py` | Trend-filtered stoch pullback long | Fewer naked mean-reversion entries in downtrends |
| `incubator/backtest_team/forward_signal_scanner.py` | Register both strategies | Forward scanner / bundle can pick them up |
| `tools/build_unified_copytrade_candidates.py` | Merge HL + PM + trusted JSON | Single file for audit/UI consumption |
| `tools/mimo_strategy_validation_smoke.py` | Import + smoke all four rehab modules | Regression guard |
| `docs/COPY_TRADE_CANDIDATES.md` | How to generate merged list | Less tribal knowledge |
| `docs/ALL_STRATEGIES.md` | Index new strategies | Discoverability |
| `MIMO_2026-04-12T213000Z.MD` | Session narrative | Audit trail |

## Testing

1. `python -m py_compile` on new baby strategies and tools (optional).
2. `python tools/mimo_strategy_validation_smoke.py` (requires `numpy`, `pandas` per `requirements.txt`).
3. `python tools/build_unified_copytrade_candidates.py` — verify JSON row count > 0.

## Not included

- No change to `smart_picks_engine` or `check_active_picks` (project policy).
- No live deploy; regenerate `unified_copytrade_candidates.json` in CI or on a schedule after scrapers.
