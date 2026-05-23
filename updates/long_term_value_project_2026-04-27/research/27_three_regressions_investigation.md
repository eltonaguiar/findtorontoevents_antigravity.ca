# Three Regressions Investigation — 2026-04-28

> **Branch:** `fix/three-regressions-followup-2026-04-28`
> **Worktree:** `/tmp/wt-regressions` (`C:\Users\zerou\AppData\Local\Temp\wt-regressions`)
> **Base:** `feat/integration-wave-risk-controls-2026-04-28` @ `4c65e6698a`
> **Author:** Claude Opus 4.7 (1M context)
> **Investigates:** R1 FOREX PF inversion, R2 phantom HALT alert, R3 circuit-breaker staleness leak.
> **Trigger doc:** `updates/2026-04-28-audit-accuracy-and-pick-quality.md` (commit `b1a820b05b`).

---

## 1. Summary

| ID | Regression | Root cause | Fix branch on origin | Fix on `origin/main`? | Status this PR |
|----|-----------|------------|----------------------|-----------------------|----------------|
| R1 | FOREX headline PF 0.27 vs recompute 1.17 | Two-pool inconsistency: headline aggregator (`performance.by_asset_class`) uses the full `closed`/`real_closed` pool (1,621 FOREX rows) while the visible `picks.recent_closed` slice the auditor recomputed on covers only 801 rows. The wider pool still contains pre-v2 picks resolved by the legacy live-spot path; their `resolver_version` is null. The v2 bar-replay code path is on main, but the legacy-resolved rows have not been re-resolved. | v2 logic on `origin/main` (`97284d22a4`); v2.1 follow-up (10bp + gap-OPEN + time-stop) only on `feat/integration-wave-risk-controls-2026-04-28` (`3086ceafcc`). | v2 yes; v2.1 no | Documented + recommendation only — re-resolve sweep is operational, not a code patch. |
| R2 | Phantom CRITICAL HALT (`-80.8% on 220 picks`) | `cross_aggregation/performance_alerts.py:_daily_loss()` still uses `p.get("unrealized_pnl_pct") or p.get("pnl_pct") or 0` over an unfiltered `active` list, summing realized PnL from terminal-status rows. | `origin/fix/phantom-halt-alert-2026-04-27` (`b51e4d88f3`) | **NO** — branch never merged | **Fix cherry-picked into this branch** (`3c51ec82a8`). |
| R3 | `alpha_engine_fast` silent 111h, `wf_audit_signals` silent 59h | `alpha_engine/circuit_breaker_aggregator.py:get_unified_breaker_state()` resets stale `*_level` to GREEN but leaves the stale `pf_state` dict intact, so `min(max_picks, pf_state.get("max_picks"))` still pulls `max_picks=0` and `min_confidence=1.0` from a 5-week-old `circuit_breaker_state.json` (`level=HALT`, `timestamp=2026-03-24`). | `origin/fix/circuit-breaker-stale-leak-2026-04-27` (`eb099a8229`) | **NO** — branch never merged | **Fix cherry-picked into this branch** (`f533a7318d`). |

**Common cause across R2 + R3:** both fixes were authored on 2026-04-27, pushed to dedicated `fix/*-2026-04-27` branches, but the merge step into `main` never executed. Memory notes `feedback_phantom_halt_alert_bug` and `feedback_circuit_breaker_stale_state_leak` both already say "Fixed; regression tests pinned" — they document the *intent* of the fix branches, not the merged state.

---

## 2. R1 — FOREX PF inversion

### Fix-branch landing audit

```
$ git log --all --grep="bar.replay\|outcome_resolver" | head
b1a820b05b docs(audit): verify dashboard accuracy + 48h pick quality (3 critical bugs)
3086ceafcc fix(resolver): v2.1 — 10bp threshold + gap-OPEN fills + time-stop          ← integration branch only
154e62b0bc fix(resolver): asset-class-gated WIN threshold + bar-replay TP/SL detection ← integration branch only
97284d22a4 fix(resolver): asset-class-gated WIN threshold + bar-replay TP/SL detection ← ON MAIN (PR #463 merge)
```

`97284d22a4` is on `origin/main` and has **byte-identical content** to `154e62b0bc` (`git diff 97284d22a4 154e62b0bc -- alpha_engine/outcome_resolver.py` returns empty). So the v2 bar-replay logic is live in production. The v2.1 follow-up (raise threshold to 10bp, add gap-OPEN fills, add time-stop) is only on the integration branch.

### Code path verification (origin/main)

`alpha_engine/outcome_resolver.py:115-125` — asset-class-gated thresholds: `FOREX: 0.0005` (5bp). Confirmed.

`alpha_engine/outcome_resolver.py:578-635` — `resolve_single_pick()` v2 branch:
- If `is_non_crypto and ohlc_window` → walk OHLC bars looking for TP/SL touch, set `exit_reason=TP_HIT_REPLAY` or `SL_HIT_REPLAY`, stamp `resolver_version=v2`.
- If `is_non_crypto and live_price and ohlc_window is None` → **refuse to close at live spot**; mark `_resolve_retry_needed=True`. ✓ Bug fixed in code.

`alpha_engine/outcome_resolver.py:1900-1955` — `close_active_non_crypto_picks()` also uses bar-replay; sets `resolved_by="non_crypto_resolver"` and `resolver_version="v2"`. ✓

### Live-data evidence (the catch)

Recompute on live `dashboard_data.json` (`picks.recent_closed`):

```
forex_n         = 801
resolver_version: Counter({'none': 801})
resolved_by:      Counter({'none': 801})
exit_reason:      SL_HIT 364, FORCE_CLOSED 284, TP_HIT 109, EXPIRED 34, UNKNOWN 10
PF_recompute   = 1.168                (close to auditor's 1.17)
Live tile      = 0.27 from a wider pool of 1,621 FOREX picks
```

**ZERO** of the 801 visible FOREX picks have `resolver_version=v2`. None carry the new `*_REPLAY` exit_reason codes. They were all resolved by the pre-v2 code (or by the `force_close` path that bypasses bar-replay entirely).

The two-pool inconsistency:
- `summary.non_crypto_performance.categories.FOREX`: `closed=801, win_rate=24.3, total_pnl_pct=10.58` — comes from `recent_closed` (slice of `resolved_closed`, capped at `MAX_CLOSED_PICKS`).
- `performance.by_asset_class.FOREX`: `closed=1621, profit_factor=0.27, pnl=-972.16` — comes from `audit_trail/dashboard_generator.py:11497-11547`, which iterates `active + closed` where `closed = real_closed` (full real-outcome ledger).

### Root cause statement

The v2 bar-replay code is correct and merged. But the production output is dominated by **pre-v2 legacy resolutions** that survive in `closed_picks.json` from before the cutover. Until those are re-resolved (or the headline aggregator is restricted to `resolver_version=v2` rows), the headline tile will keep showing PF 0.27 while the visible recompute window shows PF 1.17.

### Why this is NOT a missing-merge bug

Unlike R2/R3, the fix code IS on `main`. The "regression" is data lag, not code regression. Three remediations possible:

1. **Operational sweep** — run a one-shot script that re-resolves every non-crypto closed pick missing `resolver_version=v2` using the OHLC window. This was anticipated by the v2 design (`_resolve_retry_needed` flag). Out of scope for a code-fix PR.
2. **Aggregator gate** — change `dashboard_generator.py:11497` to skip pre-v2 non-crypto rows. Risk: cuts FOREX `closed` count to ~0 until the sweep runs, looks like a regression.
3. **Wait for natural turnover** — no action; resolver runs every cycle and will eventually re-emit. Slow.

### Recommended

Option 1 (operational sweep) — but as a separate PR / one-off script, not a permanent code change. This investigation does NOT push a code change for R1.

---

## 3. R2 — Phantom HALT alert

### Fix-branch landing audit

```
$ git branch -r --contains b51e4d88f3
  origin/fix/phantom-halt-alert-2026-04-27
```

That's the **only** branch on origin. Not on `main`, not on `feat/integration-wave-risk-controls-2026-04-28`. Confirmed via:

```
$ git show feat/integration-wave-risk-controls-2026-04-28:cross_aggregation/performance_alerts.py | sed -n '247,260p'
def _daily_loss(active):
    alerts = []
    total = sum(float(p.get("unrealized_pnl_pct") or p.get("pnl_pct") or 0) for p in active)
    if total < -5: ...
```

— still the buggy unfiltered code on the integration branch. `b51e4d88f3` was authored 2026-04-27 15:32 EDT but never merged.

### Denominator audit

`cross_aggregation/performance_alerts.py:247-272` (origin/main, unchanged):

```python
def _daily_loss(active):
    alerts = []
    total = sum(float(p.get("unrealized_pnl_pct") or p.get("pnl_pct") or 0) for p in active)
    if total < -5:
        alerts.append(_alert("CRITICAL", "DAILY_LOSS",
            f"Unrealized portfolio PnL {total:+.1f}% -- daily loss limit approaching",
            "HALT",
            total_unrealized_pnl_pct=round(total, 2),
            pick_count=len(active),  # ← over-counts terminal rows
        ))
    ...
```

Three issues, fixed in the patch on `b51e4d88f3`:
1. **Unfiltered `active`**: contains terminal-status rows (WON/LOST/TP_HIT). Patch filters to `status in {OPEN, PENDING, ""}`.
2. **Realized fallback**: `or p.get("pnl_pct")` grabs realized PnL when `unrealized_pnl_pct` is null. Patch drops this fallback.
3. **`pick_count=len(active)`** over-counts. Patch reports `len(open_picks)`.

Live evidence — the bad alert is currently published:

```json
{
  "severity": "CRITICAL",
  "type": "DAILY_LOSS",
  "message": "Unrealized portfolio PnL -80.8% -- daily loss limit approaching",
  "action": "HALT",
  "details": {"total_unrealized_pnl_pct": -80.82, "pick_count": 220}
}
```

### Fix applied (this branch)

Cherry-pick of `b51e4d88f3` → `3c51ec82a8`. Includes 2 regression tests (`tests/test_performance_alerts.py`):
- `test_daily_loss_ignores_realized_pnl_on_terminal_status` — pins the no-fallback rule.
- `test_daily_loss_fires_on_real_unrealized_drawdown` — pins that real drawdowns still trigger.

Tests pass: 6/6 in `test_performance_alerts.py`.

---

## 4. R3 — Circuit-breaker staleness leak

### Fix-branch landing audit

```
$ git branch -r --contains eb099a8229
  origin/fix/circuit-breaker-stale-leak-2026-04-27
```

Not on `main`, not on `feat/integration-wave-risk-controls-2026-04-28`. Confirmed: integration branch's `alpha_engine/circuit_breaker_aggregator.py:117-123` still says `pf_level = "GREEN"` only — does not reset `pf_state = {}`.

### State file inspection

`alpha_engine/data/circuit_breaker_state.json` (current content):

```json
{
  "level": "HALT",
  "max_picks": 0,
  "min_confidence": 1.0,
  "description": "Emergency halt — no new picks",
  "triggers": ["Loss streak 175 >= 25", "Loss streak 175 >= 15", "Loss streak 175 >= 8"],
  "metrics": {"portfolio_dd_pct": 2.0296, "loss_streak": 175,
              "daily_pnl_pct": 0.03351, "closed_picks_count": 527},
  "timestamp": "2026-03-24T06:08:02.492113+00:00"
}
```

**Timestamp 2026-03-24 = ~35 days stale.** Note `loss_streak: 175` is implausible — almost certainly a 5-week-old artifact.

### Heartbeat / consumer audit

`alpha_engine/circuit_breaker_aggregator.py:115-156` (origin/main, unchanged):

```python
# Ignore stale states (>2 hours old)
if _state_age_hours(PORTFOLIO_CB_PATH) > 2.0:
    pf_level = "GREEN"     # ← only resets the LEVEL
# pf_state is still the stale {"max_picks": 0, "min_confidence": 1.0, ...}

worst_level = max(levels, ...)  # GREEN

# Apply most restrictive settings from individual breakers
max_picks = min(
    max_picks,
    pf_state.get("max_picks", max_picks),   # ← pulls 0
    macro_state.get("max_picks", max_picks),
)
min_conf = max(
    min_conf,
    pf_state.get("min_confidence", min_conf),  # ← pulls 1.0
    macro_state.get("min_confidence", min_conf),
)
```

Result: aggregator returns `level=GREEN, max_picks=0, min_confidence=1.0`. Downstream pick generator reads `max_picks=0` and produces no picks, but the dashboard reports `level=GREEN`. Symptom: `alpha_engine_fast hasn't produced a pick in 111h` (live alert at audit time).

`wf_audit_signals` (59h silent) likely shares the same circuit-breaker consumer or has its own stale-state file with the same bug pattern.

### Fix applied (this branch)

Cherry-pick of `eb099a8229` → `f533a7318d`. Treats stale state files as `{}` so their `max_picks`/`min_confidence` keys cannot leak past the staleness check. Includes a new regression-test file (`tests/test_circuit_breaker_aggregator.py`) with 2 tests:
- `test_stale_halt_state_does_not_leak_max_picks` — repros the 5-week-stale HALT state, asserts GREEN/100/0.55.
- `test_fresh_red_portfolio_state_still_restricts` — pins that legitimate fresh non-GREEN states still apply their overrides.

Tests pass: 2/2 in `test_circuit_breaker_aggregator.py`.

**Operational note:** after merge to main, the 35-day-old `circuit_breaker_state.json` in `alpha_engine/data/` will keep tripping the staleness reset (correctly). On the next `alpha_engine_fast` cycle the breaker re-evaluates and rewrites the file with fresh values, so no manual cleanup is needed.

---

## 5. Proposed fixes

### R1 — operational only (no code change in this PR)

Run a one-shot resolver re-pass on legacy non-crypto closed picks. Suggested invocation:

```bash
python -c "
from alpha_engine.outcome_resolver import (
    resolve_single_pick, _fetch_yfinance_ohlc_window, _parse_utc_timestamp,
)
import json, pathlib
# load all non-crypto closed picks where resolver_version != 'v2'
# re-run resolve_single_pick(pick, ohlc_window=_fetch_yfinance_ohlc_window(symbol, entry_dt))
# overwrite back to closed_picks.json
"
```

Tracked separately. Optional gate of `audit_trail/dashboard_generator.py:11497` to require `resolver_version=v2 OR asset_class==CRYPTO` would blank FOREX/COMMODITY tiles until the sweep completes — defer that decision to the operator.

### R2 — `cross_aggregation/performance_alerts.py:247-272`

```diff
+_OPEN_STATUSES = {"OPEN", "PENDING", ""}
+
 def _daily_loss(active):
     alerts = []
-    total = sum(float(p.get("unrealized_pnl_pct") or p.get("pnl_pct") or 0) for p in active)
+    open_picks = [
+        p for p in active
+        if str(p.get("status", "") or "").upper() in _OPEN_STATUSES
+    ]
+    total = sum(float(p.get("unrealized_pnl_pct") or 0) for p in open_picks)
     if total < -5:
         alerts.append(_alert("CRITICAL", "DAILY_LOSS",
             f"Unrealized portfolio PnL {total:+.1f}% -- daily loss limit approaching",
             "HALT",
             total_unrealized_pnl_pct=round(total, 2),
-            pick_count=len(active),
+            pick_count=len(open_picks),
         ))
```

(Plus the parallel branch at `total < -3`.)

Applied as commit `3c51ec82a8` on this branch.

### R3 — `alpha_engine/circuit_breaker_aggregator.py:117-123`

```diff
-    if _state_age_hours(DRAWDOWN_CB_PATH) > 2.0:
-        dd_level = "GREEN"
-    if _state_age_hours(PORTFOLIO_CB_PATH) > 2.0:
-        pf_level = "GREEN"
-    if _state_age_hours(MACRO_CB_PATH) > 2.0:
-        macro_level = "GREEN"
+    if _state_age_hours(DRAWDOWN_CB_PATH) > 2.0:
+        dd_level, dd_state = "GREEN", {}
+    if _state_age_hours(PORTFOLIO_CB_PATH) > 2.0:
+        pf_level, pf_state = "GREEN", {}
+    if _state_age_hours(MACRO_CB_PATH) > 2.0:
+        macro_level, macro_state = "GREEN", {}
```

Applied as commit `f533a7318d` on this branch.

### Combined test result

```
$ python -m pytest tests/test_performance_alerts.py tests/test_circuit_breaker_aggregator.py -v
============================== 8 passed in 0.40s ==============================
```

---

## 6. Sources

### Commit hashes

| Ref | Description |
|-----|-------------|
| `b1a820b05b` | Audit verification doc that flagged the 3 regressions |
| `97284d22a4` | R1 v2 bar-replay fix on origin/main (PR #463 squash) |
| `154e62b0bc` | R1 v2 fix as cherry-picked onto integration branch (byte-identical to `97284d22a4`) |
| `3086ceafcc` | R1 v2.1 follow-up (10bp threshold + gap-OPEN + time-stop) — integration branch only, NOT on main |
| `b51e4d88f3` | R2 phantom HALT fix — only on `origin/fix/phantom-halt-alert-2026-04-27`, not on main |
| `eb099a8229` | R3 circuit-breaker stale-leak fix — only on `origin/fix/circuit-breaker-stale-leak-2026-04-27`, not on main |
| `4c65e6698a` | Branch base (`feat/integration-wave-risk-controls-2026-04-28` HEAD) |
| `3c51ec82a8` | This branch — R2 fix cherry-pick |
| `f533a7318d` | This branch — R3 fix cherry-pick |

### Memory notes

- `feedback_noncrypto_resolver_live_close_bug` — accurate description of R1 mechanism; the marker `outcome_resolver.py:97 + :384-405` predates v2 (line numbers shifted; v2 is now at `:115` for thresholds and `:1900` for the close loop).
- `feedback_phantom_halt_alert_bug` — claims "Fixed; regression tests pinned." This describes the *fix branch state*, not the merged state. The fix did not land on main.
- `feedback_circuit_breaker_stale_state_leak` — claims "Fixed." Same gap: branch exists, never merged.

### Verification reads

- `audit_dashboard/data/dashboard_data.json` (21,488,840 bytes, `generated_at=2026-04-28T20:09:46Z`)
  - `summary.non_crypto_performance.categories.FOREX`: 801 closed, WR 24.3, PnL +10.58%
  - `performance.by_asset_class.FOREX`: 1,621 closed, WR 48.1, PF 0.27, PnL -972.16%
  - `performance_alerts[0]`: CRITICAL HALT -80.8% / 220 picks
  - `performance_alerts[*]`: `alpha_engine_fast` 111h silent, `wf_audit_signals` 59h silent
  - 0/801 FOREX rows in `recent_closed` carry `resolver_version=v2`
- `alpha_engine/data/circuit_breaker_state.json`: `level=HALT, max_picks=0, min_confidence=1.0, timestamp=2026-03-24T06:08:02Z`
- `alpha_engine/data/circuit_breaker.json`: `status=EMERGENCY, total_drawdown_pct=-25,465.5%, updated_at=2026-04-23T07:22:30Z` (different file, also stale; emitted by `portfolio_circuit_breaker.py`, separate concern)
- `alpha_engine/circuit_breaker_aggregator.py:117-156` (origin/main) — confirms the half-applied staleness check
- `cross_aggregation/performance_alerts.py:247-272` (origin/main) — confirms unfiltered `_daily_loss`

### Live test evidence

```
tests/test_performance_alerts.py::test_daily_loss_ignores_realized_pnl_on_terminal_status PASSED
tests/test_performance_alerts.py::test_daily_loss_fires_on_real_unrealized_drawdown PASSED
tests/test_circuit_breaker_aggregator.py::test_stale_halt_state_does_not_leak_max_picks PASSED
tests/test_circuit_breaker_aggregator.py::test_fresh_red_portfolio_state_still_restricts PASSED
```

---

## 7. Recommendations to caller

1. Merge this branch (R2 + R3 only) into `main` via PR. Both fixes are clean cherry-picks of branches that should have merged on 2026-04-27.
2. R1 needs a separate operational sweep: re-resolve all non-crypto closed picks lacking `resolver_version=v2`. Do not gate the aggregator on v2 yet — it would empty the FOREX/COMMODITY tiles until the sweep completes.
3. After R3 merges, monitor `alpha_engine_fast` and `wf_audit_signals` workflows to confirm pick emission resumes within 1-2 cycles. If `wf_audit_signals` does not resume, look for a second stale state file specific to that emitter.
4. Update memory notes `feedback_phantom_halt_alert_bug` and `feedback_circuit_breaker_stale_state_leak` to add a "Merge state" line: distinguish "fix branch authored" from "fix on main."
