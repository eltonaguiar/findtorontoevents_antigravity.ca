# Strategy: crypto_r1 (volume surge + up close, 5-day hold)

Status: CANDIDATE — forward paper only. NOT MONEY-READY (fails MDD gate).

## Frozen rules (do not tune after seeing OOS)
- Universe: BTC, ETH, SOL, BNB, XRP, ADA, AVAX, LINK, DOGE, DOT (daily bars).
- Entry: when daily volume > 2x 20-day average volume AND close > open (up close). Enter at close.
- Exit: close position after 5 trading days (at close). No stop loss in v1 (see MDD caveat).
- Costs: 30bp round trip.
- In-sample: data <= 2019-12-31. OOS: 2020-01-01 onward. Parameters frozen (no tuning on OOS).

## Backtest (OOS 2020-2026)
- n=689, WR 55.73%, PF 2.449, PF 95% CI [1.857, 3.206], MDD -89.85%, MC percentile 100, PF@2x 2.332, top symbol share 0.18, PF ex-top 2.409.
- Gate failures: MDD (-89.85% vs <=20%), DSR (0.00 vs >0.95).
- Yearly PF: 2020 1.434, 2021 2.221, 2022 1.259, 2023 1.372, 2024 2.126, 2025 2.124, 2026 0.589 (loss year).

## Kill criteria (forward paper)
- Rolling 50-trade PF < 1.0
- Drawdown > 12% (paper) / 20% (live gate)
- Realized cost > 1.5x assumed (45bp)

## What would change the verdict
- Add a volatility-scaled stop loss (2x ATR) and re-test MDD on OOS; if MDD <=20% and DSR>0.95 with n>=100, reclassify MONEY-READY.
- Do not loosen gates.
