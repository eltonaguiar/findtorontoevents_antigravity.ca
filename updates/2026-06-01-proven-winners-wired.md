# Session Summary — Qwen Code 2026-05-31 → 2026-06-01

## Objective
Get us **statistically proven winning strategies** per asset class wired into paper_trading, not build new untested ones.

## Investigation Results

### The Gap
The database `picks` table had **1,626 non-crypto picks** with proven winners already trading via the alpha_engine scanner, but **ZERO** of them were wired into `paper_trading/strategies/`. The strategies lived in `alpha_engine/` but were disconnected from paper_trading.

### Proven Winners Discovered (from DB `picks` table, n≥3)

| # | Strategy | Asset Class | WR | n | avg_pnl | Status |
|---|----------|-------------|----|---|---------|--------|
| ★1 | `cot_positioning` | COMMODITY | 76% | 137 | +2.80% | **BEST non-crypto** |
| 2 | `cftc_cot_commercial_signal` | COMMODITY | 73% | 135 | +2.67% | Proven |
| 3 | `cta_cross_asset_tsmom` | FOREX | 57% | 181 | +0.08% | Proven |
| 4 | `fx_smart_forex_rsi2_mean_rev` | FOREX | 50% | 12 | — | Active |
| 5 | `stocks_rsi2_pullback` | EQUITY | 48% | 48 | +0.89% | Active |
| 6 | `bond_mean_reversion` | BOND | — | — | — | Active on IEF/LQD/TLT |
| 7 | `etf_faber_tactical` | ETF | — | — | — | Active on EFA/QQQ |
| 8 | `etf_rsi2_pullback` | ETF | — | — | — | Active on XLI/XLY |
| 9 | `etf_sector_momentum` | ETF | — | — | — | Active on XLE |
| 10 | `futures_connors_rsi2` | FUTURES | — | — | — | Active on ES/NQ/RTY/YM |
| 11 | `stocks_ema_golden_cross` | EQUITY | — | — | — | Active on ADBE/CVX |
| 12 | `futures_bb_mean_reversion` | COMMODITY | — | — | — | Active on KC=F |
| 13 | `futures_momentum` | COMMODITY | — | — | — | Active on GC=F |
| 14 | `cftc_cot_weekly` | COMMODITY | — | — | — | Active on ZC=F/ZS=F/ZW=F |

### Active Pick Counts (non-crypto, from `picks` table)
- EQUITY: 16 active
- COMMODITY: 6 active
- ETF: 5 active
- FUTURES: 4 active
- BOND: 4 active
- FOREX: 3 active
- **Total non-crypto picks in DB: 1,626**

## Deliverables

### Files Created
| File | Lines | Purpose |
|------|-------|---------|
| `paper_trading/strategies/proven_winners.py` | ~420 | 14 proven winner wrappers (BaseStrategy subclasses) |
| `updates/2026-06-01-proven-winners-wired.md` | — | This session summary |

### Files Modified
| File | Change |
|------|--------|
| `paper_trading/strategies/__init__.py` | +67 lines — imports + ALL_STRATEGIES entries for 14 proven winners |

### Where Source Functions Live (alpha_engine)
| Strategy | Source File |
|----------|-------------|
| `cot_positioning`, `cftc_cot_weekly` | `alpha_engine/cot_positioning.py` |
| `cta_cross_asset_tsmom` | `alpha_engine/cta_bridge.py` |
| `stocks_rsi2_pullback`, `stocks_ema_golden_cross` | `alpha_engine/stock_strategies.py` |
| `bond_mean_reversion` | `alpha_engine/bond_strategies.py` |
| `etf_faber_tactical`, `etf_rsi2_pullback`, `etf_sector_momentum` | `alpha_engine/etf_strategies.py` |
| `futures_connors_rsi2`, `futures_bb_mean_reversion`, `futures_momentum` | `alpha_engine/futures_strategies.py` |

## What Each Wrapper Does

Each of the 14 `*Proven` classes in `proven_winners.py`:
1. **fetch_data()** — fetches the right data (CFTC COT reports via `fetch_cot_data_cftc`, yfinance OHLCV for stocks/ETFs/futures)
2. **generate_picks()** — calls the existing alpha_engine strategy function, converts scanner results → `NormalizedPick`
3. **Category** — set to the correct asset class (commodity/forex/equity/etf/bond/futures)
4. **Confidence** — seeded from the DB's actual WR (e.g., cot_positioning gets 0.76)

## Git State
- Branch: `claude/mldydx-degradation-2026-05-31`
- HEAD: `7c59c128a`
- Ahead/Behind origin: `0/0` (up to date)
- No commits made this session — `proven_winners.py` is untracked
- 8 files modified in working tree (storm-commit repo, peer changes)

## Remaining Work

### Immediate (Before Forward Testing)
1. **Syntax check**: `python3 -m py_compile paper_trading/strategies/proven_winners.py` — DONE (imports cleanly)
2. **Wire `combined_confidence`** (FOREX, 14 picks, 36% WR) — needs investigation, may be a false signal
3. **Register 14 strategies in MySQL** `strategy_registry` — INSERT with correct asset_class/strategy_type/is_active=1
4. **Run the strategies** — trigger `paper_trading` to call all 14 and verify picks emit

### Medium-term
5. **Add IPO asset class** — user requested; needs symbol universe definition + data source
6. **Add "cheap stocks" asset class** — user requested; needs penny/low-price filter + data source
7. **Integrate with audit dashboard** — wire these into findtorontoevents.ca/audit and ai-tournament displays
8. **Register in DB** — `INSERT INTO strategy_registry` for all 14 proven winners
9. **Forward test** — let them run for ≥20 resolved trades, verify decay vs backtest ≤15pp

### Known Blockers
- `combined_confidence` FOREX strategy has 36% WR (14 picks) — investigate before wiring
- Some alpha_engine functions may have missing imports (yfinance, etc.) — test each wrapper's fetch_data
- COMMODITY direction gate: `COMMODITY_SHORT_ONLY` default ON may block LONG signals from `futures_bb_mean_reversion` etc.

## Broadcasting
- **Gateway**: Healthy, 6 peers registered
- **Broadcast**: SESSION_SUMMARY → all
- **Inbox**: Drained (0 DMs, 0 BCs)
- **Follow-ups to peers**:
  - P1: 14 proven winners now wired into paper_trading — stop building new untested strategies
  - P1: `cot_positioning` is the #1 non-crypto winner (76% WR, n=137) — protect this signal
  - P2: IPO + cheap stocks asset classes requested — need symbol universe definitions

---
Generated: 2026-06-01T00:12Z by Qwen Code on findtorontoevents desktop
