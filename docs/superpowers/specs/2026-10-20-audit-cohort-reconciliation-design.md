# Design: /audit Cohort Reconciliation Instrument (measurement only)

- **Date:** 2026-10-20
- **Status:** Approved with 4 changes (see §10)
- **Owner:** Zoo (Inception Labs coding agent)

## 1. Purpose

The weekly picks/snipe review (report 2026-10-20) concluded **no deployable edge exists
yet** and identified several places where the published `/audit` surfaces disagree or
hide artefacts:

- **3A** — batch-artefact closes (e.g., MomentumEMA: 73 records sharing one `closed_at`,
  June issue timestamps, source `signal_validation`) inflate a cohort's PF.
- **3B** — blocklist-bypass issuance (a blocked/retired/paper-only strategy still appears
  as an issued closed pick).
- **3D** — published surfaces disagree because they are not the same cohort (e.g., 14d
  EQUITY `n=2,780` PF 1.470 vs `n=69` PF 1.012; `pick_summary_stats_14d/48h.json` are
  stale since 2026-06-21 while `dashboard_data.json` is fresh).

This instrument is a **pure, unit-tested measurement/reconciliation tool** that recomputes
rolling PF/WR from the published `/audit` JSONs, flags the three phenomena above, and writes
a new `audit_dashboard/data/cohort_reconciliation.json`. It is **measurement only**: no new
trade trigger, no live pipeline wiring, no front-end changes.

### Honesty constraint (user-confirmed)

Approach A reads **published files only**. Therefore the check named "surface vs raw
database" is actually **published-file-vs-published-file**. The output must name this
honestly (e.g., `comparison_scope: "published-file-vs-published-file"`). A read-only DB
snapshot cross-check is explicitly out of scope and logged as a future step — we do **not**
claim to verify against the live database.

## 2. Scope / out of scope

| In scope | Out of scope |
|----------|--------------|
| Read `audit_dashboard/data/dashboard_data.json` (published) | Real database / DB reads |
| Read `audit_dashboard/data/pick_summary_stats_14d.json`, `_48h.json` | `template.html` / dashboard integration |
| Read `alpha_engine/strategy_blocklist.py` (for bypass detection) | Any new trade trigger |
| Recompute rolling PF/WR from `picks.recent_closed` over matching windows (14d, 48h) | git history rewrites / pushes |
| Flag: blocklist-bypass issuance (3B, issue-time aware) | Scheduled job (follow-up) |
| Flag: batch-artefact closes (3A) with with/without PF/WR | Read-only DB snapshot (follow-up) |
| Flag: published-file disagreement (3D, with coverage check) | |
| Emit `audit_dashboard/data/cohort_reconciliation.json` (schema-versioned) | |

## 3. Inputs (published files only)

| Input | Path | Used for |
|-------|------|----------|
| Dashboard data | `audit_dashboard/data/dashboard_data.json` | `picks.recent_closed` cohort; blocklist bypass checks; batch-close detection |
| 14-day summary stats | `audit_dashboard/data/pick_summary_stats_14d.json` | published-vs-published disagreement (3D) over the 14d window |
| 48-hour summary stats | `audit_dashboard/data/pick_summary_stats_48h.json` | published-vs-published disagreement (3D) over the 48h window |
| Blocklist | `alpha_engine/strategy_blocklist.py` (import `is_blocked_strategy`, `block_reason`, `_PAPER_ONLY_STRATEGIES`, `_RETIRED_STRATEGIES`) | blocklist-bypass detection (3B) |

All paths are passed as arguments (defaults to the canonical paths above), so tests can feed
hand-made fixtures.

## 4. Output schema: `cohort_reconciliation.json`

Schema-versioned (`"schema_version": "1.1.0"`). All numbers are counts/ratios with `n`
always reported. **The output contains no `READY` / `ENTER` wording** (explicit user
requirement).

```jsonc
{
  "schema_version": "1.1.0",
  "generated_utc": "<ISO8601>",
  "inputs": {
    "dashboard_data": {"path": "...", "present": true, "generated_utc": "...", "records": 3500},
    "summary_stats_14d": {"path": "...", "present": true, "generated_utc": "...", "stale_hours": null},
    "summary_stats_48h": {"path": "...", "present": true, "generated_utc": "...", "stale_hours": null}
  },
  "comparison_scope": "published-file-vs-published-file",
  "rolling_metrics_by_window": {
    "window_hours": 336,
    "window_label": "14d",
    "coverage": {
      "oldest_closed_at": "2026-10-06T00:00:00Z",
      "window_start_utc": "2026-10-06T01:28:00Z",
      "covers_window": true,
      "status": "complete"
    },
    "by_class": {
      "CRYPTO": {"n": 1200, "wins": 700, "losses": 500, "win_rate": 0.5833, "win_rate_hidden": false, "pf": 1.204, "pf_note": null},
      "EQ": {"n": 17, "wins": 9, "losses": 8, "win_rate": null, "win_rate_hidden": true, "pf": 1.100, "pf_note": "n<20; WR hidden"}
    },
    "by_strategy": {
      "momentum_ema": {
        "n": 73, "wins": 40, "losses": 33, "win_rate": 0.548, "pf": 1.133,
        "batch_artefact_closes": 73, "batch_close_ts": "2026-10-19T22:43:12Z",
        "pf_excl_batch": 1.204, "win_rate_excl_batch": 0.553
      }
    }
  },
  "blocklist_bypass": {
    "flagged": true,
    "count": 2,
    "issues": [
      {"pick_id": "abc", "symbol": "EURUSD", "direction": "SHORT", "strategy": "forex_rsi2_mean_reversion", "asset_class": "FOREX", "reason": "fx-kill", "issue_time_known": false, "bypass": "blocked_now_issue_time_unknown"},
      {"pick_id": "def", "symbol": "X", "strategy": "inverse_quan_engine_scalp", "reason": "retired", "issue_time_known": false, "bypass": "blocked_now_issue_time_unknown"}
    ]
  },
  "batch_artefact": {
    "flagged": true,
    "clusters": [
      {"closed_at": "2026-10-19T22:43:12Z", "count": 73, "distinct_strategies": 1, "strategy": "momentum_ema", "source_system": "signal_validation"}
    ]
  },
  "published_disagreement": {
    "flagged": true,
    "checks": [
      {"cohort": "14d/EQUITY", "window_hours": 336, "coverage_status": "complete", "dashboard_n": 2780, "dashboard_pf": 1.470, "summary_n": 69, "summary_pf": 1.012, "disagree": true},
      {"file": "pick_summary_stats_14d.json", "stale_hours": 5800, "source": "stale"}
    ]
  },
  "notes": [
    "comparison_scope=published-file-vs-published-file; no live DB read performed"
  ]
}
```

## 5. Architecture / components

Single new module + tests at repo root:

| File | Responsibility |
|------|----------------|
| `tools/cohort_reconciliation.py` | Pure functions (below); `main()` arg-parses input paths + output path and writes the JSON. |
| `tests/test_cohort_reconciliation.py` | Unit tests with hand-made fixtures for each flag (3A/3B/3D), metric math, WR-hiding below n=20, `comparison_scope` honesty, and no-READY/ENTER wording assertion. |

### Pure functions

- `load_json(path) -> dict` — read + parse; raise on missing/malformed.
- `recompute_rolling_metrics(records, window_hours) -> dict` — group by class and by
  strategy over the **given window** (336h for 14d, 48h for the 48h comparison). Compute
  `n`, `wins`, `losses`, `win_rate`, `pf = sum(pos pnl_pct)/abs(sum(neg pnl_pct))` (same
  formula as the report). **Hide `win_rate` (set `null` + `win_rate_hidden: true`) when
  `n < 20`** and always emit `n`.
  - **Coverage check (change #2):** compute `oldest_closed_at` among the cohort's records;
    compare to `window_start_utc = generated_at - window_hours`. If `oldest_closed_at` is
    newer than `window_start_utc`, set `coverage.status = "incomplete_coverage"` and the
    disagreement check for that window is **skipped** (status `incomplete_coverage`), not
    flagged as a disagreement.
- `flag_blocklist_bypass(records, block_dates=None) -> dict` — for each closed pick, call
  `strategy_blocklist.is_blocked_strategy(strategy, asset_class)`. **Issue-time aware
  (change #3):** a pick counts as a bypass only if the strategy was blocked at the pick's
  issue time. Because the current blocklist has **no block dates**, every flagged pick is
  labeled `"bypass": "blocked_now_issue_time_unknown"` (with `issue_time_known: false`).
  A future date-aware blocklist can pass `block_dates` and produce `"bypass": "blocked_at_issue_time"`.
- `flag_batch_artefact(records, min_cluster=5) -> dict` — detect clusters of records sharing
  an identical `closed_at` (optionally also same strategy/source). Flag clusters ≥
  `min_cluster`. Return `{flagged, clusters}`.
- **Batch-excluded metrics (change #4):** for each flagged cluster, recompute the strategy's
  PF/WR with the cluster's trades **removed**, emitting `pf_excl_batch` and
  `win_rate_excl_batch` alongside the base numbers so the artefact's impact is visible.
- `flag_published_disagreement(dashboard_metrics_by_window, summary_stats) -> dict` —
  compare dashboard recomputed cohort metrics vs published summary stats **for the same
  window** (14d vs 14d, 48h vs 48h). Because the `summary_stats` window label is
  self-describing, match by `window_label`. Flag discrepancies beyond a tolerance (PF delta
  > 0.1 or `n` delta > 20% or one side missing/stale). **Skip (status
  `incomplete_coverage`) when coverage is incomplete** instead of flagging.
- `assemble_output(...) -> dict` — combine all sections + `comparison_scope` + schema version
  + `generated_utc`. **Assert no "READY"/"ENTER" substring** in the serialized output (tested).

## 6. Data flow

```
dashboard_data.json ─┬─> recompute_rolling_metrics(14d) ─> rolling_metrics_by_window[14d]
                    │  > recompute_rolling_metrics(48h) ─> rolling_metrics_by_window[48h]
                    ├─> flag_blocklist_bypass ────────────> blocklist_bypass
                    └─> flag_batch_artefact (+ excl-batch) > batch_artefact
pick_summary_stats_*.json ──> flag_published_disagreement (per matching window) ─> published_disagreement
                                      │
                                      ▼
                              assemble_output ──> cohort_reconciliation.json
```

## 7. Error handling

- Missing input file: output `"present": false` for that input, skip dependent checks, and
  record it in `notes`; do **not** crash the whole run. A `--strict` flag can promote missing
  required inputs to an error.
- Malformed JSON: raise a clear error naming the file.
- Records missing required fields (`pnl_pct`, `strategy`, `asset_class`, `closed_at`):
  skipped and counted in a `skipped_records` counter in `notes`.

## 8. Testing

Each flag must have a unit test with a hand-made fixture (explicit user requirement):

1. **Blocklist bypass (issue-time)** — fixture with a closed pick whose strategy is in
   `_RETIRED_STRATEGIES` / `_PAPER_ONLY_STRATEGIES` / FX-killed; assert flagged with the
   `blocked_now_issue_time_unknown` label (since no block dates exist). A second fixture
   supplies `block_dates` to assert the issue-time path.
2. **Batch-artefact closes** — fixture with many records sharing one `closed_at`; assert
   cluster detected, and that `pf`/`win_rate` are reported both with and without the cluster
   (`pf_excl_batch`, `win_rate_excl_batch`).
3. **Published-vs-published disagreement (window-matched + coverage)** — fixture where the
   14d dashboard cohort vs 14d summary disagree → flagged; a **coverage fixture** where
   `oldest_closed_at` is newer than the window start → status `incomplete_coverage`, no
   disagreement flag; also assert the honest `comparison_scope` string.
4. **Rolling metric math (per window)** — known small cohort at 336h and 48h → exact PF/WR;
   assert `win_rate` hidden when `n < 20` and shown when `n >= 20`; assert `n` always present.
5. **Output hygiene** — assert serialized output contains neither `READY` nor `ENTER`.
6. **Missing-input resilience** — one input absent → `present: false`, no crash.

## 9. Verification

- `python3 -m py_compile tools/cohort_reconciliation.py`
- `python3 -m pytest tests/test_cohort_reconciliation.py -q` (all pass)
- Run once against the real published files; confirm the output JSON has the documented
  schema shape and the honesty note. Commit the tool + tests (not necessarily the output).

## 10. Approval changes (user feedback)

Spec approved with 4 changes, all incorporated above:

1. **Mismatched time windows** — recompute over 14d and 48h windows so each comparison uses
   the same window as the published file it is checked against (§5, §6).
2. **3,500-record cap / coverage** — add a coverage check: if `recent_closed`'s oldest
   `closed_at` is newer than the window start, set status `incomplete_coverage` and skip the
   disagreement flag instead of reporting a disagreement (§4, §5).
3. **Blocklist timing** — a pick counts as bypassing only if the strategy was blocked at
   issue time; without block dates, label it `blocked_now_issue_time_unknown` (§4, §5).
4. **Batch closes as separate result** — report PF/WR both with and without batch-closed
   trades (§4, §5, §8 item 2).
