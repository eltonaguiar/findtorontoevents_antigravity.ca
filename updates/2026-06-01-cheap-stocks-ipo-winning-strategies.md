# CHEAP_STOCKS + IPO asset classes — statistically vetted winners (2026-06-01)

## User ask

Add **IPO** and **Cheap Stocks** as new asset classes with **statistically proven** edges (not placeholder seeds).

## CHEAP_STOCKS — PASS (paper-pilot TIER_2)

**Strategy:** `cheap_stock_cross_momentum_winner` — cross-sectional 63d momentum on liquid names in **$2–$12**, top-5, 21d rebalance.

**Backtest:** `python3 tools/backtest_cheap_stock_momentum.py`

| Metric | Value |
|--------|-------|
| n (rebalance periods) | 31 |
| Win rate | **61.3%** |
| Profit factor | **2.79** |
| Evidence file | `audit_dashboard/data/cheap_stock_momentum_backtest.json` |

**Live emitter:** `alpha_engine/winners/cheap_stock_momentum_winner.py` (yfinance only — no hardcoded prices).

**Removed:** fake SOUN/PLUG placeholder picks from `unique_cheap_stock_momentum_squeeze.py` (violated no-placeholder rule).

**Caveats:** high backtest MDD (~57%); probation sizing (max AUM ~$75k/pick, 25bp slippage). Not production until forward n≥20.

## IPO — REHAB only (not a “winner” yet)

**KILLED:** `ipo_lockup_expiry` SHORT — n=23, WR 34.8%, PF 0.18 (`reports/ipo_lockup_backtest_2026-05-17.md`).

**Research variant:** `ipo_post_listing_momentum_long` (T+90d entry, 60d hold)

| Metric | Value |
|--------|-------|
| n | 24 |
| Win rate | 41.7% |
| Profit factor | 1.16 |
| Tier | **REHAB** (WR &lt; 45%) |

**Live emitter:** `alpha_engine/winners/ipo_post_listing_winner.py` — emits **only** when a name is 85–150 days post-IPO with positive 63d momentum; **often empty** (correct).

## Wiring

- Registry: `alpha_engine/eight_class_flagship_strategies.py` (+ `CHEAP_STOCKS`, `IPO`)
- Score floors: `config.py` `MIN_ELITE_SCORE_BY_CLASS`
- Hunt report: `python3 tools/eight_class_winner_hunt.py --emit`

## Verification

```bash
python3 tools/backtest_cheap_stock_momentum.py
python3 tools/backtest_ipo_post_listing_long.py
PYTHONPATH=. python3 alpha_engine/eight_class_flagship_strategies.py
```
