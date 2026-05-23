# Non-Crypto Edge Hunter Report

**Date:** 2026-04-19  
**Scope:** All non-crypto strategies in `alpha_engine/data/closed_picks.json` (4,503 records) and `alpha_engine/data/strategy_performance.json` (161 strategies).  
**Edge Bar:** Profit Factor > 1.5, Win Rate > 50%, n >= 15 closed trades, symbol-agnostic.

---

## Executive Summary

**Answer: NO.**

There is **no non-crypto strategy** in the entire dataset that meets the edge bar, let alone demonstrates symbol-agnostic profitability. The non-crypto book is effectively non-existent: only **6 closed non-crypto trades** out of 4,503 total (0.13%). All 6 originated from a single copy-trader scraper (`multi_asset_copytrader`) rather than from any dedicated alpha strategy. The dedicated non-crypto strategy files (`equity_strategies.py`, `forex_strategies.py`, etc.) are **orphaned code** — they exist in the repo but are **never imported or executed** by `production_scanner.py`.

---

## 1. High-Bar Scan (PF > 1.5, WR > 50%, n >= 15)

**Result:** Zero strategies qualify.

| Strategy | Category (as recorded) | n | WR | PF | Status |
|---|---|---|---|---|---|
| *Any non-crypto* | — | — | — | — | **NONE FOUND** |

`strategy_performance.json` contains **0 strategies** with `category != "crypto"`. The three strategies with non-crypto-sounding names are still labeled `crypto` in the aggregate file:

| Strategy | Recorded Category | Closed Picks | Win Rate | Profit Factor |
|---|---|---|---|---|
| `forex_rsi2_mean_reversion` | crypto | 8 | 0.0% | 0.000 |
| `futures_momentum` | crypto | 4 | 0.0% | 0.000 |
| `stocks_rsi2_pullback` | crypto | 2 | 0.0% | 0.000 |

> Note: The `strategy_performance.json` counts for these strategies (8, 4, 2) do not match the `closed_picks.json` counts (2, 3, 1) because the JSON aggregates may include forwarded/test data or picks that were later purged.

---

## 2. Best-Looking Non-Crypto Strategies — Symbol Breakdown

Because the dataset contains only 6 non-crypto closed trades, there is no meaningful "best-looking" strategy. Here is the full population:

| Strategy | Asset Class | Symbol | Status | PnL % |
|---|---|---|---|---|
| `futures_momentum` | FUTURES | `SI=F` | WON | +0.0127% |
| `futures_momentum` | FUTURES | `HG=F` | LOST | -0.0579% |
| `futures_momentum` | FUTURES | `PL=F` | LOST | -0.1238% |
| `forex_rsi2_mean_reversion` | FOREX | `USDCAD=X` | LOST | -0.0504% |
| `forex_rsi2_mean_reversion` | FOREX | `EURJPY=X` | LOST | -0.0452% |
| `stocks_rsi2_pullback` | EQUITY | `RIOT` | LOST | -3.097% |

**Assessment:**
- `futures_momentum` touched 3 symbols (SI, HG, PL) but is 1W/2L with a net loss.
- `forex_rsi2_mean_reversion` is 0W/2L across 2 symbols.
- `stocks_rsi2_pullback` is 0W/1L on a single equity symbol.

**Conclusion:** There is **zero evidence of symbol-agnostic edge**. The edge is not even symbol-specific; it is **non-existent** at this sample size.

---

## 3. Overall Non-Crypto Performance by Asset Class

Derived directly from `closed_picks.json`:

| Asset Class | Trades | Wins | Losses | Win Rate | Net PnL % |
|---|---|---|---|---|---|
| **FUTURES** | 3 | 1 | 2 | 33.3% | -0.169% |
| **FOREX** | 2 | 0 | 2 | 0.0% | -0.096% |
| **EQUITY** | 1 | 0 | 1 | 0.0% | -3.097% |
| **TOTAL** | **6** | **1** | **5** | **16.7%** | **-3.362%** |

---

## 4. Break-Even Scan (PF >= 1.0, WR >= 45%, n >= 10)

**Result:** None.

No non-crypto strategy has `n >= 10` closed trades. The maximum non-crypto sample size in `closed_picks.json` is **3 trades** (`futures_momentum`).

---

## 5. "Least Bad" Options

Since nothing is even break-even, the "least bad" choice is the one with the highest sample size and least catastrophic outcome:

| Rank | Strategy | n | WR | PF | Comment |
|---|---|---|---|---|---|
| 1 | `futures_momentum` | 3 | 33.3% | ~0.06 | 3 symbols tested, tiny PnL swings, but still net negative. |
| 2 | `forex_rsi2_mean_reversion` | 2 | 0.0% | 0.00 | 0W/2L, minimal $ losses. |
| 3 | `stocks_rsi2_pullback` | 1 | 0.0% | 0.00 | Single 3% loss on RIOT. |

Even the "best" option (`futures_momentum`) is **3 trades deep**, forward-test-only, and resolved within minutes on 2026-04-17. It is statistically meaningless.

---

## 6. Root Cause: Orphaned Strategies vs. Scrapers

### Do the dedicated strategy files get called?

**No.**

A full-text search of `alpha_engine/production_scanner.py` shows **zero imports** of:
- `equity_strategies`
- `forex_strategies`
- `commodities_strategies`
- `futures_strategies`
- `etf_strategies`
- `bond_strategies`

These modules **do exist** in `alpha_engine/`, and `scanner.py` imports them into dictionaries like `FOREX_STRATEGIES`, `EQUITY_STRATEGIES`, etc. However, `production_scanner.py` only imports one symbol from `scanner.py`:

```python
from scanner import _update_scanning
```

It **never** calls `scanner.get_all_strategies()`, `scanner.run_scan()`, or any function that would touch the non-crypto strategy registries. The non-crypto dictionaries are effectively **dead code**.

### Where do the 6 non-crypto picks actually come from?

Every single non-crypto closed pick has:

```json
"source_system": "multi_asset_copytrader",
"source_strategy_type": "reverse_engineered_multi_asset"
```

They are generated by the copy-trader scraper path inside `production_scanner.py` (see `enrich_forex_stock_picks()` and references to `copy_trader_intel/data/forex_copytrader_picks.json`). They are **not** produced by the standalone quantitative strategies (`forex_strategies.py`, `equity_strategies.py`, etc.).

---

## Final Verdict

### Is there a non-crypto strategy we can trust for real money?

**No.**

The non-crypto pipeline is a **scraper-driven experiment with 6 trades and no proven edge**. The dedicated non-crypto alpha strategies are **orphaned** — present in the repository but never invoked by the production scanner. Until `production_scanner.py` is wired to actually run `FOREX_STRATEGIES`, `EQUITY_STRATEGIES`, `FUTURES_STRATEGIES`, etc., and until those strategies accumulate `n >= 15` with `PF > 1.5` and `WR > 50%` across multiple symbols, there is **no non-crypto strategy fit for real capital**.

---

*Report generated by quantitative analysis of `closed_picks.json` and `strategy_performance.json`.*
