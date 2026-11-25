# Patchset — one Pages publisher, gated deploy, honest hub-sync

**Date:** 2026-11-25 · **Status:** NOT APPLIED
**Why not applied:** `.github/workflows/**` is outside this agent's `owned_prefixes` in
`tools/agent_ownership.json`, and the pre-commit guard refuses such commits. These are exact diffs
for the owner (or an agent that owns that prefix) to apply.

Evidence behind each item: `updates/2026-11-25-actions-validation-antigravity-main-and-gh-pages.md`.

---

## 1. `live_tracker.yml` — stop publishing to a branch nothing serves

**Problem.** `live_tracker` pushes a 191,291-byte "Alpha Engine — Live Autonomous Dashboard" to
`gh-pages` every hour via `peaceiris/actions-gh-pages`. Pages does **not** serve that branch: the
live `/` is the 260-byte `<meta refresh>` to `./hub/` built by `deploy-riseoftheclaw.yml`, and
`/live_picks.json`, `/big_mover_widget.html`, `/bestiejob/` all 404 while existing in the branch.
Every green `live_tracker` run therefore *asserts* a publish that no user can see.

### Diff A — remove the duplicate publisher

```diff
 permissions:
   contents: write
-  pages: write
-  id-token: write
```

```diff
-    - name: Include BESTIEJOB page in Pages publish
-      run: |
-        # peaceiris publishes ./dashboard (keep_files=false), which wipes other
-        # gh-pages paths. Include the rights-gated BESTIEJOB page so it persists.
-        if [ -d docs/bestiejob ]; then
-          mkdir -p dashboard/bestiejob
-          cp -r docs/bestiejob/. dashboard/bestiejob/
-          touch dashboard/bestiejob/.nojekyll
-          echo "Included docs/bestiejob in Pages publish"
-        fi
-
-    - name: Deploy to GitHub Pages
-      uses: peaceiris/actions-gh-pages@v4
-      with:
-        github_token: ${{ secrets.GITHUB_TOKEN }}
-        publish_dir: ./dashboard
```

The "Commit dashboard" step stays: it still commits `dashboard/` to `main`, which is what the
downstream copy below reads.

### Diff B — serve the dashboard from the real deployer

In `deploy-riseoftheclaw.yml`, inside **Prepare deployment directory**, after the existing
`# Trading Systems Hub (master dashboard)` block:

```yaml
          # Alpha Engine live dashboard + BESTIEJOB page. Both used to be published by
          # live_tracker.yml to a gh-pages branch that Pages does not serve (2026-11-25).
          mkdir -p _site/dashboard _site/bestiejob
          if [ -f alpha_engine/live_dashboard.html ]; then
            cp alpha_engine/live_dashboard.html _site/dashboard/index.html
          fi
          if [ -f dashboard/big_mover_widget.html ]; then
            cp dashboard/big_mover_widget.html _site/
          fi
          if [ -f dashboard/live_picks.json ]; then
            cp dashboard/live_picks.json _site/
          fi
          if [ -d docs/bestiejob ]; then
            cp -r docs/bestiejob/. _site/bestiejob/
            touch _site/bestiejob/.nojekyll
          fi
```

Use `if` blocks, not `[ -d x ] && cp ... && touch ...`: GitHub runs steps under `bash -e`, so a
missing directory makes the compound return 1 and fails the step.

---

## 2. `deploy-riseoftheclaw.yml` — never call `deploy-pages` without an artifact

**Problem.** Last 100 runs: **56 failure / 36 success / 7 cancelled**, always the same:

```
Fetching artifact metadata for "github-pages" in this workflow run
Found 0 artifact(s)
##[error]No artifacts named "github-pages" were found for this workflow run
```

The job reaches `actions/deploy-pages@v4` in a run where `upload-pages-artifact` produced nothing.
Note that gating on `steps.upload.outcome` is **not sufficient** — the observed failure mode is an
upload step that does not leave a `github-pages` artifact. Assert the artifact itself.

```diff
 permissions:
   contents: write
   pages: write
   id-token: write
+  actions: read
```

```diff
       - name: Upload artifact
+        id: upload
         uses: actions/upload-pages-artifact@v4
         with:
           path: '_site'

+      - name: Assert a pages artifact was produced
+        id: artifact
+        env:
+          GH_TOKEN: ${{ secrets.GH_PAT || github.token }}
+        run: |
+          n=$(gh api "repos/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID/artifacts" \
+                --jq '[.artifacts[] | select(.name=="github-pages")] | length')
+          echo "github-pages artifacts in this run: $n"
+          if [ "${n:-0}" -lt 1 ]; then
+            echo "::error::upload-pages-artifact left no 'github-pages' artifact; refusing to call deploy-pages (that call is what turns this run red)."
+            exit 1
+          fi
+
       - name: Deploy to GitHub Pages
         id: deployment
+        if: steps.artifact.outcome == 'success'
         uses: actions/deploy-pages@v4
```

This does not remove the red runs — it replaces a confusing failure 40–50 times a day with one
message naming the real cause (the build/validation step before the upload, or a cancelled upload).

---

## 3. `hub-sync.yml` — a green run must mean the data changed

**Problem.** The workflow the whole Pages site redirects into reports success hourly while
`hub/data/systems_manifest.json` still says `"generated_at": "2026-03-02T10:00:00Z"` on `main` and
live, with the last `hub/data/` commit on 2026-11-20. Both failure paths are swallowed:

```yaml
PYTHONPATH=. python signal_recorder/export_hub_combos.py || echo "::warning::Combo export failed"
git commit -m "Sync hub data $(date +%H:%M) [skip ci]" || echo "No changes"
```

```diff
       - name: Collect system data for hub
         run: |
           echo "Hub uses client-side JS (hub/js/consensus_engine.js, hub/js/quality_scorer.js)"
           echo "Ensuring hub data directory has latest winning combos..."
-
-          # Export winning combos if signal_recorder exists
-          if [ -f signal_recorder/export_hub_combos.py ]; then
-            pip install pandas 2>/dev/null || true
-            PYTHONPATH=. python signal_recorder/export_hub_combos.py || echo "::warning::Combo export failed — check signal_recorder module"
-          fi
+          # A missing exporter is a failure, not a warning: with the old `|| echo`,
+          # this workflow reported success for months while serving March data.
+          if [ ! -f signal_recorder/export_hub_combos.py ]; then
+            echo "::error::signal_recorder/export_hub_combos.py is missing — hub data cannot refresh"
+            exit 1
+          fi
+          pip install pandas 2>/dev/null || true
+          PYTHONPATH=. python signal_recorder/export_hub_combos.py
```

```diff
       - name: Commit Updates
         run: |
           git config user.name "github-actions"
           git config user.email "actions@github.com"
           git add hub/data/
-          git commit -m "Sync hub data $(date +%H:%M) [skip ci]" || echo "No changes"
+          if git diff --cached --quiet; then
+            echo "::error::hub data unchanged this run — the export produced nothing"
+            exit 1
+          fi
+          git commit -m "Sync hub data $(date +%H:%M) [skip ci]"
           bash .github/scripts/safe_push.sh
+
+      - name: Assert the hub manifest is fresh
+        run: |
+          python3 - <<'PY'
+          import json, sys
+          from datetime import datetime, timezone
+          p = "hub/data/systems_manifest.json"
+          try:
+              gen = json.load(open(p)).get("generated_at")
+          except FileNotFoundError:
+              print(f"::error::{p} is missing"); sys.exit(1)
+          if not gen:
+              print(f"::error::{p} has no generated_at"); sys.exit(1)
+          ts = datetime.fromisoformat(str(gen).replace("Z", "+00:00"))
+          if ts.tzinfo is None:
+              ts = ts.replace(tzinfo=timezone.utc)
+          age_d = (datetime.now(timezone.utc) - ts).total_seconds() / 86400
+          print(f"hub manifest generated_at={gen} age={age_d:.1f}d")
+          if age_d > 7:
+              print(f"::error::hub manifest is {age_d:.1f} days stale (limit 7d)"); sys.exit(1)
+          PY
```

Expect the first runs to go red — that is the point: the data has been stale since March and the
green check was the bug.

---

## 4. `qa-market-validation.yml` — run the gate on a fresh snapshot

**Problem.** `picks-now-live-pnl.yml` writes the snapshot at `:25`; `qa-market-validation.yml`
checks it at `:13` the following hour, so the ledger always inspects a ~50-minute-old file. The
tight per-class tolerance (0.5pp equity/ETF/forex) cannot be applied across a 50-minute market gap,
so the strict check can never fire. Measured today: at a 19-minute age, 31/31 EQUITY published
prices matched Finnhub exactly, while at ~53 minutes the same comparison produced 8 "mismatches"
that were pure drift.

```diff
 on:
   schedule:
-    - cron: '13 * * * *'        # every hour
+    # :30, not :13 -- the picks-now snapshot is written at :25, so checking at :13
+    # validated a 50-minute-old file and forced the ledger into its coarse mode.
+    # At :30 the snapshot is ~5 minutes old and the 0.5pp per-class tolerance applies.
+    - cron: '30 * * * *'
```

No code change needed: `tools/qa_ledger.py` applies the tight tolerance whenever the snapshot is
within `QA_FRESH_MIN` (default 15) minutes.

---

## Apply and verify

```bash
# apply, then prove each one behaves
gh workflow run "Hub Data Sync"            && gh run watch
gh workflow run "Deploy Rise of the Claw Dashboard" && gh run watch
gh workflow run "Live Picks Tracker"       && gh run watch
gh workflow run "QA Market Validation"     && gh run watch   # expect green on a fresh snapshot
curl -sS https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/dashboard/ -o /dev/null -w '%{http_code}\n'
```

## Ordering note

Items 1 and 2 must land **together**. Removing the `peaceiris` publish without adding the dashboard
to `_site` deletes the only route by which the Alpha Engine dashboard could ever reach Pages.
