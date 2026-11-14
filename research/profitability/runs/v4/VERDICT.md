# v4 Verdict — Crypto Funding-Rate Carry

**Date:** 2026-11-14
**Protocol:** `PROTOCOL_v4.md` (N=3; cumulative N=23)
**Verdict: NOT PROVED — 0/3 passed.**

| Candidate | OOS Sharpe | Notional CAGR | Capital/1.5 CAGR | Cash CAGR | Changes | Status |
|---|---:|---:|---:|---:|---:|---|
| H21 top-5 funding | 6.42 | 5.6% | **3.7%** | 4.5% | 134 | NOT_PROVED |
| H22 BTC-only funding | 14.24 | 7.2% | **4.8%** | 4.5% | **10** | NOT_PROVED |
| H23 top-10 funding | 8.34 | 6.2% | **4.1%** | 4.5% | 142 | NOT_PROVED |

## What is real

Funding carry is a genuine, low-vol return stream: DSR 1.0, bootstrap p05 4.5–11.9, 2× cost
Sharpe 1.7–11.2, and a 5-day execution lag barely dents it. The signal is persistent and not a
price-trend artifact.

## Why it is not a proof of *investable* profitability

1. **Capital multiplier.** A delta-neutral long-spot/short-perp position ties up ~1.5× notional
   (1× spot + ~0.5× perp margin). At 1.5×, top-5 and top-10 return **3.7%/4.1%**, below the
   **4.5% T-bill** benchmark. Only BTC-only clears cash (4.8%), and it has **10 rebalances**, below
   the pre-registered n≥30.
2. **The Sharpe is a low-vol artifact.** 6–14 Sharpe on a ~0.5–0.9% vol carry is not an
   equity-beating Sharpe; it is a cash-plus arbitrage. The economic magnitude is 0–2.7 pp over
   T-bills before capacity, counterparty, and operational costs.
3. **Unmodeled risks:** spot/perp basis, exchange counterparty/solvency, margin calls, withdrawal
   limits, funding-sign reversals, and capacity. Binance venue/regulatory risk is material.
4. **Selection:** the 30-perp universe is current survivors; funding may be lower on delisted or
   lower-quality venues.
5. **Capital efficiency is venue-specific.** Some venues let perp margin earn T-bill yield; others
   do not. A 1.2× multiplier would make top-5 ~4.7% (pass), a 2.0× multiplier makes it ~2.8% (fail).
   The result is sensitive to an operational parameter we cannot verify from public data.

## Conclusion

Funding carry is the closest thing to a real edge in this study, but on the available data and a
conservative capital assumption it does **not** beat T-bills by enough to be a proven investable
strategy. The honest label is **NOT_PROVED / economically marginal**, not "profitable approach
proved." A production version would require venue-level capital/margin data, execution and
counterparty risk modeling, and a forward paper test.
