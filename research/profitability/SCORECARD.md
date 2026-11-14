# Goal Scorecard — Profitability Research (v1–v4)

**Scored:** 2026-11-14T19:05Z
**Goal:** find and either PROVE or DISPROVE a statistically valid profitable approach.
**Outcome:** **NOT PROVED** (honest negative) after 23 candidates across four versions.

## Scores

| Criterion | Weight | Score | Basis |
|---|---:|---:|---|
| Pre-registration | 15% | **9/10** | `PROTOCOL.md` + Addenda 1, `PROTOCOL_v3.md`, `PROTOCOL_v4.md` locked before results |
| Data provenance | 15% | **7/10** | Binance spot/funding, Nasdaq ETFs, Treasury.gov, manifests + SHA-256; Nasdaq price-only, no dividends |
| Candidate breadth | 15% | **8/10** | 23 candidates; 30 crypto pairs, 50 ETFs, 30 perps; momentum, reversal, trend, rotation, carry |
| Statistical controls | 20% | **9/10** | DSR, PBO/CSCV, Bonferroni/BH, bootstrap, walk-forward, CPCV, Reality Check/SPA, cost + lag stress |
| Independent replication | 10% | **8/10** | v1/v2 winner replicated exactly + adversarial stats review; v3/v4 not independently replicated |
| Verdict honesty | 15% | **10/10** | H10 downgraded; v3/v4 failures published; capital-adjusted gate added instead of claiming a 14 Sharpe |
| **Process total** | **90%** | **7.7/10** | strong process and breadth |
| **Actual profitability proof** | **10%** | **0/10** | no candidate survives clean-OOS + effective-N + capital + execution gates |
| **Overall** | 100% | **7.0/10** | good science, negative result |

## Version results

| Version | Candidates | Best result | Verdict |
|---|---:|---|---|
| v1 | 7 | H7 RSI2: OOS 1.50 Sharpe, 17.6% CAGR vs 18.6% B&H | NOT_PROVED |
| v2 | +5 | H10 RSI2+cash: 1.83 Sharpe, 22.0% CAGR, DSR 0.978 at N=12 | NOT_PROVED (contaminated OOS; effective N=38; 2-day lag 0.70) |
| v3 | +8 | H16 ETF XS momentum: 0.98 Sharpe vs 1.18 benchmark | NOT_PROVED (0/8; SPA 0.488) |
| v4 | +3 | H22 BTC funding carry: 14.2 Sharpe, 7.2% notional, 4.8% capital-adjusted | NOT_PROVED (economic; n=10; H21/H23 below cash) |
| Peer VWAP | 8 strategies/5 symbols | reported 3.76 Sharpe, PF 1.21 | **FALSIFIED**: correct Sharpe ~1.18 (t=0.91, p=0.18); intrabar stops PF 0.81; CSCV PBO 0.84–0.97; OOS 7.18 months |

## What was learned

1. Daily RSI(2) on 2 assets is execution-fragile and regime-dependent; the apparent 22% CAGR was
   mostly T-bill carry on idle cash.
2. Breadth does not rescue momentum/reversal: 30 crypto pairs and 50 ETFs produced no edge that
   survived walk-forward + Reality Check.
3. Funding carry is a **real** low-vol return stream (DSR 1.0) but is **capital-intensive**; at
   1.5× capital it returns 3.7–4.8% vs 4.5% cash. Only BTC-only clears cash, with 10 trades.
4. A high Sharpe on a low-vol carry is not an equity-beating edge. Economic significance and
   capital efficiency matter as much as statistical significance.
5. The peer "provably profitable" VWAP claim is an artifact: annualization error (3.76 → ~1.18),
   degenerate PBO (proper CSCV 0.84–0.97), ignored intrabar stops (PF 0.81), and a 7.18-month
   OOS mislabelled as 22 months. It is not proof.

## On TradingView contest winners

Contest winners are selected from thousands of entrants; the winners are often the highest-risk
entrants in the winning regime. That is survivorship + multiple testing, not proof of a repeatable
method. The closest "real" edges in this study — T-bill carry and funding carry — are exactly the
kind of low-vol, capacity-limited strategies that do not win leveraged contests. To find a
contest-style edge you need intraday execution, options/vol-risk-premium data, order-flow or
private data, and a capital/risk model; those are outside the keyless data available here.

## What would raise the score

- Independent replication of v4 and venue-level capital/margin data.
- Intraday/order-book or options data for a genuinely different edge family.
- A forward OOS with ≥30 rebalances and the stricter gates (DSR at N≥38, ex-best-day, 2-period lag).
- A risk-matched benchmark gate, not just buy-and-hold.
