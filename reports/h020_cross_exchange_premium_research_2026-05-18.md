# H-020 CRYPTO Cross-Exchange Premium (Coinbase Premium Index) — 2026-05-18

_Generated 2026-05-18T19:09:12+00:00 by `tools/h020_cross_exchange_premium_research.py`._

## VERDICT: **REJECTED**

**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** No caller in `quality_gates.py`, `dashboard_generator.py`, or any pick-generation / scoring path. Fetches free public market data, writes this report — nothing else.

## The signal

Cross-exchange price premium — the **Coinbase Premium Index**:

- `premium = (coinbase_usd_close - binance_usdt_close) / binance_usdt_close` on the synchronized UTC daily grid.
- `signal_z` = rolling 30-observation z-score of the premium, strictly-past window.
- direction (momentum): premium z>0 (Coinbase bidding above Binance — US-institutional accumulation leading price discovery) -> LONG; z<0 -> SHORT.
- harness score field = `|signal_z|` (conviction magnitude).

**Causal mechanism:** Coinbase is the dominant US-institutional spot venue, Binance the global retail/offshore hub. A persistent premium proxies the direction of US-institutional net spot flow. The swarm pressure-test (groq/ollama/pollinations 2026-05-18) flagged that cross-exchange arbitrage closes the spread intraday, so the daily-close residual is thin — base rate estimated <20%. A sound prior is not an edge; only the harness + cost verdict counts.

## Construction (legitimate density pattern from H-008/H-014)

- **FULL continuous-position cross-sectional book** — one resolved record per coin per day, NO `|z|` self-selection, NO sparse event filter. This is the H-008-redesign density pattern, not threshold relaxation.
- **Strict no-look-ahead** — the premium z for an entry dated D uses premium observations *strictly before* D; entry D+1; return realized over Binance close(D)->close(D+1). Both venues' UTC daily close on the same grid — no overnight-gap leak.
- `signal_z` = rolling 30-obs z of the premium.

## Data

- **Binance** spot daily klines (failover api/api1/api2/api3), paginated full history.
- **Coinbase Exchange** daily candles (`/products/<p>/candles`, free, no key), paginated backward in 300-candle pages.
- **Sample:** 18153 coin-day resolved records.

| coin | records | wins | gross WR | premium obs |
|---|---|---|---|---|
| BTC | 3165 | 1547 | 48.9% | 3197 |
| ETH | 3165 | 1588 | 50.2% | 3197 |
| SOL | 1765 | 879 | 49.8% | 1797 |
| XRP | 1009 | 508 | 50.3% | 1041 |
| ADA | 1856 | 943 | 50.8% | 1888 |
| AVAX | 1660 | 799 | 48.1% | 1692 |
| LINK | 2486 | 1223 | 49.2% | 2518 |
| LTC | 3047 | 1509 | 49.5% | 3079 |

## Harness verdict (THE gate — `edge_stability_harness`, UNMODIFIED)

- per-window eff (new->old): `+0.64 +0.09 +0.37 -0.04 -0.04 +0.04 -0.57 +0.13 -0.26 -0.21 +0.38 -0.21 +0.14 +0.46 -0.05 +0.35 -0.19 -0.51 -0.04 +0.49 +0.15 +0.19 +0.04 +0.41 -0.09 +0.16 +0.13 -0.41 +0.29 -0.35 -0.29 +0.14 -0.15 -0.25 -0.38 -0.44 -0.64 +0.08 +0.29 +0.49 -0.13 -0.36 -0.19 -0.64 -0.39 -0.53 +0.41 -0.36 -0.20 -0.46 -0.65 +0.38 +0.56 -0.14 -0.46 +0.18 +0.74 +0.41 +0.40 +0.06 -0.07 -0.11 +0.01 -0.42 -0.07 +0.15 +0.40 +0.18 -0.34 +0.21 -0.15 +0.37 +0.17 +0.00 -0.36 -0.56 -0.16 +0.08 +0.03 -0.64 +0.27 +0.15 +0.42 +0.54 +0.36 +0.29 +0.27 +0.31 +0.06 -0.06 -0.04 +0.43 -0.25 -0.15 -0.02 -0.02 +0.14 -0.24 -0.24 -0.04 +0.03 -0.02 -0.04 +0.26 -0.40 +0.06 +0.13 +0.09 +0.03 -0.38 -0.18 +0.13 +0.05 +0.17 -0.09 +0.11 +0.32 -0.03 +0.19 -0.01 -0.09 +0.02 +0.10 -0.24 -0.07 +0.50`
- windows scored: 126  (strong 45: +23/-22)
- `is_admissible()`: False
- harness reason: REJECTED — strong in 45 windows but signs split (23+/22-); needs 3 same-sign

## Post-cost gate (30bps round-trip; net must keep >= 60% of gross)

- gross edge: **9.3137 bps/trade**
- net edge (after 30.0bps round-trip): **-20.6863 bps/trade**
- cost-survival: **-222.11%** (floor 60%)
- post-cost gate: **FAIL**

- pooled gross WR: 49.6%
- pooled net WR: 45.8%

## Honest conclusion

**H-020 was TESTED and REJECTED — kill #11 of the edge hunt.** The continuous-position construction gave the harness real window density, so it rendered a genuine verdict. The harness eff sign splits across windows — the identical failure mode that killed the prior 10 candidates: in-sample separation that flips sign across regimes. A sound prior is not an edge. Do NOT re-test this construction on this sample. Nothing is wired or sized.

## next_step

Kill #11. Cross-exchange daily-close premium does not yield an admissible CRYPTO edge on this sample. Do NOT re-test the daily-close Coinbase-premium z-score on this data. A future retry would need intraday (hourly/minute) premium resolution — the swarm flagged the daily residual is post-arbitrage noise — and a materially different construction (e.g. premium *velocity* around known US-session opens, or a premium-vs-funding interaction), AND must clear `edge_stability_harness` + the post-cost gate before any claim.
