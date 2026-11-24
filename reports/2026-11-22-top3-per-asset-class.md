# Top 3 per asset class — and the honest answer to "are we ready?"

**Date:** 2026-11-22 · **Register:** `reports/top3_picks_2026-11-22.json` · **Tracker:** `tools/top3_pick_tracker.py`

## Short answer

**No — we are not ready for a decision of three investments per asset class, and I will not
pretend otherwise.** Of ten classes: one is ready only as a benchmark (EQUITY), one is ready
only as cash (BOND), one is closed on data that does not exist for us (FUTURES), one is
rejected on cost (FOREX), three cannot be measured at all (ETF, MUTUAL_FUND, INDEX/PENNY),
one is a live dispute (COMMODITY), and one is beta wearing a strategy's coat (CRYPTO).

That is not a failure of effort — it is the result of actually checking. The programme has
produced **zero** money-ready classes and **zero** forward observations, and the register
below is deliberately built so that it cannot be quietly rewritten later.

## What I would actually pick, today, in one line

**VT (or SPY) for the core, BIL for the cash sleeve, 0 % commodity, and crypto at most as a
sized speculative sleeve labelled beta.** No signal from this project earns money yet, so
the correct allocation is the cheap index plus the T-bill that most of our "weak" strategies
fail to beat.

## Per class, with the number that decides it

| class | readiness | rank 1 | rank 2 | rank 3 | the number |
|---|---|---|---|---|---|
| EQUITY | benchmark only | SPY | QQQ | RSP | H-201 DSR 0.9469 — fails by 0.003 |
| ETF | not ready | VT | VTI | SPY | no survivorship-free panel for C5 |
| BOND | cash only | BIL | AGG | TLT | 1.5 % MER = −33.6 % terminal wealth / 30y |
| COMMODITY | open dispute | GLD | DBC | CPER | BH −0.81 %/yr, MDD −62.5 %; trend −2.16 %/yr |
| CRYPTO | beta only | BTC | ETH | funding book | BTC Sharpe 0.911 but DD −83 %; carry dies at 2× cost |
| FUTURES | unmeasurable | — | — | — | no free roll-adjusted contracts exist |
| FOREX | rejected | — | — | — | cost ≥ assumed edge |
| MUTUAL_FUND | peer-measured | VWELX | VBIAX | — | peer Sharpe 1.013/0.999 vs SPY 0.958, AS_STORED |
| PENNY | insufficient n | — | — | — | data quality |
| INDEX/THEMES | no data | — | — | — | no constituent history |

## Why pre-register instead of just answering

Because a pick that can be changed after the outcome is not a pick, it is a story. The
register was written **before** any entry price was fetched; the tracker may add
`entry_price`, `entry_date` and returns, and may never reorder, re-tier or rewrite a
thesis. A symbol that fails to price is reported `NO_DATA` and stays in the denominator.

```
python3 tools/top3_pick_tracker.py --init    # freezes entry prices (run once)
python3 tools/top3_pick_tracker.py --run     # marks to market, appends to data/top3_picks_history.jsonl
```
Tests: `tests/test_top3_pick_tracker.py` (5, passing) — including the two failure modes that
matter: no entry price must surface as `NO_PRICE`, and missing market data must never shrink
the denominator.

## What would move a class to READY

- EQUITY: one pre-registered rule with DSR > 0.95 at the honest trial count, both halves, 2× cost.
- COMMODITY: Mercury3's weight function, so the +3.59 % vs −2.16 % question closes.
- ETF / INDEX: a survivorship-free membership panel with delisting dates.
- CRYPTO: one measured margin-rebalancing cost number.
- FUTURES: any roll-adjusted continuous panel at all.

Until then the register stands, and the picks are paper. Zero capital sanctioned. This is not
investment advice.
