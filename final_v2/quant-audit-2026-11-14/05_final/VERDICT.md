# 05_Final — Verdict (final_v2, 2026-11-14)

**Bottom line: Do not allocate real money today. No approach is deployed and proven profitable.**

## The Core Problem

Across every review layer — my live-ledger screener (0/166 cells), peers' backtest research (3 approaches, none strictly proved), and protocol v1-v4 (~23 candidates, 0 proved) — the conclusion is identical:

> **Profitable approaches exist in research but none are deployed in the live pick ledger.**

The gap is not "more signal mining" — it is **deployment**. The 683-strategy zoo has been exhausted; it produces 0/166 passing cells. The path forward is to deploy the one or two approaches that already pass research gates, with strict paper-trading gates before any capital allocation.

## What to Deploy (in order)

| # | Candidate | Asset | Why first | Paper-trading duration |
|---|---|---|---|---|
| 1 | Regime-filtered VWAP MR (kilo) | Crypto 4h | Only approach passing all peer gates (Sharpe 3.76, PF 1.21, MDD 10%, PBO 0.489, DSR 1.0) | 90 days or 30 round trips |
| 2 | H10 SPY/QQQ RSI(2) cash | Equity | Came closest in protocol runs (Sharpe 1.83, CAGR 22%) but NOT PROVED — needs clean forward OOS | 90 days or 30 round trips |
| 3 | H22 BTC funding carry | Crypto | Clears T-bill cash (4.8% > 4.5%) but n=10<30 — expand universe first | 90 days or 30 round trips |

## What Not to Deploy

| Class | Reason |
|---|---|
| ETF | Best Sharpe 1.00, fails DSR<0.95 and "0.3 above benchmark" |
| FOREX | Live WR 40.3%, PF 0.66, negative expectancy (−0.53%) |
| BOND | Live WR 33.3%, PF 0.56, n=27 insufficient |
| COMMODITY | n=8 insufficient |
| FUTURES | n=1, WR 0% |
| MUTUAL FUND | No infrastructure exists — add class first, then accumulate data |

## Pre-Deployment Checklist

Before any candidate moves to paper trading:

- [ ] Fix EXPIRED→WON relabeling (`tools/relabel_crypto_expired.py --apply`)
- [ ] Drain zombie picks (53 at pnl=0%) via `tools/resolver_hygiene_check.py`
- [ ] Restart signal_outcomes resolution (currently RED, ~80 days stale)
- [ ] Fix dead price refresh (`fetch_prices.php` HTTP 404 since 2026-04-29)
- [ ] Enable `_FDR_GATE_ENFORCE=1` and `_SINGLE_SOURCE_GATE_ENFORCE=1` (done on `wiring` branch)
- [ ] Add MUTUAL_FUND class to `asset_class.py` + gatekeeper (only if trading mutual funds)
- [ ] Deploy `money_ready_screener.py` as CI gate on every ledger refresh

## Paper-Trading Gates (all must hold continuously)

| Gate | Threshold |
|---|---|
| Decisive trades | n ≥ 100 |
| Win Rate | ≥ 50% |
| Profit Factor | ≥ 1.5 |
| Net expectancy | > 0, bootstrap CI lower > 0 (after slippage 5-15 bps/class) |
| Max Drawdown | < 20% (COMMODITY 55% CTA norm) |
| Single-source | < 60% |
| Multi-source | ≥ 2 independent sources |
| Recency | < 48h |

**Kill switch:** If any gate fails live → halt immediately, return to research.

## Real-Money Gates (only after paper trading clears all above)

Same gates as paper trading, but must hold for the **entire** paper period with no breaches. Position sizing per `config.py` risk_policy.json (max 5% per trade, 10% per symbol, 20% per direction).

## Final Statement

The system's existing surfaces were not profitable (audit verdict FAIL). This independent review also did **not** prove a profitable approach in the live ledger. It did produce **two exploratory candidates** with strong retrospective metrics (kilo's VWAP MR and H10 RSI(2)) that fail the strict proof standard on contamination, multiple-testing, and sample-size grounds.

**Publishing this negative result is the correct outcome. Claiming any approach as "proved" would repeat the original system's error.** Deploy one candidate at a time in paper trading, with frozen parameters and strict gates. Only allocate real money after a candidate clears every Stage-3 gate.
