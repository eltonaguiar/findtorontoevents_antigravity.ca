# GitHub Actions patches applied — Pages publisher, deploy retry, hub-sync, QA gate

**Date:** 2026-11-25 · **Branch:** `fix/gha-pages-hub-sync-and-qa-cron` (from `origin/main` @ `d8a96e6ac60`)
**Commits:** `7fa2cd242b9` (QA ledger) · `bd6f9e30de9` (workflows + backups + this record)

> **Ownership note.** `.github/workflows/**` is outside this agent's `owned_prefixes` in
> `tools/agent_ownership.json`. These edits were applied at the operator's explicit instruction
> ("you can proactively fix all those"), which is the reviewed exception the policy provides for.
> They are recorded here so the deviation is auditable, and pre-patch backups are committed.
>
> Side finding: `tools/git_guard_check.py` does **not** exist on `origin/main` (only on the older
> `security/2026-11-25-phishing-cleanup` line), so the pre-commit hook exits 0 there and the
> ownership policy is not actually enforced on main today.

---

## 1. The root cause nobody had named

`deploy-riseoftheclaw.yml` deployed Pages **twice**:

```yaml
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4

      - name: Retry Deploy to GitHub Pages
        if: failure()
        uses: actions/deploy-pages@v4
```

`if: failure()` fires whenever *any* earlier step failed — including the first deploy — and the
second call re-deploys an artifact the first call has already claimed. A second `deploy-pages`
cannot succeed. That is precisely the error in 56 of the last 100 runs:

```
Fetching artifact metadata for "github-pages" in this workflow run
Found 0 artifact(s)
##[error]No artifacts named "github-pages" were found for this workflow run
```

The "retry" was making the failure worse, not recovering from it.

## 2. What changed, file by file

### `live_tracker.yml` — one publisher
Removed the `peaceiris/actions-gh-pages@v4` deploy and its BESTIEJOB staging step, plus the
`pages: write` and `id-token: write` grants. The workflow pushed a 191 KB dashboard to `gh-pages`
hourly while Pages served artifact deployments from `deploy-riseoftheclaw.yml`: the served `/` is a
260-byte redirect to `./hub/`, and `/dashboard/`, `/live_picks.json`, `/bestiejob/` 404ed even
though the branch contained them. The `Commit dashboard` step stays — it is what the real deployer
now reads.

### `deploy-riseoftheclaw.yml` — the single deployer
- Copies `alpha_engine/live_dashboard.html` → `_site/dashboard/index.html`, plus
  `dashboard/big_mover_widget.html`, `dashboard/live_picks.json`, and `docs/bestiejob/` →
  `_site/bestiejob/`. Written with `if [ -f … ]` blocks, not `[ -f … ] && cp …`, because steps run
  under `bash -e` where a false test as the last command fails the step.
- `upload-pages-artifact` v3 → **v4**, given `id: upload`.
- The retry step is **deleted**; a new `Assert a pages artifact was produced` step lists this run's
  artifacts and fails with an explicit message if there is no `github-pages` artifact, and
  `deploy-pages` is gated on `if: steps.artifact.outcome == 'success'`.
- `permissions:` gains `actions: read` for that assertion.

### `hub-sync.yml` — a green run must mean the data moved
- A missing `signal_recorder/export_hub_combos.py` is now an error, and the exporter runs without
  `|| echo "::warning::…"`.
- An unchanged `hub/data/` tree now **fails** instead of printing "No changes".
- New `Assert the hub manifest is fresh` step parses `hub/data/systems_manifest.json` and fails when
  `generated_at` is older than 7 days. It was `2026-03-02T10:00:00Z` on `main` and live.

### `qa-market-validation.yml` — check a fresh snapshot
Cron `13 * * * *` → `30 * * * *`. `picks-now-live-pnl.yml` writes the snapshot at `:25`, so the old
schedule always validated a ~50-minute-old file, which made the 0.5pp per-class tolerance
meaningless: measured today, 31/31 EQUITY published prices matched Finnhub exactly at 19 minutes of
age, while the same comparison at ~53 minutes produced the 8 "mismatches" that failed the gate.

### `tools/qa_ledger.py` — freshness asserted, not assumed
New critical `STALE_SNAPSHOT` flag (`QA_MAX_SNAPSHOT_MIN`, default 90): no parsable `generated_at`,
or a snapshot older than the limit, fails the run with the age in the message. The tracker writes
hourly, so 90 minutes means at least one cycle was missed. The summary line now prints the snapshot
age and the limit.

## 3. Backups

`reports/backups/2026-11-25-workflows-pre-patch/` — verbatim pre-patch copies of all four workflow
files plus a README with the restore command. `tools/qa_ledger.py`'s pre-patch content is commit
`547a00db1bb:tools/qa_ledger.py`.

## 4. Verification

| Check | Result |
|---|---|
| `python3 tools/qa_ledger_selftest.py` | **32/32 pass**, exit 0 (age parsing, demoted vs actionable blanks, stale drift, divergence, fresh mismatch, staleness assertion ×3, and the pre-existing self-inconsistency / unpriced / quarantine guards) |
| `yaml.safe_load` on all four workflows | all parse; cron values confirmed (`:24`, `:49,19`, `:6`, `:30`) |
| `actionlint` | not installed in this environment — **not run** |
| Patch application | applied by string replacement, then re-read and re-parsed |

### End-to-end run of the patched gate (real data, real feeds)

The patched `tools/qa_ledger.py` was run locally against the **same** `origin/main` snapshot the
scheduled job failed on (183 picks), with all quotes fetched live rather than stubbed — 181 unique
`(symbol, class)` keys prefetched across BOND/COMMODITY/EQUITY/ETF/FOREX:

```
QA ledger: 183 picks from a snapshot 37 min old (limit 90 min), 0 flags (0 critical)
  BOND             n=   54 ... quar=1
  EQUITY           n=   31 ... blank_tp/sl=0 demoted=6 mismatch=0 stale=0 div=0 self=0
  ETF              n=   72 ...
  FOREX            n=   23 ...
EXIT_CODE = 0
flags {'total': 0, 'critical': 0}
```

Against the previous code the identical inputs produced `14 flags (8 critical)` and exit 1. The 6
demoted EQUITY rows are counted (`demoted=6`) and no longer flagged; no row was hidden.

**Still not confirmed:** the *scheduled workflow* going green. That needs the branch on `main`, and
this environment cannot dispatch it safely — the workflow's final `Commit the QA artifact` step runs
`git push origin HEAD:main`, which from a branch run would push the branch itself onto main. The
confirmation step after merge is simply to watch the `:30` run.
