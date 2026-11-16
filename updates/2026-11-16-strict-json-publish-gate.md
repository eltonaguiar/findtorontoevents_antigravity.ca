# Strict-JSON publish gate for /audit sidecars (+ what the 2026-11-16 audit summary got right)

**Date:** 2026-11-16 ~07:10Z · **Verified against:** live `findtorontoevents.ca/audit`,
`main` @ `59a708c5dba`, and `main`'s committed sidecars.

The condensed audit summary listed six priority fixes. Three were checked against
ground truth first; two turned out to be **deploy/queue artifacts, not code bugs**, and
one was real and is fixed here.

## 1. Claim-by-claim verification

| Claim | Verdict | Evidence |
|---|---|---|
| Truth layer still says "Ghost rows: 0 (was 22,947)" while `db_health.json` says 22,947 | **Live page: true. `main`: already fixed.** | `audit_dashboard/template.html:857` now reads "Ghost rows: quarantined from the canonical view on 2026-05-31 (raw-table count is live in the DB Health tile above…)"; line 911 says "…and **22,947 ghost rows remain quarantined out of the canonical view**". Live HTML still serves the old sentence because the page has not been redeployed. |
| `forward_clock.js` / `excess_column.js` 404 → "deploy gaps" | **404s are real; no code gap.** | Both files exist on `main` (`audit_dashboard/*.js`), are listed in `tools/deploy_audit_files.py` `audit_js` group (lines 91–92), and in all three FTP site blocks of `audit-dashboard.yml` (lines ~1197/1334/1440). Live returns 404 only because no deploy has completed since they were restored. |
| `money_ready_verdict.json` has `NaN`, `strategy_ic_analysis.json` has `Infinity` → panels dead | **True on live, fixed in the repo, and now gated at publish.** | Live: `"dsr_score": NaN` (2 occurrences) and `"pf": Infinity` (1). `tools/money_ready_snapshot.py` already writes via `_json_safe()` + `allow_nan=False`; `deploy_audit_files.py` sanitizes what *it* uploads — but the hourly FTP deploy globs `audit_dashboard/data/*.json` directly and never used either. Still-broken committed sidecars: `hyro_ml_pick_rankings.json` (NaN), `summary_tournament_data.json` (Infinity), `hourly_asset_class_24h_report.json` (leading UTF-8 BOM — breaks `JSON.parse` the same way). |
| Deploy pipeline healthy | **No — the dispatched run was wedged.** | `audit-dashboard` #43809108656 (workflow_dispatch, 05:16Z) sat `in_progress` with job `generate-and-deploy` at `startedAt: null` for ~55 min; no runner ever picked it up. Cancelled. |
| PM signals gitignored / never reach active book | **Consistent with earlier findings** | `alpha_engine/data/{polymarket,kalshi}_signals.json` absent locally and from the published payload; producers run best-effort. Left as an owner decision (see §4). |
| Supply / smart_score / emitters / frontend | **Not touched here** | Out of scope for a data-integrity pass; see §4. |

## 2. What changed

**New `tools/sanitize_audit_json.py`** — publish-boundary strict-JSON enforcement:

- already-strict files are **never rewritten** (byte-identical, no diff churn);
- non-finite floats become `null` (absent measurement, never a fake `0`);
- a leading UTF-8 BOM is stripped;
- unparseable files are left untouched and reported with exit 1 (fabricating a
  replacement would be worse than a visibly empty panel);
- `--check` is read-only and exits 1 if anything is non-strict.

**`.github/workflows/audit-dashboard.yml`** — new step *Enforce strict JSON on audit data
sidecars*, immediately before *Deploy to all 3 FTP sites in parallel*: rewrite pass
(`--report`) then assert pass (`--check`). This is the path that bypassed sanitizing;
`deploy_audit_files.py` was never the problem.

**Three sidecars repaired in place:** `hyro_ml_pick_rankings.json`,
`summary_tournament_data.json`, `hourly_asset_class_24h_report.json`.

## 3. Verification actually run

| Check | Result |
|---|---|
| `python3 tools/sanitize_audit_json.py --report` | 338 files — 335 clean, **3 rewritten**, 0 broken |
| `python3 tools/sanitize_audit_json.py --check` | 338 clean, **0 non-strict**, exit 0 |
| Strict re-parse of the 3 repaired files with `parse_constant` raising | OK |
| `pytest tests/test_sanitize_audit_json.py tests/test_dashboard_payload_health_optional.py` | **8 passed** (4 + 4) |
| YAML load of `audit-dashboard.yml`, step present | 51 steps, gate present |
| First run of the tool | caught an over-broad rewrite (325 files reformatted); reverted with `git checkout -- audit_dashboard/data/` and fixed the tool to be a no-op on strict files — the 3-file result above is the corrected behaviour |

## 4. Left as owner decisions (not silently "fixed")

1. **PM feed persistence** — decide whether `kalshi_signals.json` / `polymarket_signals.json`
   should be committed artifacts (durable, deploys) or ephemeral. Until then they are
   registered-as-optional in the Feed Health gate, not required.
2. **Supply** — `smart_score` / `trust_tier` must be stamped at issue time by every emitter;
   that is a producer change across ~20 emitters, not a dashboard fix.
3. **Emitter mute/kill list** (FOREX, ETF orphans, silent 60–88h systems) — needs a named
   owner per emitter.
4. **Ghost rows** — 22,947 constant-PnL rows remain, by policy quarantined not deleted
   (2026-11-14 MASTER_AUDIT). Cleaning them is a data mutation and needs explicit sign-off.
5. ~~Live verification of this deploy~~ — **done, see §5.**

## 5. Post-deploy live verification (07:10Z) — PASSED

The replacement run `audit-dashboard` **#43815224263** (`workflow_dispatch` on `main`, created
06:12:51Z) picked the work up and deployed it. Re-checked against
`https://findtorontoevents.ca/audit/` after the deploy landed:

| Check | Before | After |
|---|---|---|
| `grep -c "Ghost rows: 0"` on `/audit/` | 1 | **0** |
| `grep -c "22,947 ghost rows remain"` | 0 | **1** |
| `grep -c "quarantined from the canonical view"` | 0 | **1** |
| `GET /audit/forward_clock.js` | 404 | **200** |
| `GET /audit/excess_column.js` | 404 | **200** |
| `data/money_ready_verdict.json` parsed with `parse_constant` raising | `NaN` -> parse error | **STRICT OK** (46,399 B) |
| `data/strategy_ic_analysis.json`, same parser | `Infinity` -> parse error | **STRICT OK** (42,157 B) |

Two things worth remembering for the next deploy audit:

- **`startedAt: null` is not proof of a wedged job.** The *successful* run `#43797722088` also
  reports `startedAt: null` on its completed `generate-and-deploy` job, so that field alone is
  meaningless here. The reliable wedge signal was the combination *state `in_progress` + zero
  completed steps + no `updatedAt` movement*: run #43809108656 held 54 steps at 0 completed and
  never moved from 05:16 to 06:11.
- **Cancel acknowledgement is slow on a wedged run.** `gh run cancel`, the API
  `POST .../force-cancel` and a second `gh run cancel` all returned success while the run stayed
  `in_progress`; it flipped to `cancelled` roughly 7.5 minutes after the last attempt, which
  unblocked the single-group `concurrency:` queue and let the replacement start.

