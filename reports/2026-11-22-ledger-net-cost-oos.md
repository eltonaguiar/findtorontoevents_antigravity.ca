# Net-of-cost ledger audit and out-of-sample split — 2026-11-22

Source: `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_dashboard/data/dashboard_data.json` · 3500 closed picks · `after_cost_net_per_trade` present on **0/3500**.

Costs are a stated round-trip model (fees + slippage), not measured fills:

| class | bps |
|---|---|
| CRYPTO | 20 |
| EQUITY | 10 |
| ETF | 10 |
| FOREX | 8 |
| COMMODITY | 12 |
| FUTURES | 12 |
| BOND | 10 |
| (default) | 15 |

## Class edge, gross vs net

| class | cost bps | n | WR net | CI low net | breakeven net | PF gross | PF net | exp gross % | exp net % | breakeven cost bps | verdict gross -> net |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CRYPTO | 20 | 2070 | 44.9% | 42.8% | 40.8% | 1.313 | 1.184 | +0.5355 | +0.3355 | +53.5 | PROVEN -> NOT PROVEN |
| EQUITY | 10 | 690 | 47.1% | 43.4% | 43.1% | 1.229 | 1.175 | +0.4609 | +0.3609 | +46.1 | PROVEN -> NOT PROVEN |
| ETF | 10 | 503 | 43.3% | 39.1% | 43.8% | 1.071 | 0.981 | +0.0776 | -0.0224 | +7.8 | NOT PROVEN -> NOT PROVEN |
| FOREX | 8 | 199 | 30.7% | 24.7% | 46.2% | 0.658 | 0.515 | -0.1273 | -0.2073 | -12.7 | NOT PROVEN -> NOT PROVEN |
| BOND | 10 | 28 | 35.7% | 20.7% | 55.7% | 0.563 | 0.442 | -0.2309 | -0.3309 | -23.1 | NOT PROVEN -> NOT PROVEN |
| COMMODITY | 12 | 9 | 44.4% | 18.9% | 46.5% | 1.032 | 0.919 | +0.0324 | -0.0876 | +3.2 | NOT PROVEN -> NOT PROVEN |
| FUTURES | 12 | 1 | 0.0% | 0.0% | 100.0% | 0.000 | 0.000 | -0.4746 | -0.5946 | -47.5 | NOT PROVEN -> NOT PROVEN |

## Strategy out-of-sample split

A chronological split of **realised picks**, not a re-backtest: the same signals are re-scored on later exits. It answers 'did the edge decay', not 'would a fresh run reproduce it'.

### MomentumEMA

n=73 · round-trip cost 20 bps · breakeven cost **84.2 bps**

| segment | n | WR | PF | expectancy % |
|---|---|---|---|---|
| IS_first60 | 43 | 48.8% | 1.427 | +0.4344 |
| OOS_last40 | 30 | 70.0% | 3.376 | +1.4253 |
| third1 | 24 | 37.5% | 0.907 | -0.1154 |
| third2 | 24 | 70.8% | 3.604 | +1.5188 |
| third3 | 25 | 64.0% | 2.542 | +1.1104 |

| cost bps | expectancy % | PF | WR |
|---|---|---|---|
| 0bps | +0.8416 | 1.995 | 57.5% |
| 5bps | +0.7916 | 1.913 | 57.5% |
| 10bps | +0.7416 | 1.835 | 57.5% |
| 15bps | +0.6916 | 1.760 | 57.5% |
| 20bps | +0.6416 | 1.689 | 57.5% |
| 30bps | +0.5416 | 1.556 | 57.5% |

OOS half, net at model cost: expectancy **+1.2253%/trade**, PF **2.857**.

### mega_mutation_macd_rsi_m048

n=57 · round-trip cost 20 bps · breakeven cost **593.4 bps**

| segment | n | WR | PF | expectancy % |
|---|---|---|---|---|
| IS_first60 | 34 | 67.6% | 5.204 | +6.0525 |
| OOS_last40 | 23 | 69.6% | 4.968 | +5.7578 |
| third1 | 19 | 73.7% | 7.006 | +8.0393 |
| third2 | 19 | 68.4% | 5.284 | +5.3020 |
| third3 | 19 | 63.2% | 3.539 | +4.4595 |

| cost bps | expectancy % | PF | WR |
|---|---|---|---|
| 0bps | +5.9336 | 5.108 | 68.4% |
| 5bps | +5.8836 | 5.030 | 68.4% |
| 10bps | +5.8336 | 4.953 | 68.4% |
| 15bps | +5.7836 | 4.877 | 68.4% |
| 20bps | +5.7336 | 4.804 | 68.4% |
| 30bps | +5.6336 | 4.661 | 68.4% |

OOS half, net at model cost: expectancy **+5.5578%/trade**, PF **4.676**.

## First-touch resolution

- 15 records have an exit reason that contradicts the sign of their own pnl (SL_HIT with pnl>0, or TP_HIT with pnl<0).
- BLOCKED: needs OHLC bars between entry_time and exit_time; the ledger stores only entry_price/exit_price and entry_time on 1909/3500 records.
- No OHLC is derivable from entry_price/exit_price alone, so the H-120 honest re-resolution cannot be applied to the rest of this ledger without a bar source.


## Distribution check on the two "surviving" strategies

The out-of-sample split above looks favourable. It is not a return distribution —
both strategies fill as a fixed take-profit / stop-loss grid, and once you look at
the spread of outcomes the "edge" is the grid ratio, not a forecast.

| strategy | n | min | p10 | median | p90 | max | symbols | top-3 pick share of gross |
|---|---|---|---|---|---|---|---|---|
| MomentumEMA | 73 | −2.00 | −2.00 | +3.00 | +3.00 | +3.00 | 9 | 15% |
| mega_mutation_macd_rsi_m048 | 57 | −6.89 | −4.75 | +9.10 | +12.82 | +20.32 | **3** | 18% |

* **MomentumEMA** has *two possible outcomes*: −2.00% (SL) or +3.00% (TP), 30 vs 38
  with 5 time exits. PF 1.99 is arithmetic on the 3:2 payoff, not skill. Any error in
  which of SL/TP is deemed "first touched" moves the result directly — exactly the
  defect class H-120 measured at 2.09x PF inflation on daily resolution. A 3:2
  grid needs a 40% hit rate; it recorded 52%, and that hit rate is the one number
  the ledger cannot verify without bars.
* **mega_mutation_macd_rsi_m048** is 57 trades on **three symbols** (STXUSDT 22,
  JUPUSDT 20, WIFUSDT 15) with a ~1.4:1 payoff and a 9.1% median win. That is one
  altcoin regime with three tickers, not a cross-sectional edge. Its 594 bp
  breakeven cost is not robustness — it is a symptom of very wide targets on
  volatile alts.

Consequence: the OOS split says "these did not decay in this window", not "these
would reproduce". Promotion still requires a bar-level re-resolution (see
First-touch section) and more symbols than three.
