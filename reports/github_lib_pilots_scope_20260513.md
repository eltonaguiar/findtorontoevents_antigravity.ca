# Github library integration pilots — scoping doc

**Date:** 2026-05-13
**Status:** SCOPING (no install yet — heavy deps need user approval per CLAUDE.md caution rules)
**Wire-Up rule reminder:** New integration modules MUST have production caller in `calculate_smart_score`/`passes_active_gate`/`passes_smart_gate`/`score_pick`/`smart_picks_engine`/`production_scanner`/`dashboard_generator` — OR explicit `## Wiring Plan` section labelling as opt-in sidecar.

## Pilot #1 — freqtrade

**Repo:** https://github.com/freqtrade/freqtrade (35k+ stars)
**License:** GPL-3.0
**What it brings:**
- Strategy framework (Python class-based, time-series signal emission)
- Hyperopt with Optuna backend (replace our DEAP genetic_programmer)
- Live exec layer (Binance/Kraken/Bybit/OKX out of the box)
- Backtesting engine (already faster than our naive walk-forward)
- Telegram/Discord notifications
- Docker-first deployment

**Heavy deps brought in:** ccxt, scikit-learn, scipy, pandas-ta, numpy ≥1.24, optionally TensorFlow if using FreqAI ML extension.

**Best fit for our edges:**
- **Edge #10 CRYPTO UTC death-zone (06 UTC):** freqtrade native `informative_pair` decorator supports hourly-bin filters. Our NS-C gate ("CRYPTO entries 8-9 UTC blocked") would port as freqtrade `protection: TimeBlock`.
- **Edge #11 BTC 4h regime:** freqtrade `informative_timeframe` exactly fits. BTC 4h close > 10MA = LONG-allowed regime; below = SHORT-or-flat.
- **Hyperopt cross-validation:** purged-CV via custom evaluator; replaces `cycle_*` DEAP loops.

## Pilot #2 — jesse-ai

**Repo:** https://github.com/jesse-ai/jesse (5k+ stars)
**License:** MIT
**What it brings:**
- Cleaner DSL than freqtrade (single-strategy class with `should_long/should_short/should_cancel` hooks)
- Optimization via Optuna
- Built-in indicators library (ta-lib wrapper, fewer install headaches)
- Backtesting + live exec (Binance/Bybit + futures)
- Live-trading mode is more mature than freqtrade for futures

**Heavy deps:** numpy, pandas, ta-lib (C extension — needs compilers on Windows), peewee ORM, click.

**Best fit for our edges:**
- **AA-7 FOREX JPY-cross block:** jesse strategy can directly express `symbol not in ['EURJPY','USDJPY',...]` via universe filter
- **EQUITY top-5 momentum:** jesse `dna()` evolutionary param search for lookback/skip

## Pilot #3 — pandas-ta (lighter dep, install-safe)

**Repo:** https://github.com/twopirllc/pandas-ta (4.5k stars)
**License:** MIT
**What it brings:**
- 130+ technical indicators (RSI, MACD, BB, ATR, ADX, Ichimoku, Volume Profile, etc.) as pandas DataFrame extensions
- Drop-in replacement for ta-lib without C compilation
- Single import: `import pandas_ta as ta; df.ta.rsi(length=14)`

**Heavy deps:** numpy, pandas. That's it.

**Best fit for our edges:**
- Replace any manual indicator computation in `alpha_engine/`
- Add Ichimoku regime overlay to CRYPTO Edge #11 (already validated 4h BTC concept)
- Dedupe indicator code across 12+ alpha_engine modules currently rolling their own RSI/MACD/etc.

**Recommendation: install pandas-ta first, opt-in sidecar in `alpha_engine/integrations/pandas_ta_adapter.py`.**

## Pilot #4 — VectorBT

**Repo:** https://github.com/polakowo/vectorbt (4k stars)
**License:** Apache-2.0
**What it brings:**
- 50-100× faster backtests via NumPy vectorization
- Built-in portfolio analytics (Sharpe, Sortino, Calmar, MaxDD)
- Parameter sweeps in seconds vs our minutes

**Heavy deps:** numba (JIT compilation), numpy, pandas, plotly.

**Best fit for our edges:**
- Hyperparameter scan for momentum lookback/skip across all 5 classes in <1 min vs current 5+ min per class
- Cross-validation matrix (n_long × lookback × skip × universe) for ETF top-3 robustness

## Integration plan (opt-in sidecar pattern)

Per CLAUDE.md "Wire-Up Rule" — none of the above will be wired into production scoring on first PR. Pattern:

1. **Phase 1 — Install as opt-in sidecar:** New `alpha_engine/integrations/<lib>_adapter.py` with `## Wiring Plan` section in PR body.
2. **Phase 2 — Backtest harness wire-up:** Use library in `tools/backtest_*.py` only (no live signal emission).
3. **Phase 3 — Signal-emission test:** Add `*_emit_test.py` in `tools/` that prints what the library *would* emit for current market state, side-by-side with our existing signal. No gate change yet.
4. **Phase 4 — Production wire (gated):** Only after Phase 3 shows ≥30 days of side-by-side agreement and ≥10% Sharpe lift on backtest, add to `passes_smart_gate` with a feature flag (`FREQTRADE_GATE_ENABLED=0` default).

## Wiring Plan (per CLAUDE.md Wire-Up Rule)

| Library | Target caller | Target PR date | Default state |
|---|---|---|---|
| pandas-ta | `alpha_engine/indicators_adapter.py` (new) called from `calculate_smart_score` | TBD (2026-05) | OFF |
| freqtrade | `tools/backtest_freqtrade_harness.py` only, no production caller | TBD (2026-06) | Sidecar only |
| jesse-ai | `tools/backtest_jesse_harness.py` only | TBD (2026-06) | Sidecar only |
| vectorbt | `tools/hyperopt_vectorbt.py` (new) replacing slow `cycle_*` loops | TBD (2026-05) | Tool only |

## What this scoping doc does NOT do

- Does NOT install any library (heavy deps + user approval needed per "modifying packages/dependencies" caution rule)
- Does NOT modify production scoring path
- Does NOT certify any library beats our current implementation — that's Phase 3 work
- Does NOT commit Docker/container infra (freqtrade Docker stack is 4GB+)

## Suggested next step (gated on user approval)

Run `pip install pandas-ta` (lightest dep, zero C compilation, single-import API) and write Phase 1 adapter as opt-in sidecar with explicit Wiring Plan. Defer freqtrade/jesse/vectorbt until pandas-ta integration ships first as proof of pattern.

NFA. Reversible (no production change).
