# Root Cause: Regen Pipeline Strips Manual index.html Hotfixes

**Date:** 2026-04-05
**Investigator:** `claude-regen-hardener` (subagent of `claude-sports-db-fix`)
**Status:** INVESTIGATION ONLY — no code changes applied. Awaiting peer review before fix.

---

## TL;DR

`dashboard_generator.py` is **innocent**. It is a clean template→output renderer. The stripping happens inside the `.github/workflows/audit-dashboard.yml` commit/rebase/stash-pop block, which
(a) regenerates index.html from a **stale** checkout of template.html captured at workflow start, then
(b) resolves stash-pop conflicts with `git checkout --ours audit_dashboard/index.html`, which discards any peer hotfix pushed to index.html during the ~45-minute workflow run.

**One-liner root cause:** The workflow commits the stub-less index.html it generated from a 45-minute-old template snapshot and uses `--ours` on conflict, which silently overwrites peer hotfix commits that landed in the meantime.

---

## Algorithm: How index.html Is Actually Built

### Step 1 — Generator (pure, deterministic)

File: `audit_trail/dashboard_generator.py`, function `build_html(payload)` at **line 11417–11468**.

```python
template_path = ROOT / "audit_dashboard" / "template.html"
output_path   = ROOT / "audit_dashboard" / "index.html"

html = template_path.read_text(encoding="utf-8", errors="replace")
payload_json = json.dumps(payload, default=str)
marker = "// __DASHBOARD_DATA_PLACEHOLDER__"
# ...
if marker in html:
    html = html.replace(marker, replacement)          # line 11453
else:
    inject = f"<script>\n{replacement}\n</script>\n</body>"
    if "</body>" in html:
        html = html.replace("</body>", inject)         # line 11458

output_path.write_text(html, encoding="utf-8")         # line 11466
```

This is a **single-placeholder string replacement**. There is no managed-region marker, no Jinja2, no partial update, no regex stripping, no line-range logic. Whatever sits in `audit_dashboard/template.html` at the moment `build_html` runs is what ends up in `audit_dashboard/index.html`, modulo the single `// __DASHBOARD_DATA_PLACEHOLDER__` token.

**Conclusion:** `template.html` IS the source of truth. The generator cannot strip stubs that exist in template.html.

### Step 2 — Workflow commits the result (the real bug)

File: `.github/workflows/audit-dashboard.yml`, job `generate-and-deploy`.

Relevant sequence (annotated with line numbers):

```
L32   actions/checkout@v4 with fetch-depth: 1  ← snapshot of origin/main @ T0
L153  python -m audit_trail.dashboard_generator ← reads template@T0, writes index.html
L230  git stash                                 ← stashes locally-generated index.html
L231  git pull --rebase -X theirs origin main   ← pulls any commits landed during T0..now
L237  git stash pop                             ← may conflict against pulled index.html
L243  git checkout --ours audit_dashboard/index.html  ← ← ← THE BUG
L244  git add audit_dashboard/index.html
L257  git commit -m "chore(audit-dashboard): refresh payload [skip ci]"
```

`--ours` during a stash-pop means "keep the stashed version", i.e. the output the generator produced from the **T0 template**. Any peer hotfix pushed to `audit_dashboard/index.html` (or to `template.html`) between T0 and commit time is silently discarded.

---

## Evidence: Timeline of Commit `9abd5748a9`

Workflow cron: `10 * * * *` (hourly at :10).

| Time (UTC) | Event | Commit |
|---|---|---|
| 02:10 | Cron fires → `actions/checkout` captures `origin/main` at this moment. Main is at a commit **BEFORE** 3a5accee8c. template.html has NO stubs yet. | T0 |
| 02:10–02:55 | Workflow runs ~45 min. `dashboard_generator` executes around ~02:30 reading the T0 template (no stubs) → writes index.html without stubs. | — |
| 02:51:15 | Peer commits `3a5accee8c` "fix(audit): stub syncTrustBookUi + trustBookNarrowed" — adds stubs to **template.html only** (20 insertions). | 3a5accee8c |
| 02:55:42 | Peer commits `e5a5dfe604` "hotfix(index): apply … stubs to generated index.html" — adds stubs directly to **index.html** because live site was crashing. | e5a5dfe604 |
| 02:56:21 | Workflow finishes: `git stash` → `git pull --rebase -X theirs` (picks up both peer commits) → `git stash pop` conflicts → `git checkout --ours audit_dashboard/index.html` resurrects stub-less index.html → commit + push. | 9abd5748a9 |

Verification commands used:

```
$ git show 63cffd146b:audit_dashboard/template.html | grep -c syncTrustBookUi
6
$ git show 63cffd146b:audit_dashboard/index.html | grep -c syncTrustBookUi
3    ← only call-sites, no stub definitions
$ git show e5a5dfe604:audit_dashboard/index.html | grep -c syncTrustBookUi
6    ← hotfix landed
$ git show 9abd5748a9:audit_dashboard/index.html | grep -c syncTrustBookUi
3    ← chore commit wiped stubs back out
```

Diff from the chore commit (audit_dashboard/index.html at commit `9abd5748a9`) shows the stub block being **removed** at lines 2993–3010 — exactly the 18 lines the hotfix had added.

---

## Root Cause (one line)

`.github/workflows/audit-dashboard.yml:243` uses `git checkout --ours audit_dashboard/index.html` to resolve stash-pop conflicts, which silently reverts any peer index.html hotfixes that landed during the 45-minute workflow window, AND the generator itself used a stale template.html snapshot from workflow-start (before peers' template.html fixes were merged), so even without the stash conflict the output would have been stub-less.

---

## Recommended Fixes (ranked by risk/effort)

### Option 1 — Regenerate AFTER the pull (LOW RISK, LOW EFFORT) — **RECOMMENDED**

Move the `python -m audit_trail.dashboard_generator` invocation to **after** `git pull --rebase` (and after stash-pop), so the generator always reads the freshest `template.html` including any peer fixes merged during the workflow window.

**Edit:** In `.github/workflows/audit-dashboard.yml` around lines 230-250, after stash-pop resolution and BEFORE `git add audit_dashboard/index.html`, add:

```bash
# Re-run generator against freshly-pulled template.html to pick up any
# peer hotfixes landed during the ~45-min workflow run.
python -m audit_trail.dashboard_generator
```

Then `git add audit_dashboard/index.html` will stage the re-rendered HTML. This makes `template.html` the single source of truth **at push time**, not at checkout time, and removes the entire `--ours` / stash-pop race.

Benefits:
- Preserves all existing behaviour (still writes index.html fully deterministically from template).
- Zero JS/template surgery.
- Eliminates need for index.html hotfixes entirely — peers just edit template.html and push.

Risks:
- Adds ~30s to the commit step (second generator run). Acceptable; the full workflow is ~45 min.
- If template.html itself has a syntax bug, both generator runs will fail identically (already true).

### Option 2 — Move stubs to an external JS file (LOW RISK, MEDIUM EFFORT)

Create `audit_dashboard/dashboard_enhancements.js` (already referenced in the FTP deploy at `audit-dashboard.yml:350`) containing the stubs + any other fix-forward JS. Include it via a `<script src="dashboard_enhancements.js"></script>` tag in `template.html`. The generator never touches this file.

Benefits:
- Decouples fix-forward JS from the regen cycle entirely.
- Easy for any peer to hotfix without touching template.html or index.html.
- Matches existing file convention — dashboard_enhancements.js is already being deployed.

Risks:
- Requires moving ~18 lines of stubs out of template.html and verifying load-order (stubs must execute BEFORE the inline script that calls `syncTrustBookUi`).
- Extra HTTP request on page load (negligible; file is tiny and CDN-cacheable).
- Live site currently does NOT serve dashboard_enhancements.js correctly on all 3 domains; would need verification.

### Option 3 — Patch the generator to preserve user-added script blocks (HIGH RISK, HIGH EFFORT)

Add a `<!-- BEGIN: USER_PATCHES -->` / `<!-- END: USER_PATCHES -->` managed region in both template.html and index.html. Generator copies content inside this region from existing index.html into the new output before writing.

Benefits:
- Permanent hotfix escape hatch.

Risks:
- Diverges template.html from index.html (two sources of truth for the patches region).
- Easy for a peer to forget the markers and have their fix silently dropped.
- New bespoke mechanism to maintain; high complexity for a simple problem.
- Does NOT fix the underlying staleness — if the patches are in template.html they still miss updates.

**Not recommended** unless Options 1 and 2 are both rejected.

---

## Immediate Recommendation

Apply **Option 1** (regenerate after pull). It is the smallest change with the highest leverage and eliminates the race entirely. The second generator run costs ~30s against a 45-minute workflow.

After Option 1 is verified stable (1-2 cron cycles), Option 2 is worth layering on top as belt-and-suspenders for truly out-of-band JS hotfixes where a peer does not want to edit template.html at all.

---

## Files Referenced

- `e:/findtorontoevents_antigravity.ca/audit_trail/dashboard_generator.py` (lines 11417-11468)
- `e:/findtorontoevents_antigravity.ca/audit_dashboard/template.html` (lines 3003-3020, stubs live here)
- `e:/findtorontoevents_antigravity.ca/audit_dashboard/index.html` (regen target)
- `e:/findtorontoevents_antigravity.ca/.github/workflows/audit-dashboard.yml` (lines 32, 153, 230-257 — the real bug lives at L243)

## Commits Referenced

- `3a5accee8c` — stubs added to template.html
- `e5a5dfe604` — index.html hotfix (stubs)
- `9abd5748a9` — chore regen that stripped stubs from index.html
- `d77675878f` — re-add of stubs to index.html (will be stripped again on next cron unless fixed)
- `63cffd146b` — approximate workflow checkout base (T0)
