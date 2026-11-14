# Risk Management — final_v2

**Date:** 2026-11-14 | **Worktree:** flaxen-hair

## Risk Management Framework

All profitability strategies must adhere to the following risk rules, derived from TradingView contest winner research and the finpredict-v4 scoring framework.

---

## Position Sizing Rules

| Rule | Specification | Rationale |
|------|---------------|-----------|
| Max risk per trade | 2% of equity | Retail-viable threshold from TradingView contest research |
| Kelly Criterion | 0.25×–0.5× full Kelly for proven edges | Prevents over-betting on unproven edges |
| Max concurrent positions | 2 | Limits concentration risk |
| Correlation limit | Max 1 position per correlated group | Prevents bloc risk (e.g., JUP/ENA/ADA/WIF move together) |

**Correlated groups for crypto:**
- Group 1: JUPUSDT, ENAUSDT, ADAUSDT, WIFUSDT (high-beta altcoins)
- Group 2: AVAXUSDT, DOTUSDT, STXUSDT, RENDERUSDT (mid-cap alts)

---

## Drawdown Controls

| Control | Specification |
|---------|---------------|
| Daily loss cap | -5% of equity |
| Monthly loss cap | -20% of equity |
| Max drawdown | Pre-registered envelope (strategy-specific) |
| Losing streak | 3 consecutive losses → stop trading for session (high-WR grinders) |
| No martingale | Fixed risk per trade, no scaling up after losses |

---

## Regime Filters

| Asset Class | Regime Filter | Specification |
|-------------|---------------|---------------|
| Crypto | BTC bull regime | BTC price > 200-EMA on 1h chart |
| Equity | SPY trend filter | SPY price > 200-SMA on daily chart |
| All | Staleness check | Data older than T-1 day → no new picks |

---

## Statistical Gates (finpredict-v4 6-Gate Pipeline)

| Gate | Requirement | Fail Action |
|------|-------------|-------------|
| Gate 0: Data Quality | n≥30, complete trade log, no missing prices | Halt — do not trade |
| Gate 1: Statistical Significance | Bootstrap 95% CI: PF_lower > 1.0, Sharpe_lower > 0 | Halt — do not trade |
| Gate 2: Walk-Forward | ≥60% profitable folds, mean OOS PF > 1.2 | Halt — do not trade |
| Gate 3: Gross Profitability | PF > 1.5, Sharpe > 1.0, WR > 50%, Sortino > 1.5 | Halt — do not trade |
| Gate 4: Money-Ready (Net) | Net PF > 1.2, Net Sharpe > 0.5, Net WR > 45%, DSR > 0.95 | Paper trade only |
| Gate 5: Direction Validation | If directional, both sides pass Gate 4 | Direction-specific sizing |

---

## Cost Model (for net profitability)

| Cost Component | Rate | Notes |
|----------------|------|-------|
| Commission | 10 bps per trade | Per side |
| Spread | 5 bps | Round trip |
| Base slippage | 5 bps | Volatility-adjusted |
| Intrabar penalty | 10 bps | For winners (23-24% win-to-SL flip) |
| Volatility penalty | 0.1 × realized vol | Scales with 20-day std dev |

**Net return formula:**
```
net_trade_return = gross_trade_return - commission - spread - slippage - intrabar_penalty
```

**Slippage model:**
```
slippage = 0.0005 + (0.1 * realized_vol_20d)
```

---

## Execution Risk Controls

| Risk | Mitigation |
|------|------------|
| Exchange counterparty | Diversify across venues; monitor Binance regulatory risk |
| Margin calls | Maintain excess collateral; monitor margin levels |
| Withdrawal limits | Keep emergency cash outside exchange |
| Funding-sign reversals | Monitor funding rates daily; exit if sign flips |
| Spot/perp basis | Monitor basis; exit if basis widens unexpectedly |
| Data staleness | Reject picks with data older than T-1 day |
| Price freezing | Cross-validate prices across Binance + Yahoo Finance + er-api |

---

## Mega_Mutation Specific Risk Controls

| Control | Specification |
|---------|---------------|
| Regime filter | BTC > 200-EMA (no trades in bear regime) |
| Correlation groups | Max 1 position per group (JUP/ENA/ADA/WIF | AVAX/DOT/STX/RENDER) |
| Max concurrent | 2 positions |
| Position size | 2% risk per trade on $10k equity |
| TP/SL | ATR multiples from tournament genes |
| Entry conditions | MACD/RSI or EMA cross exact tournament genes |
| Forward sample target | n=100 before live capital (currently n=50) |

---

## What to Do When Risk Limits Are Breached

| Breach | Action |
|--------|--------|
| Daily loss cap (-5%) | Stop trading for the day |
| Monthly loss cap (-20%) | Stop trading for the month; review strategy |
| 3 consecutive losses | Stop trading for session; check regime |
| DSR < 0.95 | Remove from live trading; return to paper |
| Bootstrap CI includes 1.0 | Remove from live trading |
| Data staleness > T-1 day | No new picks until data refreshed |
| Regime filter fails | Stay in cash; no new entries |

---

## Escalation Path

1. **Paper trading** — Validate strategy on gated scanner (0 capital at risk)
2. **Small live** — Allocate minimal capital after n=100 forward picks with WR≥55%, PF≥1.5
3. **Full live** — Scale up after 3+ months of clean forward performance with all 6 gates passing
4. **Halt** — Any gate failure triggers immediate halt and review
