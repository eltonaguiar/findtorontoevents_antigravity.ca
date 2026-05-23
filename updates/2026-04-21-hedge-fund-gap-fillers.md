# Hedge-Fund Gap-Fillers — Triple Barriers, Risk Parity, Meta-Labels, Risk Metrics

**Author:** Claude Opus 4.7 (1M context)
**Date:** 2026-04-21
**Status:** EXPERIMENTAL. No production files changed.
**Branch:** `exp/hedge-fund-gap-fillers`
**Related:** PR #297 (cycle 8), PR #298 (AutoHedge committee), PR #299 (cycle 9), PR #300 (skill-vs-luck)

---

## TL;DR — two big findings

1. **The "flat-close bug" is systemic, not isolated.** Triple-barrier audit on 3,500 closed picks finds **684 (20%) labeled FLAT_CLOSE_BUG**. Five CTA strategies are 60-100% flat-close:
   - `non_crypto_consensus` 88/88 (100%)
   - `cta_fx_multifactor` 11/11 (100%)
   - `cta_commodity_momentum_term` 37/46 (80.4%)
   - `ema_stack_momentum` 8/11 (72.7%)
   - `cta_cross_asset_tsmom` 36/57 (63.2%)

   Cycle-8/9 perf-review flagged only `non_crypto_consensus`. Triple-barrier surfaces the other 4 systematically. **This is P0: the resolver path that produces FORCE_CLOSED picks at pnl=0 is miscounting every CTA strategy's outcomes.**

2. **Risk parity flips the portfolio's allocation.** Under inverse-volatility weighting:
   - COMMODITY 44.27% (lowest vol 0.86%, most capital-efficient)
   - FOREX 21.92%
   - ETF 15.66%
   - EQUITY 9.72%
   - **CRYPTO 8.42%** (highest vol 5.60%, currently dominates book)

   Our current de-facto allocation is ~47% crypto by pick count. Risk-parity would drop that to 8.4%, dramatically cutting portfolio risk.

3. **EQUITY is the only class with near-skill-verified stats.** PSR 0.9954 (just below the strict 0.995 bar). Calmar 3.17. This independently confirms PR #298's AutoHedge committee finding that the equity committee hits PF 2.73 on the approved subset.

## Tools built (4 standalone modules)

### 1. `tools/triple_barrier_labeler.py` — canonical {WIN, LOSS, TIMEOUT} labeling

Lopez de Prado method (AFML Ch. 3). For each closed pick, labels the outcome based on which of three barriers hit first:
- **TP barrier** → WIN
- **SL barrier** → LOSS
- **Time barrier** (default 72h) → TIMEOUT, labeled by pnl sign

Degenerate barriers (entry=TP=SL=0 + pnl=0) → **FLAT_CLOSE_BUG** (resolver pathology).

Live-data run found 684/3500 (20%) flat-close bug picks, and 5 strategies with ≥60% flat-close rate. Audit output at `.planning/triple_barrier_audit.json` (gitignored).

### 2. `tools/risk_parity_allocator.py` — inverse-volatility capital weights

Standard hedge-fund allocation: each asset class's capital weight is proportional to 1/stdev. Floor 2%, cap 40%, renormalized. Applied over a configurable lookback window.

Use: decide how to size picks across our 6 asset classes so crypto volatility doesn't concentrate portfolio risk.

### 3. `tools/meta_labeler.py` — secondary-classifier scaffold

Lopez de Prado meta-labeling (AFML Ch. 3.4). Primary signals (our existing pipeline) emit picks; a secondary classifier trained on historical outcomes decides whether to ACT on each primary signal. Scaffold includes:
- `extract_features(picks)` → per-pick numeric feature vectors (time, asset class, score, confidence, conflict flags, kill-window flag)
- `MetaLabelModel` placeholder — pass-through prior today, swap in sklearn/lightgbm when wired
- `train_meta_labeler_from_closed(closed_picks)` — build training set from resolved picks

Wires into AutoHedge committee (PR #298) as a 5th agent: `_agent_meta_label`.

### 4. `tools/risk_metrics.py` — PSR, Sortino, Calmar, Ulcer

Standalone metric library (complements PR #300's DSR). All no-external-deps, all tested. Results per asset class on 3,500 closed picks:

| Class | n | mean% | SR | Sortino | PSR | Calmar | max DD | recovered |
|---|---|---|---|---|---|---|---|---|
| **EQUITY** | 338 | **+0.67** | 0.138 | 0.237 | **0.9954** | **3.17** | -71% | no |
| ETF | 74 | +0.03 | 0.012 | 0.017 | 0.539 | 0.06 | -47% | no |
| COMMODITY | 552 | +0.01 | 0.016 | 0.025 | 0.644 | 0.34 | -22% | **yes** |
| FOREX | 848 | -0.02 | -0.007 | -0.011 | 0.419 | -0.18 | -74% | no |
| **CRYPTO** | 1668 | **-0.79** | -0.142 | -0.171 | **0.000** | -0.91 | **-1449%** | no |

EQUITY PSR 0.9954 is notable — this is the probability that the true Sharpe > 0 given observed skew/kurt/n. Very close to the 0.995 skill-verified threshold.

## What else is in the open-source hedge-fund ecosystem (survey)

For the engineer: here's what's worth investigating but not built in this PR.

### High-impact / low-integration-cost
- **`mlfinlab` (Hudson-Thames)** — Marcos Lopez de Prado's full library. We've now reimplemented triple-barrier + meta-labeling; the rest worth grabbing:
  - Fractionally differentiated features (stationarity without loss of memory) — huge for feature engineering
  - Combinatorial purged cross-validation (CPCV) — proper time-series backtest
  - Sequential bootstrap — proper backtest sampling
- **`alphalens-reloaded`** — alpha factor analysis (IC, quantile returns, tear sheets). Would directly tell us which features in `extract_features` actually predict wins.
- **`pyfolio`** (quantopian) — portfolio tear sheets with drawdown, rolling Sharpe, regime plots. Instant hedge-fund-grade reporting for our dashboard.
- **`empyrical`** — performance metrics (Calmar, Omega, max-DD by month, etc.). Complements our `risk_metrics.py`.

### Medium-impact / medium-integration-cost
- **`vectorbt`** — fast vectorized backtester. Could replace / augment `alpha_engine/walk_forward_backtester.py` with 10-100x speedup.
- **`pysystemtrade` (Rob Carver)** — book-companion systematic trading system. Code is dense but the framework patterns (robust volatility scaling, per-instrument position sizing) are directly applicable.
- **`freqtrade`** — crypto trading bot with built-in hyperparameter optimization. Would improve our crypto committee's R:R floor tuning.

### Higher-integration-cost
- **`QuantConnect/LEAN`** — C# + Python backtesting platform. Heavy but very complete.
- **`zipline-reloaded`** — classic Quantopian engine. Event-driven; good for stocks + ETFs.
- **`hummingbot`** — market-making with CEX connectors. Out of scope unless we go market-making.
- **`backtrader`** — strategy framework. Simpler than LEAN but less battle-tested.

### Data / infrastructure
- **Polymarket subgraph on The Graph** — unblocks the wallet-discovery bottleneck from PR #300.
- **Dune Analytics** — replaces need for custom onchain indexing.
- **Arkham / Nansen** — wallet labeling / flow tracking.
- **Glassnode** — onchain metrics (active addresses, long-term holder supply).

## Concrete follow-ups (priority order)

### P0 — Investigate the flat-close resolver bug

684 closed picks (20%) labeled FLAT_CLOSE_BUG. Five CTA strategies are 60-100% flat-close. Impact:
- Inflates `n_closed` counts in `strategy_performance.json` without actual PnL resolution
- Every WR calculation involving these strategies is distorted (pnl=0 → "loss" in 0.01%-threshold filter)
- `cum_pnl` understates true exposure because true outcomes never resolved

Action: trace every writer to `recent_closed` that sets `pnl_pct=0` with zero barrier distance. Patch the resolver to either (a) retry outcome resolution, (b) mark as UNRESOLVED and exclude from aggregates, or (c) force-label as TIMEOUT with a real pnl sign if closing price is known.

### P1 — Wire risk parity into capital allocation

Add env flag `RISK_PARITY_WEIGHTS_ENABLED=shadow|enforce` in the dashboard or scanner. Shadow mode: compute target weights, log them alongside current de-facto allocation. Enforce mode: scale pick emission by target weight (e.g., crypto picks above the 8.4% weight get rejected at gate time).

### P2 — Train real meta-labeler on historical closed picks

Replace the scaffold `MetaLabelModel` with a real sklearn/lightgbm classifier trained on `recent_closed`. Label = pnl_to_label(). Features from `extract_features()`. Expected outcome: crypto class moves from PSR 0.000 toward ≥0.5 by filtering the most-likely-to-lose primary signals.

Engineering estimate: 1-2 days with a Jupyter prototype, then hardening.

### P3 — Add `alphalens-reloaded` or `pyfolio` for reporting

Instant upgrade to dashboard visuals. Tear sheets would turn cycle-by-cycle perf-reviews into structured reports with rolling metrics.

## Files in this PR

- `tools/triple_barrier_labeler.py` — 160 LOC
- `tools/risk_parity_allocator.py` — 150 LOC
- `tools/meta_labeler.py` — 180 LOC
- `tools/risk_metrics.py` — 180 LOC
- `tests/test_hedge_fund_gap_fillers.py` — **23 unit tests, all pass**
- `updates/2026-04-21-hedge-fund-gap-fillers.md` — this report

**No production files modified.** `audit_trail/quality_gates.py`, `dashboard_generator.py`, and all gate configs are untouched.

## Reproduce

```bash
# Unit tests
python -m unittest tests.test_hedge_fund_gap_fillers -v

# Triple-barrier audit on live data (find flat-close strategies)
python tools/triple_barrier_labeler.py

# Risk-parity target weights
python tools/risk_parity_allocator.py --min-n 20

# Full risk metrics by asset class
python tools/risk_metrics.py --group-by asset_class --min-n 20

# By strategy (top 20 by n) — expect EQUITY strategies to dominate positive-PSR
python tools/risk_metrics.py --group-by strategy --min-n 20
```

## Caveats

- **Static barriers only:** triple-barrier assumes the TP/SL fields in each pick are the intended barriers at emission time. If they've been rewritten post-facto by the dashboard renderer, the FLAT_CLOSE_BUG count may include false positives.
- **Risk-parity ignores regime:** inverse-vol is unconditional — no regime-aware up-weighting during bull crypto markets. A follow-up can add regime-conditional weights.
- **Meta-labeler is a scaffold.** Without a fitted model, the `predict_proba` returns a fixed prior. Scaffold is production-usable today only as a feature extractor.
- **`cum_return_pct` sums additive returns.** For accuracy over long series, compounded returns are better — but our `pnl_pct` is already per-trade-normalized, so additive is the common convention in the codebase.
