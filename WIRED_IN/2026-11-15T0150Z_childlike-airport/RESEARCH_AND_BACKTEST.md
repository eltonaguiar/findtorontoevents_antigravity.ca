# Research and the replay that did not clear a gate

## What was pulled

`yfinance` 1.3.0, daily, auto-adjusted, period 14 months for the snapshot and 5 years for the replay. 40 symbols, none missing. Snapshot last index 2026-11-15; equity session last bar 2026-11-13.

No model was asked to invent a price. The 429 on `particle-ai/particle-1:free` (see `PARTICLE_1_FREE_429.md`) means that free pool was not usable as a picker. Picks are the rule output, not a chat completion.

## Prior repo evidence used to decide the rule, not to claim edge

- `audit_dashboard/data/money_ready_verdict.json` (2026-11-14): CRYPTO intrabar not ready; EQUITY intrabar PF 0.94; ETF sample thin.
- ETF dual momentum is the only lab strategy previously noted as a Tier-2 candidate (PF 1.60, n=104, Sharpe 1.91 in the incident log). That is a different, longer holding rule than the 96h card below. It was not re-certified here.
- VWAP MR v12 (`/tmp/kilo/regime_filtered_vwap_v12_results.json`): PF 1.210, PBO 0.489. Fails PBO < 0.3. Not emitted.
- 2026-11-15 cost-sensitivity sims in `2026-11-15_AM_profitability-plan/childlike-airport/`: marginal gross edges were often net-negative at 10–30 bps. Those sims are model paths, not this cross-section.

## Replay of this exact 4-day rule

Non-overlapping. Signal on close t using only data through t. Enter next open. Exit on SL (checked before TP if both trade), else TP, else close after 4 sessions. Cost 10 bps round-trip. ATR(14) from data through the signal close. Same eligibility: close > SMA200, 21d > 0, 63d > 0, pick max 63d.

| Sleeve | n | win rate | PF | avg net / trade | sum of net |
|---|---:|---:|---:|---:|---:|
| ETF | 245 | 44.9% | 1.021 | +0.022% | +5.3% over the stitched trades |
| EQUITY | 255 | 45.5% | 1.056 | +0.072% | +18.4% over the stitched trades |

Exit mix was mostly SL and TIME, not TP (ETF 107 SL / 88 TIME / 50 TP). This does not beat a 1.5 PF gate, does not include borrow or gap-through, and is one parameter set chosen because it matches the resolver window. It is good enough to pick a name to watch. It is not good enough to size.

Most frequent historical ETF winner was SOXX (95 of 245). SOXX is below SMA200 today, so the same rule correctly refuses it. Most frequent equity winner was NVDA. NVDA is below SMA200 today, so it is refused.

## Not done

No new purged-k-fold, no PBO, no DSR, no live fill, no mutual-fund NAV, no SubQ call. Those gaps are why every row is `trust_tier=UNPROVEN` and `sizing_allowed=false`.
