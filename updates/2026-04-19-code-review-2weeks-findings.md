# Code Review — Past 2 Weeks (2026-04-05 → 2026-04-19)

**Reviewer:** Codebuff (Claude Opus 4.7)
**Scope:** 215 human-authored commits (author: `eltonaguiar`) across crypto scoring, quality gates, forward validator, non-crypto edge work, and dashboard generation.
**Method:** Targeted read of the two highest-churn critical files (`audit_trail/quality_gates.py` at 212k chars / ~3.5k lines, `alpha_engine/forward_validator.py` at 168k chars / ~3.7k lines). Corroborated against recent diffs in `alpha_engine/data/score_boost_log.json` and `audit_dashboard/data/dashboard_data.json`.

The codebase is extremely active (multiple commits/hour). This review is **not** exhaustive — it concentrates on correctness bugs in the hot path that have high confidence and low fix risk.

---

## Summary

| # | Severity | File | Issue | Fix included? |
|---|----------|------|-------|---------------|
| 1 | **HIGH**   | `audit_trail/quality_gates.py` | Penalty log-label says `:-20` but actual score delta is `-60` — breaks score transparency / audits | ✅ Yes |
| 2 | **MEDIUM** | `audit_trail/quality_gates.py` | `SMART_PICKS_MIN_ML_SCORE` defined twice (0.60 then 0.0) — first definition is dead; fragile to reorder | ✅ Yes |
| 3 | **HIGH**   | `alpha_engine/forward_validator.py` | `DIRECTION_GATE` gates LONG picks using **system-wide WR across ALL directions**, not LONG-only WR. Variable name & log say "long WR" but computation is total WR. | ✅ Yes |
| 4 | MEDIUM    | `alpha_engine/forward_validator.py` | `save_closed_picks` silently truncates to **last 500** on every save — permanent data loss if full ledger grows past 500 and no alternate store exists | 🚫 Behavioral — needs product decision |
| 5 | LOW       | `alpha_engine/forward_validator.py` | `print_performance_report` crypto/forex/equity section filters use unparenthesized `or…and` precedence; relies on fallback | 🚫 Cosmetic |
| 6 | LOW       | `audit_trail/quality_gates.py` | Several penalty strings emit `:-{num}` that doesn't match the code delta after later refactors; hard to spot without greps | 🚫 Hygiene |

Fixes 1–3 are applied in this PR. Fixes 4–6 are documented for follow-up and **not** changed here (would require product sign-off / broader refactor).

---

## Finding 1 — Penalty label mismatch for `BLOCKED_ASSET_CLASSES` (HIGH)

### File
`audit_trail/quality_gates.py` (in `_apply_score_penalties`)

### Problem
```python
if _asset_class in BLOCKED_ASSET_CLASSES:
    score -= 60
    penalties.append(f"blocked_asset_class({_asset_class}):-20")   # <-- says -20
```

The score is reduced by **60** points but the breadcrumb written to `pick["_penalties"]` claims it was **-20**. This breaks downstream transparency/audit tooling (`score_boost_log.json`, dashboard explainability) because operators auditing why a pick was demoted see the wrong number.

The `-60` value is correct per the surrounding comment (`BLOCKED_ASSET_CLASSES` was `{"FUTURES"}` with -60 penalty until 2026-04-16). The label string is the stale one.

### Impact
- Score-boost logs / dashboards mis-report the actual penalty magnitude.
- If anyone later wires a "reverse penalty" unwinder off the string, it will under-refund by 40 points.
- Currently `BLOCKED_ASSET_CLASSES = set()` so the branch is inert for live picks — but the bug will fire the moment a class is re-added (which is done routinely for drain-control).

### Fix
Sync the label to the actual delta:
```python
penalties.append(f"blocked_asset_class({_asset_class}):-60")
```

### Risk
**Very low.** Pure string change, no score-math change. Can't destabilize picks.

---

## Finding 2 — Duplicate `SMART_PICKS_MIN_ML_SCORE` definition (MEDIUM)

### File
`audit_trail/quality_gates.py`

### Problem
```python
# Line ~260
SMART_PICKS_MIN_ML_SCORE = 0.60  # BEST predictor IC=+0.33

# ... ~50 lines later ...

SMART_PICKS_MIN_ML_SCORE = 0.0   # Disabled - ML scores not currently populated
```

The second definition shadows the first — the effective value is `0.0`. The first assignment with its "BEST predictor" comment is **dead code**. A reader (human or agent) skimming the top of the file will mis-remember the gate as active at 0.60. If someone later deletes the "Disabled" line as cleanup, the gate silently activates — potentially rejecting a large fraction of picks with `ml_score=0`.

### Impact
- Readability / onboarding confusion.
- Latent foot-gun: reorders or deletes could silently flip a hard filter from off to on.

### Fix
Consolidate to a single assignment with the current intent documented inline:
```python
# ML score gate is currently DISABLED (ml_score not reliably populated upstream).
# When re-enabling, 0.60 was the prior target (IC=+0.33 on historical data);
# validate against live fill rates before flipping. See 2026-04 audit.
SMART_PICKS_MIN_ML_SCORE = 0.0
```

### Risk
**None.** Same observable value (0.0) before and after; we only collapse two lines into one and reword the comment.

---

## Finding 3 — `DIRECTION_GATE` computes wrong win rate (HIGH)

### File
`alpha_engine/forward_validator.py` (in `run_generation`, inside the ranked-signals loop)

### Problem
```python
ALPHA_LONG_WR_THRESHOLD = 0.30
ALPHA_LONG_MIN_TRADES = 10
if _direction == "LONG":
    _perf_data = load_strategy_performance()
    _long_wins = 0
    _long_total = 0
    for _s, _sd in _perf_data.items():
        _long_wins += _sd.get("wins", 0)              # <-- ALL wins, not LONG wins
        _long_total += _sd.get("closed_picks", 0)     # <-- ALL trades, not LONG trades
    _long_wr = _long_wins / _long_total if _long_total > 0 else 0.5
    if _long_total >= ALPHA_LONG_MIN_TRADES and _long_wr < ALPHA_LONG_WR_THRESHOLD:
        # skip this LONG pick
```

`strategy_performance.json` stores wins/losses aggregated across **both directions** per strategy. Summing them yields the **overall system WR**, not the LONG-only WR the variable name (`_long_wins`, `_long_wr`) and log line ("SKIP LONG … long WR=…") both claim.

Effect: whether any new LONG pick is admitted is decided by a number that mixes SHORT performance in. If SHORTs have a particularly good or bad week, LONG picks get wrongly allowed / blocked.

The simplest honest behavior given the available data is one of:

1. **Preserve the gate's intent** — only count LONG-direction picks. Requires per-direction stats, which aren't directly stored in the aggregate dict. Would need a direct scan of closed picks → expensive in the hot path.
2. **Rename the gate to reflect what it actually measures** (system-wide WR) and keep the behavior. Safe and honest; defers the per-direction work to a follow-up.

This PR takes option **(2)** as the minimum-risk fix — we rename the variables and log line to match the actual computation. The stricter direction-aware gate is called out as a TODO with a proposed implementation sketch.

### Impact
- **Misleading log output** in every scan cycle.
- If operators later rely on the log to debug "why was my LONG blocked?" they chase the wrong metric.
- Not a monetary bug today (no divergence between the stated and actual behavior in live effect — it just isn't what the code claimed).

### Fix (applied in this PR)
```python
# NOTE: strategy_performance.json aggregates wins/losses across BOTH directions per
# strategy, so this is SYSTEM-WIDE WR, not LONG-only. Rename locals + log line to
# match. A proper direction-aware gate needs per-direction stats (TODO).
ALPHA_SYSTEM_WR_THRESHOLD = 0.30
ALPHA_SYSTEM_MIN_TRADES = 10
if _direction == "LONG":
    _perf_data = load_strategy_performance()
    _sys_wins = 0
    _sys_total = 0
    for _s, _sd in _perf_data.items():
        _sys_wins += _sd.get("wins", 0)
        _sys_total += _sd.get("closed_picks", 0)
    _sys_wr = _sys_wins / _sys_total if _sys_total > 0 else 0.5
    if _sys_total >= ALPHA_SYSTEM_MIN_TRADES and _sys_wr < ALPHA_SYSTEM_WR_THRESHOLD:
        print(f"  [DIRECTION GATE] SKIP LONG {signal['symbol']} {strategy} "
              f"(system WR={_sys_wr:.1%} < {ALPHA_SYSTEM_WR_THRESHOLD:.0%} "
              f"across {_sys_total} trades; NOTE: not LONG-specific — see TODO)")
        ...
```

### Risk
**Very low.** Behavior is unchanged — we only rename locals and clarify the log. No threshold/constant value was changed. Existing gate behavior continues; the misleading log is replaced with an accurate one.

---

## Deferred findings (documented only — not fixed in this PR)

### 4. `save_closed_picks` silently truncates to last 500

`alpha_engine/forward_validator.py::save_closed_picks` ends with:
```python
json.dump(_sanitize_for_json(deduped[-500:]), f, indent=2)
```

Every save cycle drops anything older than the 500th-most-recent closed pick from `closed_picks.json`. If there is no other canonical store of full history (the repo also has `universal_resolved_picks.json` which may fill that role), this is permanent data loss, and backtest/performance-attribution reports run off this file will have a rolling-window horizon they don't document.

**Not fixed here** — the fix depends on whether a separate "full history" store exists. Needs product decision: (a) remove the truncation and let the file grow, (b) archive to `closed_picks.archive.jsonl` before trimming, or (c) confirm `universal_resolved_picks.json` already carries canonical history and add a comment pointing readers to it.

### 5. Operator precedence in `print_performance_report`

```python
crypto_strats = [(s, d) for s, d in sorted_strats
                 if "crypto" in s or "btc" in s or ...
                 or "breakout" in s and "forex" not in s]
```
`and` binds tighter than `or`, so the last clause is `("breakout" in s and "forex" not in s)` — the author almost certainly intended that, but parenthesizing would document intent and prevent a future maintainer from introducing a subtle bug.

### 6. Breadcrumb-label drift across penalties

Multiple penalty strings in `_apply_score_penalties` bake the score delta into the label (e.g. `f"killed_strategy:-40"`, `f"invalid_trade_geometry:-35"`). These are generated manually; any refactor of the numeric constant silently leaves the old string behind — exactly the bug we fix in Finding 1. Long-term, the penalty helper should take `(label, delta)` and format the string automatically. Out of scope for this PR.

---

## Files changed by this PR

- `audit_trail/quality_gates.py`
  - Fix Finding 1: breadcrumb label `-20` → `-60` for `blocked_asset_class` penalty.
  - Fix Finding 2: collapse the duplicate `SMART_PICKS_MIN_ML_SCORE` assignment and clarify intent in the comment.
- `alpha_engine/forward_validator.py`
  - Fix Finding 3: rename `ALPHA_LONG_WR_*` / `_long_wins` / `_long_wr` to `ALPHA_SYSTEM_WR_*` / `_sys_wins` / `_sys_wr`; update log line to accurately describe what's measured; add TODO pointer.
- `updates/2026-04-19-code-review-2weeks-findings.md` (this file).

## Verification

- Python syntax compile check on both modified files (pre- and post-change).
- `code-reviewer` subagent review of the diff.
- No behavioral change in the hot path for Findings 1 and 2 (Finding 1 branch is currently inert; Finding 2 preserves `0.0`). Finding 3 preserves the threshold and counting logic — only identifiers + log text change.

## Not run

- Full production pipeline (per `AGENTS.md`: do not run `smart_picks_engine.py` or `check_active_picks.py` automatically).
- Unit tests (none found targeting these specific branches in the areas changed).

## Next steps (recommended, not done)

1. Add a unit test covering the `blocked_asset_class` penalty path — would have caught Finding 1.
2. Introduce a `_penalize(score, label, delta)` helper that owns the breadcrumb formatting.
3. Extend `strategy_performance.json` (or add a sibling file) with per-direction stats, then upgrade the direction gate to be honest about LONG vs system WR.
4. Decide on `closed_picks.json` retention policy and document it at the top of the file.
