# Edge-Stability Cron Wire Audit — 2026-05-31

## Finding: Already wired (PR #285 merged earlier today)

The blackbox's premise — that no cron regenerates `edge_stability_index.json` — was correct as of the snapshot they took (`as_of: 2026-05-12`), but a workflow has since been authored and merged to main on 2026-05-31 21:07 UTC. The gap is closed; first scheduled run will fire 2026-06-01 00:30 UTC.

## 1. Generator script

- Path: `tools/edge/edge_stability.py`
- Entry: `python -m tools.edge.edge_stability --all`
- Args: `--class <ASSET_CLASS>` | `--all` | `--out <dir>`
- Output dir: `audit_dashboard/data/edge_stability/` (writes `edge_stability_index.json` + per-class `edge_stability_<CLASS>.json`)
- Input dependency: reads `audit_trail/data/dashboard_payload.json` (fetched from live site in the workflow)

## 2. Existing workflows

`grep -ln edge_stability .github/workflows/*.yml`:
- `.github/workflows/audit-dashboard.yml` (uses the JSONs, doesn't regenerate)
- `.github/workflows/edge-stability-refresh.yml` (NEW — merged via PR #285 commit `b1f817e93`)

## 3. Workflow YAML (already in main)

```yaml
name: Edge stability refresh
'on':
  schedule:
    - cron: '30 0 * * *'  # daily 00:30 UTC
  workflow_dispatch:
permissions:
  contents: write
jobs:
  refresh:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v6
        with:
          token: ${{ secrets.GH_PAT || github.token }}
      - uses: actions/setup-python@v6
        with:
          python-version: '3.11'
      - name: Fetch live dashboard_payload.json
        run: |
          mkdir -p audit_trail/data
          curl -fsSL --retry 3 -o audit_trail/data/dashboard_payload.json \
            https://findtorontoevents.ca/audit/data/dashboard_payload.json
      - name: Regenerate edge_stability per asset class
        run: python -m tools.edge.edge_stability --all
      - name: Commit refreshed JSONs
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add audit_dashboard/data/edge_stability/*.json
          git diff --cached --quiet || git commit -m "chore(edge-stability): daily refresh [skip ci]"
          git push
```

## 4. Self red-team

- Entry command matches `--help` output. PASS.
- No DB creds needed — script consumes `audit_trail/data/dashboard_payload.json` over HTTPS from the live site (cleaner than DB; no AUDIT_DB_PASS required). PASS.
- Output path matches what `audit_dashboard/edge_stability.html` and the live `/audit/data/edge_stability/` directory expect. PASS.
- Cron `30 0 * * *` is valid 5-field syntax. PASS.
- `permissions: contents: write` + `GH_PAT || github.token` ensures push works. PASS.
- Timeout 15m is appropriate (script reads a single JSON and aggregates).
- One residual risk: cron will not have fired yet (merged 21:07 UTC, next trigger 00:30 UTC). Operator should run `workflow_dispatch` to verify the first invocation succeeds end-to-end before relying on the schedule.

RT verdict: **PASS** (with the manual-dispatch follow-up recommended).

## 5. PR

Already merged: **PR #285** (`ci/edge-stability-daily-refresh` -> main, commit `b1f817e93`). No new PR opened — the work is done.

## 6. +313% provenance grep

`grep -rn "313\.43\|313%\|rolling_100" --include="*.py" --include="*.json" --include="*.html"` against `audit_dashboard/` and `reports/` returned **no match** for the exact figure "+313.43%" or "+313%" in any dashboard JSON, HTML, or report. Hits in worktrees were unrelated (hyperliquid whale ROI tag `whale_35M_313roi`, EMA exit prices `313.4xxxx`, position values).

Source not found in canonical paths. If the figure is appearing live on `/audit/edge_stability.html`, it is either (a) computed client-side from the rolling pnl series in `edge_stability_<CLASS>.json`, or (b) carried in a payload field not named with "313". Recommend the blackbox supply the exact URL + DOM selector so the field can be traced; cannot resolve provenance from grep alone.

Provenance: **not_found**.
