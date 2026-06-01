# Eight-class winning strategies — wired for live paper emission (2026-06-01)

## What was broken

1. **ETF winner** imported `etf_strategies` which uses legacy `from config import` → `ImportError` on Linux/Cursor paths.
2. **FOREX carry** emitted picks without `entry_price` → Layer 2.5 dropped all FOREX rows.
3. **COMMODITY** planting/harvest window is calendar-gated (ISO week 22 = no WHEAT/COTTON window) and `commodity_cross_momentum.py` was never committed to main tree.
4. **CRYPTO** Fear/Greed + multi-day WF strategies correctly return **0** when FGI > 25 and no 3-day momentum stack — chain ended with no live fallback.

## What changed

| Asset class | Backtest / WF winner | Live emitter | Fallback when idle |
|-------------|---------------------|--------------|-------------------|
| CRYPTO | `st_fear_greed_contrarian` (WF PF 2.50) | `winners/crypto_fear_greed_winner.py` | multi-day momentum → vol regime → **funding_rate_arb** (Binance) |
| EQUITY | sector rotation (PF 1.27) | `winners/equity_sector_rotation_winner.py` | — |
| ETF | sector momentum + SMA200 (PF 2.05) | `winners/etf_sector_momentum_winner.py` (inline yfinance) | `etf_factor_regime_rotation` |
| FOREX | carry + VIX gate | `fx_carry_vix_regime.py` + **yfinance entry/TP/SL** | DXY divergence, cross-pair momentum |
| COMMODITY | seasonal WHEAT/COTTON (PF 1.37) | `commodity_seasonal.py` | **`winners/commodity_cross_momentum_winner.py`** (self-contained) |
| FUTURES | TS-momentum (PF 1.68) | `winners/futures_tsmom_winner.py` | — |
| BOND | HYG/LQD momentum (PF 1.65) | `winners/bond_hyg_lqd_winner.py` | — |
| PM | Polymarket API | `polymarket_signals` | paper pilot; L2.5 may filter low-quality entries |

Orchestrator: `alpha_engine/eight_class_flagship_strategies.py`  
Batch tool: `python3 tools/eight_class_winner_hunt.py [--emit]`

## Verification

```bash
PYTHONPATH=. python3 alpha_engine/eight_class_flagship_strategies.py
# Expect n≈20–25 picks across 7 classes (PM optional)

python3 tools/eight_class_winner_hunt.py --emit
# Writes reports/eight_class_winners_YYYYMMDD.json + alpha_engine/data/winning_picks_*.json
```

**2026-06-01 sample:** 24 picks — CRYPTO 5, FUTURES 5, COMMODITY 4, EQUITY 3, ETF 3, FOREX 3, BOND 1.

## Production caveat (Goal #1)

Backtest/WF tiers are **research/paper-pilot**. `/audit` resolved DB track record (`money_ready_verdict.json`) still requires forward n≥20 per class and full TESTING_PROTOCOL layers 3–7 before sizing up. Do not promote to PRODUCTION on historical PF alone.
