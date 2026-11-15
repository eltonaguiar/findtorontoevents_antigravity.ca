# Pick justification — snapshot 2026-11-15T0150Z

Prices are yfinance daily closes, auto-adjusted, pulled that hour. Equity/ETF/bond/commodity last bar is 2026-11-13 (session closed). Crypto last bar is 2026-11-15 and was not used, because crypto was eliminated.

## XLV — ETF

Eligible ETF set that day: XLV, XLF. Everything else failed SMA200 or 63-day return or 21-day return.

| Symbol | close | >SMA200 | 21d | 63d | 12-1 | RSI14 |
|---|---:|---|---:|---:|---:|---:|
| XLV | 188.85 | yes | +6.6% | +13.5% | +26.6% | 70.4 |
| XLF | 58.68 | yes | +6.2% | +2.3% | +5.4% | 64.1 |

XLV wins on 63-day return. RSI 70 is extended. The rule does not override for RSI. XLF is the runner-up, not a second card.

Entry 188.85, ATR14 3.6957, SL 185.15, TP 195.03.

## LLY — EQUITY

Eligible names: LLY, AAPL, COST, AMZN, UNH. Ranked by 63-day return, LLY is first.

| Symbol | close | 21d | 63d | RSI14 | note |
|---|---:|---:|---:|---:|---|
| LLY | 1443.50 | +15.5% | +22.2% | 75.1 | selected |
| AAPL | 356.27 | +4.3% | +16.7% | 58.7 | cleaner tape, lower rank |
| COST | 1106.21 | +13.3% | +16.2% | 74.0 | third |

AAPL would be the discretion pick if the goal were "least extended." That would be a post-hoc override of the rule that was actually replayed. Not applied.

Entry 1443.50, ATR14 50.9722, SL 1392.53, TP 1528.62.

## SHY — BOND

TLT 79.38 is below SMA200, 12-1 return −7.9%, RSI 33.5. That is the existing duration-rotation regime (short duration when long bonds are weak). SHY 81.17 is above SMA200. SGOV was considered and rejected as a pick: it is cash, ATR is noise, and a TP will not print inside 120h. SHY can at least be resolved.

Entry 81.17, ATR14 0.1306, SL 81.04, TP 81.39. Expect TIME_EXIT more often than TP.

## What these are not

They are not a claim that the book is profitable. Repo verdicts still fail money-ready gates (EQUITY intrabar PF 0.94, CRYPTO PF 0.92, ETF sample too thin and previously misaligned). Confidence is 0.40–0.46 on purpose. `sizing_allowed` is false.
