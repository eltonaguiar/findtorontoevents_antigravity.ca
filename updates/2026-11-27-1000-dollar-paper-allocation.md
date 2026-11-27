# $1,000 paper allocation — PLAN-2026-11-27-1000

Decision date 2026-11-27. **Paper only. Not investment advice. No order is ever placed by this repo.**

## What the evidence said before allocating

| Class | Live verdict (audit3 ledger, 2026-11-27T12:35Z) | n | Net expectancy/trade | Gate |
|---|---|---|---|---|
| CRYPTO | **KILL** | 7,089 | −0.312% (CI −0.58 / −0.04), PF 0.84 | CI below zero |
| FOREX | **KILL** | 295 | −0.142%, PF 0.60 | CI below zero |
| COMMODITY | **KILL** | 56 | −2.450%, PF 0.19 | CI below zero |
| EQUITY | WEAK | 960 | +0.085% (CI −0.53 / +0.70) | needs 35,533 rows |
| ETF | WEAK | 590 | +0.002% | needs ~29.9M rows |
| BOND | WEAK | 38 | −0.155% | needs 386 rows |
| FUTURES | INSUFFICIENT | 6 | −2.058% | n too small |

Ledger-wide: **0 PROVEN, 1 CANDIDATE** (`crypto_winners` LONG, n=37, WR 73%, +0.634%/trade, DSR 0.666 vs a 0.95 gate).
The review site's own conclusion stands: the only line it would act on is **broad-market beta at ~6.7 bp/yr**, and the bar
every strategy failed to beat is **cash at 4.32%**.

## The allocation

| Sleeve | Weight | Instrument | Entry (2026-11-27) | Why |
|---|---|---|---|---|
| `CORE_BETA` | 70% — **$700** | ITOT (iShares Core S&P Total US Market, ER 0.03%) | $158.64 | The single act-on-able line: market beta at minimum wrapper cost. Expense ratio is the edge, not wrapper type. |
| `CASH_HURDLE` | 30% — **$300** | SGOV (0-3m T-bills) | $100.71 | The 4.32% hurdle is the benchmark nothing beat. Holding it is a decision, not a failure. |
| `SHADOW_CRYPTO` | 0% — **$0** | crypto_winners LONG cell (paper) | BTC $59,791.46 | Only CANDIDATE in the ledger (n=37, DSR 0.666). Fund $100 from `CORE_BETA` **only if** DSR ≥ 0.95 at n ≥ 100 forward rows. |
| `SHADOW_ETF_TREND` | 0% — **$0** | ETF trend forward clock (paper) | SPY $728.32 | Proves whether the trend overlay adds anything over just holding the vehicle. Fund $100 from `CASH_HURDLE` only if it clears 4.32%/yr net. |

Reserve logic: at most **$200 of the $1,000 is ever at risk of leaving beta/cash**, and only against a pre-registered gate.
Until then the expected case is market return on 70% and T-bill on 30%.

## Where this is tracked

Table **`buffy_1000_plan`** in `ejaguiar1_stocks` (`mysql.50webs.com`) — one row per sleeve, created by
`tools/buffy_1000_plan_tracker.py --init`. Columns cover entry, current price, return, benchmark return, TP/SL, max hold,
the funding gate, and status (`OPEN` → `TP_HIT`/`SL_HIT`/`EXPIRED`).

```bash
python3 tools/buffy_1000_plan_tracker.py --init     # create + insert (idempotent)
python3 tools/buffy_1000_plan_tracker.py --resolve  # refresh prices, returns, status
python3 tools/buffy_1000_plan_tracker.py --show     # print state
```

Verified 2026-11-27: table created, 4 sleeves inserted, `--resolve` wrote live prices (SGOV 100.71, ITOT 158.64,
BTC 59,779.23, SPY 728.32) and computed returns and benchmark returns per sleeve.

## Pre-registered predictions (falsifiable)

1. **P-1** — 12 months from 2026-11-27, `CORE_BETA` net return is within ±2 pp of SPY total return minus 0.03%. Falsified if it deviates by more (bad fills/look-through).
2. **P-2** — `CASH_HURDLE` returns > 0 and within 0.5 pp of the prevailing 3-month T-bill yield. Falsified if negative.
3. **P-3** — `crypto_winners` does **not** clear DSR 0.95 by n=100 forward rows. Falsified if DSR ≥ 0.95 at n ≥ 100 (then fund $100).
4. **P-4** — No currently-KILLED class (CRYPTO/FOREX/COMMODITY aggregates) posts a positive net-expectancy CI that excludes zero over the next 100 resolved rows. Falsified if any does.
5. **P-5** — The 70/30 split beats a 100% beta allocation only if the market draws down > 13% over the window (breakeven: 30% × 4.32% vs 70% × drawdown). Falsified if the window ends up strongly positive.

## What would change the recommendation

- A pod clearing the forward gate (n ≥ 100 post-registration, PF CI-LB > 1.0, honest intrabar first-touch on 100%).
- A class whose **2× cost** CI still excludes zero — today none do.
- Repair of the dead FX feed, which would let the AUDJPY hypothesis (DSR 0.815 claimed) actually test.
