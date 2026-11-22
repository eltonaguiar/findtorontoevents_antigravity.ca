# Practical portfolio tracking

Two working tools, both on free data, both runnable today.

## 1. `tools/portfolio_option_backtest.py` — WHICH PORTFOLIO OPTION WINS (renamed 2026-11-22)

> Renamed from `portfolio_tracker.py` per peer request (buffy) to end a name
> collision: THIS file answers "which portfolio option wins on a common window",
> while `tools/recommended_portfolio_tracker.py` answers "what is the live MTM
> value of the tracked pick". Two different questions, two different files.

```bash
python3 tools/portfolio_option_backtest.py --init      # build state from config (real daily data)
python3 tools/portfolio_option_backtest.py --report    # each portfolio on its own window
python3 tools/portfolio_option_backtest.py --common    # ALL on one common window (fair)
python3 tools/portfolio_option_backtest.py --html      # writes portfolio_dashboard.html
```

Config: `portfolios/portfolio_config.json`. State: `portfolios/portfolio_state.json`.
Dashboard: `portfolios/portfolio_dashboard.html` (self-contained, no CDN).

**Why `--report` and `--common` are different commands.** Comparing CAGR across
series that start on different dates is how this project got burned before
(peer buffy caught an AOA-vs-SPY "win" that was purely a window artifact). Use
`--common` for any decision. `--report` exists only to show full history.

### Rules supported
| rule | meaning |
|---|---|
| `buy_hold` | hold target weights permanently |
| `sma_filter` | hold only while `filter_symbol` > its N-month SMA, else cash |
| `rebalance: "monthly"` | re-derive target weights from prices each month |

Signals use data through month `t-1`; trades execute at month `t`'s close. Costs
are charged at `10bp` one-way on **every rebalance leg**.

### Results — common window 2006-04 → 2026-11 (248 months, $10,000 start)

| portfolio | CAGR % | Sharpe | MDD_daily % | terminal $ |
|---|---:|---:|---:|---:|
| P03 60/40 + SPY-trend legs | 6.42 | **0.91** | **−11.68** | 41,072 |
| P02 SPY + 10m SMA filter | 8.93 | 0.81 | −19.61 | 221,095 |
| P01 static 60/40 | 7.63 | 0.81 | −32.35 | 56,681 |
| P00 buy & hold SPY | **10.33** | 0.73 | −50.80 | **286,771** |
| P07 gold + 10m SMA | 7.14 | 0.56 | −37.04 | 57,889 |
| P04 5-asset EW basket + trend | 5.23 | 0.54 | −32.07 | 28,702 |
| P06 bond carry (AGG/TLT/IEF) | 3.23 | 0.46 | −29.14 | 20,412 |

`n_trials = 8`, **not deflated**. Zero forward observations. Not advice.

**Reading it honestly:** buy & hold SPY wins on raw return by a wide margin
($287k vs $41k). The trend overlay does not beat it on return — it gives up
~1.4pp of CAGR to cut max drawdown by **61%** (−50.8% → −19.6%). P03 delivers
the best risk-adjusted figure and the shallowest drawdown but the smallest
terminal value of the equity-heavy options. **If the goal is maximum money, the
answer is boring: buy and hold.** The trend overlays are drawdown insurance paid
for out of return, and that is the only claim they support.

**Diversification alone did not help.** P04 spreads across 5 asset classes and
still lost to single-asset SPY. That independently reproduces peer pasc's
finding that combining strategies reduces variance but does not create expected
return.

## 2. `tools/funding_carry_measure.py` — measure a delta-neutral carry book

```bash
python3 tools/funding_carry_measure.py            # cached
python3 tools/funding_carry_measure.py --refresh  # re-pull funding history
```

No API key needed (ccxt public funding history). Output:
`reports/funding_carry/funding_carry_measure.json`.

**Measured** (BTC/ETH/BNB/SOL/XRP, 2021-01-01 → 2026-11-22, 2,152 days):

| | value |
|---|---:|
| mean funding | **+1.9252 bp/day** = +7.28%/yr |
| carry Sharpe | 3.423 |
| days funding **negative** | **26.8%** (577/2,152) |
| worst day | −362.44 bp |
| **max drawdown of the carry stream** | **−1,045.9 bp (−10.5%)** |
| halves | +2.504 then +1.346 bp/day (**decaying ~46%**) |

Drag sensitivity — the verdict flips between **0.5 and 1.0 bp/day**:

| drag bp/day | net bp/day | Sharpe | CI-LB | verdict |
|---:|---:|---:|---:|---|
| 0.00 | +1.9252 | 3.423 | +0.9717 | PASS |
| 0.50 | +1.4252 | 2.534 | +0.4717 | PASS |
| 1.00 | +0.9252 | 1.645 | −0.0283 | FAILS CI-LB |
| 2.00 | −0.0748 | −0.133 | −1.0283 | FAILS 2× cost |

**The important nuance:** a flat `bp/day` drag model is wrong for this book.
Internal spot↔futures transfers on one exchange are free, so real drag is
`round-trip cost ÷ holding days`. At ~40bp round trip: 30-day hold = 1.33 bp/day
(fails), 90-day = 0.44 bp/day (**passes**), 180-day = 0.22 bp/day. A quarterly
hold therefore likely clears the gate that a monthly hold fails.

## Status

- Back-test only. **Zero forward observations. Zero capital.**
- `portfolio_state.json` is a full monthly replay, not a live positions ledger —
  the last point in each curve is the current mark.
- Next: wire `--init` into a weekly GitHub Action to append real forward
  observations, and replace the replay's final month with a live paper book.
