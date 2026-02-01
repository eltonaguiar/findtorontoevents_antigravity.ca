# STOCKSUNIFY2 - Scientific Stock Analysis Engine

[![Daily Audit](https://img.shields.io/badge/Audit-Daily%2021%3A00%20UTC-blue)](https://github.com/eltonaguiar/stocksunify2/actions)
[![Regime](https://img.shields.io/badge/Market%20Regime-BULLISH-green)](./data/v2/current.json)
[![Picks](https://img.shields.io/badge/Active%20Picks-20-purple)](./data/v2/current.json)

## Overview

STOCKSUNIFY2 is the **Scientific Validation Engine** for algorithmic stock analysis. Unlike traditional backtesting approaches, V2 enforces:

1. **Temporal Isolation** - Picks are timestamped and archived before market opens
2. **Regime Awareness** - Engine shuts down in bearish regimes (SPY < 200 SMA)
3. **Slippage Torture** - Returns are penalized 3-5x standard spread to find "bulletproof" liquidity
4. **Immutable Ledger** - Every pick is hashed and committed to Git history

## Live Data

| Resource | Link |
|----------|------|
| Current Picks | [data/v2/current.json](./data/v2/current.json) |
| Historical Ledgers | [data/v2/history/](./data/v2/history/) |
| Research Paper | [STOCK_RESEARCH_ANALYSIS.md](./STOCK_RESEARCH_ANALYSIS.md) |

## V2 Scientific Strategies

### 1. Regime-Aware Reversion (RAR)
Buy high-quality stocks in an uptrend that have a short-term RSI dip. Only active in bullish regimes.

### 2. Volatility-Adjusted Momentum (VAM)
Ranks stocks by Return / Ulcer Index (Martin Ratio). Prioritizes smooth uptrends over volatile gains.

### 3. Liquidity-Shielded Penny (LSP)
Penny stocks ($0.10-$5) that pass the "Slippage Torture Test" - returns must survive 3% slippage penalty.

### 4. Scientific CAN SLIM (SCS)
Traditional O'Neil methodology with Regime Guard and Slippage Penalty adjustments.

### 5. Adversarial Trend (AT)
Volatility-normalized trend following. Requires golden cross alignment and stable ATR.

## Architecture

```
STOCKSUNIFY2/
├── data/
│   └── v2/
│       ├── current.json          # Live picks (updated daily)
│       ├── ledger-index.json     # 30-day index
│       └── history/              # Immutable archive
│           └── YYYY/MM/DD.json
├── scripts/
│   └── v2/
│       ├── generate-ledger.ts    # Daily audit generator
│       ├── verify-performance.ts # Weekly truth engine
│       └── lib/
│           ├── v2-engine.ts      # Core orchestration
│           └── strategies.ts     # 5 scientific strategies
└── README.md
```

## Usage

### Generate Daily Ledger

```bash
npx tsx scripts/v2/generate-ledger.ts
```

### Verify Performance (Weekly)

```bash
npx tsx scripts/v2/verify-performance.ts
```

## Comparison: V1 vs V2

| Feature | STOCKSUNIFY (V1) | STOCKSUNIFY2 (V2) |
|---------|------------------|-------------------|
| Algorithms | CAN SLIM, Technical Momentum, Composite | RAR, VAM, LSP, SCS, AT |
| Regime Filter | None | SPY > 200 SMA required |
| Slippage Model | None | 3-5x standard spread penalty |
| Audit Trail | Basic timestamps | Immutable Git ledger |
| Bias Prevention | Manual | Temporal isolation enforced |

## Disclaimer

This is experimental financial research software. All picks are for educational purposes only. Past performance does not guarantee future results. Always consult a licensed financial advisor.

## Links

- **Live Site**: [findtorontoevents.ca/findstocks2](https://findtorontoevents.ca/findstocks2)
- **V1 Classic**: [github.com/eltonaguiar/stocksunify](https://github.com/eltonaguiar/stocksunify)
- **Source Repo**: [github.com/eltonaguiar/TORONTOEVENTS_ANTIGRAVITY](https://github.com/eltonaguiar/TORONTOEVENTS_ANTIGRAVITY)

---

*Last Updated: 2026-01-28T03:04:13.174Z*
