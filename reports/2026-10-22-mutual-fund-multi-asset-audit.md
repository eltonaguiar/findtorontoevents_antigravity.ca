# Mutual-Fund / Multi-Asset Audit — 2026-10-22 (directive G next phase)

**Scope:** inspect the existing "variety-pack mutual fund" machinery and judge which
components are actually trustworthy right now. Analyzes [`multi_asset/data/multi_asset_closed.json`](../multi_asset/data/multi_asset_closed.json)
(105 rows) and [`multi_asset/data/institutional_closed.json`](../multi_asset/data/institutional_closed.json)
(23 rows) plus the active pick feed [`multi_asset/data/multi_asset_picks.json`](../multi_asset/data/multi_asset_picks.json)
(43 rows).

## 1. Existing machinery (the "variety pack" already exists)

- [`multi_asset/portfolio_defs.py`](../multi_asset/portfolio_defs.py) is the single source of
  truth: a strategy registry (with backtest status + academic references), per-class symbol
  universes, risk profiles (conservative/moderate/aggressive), QA_checks, and **16 production
  portfolios** covering index futures, stocks, forex, ETF rotation, bonds, penny stocks, COT,
  and crypto on-chain. There is even a `tactical_fund_rotation` strategy mapped to the
  `mutual_fund` asset class.
- Supporting modules: institutional picks engine, monte-carlo validator, per-class strategy
  files (equity/forex/commodity-futures), and a portfolio tracker with a Sharpe allocator.

**Conclusion:** the *machinery* for a variety-pack fund exists. The problem (as the user
suspected) is that its **current components are not earning** — see §3.

## 2. Data-quality findings (the feeds are clean on the big-ticket items)

| Check | multi_asset_closed | institutional_closed | verdict |
|---|---|---|---|
| Placeholder / zero-PnL-suspicious exits | 0 | 0 | ✅ clean |
| Micro-hold < 60 s (instant synthetic fills) | 0 | 0 | ✅ clean |
| Hold duration | all ≥ 1 h | all ≥ 1 h | ✅ genuine holds |
| Status coverage | CLOSED/LOST/WON | CLOSED | ✅ resolved |

> Note: an earlier scan flagged many "micro-holds" here; that was a false positive from a
> lenient timestamp fallback (closed_at read as entry when created_at missing). Re-checked with
> strict `created_at`→`closed_at` semantics: every row has a genuine hold ≥ 1 h. These feeds do
> **not** carry the micro-hold bug fixed in the dashboard feeds. No PnL here is phantom from
> instant fills.

**One real gap:** all 43 active picks in `multi_asset_picks.json` are `forward_validated=False` —
the non-crypto forward-validation loop has not yet stamped them. Until they are forward-validated,
they cannot be treated as proven.

## 3. Performance reality — confirms "current components are bad"

Closed-feed rollups (net Σ PnL%):

| asset_class | n | WR% | Σ PnL% | note |
|---|---|---|---|---|
| FUTURES | 28 | 3.6 | −9.52 | dominated by losing `vix_reversal` |
| EQUITY | 33 | 27.3 | −8.77 | negative |
| ETF | 12 | 25.0 | −3.60 | negative |
| FOREX | 31 | 19.4 | −0.02 | ~flat, slight negative |
| PENNY_STOCK | 4 | 50.0 | −21.35 | institutional feed, heavy loss |

Top strategies (n≥3):
- `vix_reversal` (n=56) **−21.74** — the biggest drag.
- `penny_deep_oversold` (n=4) **−21.35**.
- `hyperopt_connors_rsi2` (n=5) **−13.87**.
- `forex_carry_momentum` (n=4) **−7.98**.
- `extreme_oversold_bounce` (n=13/8) ≈ flat (≈ +0.00 / −14.33 institutional).
- `ema_stack_momentum` (n=12) +0.02 — tiny positive, too small to trust.

Only a handful of *symbol* cohorts are positive at n≥3 (TSLA +1.22, GOOGL +0.24,
XLK +0.03), all n≈3 — nowhere near trustworthy.

## 4. Convergence — the one strategy already proving out in both worlds

`forex_rsi2_mean_reversion` is **both**:
1. the top proven FOREX winner in the dashboard closed-feed analysis (n=37, WR 75.68%, PF
   5.333), **and**
2. the most common strategy in the active `multi_asset_picks.json` feed (8 of 43 picks,
   asset class FOREX).

This is the single strongest convergence signal in the whole codebase: the multi-asset engine
is already emitting the one strategy that has real forward proof. Everything else in the
multi-asset book currently lacks proof (or is a demonstrated loser).

## 5. Verdict & recommendation (directive G next phase)

- **Do not deploy** the current non-crypto mutual-fund components as-is. The closed record is
  net-negative across FUTURES/EQUITY/ETF/PENNY_STOCK, and the active book is not
  forward-validated. This matches the user's assessment that "the components of such mutual
  fund would be bad."
- **Includable now** (from the per-class winners deliverable): FOREX `forex_rsi2_mean_reversion`
  (`CADJPY=X`/`AUDUSD=X`) + the CRYPTO cohorts (`mega_mutation_macd_rsi_m017/m048`, and
  symbols `ENJUSDT`, `ETCUSDT`, `ONDOUSDT`, `THEUSDT`, `POLUSDT`, `WIFUSDT`).
- **Next concrete step** to make the variety-pack real: enable forward-validation stamping for
  the `multi_asset_picks.json` book (clear `forward_validated=False`), and retire/replace the
  demonstrated losers (`vix_reversal`, `penny_deep_oversold`, `hyperopt_connors_rsi2`,
  `forex_carry_momentum`). Re-run the per-class analyzer once a meaningful closed sample
  accumulates for the non-crypto classes (currently n≤31).
