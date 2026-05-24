# GITHUB ACTIONS HEALTH MONITOR — QWEN (continuation of OPENCODE)

**Investigator:** Claude Opus 4.7 (1M ctx)
**Window covered:** 2026-05-24 06:00 – 07:15 UTC (today's failures on `main`)
**Branch:** plan/institutional-readiness-2026-05-24 (fixes staged locally)

---

## Scope

Per user: "go through each failed github actions job without a next subsequent success run for the next hour, then investigate the root cause and fix, or document as a .MD."

Pulled the last 30 runs, filtered to `conclusion=failure` with `startedAt` on 2026-05-24, then for each failing workflow checked whether a later run of the same workflow had succeeded. Two workflows had **no subsequent success** as of 07:15 UTC.

---

## Failure #1 — CI Tests (latest run 26354702330, main @ 459e49cd)

**Status:** ❌ FAILED on both Python 3.11 and 3.12
**No subsequent success.**

### Root cause (FIXED)

`tests/test_purged_pnl_compounded_ew.py` had assertions written against the *pre-cap* compounding behavior of `alpha_engine.stats_cleaner._compound_pct_ew_chronological`.

Commit `644574f7 fix: audit dashboard compound return metrics capped at ±2%` tightened the per-trade cap from `None` (uncapped) → `max_abs_pct=2.0` to stop the 3.9-billion-percent returns produced when outlier trades (e.g. CADJPY +8559%) were included. That fix was correct and load-bearing, but the two tests in this file fed 10.0% inputs and still asserted the uncapped totals (10.0 and 21.0).

Concrete delta after the cap:
- `test_purged_compound_excludes_toxic_symbol`: BTC pnl=10.0 → capped to 2.0 → compound = 2.0 (was 10.0).
- `test_purged_compound_two_trades`: A=10, B=10 → both capped to 2.0 → `(1.02)² − 1 = 4.04%` (was 21.0).

### Fix applied

[tests/test_purged_pnl_compounded_ew.py](tests/test_purged_pnl_compounded_ew.py): reduced the pnl inputs from 10.0 → 2.0 (within the new ±2% cap) and updated the raw/compound expectations to 2.0 / 4.04. Preserves the test intent (raw sum vs geometric compound on the purged set, with TRXUSDT excluded as a toxic symbol) while staying inside the cap so the test demonstrates real compounding behavior rather than cap saturation.

Local verification: `pytest tests/test_purged_pnl_compounded_ew.py -v` → 2 passed.

---

## Failure #2 — Decile Separation Test (run 26354833305, main)

**Status:** ❌ FAILED
**No subsequent success.**

### Root cause (FIXED)

[alpha_engine/decile_separation_test.py:50-51](alpha_engine/decile_separation_test.py#L50-L51):

```python
"pnl_pct": float(p.get("pnl_pct", 0.0)),
"confidence": float(p.get("confidence", 0.0)),
```

Classic `dict.get` defaulting trap: the default value of `0.0` is only used when the key is **absent**. If the key is present and the value is explicitly `None` (which happens regularly in `closed_picks` for picks with no resolved confidence), `float(None)` raises `TypeError: float() argument must be a string or a real number, not 'NoneType'`. This blew up the whole report generator at module load — exit code 1.

### Fix applied

Switched to `p.get("pnl_pct") or 0.0` / `p.get("confidence") or 0.0`, which coerces both missing **and** `None` to `0.0`. Standard pattern used elsewhere in this repo (e.g. `_safe_float` in `tools/drift/build_backtest_forward_drift.py`).

---

## Failures NOT acted on (documented in OPENCODE log, infra-class)

Per the user instruction "fix, or document as a .MD" — these three remain documented in `___HELL_HEALTH_OPENCODE.MD` and require infrastructure access I do not have:

1. **MySQL Trading Picks Sync** — `Access denied for user 'ejaguiar1_stocks'@'52.150.28.32'`. Needs GitHub Secrets credential rotation and/or 50webs IP-allowlist update. Not a code bug.
2. **Claude's Test Portfolio Manager push** — git push exit 128, likely concurrent-commit race on large binary artifacts. Workflow refactoring (queuing / LFS) is the right fix; out of scope for a one-hour triage.
3. **Live Picks Tracker GitHub Pages deploy** — `peaceiris/actions-gh-pages@v3` rejecting `GITHUB_TOKEN`. Token-permissions / action-version bump.

---

## Files changed by this triage

- [tests/test_purged_pnl_compounded_ew.py](tests/test_purged_pnl_compounded_ew.py) — assertions aligned with the ±2% compound cap shipped in 644574f7.
- [alpha_engine/decile_separation_test.py](alpha_engine/decile_separation_test.py) — None-safe coercion of `pnl_pct` / `confidence` before `float()`.

No production / dashboard data files touched. No generators run locally (per CLAUDE.md).

---

## Recommended next steps (not done in this session)

- After these two fixes land on `main`, rerun the **CI Tests** and **Decile Separation Test** workflows once to confirm green.
- The three infra-class failures in OPENCODE log are still open; pick whichever has the highest blast radius (MySQL sync looks worst — picks aren't reaching prod DB) and run a dedicated secret-rotation session.
- The `SyntaxWarning: invalid escape sequence '\B'` in `tests/test_equity_price_failover_cache_path.py:53` is a benign warning today but will become an error in Python 3.14; cheap to fix while in the area.
