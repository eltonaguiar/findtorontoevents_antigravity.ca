# H-032 CRYPTO intraday order-flow-imbalance reversion (1m) — 2026-05-19

_Generated 2026-05-19T07:03:46+00:00 by `tools/h032_orderbook_imbalance_reversion.py`._

**Status: OPT-IN RESEARCH SIDECAR / 2-4 WEEK PROBE. No production wiring.** Fetches free Binance public 1m klines, runs the pre-registered signal through `edge_stability_harness` (imported UNMODIFIED), writes this report.

## Pre-registered hypothesis (registry `tier2_2026_05_19` / H-032)

CRYPTO intraday order-flow-imbalance mean-reversion at **1-minute** resolution — the one untested data axis the 11 prior daily-bar crypto kills point toward. Per-minute order-flow split from the Binance 1m kline `takerBuyBaseVolume` field (aggressive-buy vs aggressive-sell). OFI = (buy-sell)/(buy+sell); z-scored against a strictly-past 240-minute window. When |OFI_z| >= 2.0 (liquidity vacuum) FADE the imbalance (SHORT a buy spike, LONG a sell spike); enter at the minute close, exit +5 minutes.

**No-look-ahead:** the OFI_z baseline reads only minutes t-240..t-1; OFI_t is the close-of-minute aggregate; entry is close(t), exit close(t+5).

## Data

- Binance public 1m klines via the api-failover chain (api/api1/api2/api3.binance.com), free, no key. ~90d pull. Cached to `tools/cache/h032_orderflow_cache.json`.
- Symbols fetched: 4.
- Continuous-book resolved records (every instrument-minute): **519020**.
- Of which qualifying |OFI_z|>=2.0 extreme-imbalance minutes: **9919**.

| symbol | minutes | records | signal min | wins | WR |
|---|---|---|---|---|---|
| BTCUSDT | 130000 | 129755 | 2524 | 64944 | 50.0% |
| ETHUSDT | 130000 | 129755 | 3334 | 64659 | 49.8% |
| SOLUSDT | 130000 | 129755 | 2067 | 62334 | 48.0% |
| XRPUSDT | 130000 | 129755 | 1994 | 62122 | 47.9% |

## Harness verdict (THE gate — harness imported UNMODIFIED)

- per-window eff (new->old): `-0.01 +0.01 -0.00 +0.02 +0.01 +0.01 +0.01`
- windows scored: 7  (strong: 0)
- sign: `mixed`  same-sign ok: False
- harness `is_admissible()`: False
- harness reason: REJECTED — only 0/7 windows reach eff>=0.3

## Edge & cost survival (over the qualifying extreme-imbalance minutes)

- pooled WR: 50.15%
- gross mean per-trade return: -1.7e-05
- net mean per-trade return (after 30bps): -0.003017
- cost-survival (|gross| > 30bps): 7.5%  (gate >= 60%: FAIL)

## VERDICT: **REJECTED**

Clean kill. Intraday 1m order-flow-imbalance reversion does not separate winners from losers with a stable sign across enough 14-day windows (or fails the 30bps cost gate). The one untested microstructure axis also fails — paper-only becomes the standing verdict. Archive as a tested failure.
