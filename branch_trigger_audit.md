# Branch Trigger Audit — `push:` / `pull_request:` blast radius

**Repo:** `eltonaguiar/findtorontoevents_antigravity.ca`
**Base commit:** `eb23252219786dc09362a5a500aef2f9bc6f794f` (`origin/main`)
**Scope:** all 358 `.yml`/`.yaml` files under `.github/workflows/` at that commit (read via `git show origin/main:<path>`; working tree not used — local `main` is 17 commits behind).
**Method:** static parse of the top-level `on:` block. No API, no browser, no CDP. Script: `scratch/classify_triggers.py`.
**Reproduce:** `python3 classify_triggers.py <repo> origin/main .github/workflows`

---

## 0. Correction notice — read before citing any earlier number

> [!IMPORTANT]
> **This supersedes the earlier "4 whole-fleet-on-push hazards" finding. That finding was wrong and must not be re-raised.**
>
> The four files (`audit-drift-telemetry.yml`, `audit-frontend-manifest.yml`, `incidents-enhancements-nightly.yml`, `schema-drift-watchdog.yml`) do have a bare `push:` with no `branches:` key. That observation was correct. But **"no `branches:`" is the necessary condition for a fleet-wide push hazard, not the sufficient one.** All four carry a `paths:` filter, so a push touching none of those globs runs nothing.
>
> The sufficient condition is **no `branches:` AND no `paths:`**. On that test, **the push hazard set is empty.**
>
> Per @coordinator in board #95. Anyone re-deriving this by grepping for missing `branches:` alone will reproduce the false P1 — use the two-axis test in §1.

---

## 1. The rule that makes this audit meaningful

Under `on: push`, GitHub Actions evaluates `branches:` and `paths:` as **AND-ed filters over two different dimensions**:

| filter | dimension it restricts | omitted means |
|---|---|---|
| `branches:` | *which refs* may trigger | any branch |
| `paths:` | *which files* the push must touch | any file |

Omitting `branches:` alone yields "any branch **that also matches `paths:`**". It does **not** yield "any push in the repo". So `paths:` by itself is a complete blast-radius bound: the set of triggering events is finite and enumerable (pushes touching those globs), even though the set of triggering *refs* is unbounded.

That is why the classification must be two-axis:

```
                       has paths: ?
                    no              yes
              +----------------+----------------+
 has          |                |                |
 branches: no |  H  HAZARD     |  B  BENIGN     |
              |  (unbounded)   |  (bounded)     |
              +----------------+----------------+
              |                |                |
          yes |  F  ref-bound  |  F  ref+path   |
              |  (bounded)     |  (bounded)     |
              +----------------+----------------+
```

- **`H`** — no `branches:` and no `paths:`. Every push to every ref runs this workflow. **This is the only shape that deserves the word "hazard".**
- **`B`** — no `branches:` but has `paths:`. Benign by construction. **Footnote material only** — see §3.
- **`F`** — has `branches:`. Bounded on the ref axis regardless of `paths:`. Not part of this audit's risk set.

The same table applies to `pull_request:` (`branches:` there matches the **base** branch; a bare `pull_request:` fires on every PR against every base, including forks).

---

## 2. Axis A — `push:` (the requested audit)

### `H` — true hazard: no `branches:` AND no `paths:`

> [!IMPORTANT]
> **Count on `origin/main` @ `eb23252`: 0 of 358.** The hazard set is **empty**, not merely "near-empty". @coordinator's expectation is confirmed exactly — no file needed to be excused.

There is therefore **no whole-fleet-on-push workflow on main today**. Any report claiming one exists is reproducing the §0 error.

Empirically: 36 files have a `branches:`-filtered push, 4 have a paths-only push, 318 have no `push:` trigger at all. 36 + 4 + 318 = 358.

### `B` — benign by construction (footnote, not a finding)

These 4 files declare `push:` with `paths:` but no `branches:`. They are bounded: only a push touching one of their globs runs them, on any branch. Listed once here so the set is closed and nobody re-derives it as a hazard.

| file | bounded by `paths:` |
|---|---|
| `audit-drift-telemetry.yml` | `audit_dashboard/**`, `tools/drift/**`, 2 configs |
| `audit-frontend-manifest.yml` | `template.html`, `hc_filter.js`, `money_ready_filter.js`, its own `.py` |
| `incidents-enhancements-nightly.yml` | 2 specific `.py` paths |
| `schema-drift-watchdog.yml` | `schemas/baseline_*.json`, its own file |

**No action required on any of these four.** They were the entire content of the retracted finding.

---

## 3. Axis B — `pull_request:` (not requested, but the same shape, and it is where the residual risk actually lives)

Applying the identical two-axis test to `pull_request:` moves the finding away from `push` entirely.

### `h` — `pull_request:` with no `branches:` AND no `paths:`

**Count: 2.** These fire on **every PR event, against every base branch, including PRs opened from forks.**

| file | shape | cost per run | mitigation present |
|---|---|---|---|
| `conflict-marker-check.yml` | `pull_request:` (bare); separately `push: branches: [main, copilot/**, codebuff/**]` | `actions/checkout@v6` (`fetch-depth: 1`) + `git grep` over tracked files | `concurrency.cancel-in-progress: true`, `timeout-minutes: 6` |
| `no-stale-db-passwords.yml` | `pull_request:` (bare); separately `push: branches: [main]` | `actions/checkout` + regex grep over `*.py` | `concurrency.cancel-in-progress: true` |

Note the split: **each file's `push:` is properly bounded (`F`) — it is only the `pull_request:` leg that is unbounded.** Checking these files for missing `branches:` on the push trigger and clearing them would miss the actual gap.

**Severity: low, and deliberately not escalated.** Both are cheap static greps, both self-cancel superseded runs, neither consumes a shared resource or deploys anything. The realistic exposure is runner-minutes on fork PRs and, in principle, repository-fork PR traffic — not a fleet-wide event. Recorded as a genuine unbounded trigger, not as a P1. Escalating this to the same rank the §0 correction demoted would repeat that mistake in the opposite direction.

### For completeness — bounded PR triggers

- `b` (paths only, 12): `asset-class-freshness-watchdog.yml`, `ci-tests.yml`, `hc-parity.yml`, `masking-policy-lint.yml`, `ml-staleness-watchdog.yml`, `money-ready-registry-gate.yml`, `pick-data-quality-gate.yml`, `quant-auditor-fast-pr.yml`, `sports-smoke-and-e2e.yml`, `strategy-performance-no-regression.yml`, `ueps_smoke_tests.yml`, `validate-hf-asset-class.yml`
- `f` (branches-filtered, 3): `db-password-leak-guard.yml`, `secret-scan.yml`, `walkforward-gate.yml`
- no `pull_request:` trigger: 341

---

## 4. Files with no `push`/`pull_request`/`schedule`/`dispatch` trigger (3)

Not hazards — listed so the 358 total reconciles and so no one reads "no trigger" as "zero risk".

| file | actual state |
|---|---|
| `_dynamic-runner-template.yml` | `workflow_call` only — reusable template, invoked by callers. **Classifier gap:** the script does not currently recognise `workflow_call` as a trigger and buckets this as "no trigger". Verdict by manual read: correct by design, not dead. |
| `ml-gatekeeper-ab-bootstrap.yml` | `on: {}` — intentionally disabled 2026-11-16 (comment in file). |
| `mysql-q001-sync.yml` | `on: {}` — intentionally disabled 2026-11-16 (comment in file). |

---

## 5. Summary table

| axis | shape | count | verdict |
|---|---|---|---|
| `push` | no `branches:` + no `paths:` | **0** | **no hazard exists** |
| `push` | `paths:` only (no `branches:`) | 4 | benign — footnote only |
| `push` | has `branches:` | 36 | bounded |
| `push` | no push trigger | 318 | — |
| `pull_request` | no `branches:` + no `paths:` | **2** | unbounded, low severity, mitigated |
| `pull_request` | `paths:` only | 12 | benign |
| `pull_request` | has `branches:` | 3 | bounded |
| `pull_request` | no PR trigger | 341 | — |
| — | `workflow_call` only | 1 | by design |
| — | `on: {}` (disabled) | 2 | intentional |

---

## 6. Delta against `branch_capability.tsv`

Not my file — recorded here only so the shared vocabulary matches. A `push_any` column defined as "no `branches:`" will read **true** for all four §2 `B` files and will be indistinguishable from a hazard when skimmed; per board #95 it should be renamed `push_unbranched` or paired with `push_any_nopaths` (no `branches:` **and** no `paths:`), which is the column that actually equals the hazard set — and which is **all-false on main today**.

---

## 7. Caveats

- **Numbers are pinned to `eb23252`.** This repo commits with `[skip ci]` roughly every minute; `origin/main` has moved since. Re-running the classifier at a later SHA may legitimately produce different counts — that is drift, not an error in this pass.
- **`H` = 0 is a statement about the `on:` block as parsed**, not about what those workflows do once running. A workflow that is `branches:`-bounded can still be expensive; that is the cron/queue audit's problem, not this one.
- Local `main` (17 commits behind) was not audited. The three untracked working-tree files (`.github/workflows/lint.yml`, `INSTALL.md`, `WIRED_IN/audit_report.md`, `Windows/`) are **not** on `origin/main` and are excluded. Note `lint.yml` is untracked — if it is ever committed, it should be re-audited, as an uncommitted workflow has never been run and its triggers are unverified.
