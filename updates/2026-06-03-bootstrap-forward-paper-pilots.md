# 2026-06-03 — Bootstrap forward paper pilots (B_flip + inverse_ml BTC)

## What changed
Added virtual forward books for the two bootstrap-approved strategies from PR #482 (`updates/2026-06-02-suspicious-pass-investigation.md`):

- `B_flip_PriceRocMeanReversion` — inverted PriceRoc mean-reversion on BTCUSDT 1h
- `inverse_ml_enhanced_BTCUSDT_15m_D` — SHORT via `ml_strategy_reviver` inverse pick logic

Wired into `tools/run_verified_pilots_daily.py`, `tools/bootstrap_forward_stats.py`, and `tools/pilot_forward_dashboard.py`.

## Production safety
- `production_enable: false` on both pilots
- No scanner env flags (`B_FLIP_PRICEROC_ENABLED`, `INVERSE_ML_BTC_15M_ENABLED`) — documentation only until forward `n>=100`
- `money_ready_verdict.json` still governs capital (`freeze_promotions`)

## Files
| Path | Role |
|------|------|
| `verified_strategies/paper_pilot/b_flip_price_roc_forward_pilot.py` | Daily virtual SHORT book |
| `verified_strategies/paper_pilot/inverse_ml_btc_forward_pilot.py` | Daily inverse ML BTC book |
| `verified_strategies/paper_pilot/pilot_forward_summary.py` | Shared PF/WR/gates |
| `tools/bootstrap_forward_stats.py` | Aggregates both sleeves |

## Verify
```bash
python3 verified_strategies/paper_pilot/b_flip_price_roc_forward_pilot.py
python3 verified_strategies/paper_pilot/inverse_ml_btc_forward_pilot.py
python3 tools/bootstrap_forward_stats.py --write
python3 tools/run_verified_pilots_daily.py
```

## Refs
- PR #482 suspicious PASS investigation
- `reports/bootstrap_forward_stats_latest.json`