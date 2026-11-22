# Closed ledger: net-of-cost verdicts, out-of-sample split, first-touch blocked — 2026-11-22

## What was broken

`audit_dashboard/data/dashboard_data.json` carries `after_cost_net_per_trade` on
**0 of 3,500** closed picks, so every verdict published from it is gross — including
the 2026-11-18 edge-by-asset-class audit that called CRYPTO and EQUITY "PROVEN".
A 0.53%/trade crypto edge and a 0.078%/trade ETF edge are not the same claim once
fees and slippage are subtracted, and the ledger could not tell you which survived.

## What changed

New `tools/ledger_net_and_oos.py` (self-check included):

* per-class round-trip cost model (CRYPTO 20bp, EQUITY/ETF 10bp, FOREX 8bp,
  COMMODITY/FUTURES 12bp, BOND 10bp, default 15bp) applied to every closed pick,
  then the win-rate-vs-own-breakeven test re-run on net returns;
* `breakeven_cost_bps` — the round-trip cost at which a class's expectancy hits zero;
* chronological 60/40 and thirds split plus a 0/5/10/15/20/30 bp cost grid for named
  strategies (explicitly an out-of-sample split of realised picks, **not** a re-backtest);
* geometry audit for exit reasons that contradict their own pnl sign.

## Result

| class | n | PF gross | PF net | exp gross % | exp net % | breakeven cost bps | verdict |
|---|---|---|---|---|---|---|---|
| CRYPTO | 2070 | 1.313 | **1.184** | +0.5355 | **+0.3355** | +53.5 | PROVEN → **NOT PROVEN** |
| EQUITY | 690 | 1.229 | **1.175** | +0.4609 | **+0.3609** | +46.1 | PROVEN → **NOT PROVEN** |
| ETF | 503 | 1.071 | **0.981** | +0.0776 | **−0.0224** | +7.8 | NOT PROVEN → NOT PROVEN |
| FOREX | 199 | 0.658 | 0.515 | −0.1273 | −0.2073 | −12.7 | NOT PROVEN |
| BOND | 28 | 0.563 | 0.442 | −0.2309 | −0.3309 | −23.1 | NOT PROVEN |
| COMMODITY | 9 | 1.032 | 0.919 | +0.0324 | −0.0876 | +3.2 | NOT PROVEN |

CRYPTO net: WR 44.9%, Wilson low 42.8% against its own net breakeven 40.8% — it
still clears the win-rate test, but net PF 1.184 misses the audit's PF>1.2 bar by
1.6 points, and 20bp erases 37% of the gross expectancy. EQUITY fails the same way.
ETF is the clean kill: its entire edge is 7.8bp wide, i.e. less than one spread.

## The two "survivors" are payoff grids, not strategies

* **MomentumEMA** — 73 fills, and the pnl takes exactly two values: −2.00% (30 SL)
  and +3.00% (38 TP), plus 5 time exits. PF 1.99 is the 3:2 payoff ratio. The only
  real number is a 52% hit rate, and hit rate is precisely what daily-resolution
  first-touch errors corrupt (H-120 measured 2.09× PF inflation from that alone).
* **mega_mutation_macd_rsi_m048** — 57 fills across **3 symbols** (STXUSDT, JUPUSDT,
  WIFUSDT), median win +9.1%, ~1.4:1 payoff. Its 594bp breakeven cost is wide
  targets on volatile alts, not robustness.

Both looked positive out of sample *within this window*; neither is promotable.

## First-touch resolution for the rest of the ledger — BLOCKED

The H-120 honest first-touch re-resolution cannot be applied here as asked:
the ledger stores only `entry_price` / `exit_price`, no OHLC bars between entry and
exit, and `entry_time` is populated on only 1,909/3,500 records. What *was*
checkable without bars: **15 records** have an exit reason contradicting the sign of
their own pnl (SL_HIT with pnl>0, or TP_HIT with pnl<0) — a floor on the
mis-resolution rate, not a measurement of it. Clearing this needs a bar source
(daily OHLC per symbol covering each hold window); the class-level effect is then
recomputable with this same tool.

## Repro

```
python3 tools/ledger_net_and_oos.py --self-check
python3 tools/ledger_net_and_oos.py --dashboard /home/eaguiar2015/findtorontoevents_antigravity.ca/audit_dashboard/data/dashboard_data.json
```

Outputs: `reports/2026-11-22-ledger-net-cost-oos.{json,md}`.
