# Asset-Class Notes (harvested)

Quick per-class summary of what has been tried, what died, and where the only remaining room is. Detail lives in `Plan/<class>/PLAN.md`.

## Equity (US)
- Tried: EMA momentum (F1), LGBM features (F2), VPIN ensemble (F3), VPIN reversion (F4/F27), vol-momentum (F5), quality-momentum (F6), dual momentum (F7), HMM (F16), random forest (F29), intrabar resolver (F25)
- Died at: significance vs SPY (F1, F6), shuffle/look-ahead (F2, F29), WFO drift (F4, F7, F27)
- Near-miss: F3 (N<60), F5 (cost margin), F25 (PF 0.80 vs 1.15 gate)
- Only room: cross-sectional (relative) construction, pre-registered — `Plan/equity/`
- Hard fact: **EQUITY was formally closed as a beta source** (NO_ALPHA_BETA, t=1.05 vs SPY). Reopening needs a new pre-registered trial ID, not a threshold change.

## Crypto
- Tried: breakout+funding carry (F9), token unlocks (F11), transformer (F30)
- Died at: shuffle control (F9 — look-ahead leak, a bug not a market fact), N too small (F11, F30)
- Near-miss: F11
- Only room: cross-sectional carry+trend on weekly cadence, *after* a leakage audit — `Plan/crypto/`

## Commodity / Futures
- Tried: COT + momentum (F12)
- Near-miss: F12 (OOS erodes after costs)
- Only room: pure TSMOM with explicit roll cost — `Plan/commodity/`
- Note: `tools/cot_contrarian_backtest.py` failed 4/4 pre-registered checks — an honest negative result worth keeping.

## ETF
- Tried: essentially nothing clean; SPY miscategorised as equity; zero live picks
- Only room: dual momentum tactical test — `Plan/etfs/`

## Bond
- Tried: sparse (n≈35). Below any significance floor.
- Only room: yield-curve steepener/flattener, monthly, ballast research — `Plan/bonds/`

## Forex
- Tried: carry+trend (F13)
- Died at: friction — 0.1% round-turn spread eats the entire edge; all MC paths negative
- Verdict: no edge at retail spread. Document and stop — `Plan/forex/`

## Mutual Funds / Low-cost ETFs
- Tried: nothing (infrastructure never built; `findmutualfunds2` empty of production path)
- This is **not alpha** — it's beta capture + cost discipline. Highest probability of positive real return.
- Only room: rules-based low-cost selection + allocation — `Plan/mf_etf/`, `Plan/multi_asset/`

## Prediction Markets (Kalshi / Polymarket)
- Tried: consensus copy-trading (F10)
- Died at: structural — zero-sum + adverse selection + maker/taker fees + latency + size mismatch
- Verdict: no retail copy-trading edge. Only a maker/liquidity-provision *business* is testable — `Plan/prediction_markets/`

## Multi-asset
- Tried: risk parity (F8), equal-risk-parity 5-signal combo (F28)
- Near-miss: F8 (PF≈1.00 at gate)
- Only room: core-satellite allocation with an explicit benchmark — `Plan/multi_asset/`

## Cross-cutting
- 9/9 classes have `sizing_allowed: false`.
- The binding constraints are the same everywhere: **look-ahead leaks, WFO drift, and friction**.
- Two repo gates (`MONEY_READY_FDR_GATE`, `MONEY_READY_SINGLE_SOURCE_GATE`) ship **off** — enable before any promotion.
