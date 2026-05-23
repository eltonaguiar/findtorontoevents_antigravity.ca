# VERDICT: GATE_REGRESSION

**Date:** 2026-05-08  
**Reviewer:** Claude Code (automated verification)  
**Subject:** Week-1 follow-up — rapid_fire pair-blocklist bypass fix (PR #597 / B11)  
**Observation window:** 2026-05-01T23:00Z → 2026-05-08T23:00Z (7 days)

---

## 1. Commit / PR Merge Status

| Check | Result |
|---|---|
| Commit `ae31b43979` on origin/main | **NOT_MERGED** — hash not traceable in git log |
| Fix code present in `isolated_signal_integrator.py` | **YES** — merged via squash/auto-update commit `6720a895` (2026-05-02 06:42 UTC) |
| PR #597 branch still open | Branch `investigate/usdchf-concentration-2026-05-01` — not visible in current remotes |

**Effective commit status:** The code fix landed on main (evidenced by lines 675-685 of `isolated_signal_integrator.py`) but the original commit hash `ae31b43979` was squash-merged and is no longer traceable. The fix is WIRED in the integrator path.

---

## 2. Gate Presence Check

```
grep -n 'is_blocked_pick' alpha_engine/isolated_signal_integrator.py
```

| Line | Content |
|---|---|
| 29 | `from alpha_engine.strategy_blocklist import is_blocked_pick, pick_block_reason` |
| 32 | `from strategy_blocklist import is_blocked_pick, pick_block_reason` (local fallback) |
| 34 | `def is_blocked_pick(_pick): return False` (import-failure no-op fallback) |
| 675 | `if is_blocked_pick({"strategy": strategy, "source_system": source_name}):` |

**Gate status in integrator:** `GATE_PRESENT` (4 hits, correct import + call site with comment referencing the B11 fix)

---

## 3. Breach Count Table

### `rapid_fire_data/closed_picks.json` (post-fix window ≥ 2026-05-01T23:00Z)

| Retired Pair | n_post_fix | WR | sum_pnl | First Breach | Last Breach |
|---|---|---|---|---|---|
| `rapid_fire` + `macd_rsi_confluence` | **28** | 50% | +14.0% | 2026-05-02T01:09Z | 2026-05-08T22:10Z |
| `rapid_fire` + `rsi_bounce` | **7** | 29% | −5.0% | (in window) | (in window) |
| `kimi_signal_tracking` + `default` | 0 | — | — | — | — |
| `copy_trader_intel` + `copy_hl_lb_None` | 0 | — | — | — | — |
| `alpha_engine` + `copy_hl_lb_None` | 0 | — | — | — | — |
| `goldmine_stocks` + `goldmine_5x_consensus` | 0 | — | — | — | — |
| `goldmine_stocks` + `goldmine_6x_consensus` | 0 | — | — | — | — |
| `goldmine_stocks` + `goldmine_7x_consensus` | 0 | — | — | — | — |

**`n_post_fix_breaches` = 35** (28 + 7)

### `audit_dashboard/data/dashboard_data.json` `recent_closed` slice (1093 post-fix picks)

| Retired Pair | n_dashboard_post_fix |
|---|---|
| `rapid_fire` + `macd_rsi_confluence` | **0** |
| `rapid_fire` + `rsi_bounce` | **0** |
| All other retired pairs | **0** |

**`n_dashboard_post_fix` = 0**

### Still-active banned picks in `rapid_fire_data/active_picks.json`

**0** — no currently open banned picks.

---

## 4. Root Cause Analysis — Why the Gate Fails

The integrator gate is wired correctly but guards **only one of two write paths** into `rapid_fire_data/closed_picks.json`:

```
Path A (GATED — clean):
  rapid_fire source → isolated_signal_integrator.py:675 → is_blocked_pick() → BLOCKED
  → main system active picks → alpha_engine closed picks → dashboard_data.json

Path B (UNGATED — leaking):
  rapid_fire scanner → rapid_fire_data/active_picks.json (NO gate)
      ↓
  rapid_fire_data/pick_tracker.py → check_tp_sl() → make_closed_record()
      ↓
  rapid_fire_data/closed_picks.json (NO is_blocked_pick() call)
```

`pick_tracker.py` is the bypass. Its `main()` function loads `active_picks.json`, checks TP/SL/time exits, and calls `make_closed_record()` — all without any blocklist check. It also does not filter `active_picks.json` on load.

This matches the memory anchor `memory/feedback_gate_at_execution_not_generation.md`: the gate was placed at signal **ingestion** into the main system, but the rapid_fire subsystem has its own execution loop that bypasses the main integrator entirely.

**Why the dashboard is clean:** The dashboard reads from `alpha_engine`'s closed picks (Path A), which IS fully gated. The dashboard never reads `rapid_fire_data/closed_picks.json` directly.

**Why the raw JSON is dirty:** `rapid_fire_data/closed_picks.json` is the rapid_fire-subsystem's own ledger, written exclusively by `pick_tracker.py` (Path B), which has no blocklist protection.

---

## 5. Post-Fix Observation Window Summary

- **Window:** 2026-05-01T23:00Z → 2026-05-08T22:10Z (7 days, 1 hour)
- **Total rapid_fire closed picks in window:** 72
- **Banned-pair picks that closed:** 35 (48.6% of all rapid_fire closes in window)
- **Net P&L from banned picks:** +14.0% (macd_rsi_confluence, 50% WR) + −5.0% (rsi_bounce, 29% WR) = **+9.0% combined**
- **Production risk:** The banned pairs' net positive P&L in this window is deceptive — the kill decision was based on n=133 BANNED-tier history (WR 36.8%, −48.88% sum). A 7-day 50% WR window is noise, not rehabilitation.
- **Dashboard integrity:** INTACT — zero breaches in the audit path.

---

## 6. Verdict

**GATE_REGRESSION**

The B11 fix successfully protects the main execution path (dashboard = clean, 0 audit breaches). However, the rapid_fire subsystem's own pick tracker (`rapid_fire_data/pick_tracker.py`) is an unprotected bypass channel. 35 picks from two retired pairs closed in the 7-day post-fix window via this path.

---

## 7. Recommendation

**Re-investigate: add blocklist gate to `pick_tracker.py`**

Two changes required (do NOT modify production code in this PR — this is a read-only verification):

### Fix A — Filter on load in `pick_tracker.py` `main()`
```python
# After: active = load_json(ACTIVE_FILE)
from alpha_engine.strategy_blocklist import is_blocked_pick
active = [p for p in active
          if not is_blocked_pick({"strategy": p.get("strategy",""),
                                   "source_system": p.get("source_system","rapid_fire")})]
```

### Fix B — Gate at active_picks write time (rapid_fire scanner)
Identify the scanner that populates `rapid_fire_data/active_picks.json` and add the same `is_blocked_pick()` check before appending.

### Acceptance criteria for closure
- `n_post_fix_breaches == 0` in `rapid_fire_data/closed_picks.json` for any 48h window after Fix A lands
- `rapid_fire_data/active_picks.json` contains zero picks with `strategy in {'macd_rsi_confluence','rsi_bounce'}`
- Dashboard `n_dashboard_post_fix` remains 0 (already passing)

### Priority
**P0** — 35 picks/week is high throughput for a banned strategy. The macd_rsi_confluence historical record is n=133, WR 36.8%, −48.88% sum. The current 7-day 50% WR is within noise at n=28.

---

## References

- Fix commit (intended): `ae31b43979` on branch `investigate/usdchf-concentration-2026-05-01` (PR #597) — squash-merged, hash not traceable
- Actual commit on main: `6720a895` (2026-05-02 06:42 UTC auto-update batch)
- Pre-fix breach report: `reports/24h_verification_2026_04_30.md` §C
- Memory anchor: `memory/feedback_gate_at_execution_not_generation.md`
- Kill decision: `reports/strategy_kill_rapid_fire_macd_rsi_confluence_2026_04_29.md`
- Bypass file: `rapid_fire_data/pick_tracker.py` (no `is_blocked_pick` call)
- Gate file: `alpha_engine/isolated_signal_integrator.py:675`
