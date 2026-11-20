# 2026-11-20 — /audit publish stall + sleeve gate wired into the hourly pipeline

**Agent:** linux-deepseek-v4-flash
**Branch basis:** `origin/main` @ `b62624b39d5`
**Delivered as:** `reports/patches/2026-11-20-hourly-pipeline-sleeve-gate-and-audit-publish.patch` (393 lines, 3 files)
**No shared source file in the main tree was edited. The patch is the deliverable.**

---

## 1. What was asked

1. Find out why `/audit` stopped rebuilding at 21:02 and fix the stall so it cannot drift
   multiple build cycles behind `/audit3`.
2. Wire the sleeve gate into the hourly audit pipeline so implausible-PF sleeves are
   flagged on every rebuild.
3. Harden the pre-push check so a branch that compiles but crashes at runtime cannot be
   called verified.

## 2. What was broken

### 2.1 The `/audit` stall — and the wrong root cause I reported first

**Measured at 01:05Z:** `/audit` served `generated_at 2026-11-19T21:02:25`, 8,621 rows,
while `/audit3` served `00:45:04`, 8,632 rows. Parity `RED (exit 2)`, build gap
**222.6 min**. My first read was "no workflow writes `/audit/data/audit3_ledger.json`".

**That was wrong.** Re-measured at 02:05Z the same file had moved — rows 8,621 → 8,632,
exactly the content `/audit3` had rendered at 00:45:

```
SURFACE PARITY: RED (exit 2) at 2026-11-20T02:05:19Z
  - ROWS_DIVERGE: |8632-8769|=137 > 0 (whitelist)
  - BUILD_GAP_EXCEEDS_CYCLE: 72.3 min > 70 min tolerance
```

The writer exists: `audit-dashboard.yml` uploads its checkout of
`audit_dashboard/data/*.json` to `/audit/data` on the hourly `:10` cron, and that job
takes ~35 minutes. The actual defect is a **publish-ordering split**:

| Artifact | Produced by | Cadence | Publishes to |
|---|---|---|---|
| `audit3_ledger.json` | `audit3-ledger.yml` | 6-hourly `23 */6` | `/audit3/` — fresh, immediately |
| same file | `audit-dashboard.yml` | hourly `:10`, ~35 min job | `/audit/data/` — one generation later |

`/audit` is therefore fed by a slower consumer of the *same* file, so it always renders
the **previous** ledger, and the 70-minute parity tolerance is **unsatisfiable** against a
6-hourly producer. It is not a crashed stage; it is two publishers racing on one artifact.
When the dashboard job backlogged, the lag reached 223 minutes — several build cycles.

### 2.2 The sleeve gate was hand-run only

`.github/workflows/audit3-ledger.yml` invoked the tribunal with `--picks`, `--alpha` and
`--history`, but never `--sleeves`. The gate existed as a patch and a local proof and
nothing else, so an implausible PF (155, 112, 57, 49, 33 on CRYPTO) could sit on the page
indefinitely. `origin/main`'s tribunal has **0** occurrences of `sleeves`.

### 2.3 Verification was satisfiable without running anything

The `hotfix/required-n-power` episode: `py_compile` OK, `--help` exit 0, and it was
recommended for merge. Its first real invocation dies with
`TypeError: build_report() got an unexpected keyword argument 'require_alpha'` at
`alpha_engine/audit3_tribunal.py:1991`. `--help` exits inside `argparse`, before `main()`
builds a report, so it cannot see the defect. There was no tool in the repo that ran the
thing.

## 3. What was changed

One patch, three files. **One deletion line total** (the invocation line being replaced);
everything else is additive, so it cannot revert another agent's landed work.

### 3.1 `.github/workflows/audit3-ledger.yml` (+2,092 bytes; 15,023 → 17,115)

**(a) Publish to every surface in the same step.** The deploy step ended after uploading
`/audit3/` and `/audit2/`. It now continues to `/audit/data/` and uploads the ledger it
*just generated*, so one generation produces one identical artifact on all three
surfaces instead of waiting for the hourly dashboard job:

```python
ftp.cwd("..")
ftp.cwd("audit")
try:
    ftp.mkd("data")
except ftplib.error_perm:
    pass
ftp.cwd("data")
with open("audit_dashboard/data/audit3_ledger.json", "rb") as f:
    ftp.storbinary("STOR audit3_ledger.json", f)
```

**(b) Run the sleeve gate on every rebuild.** The build step passes `--sleeves`, but only
after probing the CLI:

```bash
sleeves_arg=""
if python3 -m alpha_engine.audit3_tribunal --help 2>&1 | grep -q -- "--sleeves"; then
  sleeves_arg="--sleeves /tmp/audit3/dashboard_data.json"
else
  echo "::warning title=audit3::sleeve gate NOT wired — ... apply reports/patches/2026-11-20-sleeve-gate-on-main.patch"
fi
```

The probe is deliberate: this workflow and `audit3_tribunal.py` are owned separately, and
an unreachable option would abort the build with `unrecognized arguments`. Once the sleeve
patch is merged the probe succeeds and the gate is live with no further change. Until
then the build prints a `::warning` naming the patch to apply — inert, but never silent.

**(c) Assert the gate fired and never published a fantasy PF.** Added to the existing
ledger assertion block, so a regression fails the build instead of shipping:

```python
sl = d.get("sleeves")
if sl is None:
    print("::warning title=audit3::no 'sleeves' block — implausible-PF gate is inert")
else:
    rankable = [x for x in sl if x.get("rankable")]
    bad = [x for x in rankable if float(x.get("pf") or 0) > 25.0]
    assert not bad, f"implausible-PF sleeve published as rankable: {bad}"
```

### 3.2 `alpha_engine/audit3_tribunal.py`

The sleeve-gate patch from the previous round, unchanged and additive
(`reports/patches/2026-11-20-sleeve-gate-on-main.patch`, 123 lines) so the pipeline wiring
above has something to call.

### 3.3 `tools/assert_tribunal_runs.py` (NEW, 236 lines)

The pre-push gate. It runs the tribunal for real — on real picks, in a throwaway worktree
when `--ref` is given — and fails unless the run exits 0 and emits `schema`,
`generated_at`, `summary`, `coverage`, `denylist_hits`, with `n_rows >= 100`.

```
python3 tools/assert_tribunal_runs.py                       # this tree
python3 tools/assert_tribunal_runs.py --ref origin/main
python3 tools/assert_tribunal_runs.py --ref hotfix/x --expect-fail
python3 tools/assert_tribunal_runs.py --require-sleeves      # also demand the gate output
```

`--help` is recorded but explicitly labelled informational — it is the check that produced
the bad GO, so it is never allowed to decide the verdict. `--expect-fail` inverts the
result so a known-broken ref can be pinned as a regression case.

## 4. How it was verified

```
# patch is clean against origin/main
git worktree add -f /tmp/wt_chk origin/main --detach
git apply --check reports/patches/2026-11-20-hourly-pipeline-...patch   → OK
git apply ...  → deploy uploads /audit/data: True
                 build passes --sleeves:   True
                 tool present:             True

# workflow is structurally valid
yaml.safe_load(...)                → OK, 11 steps
bash -n on the edited build block  → exit 0
compile() on the deploy heredoc    → OK

# the run the workflow now performs (patched tribunal, real 34 MB payload)
python3 -m alpha_engine.audit3_tribunal --picks <picks> --sleeves <picks> --out /tmp/pipe_ledger.json
  RUN EXIT=0
  sleeves: 10  rankable: 0  flagged: 10  implausible-but-rankable: 0
  denylist_hits present: True  |  n_rows: 3500

# the smoke gate PASSES healthy main
python3 tools/assert_tribunal_runs.py            → real run exit=0, verdict PASS, EXIT=0

# the smoke gate CATCHES the branch that broke this rule
python3 tools/assert_tribunal_runs.py --ref hotfix/required-n-power \
        --picks <picks> --expect-fail
  help      exit=0   (informational)
  real run  exit=1   TypeError: build_report() got an unexpected keyword argument 'require_alpha'
            File ".../alpha_engine/audit3_tribunal.py", line 1991, in main
  verdict: FAIL (expected FAIL)   EXIT=0
```

That last block is the point of the whole change: the exact branch I wrongly approved is
now rejected by an automated check, on the exact line, without a human remembering why.

## 5. Limitations — stated, not hidden

- **The patch is not applied to any tracked file.** It exists as a diff against
  `origin/main` @ `b62624b39d5` for the owners of those files to apply. Nothing deployed.
- **The sleeve gate stays inert until `alpha_engine/audit3_tribunal.py` is patched.** The
  workflow probes for `--sleeves` and warns by name if it is missing; it does not silently
  claim the gate ran.
- **`audit-dashboard.yml` still uploads its own copy of `audit3_ledger.json` to
  `/audit/data`.** After this patch two publishers write that path. Because both deploy
  from `main` and `audit3-ledger.yml` commits before it deploys, the newest bytes win in
  practice — but a dashboard run whose checkout predates a concurrent ledger commit can
  still overwrite with older bytes for one cycle. Removing that second upload is a
  follow-up in a file I do not own (`audit-dashboard.yml`).
- **`/audit2` is still unpinned.** It renders whichever entry of its fallback chain
  resolves first, and `tools/assert_surface_parity.py` does not check it. Unchanged here.
- **`n_rows=3500` locally vs ~8,769 live**, because the local 34 MB `dashboard_data.json`
  is a different vintage than the live payload the cron fetches. The gate arithmetic and
  the wiring are unaffected; this is not a reproduction of a live run.

## 6. Recommended next action

1. Apply the combined patch. It is three files, one deletion line, and it fixes the
   publish split and wires the gate in the same commit.
2. Delete the `audit3_ledger.json` upload from `audit-dashboard.yml` so exactly one
   workflow owns that artifact (owner: Kilo Linux CLI).
3. Pin `/audit2` to a single ledger path and add it to `assert_surface_parity.py`.
4. Run `python3 tools/assert_tribunal_runs.py --ref <branch>` before any future GO.
