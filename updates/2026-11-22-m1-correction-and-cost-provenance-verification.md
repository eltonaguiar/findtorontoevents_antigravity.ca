# M1 claim withdrawal + verification of the 12.07 bp equity cost figure

**Date:** 2026-11-22
**Trigger:** `zoo-savant`'s `ASK A3 | HAVE IT` reply on the COMS bus.
**Files changed:** `COMMUNICATION/COMS_METHODOLOGY_XREVIEW_2026-11-22.md` (M1 corrected),
`COMMUNICATION/COMS_REPLY_FREEBUFF_TO_ZOO_2026-11-22.md` (new), and this note.
**Not changed:** any verdict, any gate threshold, any cost model constant.

## 1. What was broken

Two separate defects, both of the same family: **a published statement that the artifact
underneath it did not support.**

### 1.1 M1 was false

I published, in a cross-review document sent to every desk on the bus:

> "Enforcement must exist in exactly one module
> (`alpha_engine/audit3_tribunal.py::forward_gate_block`); every other surface labels itself
> display-only."

`zoo-savant` replied `ASK A3 | HAVE IT` and cited the promotion surface. I opened every citation
and they reproduce verbatim:

| Evidence | What it shows |
|---|---|
| `audit_trail/dashboard_generator.py:12238` | `_PROMOTED_SIDECARS = {` — a hard-coded set |
| `audit_trail/dashboard_generator.py:12297` | `is_promoted = name in _PROMOTED_SIDECARS` — membership **overrides** computed status |
| `audit_trail/dashboard_generator.py:12256` | docstring: `PROMOTED status is sticky — driven by _PROMOTED_SIDECARS not stats.` |
| `tests/test_sidecar_promotion.py:108` | `test_promoted_status_sticky_regardless_of_stats` — docstring `"1 awful trade -> still PROMOTED"` |
| `alpha_engine/money_ready_verdict.py:1374`, `:739` | a second, independent class-level verdict emitter |

The test is the part neither of us said clearly enough: **the bypass is asserted by a passing
test**, so removing it fails CI. A defect locked by a green test is a contract, and any fix that
touches only the code will be reverted.

### 1.2 The equity cost figure had no artifact behind it — for about twenty minutes

While reviewing, I read `reports/equity_cost_measurement/equity_cost_20261122.json` and found
`spread: {status: ...}` only, with `spread_aggregate.n_symbols_with_data = 0` and every median
`null`. I concluded in `plans/2026-11-22-coms-review-and-todos.md` that the 12.07 bp was
"UNBACKED — do not cite".

**That conclusion was itself wrong, because I read a stale file.** The peer's provenance repair
landed at 23:09:46Z (the write-up describes it as a `TIINGO_API_KEY` gate that silently
overwrote a good run with `SKIPPED_OFFLINE_OR_NO_KEY`; the gate is fixed in
`tools/equity_cost_measure.py`). Re-reading the same path shows `n_symbols_with_data = 13`,
`provenance_self_check = PASS`, `generated_utc = 2026-11-22T23:08:17Z`.

So the defect was real and self-reported, the repair was real, and **my correction was itself
one file-read away from being a false accusation**. The lesson is not "trust the paragraph" or
"distrust the paragraph" — it is **record the mtime when you read an artifact you are about to
call empty**, because "empty" and "stale" look identical in a `json.load`.

## 2. What I changed

1. `COMMUNICATION/COMS_METHODOLOGY_XREVIEW_2026-11-22.md` — the M1 paragraph is kept (struck
   through in effect, marked corrected) and followed by a block that withdraws the sentence,
   lists the five citations, states the stronger test-locked finding, and restates the surviving
   claim: **exactly one module gates capital; at least three sticky label paths can display a
   promotion the gate never granted.**
2. `COMMUNICATION/COMS_REPLY_FREEBUFF_TO_ZOO_2026-11-22.md` — §6-format reply: A3
   `CONFIRMED_AND_WORSE`, A4 scope granted with the tools' known weakness stated up front.
3. `plans/2026-11-22-coms-review-and-todos.md` — C5 rewritten from "unbacked, do not cite" to
   the verified state.

## 3. How verified

### 3.1 The 12.07 bp figure, recomputed from the artifact

```
n_symbols_with_data  = 13
range_ub_rt_median   = 12.074926303113397
corwin_schultz_rt    = 1.5033324854592698
per_side_used_bp     = 6.0374631515566985
self_check           = PASS
per_name             = AAPL 8.2295, AMZN 13.0449, GOOGL 12.8013, META 14.1022, MSFT 12.1233,
                       NVDA 20.9972, QQQ 12.0749, SPY 8.3139, XLE 7.3870, XLF 6.1146,
                       XLK 14.2149, XLV 5.7847, XLY 7.3099
```

Sorting the 13 values, the 7th (the median) is `QQQ = 12.074926303113397` — identical to the
reported median to the last digit, which is what "the median is one of the samples" predicts for
n=13. `per_side_used_bp` is exactly half. Per-name values are inline in the artifact, so every
number is checkable without re-running anything.

### 3.2 Independent re-run

`python3 tools/equity_cost_measure.py` was re-run end to end this session (yfinance 1.3.0, live
fetch, 20 symbols `fetch_status: ok`), reproducing the per-name spread bounds and then the cost
curve and proof bar. Log: `/tmp/equity_cost_rerun.log`. The pre-run artifact was backed up to
`/tmp/equity_cost_20261122.pre_rerun.json` so a failed network run could not destroy the good
artifact — the exact failure that produced the original defect.

### 3.3 Claims not touched

- `pod break_even_bp_per_side = 14.583824398554036` reproduces.
- `proof_bar.measured` at 6.0375 bp/side: null 10.2nd percentile, excess CAGR −14.25%
  [−46.32%, +32.31%], required 28.54%, **NOT_INVESTABLE**.
- No verdict changes: H-201 remains `NOT_PROVEN`, 0 of 9 classes pass, zero capital.

## 4. What this does not fix

- The **sticky promotion bypass** is still in the code and still test-locked. I have documented
  and reported it; I have not changed it, because changing it is a test change on a surface other
  desks depend on and it is not mine to make unilaterally.
- **`COMMISSION_UNKNOWN`** — every equity cost number above is spread only.
- **MEME cost is not measurable** from 1-min bars (SHIB tick-truncated to a 53-price grid).
- The **claim register is divergent**: `reports/claim_register.json` in the main tree holds 9
  claims while the worktree copy holds 25. I did not append to either with a fresh id, because
  that would fork the register further; recorded as a todo instead.

## 5. Claim-register divergence resolved (same session)

**Was:** main tree `reports/claim_register.json` = 9 claims (C-001..C-009);
`/tmp/fr/reports/claim_register.json` = 25 claims (C-001..C-025).

**Check made before touching anything:** is the worktree copy a strict superset? Compared the id
sets — `main-only ids (missing from wt): []`. All nine main-tree claims exist in the 25, so
adopting the worktree copy loses nothing and forks nothing.

**Done:** copied the 25-claim register over the 9-claim one. Verified after the copy:
`n_claims: 25`, ids `C-001`..`C-025`, `schema_version: 1`, four rules, and the three
`supersedes` chains intact (`C-017 -> C-016`, `C-018 -> C-013`, `C-025 -> mechanism sentence in
C-022`). Status distribution preserved: 7 REFUTED, 8 MEASURED, 2 CORRECTED, 1 REPRODUCED,
2 AS_STORED, 2 PROPOSED, 2 NOT_PROVEN.

**Not done, deliberately:** I did not add an M1 entry. The register is append-only and the
superseding entry for the M1 withdrawal belongs with the corrected hypothesis, not bolted on by
the reviewer who got it wrong; the withdrawal is recorded in the methodology document and in
`COMMUNICATION/COMS_REPLY_FREEBUFF_TO_ZOO_2026-11-22.md` instead.

## 6. H-201 pod forward clock is now scheduled

**Was:** `tools/pod_forward.py` recorded real forward rows, but nothing invoked it. The clock
stood at 15/20 days and 3/10 trades and advanced only when a human ran it. The one existing pod
workflow, `.github/workflows/premia-pod-forward-clock.yml`, is a **stub**: its run step is
`echo "Forward clock not yet implemented (Phase 3)."` with the real invocation commented out, so
it schedules nothing.

**Done:** `.github/workflows/pod-h201-forward-clock.yml` in the worktree that holds the tool —
daily cron `20 22 * * *` (after the US close), `workflow_dispatch` with a `dry_run` input,
`python tools/pod_forward.py`, then `pod_status.py`, then a commit of
`reports/pods/forward/*.jsonl` carrying `[skip ci]` and skipped when nothing changed.

**No push trigger**, matching the 2026-05-19 precedent that removed it from
`audit-dashboard.yml`: this job commits data that would otherwise re-trigger it.

**Verified:** YAML parses (`yaml.safe_load`), triggers `['schedule','workflow_dispatch']`, cron
`20 22 * * *`, all six steps present and named; and `python3 tools/pod_forward.py --dry-run`
exits 0 in the worktree, emitting the expected `signal` and `entry` events (basket MSFT/XOM/AAPL,
`cost_bps_per_name: 33.0`).

**Limit, stated plainly:** the workflow only starts running once the branch is pushed and merged.
I did not push — the main tree is on a branch carrying other agents' work. Until then the clock
advances only when the tool is run by hand, which is exactly what this file stops being true.

## 7. Pod clock wired to the PIT universe (2026-11-23)

**Why the recorded clock could never conclude:** `pod_forward.py` read
`UNIVERSES["EQUITY"]` — 10 mega-caps — while the pod spec requires
`universe.minimum_names: 22`. It enforced that bar correctly and therefore set `universe_ok:
false` on every run and barred its own PASS. Recording rows into a clock that cannot conclude is
bookkeeping, not a test.

**What changed** (full record in the worktree's
`updates/2026-11-23-pod-h201-pit-universe-wiring.md`): the recorder now reads the 44-name PIT
artifact and carries its provenance into every summary (`universe_source`,
`universe_survivorship_status`, `universe_label`); the universe is **pinned at the anchor**, and a
differing universe aborts unless `--switch-universe` is passed, which archives the running rows
plus a `switch.json` and restarts the anchor; and the top rung on a flagged universe is renamed
`CANDIDATE_SURVIVORSHIP_FLAGGED` so a clean label cannot imply a clean universe.

**Verified:** compile OK; unannounced swap → RC=1 with the pinned-vs-requested counts;
`--switch-universe` → RC=0, archived to `archive_pre_switch_20261123T001739Z`, `universe_names:
44`, `universe_ok: true`, `PARTIAL_NON_DELISTING_AWARE`, verdict still
`NO_VERDICT_TOO_FEW_DAYS_FOR_INFERENCE` at 15 days; immediate re-run → RC=0, `new 0`.

**The important negative:** the universe change did not manufacture a result. 44 names cleared
the count bar and the pod still has no verdict, because 15 days is below its own 20-day gate.
That is the intended outcome — the fix removes a structural blocker, not a statistical one.
