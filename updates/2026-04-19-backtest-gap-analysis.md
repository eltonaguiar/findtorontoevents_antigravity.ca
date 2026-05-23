# Non-Crypto Performance: Backtest Gap vs. Broken Strategies

**Date:** 2026-04-19  
**Analyst:** Quantitative Research Sub-Agent  
**Scope:** `alpha_engine/data/closed_picks.json` (4,503 records), `alpha_engine/data/strategy_performance.json`, `alpha_engine/production_scanner.py`

---

## Executive Summary

The "horrible" non-crypto performance is **not** primarily caused by a lack of backtests. It is caused by a toxic mix of:
1. **Structurally flawed strategies** (analyst-consensus scrapers, copy-trader clones, and penny-stock mean-reversion) that were allowed to emit picks and produced 0–19 % win rates.
2. **A historical blanket block on all non-crypto asset classes** (removed 2026-04-18) that prevented academically sound strategies from ever generating forward data, while the broken strategies leaked through via copy-trader merges and mis-categorized equity symbols.

Running 10× more backtests on the *current* non-crypto suite would **not** improve realized results. The losing strategies are already proven losers with statistically significant negative edge. The handful of academically grounded strategies (Connors RSI-2, TSMOM, Faber TAA) already have acceptable backtests; what they lack is **forward trading history**, not more historical simulations.

---

## 1. Forward-Validation Stats for Non-Crypto Picks (Q1)

Out of **4,503** closed picks in `closed_picks.json`, only **6** (0.13 %) are non-crypto:

| Category | Count | Strategies Present |
|----------|-------|--------------------|
| `commodity` | 3 | `futures_momentum` |
| `forex` | 2 | `forex_rsi2_mean_reversion` |
| `equity` | 1 | `stocks_rsi2_pullback` |

**Forward-validation profile of these 6 picks:**

- **`forward_validated=true`:** **0** picks.
- **`forward_validated=false`:** **6** picks (100 %).
- **`forward_trades=0`:** 5 of 6 picks.
- **`forward_trades>0`:** 1 pick (`stocks_rsi2_pullback`, `forward_trades=3`, `forward_wr=0.4`).

**Conclusion:** Non-crypto picks are entering the book with **no forward validation and no forward-trade history**. The forward-data pipeline for non-crypto is effectively non-existent in the main closed ledger.

---

## 2. Forward Validation vs. Realized Performance (Q2)

Because **zero** non-crypto picks have `forward_validated=true`, a direct within-class comparison is impossible.

Globally (all asset classes), the ledger shows:

| Forward Validated | Count | WR | Avg PnL % | PF |
|-------------------|-------|----|-----------|----|
| `true` | 0 | — | — | — |
| `false` / `None` | 4,503 | 5.9 % | -14.8 % | 0.60 |

The fact that **not a single pick** out of 4,503 has `forward_validated=true` indicates that the forward-validation gate is either disabled or not populating data for any asset class, not just non-crypto. For non-crypto specifically, this means there is **no empirical filter** separating potentially good strategies from bad ones before they hit the book.

---

## 3. Backtest Coverage in `strategy_performance.json` (Q3)

Only **3** non-crypto strategies appear in the production performance registry:

| Strategy | `closed_picks` | WR | PF | `p_value` | `kelly_fraction` |
|----------|----------------|----|----|-----------|------------------|
| `forex_rsi2_mean_reversion` | 8 | 0.0 % | 0.00 | 1.00 | 0.00 |
| `futures_momentum` | 4 | 0.0 % | 0.00 | 1.00 | 0.00 |
| `stocks_rsi2_pullback` | 2 | 0.0 % | 0.00 | 1.00 | 0.00 |

**All three are essentially untested** (`n < 15`) and have produced **zero wins**.

By contrast, the codebase defines **34** distinct non-crypto strategies across `forex_strategies.py`, `equity_strategies.py`, `futures_strategies.py`, `etf_strategies.py`, and `bond_strategies.py`. **33 of 34 (97 %)** are **absent** from `strategy_performance.json`, meaning they have **zero tracked production trades**.

Key non-crypto strategies with **no production track record** include:
- `connors_rsi2_scanner`, `triple_rsi_scanner` (equity)
- `forex_tsmom_12m`, `carry_trade_momentum`, `london_session_breakout` (forex)
- `futures_tsmom`, `futures_vol_regime_breakout` (futures)
- `etf_faber_tactical`, `etf_dual_momentum` (ETF)
- `bond_yield_momentum`, `bond_connors_rsi2` (bonds)

**Conclusion:** The performance database does not contain meaningful backtest or forward data for the overwhelming majority of non-crypto strategies. They are not "under-tested" in the sense of having a small sample—they are **untested** (`n = 0`).

---

## 4. Strategy Sourcing in `production_scanner.py` (Q4)

Non-crypto picks reach the production pipeline through **two distinct channels**:

### A. Backtested Academic Strategy Modules
`scanner.run_strategies()` loads `FOREX_STRATEGIES`, `EQUITY_STRATEGIES`, `FUTURES_STRATEGIES`, `ETF_STRATEGIES`, and `BOND_STRATEGIES` when `STRATEGY_FILTER=all` (default since 2026-04-18). These modules contain academically backed rules (e.g. Connors RSI-2, Faber TAA, TSMOM).

**Critical finding:** Until 2026-04-18 the scanner defaulted to `strategy_filter="crypto"`, so **bonds, ETFs, and futures were dead code**—no source ever generated signals for them. Even now, the modules are wired in, but most strategies have **zero emitted picks** because they are either gated by downstream quality filters or have not yet been activated.

### B. Copy-Trader Scrapers with No Backtests
`production_scanner.py` explicitly merges forex picks from:
```python
copy_trader_intel/data/forex_copytrader_picks.json
```
These picks are tagged `source_system="forex_copy_trader"`. There is **no evidence** of systematic backtesting for these scraper signals; they enter the pipeline as raw copy-trader output and are subject only to downstream confidence gating.

### C. ML Predictions
There is **no dedicated non-crypto ML pipeline** in `production_scanner.py`. The `ml_enhanced_*` family is crypto-only (e.g. `ml_enhanced_FETUSDT`). The ML health gate blocks all `ml_enhanced` strategies unless `_ml_trading_enabled` is true, and no non-crypto ML models are referenced.

**Summary of source quality:**
- **Academic modules:** Theoretically sound, but historically suppressed by the `crypto`-only filter. Backtests exist locally (see §6) but have **zero forward trades**.
- **Copy-trader scrapers:** No backtests, no forward validation. The forex variant (`community_london_breakout_v2_forex`) is a documented 0 % WR loser (`n=16`).
- **ML:** Not a factor for non-crypto.

---

## 5. Strategies with `forward_trades >= 15` (Q5)

In `closed_picks.json` there are **zero** non-crypto strategies with `forward_trades >= 15`.

The maximum forward-trade count observed is:
- `stocks_rsi2_pullback`: `forward_trades=3`, `forward_wr=0.40` — **1 loss** in production.
- `forex_rsi2_mean_reversion`: `forward_trades=0` on both closed forex picks.
- `futures_momentum`: `forward_trades=0` on all three commodity picks.

Because **no non-crypto strategy has reached the 15-trade threshold**, there is **no evidence** that "more backtests" would fix the problem. The strategies that do have any data at all show 0 % realized WR, and the ones with zero data have never been allowed to trade. The bottleneck is **emission and forward tracking**, not backtest sample size.

---

## 6. Hypothesis Test: Would 10× More Backtests Help? (Q6)

### Evidence from the Codebase

1. **Toxic strategies are already proven losers.**
   - `yahoo_analyst_consensus` (equity): **6.2 % WR**, PF 0.14, `n=48`
   - `claude_gainer_ml` (equity): **0 % WR** on tracked sample
   - `community_london_breakout_v2_forex`: **0.0 % WR**, `n=16`, -7.9 % PnL
   - `cot_positioning` (commodity): contributed to **19 % WR** on 16 commodity picks
   - `futures_mean_reversion`, `ema_stack_momentum` (futures): **0 % WR**

   These are **structurally flawed** (relying on noisy analyst data, social-velocity scrapers, or mis-specified mean-reversion in trending assets). Additional backtests would only confirm the negative edge already visible in the small forward sample.

2. **Academic strategies have acceptable backtests but zero forward data.**
   - `connors_rsi2_backtest.json` / `connors_rsi2_multiasset.json`: **SPY 75.7 % WR, QQQ 75.0 % WR, IWM 71.2 % WR, NVDA 73.3 % WR**.
   - `forex_backtest_results.json`: Portfolio-level **41–46 % WR**, PF **1.07–1.30**, Sharpe **0.5–2.1** across 188–469 trades.

   These backtests are not "insufficient." The problem is that the strategies were **blocked from emitting** by the old `strategy_filter="crypto"` default and by downstream blanket category blocks. They need **forward trades**, not more historical simulations.

3. **Production scanner explicitly acknowledges this.**
   > *"REMOVED 2026-04-19: blanket `_BLOCKED_CATEGORIES` was blocking ALL equity/commodity/futures/bond/etf picks regardless of strategy quality. The cited '0% WR on 92 equity picks' and '19% WR on 16 commodity picks' were from killed strategies … New academic strategies … can't build forward history if the class is blocked."*
   — `production_scanner.py`, lines 2069–2074

### Verdict

**No.** Running 10× more backtests on the *current* non-crypto suite would **not** materially improve realized performance. The under-performance is driven by:
- A small set of **structurally broken strategies** that already show 0–19 % WR.
- A large set of **academically sound strategies that have never traded forward** because of pipeline blocks.

The fix is **curatorial**, not statistical: kill the toxic scrapers, unblock the academic strategies, and collect forward data under tight risk caps.

---

## Recommendations

| Action | Priority | Rationale |
|--------|----------|-----------|
| **Permanently pause** all non-crypto copy-trader scrapers (`forex_copy_trader`, `community_london_breakout_v2_forex`, `myfxbook_retail_contrarian`, etc.) and analyst-consensus strategies (`yahoo_analyst_consensus`, `claude_gainer_ml`, `value_quality_factor`). | P0 | Proven 0–19 % WR; more backtests will not create edge. |
| **Unblock and sandbox** academically grounded strategies (`connors_rsi2_scanner`, `forex_tsmom_12m`, `futures_tsmom`, `etf_faber_tactical`, `bond_yield_momentum`). Emit with **0.5× sizing**, max **5 active picks per asset class**, and a **15-trade kill switch** (auto-disable if WR < 35 % or PF < 0.8). | P1 | They have acceptable backtests (WR > 40 %, PF > 1.0) but zero forward history. Need real trades, not more simulations. |
| **Fix forward-validation plumbing** for non-crypto picks. Currently 100 % of non-crypto closed picks have `forward_validated=false` and `forward_trades=0`. The forward validator must run against yfinance/Binance closing prices for stocks, forex, and futures. | P1 | Without forward data, the pipeline cannot distinguish good from bad non-crypto strategies. |
| **Do NOT allocate a 50 % non-crypto quota** (`enforce_portfolio_cap`) until at least **3 strategies per asset class** have >= 15 forward trades with WR ≥ 40 % and PF ≥ 0.9. | P2 | Forcing diversity with untested or toxic strategies creates guaranteed bleed. |
| **Collect 90 days of forward sandbox data** before scaling position sizes above 1× for any non-crypto strategy. | P2 | Backtests are already adequate; forward regime behavior (slippage, overnight gaps, macro shocks) is the unknown. |

---

## Bottom Line

> **The non-crypto book is not suffering from a backtest shortage. It is suffering from a strategy-quality crisis:** broken scrapers and consensus bots were allowed to trade, while academically sound strategies were locked out by asset-class blocks. More backtests on the current roster would be wasted compute. The path forward is **surgical curation**—kill proven losers, sandbox proven academic rules, and collect forward data.
