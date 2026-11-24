# 1000-cell census rollup

Total 1000. Categories: {'claimed': 3, 'measured_kill': 96, 'blocked': 861, 'insufficient': 40}

**Zero survivors.** Every cell with data to measure (96) is KILLED.

## Measured kills only exist for these symbols (5 crypto-daily): BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, DOGEUSDT

## By horizon
- 15m: {'claimed': 1, 'blocked': 199}
- 1h: {'claimed': 1, 'measured_kill': 8, 'blocked': 191}
- 4h: {'claimed': 1, 'measured_kill': 8, 'blocked': 191}
- 1d: {'measured_kill': 35, 'insufficient': 40, 'blocked': 125}
- 1w: {'measured_kill': 45, 'blocked': 155}

## What unlocks the 861 blocked cells
- Daily bars for SPY/QQQ/IWM/AAPL/MSFT/NVDA/JPM/XLE/GLD/TLT, EURUSD/USDJPY/GBPUSD, ADAUSDT/LINKUSDT -> opens all 1d/1w cells for 15 more symbols.
- 15m bars for any symbol -> opens the entire 15m row (200 cells).
- 1h/4h bars for non-BTC crypto -> opens 1h/4h for ETH/SOL/XRP/DOGE (+4 symbols x 2 horizons x 10 strategies).
- gap_fade needs an 'open' field (current sources are close-only) -> opens 100 gap_fade cells where bars exist.

*Paper only. Not investment advice.*
