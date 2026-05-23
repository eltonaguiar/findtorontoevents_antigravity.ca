# Baidu Ernie "Top Predictors Playbook" — Filtered Action Items — 2026-05-13

**Source:** Baidu Ernie's Forex/Futures/Crypto top-predictors playbook (user-pasted 2026-05-13). The doc is broad and mostly already covered by our existing queue. Filtering for genuinely net-new items vs duplicates.

## Already in our queue (no new action)

| Ernie item | Where we already have it |
|---|---|
| Funding rate extremes for CRYPTO | P0-B confidence-inversion gate scope + v1 plan's funding_rate_arb.py |
| Monte Carlo robustness | COT Step 7 already shipped per session 1e0e (10,000-seq bootstrap at $5k/$10k/$25k tiers) |
| Walk-forward optimization | PR #940 shipped COMMODITY entry; Charter §9 binding |
| Slippage + commission modeling | P0.5-2 in queue (now load-bearing per `multi_asset_cot_slippage_analysis`) |
| COT report tracking | Already wired via `cot_positioning.py` (PR #941 fix in flight) |
| Confluence requirement (3+ signals) | P1-A FOREX composite ranking captures this (`Final_Score = 0.4·WR + 0.3·Trust + 0.2·Score + 0.1·Liquidity`) |
| Seasonal patterns for commodities | P1 COMMODITY Seasonal Supply-Demand strategy (already queued) |

## Genuinely new — adding to queue

### Tier-A: high-leverage, fits existing infrastructure

1. **Donchian Channel breakout (20-day / 55-day)** as FUTURES strategy
   - Maps directly to my queued "P1 FUTURES mutation-replay" item
   - Turtle Trading rule: buy 20-day high, sell 20-day low; simpler than the SHORT-axis variant I had queued
   - Estimated effort: 1 strategy file + workflow wire-in + tests; 4-6h
   - Expected impact: revives FUTURES class which has n=0 today; not a magic-bullet, just unblocks the data accumulation

2. **Term structure analysis (contango vs backwardation)** for COMMODITY
   - Free CFTC + CME data; complements existing COT positioning
   - Wire: extend `alpha_engine/commodity_seasonal.py` (already opt-in per v1 plan ANTI_OVERFIT_VALIDATOR_ENABLED pattern)
   - Estimated effort: 3-4h
   - Expected impact: COMMODITY edge diversification beyond CT=F single-symbol concentration (per `multi_asset_cot_slippage_analysis` — 94% of trades are CT=F today)

### Tier-B: integration items (P3-P4 stretch)

3. **iTick API** for FOREX/Futures real-time data
   - Free tier; complements existing yfinance fallback
   - But: we have multiple data sources already; this is a "more is better" add, not a gap fix
   - Defer to P3

4. **Nautilus Trader** institutional-grade quant engine
   - This would be a re-platform, not an addition. 5GB+ repo migration cost.
   - Defer to P5 — only valuable AFTER we have stable money-ready picks worth executing at tick-level

5. **Kronos Transformer** for K-line prediction
   - Trained on 45 exchanges; novel as a pure-AI prediction layer
   - We have ml_gatekeeper which is the analogous layer; adding Kronos would be an ensemble member
   - Defer to P4

### Tier-C: do NOT pursue

- **Martingale / Anti-Martingale** — Ernie correctly warns "EXTREME RISK"; explicitly not on queue
- **Grid trading** on CRYPTO — would conflict with the position sizing logic just shipped (PR #945 Charter §7 caps); incompatible with our risk-policy architecture

## Net-new todos (3 items to add)

1. **P1-K: Donchian 20-day breakout strategy for FUTURES** (replaces my P1 FUTURES mutation-replay item; simpler design)
2. **P1-L: Term structure analysis for COMMODITY** (complements seasonal supply-demand)
3. **P1-M: Carry-trade-with-minimum-1-week-hold for FOREX** (per Inception Mercury — combines with SHORT-only rehab; central-bank interest-rate differential as base signal; hold-period filter cuts roll-over noise)

## Inception Mercury cross-check (2026-05-13)

Mercury's playbook of "proven world-known techniques" 90% overlaps Ernie's. Specific net-new beyond Ernie:
- **Exact Turtle parameters** — 20-day entry / 10-day exit / 2× ATR stop / 1% equity risk per ATR (Richard Dennis 1974-1983, 80%+ annualized on diversified futures basket)
- **Carry trade with 1-week minimum hold** for FX (added as P1-M above)
- **Pairs trading z-score gates** — entry at |z|>2, exit at |z|<0.5 (P3 stretch; we don't have a pair construction module yet)
- **Dual Thrust intraday** — `Range = max(H_yesterday, L_yesterday) − min(O_yesterday, C_yesterday)`, breakout at Open ± K×Range (P3 stretch; we're not intraday yet)

Mercury also recommends Backtrader skeleton; our existing test infrastructure is sufficient — Backtrader would be a re-platform cost, not a gap fix.

## What this playbook validates

The "edge = confluence of 3+ signals" framing in Ernie's playbook reinforces our `passes_smart_gate` design where multiple independent signals must align before a pick is sized. The COT timing-leakage finding fits the same frame: a single high-DSR signal isn't enough — needs to survive lag-correction + slippage + concentration checks.

The Donchian-channel grandfather-status of trend-following systems gives historical cover for the suggestion that the FUTURES class can be revived without inventing anything new. Donchian is the strategy least likely to overfit (it has essentially 1 parameter: the lookback window).
