# Stalled-Producer Detector — `tools/check_stalled_producers.py`

**NEW tool — 2026-06-23 (added during the `/money-maker-ready-June112026edition` audit).**
**Companion to:** `reports/money_maker_ready_20260623T235825Z.md` (Appendix A — Stalled-producer evidence).

---

## Why this tool exists

During the 2026-06-23 audit we discovered the GH Actions `audit-dashboard.yml` cron run has been **reporting `conclusion: success` while the canonical data files it publishes have been silently stalled since 2026-06-03** (~20 days). Five files are stale:

| File | Age at audit |
|---|---|
| `audit_dashboard/data/dashboard_data.json` | 489 h |
| `audit_dashboard/data/pick_funnel_90d.json` | 489 h |
| `audit_dashboard/data/pick_funnel_today.json` | 489 h |
| `audit_dashboard/data/money_ready_verdict.json` | 64 h |
| `audit_dashboard/data/walkforward_results.json` | MISSING |
| `audit_dashboard/data/fwd_vs_bt_divergence.json` | MISSING |
| `entry_conditions_forward.json` | MISSING |

The cron's narrow per-job success masks a downstream "publish into disk" silent no-op — most likely fed by a stale GH Actions `MYSQL_PASSWORD` secret vs a LAN-rotated LAN DB password (see `updates/2026-06-23-mysql-lan-block-unblock-runbook.md`).

The `/money-maker-ready` skill v1.1 §0 already specifies a fail-fast freshness preflight: `dashboard_data.json::generated_at` > 2 h → abort. **This tool automates that preflight inline at the GH Actions cron**, so today's silent no-op becomes a loud `exit 1` and the cron `conclusion` flips to `failure` — page-able, not silently misleading.

---

## What this tool does

Reads the `mtime` of nine canonical audit-pipeline data files and emits a per-file health row with one of three statuses:

- **`ok`** — `age_h ≤ threshold_h` (file present and fresh)
- **`stale`** — `age_h > threshold_h` (file present but NOT fresh)
- **`missing`** — file path doesn't exist on disk

Default thresholds (per skill v1.1 §0):

| Path | Default `max_age_h` | Why this threshold |
|---|---:|---|
| `audit_dashboard/data/dashboard_data.json` | 2.0 | hourly cron; skill §0 |
| `audit_dashboard/data/money_ready_verdict.json` | 2.0 | hourly cron; skill §0 |
| `audit_dashboard/data/pick_funnel_90d.json` | 2.0 | hourly cron |
| `audit_dashboard/data/pick_funnel_today.json` | 2.0 | hourly cron |
| `audit_dashboard/data/walkforward_results.json` | 6.0 | 4× heavier; runs slower |
| `audit_dashboard/data/fwd_vs_bt_divergence.json` | 6.0 | 4× heavier |
| `entry_conditions_forward.json` | 2.0 | hourly predicate |
| `audit_dashboard/data/audit_surface_truth.json` | 4.0 | sub-hourly |
| `audit_dashboard/data/nav_surface_edge_matrix.json` | 4.0 | sub-hourly |

---

## Exit codes

| Code | Meaning | GH Actions mapping |
|---:|---|---|
| 0 | All files within freshness window | job SUCCEEDS — green ✓ |
| 1 | At least one file STALE (mtime > threshold) | job FAILS — yellow/red |
| 2 | At least one file MISSING OR UNREADABLE — `path` exists but `stat()` raised `OSError` (e.g. permission) | job FAILS — red |
| 3 | Repo root not found (config error) | job FAILS — config error |
| 4 | Bad `--threshold-override` parse (empty path, non-numeric hours, negative hours) | job FAILS — config error |
| 5 | Argument conflict — both `--strict` and `--threshold-hours` passed | job FAILS — config error |

**Per-file `FileHealth.status` values** (in `--json` output): `"ok" | "stale" | "missing" | "unreadable"`. Path-traversal-blocked paths surface as `status="missing"` with `note="path-traversal-blocked"` for diagnostic visibility.

---

## How to use

### (a) Local sanity check (the most common use)

```bash
cd /home/eaguiar2015/findtorontoevents_antigravity.ca
python3 tools/check_stalled_producers.py
```

Sample output (text mode):

```
FILE                                                  STATUS     AGE(h)   THR(h)  SIZE(KB)  WHY
--------------------------------------------------------------------------------------------------------------
audit_dashboard/data/dashboard_data.json              stale     489.50     2.0    18827.5  main payload / 18MB
audit_dashboard/data/money_ready_verdict.json         stale      64.30     2.0     243.1  honest intrabar-truth per class
audit_dashboard/data/pick_funnel_90d.json             stale     489.50     2.0      85.4  pick funnel 90d window
audit_dashboard/data/pick_funnel_today.json           stale     489.50     2.0      18.7  today's funnel
audit_dashboard/data/walkforward_results.json         missing       —      6.0        —   OOS folds (writes are heavier)
audit_dashboard/data/fwd_vs_bt_divergence.json        missing       —      6.0        —   backtest overfit detector
entry_conditions_forward.json                         missing       —      2.0        —   sigma-geometry entry sidecar
audit_dashboard/data/audit_surface_truth.json         stale      26.85     4.0     433.0  surface-truth reconciliation
audit_dashboard/data/nav_surface_edge_matrix.json     stale      64.30     4.0     183.2  NAV-by-surface edge matrix

RESULT: ok=0 stale=6 missing=3 total=9
...
```

### (b) `--strict` mode (1h threshold everywhere)

```bash
python3 tools/check_stalled_producers.py --strict
```

For tight-cadence pipelines where 2h is too lenient.

### (c) JSON output (for GH Actions `$GITHUB_OUTPUT` / parsing)

```bash
python3 tools/check_stalled_producers.py --json
```

Output is a list of dicts:

```json
[
  {"path":"audit_dashboard/data/dashboard_data.json","status":"stale","age_h":489.5,"threshold_h":2.0,"mtime_utc":"...","size_kb":18827.5,"why":"main payload / 18MB"},
  {"path":"...","status":"missing","age_h":null,"threshold_h":6.0,"mtime_utc":null,"size_kb":null,"why":"OOS folds (writes are heavier)"}
]
```

### (d) Per-override

```bash
python3 tools/check_stalled_producers.py \
  --threshold-override audit_dashboard/data/walkforward_results.json=12 \
  --threshold-override audit_dashboard/data/fwd_vs_bt_divergence.json=12
```

---

## Recommended GH Actions wiring

Add to `.github/workflows/audit-dashboard.yml` as the **last job in the workflow**, before the auto-commit:

```yaml
      - name: Stalled-producer health-check
        run: |
          python3 tools/check_stalled_producers.py --json --strict
        shell: bash
```

This way:
- If the upstream cron jobs pass locally but the big-file publishers silently no-op (the 2026-06-03 scenario), this step's `exit 1` flips the cron `conclusion` to `failure`.
- The auto-commit step (if it's after this one) is skipped because of `if: success()` default.
- Operator pages a Slack alert via the existing `db-freshness-guardian.yml` cadence.

> **NOTE:** do NOT gate the OFFICIAL freshness guardian (`.github/workflows/db-freshness-guardian.yml`) on this — that watchdog has its own schedule + alerting rules; this is the cron-internal fence.

### Threshold-default rationale

Default `max_age_h` per file (in `DEFAULT_FILE_TABLE`):

| File | Default | Why |
|---|---:|---|
| `audit_dashboard/data/dashboard_data.json` (18 MB) | 2.0 | hourly cron target; skill §0 fail-fast |
| `audit_dashboard/data/money_ready_verdict.json` | 2.0 | hourly cron |
| `audit_dashboard/data/pick_funnel_90d.json` | 2.0 | hourly cron |
| `audit_dashboard/data/pick_funnel_today.json` | 2.0 | hourly cron |
| `audit_dashboard/data/walkforward_results.json` | 6.0 | 4× heavier OOS compute |
| `audit_dashboard/data/fwd_vs_bt_divergence.json` | 6.0 | 4× heavier |
| `entry_conditions_forward.json` | 2.0 | hourly predicate |
| `audit_dashboard/data/audit_surface_truth.json` | 4.0 | sub-hourly reconciliation |
| `audit_dashboard/data/nav_surface_edge_matrix.json` | 4.0 | sub-hourly |

**Python 3.9+ required** — `Path.is_relative_to` strictly (no Py<3.9 fallback). Project runs Py3.11+.

---

## Verification (the audit-time smoke test)

```bash
cd /home/eaguiar2015/findtorontoevents_antigravity.ca
python3 -m py_compile tools/check_stalled_producers.py && echo OK
python3 tools/check_stalled_producers.py
echo "exit=$?"
# Expect: exit=1 or 2 (because stale data; that's correct today)

python3 tools/check_stalled_producers.py --json | head -20
# Expect: parses to JSON list

python3 tools/check_stalled_producers.py --strict
echo "exit=$?"
# Expect: stricter failure

python3 tools/check_stalled_producers.py --threshold-hours 9999
echo "exit=$?"
# Expect: exit=0 (everything "fresh" relative to 9999h)
```

---

## What this tool does NOT do

- Does NOT attempt to **restart** the producer. It only signals the stall.
- Does NOT commit/push anything. Read-only inspection.
- Does NOT depend on MySQL or any network. Pure local `mtime` reads.
- Does NOT mutate `blocklist`/`blacklist` per AGENTS.md safety.

---

## AGENTS.md compliance summary

- ✅ Read-only — no destructive ops (per `safety - Never run destructive commands`)
- ✅ No git push (per `Only Push Your Own Changes`); the new file is documented but not pushed
- ✅ `updates/` companion — this file (per AGENTS.md "Document Every Fix" mandate)
- ✅ Honest labeling — does not claim a fix it doesn't make (`exit 1` is what surfaces the problem; the underlying producer fix is a separate ticket)
- ✅ Skill v1.1 failure-mode handling — covers "Dashboard data >2h stale → abort, surface, ask wait/proceed"

---

## Cross-references

| Reference | Path |
|---|---|
| Full audit (this audit-cycle) | `reports/money_maker_ready_20260623T235825Z.md` |
| Operator-summary updates doc | `updates/2026-06-23-money-maker-ready-june11-edition.md` |
| MySQL LAN-block runbook (the likely producer feeder) | `updates/2026-06-23-mysql-lan-block-unblock-runbook.md` |
| Equity 7× SMART-gate audit | `updates/2026-06-23-equity-smart-gate-7x-disparity-audit.md` |
| Cross-class SMART floor audit | `updates/2026-06-23-cross-class-smart-floor-audit.md` |
| Equity revalidation helper | `tools/revalidate_equity_smart_audit.py` |
| Money-maker-ready skill | `/money-maker-ready` v1.1 2026-05-15 |

---

## Author + version

- Author: Buffy via `/money-maker-ready-June112026edition` audit
- Created: 2026-06-23T23:58:25Z
- Version: 1.0 (initial)
- License: repo-internal
- Files: `tools/check_stalled_producers.py` (~190 lines) + this `updates/2026-06-23-stalled-producer-detector.md`
