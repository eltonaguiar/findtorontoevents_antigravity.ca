# WR Reconciliation: `performance.by_asset_class` vs `picks.recent_closed`

**Date:** 2026-04-05
**Author:** claude-wr-reconcile (subagent of claude-sports-db-fix)
**Status:** Investigation complete — root cause identified, peer review requested
**File:** `audit_dashboard/data/dashboard_data.json`

---

## TL;DR

Both rollups are computed in `audit_trail/dashboard_generator.py`. They describe the same universe of closed trades but use **different input datasets**:

| Rollup | Source List | Deduped? | Dead-strat pruned? | Cap |
|---|---|---|---|---|
| `performance.by_asset_class` | `closed` (= `real_closed`) | **NO** | **NO** | none (~12,100 rows) |
| `picks.recent_closed` | `resolved_closed` (deduped) | YES | YES | 3,500 |
| `summary.*` (headline) | `resolved_closed` (deduped) | YES | (partial) | none |

**Root cause:** `performance.by_asset_class` iterates the **pre-dedupe, pre-dead-strategy-pruned** `closed` list. 1,636 mirror duplicates + noise from dead strategies are counted as real trades, dragging WR down from ~52% to ~44% and PnL from +690% to -18,219%.

**Ground truth:** `picks.recent_closed` (and `summary.headline_closed_unique`) — these use deduplicated, valid, realized trades.
**Recommendation:** Fix `by_asset_class` to use `resolved_closed` (post-dedupe); do NOT delete — it's the only per-asset-class rollup the UI has.

---

## Exact Code Paths

### `performance.by_asset_class` computation
**File:** `audit_trail/dashboard_generator.py`
**Function:** inline, builds `ac_breakdown` dict
**Lines:** `9690-9739`
**Emitted:** line `10439` — `"by_asset_class": ac_breakdown`

Input: `for p in active + closed:` at line **9692**, where `closed = real_closed` (set at line **5867**).

`real_closed` is built at lines **5842-5850**: full `closed` list with `_auto_expired` picks removed, but **no deduplication** and **no dead-strategy pruning**.

Per-row logic (line 9704-9718):
```python
b = ac_breakdown[ac]
if p["status"] == "OPEN":
    b["active"] += 1
else:
    b["closed"] += 1                      # increments BEFORE validity check
    if not _is_valid_resolved_pick(p):
        continue                          # paper/expired skip, but count stays
    pnl = float(p.get("pnl_pct", 0) or 0)
    b["pnl"] += pnl
    if pnl > 0:  b["wins"] += 1; ...
    elif pnl < 0: b["losses"] += 1; ...
```

Off-by-note: `b["closed"]` is incremented before validity filtering, so the "closed" count is inflated by paper-trade / expired-without-pnl rows that DO NOT contribute to wins/losses. Also `pnl_pct == 0` falls through (not counted as win OR loss), which is correct, but the "closed" count still includes them.

### `picks.recent_closed` population
**File:** `audit_trail/dashboard_generator.py`
**Function:** `_build_recent_closed_picks(resolved_closed, max_picks=3500, reserved_slots=…)`
**Defined:** line `4037`
**Called:** line `9788`
**Emitted:** line `10435` — `"recent_closed": [_slim_closed_pick(p) for p in recent_closed]`

Input: `resolved_closed` — constructed at lines **9292-9312**:
1. `_filter_valid_resolved_picks(closed)` — drops paper_trade / expired_no_pnl / _auto_expired
2. **Deduplicates mirrors** by `(symbol, direction[0], entry_price, pnl_pct)` — line 9296-9310 (1,636 mirror dupes removed per `summary.headline_mirror_duplicates_removed`)
3. **Prunes dead strategies** (lines 9773-9783): strategies with <3 trades, or ≥5 trades & WR<30%, or avg_pnl<-3% are removed from `resolved_closed`

Then `_build_recent_closed_picks` caps to 3,500 rows with reserved slots for PM/copy-trader track records, sorted by timestamp desc.

`MAX_CLOSED_PICKS = 3500` declared at line **83**.

`summary.*` (headline stats) use the SAME `resolved_closed` list (post-dedupe, post-prune). Lines 9319-9326 compute `wins/losses/zero_pnl_count`.

### Data source (where closed trades originally come from)
Both rollups read from the same in-memory `closed` list — built during `collect_all_picks()` / alpha_engine aggregation much earlier in the generator. Neither reads from a separate MySQL query or external JSON. The divergence is purely in the **post-processing filter chain**.

---

## Side-by-Side Comparison

Computed fresh from `audit_dashboard/data/dashboard_data.json` on 2026-04-05.

### Per-asset-class rollup

| Asset Class | recent_closed n | recent_closed WR | recent_closed PnL | by_asset_class n | by_asset_class WR | by_asset_class PnL | Δ n |
|---|---:|---:|---:|---:|---:|---:|---:|
| CRYPTO    | 2,662 | 52.7% | +669.47 | 10,939 | 44.1% | -18,218.95 | +8,277 |
| FOREX     |   380 | 47.6% |  +15.10 |    479 | 44.3% |      -3.10 |    +99 |
| EQUITY    |   286 | 46.3% |  +72.94 |    495 | 35.2% |    -477.32 |   +209 |
| COMMODITY |   155 | 50.3% |  +18.95 |    164 | 49.0% |     +15.86 |     +9 |
| BOND      |     8 | 57.1% |   +4.94 |      8 | 57.1% |      +4.94 |      0 |
| ETF       |     4 | 75.0% |   +2.01 |     18 | 33.3% |     -25.05 |    +14 |
| FUTURES   |     5 |  0.0% |  -94.14 |     18 |  5.9% |     -96.09 |    +13 |
| SPORTS    |     0 |   —   |    0.00 |      0 |   —   |      0.00 |      0 |
| **TOTAL** | **3,500** | **51.4%** | **+689** | **12,121** | **43.7%** | **-18,800** | **+8,621** |

### Direction rollup (from recent_closed)
- LONG:  n=2,746, WR 51.3%, PnL +489.9
- SHORT: n=754,  WR 52.2%, PnL +199.4

### Headline summary (deduped set, NOT 3,500-capped)
From `data.summary`:
- `total_closed_picks: 12102` (pre-dedupe, post-auto-expired)
- `valid_closed_picks: 5905` (post-dedupe, post-validity)
- `headline_closed_unique: 5905`
- `headline_mirror_duplicates_removed: 1636`
- `auto_expired_excluded: 7562`
- `wins: 4369, losses: 5884, overall_win_rate: 42.1%, total_pnl_pct: -18185.31`

**Note:** The `summary` headline stats (-18,185 PnL, 42.1% WR) match `performance.by_asset_class` sums very closely — both roll up the large, un-capped dataset. `picks.recent_closed` is the ONLY view that reflects the 3,500 post-prune slice.

---

## Root Cause

**Single sentence:** `performance.by_asset_class` counts 1,636 mirror-duplicate trades + thousands of dead-strategy losers that `picks.recent_closed` and `summary.headline_closed_unique` correctly exclude, causing crypto WR to drop from 52.7% → 44.1% and PnL from +669 → -18,219.

### Mechanism
1. After line 5867, `closed = real_closed` (12,102 rows).
2. Line 9292-9312 builds `resolved_closed` = deduped + valid subset (5,905 rows).
3. Line 9777 further prunes dead strategies from `resolved_closed`.
4. BUT `ac_breakdown` at line 9692 iterates the original `closed` (12,102), not `resolved_closed`.
5. The duplicate rows are disproportionately losing trades (mirror-trade behavior on losers produces 2x PnL loss), which is why the PnL divergence is 27x worse than the count divergence.

### Secondary bug
In `ac_breakdown`, `b["closed"] += 1` is incremented before the `_is_valid_resolved_pick` gate (lines 9708-9710). A row that fails validity still increments the "closed" count but never increments "wins" or "losses". This explains why `by_asset_class` totals (closed=12,121, wins+losses=11,834) have a 287-row gap even beyond the dedupe issue — paper/expired rows inflate "closed" without contributing outcomes.

---

## Ground-Truth Recommendation

**For real-money decisions: use `picks.recent_closed` / `summary.headline_*` (the deduped, pruned set).**

Rationale:
- Mirror duplicates are bookkeeping artifacts (same symbol + direction + entry + pnl), not independent trades — counting both double-weights wins AND losses.
- Dead-strategy pruning is legitimate: strategies with <3 trades or WR<30% on ≥5 trades are noise that should not skew aggregates.
- The `summary.headline_*` block was specifically built as the post-dedupe canonical view (per `headline_mirror_duplicates_removed` field).

**Do NOT delete `performance.by_asset_class`** — it is the only per-asset-class view the UI has. Instead **fix its data source**.

**Do relabel** any UI surface currently displaying raw `performance.by_asset_class` numbers as "unreconciled — includes mirrors" until the fix lands.

---

## Patch Sketch (NOT APPLIED — peer review required)

Change the loop input on line 9692 from `active + closed` to `active + resolved_closed`, and gate `b["closed"]` increment behind the validity check:

```python
# audit_trail/dashboard_generator.py ~ line 9690
# BEFORE:
ac_breakdown = {}
for p in active + closed:            # <-- pre-dedupe, pre-prune
    ac = p["asset_class"]
    ...
    if p["status"] == "OPEN":
        b["active"] += 1
    else:
        b["closed"] += 1             # <-- increments before validity gate
        if not _is_valid_resolved_pick(p):
            continue
        ...

# AFTER:
ac_breakdown = {}
# resolved_closed is deduped + dead-strat-pruned at lines 9292-9783.
# Using it here matches summary.headline_* and picks.recent_closed.
for p in active + resolved_closed:
    ac = p["asset_class"]
    ...
    if p["status"] == "OPEN":
        b["active"] += 1
    else:
        # _is_valid_resolved_pick is redundant here (resolved_closed already
        # filtered), but keep for defense-in-depth.
        if not _is_valid_resolved_pick(p):
            continue
        b["closed"] += 1             # now only counts outcome-bearing rows
        pnl = float(p.get("pnl_pct", 0) or 0)
        b["pnl"] += pnl
        ...
```

### Expected post-patch numbers
`by_asset_class` should match the "recent_closed rollup" column in the table above **exactly for rows that fit under the 3,500 cap**, and should EXCEED those numbers slightly for crypto (since `resolved_closed` has 5,905 rows pre-cap but `recent_closed` is capped at 3,500). Expected crypto post-patch: ~5,000 trades, ~52% WR, positive PnL.

### Test plan
1. `py_compile audit_trail/dashboard_generator.py`
2. Rerun via GH Action (NOT locally — never run generators locally per CLAUDE.md).
3. Verify: post-run, `sum(v["closed"] for v in performance.by_asset_class.values())` should equal `summary.valid_closed_picks` (5,905) plus any active OPEN rows.
4. Verify: CRYPTO WR in by_asset_class should match CRYPTO slice of `summary.overall_win_rate` within 2pp.

---

## Concurrent Agent Notes

- Lock acquired on `docs/WR_RECONCILIATION_20260405.md` at investigation start (Redis bus).
- No edits made to hot files (`dashboard_generator.py`, `quality_gates.py`, `template.html`) per constraint.
- No generators were run locally.
- Peer review owner: **antigrav-dash-integrity** (fix owner per task routing).

