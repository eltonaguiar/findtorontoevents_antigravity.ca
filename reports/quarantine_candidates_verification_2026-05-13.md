# Quarantine Candidates — Verification 2026-05-13

**Trigger:** Cross-AI audit (Mimo data-backed, 2026-05-12 05:45Z, referenced in `/updates/index.html`) named 5 strategies as "0% WR with n ≥ 4 — hard-quarantine candidates." Per CLAUDE.md "NEVER auto-add to BLOCKED_ASSET_STRATEGY_PAIRS without explicit user approval," verifying each before any blocklist edit.

## Reproducible query

```python
import json
from collections import defaultdict
d = json.load(open('audit_dashboard/data/dashboard_data.json', encoding='utf-8'))
rc = d.get('picks', {}).get('recent_closed', [])
targets = ['drawdown_recovery_rsi_sol','drawdown_recovery_rsi_eth',
           'b_flip_pricerocmeanreversion','crypto_vwap_volprofile_reversion_v1',
           'macd_divergence']
# Substring match on `strategy`, accumulate n / wins / losses / flat / pnl_sum
```

## Verified results (2026-05-13T02:43Z, dashboard_data.json fresh)

| Strategy | n | WIN | LOSS | FLAT | unresolved | WR | total pnl% |
|---|---|---|---|---|---|---|---|
| drawdown_recovery_rsi_sol | 6 | 0 | 0 | 0 | 6 | — | −6.00 |
| drawdown_recovery_rsi_eth | 7 | 0 | 0 | 0 | 7 | — | −7.00 |
| b_flip_pricerocmeanreversion | 5 | 0 | 0 | 0 | 5 | — | −7.44 |
| crypto_vwap_volprofile_reversion_v1 | 12 | 0 | 0 | 0 | 12 | — | −4.54 |
| macd_divergence | 3 | 0 | 0 | 0 | 3 | — | 0.00 |

## What this means

1. **All 5 strategies have 0 resolved outcomes** in `recent_closed`. The audit's "0% WR" framing is technically vacuous — WR can't be computed when no rows have WIN/LOSS/FLAT.
2. **4 of 5 have measurable negative pnl sums** (−4.54 to −7.44%). So they ARE losing money in aggregate, just without formal outcome tagging.
3. **`macd_divergence` n=3 is below the n≥4 threshold the audit claimed**. Either the audit used a different snapshot or it counted across a broader window.

## Procedural finding (more important than the strategies themselves)

The cross-AI audit's "0% WR n ≥ 4" methodology was **subtly broken**: it counted `recent_closed` rows but apparently didn't require an `_outcome` value. Result: 4 of 5 named strategies are *cosmetically* "0% WR" because they're 100% unresolved. This is the same failure mode (claim without reproducible query) flagged in the session-handoff §4 list.

## Recommended actions

| Strategy | Recommendation | Reason |
|---|---|---|
| drawdown_recovery_rsi_sol | AVOID list per [docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md](docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md) | n=6 with −6% cumulative pnl is below random; worth investigation but not yet block-eligible (pnl gate, not WR gate) |
| drawdown_recovery_rsi_eth | AVOID list | n=7 with −7% pnl |
| b_flip_pricerocmeanreversion | AVOID list | n=5 with −7.44% pnl |
| crypto_vwap_volprofile_reversion_v1 | AVOID list | n=12 with −4.54% pnl |
| macd_divergence | NO ACTION | n=3 below stat-sig threshold; 0 pnl is neutral, not losing |

**Net-new TODO:** investigate why these 5 strategies have 0 resolved outcomes. This likely points to a broader resolver gap — every other class is resolving picks normally per [reports/commodity_bond_forensic_2026-05-13.md](reports/commodity_bond_forensic_2026-05-13.md). Candidate causes:
- Strategy emits with no TP/SL set (resolver can't evaluate)
- Strategy emits with `max_hold_days` too far in the future
- Strategy emits without `entry_price` (resolver can't compute pnl)

## Pattern: this is now the 5th confidently-wrong claim caught this session

The session-handoff §4 listed 4 confidently-wrong claims. This is the 5th. The procedural rule from §4 holds: **every "X is broken" / "Y is high-WR" claim must ship with a one-liner grep / SQL command anyone can re-run.** The audit's claim shipped without that one-liner; verification revealed the framing issue in under 60 seconds.

Approval gate: per CLAUDE.md, BLOCKED_ASSET_STRATEGY_PAIRS edits need explicit user approval. Flagging here for decision rather than auto-blocking.
