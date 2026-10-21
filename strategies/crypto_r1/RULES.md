# Strategy: crypto_r1_v2 (volume surge + up close + 50-day SMA uptrend, ATR TP 4x / SL 2x, 3-day hold)

Status: FAIL on MDD gate (MDD -21.29% vs <=20%) and DSR. Closest viable candidate. NOT MONEY-READY.

## Frozen rules (do not tune after seeing OOS)
- Universe: BTC, ETH, SOL, BNB, XRP, ADA, AVAX, LINK, DOGE, DOT (daily bars).
- Entry: daily volume > 2x 20-day avg AND close > open (up close) AND close > 50-day SMA. Enter at next bar's open.
- Exit: TP = entry + 4x ATR(14); SL = entry - 2x ATR(14); max 3-day hold. Exit intraday on TP/SL (high/low), else close at day 3.
- Costs: 30bp round trip (assumed, no external source).
- In-sample: data <= 2019-12-31. OOS: 2020-01-01 onward. Params frozen.

## Backtest (OOS 2020-2026, method-fixed)
- n=595, WR 50.59%, PF 1.572, 95% CI [1.236, 2.032], MDD -21.29%, MC 98.3, PF@2x 1.485, top symbol share 0.175, PF ex-top 1.712.
- Gate failures: MDD (-21.29 vs <=20), DSR (0.00 vs >0.95).
- Yearly PF: see results JSON.

## Kill criteria (forward paper)
- Rolling 50-trade PF < 1.0
- Drawdown > 12% (paper) / 20% (live gate)
- Realized cost > 1.5x assumed (45bp)

## What would change the verdict
- Reduce MDD below 20% (try trailing stop or vol-scaled sizing) without dropping PF below 1.5.
- Pre-register a single variant (not 24) to improve DSR.
- Do not loosen gates.
