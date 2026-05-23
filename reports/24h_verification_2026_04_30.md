# 24h Post-Merge Verification — 2026-04-30

**Date:** 2026-04-30  
**Scope:** PRs merged 2026-04-29: #492, #494, #497, #498, #499, #500, #501, #502, #503, #504, #505, #506, #508, #509, #510  
**Verifier:** Claude Sonnet 4.6 (read-only session)  
**Budget:** ~15 min wall-clock

---

## Task A — Opt-in Env-Flag Flip Status

Checked via `grep -rn '<FLAG>' .github/workflows/` — **zero matches** for all flags in every workflow file (312 total in `.github/workflows/`).

| Flag | PR | Default | GHA Flipped ON? | Status |
|---|---|---|---|---|
| `WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED` | #505 | OFF (`"0"`) | ❌ No | Default-off; no wf picks up failing null verdicts yet |
| `MAX_CONCURRENT_PER_SYMBOL` | #506 | 0 (uncapped) | ❌ No | Default-off; concurrent-symbol cap not active |
| `EQUITY_TRUST_TIER_EXEMPT_ENABLED` | #508 | OFF (`"0"`) | ❌ No | Default-off; equity trust exemption not live |
| `RAPID_FIRE_MACD_KILL_DISABLED` | #509 | UNSET = kill active | ❌ No | Kill IS active (unset = block on) — flag not needed unless rollback |
| `EARNINGS_FETCHER_ENABLED` | #499 | OFF (`"0"`) | ❌ No | Default-off; fetcher never runs in GHA |
| `ASSET_CLASS_MAP_MEME_TO_CRYPTO` | #501 | **ON (`"1"`)** ⚠️ | N/A | **ANOMALY: default is ON, not opt-in.** `audit_trail/dashboard_generator.py:3189` uses `os.environ.get("ASSET_CLASS_MAP_MEME_TO_CRYPTO", "1") == "1"`. Meme→CRYPTO mapping is active in every run without anyone setting the flag. No operator action needed to enable it. |
| `CPCV_GATE_ENABLED` | #507 (draft) | N/A | ❌ No | Not found in any production `.py` file. PR still draft; gate not implemented. |

**Summary:** No opt-in flag was explicitly flipped on by the operator. All remain at their code defaults. One anomaly: `ASSET_CLASS_MAP_MEME_TO_CRYPTO` is effectively ON-by-default, not opt-in as advertised in PR #501.

---

## Task B — Post-Merge Regression Scan

**Note:** `gh` CLI is not available in this environment. Regression assessment is based on (a) the most recent GHA audit report (`reports/gha_audit_workflows_2026_04_29.md`) and (b) `trading_bot.log` (last updated 2026-04-30 16:50 UTC).

### Known pre-existing CI failure (not caused by the 04-29 PR batch)

| Workflow | Status | Notes |
|---|---|---|
| `ci-tests.yml` (CI Tests) | 🔴 FAILING | SyntaxError in `tests/test_quan_engine_concurrency_cap.py:41` — f-string nesting issue (Python 3.11/3.12 matrix). **Pre-existing**, confirmed in `reports/gha_audit_workflows_2026_04_29.md` as ">207 failures in last-500 lookback." Root cause is unrelated to the April 29 PRs. |
| `audit-dashboard.yml` | 🟡 SLOW | Avg ~42 min vs 25-min target. Pre-existing. |
| `dynamic-alpha-engine.yml` | 🟡 SLOW | ~37 min avg; 49 failures in last-500. Pre-existing. |

**No new workflow-level regressions attributable to PRs #492–#510 were detected.** The `trading_bot.log` shows CoinGecko API merge errors (`datetime64[ns]` vs `int64` for 'timestamp' key) but these appear to be pre-existing data-fetch issues with no crash.

---

## Task C — Surgically-Killed Strategy Verification

**Kill:** `("rapid_fire", "macd_rsi_confluence")` — PR #509, merged 2026-04-29 16:23Z.

### Quantitative check

```
Total rapid_fire×macd_rsi_confluence in dashboard recent_closed: 145
Post-cutoff closures (closed_at > 2026-04-29T16:23Z): 6
  - 3 pre-existing picks (generated BEFORE kill, closed after): EXPECTED
  - 2 picks generated AFTER kill: BREACH ⚠️
  - 1 boundary pick (BNBUSDT, generated pre-kill, closed post-kill): EXPECTED
```

### Post-kill breach detail

| Pick | Generated (`opened_at`) | Closed | Status | Trust Tier |
|---|---|---|---|---|
| SOLVUSDT LONG | 2026-04-30 03:27:44 UTC | 2026-04-30 09:03:42 UTC | LOST (SL_HIT) | BANNED |
| ORCAUSDT LONG | 2026-04-30 03:27:44 UTC | 2026-04-30 11:51:28 UTC | LOST (SL_HIT) | BANNED |

Both generated ~11h after the kill merged. Confirmed in `rapid_fire_data/closed_picks.json` (ORCAUSDT `opened_at: 2026-04-30 03:27:44`).

### Root cause: blocklist gap in isolated_signal_integrator.py

The kill in `alpha_engine/strategy_blocklist.py` is correctly implemented and the `_RETIRED_SYSTEM_STRATEGY_PAIRS` frozenset includes `("rapid_fire", "macd_rsi_confluence")`. However:

1. The rapid_fire runner generates picks independently and writes them directly to `rapid_fire_data/active_picks.json`, `rapid_fire_data/closed_picks.json`, and `rapid_fire_data/now_picks.json` **without consulting `is_blocked_pick()`**.
2. `alpha_engine/isolated_signal_integrator.py` reads from these files (line 78: `("rapid_fire_data/active_picks.json", None, "rapid_fire")`) and **does not call `is_blocked_pick()`** — confirmed: `grep 'is_blocked_pick' alpha_engine/isolated_signal_integrator.py` returns 0 matches.
3. `alpha_engine/feed_hygiene.py` calls `is_blocked_pick()` at line 160, but only if the audit pipeline routes picks through `feed_hygiene` before `dashboard_generator` ingests from `rapid_fire_data/`.

The blocklist kill works only when picks pass through `feed_hygiene.py` → `is_blocked_pick()`. Picks that the rapid_fire runner writes directly to its own JSON files and which `isolated_signal_integrator.py` ingests bypass this gate.

**Net damage from breach:** 2 picks, both BANNED-tier, both SL_HIT, both LOST. Total incremental PnL drag: approximately −4% combined (−2% each). Minor in absolute terms, but confirms a structural gap.

### Active-picks state (NOW)

```
rapid_fire_data/active_picks.json: 0 macd_rsi_confluence picks active
dashboard_data.json active picks: 0 macd_rsi_confluence rapid_fire picks
```

No new breach in progress at time of verification.

---

## Unexpected Findings

### Finding 1: `ASSET_CLASS_MAP_MEME_TO_CRYPTO` is ON by default (not opt-in)

PR #501 was presented as an opt-in env flag. The implementation at `audit_trail/dashboard_generator.py:3189` uses `default="1"`, making meme→CRYPTO mapping always active unless the operator explicitly sets the var to `"0"`. This is opposite of opt-in behavior. With 174 memecoin picks affected (per the code comment), this affects CRYPTO tile volume counts in every dashboard run. No operator action is currently needed to enable it — it was active from the moment PR #501 merged.

### Finding 2: `rapid_fire_data/now_picks.json` contains 199 stale macd_rsi_confluence historical picks

The file contains 500 picks total, 199 tagged `strategy: macd_rsi_confluence`. These appear to be a historical snapshot (earliest `scan_time` observed: 2026-04-16). None were generated post-kill — the newest timestamp predates the kill. However, if any downstream pipeline blindly re-ingests `now_picks.json` without a date filter and without `is_blocked_pick()`, these could re-appear in dashboard metrics. Recommend auditing which callers consume `now_picks.json`.

### Finding 3: `ci-tests.yml` syntax failure blocks PR green checks

The f-string nesting error in `tests/test_quan_engine_concurrency_cap.py:41` has caused 207+ CI failures. Until this is fixed, any PR that touches the test matrix will appear red on CI, making automated green-checks unreliable as a merge gate.

---

## Recommended Next-Action Items

| Priority | Action | Owner | Why |
|---|---|---|---|
| P0 | **Patch `isolated_signal_integrator.py`** to call `is_blocked_pick()` before registering any pick from `rapid_fire_data/`. One-liner filter at the merge point (lines ~78–96). | Next session | Kill breach confirmed; 2 post-kill BANNED picks slipped through this gap. |
| P1 | **Fix `ci-tests.yml` SyntaxError** in `tests/test_quan_engine_concurrency_cap.py:41` (f-string nesting). `rebase on main after #482+#495 fixture fixes` resolves similar issues per `reports/gha_audit_workflows_2026_04_29.md`. | Next session | 207+ accumulated CI failures; green-check gate is meaningless until resolved. |
| P1 | **Correct `ASSET_CLASS_MAP_MEME_TO_CRYPTO` default** from `"1"` to `"0"` in `dashboard_generator.py:3189` if the intent was opt-in, OR update the PR description / flag table to reflect that it is default-ON (back-compat behavior, set to "0" to disable). | Next session | Default contradicts the opt-in design contract stated in PR #501. |
| P2 | **Audit `now_picks.json` consumers** — ensure all paths that read `rapid_fire_data/now_picks.json` apply `is_blocked_pick()` filtering before writing to any accumulator. 199 stale macd_rsi_confluence picks present in the file. | Next session | Risk of re-surfacing killed picks in future aggregation runs. |
| P2 | **Enable `WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED`** in the appropriate walk-forward workflow (suggested: `audit-dashboard.yml`) once the operator is ready to harden null-verdict treatment. Currently default-off. | Operator decision | The flag was built for a reason; keeping it default-off indefinitely means the guard never fires. |
| P3 | **Resolve `dynamic-alpha-engine.yml` runtime** from ~37 min to under 25 min to prevent cascading cancellations with the next cron tick. | Background | Pre-existing, but compounding with audit-dashboard's ~42 min budget. |

---

## Summary

| Check | Result |
|---|---|
| Flags flipped ON by operator | None (all defaults held) |
| Anomalous default-ON flag | `ASSET_CLASS_MAP_MEME_TO_CRYPTO` (default `"1"`, not opt-in) |
| New regressions from 04-29 PRs | None detected |
| Pre-existing CI failures | `ci-tests.yml` (207+ failures, SyntaxError — pre-existing) |
| Kill held (no new active picks) | ✅ 0 active rapid_fire×macd_rsi_confluence |
| Kill breach (historical file gap) | ⚠️ 2 post-kill picks leaked via `isolated_signal_integrator.py` bypass |
| Net breach damage | −4% combined PnL, both BANNED-tier, both SL_HIT |
