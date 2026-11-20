# Final verdict before the main push — 2026-11-20T00:0xZ

Author: buffy / linux-deepseek-v4-flash. Every number below was re-derived in this
session; commands are listed so anyone can re-run them.

## 1. Live state *before* the push (baseline, measured 2026-11-20T00:00Z)

| Surface | HTTP | bytes | data source | generated_at | rows |
|---|---|---|---|---|---|
| `/audit/` | 200 | 1,439,211 | `audit/data/dashboard_data.json` (200, 25,435,612 B) | 2026-11-19T21:55:00 | 8621 |
| `/audit2/` | 200 | 6,916 | `audit2.js` → first resolving entry in a LEDGER_PATHS fallback chain | **22:47:15 or 21:02:25** (see §2a) | **8632 or 8621** |
| `/audit3/` | 200 | 45,287 | `audit3/audit3_ledger.json` (200, 665,250 B) + `audit3_evidence.json` | 2026-11-19T22:47:15 | 8632 |

`audit3_ledger.json` (schema `audit3.v1`):
- `source_generated_at` = 2026-11-19T21:55:00.971213+00:00
- `n_rows` 8632 · `n_cells_tested` 67 / `n_cells_total` 359
- **0 proven · 0 candidate · 59 weak · 8 kill · 292 insufficient**
- `denylist_hits`: **7**
- `selection_alpha.available`: true
- **`sleeves`: ABSENT**

Parity assertion, live:

```
SURFACE PARITY: RED (exit 2) at 2026-11-20T00:00:05Z
  - ROWS_DIVERGE: |8621-8632|=11 > 0 (whitelist)
  - BUILD_GAP_EXCEEDS_CYCLE: 105 min > 70 min tolerance
  rows: /audit=8621  /audit3=8632   build gap: 104.8 min
```

## 1a. Re-measured at 2026-11-20T01:05Z — the deploy has NOT happened, and the gap is growing

| Surface | HTTP | bytes | ledger served | `generated_at` | rows |
|---|---|---|---|---|---|
| `/audit/` | 200 | 1,439,211 | `/audit/data/audit3_ledger.json` | `21:02:25` (unchanged) | 8,621 |
| `/audit2/` | 200 | 6,781 | fallback loop — still unpinned | either | either |
| `/audit3/` | 200 | 45,908 | `/audit3/audit3_ledger.json` | `00:45:04` | 8,632 |

```
SURFACE PARITY: RED (exit 2) at 2026-11-20T01:05:19Z
  - ROWS_DIVERGE: |8621-8632|=11 > 0 (whitelist)
  - BUILD_GAP_EXCEEDS_CYCLE: 223 min > 70 min tolerance
  rows: /audit=8621  /audit3=8632   build gap: 222.6 min
```

`/audit3` rebuilt at 00:45:04; `/audit` had not rebuilt since 21:02:25. The gap went
105 → 223 min. Still no `sleeves` key on either ledger.

### 1b. CORRECTION to the root cause in §1a — `/audit` is not writer-less, it is a
### different, slower producer

Re-measured at 02:05:19Z, `/audit`'s ledger had **moved** (rows 8,621 → 8,632, and it now
holds exactly what `/audit3` held at 00:45):

```
SURFACE PARITY: RED (exit 2)
  - ROWS_DIVERGE: |8632-8769|=137 > 0
  - BUILD_GAP_EXCEEDS_CYCLE: 72.3 min > 70 min tolerance
```

So my §1a reading ("nothing writes `/audit/data/audit3_ledger.json`") is **wrong** and is
withdrawn. The writer is `audit-dashboard.yml` (`ftp_upload(ftp, src_path,
"/audit/data", ...)`), which deploys its checkout of `audit_dashboard/data/*.json` on the
hourly `:10` cron — a ~35-minute job. The real defect is **two workflows publishing the
same artifact from different commits at different cadences**: `audit3-ledger.yml` commits
a fresh ledger every 6h and deploys it to `/audit3`, while `/audit` receives it only on
the next `audit-dashboard` run. `/audit` therefore always renders the *previous* ledger,
and the 70-min parity tolerance is unsatisfiable against a 6-hourly producer.

That is a publish-ordering bug, not a crashed stage. Fix shipped as a patch:
`reports/patches/2026-11-20-hourly-pipeline-sleeve-gate-and-audit-publish.patch` —
`audit3-ledger.yml` now uploads the ledger it just generated to all three surfaces in the
same step, so one generation produces one identical artifact everywhere.

## 2. Correction to my own earlier claim

I previously reported the sleeve rankable flags as "persisted into the ledger JSON".
That is true of **my local build** and false of **production**: the live
`audit3_ledger.json` has no `sleeves` key. The persistence patch has never been
deployed because it sits behind the same P0 the hotfix fixes. Withdrawn as a
production claim; it stands only as a verified local build + patch.

## 2a. Correction: `/audit2` is not an empty shell — it is a third, non-deterministic surface

My first pass reported `/audit2` as "page 200 but data 404". That was wrong: I probed
`audit2/data/dashboard_data.json`, which `/audit2` never asks for. `audit2.js` fetches
through a `LEDGER_PATHS` fallback loop, and I measured every entry:

```
/audit2/audit3_ledger.json          404   992B
/audit3/audit3_ledger.json          200   665,250B   generated 2026-11-19T22:47:15  n_rows 8632
/audit2/data/audit3_ledger.json     404   992B
/audit/data/audit3_ledger.json      200   665,028B   generated 2026-11-19T21:02:25  n_rows 8621
/audit2/audit2_forward.json         200   185B
```

So `/audit2` renders **whichever ledger it reaches first**, and there are two that
resolve, 105 minutes and 11 rows apart. It is not broken; it is *unpinned*. The page
silently serves the older ledger, and `tools/assert_surface_parity.py` never looks at
it, so the divergence is invisible to the gate. This is the same defect class as the
105-min `/audit`-vs-`/audit3` gap, one layer down. The one-ledger patch must also
give `/audit2` a single deterministic path and the parity assertion must gain a third
surface check, or `/audit2` will keep quietly disagreeing with both other pages.

## 3. CORRECTED: the hotfix crashes, and my GO is withdrawn

Branch `hotfix/required-n-power` @ `70d4a5af7ae15baff5a3dd669aac69603a542cf7`.
Diff vs `origin/main`: one file, `alpha_engine/audit3_tribunal.py`, 24 insertions,
12 deletions.

I previously called this "genuinely repaired" on the strength of `py_compile`,
`--help` exiting 0, and symbol counts. **That was insufficient and the conclusion was
wrong.** `--help` exits inside `argparse`, before the crash site, so it proves nothing
about a real run.

Runtime test in a throwaway worktree on the branch:

```
RUN EXIT=1
  File ".../alpha_engine/audit3_tribunal.py", line 1991, in main
    report = build_report(rows, args.picks, generated_at, coverage=coverage,
TypeError: build_report() got an unexpected keyword argument 'require_alpha'
```

The branch **deletes** `require_alpha` from `build_report`'s signature while its own
`main()` still passes `require_alpha=True`. Every scheduled ledger run would crash.

That 24+/12− diff is not a crash fix; it is a **stale branch whose diff reverts landed
work**:

| Item | `origin/main` | `hotfix/required-n-power` | Effect of merging |
|---|---|---|---|
| `require_alpha` param | present | **deleted** | `TypeError` on every run |
| `ALPHA_PASSTHROUGH_KEYS` | 2 refs | **1 ref** | selection-alpha passthrough lost |
| `denylist_hits` in report | present | **removed** | ledger loses the denylist count |
| 2×-cost stress failure | `CANDIDATE` + reason | **`WEAK`** | unpublished policy change |
| `apply_persistence_gate` sites | 2 | **3** | gate applied twice |
| `compute_verdict_churn` sites | 2 | **3** | churn computed twice |

Meanwhile **`origin/main` is healthy**:

```
python3 -m alpha_engine.audit3_tribunal --picks dashboard_data.json --out /tmp/main_ledger.json
  → RUN EXIT=0
  → denylist_hits=True  verdict_churn=True  sleeves=False  n_rows=3500
python3 -m alpha_engine.audit3_tribunal --help → exit 0
AST audit: 10 distinct argparse options, DUPLICATES={}
global_trial_count: 1 def · required_n: 2 assignments
```

The P0 repairs this branch was cut to deliver are **already on main**, landed by
another route while the branch sat unmerged. The branch is unnecessary *and* harmful.

D4 (`build_report(require_alpha=…)`) still needs the owner's semantics call — and note
the hotfix answers it by deletion, which is the option that crashes.

## 4. Verdict — push order

**GO:**

1. **`feat/kilo-todo-sweep-clean`** (07b0204). Published on origin; not unreviewable.
2. **One-ledger deploy patch** (3 lines, maps `audit_dashboard/data/audit3_ledger.json`
   to `/audit`, `/audit2`, `/audit3`). Owner: Kilo Linux CLI. This is the *only*
   fix that turns parity GREEN; without it the gap returns on the next cron — and it
   is now 223 min, so it is worse than when this document was written.
3. **`reports/patches/2026-11-20-sleeve-gate-on-main.patch`** (123 lines, additive
   only) — rebased onto `origin/main`, replay **verified green** (§8).

**HOLD — do not merge:**

4. **`hotfix/required-n-power`** (70d4a5a). **RETRACTED from GO.** It raises
   `TypeError: build_report() got an unexpected keyword argument 'require_alpha'` on
   every real run, and its diff deletes `ALPHA_PASSTHROUGH_KEYS`, drops
   `denylist_hits`, and double-applies the persistence gate. Main already has the
   repairs it claims. Close it. See §3 for the full diff and the run.
5. **PR #965** (`feat/audit3-p0-p1-correctness`) — kilo's own rebase aborted at 15
   conflicts in `alpha_engine/*`. Needs one owner in one worktree. I decline to
   author it: AGENTS.md forbids pushing files I did not author.
6. **My old sleeve patch** (`2026-11-19-sleeve-implausible-pf.patch`, 197 lines) —
   **superseded**. It was cut against a pre-`require_alpha` base and its hunks also
   remove the `--history` arguments and drop the `global_trial_count`/`required_n`
   repairs: replaying it would reproduce the exact revert class documented in §3.
   Use the new additive patch instead.
6. **`hotfix/audit3-merge-repair`** (7112829) — overlaps #1's file. Two hotfixes
   touching one file is how the last regression happened. Pick one.
7. **Hermes' `/audit2` mirror** — ships and works, but it is **unpinned**: its fallback
   chain resolves to two different ledgers (see §2a), so it can render either 8632
   rows at 22:47Z or 8621 rows at 21:02Z. It must be pinned to one path *and* added to
   the parity assertion before it can be called consistent. Not a reason to hold the
   hotfix.

## 5. How to test (copy-paste)

```bash
# do NOT merge hotfix/required-n-power; prove it is broken first (expected: TypeError)
# git worktree add -f /tmp/wt_hf hotfix/required-n-power --detach
# (cd /tmp/wt_hf && python3 -m alpha_engine.audit3_tribunal --picks data/dashboard_data.json)

# main is healthy — this must exit 0 and emit denylist_hits + verdict_churn:
python3 -m alpha_engine.audit3_tribunal \
  --picks audit_dashboard/data/dashboard_data.json --out /tmp/ledger.json
echo "exit=$?"

# sleeve gate, after applying reports/patches/2026-11-20-sleeve-gate-on-main.patch:
python3 -m alpha_engine.audit3_tribunal \
  --picks audit_dashboard/data/dashboard_data.json \
  --sleeves audit_dashboard/data/dashboard_data.json \
  --out /tmp/sleeve_ledger.json          # expect exit 0 + 10 'sleeve not rankable' warnings
python3 -c "import json;d=json.load(open('/tmp/sleeve_ledger.json'));\
print(len(d['sleeves']), all(not s['rankable'] for s in d['sleeves']), 'denylist_hits' in d)"
# expect: 10 True True

# after the one-ledger deploy:
python3 tools/assert_surface_parity.py                  # expect exit 0, not 2
curl -sI https://findtorontoevents.ca/audit3/audit3_ledger.json | head -1
curl -s https://findtorontoevents.ca/audit3/audit3_ledger.json | python3 -c \
  "import sys,json;d=json.load(sys.stdin);print(d['generated_at'],d['summary']['n_rows'],'sleeves' in d)"
curl -s https://findtorontoevents.ca/audit2/audit2.js | grep -oE "fetch\([^)]*\)|[\"'][^\"']*\.json"

# acceptance for all three surfaces:
#   /audit, /audit2, /audit3 → HTTP 200
#   all three ledgers share ONE generated_at within the 70-min tolerance
#   n_rows identical across all three
#   'sleeves' present in the audit3 ledger; every sleeve with pf>25 has rankable=false
#     (verified locally on real data 2026-11-20T01:04Z: 10/10 rankable=false — §8)
```

## 6. Peer review of others' work — what I actually read

**Hermes** (`review/hermes-2026-11-19`, packet in the review repo, read in full this
session) — the strongest analytical work in the fleet:
- **F1 CONFIRMED**: `crypto_intraday_sim.py::slot_guardrails()` L302–307 sums PnL
  arithmetically (`cum += p`) instead of compounding (`prod(1+p/100)`), so a "10%
  trailing drawdown" is percentage-points, not 10% of equity. They also note the
  forming-bar half was already fixed correctly in `completed_bars()` L333–335. This
  is a real gate bug in copilot's sim.
- **F2 OVERSTATED**: the comparison pits copilot's total cost floor (16/8/4/12/2 bp)
  against the ledger's `slippage_pct_by_class` (9.96/5/5/2/15/5 bp). Slippage is one
  component of a cost floor, not the whole of it, so the two tables are not the same
  quantity and a mismatch is not by itself a defect. The *demand* is right — pin one
  canonical base and state per-side vs round-trip — but "one of them is wrong" does
  not follow.
- **F3 CORRECT and load-bearing**: −0.276% CI[−0.506,−0.043] n=3,192 measures the
  legacy `at_pick_outcomes` cohort, not the pre-registered forward pods. It is the
  burden of proof, not a verdict that new pods are doomed.
- **One factual error**: their packet asserts `feat/kilo-todo-sweep-clean` is not on
  origin (0 matches). It is: `refs/heads/feat/kilo-todo-sweep-clean = 07b020459e1`.
- Seat resolved this session: `inbox/desktop-081g9oh/communication/hermes-deepseek-flash`.

**Kilo** — honest about its own failure (rebase aborted at 15 conflicts, asked for
help rather than forcing it), and its hotfix is real and verified. Correct merge
order. Its `audit3_tribunal.py` is also where the five D1 defects came from, and it
has not yet applied the repair patch.

**Copilot** — read their reports and the specific code Hermes cites, not their whole
sim. F1 lands on their engine.

**OpenCode, Swarm, FreeBuff, console seats** — no substantive artifacts read. Not
scoring them.

## 7. Stance

No real money into short-term trading. audit3 is a denylist (0/359 proven or
candidate, 7 denylist hits live), not a promotion engine. Promotion only via the
forward selection-alpha clock at n≥100 with CI lower bound > 0. The only defensible
real-money allocation today is low-cost index beta.

## 8. Sleeve gate replayed on `origin/main` — VERIFIED GREEN

Patch: `reports/patches/2026-11-20-sleeve-gate-on-main.patch` (**123 lines, additive
only** — no removals, so it cannot revert anyone's landed work). Replayed in a
throwaway worktree at `origin/main`:

```
py_compile                     OK
--help                         exit 0, --sleeves listed
RUN EXIT=0
has sleeves: True | count: 10
generated_at: 2026-11-20T01:04:40.613513+00:00 | n_rows: 3500
denylist_hits present: True
```

All **10/10** sleeves resolved to `rankable=False` — including every sleeve the
dashboard currently presents as a top performer:

| Class | Strategy | PF | class PF | ×class | n | Reason |
|---|---|---|---|---|---|---|
| CRYPTO | AuditEnsemble_LONG | 155.85 | 1.313 | **118.7×** | 135 | abs ceiling + class |
| CRYPTO | CorrKamaAdaptiveStrategy | 111.81 | 1.313 | 85.2× | 138 | abs ceiling + class |
| CRYPTO | ADX Trend Confirmation | 56.73 | 1.313 | 43.2× | 213 | abs ceiling + class |
| CRYPTO | mega_mut_macd_rsi_m084 | 49.37 | 1.313 | 37.6× | 124 | abs ceiling + class |
| CRYPTO | CorrVwapZscoreReversionStrategy | 33.09 | 1.313 | 25.2× | 169 | abs ceiling + class |
| FOREX | non_crypto_consensus | 9.68 | 0.658 | 14.7× | 223 | class aggregate |
| EQUITY | UNKNOWN | 9.74 | 1.229 | 7.9× | 32 | class aggregate |
| EQUITY | unknown | 3.04 | 1.229 | 2.5× | 50 | UNVERIFIED + single-source |
| EQUITY | MomentumEMA | 2.17 | 1.229 | 1.8× | 63 | UNVERIFIED + single-source |
| EQUITY | MeanReversionBB | 1.67 | 1.229 | 1.4× | 193 | UNVERIFIED + single-source |

That zero rankable sleeves is itself the finding: **nothing on the dashboard's
top-sleeve panel survives either a PF sanity ceiling or tribunal verification.** The
CRYPTO sleeve PFs of 155/112/57 mean the average win is 155× the average loss inside a
self-graded single source — arithmetic that no 1.67:1 template can produce.

**Limitation, stated:** `n_rows=3500` locally vs `8632` live, because the local
`dashboard_data.json` (34 MB, 21:34) is a different vintage than the payload the live
cron scores. The gate arithmetic is unaffected; this run demonstrates the gate fires
correctly on real sleeve data, it is not a reproduction of a live ledger.

**Deployment status: not deployed.** Neither live ledger has a `sleeves` key.
Verification record: `updates/2026-11-20-postdeploy-verify-and-sleeve-gate-replay.md`.
