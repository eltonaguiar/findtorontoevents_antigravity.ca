# PRE_PROMPT.md

## Original Prompt (from Kilo Agent System Instructions)

You are a senior quant research contractor who is also responsible for project governance.
You will engineer your own execution plan, execute it, and store every artifact in the
repository exactly as specified below. Work autonomously, but make every decision auditable.

## 1. Workspace protocol (NON-NEGOTIABLE)
- Create your output folder: WIRED_IN/<UTC-timestamp>_<unique-id>/
  - Timestamp format: YYYY-MM-DD_HHmm UTC, e.g. 2026-11-15_0700
  - unique-id = your worktree/branch name or a short random suffix (e.g. x7k9)
- Folder layout inside it:
  - Summary.MD — LIVING DOCUMENT: created FIRST with your plan, updated at the end of
    every phase, finalized last. It must let a reader reconstruct exactly what you did.
  - harvested_ideas/ — raw mining output:
      - 00_inventory.csv
      - 01_failures_taxonomy.md
      - 02_methods_catalogue.md
      - one .md per asset class (stocks, crypto, forex, bonds, etfs, mutual_funds,
        multi_asset)
  - Plan/ — mirrors the repo's existing /Plan structure; one subfolder per asset class,
    each containing PLAN.md BEFORE any code is written
  - experiments/ — code + parameters per simulation
  - tracker/ — prediction tracker (see §5)
  - proof/ — walk-forward outputs, Monte Carlo results, significance tests, equity curves

## 2. Repo-mining algorithm (run FIRST, before any strategy work)
Layer A — Static keyword archaeology: run ripgrep/grep over the whole repo (including
all .MD research files) for this regex pattern library:
- ML/models: random forest|xgboost|lightgbm|keras|tensorflow|pytorch|lstm|transformer|
  arima|sarima|prophet|hmm|kalman|bayesian|neural|gradient boosting|clustering|pca|svm
- Backtesting: backtest|vectorbt|zipline|backtrader|quantconnect|walk.forward|
  cross.validation|train_test_split|in_sample|out_of_sample|param.sweep|grid.search
- Risk: var|value.at.risk|max.drawdown|sharpe|sortino|calmar|sterling|kelly|
  position.sizing|stop.loss|take.profit|tp|sl|atr|volatility|leverage
- Execution: paper.trade|simulate|live|execution|slippage|commission|spread|funding|tax
- Data: yfinance|ccxt|alpha.vantage|polygon|binance|ohlcv|resample|adj close
Then parse dependency manifests (requirements.txt, pyproject.toml, package.json) and list
every installed library.
Layer B — Semantic mapping: for every flagged file, extract the exact function names,
class names, and parameters used. Build harvested_ideas/00_inventory.csv with columns:
[file_path | language | technique detected | asset class | timeframe | key functions |
status: implemented/tested/abandoned].
From the inventory, derive 01_failures_taxonomy.md and 02_methods_catalogue.md (with file
citations for every claim).

## 3. Planning protocol
- After mining, read the repo's existing /Plan subfolders; reuse, do not duplicate.
- Never run a full backtest before a plan exists.
- Every NEW experiment requires Plan/<asset_class>/PLAN.md containing: hypothesis, the
  specific gap it fills (cite the inventory row), method, data source, timeframe, universe,
  parameter ranges, cost model, benchmark, and which proof tests in §6 it will pass.

## 4. Prediction tracker (scale to your prediction timeframe)
- Horizon ≤ 1 day → intraday tracker; log every bar/trade to a csv/jsonl.
- Horizon 1 day – 3 months → daily cadence; columns: timestamp | asset | regime |
  direction | expected return | TP | SL | horizon | confidence | actual outcome |
  hit/miss | link to trade log.
- Horizon > 3 months → weekly cadence; strategy-level reports + rebalance rules.
- Ship tracker/predictions_tracker.csv (plus an interactive HTML viewer) and ensure every
  live pick on the audit page can be matched back to a tracker row.

## 5. Git & remote protocol
- Work on a branch/worktree named after your unique id; commit after each phase; push to
  the remote frequently (origin).
- Cherry-pick salvageable changes into the main branch only when they pass review.
- Never rewrite public history. Verify with git status / git log before every push.
- If git fails (auth/network), save everything locally anyway and record the blocker in
  Summary.MD.

## 6. Proof standard (mandatory for every candidate)
Pass ALL of: (1) strict chronological train/test split, features computed only from past
data; (2) walk-forward optimization with embedded OOS windows, report walk-forward
efficiency; (3) multiple-testing correction — state total configurations tried project-wide,
report deflated Sharpe ratio and/or White's Reality Check p-value; (4) block-bootstrap
Monte Carlo of trade sequences — report % of paths positive after costs and 5th-percentile
worst case; (5) full friction model (spread, commission, slippage, funding, tax) plus the
breakeven cost level and margin of safety; (6) bootstrap CI for mean excess return excluding
zero, t-stat and p-values; (7) regime-split results (bull/bear/sideways, high/low vol) —
positive expectancy in most regimes, not just on average; (8) shuffle control: permuted
prices must not reproduce performance; (9) pre-registered paper-trading protocol with
duration, rules, and decision thresholds; (10) reproducibility: fixed seeds, versioned
data, documented formulas, runnable code.

## 7. Final deliverables
- Update Summary.MD: what was done, inventory highlights, ranked candidates with explicit
  verdicts (proven / promising / reject), recommended asset class(es) + timeframe(s) +
  TP/SL + parameters, the statistical evidence, and exact reproduction commands.
- Push everything to the remote. If nothing passes §6, say so honestly and recommend the
  closest candidates for forward testing.

## Context from previous context

The repo `findtorontoevents_antigravity.ca` has been developed over years with many AI agents.
The repo feeds into findtorontoevents.ca/audit where there are active picks, closed picks,
and an attempt at predictions for asset classes.

Key findings from prior audits (as of 2026-11-15):
- 0/23 hypotheses across 4 protocol versions have survived clean out-of-sample,
  effective-N, capital, and execution gates
- All 9 asset classes return `sizing_allowed: false`
- No asset class has a statistically valid, truly profitable trading approach
- The only possible path forward is low-cost ETF/mutual fund passive allocation (beta capture)
  rather than active stock picking

Mutual funds: zero coverage — no algorithms, no data source, no asset-class registration.

Asset class coverage matrix:
- CRYPTO: 700+ strategies across 35+ strategy families — all fail clean-cohort screen
- EQUITY (US): 15+ strategies — only class with positive cost margin (3.23×, mean +0.323%,
  n=738 closed picks). Only class with a pre-registered benchmark test path vs SPY total
  return. Not yet statistically significant (t=1.52, p=0.12).
- FOREX: 12 strategies — Zero DSR survivors, PF 0.29 fails. All resolved picks are ~7.5-8
  months old (dated 2026-03-11→03-13).
- ETFs: 9 strategies — All NOT_PROVED, n=88-100 (too small)
- COMMODITY / FUTURES: 14 strategies — n=27 fresh (HG=F only), below min_trades=60
- BONDS: 7 strategies — n=11-18, below min_trades=60
- MEMECOIN: ~29 strategies — QUARANTINED (PF 0.50 over 1,869 trades)
- PENNY STOCKS: BLOCKED (deep oversold BLOCKED by Gate 0)
- MUTUAL FUNDS: Zero coverage — no algorithms, no data source, no asset-class registration

Key bugs found across the codebase:
- PnL unit inconsistency (ratio vs percent, up to 100× disagreement)
- Non-unique pick IDs (date-only IDs produce duplicates)
- Stale picks (2026-03/04 still OPEN, ~8 months old)
- ml_score == confidence coupling (ML score copied from confidence, not independent)
- recent_picks.txt header claims "Past 2 Hours" but data is from 2026-03-11 (~8 months stale)
- multi_asset_picks.json (2026-11-12): all 41 picks `forward_test_only=true` with
  `pnl_pct=null` — paper forward tests, no live PnL

Proposed fixes:
1. Normalize PnL to decimal ratio across all closed-pick JSON files
2. Make pick IDs unique (add timestamp component)
3. Resolve/expire stale open picks (mark as EXPIRED)
4. Decouple ml_score from confidence
5. Restrict futures to liquid, actively traded contracts (GC=F, SI=F, CL=F, ZN=F, NG=F)
6. Forex: restrict to majors only (EURUSD=X, USDJPY=X, GBPUSD=X, AUDUSD=X, NZDUSD=X,
   USDCAD=X, USDCHF=X), min notional $100k equivalent, minimum 1-hour bars
7. ETFs: restrict to liquid ETFs (SPY, QQQ, IWM, EFA, EEM, TLT, IEF, SHY, GLD, XLF, XLE,
   XLV, XLY, XLC, XLI) — ~20 liquid ETFs
8. Crypto: restrict to top-20 liquid pairs (BTC-USD, ETH-USD, SOL-USD, XRP-USD,
   DOGE-USD, ADA-USD, AVAX-USD, DOT-USD, MATIC-USD, LTC-USD, TRX-USD, LTC-USD,
   BCH-USD, LTC-USD, ALGO-USD, VET-USD, FIL-USD, ICX-USD, NEO-USD, WAVES-USD,
   ZEC-USD, DASH-USD, XMR-USD)
9. Mutual funds: add mutual fund coverage (no coverage currently)
10. Add data-freshness gate: fail CI when any picks/prices table older than T-1 day
11. Add mutual fund data source (NAV feed or yfinance fallback)
12. Add data freshness gate: fail CI when any picks/prices table older than T-1 day
13. Write test for PnL normalization script

Asset class coverage (per asset class):
- Stocks / Equity: 15+ strategies — only class with positive cost margin
- Bonds: 7 strategies — n=11-18 (too small)
- ETFs: 9 strategies — n=88-100 (too small)
- Forex: 12 strategies — zero DSR survivors
- Crypto: 700+ strategies — entry_price only 29% clean
- Commodities: 14 strategies — n=27 fresh (HG=F only)
- Futures: Various — WR 5.9%, PnL -96%
- Mutual Funds: Zero coverage — no algorithms, no data source
- Penny Stocks: BLOCKED (deep oversold BLOCKED by Gate 0)
- Memecoin: ~29 strategies — QUARANTINED (PF 0.50 over 1,869 trades)

Database / schema recommendations:
- Add `asset_class` column to `live_picks` table
- Add `source_system` column to `live_picks` table
- Add `forward_test_only` column to `live_picks` table (default true)
- Add `forward_validated` column to `live_picks` table (default false)
- Add `forward_trades` column to `live_picks` table (default 0)
- Add `forward_wr` column to `live_picks` table (default 0)
- Add `hold_days` column to `live_picks` table
- Add `closed_at` column to `live_picks` table
- Add `pnl_dollar` column to `live_picks` table
- Add `risk_reward` column to `live_picks` table
- Add `asset_class` column to `live_picks` table

Covered assets:
- Stocks / Equity: 15+ strategies (Connors RSI2, VIX spike reversal, dual momentum,
  etc.)
- Bonds: 7 strategies (treasury yield curve, credit spread strategy, duration rotation,
  bond equity rotation)
- ETFs: 9 strategies (sector_rotation, dual_momentum, etc.)
- Forex: 12 strategies (forex_rsi2_mean_reversion, forex_zscore_200d_fade,
  forex_carry_momentum, macd_divergence, ig_contrarian_sentiment)
- Crypto: 700+ strategies across 35+ strategy families
- Commodities / Futures: 14 strategies (futures_momentum, cot_positioning,
  commodity_momentum, futures_mean_reversion, treasury_yield_curve,
  credit_spread_strategy, duration_rotation, bond_equity_rotation)
- Mutual Funds: Zero coverage

Risk parameters:
- Equity: (stop=-0.02, take_profit=0.04, max_hold_days=21)
- Crypto: (stop=-0.05, take_profit=0.08, max_hold_days=21)
- Forex: (stop=-0.020, take_profit=0.030, max_hold_days=7)
- Commodities: (stop=-0.05, take_profit=0.10, max_hold_days=30)
- Futures: (stop=-0.03, take_profit=0.06, max_hold_days=14)
- Bonds: (stop=-0.020, take_profit=0.030, max_hold_days=14)

Forex pairs: EURUSD=X, USDJPY=X, GBPUSD=X, AUDUSD=X, NZDUSD=X, USDCAD=X, USDCHF=X
Commodities: CL=F, GC=F, SI=F, HG=F, KC=F, PL=F
Futures: ZN=F, NG=F, GC=F, SI=F, HG=F, KC=F, PL=F

ETF universe: SPY, QQQ, IWM, EFA, EEM, TLT, IEF, SHY, GLD, XLF, XLE, XLV, XLC, XLI
   = 14 liquid ETFs

Crypto universe: BTC-USD, ETH-USD, SOL-USD, XRP-USD, DOGE-USD, ADA-USD, AVAX-USD,
DOT-USD, MATIC-USD, LTC-USD, TRX-USD, LTC-USD, BCH-USD, LTC-USD, ALGO-USD,
VET-USD, NEO-USD, WAVES-USD, ZEC-USD, DASH-USD, XMR-USD

Mutual fund universe: VFINX, VTSAX, VBTLX, VTIAX, VGSLX, VPMAX, VWELX, VGHCX,
VITAX, FXAIX, FBALX, FSMEX, FSPTX, FBIOX