# Safest-Consensus Picks Analysis — 2026-06-04 23:00 UTC

**Method**: 6-engine swarm review (vllm-large/fast + ollama-large/fast via :4000 LiteLLM proxy; deepseek + xai via api_consult) over consolidated audit context (4154 MISPRICED cleaned, INCIDENT #94 backfilled, per-asset-class verdicts post 7 rounds).

## TL;DR for operator

**3 verified-edge LONG positions** (tournament_picks deduped — ratio 1.00x, NO dup-inflation problem):

| Ticker | n (closed) | WR | avg pnl | Today's avg-entry | 30d ARIMA 95% CI |
|---|---:|---:|---:|---:|---|
| **SPY** | 35 | **82.9%** | +1.56% | $610 (today open consensus, 14 models LONG) | [$677, $845] from current $757 |
| **QQQ** | 33 | **84.8%** | **+2.51%** | (5 models still OPEN) | [$645, $850] from current $741 |
| **IWM** | 34 | 79.4% | +1.45% | $228 (today open, 17 models LONG) | [$256, $332] from current $292 |

**1 anti-consensus AVOID** (high model agreement but the consensus is empirically wrong):
- **MSFT LONG**: n=49 closed at WR 42.9% / avg -0.49%. 9 models still open LONG — operator should NOT follow this.

**5 insufficient-history watch list** (all OPEN today, zero closed history):
- GLD (12 models LONG @ $220), EEM (16 models @ $42.92), AAPL (6 @ $288), JPM (7 @ $194), MA (6 @ $462)

**NVDA / INTC operator-specific**:
- NVDA: 30% LONG WR / 37% SHORT WR — no edge either side. Coin flip. Wait for >5-model consensus + volatility filter before any directional bet.
- INTC: 0/0 closed (all OPEN, TIME_EXIT pnl=0 pre-backfill). Will resolve after next price-tracker rebuild; re-check then.

## Why these three are the safest

1. **Tournament_picks has 1.00x dup-ratio for SPY/QQQ/IWM/MSFT** (verified by query). Unlike at_signal_outcomes which had 5-43x INCIDENT #91 inflation, tournament_picks numbers are honest.
2. **Multi-model consensus** — 14-23 distinct LLM models independently picked LONG with high WR over 30+ closed trades.
3. **Avg PnL +1.45% to +2.51% per trade** — positive expectancy survives even with realistic slippage assumptions.
4. **Tier-1 thresholds** (n>=30, WR>=70%, PF positive) all met for SPY/QQQ/IWM. Tier-2 (n>=100) requires more time.

## Why ARIMA bands are wide (and that's correct)

`tools/forecast_consensus_picks.py` runs ARIMA(1,1,1) on log-closes + ADF stationarity test + 30-day forecast band, logged per-ticker to `mlflow.db`. Results: 30d 95% CI ranges span ±10-15% for all tickers. This is the *correct* finding — equity directional forecasting from price alone is inherently uncertain. The actual edge sits in the tournament-consensus signal, not in time-series extrapolation.

## ML stack roadmap (next 3 commits, swarm consensus)

1. **Dedup-safe aggregation layer over at_signal_outcomes** — row_number() over (strategy, symbol, opened_at) to eliminate ~40K legacy duplicates before any analytics pull (DeepSeek + xai top pick)
2. **Wire automatic tournament_pick row → mlflow.db metrics** — every new pick row appends a metric snapshot; enables real-time dashboard refresh
3. **Add 30d ARIMA bands to bootstrap_forward_stats.json** — operators see forecast confidence per consensus ticker on /audit/data/bootstrap_forward_stats.json

## Files shipped this turn

- `tools/mlflow_verified_strategies_log.py` — logs 6 verified strategy sleeves with WR/PF/cumPnL/ADF (already pushed, commit `b18f9da2ae`)
- `tools/forecast_consensus_picks.py` — ARIMA forecaster for consensus tickers, logs to mlflow.db (this commit)
- `mlflow.db` (gitignored) — local SQLite, view via `mlflow ui --backend-store-uri sqlite:///mlflow.db`

## Operator action items, sorted by leverage

1. **Verify the WR claims independently** before sizing positions — pull yfinance Closes for each ticker's historical entry/exit dates and re-compute the +1.56%/+2.51%/+1.45% per-trade avg returns.
2. **Size SPY/QQQ/IWM positions conservatively** — small sample size (n=33-35) means 95% CI on WR is wide (~67-93%). Quarter-Kelly sizing recommended until n>=100.
3. **Do not follow MSFT LONG consensus** — empirical record shows 42.9% WR. Avoid.
4. **NVDA/INTC**: wait for next price-tracker rebuild + 5+ model agreement before any directional bet.
5. **Open the mlflow UI** to inspect all logged runs visually: `mlflow ui --backend-store-uri sqlite:///mlflow.db` then http://localhost:5000
