# FIX BATCH A — Operator Review TypeError + audit JS 404s

**Date:** 2026-11-15
**Scope:** 3 files, working-tree only (no commit/branch/push — left for user/merger).

## What was broken

### 1. Operator Review TypeError (browser-confirmed)

`audit_dashboard/dashboard_enhancements.js`, `renderOperatorReviewToday` (line ~155-156):

```js
const srcRows = (p.source_strategies || []).map(function (s) {
  const sn = htmlEscape(s.name || s.cite || '?');   // ← crash
```

The guard `(p.source_strategies || [])` only protects against the *array itself*
being null/undefined. Live payload contained a **null element inside** the array,
so the `.map` callback ran with `s === null` and threw:

```
TypeError: Cannot read properties of null (reading 'name')
    at dashboard_enhancements.js:156:33
```

This killed the Operator Review panel rendering for the whole page.

### 2. Two audit JS files 404 on live

`audit_dashboard/index.html` (line 18991-18992) and `template.html` load:

```html
<script src="excess_column.js"></script>
<script src="forward_clock.js"></script>
```

Both files exist in the repo but were **never added to any deploy list**, so all
three sites returned 404 for them. Effects: the "vs Bench" excess column falls
back to a `—` cell (`title="excess_column.js not loaded"`), and the forward-clock
panel never renders.

## What changed

| File | Change |
|------|--------|
| `audit_dashboard/dashboard_enhancements.js` | Added `.filter(Boolean)` before `.map(...)` on `p.source_strategies` (line ~155) + dated comment. |
| `tools/deploy_audit_files.py` | Added `forward_clock.js` + `excess_column.js` as `(local, remote, "audit_js")` tuples matching sibling entries (`/findtorontoevents.ca/audit/<file>`), right after `validation_metrics.js`. |
| `.github/workflows/audit-dashboard.yml` | Added `forward_clock.js` + `excess_column.js` to all **three** per-site JS upload lists (findtorontoevents.ca ~line 1195, torontoevent.net ~line 1333, tdotevent.ca ~line 1441) where the sibling `dashboard_enhancements.js` etc. already appear. |

### Scope note on Fix 1

Audited every `.map(function` in `dashboard_enhancements.js`:
- Line 155 (`source_strategies` array of objects) — **fixed** (same null-element risk).
- Line 133 (`payload.picks`) and line 1089 (`Object.keys(byClass)`) — different data shape, no null-element risk, untouched.
- Lines ~368/~387 treat `source_strategies` as an **object** via `Object.keys(p.source_strategies || {})` — null array is guarded by `|| {}`, arrays with null elements are safe under `Object.keys`. Untouched.

## Verification (all passed)

1. `node --check audit_dashboard/dashboard_enhancements.js` → **OK** (no output, exit 0).
2. `python -c "import ast; ast.parse(open('tools/deploy_audit_files.py').read())"` → **OK**.
3. `python -c "import yaml; yaml.safe_load(open('.github/workflows/audit-dashboard.yml'))"` → **YAML_OK** (pyyaml present, full parse).
4. `git diff --stat` scoped to the 3 files:
   ```
   .github/workflows/audit-dashboard.yml     | 12 +++++++++---
   audit_dashboard/dashboard_enhancements.js |  4 +++-
   tools/deploy_audit_files.py               |  4 ++++
   3 files changed, 16 insertions(+), 4 deletions(-)
   ```
   Repo dirty count went 88 → 91 — exactly these 3 files, nothing else touched.

## Pre-edit conflict check

Before editing, `git status --porcelain <file>` was run on each target — **all
three were clean** (88 other dirty paths belonged to sibling agents; none
overlapped). A peer-agent notice arrived from the read-only live-audit agent
(no file writes in its brief) — no conflict.

## Rollback

```bash
git checkout -- audit_dashboard/dashboard_enhancements.js \
                tools/deploy_audit_files.py \
                .github/workflows/audit-dashboard.yml
```

(Only valid while these edits remain uncommitted; they are the only changes to
these 3 paths in the working tree at time of writing.)

## Post-deploy check

After the next audit-dashboard run / `tools/deploy_audit_files.py` execution:

- `curl -sI https://findtorontoevents.ca/audit/forward_clock.js` → 200
- `curl -sI https://findtorontoevents.ca/audit/excess_column.js` → 200
- (repeat for `tdotevent.ca`, `torontoevent.net`)
- Load `/audit/` → Operator Review panel renders, no `TypeError ... reading 'name'` in console.

---

# Batch B — 2026-11-16 (strategy-tribunal 404 + hypothesis tracker)

Two follow-up items implemented **on top of batch A** (batch A edits to
`.github/workflows/audit-dashboard.yml`, `tools/deploy_audit_files.py`,
`audit_dashboard/dashboard_enhancements.js` were preserved untouched —
`git status --porcelain` checked before each edit; `audit_dashboard/template.html`
was clean pre-edit). No commit/branch/push performed. `audit_dashboard/index.html`
not edited (CI-built from `template.html`).

## B1 — `strategy_tribunal_latest.json` 404

**What was broken:** the `/audit` template fetches
`./data/strategy_tribunal_latest.json` and both deploy paths
(`tools/deploy_audit_files.py` UPLOADS + the workflow's `audit_dashboard/data/*.json`
FTP glob) already shipped it — but **no step in the hourly
audit-dashboard workflow generated the file**. Only the weekly
`strategy-tribunal.yml` ran `tools/strategy_kill_tribunal.py`, and even its commit
step never got the file onto `main` (its own comment documents the push race),
so `audit_dashboard/data/strategy_tribunal_latest.json` is absent from the repo
and the live sidecar 404'd.

**Fix:** added a non-fatal generation step in the hourly build job, directly after
the `python tools/money_ready_snapshot.py || echo ...` line (~618) inside the
`Generate dashboard payload and build HTML` step — same `run:` block, therefore the
same `env:` (incl. `DB_PASS_STOCKS` / `DB_PASS_BACKUPS`, which
`tools/db_env.get_stocks_creds()` needs; `pymysql` is installed earlier in the job
at line ~135):

```bash
python tools/strategy_kill_tribunal.py || echo "strategy tribunal snapshot warning (non-fatal)"
```

Placement guarantees the fresh file is (a) written before the `Commit updated data`
git-add loop (which already lists `audit_dashboard/data/strategy_tribunal_latest.json`)
and (b) present before the FTP deploy's `audit_dashboard/data/*.json` glob.

**Job audit:** `yaml.safe_load` confirms this workflow has exactly **one job**
(`generate-and-deploy`, 50 steps) — there is no second job that uploads audit data,
so no (b) insertion point exists. Other workflows that call
`deploy_audit_files.py --only audit_data` (ai-leaderboard-freshness,
daily-top-picks-filter) only *upload* existing files and need no generator.

**Rollback:** delete the 11 added comment/command lines from
`.github/workflows/audit-dashboard.yml` (search `batch B`).

## B3 — hypothesis/theories tracker wired to the dashboard

**Schema discovered** (read, not guessed) — `reports/hypothesis_registry.json`:
top level = `schema_version`, `description`, `rule`, `notes` (string list) + **19
list-of-object buckets** carrying hypothesis entries (`hypotheses` = the main list
of **99**; plus side buckets `fork2_new_signals`, `free_api_hypotheses_2026_05_18`,
`copilot_fund_etf_simulation_2026_11_15`, …). Entry fields: `id`, `asset_class`,
`family`, `description`, `test_statistic`, `acceptance_criteria`, `economic_prior`,
`status`, `registered_at`, `data_sample_lock`, `result`, `kill_reason` (+ sparse
extras). **141 entries across 20 buckets** by the box's per-entry count.
No `updated_at` field exists — recency = max `YYYY-MM-DD` over all date-like string
fields (`registered_at`, `tested_at`, `last_evaluated`, `pre_registered_utc`, …).
`status` is free-form: 41 raw distinct values, normalized by the box to
first-segment-before-` - ` + UPPER + `-`→`_` (merges e.g. `PRE-REGISTERED`/
`PRE_REGISTERED`, `forward-shadow`/`FORWARD_SHADOW`, `REJECTED - tested, …`→`REJECTED`).
Top normalized counts on current data: FORWARD_OBSERVATION 19, PRE_REGISTERED 18,
UNTESTED 17, REJECTED 16, REFUTED 15, TESTED_KILL 12, PAPER_PILOT 7,
FORWARD_SHADOW 7 (+20 more).

**Deploy (3 wirings):**
1. `tools/deploy_audit_files.py` UPLOADS: `("reports/hypothesis_registry.json",
   "/findtorontoevents.ca/audit/data/hypothesis_registry.json", "audit_data")`
   (runs daily 04:50 UTC + every 4h via `--only audit_data`).
2. Workflow commit git-add `for f in ...` list: added `reports/hypothesis_registry.json`
   (guarded by the existing `[ -f "$f" ] || continue`).
3. **Extra:** the workflow's inline FTP deploy has its own "Extra data" list (it does
   **not** call `deploy_audit_files.py`, and that script only targets
   `/findtorontoevents.ca/…`), so the tuple was also added to the extra-data list of
   **all 3 site functions** (`deploy_findtorontoevents`, `deploy_torontoevent_net`,
   `deploy_tdotevent_ca`) → `…/audit/data/hypothesis_registry.json` on every site on
   the first hourly run. Without this, tdotevent.ca / torontoevent.net would 404 forever.

**Template box** (`audit_dashboard/template.html` only): a compact
`<details id="hypothesis-registry-panel">` placed directly after the
`strategy-tribunal-panel` box (same informational-box stack, always visible above the
tab bar), copied from that neighbour's markup. 54 lines (43 JS). On load it fetches
`./data/hypothesis_registry.json?` + `Date.now()` and renders: total entries + bucket
count + main-list size, top-8 normalized status counts (+N more), and the 3 most
recently dated entries (`id · status · date — description`). All interpolations go
through an `esc()` HTML-escaper. **On non-OK response, empty/absent `hypotheses`, or
any exception the whole box is hidden (`style.display='none'`)** — no broken UI if the
sidecar is missing.

## Verification (all passed)

1. `python -c "import ast; ast.parse(open('tools/deploy_audit_files.py').read())"` → OK.
2. `python -c "import yaml; yaml.safe_load(open('.github/workflows/audit-dashboard.yml'))"` → OK (pyyaml present); jobs = `['generate-and-deploy']`.
3. Template: added `<script>` extracted → `node --check` OK; CI-equivalent
   `new Function(script)` sweep over `template.html` → 0 errors; `html.parser` pass on
   the 54-line added snippet → no unclosed/mismatched tags.
4. Behavioural dry-run in node with the real registry: success path renders
   `141 entries across 20 buckets (main hypotheses list: 99)` + status mix + recent 3
   (H-142 / H-143 / H-141); null payload, `{}` payload and rejected fetch all set
   `display: 'none'`.
5. `git diff --stat` (batch A + B combined):
   ```
   .github/workflows/audit-dashboard.yml     | 40 ++++++++++++++++++++---
   audit_dashboard/dashboard_enhancements.js |  4 ++-   (batch A only, untouched by B)
   audit_dashboard/template.html             | 53 +++++++++++++++++++++++++++++++
   tools/deploy_audit_files.py               |  9 ++++++
   4 files changed, 101 insertions(+), 5 deletions(-)
   ```
   Only expected files changed; no other tracked file modified.

## Rollback

```bash
git checkout -- audit_dashboard/template.html \
                tools/deploy_audit_files.py \
                .github/workflows/audit-dashboard.yml
```
(batches A+B are both still uncommitted — this also reverts batch A on those 2 files;
to keep A, revert manually by searching `batch B` comments.)

## Post-deploy check

- `curl -sI https://findtorontoevents.ca/audit/data/strategy_tribunal_latest.json` → 200
- `curl -sI https://findtorontoevents.ca/audit/data/hypothesis_registry.json` → 200 (also `tdotevent.ca`, `torontoevent.net`)
- Load `/audit/` → 🧪 Hypothesis Tracker box renders counts + recent entries; console free of fetch errors for both sidecars.

## Batch B restoration (2026-11-25)

The batch A+B working-tree edits were **lost from disk** between sessions (a
checkout/merge sequence on 2026-11-17/23 by other agents — the docs above
survived, the `.md` reconstruction source was used to re-apply). Restored on
2026-11-25 against current main:

- **B1** — `strategy_kill_tribunal.py` non-fatal step re-inserted after
  `money_ready_snapshot.py` (now line ~633; workflow had grown).
- **B3** — all three wirings re-applied (deploy-tuple, git-add list, 3-site FTP
  extra-data lists) + the template box re-written to spec as
  `#hypothesis-registry-panel` (**restyled as "Hypothesis Registry (rule M-107
  pre-registration ledger)"** because a sibling panel,
  `#theory-tracker-panel` — `theory_portfolios.json` + `reports/h0XX_*.json`,
  live and 200 — now occupies the slot next to the tribunal panel; the two are
  complementary, not duplicates).

Re-verified 2026-11-25: yaml.safe_load OK (1 job), ast OK, `node --check` OK,
`new Function` sweep 18 scripts 0 errors, html.parser OK, dry-render on the live
registry: `181 entries across 20 buckets (main hypotheses list: 139) schema
v1.0`, top statuses PRE_REGISTERED 57 / FORWARD_OBSERVATION 19 / ..., recent 3
(R4b 2026-11-23, H-119, H-2026-11-19-01), null/`{}`/notes-only payloads all hide
the box.
