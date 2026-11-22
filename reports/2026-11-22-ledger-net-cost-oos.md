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
| CRYPTO | 20 | 1835 | 35.9% | 33.7% | 50.3% | 0.624 | 0.553 | -0.7589 | -0.9589 | -75.9 | NOT PROVEN -> NOT PROVEN |
| EQUITY | 10 | 782 | 45.1% | 41.7% | 45.4% | 1.034 | 0.990 | +0.0768 | -0.0232 | +7.7 | NOT PROVEN -> NOT PROVEN |
| ETF | 10 | 588 | 42.7% | 38.7% | 43.9% | 1.038 | 0.954 | +0.0438 | -0.0562 | +4.4 | NOT PROVEN -> NOT PROVEN |
| FOREX | 8 | 204 | 32.4% | 26.3% | 35.8% | 1.203 | 0.857 | +0.0424 | -0.0376 | +4.2 | NOT PROVEN -> NOT PROVEN |
| COMMODITY | 12 | 50 | 20.0% | 11.2% | 62.0% | 0.165 | 0.153 | -2.8119 | -2.9319 | -281.2 | NOT PROVEN -> NOT PROVEN |
| BOND | 10 | 37 | 43.2% | 28.7% | 51.2% | 0.904 | 0.726 | -0.0456 | -0.1456 | -4.6 | NOT PROVEN -> NOT PROVEN |
| FUTURES | 12 | 4 | 50.0% | 15.0% | 34.5% | 2.026 | 1.901 | +1.4353 | +1.3153 | +143.5 | NOT PROVEN -> NOT PROVEN |

## Strategy out-of-sample split

A chronological split of **realised picks**, not a re-backtest: the same signals are re-scored on later exits. It answers 'did the edge decay', not 'would a fresh run reproduce it'.

### MomentumEMA

n=0 · round-trip cost 15 bps · breakeven cost **None bps**

n<10: no split attempted

### mega_mutation_macd_rsi_m048

n=0 · round-trip cost 15 bps · breakeven cost **None bps**

n<10: no split attempted

## First-touch resolution

- 22 records have an exit reason that contradicts the sign of their own pnl (SL_HIT with pnl>0, or TP_HIT with pnl<0).
- BLOCKED: needs OHLC bars between entry_time and exit_time; the ledger stores only entry_price/exit_price and entry_time on 3500/3500 records.
- No OHLC is derivable from entry_price/exit_price alone, so the H-120 honest re-resolution cannot be applied to the rest of this ledger without a bar source.

