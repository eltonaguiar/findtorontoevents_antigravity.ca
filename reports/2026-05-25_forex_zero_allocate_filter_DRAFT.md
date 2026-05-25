# FOREX Zero-Allocate Filter — Investigation + Filter Draft

**Date:** 2026-05-25
**Status:** DRAFT — no code applied, no commits, no DB mutation
**Operator gate:** docs/INCIDENTS_TRIAGE_PROCESS_2026-05-25.md Phase 3 (operator approval required)
**Related drafts (sequence before merging):**
- `reports/2026-05-25_smart_picks_inverted_weight_fix_DRAFT.md` — touches `smart_picks_engine.py` (confidence weighting). No file overlap with this draft.
- `reports/2026-05-25_high_conviction_trust_score_audit.md` — trust_score NULL audit, no proposed code changes yet. No file overlap with this draft.

---

## 1. What the plan ACTUALLY says

Source: `reports/EDGE_CRITERIA_ACTION_PLAN_2026-05-24.md`

The plan calls for a **full zero-allocation kill of all FOREX**, not "longs only", not "specific strategies", not "paper-only demote". Direct quotes:

- Title row (line 14): "Additional — FOREX exclusion ... both agree it's low-effort"
- Section 3.3 (lines 31-34):
  > **Both agree:** Zero allocation is the right first step.
  > **Cerebras:** "Kill the inverse signal idea — the statistical evidence strongly suggests the signal is bad, not merely mis-scaled."
  > **Resolution:** Zero-allocate FOREX immediately. Kill the faded signal experiment.
- Sprint 1 row 3 (line 44):
  > **FOREX — Zero allocation** | `alpha_engine/scanner.py` filter stage | ~8 | `SELECT COUNT(*) WHERE asset_class='FOREX'` → 0
- Deferred/Killed (line 72):
  > FOREX faded signal | **Killed** | Both engines agree: signal is bad, not mis-scaled.

**The verification criterion is explicit:** `SELECT COUNT(*) WHERE asset_class='FOREX'` should return **zero** new picks after the filter ships.

**Caveat — the `cta_replicator` carve-out is a separately-blessed exception.** Commit `e9dcfdca8` (2026-05-24, ~6 hours before the action-plan synthesis) isolated `cta_replicator` (PF 2.51, n=97, WR 64.9%) into a `FOREX_HIGH_CONVICTION` sub-class with a 0→15% allocation carve-out. The allocation-cap commit `cc8acc77c` ratified this: FOREX 0%, FOREX_HIGH_CONVICTION not in the zero set. So "zero-allocate FOREX" means **`category='FOREX'`**, not `FOREX_HIGH_CONVICTION`.

---

## 2. What was actually implemented (and why it leaks)

Commit `e9dcfdca8` added a kill-switch at `alpha_engine/scanner.py:2559-2566`:

```python
# FOREX zero-allocation (2026-05-24): kill-switch per EDGE_CRITERIA_ACTION_PLAN.
# Both swarm engines agree: FOREX signal is bad, not mis-scaled. Zero-allocate.
# Verification: SELECT COUNT(*) WHERE asset_class='FOREX' → 0.
if cat == "FOREX":
    sig["confidence"] = 0.0
    sig["forex_killed"] = True
    nc_blocked += 1  # count in summary log
    continue  # skip — do not append to cleaned_signals
```

**This filter only runs inside `nc_quality_gate` (scanner.py:2511-2596), which only sees signals emitted by `alpha_engine/scanner.py`'s own strategy loop.** Every other source that writes to `trading_picks` bypasses it entirely:

DB query confirms (`SELECT ... FROM trading_picks WHERE category='FOREX' AND created_at >= '2026-05-24'`):

| source_system                   | count | window                                    |
|----------------------------------|-------|--------------------------------------------|
| multi_asset_copytrader           | 164   | 2026-05-24 00:47 → 2026-05-25 05:04        |
| non_crypto_consensus             | 118   | 2026-05-24 00:54 → 2026-05-25 03:56        |
| cta_replicator (legitimate HC)   |  39   | 2026-05-24 00:48 → 2026-05-25 05:04        |
| combined_confidence_strategy     |  25   | 2026-05-24 00:28 → 2026-05-24 22:53        |
| forex_copy_trader                |  21   | 2026-05-24 03:11 → 2026-05-25 00:49        |
| regime_terminal                  |  18   | 2026-05-24 01:49 → 2026-05-25 03:57        |
| alpha_engine                     |   1   | 2026-05-24 08:56                           |
| prediction_market_agents         |   1   | 2026-05-24 23:22                           |
| **TOTAL**                        | **387** | 2026-05-24 00:28 → 2026-05-25 05:04      |

- Day breakdown: 318 on 2026-05-24, 69 on 2026-05-25 (through 05:04 UTC). The 14-day sweep's 368-figure is consistent — current count is **387** (still climbing).
- Subtracting the legitimate `cta_replicator` HC carve-out (39 rows), there are **348 in-scope FOREX picks** that should have been killed but weren't.
- Top strategies: `non_crypto_consensus` (118), `forex_rsi2_mean_reversion` (72 — note this is in `EXTRA_KILLED_FOREX_STRATEGIES` per commit `25e03227e`, the kill is also leaking), `ig_contrarian_sentiment` (63), `myfxbook_retail_contrarian` (50), `cta_cross_asset_tsmom` (40, mostly the cta_replicator HC), `combined_confidence` (26), `regime_mild_bear` (18).

**Diagnosis:** the scanner-side filter is at the wrong pipeline stage. Picks from `multi_asset_copytrader`, `non_crypto_consensus`, `forex_copy_trader`, `regime_terminal`, `combined_confidence_strategy`, `prediction_market_agents` are all merged into `active` *downstream* of `nc_quality_gate` (see `production_scanner.py:3870` which appends `forex_copy_trader` picks directly to `active` with `asset_class="FOREX"` and no gate). They never traverse the scanner kill-switch.

The strategy-level kills in `quality_gates.py::EXTRA_KILLED_FOREX_STRATEGIES` (lines ~2114, ~3114) only halve confidence in scanner-internal flows; downstream merges bypass them.

---

## 3. Where the filter SHOULD go

There is exactly one funnel that **every** FOREX pick flows through before becoming visible in `trading_picks`: `alpha_engine/mysql_trading_sync.py::sync()` → `pick_to_row()` → batch `UPSERT_SQL`. Filtering here is leak-proof and surface-agnostic.

Defense-in-depth: also add a hard `BLOCKED_ASSET_CLASSES_FOR_EMISSION` set in `audit_trail/quality_gates.py` so any future caller that goes through `passes_active_gate` / `passes_smart_gate` also rejects.

---

## 4. DRAFT — Preferred filter (block all `category='FOREX'`, allow `FOREX_HIGH_CONVICTION`)

### 4a. Primary gate: `alpha_engine/mysql_trading_sync.py` (the single emission funnel)

**File:** `alpha_engine/mysql_trading_sync.py`
**Insert after line 485** (after the `for pick in all_active + all_closed:` loop builds `rows`, but before `log_ok(f"Prepared {len(rows)} unique rows for upsert")`).

The cleanest spot is inside the build loop. Modify lines 477-485:

```python
# Build rows
rows = []
seen_ids = set()
forex_blocked = 0  # 2026-05-25 zero-allocate enforcement
for pick in all_active + all_closed:
    pid = pick.get("id", "")
    if not pid or pid in seen_ids:
        continue
    seen_ids.add(pid)

    # 2026-05-25 — FOREX zero-allocation enforcement (per
    # reports/EDGE_CRITERIA_ACTION_PLAN_2026-05-24.md Sprint 1 item 3).
    # The scanner.py:2562 kill-switch only covers nc_quality_gate flows;
    # picks from multi_asset_copytrader, non_crypto_consensus,
    # forex_copy_trader, regime_terminal, combined_confidence_strategy,
    # and prediction_market_agents bypass it (387 leaked picks in
    # 28h since e9dcfdca8 shipped — see
    # reports/2026-05-25_forex_zero_allocate_filter_DRAFT.md).
    # FOREX_HIGH_CONVICTION is a separately-blessed carve-out
    # (cta_replicator, PF 2.51) per commit e9dcfdca8 — do NOT block.
    _cat = str(pick.get("category") or pick.get("asset_class") or "").upper()
    if _cat == "FOREX":
        forex_blocked += 1
        continue

    try:
        rows.append(pick_to_row(pick))
    except Exception as e:
        continue

if forex_blocked:
    log_ok(f"FOREX zero-allocate: blocked {forex_blocked} pick(s) from emission")

log_ok(f"Prepared {len(rows)} unique rows for upsert")
```

**Why this is leak-proof:**
- Every JSON source listed in `JSON_PICK_SOURCES` (dashboard_generator.py) gets normalized through this loop.
- `cta_replicator` legitimate HC picks carry `category='FOREX_HIGH_CONVICTION'` (commit `e9dcfdca8` reclassifies at scanner.py:2553-2556) — they pass the gate cleanly.
- Edge case: if any HC pick still has `category='FOREX'` because it was emitted by a path that bypasses the scanner.py reclassification, it gets blocked. That is the safer default — operator can audit `forex_blocked` count vs `cta_replicator` count in the next sync and reclassify upstream if needed.

### 4b. Defense-in-depth: `audit_trail/quality_gates.py`

**File:** `audit_trail/quality_gates.py`
**Insert at line 1712** (replace the existing one-liner):

```python
BLOCKED_ASSET_CLASSES: set = set()  # Was {"FUTURES"} — removed 2026-04-16; -60 penalty created data starvation catch-22

# 2026-05-25 — Hard emission block for asset classes that have been
# zero-allocated by the swarm consensus. Unlike BLOCKED_ASSET_CLASSES
# (which only applies a score penalty), this set causes passes_active_gate
# and passes_smart_gate to return False outright. FOREX_HIGH_CONVICTION
# (cta_replicator carve-out, PF 2.51 — commit e9dcfdca8) is intentionally
# NOT in this set.
# Source: reports/EDGE_CRITERIA_ACTION_PLAN_2026-05-24.md Sprint 1 item 3.
BLOCKED_ASSET_CLASSES_FOR_EMISSION: frozenset = frozenset({"FOREX"})
```

Then wire it into `passes_active_gate` and `passes_smart_gate` — both call `score_pick` first, but the cleanest insertion is at the top of each (before any score work). Find each function and add right after the `_asset_class` extraction:

```python
_asset_class = str(pick.get("asset_class", "") or "").upper()
if _asset_class in BLOCKED_ASSET_CLASSES_FOR_EMISSION:
    return False  # 2026-05-25 zero-allocate enforcement (FOREX)
```

(Exact line numbers depend on each function's structure; operator should grep `def passes_active_gate` and `def passes_smart_gate` and place the guard at the function head.)

### 4c. Belt-and-braces: scanner-side guards

The existing `scanner.py:2562` block is **correct in shape but reaches only some signals**. Two additional early-exit guards needed:

- `alpha_engine/production_scanner.py:3867-3881` — the `forex_copy_trader` merge loop appends to `active` unconditionally. Wrap with:
  ```python
  if str(_fp.get("category", "")).upper() == "FOREX":
      continue  # 2026-05-25 zero-allocate (forex_copy_trader is in scope)
  ```
  Place inside the `for _fp in _fxct_raw:` loop, right after the `isinstance` check at line 3869.

- `alpha_engine/smart_picks_engine.py:1614-1616` — same pattern for the smart-picks `forex_copy_trader` merge; mirror the guard above.

These two upstream guards are optional given the mysql_trading_sync gate (4a) is leak-proof, but they save CPU and prevent FOREX picks from polluting JSON snapshots that downstream tools may read independently of the DB.

---

## 5. ALT — Paper-only route (if operator overrides "kill" → "paper")

The plan unambiguously says "zero-allocate" and "kill". This alt is documented only for completeness in case the operator wants a 30-day shadow period.

**Sketch (do not apply):** instead of `continue` in §4a, route the pick to a separate sink:

```python
if _cat == "FOREX":
    _paper_sink.append(pick)  # accumulated; written to alpha_engine/data/active_picks_paper.json at loop end
    continue
```

Then at the end of `sync()`, write `_paper_sink` to `alpha_engine/data/active_picks_paper.json`. This file is **not** in `JSON_PICK_SOURCES` so it never reaches `trading_picks`, but it is preserved for back-testing.

Cons: requires a new file path the resolver doesn't know about, requires extending `outcome_resolver.py` to attribute outcomes, and contradicts the plan's verification criterion (`SELECT COUNT(*) WHERE asset_class='FOREX' → 0`). Recommend against unless operator explicitly wants it.

---

## 6. Predicted impact

- **Picks suppressed/day:** based on the 28h DB window (387 picks − 39 `cta_replicator` HC = 348 suppressed in ~28h) → **~298 picks/day suppressed.**
- **Dashboard surfaces affected:**
  - `audit_dashboard/data/dashboard_data.json::performance.asset_class_health.FOREX` — `n` drops to near-zero (only resolved closed picks pre-filter remain in the historical rollup; new emissions stop). The rollup is read from `trading_picks` per `audit_trail/dashboard_generator.py`, so the live verdict number will accurately reflect "no new emissions".
  - `audit_dashboard/data/dashboard_data.json::performance.by_asset_class.FOREX` — same.
  - `audit_dashboard/data/dashboard_data.json::strategies` — FOREX strategies (`non_crypto_consensus`, `forex_rsi2_mean_reversion`, `ig_contrarian_sentiment`, `myfxbook_retail_contrarian`, `regime_mild_bear`, `combined_confidence`) stop accumulating new sample. Existing sample is preserved.
  - `FOREX_HIGH_CONVICTION` rollup — **unaffected**, `cta_replicator` continues to emit and resolve.
- **Risk register:**
  - **Catch-22 risk (LOW):** unlike the 2026-04-16 `BLOCKED_ASSET_CLASSES={FUTURES}` rollback (data starvation from `-60` penalty), this is a clean emission block. No "needs sample to validate" loop because the explicit policy decision is *zero-allocate*, not "wait for better sample".
  - **Misclassification risk (LOW):** if a `cta_replicator` pick somehow gets emitted with `category='FOREX'` instead of `FOREX_HIGH_CONVICTION`, it would be blocked. The `forex_blocked` log counter is the canary — if `forex_blocked` < expected (~300/day) AND `cta_replicator` emission count drops, investigate the scanner.py:2553-2556 reclassification path.
  - **Verification feedback loop:** the plan's own success criterion (`SELECT COUNT(*) WHERE asset_class='FOREX' AND created_at > deploy_ts` → 0) gives a 1-hour verifiable signal.

---

## 7. A/B-style validation plan

After hypothetical merge:

1. **Pre-merge baseline** (already captured): 387 FOREX picks in `trading_picks` between 2026-05-24 00:28 and 2026-05-25 05:04 (28h window). Of those, 39 are `cta_replicator` (legitimate).
2. **Post-merge T+1h check:**
   ```sql
   SELECT COUNT(*) FROM trading_picks
   WHERE category='FOREX' AND created_at >= <merge_ts>;
   ```
   Expected: 0. Any non-zero → filter has a leak; investigate which `source_system` slipped through.
3. **Post-merge T+1h sanity for the carve-out:**
   ```sql
   SELECT COUNT(*) FROM trading_picks
   WHERE category='FOREX_HIGH_CONVICTION' AND source_system='cta_replicator'
     AND created_at >= <merge_ts>;
   ```
   Expected: > 0 (cta_replicator typically emits ~33/day). If zero, the §4a guard is too broad — the carve-out's category-string is not making it through one of the upstream merges.
4. **Post-merge T+24h dashboard check:** `dashboard_data.json::performance.asset_class_health.FOREX.window_picks_14d` should plateau (no new additions, old ones age out over 14d).
5. **Post-merge T+24h log audit:** `grep "FOREX zero-allocate: blocked" logs/mysql_trading_sync.*.log` — count should equal pre-merge daily emission rate (~298/day).

If steps 2-5 pass: filter holds. Then schedule a cleanup PR to also wire 4b/4c so the gate is enforced earlier and the JSON snapshots stay clean too.

---

## 8. Files touched in proposed diff (for sequencing review)

| File | Lines | Purpose | Conflict with sibling drafts? |
|------|-------|---------|-------------------------------|
| `alpha_engine/mysql_trading_sync.py` | ~477-487 | Primary emission gate | No — sibling DRAFT `smart_picks_inverted_weight_fix` touches `smart_picks_engine.py` only. |
| `audit_trail/quality_gates.py` | 1712 + 2 insertions in `passes_active_gate` / `passes_smart_gate` | Defense-in-depth | No — trust_score audit is read-only. |
| `alpha_engine/production_scanner.py` | ~3869 | Optional upstream guard | No. |
| `alpha_engine/smart_picks_engine.py` | ~1614 | Optional upstream guard | **POTENTIAL** — sibling `smart_picks_inverted_weight_fix_DRAFT.md` also edits this file. Operator should sequence: merge smart_picks_inverted_weight_fix first (different lines, no conflict expected), then this guard. |

---

## 9. Operator decision required

**ONE binary decision:** block FOREX emission outright (§4 preferred) vs route to paper-only sink (§5 alt).

Plan language ("zero-allocate", "kill", `COUNT → 0`) strongly supports §4. §5 is documented only as a fallback if operator wants a shadow validation period before fully killing.
