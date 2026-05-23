# B1 Altcoin Basis Arbitrage -- S1 Result: FAIL

Generated: 2026-04-19T05:48:09.096409+00:00

## Headline
- n trades: **101531**
- Sharpe (ann, post-cost): **-87.525**
- Win rate: **0.000**
- W/L magnitude ratio: **2.272**
- Sum bps: -1999997.6   Max DD bps: -1999995.2
- Avg hold (h): 3.69

## Year-by-year
- 2023: n=31990  Sharpe=-97.52  WR=0.00
- 2024: n=31464  Sharpe=-68.67  WR=0.00
- 2025: n=29265  Sharpe=-124.70  WR=0.00
- 2026: n=8812  Sharpe=-83.48  WR=0.00

## Splits (time-ordered 70/15/15)
- IS: n=71071  Sharpe=-82.46  WR=0.00
- OOS1: n=15230  Sharpe=-137.34  WR=0.00
- OOS2: n=15230  Sharpe=-87.84  WR=0.00

## Universe
Loaded: ADAUSDT, DOTUSDT, AVAXUSDT, LINKUSDT, NEARUSDT, ATOMUSDT, SOLUSDT, XRPUSDT, BNBUSDT, MATICUSDT, APTUSDT, ARBUSDT, OPUSDT, SUIUSDT, DOGEUSDT, ALGOUSDT, FILUSDT, RNDRUSDT
Skipped: PEPEUSDT(insufficient), SHIBUSDT(insufficient)

## Failed criteria
- Sharpe -87.53 <= 1.0
- WR 0.000 <= 0.55
- Only 0/3 yearly sub-windows (2023/2024/2025) Sharpe>0.5

## Data caveat
Index leg uses Binance markPriceKlines (mark price), which already incorporates spot index + funding. True perp-vs-spot basis is thus understated vs a raw spot midpoint. Direction of bias: against the strategy (fewer extreme basis readings).