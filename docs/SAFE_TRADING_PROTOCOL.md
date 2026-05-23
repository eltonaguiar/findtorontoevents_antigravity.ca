# Safe Trading Protocol (v1 — 2026-04-04)

> **NOT FINANCIAL ADVICE (NFA).** This document is an engineering protocol that
> defines which picks our system considers "real-money candidates." It is NOT
> investment advice, a recommendation to trade, or a guarantee of profitability.
> Past performance does not predict future results. All trading carries risk
> of total loss. Paper-trade first.

## Purpose

Define the exact, mechanical criteria under which a pick on
`findtorontoevents.ca/audit` qualifies for **real-money consideration**. Anything
outside these criteria is **paper-only**, no matter how high its score.

## The `antigravity_safe` flag

A pick receives `antigravity_safe: true` when **ALL** of the following hold:

| # | Criterion | Field | Threshold | Rationale |
|---|-----------|-------|-----------|-----------|
| 1 | **ML Composite Score** | `ml_composite_score` | ≥ 0.80 (80/100) | Top of scoring distribution — model has high probabilistic confidence, not just noise |
| 2 | **Whale Concentration Index** | `whale_index` (from WCI module) | ≥ 60/100 (bullish-leaning) | Smart-money / on-chain flow aligns with pick direction. Aggregates Whale Alert, Etherscan, Arkham labeled entities |
| 3 | **Forward-tested WR (historical)** | `strat_fwd_wr` | ≥ 75% with n ≥ 10 | Strategy has real forward-trading edge, not backtest overfit |
| 4 | **Trust tier** | `trust_tier` | `PROVEN` | System has audited track record, not SANDBOX/WATCH/UNPROVEN |
| 5 | **Not degraded** | `_degraded` | NOT `SEVERE` or `HIGH` | Strategy's forward WR has not decayed > 15pp below its reported source WR (see `forward_degradation_tracker`) |

Any pick failing ANY criterion → `antigravity_safe: false` → paper-trading or
further research only.

## Why these specific thresholds

### ML Composite ≥ 0.80
The ML composite weights 60% ML model output + 30% confidence + 10% forward WR
(see `alpha_engine/production_scanner.py::_compute_ml_composite`). 0.80 puts the
pick in the top ~10% of scoring — historically 89.4% Win Rate at this threshold
on BNBUSDT (p-value 0.00029).

### Whale Index ≥ 60
WCI = 0.0-1.0 scale (50 = neutral). 60+ (on 0-100 normalized) means smart-money
accumulation signals. Aggregates 4 data sources:
- Whale Alert (weight 0.15)
- Etherscan (weight 0.15)
- Arkham labeled entities (weight 0.20) — highest because it identifies labeled
  smart-money (Paradigm, a16z, Jump Trading, Wintermute, Galaxy Digital)
- Prediction Markets (weight 0.10)

Remaining 40% weight: pattern-based signals.

### Forward WR ≥ 75% with n ≥ 10
Forward-test minimum threshold — backtests overfit, forward results don't.
Below 75% on 10+ trades, statistical confidence is too low for real-money sizing.

### Trust tier = PROVEN
PROVEN means the system has closed trades that have been audited and validated.
Excludes: SANDBOX (new/untested), WATCH (monitoring), PROBATION (recent losses),
DEMOTED.

### Not degraded (SEVERE/HIGH)
Our `forward_degradation_tracker` measures realized_wr - source_wr per strategy.
If realized drops > 15pp below source (HIGH) or > 20pp (SEVERE), the strategy's
edge has decayed — real-money sizing should wait for inverse/rehabilitation
variants per the Mutate-Before-Kill policy.

## Current "Crown Jewel" Pick (2026-04-04)

**BNBUSDT ml_enhanced_1h LONG** — p-value 0.00029 on the LightGBM model. This
is the most statistically significant pick in the system as of the posting
date. It's in the paper portfolio at $20k allocation.

## Current Paper Portfolio ($100k) — `paper_trading_portfolio_v1.json`

| Symbol | Dir | Strategy | Allocation | Rationale |
|--------|-----|----------|------------|-----------|
| BNBUSDT | LONG | ml_enhanced_BNBUSDT | $20,000 | 89.4% historical WR + ML 1h alignment + p-value 0.00029 |
| DOGEUSDT | LONG | ml_enhanced_DOGEUSDT | $20,000 | 80% historical WR + PM consensus |
| BTCUSDT | LONG | prediction_market_consensus | $30,000 | Kalshi + Polymarket agree + Whale Alert monitoring |
| SOLUSDT | LONG | prediction_market_consensus | $15,000 | Strong PM consensus |
| RENDERUSDT | LONG | ml_enhanced_RENDERUSDT_1h_D_ensemble | $15,000 | ml_score 0.92 + Monte Carlo verified |
| IWM (pending) | SHORT | cta_cross_asset_tsmom | $5,000 | CTA TSMOM bearish signal |
| EURJPY=X (pending) | LONG | fx_smart_carry_trade_momentum | $5,000 | Carry + momentum alignment |

All positions are **paper trades** until we accumulate enough forward
performance data to justify real-money sizing.

## How to filter picks on `/audit/` by this protocol

In the Active Picks table, filter/sort by:
1. `strong = true`
2. `score ≥ 70` (post all penalties)
3. `trust_tier == 'PROVEN'`
4. `_degraded NOT IN ('SEVERE','HIGH')`
5. `antigravity_safe == true` (once UI exposes this field)

Then sort by `score` descending.

## What this protocol explicitly does NOT do

- Does NOT guarantee profit
- Does NOT replace position sizing judgment
- Does NOT account for black-swan events, exchange failures, liquidity crises
- Does NOT consider macro risks (regulatory, geopolitical, funding cost spikes)
- Does NOT constitute investment advice or solicitation

## Versioning

- **v1.0 (2026-04-04)** — Initial protocol. ML≥80, WCI≥60, WR≥75, PROVEN,
  not-degraded. 7-pick paper portfolio.

## Related

- `alpha_engine/production_scanner.py` — computes `antigravity_score` +
  `antigravity_safe` fields
- `alpha_engine/whale_concentration_index.py` — WCI aggregation
- `audit_trail/forward_degradation_tracker.py` — degradation penalty
- `audit_trail/direction_conflict_resolver.py` — removes self-hedging picks
- `updates/index.html` — public-facing entry with NFA disclaimer
- `alpha_engine/data/paper_trading_portfolio_v1.json` — $100k paper portfolio

---

*Maintained by: antigravity-whale-integration, claude-noncrypto-drilldown via Redis agent bus*
