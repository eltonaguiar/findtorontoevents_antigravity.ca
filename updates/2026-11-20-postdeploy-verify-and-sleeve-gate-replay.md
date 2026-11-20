# 2026-11-20 — Post-deploy verification + sleeve-gate replay (and a withdrawn GO)

**Agent:** linux-deepseek-v4-flash
**Scope:** read-only measurement of the three live surfaces; one new patch file; explicit withdrawal of a prior recommendation.
**Nothing in this document was deployed. No shared file was edited.**

---

## 1. What was asked

1. Verify the deploy on `findtorontoevents.ca/audit`, `/audit2`, `/audit3`.
2. Replay the sleeve implausible-PF gate.

## 2. What was broken (finding)

### 2.1 The deploy has not happened, and the gap it was meant to close has widened

Measured `2026-11-20T01:05:19Z`:

| Surface | HTTP | bytes | ledger served | `generated_at` | rows |
|---|---|---|---|---|---|
| `/audit/` | 200 | 1,439,211 | `/audit/data/audit3_ledger.json` | `21:02:25` | 8,621 |
| `/audit2/` | 200 | 6,781 | fallback loop — unpinned | either | either |
| `/audit3/` | 200 | 45,908 | `/audit3/audit3_ledger.json` | `00:45:04` | 8,632 |

`tools/assert_surface_parity.py` → **RED, exit 2**:

```
ROWS_DIVERGE: |8621-8632|=11 > 0 (whitelist)
BUILD_GAP_EXCEEDS_CYCLE: 223 min > 70 min tolerance — /audit renders a 223-minute-old ledger
```

At 00:00Z the gap was 104.8 min. It is now **222.6 min** and growing: `/audit3` rebuilt at
00:45:04, `/audit` did not rebuild at all (still 21:02:25). `/audit` is drifting multiple build
cycles behind, so this is no longer "a rebuild in flight" — it is a stalled publish target.

`/audit2` remains unpinned: `/audit2/audit3_ledger.json` and `/audit2/data/audit3_ledger.json` both
404, so `audit2.js` falls through to `/audit3/` (8,632 rows) or `/audit/` (8,621 rows) depending on
which fetch wins. Two populations, one page, no disclosure.

**Neither ledger contains `sleeves`.** The gate has never been published.

### 2.2 `hotfix/required-n-power` is unsafe to merge — my prior GO is withdrawn

I previously recommended fast-tracking `hotfix/required-n-power` (`70d4a5af7ae`) to main. **That
recommendation was wrong and is withdrawn.**

Evidence that my earlier verification was insufficient: I checked `py_compile`, `--help`, and symbol
counts. `--help` exits during `argparse` parsing, *before* the crash site, so it proves nothing about
a real run.

Runtime test in a throwaway worktree on the branch:

```
RUN EXIT=1
  File "/tmp/wt_hf/alpha_engine/audit3_tribunal.py", line 1991, in main
    report = build_report(rows, args.picks, generated_at, coverage=coverage,
TypeError: build_report() got an unexpected keyword argument 'require_alpha'
```

The branch **deletes** `require_alpha` from `build_report`'s signature while its own `main()` still
passes `require_alpha=True`. Every scheduled ledger run would crash.

`git diff origin/main hotfix/required-n-power -- alpha_engine/audit3_tribunal.py` (24+/12−) is not a
crash fix. It is a diagnostic of a **stale branch whose diff reverts landed work**:

| Item | `origin/main` | `hotfix/required-n-power` | Effect of merging |
|---|---|---|---|
| `require_alpha` param | present | **deleted** | `TypeError` on every run |
| `ALPHA_PASSTHROUGH_KEYS` | 2 refs | **1 ref** | selection-alpha passthrough lost |
| `denylist_hits` in report | present | **removed** | ledger loses the denylist count |
| 2×-cost stress failure | `CANDIDATE` + reason | **`WEAK`** | unpublished policy change |
| `apply_persistence_gate` call sites | 2 | **3** | gate applied twice |
| `compute_verdict_churn` call sites | 2 | **3** | churn computed twice |

Meanwhile `origin/main` is **healthy**: `python3 -m alpha_engine.audit3_tribunal --picks
dashboard_data.json` exits **0** and emits `denylist_hits=True`, `verdict_churn=True`, `sleeves=False`.
Main's `--help` also exits 0 with no duplicate `add_argument` options (AST-verified: 10 distinct
options, `DUPLICATES={}`). The P0 repairs this branch was cut to deliver are **already on main**
(`global_trial_count` 1 def, `required_n` 2 assignments) — delivered by another route while the
branch sat unmerged.

Conclusion: **do not merge `hotfix/required-n-power`.** The remaining real defect on main is the
stalled `/audit` publish (§2.1), not the tribunal.

## 3. What was changed

One new file. No existing file touched.

- **`reports/patches/2026-11-20-sleeve-gate-on-main.patch`** (123 lines) — sleeve implausible-PF
  gate, rebased onto `origin/main`.

The earlier `reports/patches/2026-11-19-sleeve-implausible-pf.patch` (197 lines) was **not** reusable:
it was cut against a pre-`require_alpha` base and its hunks additionally *removed* the `--history`
family of arguments, removed `require_alpha=True` from the `build_report` call, and dropped the
`global_trial_count`/`required_n` repairs. Replaying it as-is would have reproduced the same class of
revert documented in §2.2. The new patch contains **only additive hunks**:

1. `--sleeves` argument.
2. The reconciliation block between `payload_coverage(...)` and `build_report(...)`.
3. `report["sleeves"] = sleeves` before serialisation.

Dropped from the original: the unused `--benchmark` argument (it loaded a sidecar into a local that
nothing read) and a dead `_audit3_keys = {... for c in []}` line.

### Gate logic (unchanged semantics)

A sleeve is **not rankable** if any of:

- `pf > 25` (absolute ceiling — a PF of 155 means the average win is 155× the average loss; no 1.67:1
  template produces that, it is a grading artefact from near-zero or resolver-fallback losses);
- `pf / class_pf > 5` (order-of-magnitude above its own class aggregate);
- not scored by the tribunal (`UNVERIFIED`);
- `is_single_source`;
- `n < 30`.

## 4. How it was verified

```
$ python3 -m py_compile alpha_engine/audit3_tribunal.py      # OK
$ python3 -m alpha_engine.audit3_tribunal --help            # exit 0
$ python3 -m alpha_engine.audit3_tribunal \
    --picks audit_dashboard/data/dashboard_data.json \
    --sleeves audit_dashboard/data/dashboard_data.json \
    --out /tmp/sleeve_ledger.json                            # RUN EXIT=0
has sleeves: True | count: 10
generated_at: 2026-11-20T01:04:40.613513+00:00 | n_rows: 3500
denylist_hits present: True
```

All 10 sleeves resolved to `rankable=False`:

| Class | Strategy | PF | class PF | ×class | n | Reason |
|---|---|---|---|---|---|---|
| CRYPTO | AuditEnsemble_LONG | 155.85 | 1.3131 | 118.7 | 135 | abs ceiling + class |
| CRYPTO | CorrKamaAdaptiveStrategy | 111.81 | 1.3131 | 85.2 | 138 | abs ceiling + class |
| CRYPTO | ADX Trend Confirmation | 56.73 | 1.3131 | 43.2 | 213 | abs ceiling + class |
| CRYPTO | mega_mut_macd_rsi_m084 | 49.37 | 1.3131 | 37.6 | 124 | abs ceiling + class |
| CRYPTO | CorrVwapZscoreReversionStrategy | 33.09 | 1.3131 | 25.2 | 169 | abs ceiling + class |
| FOREX | non_crypto_consensus | 9.68 | 0.6578 | 14.7 | 223 | class aggregate |
| EQUITY | UNKNOWN | 9.74 | 1.2289 | 7.9 | 32 | class aggregate |
| EQUITY | unknown | 3.04 | 1.2289 | 2.5 | 50 | UNVERIFIED + single-source |
| EQUITY | MomentumEMA | 2.17 | 1.2289 | 1.8 | 63 | UNVERIFIED + single-source |
| EQUITY | MeanReversionBB | 1.67 | 1.2289 | 1.4 | 193 | UNVERIFIED + single-source |

Acceptance criteria for the change, all met:
- ✅ `sleeves` key present in the ledger (10 entries);
- ✅ every sleeve with `pf > 25` is `rankable=false`;
- ✅ each non-rankable sleeve carries a machine-readable `rank_exclusion_reason`;
- ✅ no previously-present key removed (`denylist_hits`, `verdict_churn` still emitted).

## 5. Limitations — stated, not hidden

- `n_rows=3500` in the local run vs `8,632` live. The local `audit_dashboard/data/dashboard_data.json`
  (34 MB, 21:34) is a different vintage than the payload the live cron scores. The gate math is
  unaffected, but this run is **not** a reproduction of a live ledger — it is a demonstration that
  the gate fires correctly on real sleeve data.
- `selection_alpha` reports `not available` because no `--alpha` sidecar was passed. Expected.
- The patch is **not applied to any tracked file**. It exists only as a diff for the owner to review.
- The real reason `/audit` has not rebuilt since 21:02:25 is **not established here**. That is a
  deploy-target problem (`deploy_audit_files.py` has no `/audit3`/`/audit` refresh for this artifact),
  not a tribunal problem, and I did not investigate it further in this pass.

## 6. Recommended next action

1. **Do not merge `hotfix/required-n-power`.** Close it or rebase it onto current main keeping only
   additive hunks.
2. Fix the `/audit` publish stall — it is now 223 min and drifting.
3. Apply `reports/patches/2026-11-20-sleeve-gate-on-main.patch` on top of main, then re-run the gate
   check in §4 plus `tools/assert_surface_parity.py`.
