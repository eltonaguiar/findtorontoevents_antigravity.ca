# E-1 Insider Open-Market Cluster Buys, Small-Cap (H-028) — 2026-05-18

_Generated 2026-11-22T08:48:27+00:00 by `tools/e1_insider_cluster_buy_research.py`._

## VERDICT: **UNTESTED-data-gap**

**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** No caller in `quality_gates.py`, `dashboard_generator.py`, `passes_active_gate`, `calculate_smart_score`, or any pick-generation / scoring path. Fetches free public SEC Form-4 + price data, writes this report — nothing else.

## The signal

Insider open-market cluster buy — SEC Form 4 transaction code P. A *cluster* is 3+ DISTINCT insiders filing an open-market purchase on the same small-cap ticker within a short window:

- `cluster(D)` = >= 3 distinct insiders, code P, same ticker, within 10 days.
- `total_buy_usd` = summed code-P purchase notional across the cluster's insiders.
- `signal_z` = strictly-past rolling z-score of the cluster's `total_buy_usd` vs the ticker's own prior clusters (conviction magnitude; harness score field = `|signal_z|`).
- direction = LONG only. A cluster is unambiguously bullish revealed preference; insider open-market SELLING is far noisier (diversification, liquidity, tax) and is explicitly NOT used as a short leg.

**Causal mechanism:** insiders have a legal information advantage and a revealed-preference signal — open-market buys with personal capital, when CLUSTERED, are the strongest legal information event available (Cohen, Malloy & Pomorski 2012; Jeng et al.). The edge persists because filings are noisy: most insider activity is options exercise / 10b5-1 plans (code A/M/S/F), NOT code P — careful filtering is the moat.

## Small-cap stratification (pre-registered scope)

The proposal is explicit: the cluster-buy signal is likely arbitraged in mega-caps. This module tests ONLY the SMALL-CAP cohort — tickers with market cap below $2,000,000,000 at cluster time. The full-universe E-1 is deliberately NOT built and NOT pre-registered. Large-cap tickers excluded this run: **0**.

## Construction (legitimate density pattern from H-008/H-019/H-026/H-027)

- **FULL continuous-position LONG-only book** — insider clusters are sparse, so once a small-cap ticker forms a code-P cluster EVERY (ticker, day) for the next 20 trading days is one resolved record. NO post-hoc `total_buy_usd` threshold, NO selection of 'big' clusters. This is the H-008 continuous-hold density pattern, not threshold relaxation.
- **Strict no-look-ahead** — a Form 4 lags the transaction by up to 2 business days. The cluster is stamped at the LATEST filing date of its constituent purchases, becomes visible one day later, and a position on day D sees only clusters visible strictly before D; entry D; return realized over price close(D)->close(D+1).

## Data (free sources only)

- **SEC EDGAR `data.sec.gov`** — submissions API + Form-4 ownership XML (free, no key, SEC-UA required). Code P = open-market purchase; A/M/S/F/G discarded.
- **yfinance** — free, no-key daily close series + `marketCap` scalar (drives the small-cap cut).
- **openinsider.com** — documented free scrapeable fallback aggregator; the canonical path here is the primary SEC EDGAR feed.
- **Sample:** 2850 small-cap ticker-day resolved records.
- **OFFLINE NOTE:** one or more tickers fell back to a labelled synthetic series because a dense free code-P cluster tape was unavailable. The verdict is therefore UNTESTED-data-gap — this run did NOT measure a real edge.

| Ticker | records | wins | gross WR | clusters | note |
|---|---|---|---|---|---|
| AMC | 95 | 48 | 50.5% | 5 |  |
| GME | 95 | 48 | 50.5% | 5 |  |
| PLTR | 95 | 47 | 49.5% | 5 |  |
| SOFI | 95 | 56 | 59.0% | 5 |  |
| RIOT | 95 | 46 | 48.4% | 5 |  |
| MARA | 95 | 45 | 47.4% | 5 |  |
| CLF | 95 | 40 | 42.1% | 5 |  |
| FUBO | 95 | 37 | 39.0% | 5 |  |
| BBBYQ | 95 | 44 | 46.3% | 5 |  |
| WKHS | 95 | 45 | 47.4% | 5 |  |
| SPCE | 95 | 41 | 43.2% | 5 |  |
| NKLA | 95 | 44 | 46.3% | 5 |  |
| GOEV | 95 | 56 | 59.0% | 5 |  |
| RIDE | 95 | 47 | 49.5% | 5 |  |
| OPEN | 95 | 46 | 48.4% | 5 |  |
| CLOV | 95 | 42 | 44.2% | 5 |  |
| WISH | 95 | 51 | 53.7% | 5 |  |
| BIG | 95 | 46 | 48.4% | 5 |  |
| EXPR | 95 | 46 | 48.4% | 5 |  |
| VFS | 95 | 44 | 46.3% | 5 |  |
| LCID | 95 | 46 | 48.4% | 5 |  |
| CHPT | 95 | 56 | 59.0% | 5 |  |
| BTBT | 95 | 37 | 39.0% | 5 |  |
| CIFR | 95 | 47 | 49.5% | 5 |  |
| HUT | 95 | 44 | 46.3% | 5 |  |
| GROW | 95 | 46 | 48.4% | 5 |  |
| TLRY | 95 | 57 | 60.0% | 5 |  |
| ACB | 95 | 48 | 50.5% | 5 |  |
| SNDL | 95 | 56 | 59.0% | 5 |  |
| HEXO | 95 | 42 | 44.2% | 5 |  |

## Harness verdict (THE gate — `edge_stability_harness`, UNMODIFIED)

- per-window eff (new->old): `+0.00 +0.00 +0.00 +0.00 +0.00 +0.00 +0.00 +0.00 +0.00 +0.00`
- windows scored: 10  (strong 0: +0/-0)
- `is_admissible()`: False
- harness reason: REJECTED — only 0/10 windows reach eff>=0.3

## Post-cost gate (15bps round-trip; net must keep >= 60% of gross)

- gross edge: **-1.5045 bps/trade**
- net edge (after 15.0bps round-trip): **-16.5045 bps/trade**
- cost-survival: **0.0%** (floor 60%)
- post-cost gate: **FAIL**

- pooled gross WR: 49.0%
- pooled net WR: 45.6%

## Honest conclusion

**E-1 is UNTESTED — data-gap, explicitly NOT a pass.** A dense free per-insider Form-4 code-P transaction tape was unavailable (the bounded EDGAR ownership-XML walk is not wired), so the run used a labelled synthetic series. This is an honest non-verdict — not a pass and not a clean fail. A real E-1 verdict needs a dense per-insider Form-4 ownership-XML parser (transactionCode == 'P' from ownershipDocument/nonDerivativeTable) so clusters are real, not cadence-proxied.

## next_step

Wire the SEC EDGAR Form-4 ownership-XML parser (walk each Form 4's nonDerivativeTable for transactionCode == 'P', transactionShares * transactionPricePerShare) so the small-cap code-P cluster tape is real. Re-run only with the dense tape.
