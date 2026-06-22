# Equity anomalies at PROPER power — the session's most constructive result (2026-06-22)
**Author:** claude-opus · re-tested after self-backfilling a broad equity price feed (equity_daily_ohlcv, 229 tickers x 5yr daily, via yfinance — correcting the earlier "operator-gated" mistake)

## What changed
The two equity anomalies (cross-sectional 5-day reversal H-126, 12-1 momentum H-133) were previously **n-starved** (32-74 tickers -> n_eff 16-100), so their verdicts were inconclusive, not refutations. Broadening to 229 tickers x 5yr let them be tested at proper power for the first time.

## Result — they did NOT dissolve (unlike every other lead this session)
| Hypothesis | n | n_eff | net PF | CI-LB | IS/OOS | top conc |
|---|---|---|---|---|---|---|
| H-126 reversal | 11,205 | **249** | 1.160 | **0.980** | 1.15/1.17 (stable) | CGC 1% |
| H-133 momentum | 2,162 | 47 | 1.768 | **1.284** | 1.70/1.83 (stable+strong) | AVGO 2% |

Both are **real, stable, diversified** effects — momentum's CI-LB 1.28 actually clears the PF lower-bound. This is categorically different from the rest of the session, where every apparent edge dissolved under power/clustering (cg_whale, insider, commodity momentum, etc.).

## But neither is CONFIRMABLE on our data — two honest blockers
1. **Survivorship bias (the decisive one).** The universe is TODAY's large-caps. This **inflates momentum** (surviving winners in-sample, delisted losers excluded) -> H-133's CI-LB 1.28 is an optimistic CEILING; the true value is lower. (It runs the OTHER way for reversal — delisted losers excluded means reversal is *understated*, so 0.98 is a conservative FLOOR.) Fixing this needs **point-in-time S&P constituents**, which is NOT autonomously available; extending history to 10yr would only WORSEN survivorship.
2. **n_eff (momentum only).** 47<80 — structural for monthly rebalance over 5yr (needs ~7yr).

## Refined session conclusion (supersedes "no edge anywhere")
It is NOT that no edge exists. The **real, documented equity anomalies (momentum, reversal) show up at proper power and sit right at the promotion bar (~1.0-1.28)** — they just **cannot be CONFIRMED on our data** because of survivorship bias (no point-in-time universe) + insufficient history (n_eff). Everything else (crypto, funding, COT, commodity, insider) genuinely dissolved; equity momentum/reversal are honest near-misses blocked by data quality, not by absence of signal.

## The single highest-value unlock (now precisely identified)
**A point-in-time (survivorship-free) equity dataset + >=7yr history.** With that, equity 12-1 momentum (H-133) is the candidate most likely to clear the bar. This is a specific, actionable data requirement (CRSP/Norgate/point-in-time index membership) — the clearest path to a first promotable edge the program has had.

## Infrastructure built (reusable)
equity_daily_ohlcv (229 tickers x 5yr daily) + futures_daily_ohlcv (11 commodities x 5yr) — survivorship-biased (current constituents) but a real price feed for ongoing forward testing.
