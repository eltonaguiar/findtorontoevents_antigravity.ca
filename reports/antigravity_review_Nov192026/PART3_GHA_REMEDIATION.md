# Part 3 · P3-5: GHA QA Findings + Live CI Health Check

**Author:** GitHub Copilot / Mercury-3 AI (`githubcopilot-mercury3AI`)
**Date:** 2026-11-22 04:30 EST

This doc reconciles the **static workflow audit** (what the YAMLs look like) with a **live health check** (what actually failed in GitHub Actions). It also corrects several false positives from the static scan.

---

## 1. Live GitHub Actions health check (source repo, 2026-11-22 07:00 UTC)

Analyzed the last **100 workflow runs** via the Actions API:

| Metric | Value |
|---|---|
| Total runs | 100 |
| Success | 80 |
| Failed | **4** |
| Pending/in-progress | 16 (scheduled hourly jobs, normal) |
| Event mix | schedule 71 · pull_request 24 · workflow_run 4 · dynamic 1 |

**The 4 failures:**
| Workflow | Event | Root cause |
|---|---|---|
| **CI Tests** | pull_request | `ImportError: cannot import name 'merge_gate' from tools.audit2_forward_summary` in `tests/test_audit2_forward_summary.py:7` — blocks collection (exit 2) |
| **CI Tests** (×3) | pull_request | same root cause (3 PR runs → same import collection error) |
| **Kalshi snapshot** | schedule | sports-markets cache (separate) |

### CI failure detail (the actionable one)
```
tests/test_audit2_forward_summary.py:7:
    from tools.audit2_forward_summary import merge_gate
E   ImportError: cannot import name 'merge_gate' from 'tools.audit2_forward_summary'
```
`test_audit2_forward_summary.py` imports `merge_gate` from `tools/audit2_forward_summary.py`, but that function does not exist in the module. **Fix:** update the test to import the actual symbol (or add `merge_gate` to the module), or quarantine the test. This is the *only* thing blocking CI on PRs.

---

## 2. Static audit — real issues vs false positives

The earlier static scan flagged 7 workflows. **Verified against actual file contents:**

| Workflow | Static flag | Verdict |
|---|---|---|
| `masking-policy-lint.yml` | "schedule without workflow_dispatch" | **FALSE POSITIVE** — it is PR-only (`on: pull_request`), no schedule at all |
| `_dynamic-runner-template.yml` | "schedule without workflow_dispatch" + "no concurrency" | **FALSE POSITIVE** — it is a reusable `workflow_call` template, not a scheduled run |
| `pod-emission-audit.yml` | "no concurrency" | **FALSE POSITIVE** — single job; already has `schedule` + `workflow_dispatch` + `pull_request` |
| `ci-tests.yml` | "broad deploy-path glob" | **FALSE POSITIVE** — globs are `**/*.py` (code-only), precisely the intended behavior |
| `deploy-competition-to-site.yml` | "broad deploy-path glob" | **PARTIAL** — includes `audit_dashboard/**` (broad) — narrow to exact files |
| `audit-drift-telemetry.yml` | "broad deploy-path glob" | **PARTIAL** — `audit_dashboard/**` is legitimate here (it IS the drift telemetry for the dashboard); acceptable |

**Real recommended edits:** only `deploy-competition-to-site.yml` should narrow its `audit_dashboard/**` glob. The static scan over-reported; the **live check found the real problem (CI import error)** which the static scan cannot see.

---

## 3. Recommendation

1. **Fix the CI collection error** (the only real red): align `test_audit2_forward_summary.py` with `tools/audit2_forward_summary.py`.
2. **Narrow** `deploy-competition-to-site.yml` to explicit file paths (drop `audit_dashboard/**`).
3. **Keep** the `_dynamic-runner-template.yml` as-is (template), and add `workflow_dispatch` + `concurrency` to genuine multi-job *scheduled* workflows (none currently broken).
4. Improve the audit script to ignore `workflow_call` templates and to parse `on:` YAML properly (so it stops flagging false positives).

---
*Not investment advice. Live data: Actions API 2026-11-22 07:00 UTC; static data: .github/workflows/ contents.*
