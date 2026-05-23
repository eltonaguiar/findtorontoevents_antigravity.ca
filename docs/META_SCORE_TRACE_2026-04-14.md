# META / `multi_asset_copytrader` score trace (2026-04-14)

## Root cause (from live `dashboard_data.json` row)

`META` had **`confidence: 0.60`** and **`direction: LONG`**. In `audit_trail/quality_gates.py` → `_apply_score_penalties`:

1. **`conf_danger_zone(0.60): -10`** — bucket `0.60 <= conf < 0.65` (historical WR ~38% for that band).
2. **`long_deadzone_combo(0.60): -12`** — LONG + `0.60 <= conf < 0.70` (historical poor LONG performance in that band).

Those two stack to **-22** before other bonuses (`proven_source +5`, `trust_mid +7`, `trade_count_elite +10`, etc.). The row also carries **strong strategy forward stats** (`strat_fwd_trades=746`, `strat_fwd_wr=46.8%`, `forward_validated=true`) — i.e. the same evidence HC Gate 5 uses — but the confidence buckets were designed for crypto-heavy aggregates, not **EQUITY + large-n forward book**.

`multi_asset_copytrader` is **not** missing `_SOURCE_SYSTEM_SCORES` (it is **+5**). The drag is **confidence / LONG interaction**, not the stale `last_signal` penalty (META has fresh `timestamp`).

## What we shipped

**Helper:** `_equity_forward_proven_mitigates_conf_deadzone(pick)`  
**Rules:** EQUITY + `forward_validated` + `strat_fwd_trades >= 50` + `strat_fwd_wr >= 45%` (ratio scale via `_effective_forward_wr_ratio`).

**Behavior change:**

| Block | Before | After (when mitigation applies) |
|-------|--------|----------------------------------|
| `0.60 <= conf < 0.65` | `-10` (`conf_danger_zone`) | `-3` (`conf_below_avg_equity_forward_proven`) |
| LONG + `0.60 <= conf < 0.70` | `-12` (`long_deadzone_combo`) | **0** (`long_deadzone_exempt_equity_forward_proven`) |

**Net:** up to **+19** points vs the old stack for qualifying EQUITY rows (e.g. META-like). That is enough to move many META-like rows from the high-30s into **strict-edge EQUITY** territory (score ≥ 50) **after** the next dashboard regeneration that re-runs `passes_active_gate` / `_apply_score_penalties`.

## Tests

`tests/test_quality_gates.py`:

- `test_equity_forward_proven_skips_conf_danger_and_long_deadzone`
- `test_equity_forward_unproven_still_gets_conf_danger_and_long_deadzone`

## Follow-up (not done here)

- **COST** and other low-`n` / low-WR equity copy rows: unchanged — they do not meet the mitigation threshold.
- **A/B** on live dashboard: watch for unintended boosts on thin `strat_fwd_*` (mitigation requires `n>=50` and `wr>=45%`).
- **PM pipeline** remains a separate project (`closed_path: None`); see `docs/HC_FOLLOWUP_TODOS_2026-04-14.md`.
