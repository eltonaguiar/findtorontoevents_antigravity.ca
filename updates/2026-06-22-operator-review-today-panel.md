# feat(audit): Operator Review today panel — manual candidates sidecar (ENAUSDT SHORT + ADAUSDT LONG)

**Date:** 2026-06-22
**Branch:** feat/operator-review-today-panel
**Spec lineage:** tools/crypto_rsi5070_forward_tracker.py (shadow-sidecar pattern, 2026-06)

## What

A dedicated /audit panel ("🌅 Operator Review — Manual Candidates") surfaces 2 hand-curated picks that the production sizing lane would otherwise filter out:

| Symbol | Direction | n (cohort) | WR% | PF (net) | Restriction basis |
|---|---|---|---|---|---|
| ENAUSDT | SHORT | 39 | 71.8 | **2.092** | M-036 N/A (SHORT unaffected); luxalgo_confluence SHORT cell passes cell-level gate |
| ADAUSDT | LONG | 1205 (class) | 32.61 | 0.79 | **M-036b BLOCKED** — CRYPTO sized LONG hard-rejected at audit_trail/quality_gates.py:7317-7349; panel bypass is visibility-only |

ADAUSDT LONG is the test case for the "operator-review sidecar" pattern — the panel deliberately bypasses the gate so a human eye sees what the kill-switch would otherwise filter out.

## Files

| Path | State | What it does |
|---|---|---|
| audit_dashboard/data/operator_review_today.json | NEW (~5.5KB) | Initial 2-pick hand-curated JSON. Fail-closed contract: dashboard_enhancements.js renders NOTHING if operator_review_only !== true, picks[] empty, or file missing. |
| audit_dashboard/data/operator_review_dismissed.json | NEW (566B) | Empty audit log of operator accept/reject decisions; appended from operator click events (TODO: build_dismissed_audit.py). |
| tools/build_operator_review_today.py | NEW (~14KB) | Read seed, enrich each pick via live-data lookups (luxalgo_short condition + per-(symbol,dir,strategy) intrabar index + class verdict), write JSON. Flags: --apply (writes), --stdout (print), --strict (refuse on empty). |
| tools/operator_review_seed.json | NEW (~3.2KB) | Hand-curated 2-pick seed (operator edits nightly before 07 UTC commit). |
| audit_dashboard/dashboard_enhancements.js | MODIFIED (~1178 lines; +90 LOC; 9 functions preserved) | ADDS `renderOperatorReviewToday()` async fn — fail-closed fetch from operator_review_today.json + amber-striped MANUAL CANDIDATES card panel. PRESERVES all 8 pre-existing functions (System Trends, Strategy Consensus, Time-Window Leaderboard, DB Health, Top-N Backtest, ML Gatekeeper A/B, EAGLE2, Commodity Tooltips). |
| .github/workflows/operator-review-today.yml | NEW (~8KB) | Daily cron `0 7 * * *` UTC + manual workflow_dispatch. Concurrency group `dashboard-publish` (shared with audit-dashboard). Validates schema before commit, retries push up to 5x. |
| tests/test_no_sizing_consumer.py | NEW (~190L) | Pre-merge contract: any *.py under tools/ + audit_trail/ + alpha_engine/ that reads operator_review_today.json MUST reference operator_review_only OR carry # allowed: operator-review consumer. Catches Q7c papercut. |
| updates/2026-06-22-operator-review-today-panel.md | NEW (this file) | Documentation per AGENTS.md "Document Every Fix" rule. |

## Why

The /audit dashboard surfaces only auto-emission: `picks_now.json`, `active_picks.json`, `dashboard_data.json::picks.active`. The production lane blocks ADAUSDT LONG (M-036b CRYPTO_SIZED_LONG_BLOCK=1 hard-reject on direction=LONG at quality_gates.py:7317-7349) and any other candidate the kill-switch / gates consider net-losers. Without this panel, an operator who wants to evaluate a M-036b-blocked candidate has no surface to do so — the candidate simply never appears.

This panel is a deliberately sidecarred read-only lane that DELIBERATELY bypasses the kill-switches for VISIBILITY ONLY. The visual differentiation (amber-striped border, "MANUAL CANDIDATES — NOT auto-emitted" pill, "NOT auto-emitted / NOT sized" on every header line) is the ONLY thing keeping an operator from misreading this as a sizing signal. There is no auto-trading, no auto-sizing, no auto-resolve; the operator must click / accept / reject explicitly.

ENAUSDT SHORT sits on the `luxalgo_short` cell of `entry_conditions_forward.json::conditions` — n=39, wr=71.8%, net_pf=2.092, verdict_note "accruing forward n; below the n>=100 gate". This is real evidence in our honest intrabar cohort; the panel surfaces it as a candidate, not a sizing signal, because n<100 means it's still pre-promotion.

## How it works

1. Operator edits `tools/operator_review_seed.json` to declare today's picks (2-5 entries; each needs `symbol`, `asset_class`, `direction`, `restriction`).
2. Daily cron at 07:00 UTC runs `tools/build_operator_review_today.py --apply` which:
   - Reads the seed
   - For each pick: looks up `entry_conditions_forward.json::conditions[key]` for live n/WR/PF; looks up `intrabar_sym_dir_fwd.json::by_key SYMBOL|DIRECTION|STRATEGY` for per-(symbol,dir,strategy) sub-cohort; looks up `money_ready_verdict.json::classes[C]` for class verdict
   - Writes the enriched JSON to `audit_dashboard/data/operator_review_today.json`
3. `/audit` page loads `audit_dashboard/dashboard_enhancements.js` which calls `renderOperatorReviewToday()` from `initEnhancements()`. That function:
   - Fetches `data/operator_review_today.json`
   - Validates `operator_review_only === true` (else renders nothing)
   - Renders the amber-striped MANUAL CANDIDATES panel ABOVE the today-tab content with per-pick cards showing n / WR / PF / restriction / TP/SL / source strategies / operator_decision_required (in a `<details>` block)
4. Operator makes accept/reject decisions, appending to `operator_review_dismissed.json`.
5. Hourly `audit-dashboard.yml` cron FTP-deploys everything to the live site (operator_review_today.json is in the data/ globs at audit-dashboard.yml:~line 681 git-add).

## Verification

**Pre-ship validation (all PASS):**
- `python3 -m py_compile tools/build_operator_review_today.py` → exit 0
- `tools/operator_review_seed.json` parses; 2 picks present
- `audit_dashboard/data/operator_review_today.json` parses; `operator_review_only=true`, 2 picks, pick[0].live_n=39, pick[0].live_wr_pct=71.8
- `audit_dashboard/data/operator_review_dismissed.json` parses; schema field present
- YAML 11/11 safety checks pass (concurrency group dashboard-publish, cancel-in-progress:false, cron `0 7 * * *`, retry loop cap 5, only operator_review_today.json git-added, env block has zero DB_* keys)
- `tools/build_operator_review_today.py --stdout` dry-run enriches correctly with live n=39 wr=71.8% net_pf=2.092 + per-symbol-per-dir cohort trace
- `dashboard_enhancements.js`: 1178 lines, 9 functions (1 new + 8 preserved), `renderOperatorReviewToday()` exported on window, called from `initEnhancements()` in try-list, `console.log` line includes "Operator Review Today"

**Post-ship validation:**
- `gh workflow run operator-review-today.yml --ref main` manual dispatch registers and runs to terminal status

## Risks

1. **ADAUSDT LONG visibility-misread-risk**: the panel surfaces a CRYPTO LONG candidate the M-036b kill-switch explicitly rejects. The amber-striped MANUAL CANDIDATES banner + "NOT auto-emitted / NOT sized" copy on every header line is the mitigation. There is NO code path that converts this into a trade — `operator_review_only: true` is the fail-closed flag and the JS reads it on every render.
2. **dashboard_enhancements.js is the persistent-survives-regen JS**: any future modification MUST preserve all 9 functions (grep check passed at 9/9 right now). If you delete a function, the corresponding /audit panel breaks.
3. **Concurrency group shared with audit-dashboard**: a 35-min audit-dashboard run at 06:10 may queue our 07:00 daily run if it overruns past 07:00. Acceptable — both jobs are idempotent and the JSON rewrites cleanly on the next run. cancel-in-progress is intentionally `false` (we don't want mid-write truncation).

## Upstream

- **Canonical regenerator:** `tools/build_operator_review_today.py` daily.
- **Manual override:** Operator can edit `audit_dashboard/data/operator_review_today.json` directly for same-day edits; next daily cron overwrites.
- **Audit trail:** Operator accept/reject decisions go to `audit_dashboard/data/operator_review_dismissed.json` (TODO: `tools/build_dismissed_audit.py` to write to that file on operator click events).
- **Spec lineage:** Mirrors the `crypto_rsi5070_us_forward_status.json` shadow-sidecar pattern (audit_dashboard/data/crypto_rsi5070_us_forward_status.json) — that one tracks a single forward-tracking lead; this one tracks the operator's daily manual candidates.

## Contract enforcement

Sidecar isolation discipline is enforced as a fail-closed gate by `tests/test_no_sizing_consumer.py`, wired into this cron as a step AFTER the JSON validate + BEFORE the commit:

| Layer | Behavior |
|---|---|
| **Payload contract** | `audit_dashboard/data/operator_review_today.json` must carry `_schema_note` (string) AND `operator_review_only` (strict `True` boolean, not just truthy) — these are the human-readable + machine-readable gate that fail-closed consumers read |
| **Unguarded-reader scan** | Any `*.py` under `tools/` + `audit_trail/` + `alpha_engine/` that opens the sidecar must EITHER reference the `operator_review_only` gate-flag string OR carry a `# allowed: operator-review consumer` line marker. Exempt: the writer (`tools/build_operator_review_today.py`) + the test file itself |
| **Cron-mode fail-closed** | When the workflow step sets `OPERATOR_REVIEW_CRON_MODE: "1"` at its env block (scoped to that one step only — not workflow-env, not job-env), a missing sidecar AFTER the build step ran becomes a hard `pytest.fail()` (not a graceful `pytest.skip()`). The step runs `python3 -m pytest tests/test_no_sizing_consumer.py -v --tb=short` AFTER `pip install pytest` |

Pre-merge gates this catches: dummy consumer scripts that silently re-ingest the sidecar as a sizing surface; build scripts that silently drop the payload (`--apply` writes empty seed → empty panel); schema drift that strips the `_schema_note` / `operator_review_only` keys.

This addresses two papercuts from the same code-review:

1. **Q7c** — `_schema_note` was a docstring-only contract previously; now it's a pre-merge test.
2. **(implicit)** — without the cron-mode env var, the test's `pytest.skip("sidecar missing")` would mask a regression in the cron flow (build ran but sidecar absent). The env var converts that skip into a fail pre-commit.
