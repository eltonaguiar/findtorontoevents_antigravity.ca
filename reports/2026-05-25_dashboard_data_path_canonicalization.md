# Dashboard Data Path Canonicalization — Diagnosis

**Date:** 2026-05-25
**Task:** TASK A — locate the canonical `dashboard_data.json` path; reconcile against `/money-maker-readyv2` skill expectations.

## TL;DR

- **Canonical write path** (production hourly generator): `audit_dashboard/data/dashboard_data.json`
- **Canonical read path** (production readers): `audit_dashboard/data/dashboard_data.json` (most), with a SECOND lineage `audit_trail/data/dashboard_payload.json` used by a different cluster of tools.
- **Skill expectation** (`/money-maker-readyv2`): `audit_dashboard/data/dashboard_data.json` — **MATCHES the canonical write path**. The skill is correct; the file is simply absent in this local clone because both paths are gitignored and regenerated hourly only in CI / on the live box.
- **`audit/data/dashboard_data.json`** is NOT the canonical file. It is a legacy snapshot (file `generated_at: 2026-04-11T00:03Z`, ~6 weeks old; `performance.asset_class_health` is empty). The previously-reported "1062h stale" referred to this dead path — not a real freshness alarm on the live data.
- **Recommended fix:** **NO code change required.** Update the skill SKILL.md with a small "file may be missing locally — fetch it" note so future agents don't conclude the path is wrong.

## Evidence

### 1. Who WRITES `dashboard_data.json`?

`audit_trail/dashboard_generator.py`:
- Line 18107-18116 (main writer):
  ```
  external_data_path = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
  ...
  external_data_path.write_text(json.dumps(payload, ...), encoding="utf-8")
  ```
- Line 16684 also writes `audit_trail/data/dashboard_payload.json` (intermediate payload for downstream consumers).

There is **one** production writer for `dashboard_data.json` and it lands in `audit_dashboard/data/`.

### 2. Who READS `dashboard_data.json`?

`grep -rn "dashboard_data.json" --include="*.py"` (filtered to read-open calls):

Readers of `audit_dashboard/data/dashboard_data.json`:
- `score_audit.py`, `score_audit2.py`, `tools/run_anti_overfit_audit.py`,
  `tools/audit_data_health_pipeline.py`, `tools/_analyze_picks.py`,
  `tools/edge_latent_features.py`, `tools/predictor_ic_reproducer.py`,
  `tools/backfill_closed_smart_scores.py`, `tools/apply_equity_inverse_mutations.py`,
  `tools/run_audit.py` (default `--dashboard` flag),
  `tools/audit_smart_gate_funnel.py`, `tools/protocol_closed_pick_backtest.py`,
  `tools/_perf_by_class.py`, `tools/pick_notarizer.py`,
  `tools/paper_trade_mysql_writer.py`, `tools/_verify_n_reproducible.py`,
  `tools/_analyze_audit.py`, **and `alpha_engine/money_ready_verdict.py` line 95
  (`DASHBOARD_PATH = REPO_ROOT / "audit_dashboard/data/dashboard_data.json"`,
  used as a fallback when `pf_registry.json` is unavailable).**

Readers of `audit_trail/data/dashboard_payload.json` (the second lineage):
- `analyze_crypto_patterns.py`, `audit_researcher_analysis.py`,
  `analyze_short_strategies.py`, `check_systems.py`, `generate_report.py`,
  `predictions/audit_signal_enrichment.py`, `genome/mutation_lab/db_wrapper.py`,
  `tools/risk_parity_allocator.py`, `tools/risk_metrics.py`,
  `tools/validate_asset_class_plan_changes.py`, `test_fast_automation.py`.

The two files are NOT equivalent: `dashboard_payload.json` is the intermediate
"raw payload" written before the dashboard-side post-processing; `dashboard_data.json`
is the final external data file embedded by the audit page.

### 3. What does the SKILL expect?

`.claude/skills/money-maker-readyv2/SKILL.md`:
- Line 43-45: cites `audit_dashboard/data/dashboard_data.json::performance.asset_class_health` and `::walkforward.by_class` and `::fwd_vs_bt_divergence.rows`.
- Line 53: `d = json.loads(Path("audit_dashboard/data/dashboard_data.json").read_text())`
- Line 109: pulls open picks from `audit_dashboard/data/dashboard_data.json::systems`.

This is **the correct canonical path**. The skill is in sync with the production writer and the majority of readers.

### 4. Why does the file not exist locally?

`.gitignore` lines 214-215:
```
audit_dashboard/data/dashboard_data.json
audit_trail/data/dashboard_payload.json
```

Both files are gitignored (regenerated hourly in CI / on the live box). A fresh
clone or a worker PC will not have either until the local generator runs or the
file is pulled from prod.

### 5. The "stale 1062h" red herring

`stat audit/data/dashboard_data.json` shows mtime `2026-05-23 09:23` (recent),
but the file's internal `generated_at` is `2026-04-11T00:03Z` (~44 days old) and
`performance.asset_class_health` is **empty `{}`** (pre-M-067 schema). This file
is **not the canonical artifact** — it's a legacy snapshot, probably left over
from an old refactor or test fixture. The previously-reported 1062h staleness
was reading the OLD `generated_at` not mtime. Either way, this path is not what
the skill targets and not what production writes.

## Minimum-risk recommendation

Two options; option (A) preferred:

**(A) Document the local-absence behavior in SKILL.md (no code change).**
Add a 3-line note near the path table:

> NOTE: `audit_dashboard/data/dashboard_data.json` is gitignored. On a fresh
> clone it will be missing — fetch it from
> `https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/audit_dashboard/data/dashboard_data.json`
> (or run the hourly `audit_trail/dashboard_generator.py` if you have a full
> pick ledger). Do NOT fall back to `audit/data/dashboard_data.json` — that is
> a stale legacy snapshot with an empty `asset_class_health`.

`tools/run_audit.py:297` already prints the same fetch URL on missing-file
errors; mirroring that in SKILL.md keeps the contract obvious.

**(B) Delete `audit/data/dashboard_data.json`** (the legacy snapshot) to
prevent future agents from mistaking it for the canonical file. Low risk:
nothing in the production read-list above points to that path; the only readers
are 4 ad-hoc analysis scripts (`analyze_closed.py`, `analyze_perf.py`,
`analyze_perf2.py`, `analyze_picks.py`) hardcoded to `C:/...` Windows paths and
clearly not on the live pipeline.

**Do NOT** rewrite the skill to point at `audit/data/...` or to add symlinks —
that would diverge from the production writer and break every other reader.

## Outstanding

- Decide whether to also rename `dashboard_payload.json` callers to consume
  `dashboard_data.json` (a separate, larger refactor — out of scope for this
  diagnosis).
