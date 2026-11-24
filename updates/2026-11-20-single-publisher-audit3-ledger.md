# Single publisher for `audit3_ledger.json` on findtorontoevents.ca

**Date:** 2026-11-20
**Area:** `.github/workflows/audit-dashboard.yml` -- FTP deploy of `/audit/data`
**Base:** `origin/main` @ `dfe83027cc9`

## 1. What was broken

Two workflows published the same artifact to the same URL.

`audit3-ledger.yml` (6-hourly, `23 */6`) generates `audit_dashboard/data/audit3_ledger.json`,
commits it, and deploys `/audit3/` immediately. `audit-dashboard.yml` (3-hourly `10 */3`, ~35 min wall time) never names the file -- its FTP deploy globs `audit_dashboard/data/*.json` straight
to `/{SITE_ROOT}/audit/data` -- so the ledger rode along on a **stale checkout**.

Measured 2026-11-20: `/audit/data/audit3_ledger.json` trailed `/audit3/audit3_ledger.json` by
**222.6 minutes** (8,632 vs 8,769 rows, parity gap 72.3 min). The every-3-hours producer overwrote the 6-hourly producer's fresh bytes with an older copy.

Same root cause as `updates/2026-11-20-audit-publish-stall-and-sleeve-gate-wiring.md` §2, where
this was left as open item 2.

## 2. What changed

One scoped exclusion inside `deploy_findtorontoevents()`, 14 added lines, zero removed:

```python
_PUBLISHED_ELSEWHERE = {"audit3_ledger.json"}
for df in _jsons:
    if df.name in _PUBLISHED_ELSEWHERE:
        print(f"  [{label}] skip {df.name} - published fresh by audit3-ledger.yml")
        continue
```

The file stays in the checkout -- local consumers still read it
(`alpha_engine/money_ready_verdict.py`, `alpha_engine/audit3_denylist.py`,
`tools/audit3_db_sync.py`, `audit3-health.yml`, `audit3-denylist-watchdog.yml`). Only its
**publication** from this workflow is removed. Nothing reads the deployed
`/audit/data/audit3_ledger.json` from inside the runner.

## 3. Why only one of the three sites

`audit-dashboard.yml` deploys to three FTP roots and all three glob `data/*.json`, but
`audit3-ledger.yml` logs in and `cwd`s into `findtorontoevents.ca` **only**.

| Site function | `/audit/data/audit3_ledger.json` before | after |
|---|---|---|
| `deploy_findtorontoevents()` | stale copy, overwrote fresh | **skipped -- fresh copy comes from `audit3-ledger.yml`** |
| `deploy_torontoevent_net()` | only publisher | unchanged (glob left intact) |
| `deploy_tdotevent_ca()` | only publisher | unchanged (glob left intact) |

Skipping on the other two domains would not create a single publisher, it would create
**zero** and freeze those copies. The asymmetry is intentional and commented in the workflow.

## 4. Verification (on `dfe83027cc9`, fresh pinned worktree)

- YAML parses (`jobs = ['generate-and-deploy']`); all 5 embedded python heredocs pass `ast.parse`.
- Semantic checks, all PASS: skip set defined once, membership test once, present in
  `deploy_findtorontoevents()` only, **3** `for df in _jsons:` loops intact, `_critical` set
  (`pf_registry.json` / `money_ready_verdict.json` / `dashboard_data.json`) and the
  `dashboard_data.json`-last ordering untouched.
- Loop emulation over the real `audit_dashboard/data/*.json` (**346** files):
  findtorontoevents.ca now deploys **345** of them with the ledger absent;
  torontoevent.net and tdotevent.ca still deploy all **346** with it present.
- `git diff --stat`: 1 file changed, 14 insertions(+), 0 deletions. No other file touched.

## 5. Merge order -- a dependency, not a preference

**Merge PR #985 first, then this.** #985 adds the replacement publisher (a fresh-ledger upload
to `/audit/data` inside `audit3-ledger.yml`). Landing this change alone would remove the only
updater of `/audit/data/audit3_ledger.json` on findtorontoevents.ca and freeze it -- the exact
opposite of the intent.

## 6. Limitations, stated

1. **One writer now:** if `audit3-ledger.yml`'s FTP credentials are ever absent it warns and
   exits 0 without uploading, so `/audit/data` keeps whatever was there before. A freshness
   assertion on that path would close this.
2. `audit3_verdict_history.json` (present in `audit_dashboard/data`: yes) rides the same
   three globs and has the same two-publisher shape. **Not** changed here -- out of scope for
   this request -- recorded as an open item.
3. `/audit2` remains unpinned and outside `tools/assert_surface_parity.py`.
4. Not deployed and not observed post-merge. The parity gap can only be re-measured after both
   PRs merge and the next 6-hourly run completes.

## 7. Correction (2026-11-20T07:31Z) -- cadence was stated wrong

§1 called this workflow "hourly `:10`". It is **`10 */3 * * *`** -- every 3 hours at :10. The
fix, its scope and all verification results are unaffected: the defect is that two workflows
publish one artifact, which is independent of how often each runs. Corrected there and in
`.github/workflows/audit-dashboard.yml`'s comment, which said a "full 6-hour cycle behind".
