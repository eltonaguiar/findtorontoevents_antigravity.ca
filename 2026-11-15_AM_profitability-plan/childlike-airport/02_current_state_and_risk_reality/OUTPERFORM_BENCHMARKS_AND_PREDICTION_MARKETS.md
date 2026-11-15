# 02b — Outperforming S&P 500 / Buy-and-Hold, and Why Prediction-Market Copy Trading Fails

## 1) “Profitable” vs “beats the benchmark” (critical distinction)
- **Absolute return > 0** is insufficient for an equity/ETF strategy if it underperforms a passive alternative on a **risk-adjusted, net-of-cost** basis.
- **Equity/ETF alpha bar:** outperform **SPY or total-market buy-and-hold (total return)** over comparable risk and multiple regimes, after all costs (fees, spread, slippage, taxes/turnover). Track alpha/beta, tracking error/information ratio, and drawdown.
- **Long-horizon reality:** a low-cost diversified index/MF allocation often wins for real investors because it reliably captures the **equity risk premium** with minimal frictions — the “edge” is **cost + diversification + discipline**, not prediction. This can be the right money outcome even when the prediction system has no alpha.
- **Crypto/other:** compare to the relevant passive hurdle (e.g. BTC/ETH buy-and-hold or risk-matched) and to cash/T-bills; many active crypto strategies fail once costs/funding and regime risk are included.
- **Mutual funds:** judge net-of-fee vs stated benchmark over meaningful horizons (SPIVA-like evidence: persistent net alpha is uncommon). Next-NAV mechanics mean they are not intraday trading vehicles.

## 2) Why Kalshi/Polymarket copy-trading attempts still don’t produce winners
Copying visible “top wallets” or contracts is structurally disadvantaged (verify each with timestamped, net data):

| Mechanism | Why it breaks copy-traders |
|---|---|
| **Zero-sum minus fees** | Aggregate profit is others’ loss less fees/spread — no shared growth premium like equities. |
| **Adverse selection & latency** | Informed/faster flow moves prices first; copiers arrive late at worse executable prices. |
| **Professional/bot dominance** | Sophisticated makers/arbs capture much of available edge; retail often provides liquidity. |
| **Costs & microstructure** | Maker/taker fees, spread, tick/contract rules, and position/withdrawal limits compress small edges. |
| **Size/capacity mismatch** | Whale sizing/limits don’t translate to small accounts; copying can move price or be unfillable. |
| **Survivorship/selection bias** | “Top wallets” are often lucky or short-track; losers disappear from view. |
| **Missing context** | A copied leg may be hedged elsewhere or express a portfolio view you don’t replicate. |
| **Resolution & model risk** | Payout depends on precise settlement rules and calibrated probabilities, not direction alone. |
| **Non-stationarity** | Event regimes and information structure change; past hit-rates decay. |
| **Copy/measurement fidelity** | Signal vs fill timestamps, partial fills, net accounting, and attribution errors can erase apparent edge. |

**What would be required to claim an edge:** timestamped signal-vs-executable records, full net PnL after fees/spread/limits, capacity-aware sizing, calibration (e.g. Brier) and baseline comparison, multiple-testing control, and forward/live proof. Absent that, treat prediction-market copy trading as **non-transferable** by default.

## 3) Implication for this system
- Default core: **low-cost diversified buy-and-hold/TAA allocation** measured against proper benchmarks.
- Active/prediction research: only promotable if it **beats the relevant buy-and-hold benchmark net, risk-adjusted, forward**.
- Prediction-market sources: hypothesis generators with per-source scorecards, not copy signals.
