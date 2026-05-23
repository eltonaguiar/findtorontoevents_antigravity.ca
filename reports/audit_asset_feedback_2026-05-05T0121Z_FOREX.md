# FOREX Audit Feedback - 2026-05-05T0121Z

Agent: GPT-5.5

## Verdict

FOREX is the highest-priority rehab target. Current payload: `n=1249`, `WR=45.6%`, `PF=0.28`, `PnL=-986.16%`, `status=stressed`, `sizing_allowed=false`.

## Legit Fix Path

- Put `kimi_signal_tracking` into immediate rehab: `n=177`, `PF=0.26`, `PnL=-958.10%`, `MDD=994.95%`, top loss dependency `USDCHF=X`.
- Use mutation lanes before kill: SHORT-only tests for `ig_contrarian_sentiment`, `myfxbook_retail_contrarian`, `cta_cross_asset_tsmom`, and `quan_engine_swing`; pause or invert `forex_rsi2_mean_reversion` LONGs.
- Add per-pair symbol gates for toxic FX pairs only after the three-axis mutation report confirms the split is stable.

## Do Not Do

Do not hard-kill FOREX as an asset class. The protocol requires symbol, direction, and timeframe autopsy first.
