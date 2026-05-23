# quan_engine_scalp CRYPTO Permanent Block — Multi-Round Swarm Decision

**Date:** 2026-05-18
**Decision:** PERMANENT BLOCK CONFIRMED (Option B)
**Status:** Already implemented — `("CRYPTO", "quan_engine_scalp")` at `audit_trail/quality_gates.py:2396`

## Evidence

| Metric | Value |
|--------|-------|
| Closed picks (n) | 5,293 |
| Win rate | 29.9% |
| Profit factor | 0.379 |
| Cumulative PnL | -960% |
| Avg win | +0.370% |
| Avg loss | -0.417% |

**Walk-forward (5 folds):** 20.4%, 25.5%, 27.9%, 19.0%, 23.9% — ALL below 50%. Mean=23.3%.

**Root causes:**
1. ONDOUSDT 60% concentration at peak
2. Signal spam ~100/day from correlated EMA sub-signals
3. Avg win/loss ratio below 1.0
4. Parent source `quan_engine` already in `BLOCKED_SOURCE_SYSTEMS` since 2026-05-06
5. 240-cell autopsy (symbol × direction × timeframe) found zero profitable sub-segment

## Swarm Verdict (4 Rounds, 7 Agents)

| Round | Engine | Verdict | Option |
|-------|--------|---------|--------|
| 1 | Risk Committee | BLOCK — structural failure, no rescue path | B |
| 1 | Contrarian Adversarial | BLOCK — 5 rescue arguments all debunked | B |
| 2 | deepseek | BLOCK — no rescue without architectural redesign | B |
| 2 | kilo | BLOCK — explicit block prevents config-drift reactivation | B |
| 3 | gemini | PERMANENT BLOCK CONFIRMED — noise generator | B |
| 4 | openrouter (gpt-4o-mini) | BLOCK — no valid statistical argument against B | B |

**Result: 7/7 unanimous (0 dissent)**

## Decision

No reversal warranted. The block already in place at `quality_gates.py:2396` is correct.
No mutation rescue attempt justified (C). No unblock gate (D).

The strategy is structurally broken: negative expectancy, no temporal robustness (0/5 walk-forward folds above 50% WR), and no salvageable sub-segment across a 240-cell autopsy with n=5,293.

Additional evidence that could change this verdict: a walk-forward fold showing WR>40% with PF>1.0, OR a clearly defined non-correlated sub-segment backtesting positive expectancy on out-of-sample 2026 data. Neither exists. Block stands.
