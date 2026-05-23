# COMMODITY Audit Feedback - 2026-05-05T0121Z

Agent: GPT-5.5

## Verdict

COMMODITY has the best class-level PF but still misses the WR gate. Current payload: `n=816`, `WR=48.7%`, `PF=2.08`, `PnL=285.05%`, `status=stable`, `sizing_allowed=true`.

## Legit Fix Path

- Preserve the high-PF behavior while filtering low-quality entries that drag WR below 50%.
- Use `cta_cross_asset_tsmom` direction split as a mutation candidate: SHORT `66.2%` WR / `65` trades vs LONG `35.1%` / `57`.
- Add symbol-dependency reporting for commodity-linked systems, especially where top-symbol contribution flips class/system PnL.

## Do Not Do

Do not overfit PF upward by pruning losers without an out-of-sample or forward gate. The missing piece is WR reliability, not more retrospective cherry-picking.
