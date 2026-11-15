# Algorithm spec — one rule per asset class

Hold window is the resolver window, not a portfolio horizon: ETF/EQUITY 96h, BOND 120h, CRYPTO 48h. Stops are ATR so a 4-day card can actually hit TP or SL. Entry is the last equity daily close (2026-11-13). No `current_price` field — the resolver treats that as an already-closed row.

## ETF and EQUITY — `wired_in_trend_momo_4d`

Universe (liquid names already in `alpha_engine/asset_class.py` plus the sector set used by the ETF emitter):

- ETF: SPY, QQQ, IWM, EFA, EEM, VNQ, SOXX, XLV, XLF, XLE, XLU
- EQUITY: AAPL, MSFT, NVDA, AMZN, GOOGL, META, JPM, LLY, AVGO, COST, UNH, XOM

Eligible only if all three are true on the last daily close:

1. close > SMA200
2. 21-day return > 0
3. 63-day return > 0

Emit the single eligible name with the highest 63-day return. One card per class. No shorts.

Stops, from that same close:

- stop = entry − 1.0 × ATR(14)
- target = entry + 1.67 × ATR(14)

21-day filter exists because the monitor dies at 96h. A 12-month winner that is falling this month is the wrong card for that window.

## BOND — `wired_in_short_duration_ballast`

Not an alpha rule. If TLT close < SMA200, long SHY (1-3y Treasury) with the same ATR stops. If TLT were above SMA200, the card would be IEF. It is not. Long-duration (TLT, LQD) is ineligible in this regime.

## CRYPTO

Would have been: BTC-USD long only if close > SMA200 and 21-day return > 0. Both failed (close below SMA200, 21-day about −23%, RSI about 21). No short. No fallback altcoin.

## FOREX, COMMODITY, FUTURES, mutual funds, prediction markets

No emission rule. See ELIMINATION.md. A class with no eligible name produces no row. Empty is the output, not a missing file.
