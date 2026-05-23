# Prop-firm style challenge picks (April 2026) — research synthesis

**Purpose:** Support a **HyroTrader**-style evaluation (e.g. free trial: **10k USDT**, **5%** profit target, **5%** daily drawdown, **10%** max loss, **≥5** trading days, **stop loss mandatory**).

**Live tracker:** [https://findtorontoevents.ca/audit/hyrotrader/](https://findtorontoevents.ca/audit/hyrotrader/)  
**Machine-readable picks:** `audit_dashboard/data/hyrotrader_picks.json` (update `entry_price` / `stop_loss` / `take_profit` / `status` when you execute — do not invent prices in the doc).

**Crypto-only execution playbook** (Bollinger/RSI/funding setups, survival math): [`HYROTRADER_CHALLENGE_STRATEGY.md`](./HYROTRADER_CHALLENGE_STRATEGY.md) — use for **BTC/ETH/SOL** execution; **sizes:** [`HYROTRADER_POSITION_SIZES.md`](./HYROTRADER_POSITION_SIZES.md). **Locked profile:** **Hyro FREE TRIAL · 5K futures · trailing** — profit **+250 USDT**, DD **−250 USDT**, max loss **−500 USDT**, **5** T-days (see JSON + strategy doc). This file remains the **cross-asset** idea list only.

---

## Ten ideas across five asset classes

| # | Asset | Direction | Confidence | Key edge (hypothesis) |
|---|--------|-----------|------------|------------------------|
| 1 | Gold | LONG | 90% | Strength + geopolitical bid; monitor real yields |
| 2 | Crude (WTI) | LONG | 88% | Supply / shipping risk premium |
| 3 | Bitcoin | LONG | 82% | Spot structure; funding / liquidation contrarian cues |
| 4 | S&P 500 | SHORT | 78% | Macro stress vs equities; confirm with breadth |
| 5 | EUR/USD | SHORT | 75% | USD vs ECB/Fed path; event risk |
| 6 | XRP | LONG | 72% | Flow / ETP narrative; high beta |
| 7 | Silver | LONG | 70% | Ratio mean-reversion vs gold; higher vol |
| 8 | Ethereum | LONG | 68% | ETH/BTC; beta to BTC |
| 9 | USD/JPY | LONG | 65% | Carry / policy divergence; intervention risk |
| 10 | Natural gas | LONG | 60% | Convex geopolitical / weather; smallest size |

**Dominant theme (hypothesis):** Shock channel → long hard assets / energy, cautious on risk paper and EUR until confirmed by your own risk limits.

---

## Hyro-aligned risk management

1. **Stop loss obligation** — No entry without a hard SL on the platform (Hyro rule).
2. **Daily circuit breaker** — If intraday loss approaches **5%** of day-start equity, stop new trades and flatten per your plan.
3. **Max loss** — **10%** from baseline account equity: halt challenge attempt; review process.
4. **Profit target** — **+5%** on nominal account = success criterion for the trial framing.
5. **Trading days** — Log at least **5** distinct days with risk-taking (not necessarily 5 wins).
6. **Sizing** — Use small fractional risk per trade so a string of stops cannot breach **10%** total.

---

## Repo touchpoints (for deeper research)

- Funding / contrarian context: `alpha_engine` scanners, `docs/HEDGE_FUND_QUALITY_PLAN.md`, audit quality gates.
- Execution tracking: update **`hyrotrader_picks.json`** and optionally mirror closed trades into your existing audit / paper pipelines.

---

## Disclaimer

Not financial advice. Prop-firm rules change; confirm all parameters on **HyroTrader** before trading. This document is a **research and tracking** aid for your own execution discipline.
