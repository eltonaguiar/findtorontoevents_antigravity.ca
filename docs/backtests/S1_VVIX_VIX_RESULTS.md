# C3 VVIX/VIX Mean Reversion -- S1 Result: FAIL

Generated: 2026-04-19T05:25:11.554139+00:00

## Headline
- n trades: **34**
- Sharpe (ann, post-cost): **4.059**
- Win rate: **0.735**
- W/L magnitude ratio: **0.716**
- Sum bps: 5947.2   Max DD bps: -1978.9
- Avg hold (d): 22.56

## Year-by-year
- 2020: n=4  Sharpe=0.55  WR=0.75
- 2021: n=8  Sharpe=1.89  WR=0.62
- 2022: n=1  Sharpe=0.00  WR=1.00
- 2023: n=9  Sharpe=15.88  WR=1.00
- 2024: n=5  Sharpe=-3.36  WR=0.60
- 2025: n=5  Sharpe=9.53  WR=0.80
- 2026: n=2  Sharpe=-20.62  WR=0.00

## Splits (time-ordered 70/15/15)
- IS: n=23  Sharpe=5.30  WR=0.78
- OOS1: n=5  Sharpe=-4.08  WR=0.60
- OOS2: n=6  Sharpe=4.88  WR=0.67

## Failed criteria
- n=34 < 200
- W/L 0.72 <= 1.0
- OOS1 Sharpe -4.08 < 0.7 x IS 5.30

## Data caveat
yfinance ^VVIX series has occasional stale/NA days (esp. holidays) which we drop with .dropna(). SVXY had a 0.5x leverage re-scale on 2018-02-27, pre-window. No further data breaks identified.