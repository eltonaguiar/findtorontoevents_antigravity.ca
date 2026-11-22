# 2026-11-20 — Session final notes: /audit pipeline, sleeve gate, pre-push gate

**Agent:** linux-deepseek-v4-flash
**Session window:** 2026-11-19T22:00Z → 2026-11-20T02:45Z
**Repo basis:** `origin/main` @ `b62624b39d5` (moved from `3af1336` mid-session)
**Published to:** `eltonaguiar/antigravity_review_Nov192026` — `66da943`, then `184fe2d`
**Nothing deployed. No shared source file in this checkout was modified.**

---

> **Tip churn caveat.** `origin/main` advanced four times during and after this session
> (`3af1336` → `94466c0` → `ec387e4` → `1d2468a4ffe` → `fd1c9f0cb68`). The patch was
> re-verified against each new tip it was checked at. The short SHA recorded in this file
> is the tip the last `git apply --check` and real ledger run were performed against —
> **not** a promise it still is. Re-run the commands in §13 rather than trusting the SHA.

## 1. What this session set out to do

Four queued tasks, all on the `/audit` · `/audit2` · `/audit3` pipeline:

1. Find out why `/audit` stopped rebuilding at 21:02 and stop it drifting multiple build
   cycles behind `/audit3`.
2. Wire the sleeve gate into the hourly pipeline so implausible-PF sleeves are flagged on
   every rebuild, not only when run by hand.
3. Harden the pre-push check so a branch that compiles but crashes at runtime can't be
   called verified again.
4. Check in with the COMS fleet.

Plus the standing instruction to re-check all three live surfaces after anything lands.

## 2. Status of each task

| # | Task | Status | Evidence |
|---|---|---|---|
| 1 | `/audit` publish stall | **Diagnosed, patched, NOT resolved** — patch unmerged, parity still RED | §3, §5 |
| 2 | Sleeve gate in hourly pipeline | **Wired in the patch, inert until the tribunal patch is applied** | §6 |
| 3 | Pre-push runtime gate | **Built and proven both directions** | §7 |
| 4 | COMS check-in | **Done** — 2 retained messages, read back off the broker | §8 |
| — | Re-check 3 surfaces | **Done** — all 200s; parity RED | §5 |

## 3. The stall: root cause, and the wrong answer I gave first

**Measured at 01:05Z:** `/audit` served `generated_at 2026-11-19T21:02:25`, 8,621 rows;
`/audit3` served `00:45:04`, 8,632 rows. Build gap **222.6 min**, parity `RED (exit 2)`.

**My first root cause was wrong.** I reported that no workflow writes
`/audit/data/audit3_ledger.json`. Re-measured at 02:05Z, the file had **moved** — rows
8,621 → 8,632, exactly the content `/audit3` rendered at 00:45. Something does write it.
That claim is **withdrawn** and recorded as a correction in
`reports/FINAL_VERDICT_PRE_MAIN_2026-11-20.md` §1b.

**Actual defect — a publish-ordering split:**

| Artifact | Producer | Cadence | Publishes to |
|---|---|---|---|
| `audit3_ledger.json` | `audit3-ledger.yml` | 6-hourly `23 */6` | `/audit3/` — fresh, immediately |
| same file | `audit-dashboard.yml` | hourly `:10`, **~35 min job** | `/audit/data/` — one generation later |

`/audit` is fed by a *slower consumer of the same artifact*, so it always renders the
**previous** ledger. The 70-minute parity tolerance is **unsatisfiable against a
6-hourly producer**, and when the dashboard job backlogged the lag reached 223 minutes —
several build cycles. Not a crashed stage; two publishers racing on one file.

**Fix (in the patch):** `audit3-ledger.yml` now uploads the ledger it just generated to
`/audit/data` in the same deploy step, so one generation yields one identical artifact on
all three surfaces.

## 4. Withdrawals made this session — explicit, not silent

1. **`hotfix/required-n-power` (70d4a5a) is WITHDRAWN from GO.** I had recommended it.
   Its first real invocation exits 1:
   `TypeError: build_report() got an unexpected keyword argument 'require_alpha'` at
   `alpha_engine/audit3_tribunal.py:1991`. `--help` exits inside `argparse`, before
   `main()` builds a report — that is exactly why my GO was wrong. The diff also deletes
   `ALPHA_PASSTHROUGH_KEYS`, drops `denylist_hits`, downgrades `CANDIDATE`→`WEAK`, and
   double-applies the persistence gate. `origin/main` already carries the repairs.
2. **"Nothing writes `/audit/data/audit3_ledger.json`"** — withdrawn, see §3.

## 5. Live surface state at the end of the session

```
/audit            200 OK   1,439,211 B   ledger generated_at 2026-11-19T21:02:25  (8,632 rows)
/audit2           200 OK       6,781 B
/audit3           200 OK      45,908 B   rebuilt 00:45:04  (8,769 rows)

SURFACE PARITY: RED (exit 2) at 2026-11-20T02:05:19Z
  - ROWS_DIVERGE: |8632-8769| = 137 > 0
  - BUILD_GAP_EXCEEDS_CYCLE: 72.3 min > 70 min tolerance
```

No `sleeves` key exists on any production ledger. The stall is understood and patched,
**not fixed** — the patch has no owner yet.

## 6. Sleeve gate — what it proved and what it needs

Replayed on `origin/main` with the additive patch applied
(`reports/patches/2026-11-20-sleeve-gate-on-main.patch`, 123 lines, 97 added, 0 removed):

```
run exit 0 — sleeves: 10 · rankable: 0 · flagged: 10
ceiling 25.0 · class-relative 5.0x · SLEEVE_MIN_N=30 · CRYPTO class_pf 1.3131
  AuditEnsemble_LONG                155.85   (118.7x class)
  CorrKamaAdaptiveStrategy          111.81
  ADX Trend Confirmation             56.73
  mega_mut_macd_rsi_m084             49.37
  CorrVwapZscoreReversionStrategy    33.09
  FOREX/non_crypto_consensus          9.68   (14.7x)
  EQUITY/UNKNOWN                      9.74   (7.9x)
  3 EQUITY sleeves UNVERIFIED + single-source
```

Every sleeve ranks `rankable=False` — the gate refuses to publish a fantasy PF. In the
workflow it is invoked behind a **CLI capability probe**: if `--sleeves` is missing the
build prints `::warning` naming the patch to apply instead of aborting on
`unrecognized arguments`. It never silently claims the gate ran.

## 7. The pre-push gate

`tools/assert_tribunal_runs.py` (new, 202 lines) runs the tribunal **for real** on real
picks, in a throwaway worktree when `--ref` is given, and fails unless the run exits 0 and
emits `schema`, `generated_at`, `summary`, `coverage`, `denylist_hits` with
`n_rows >= 100`. `--help` is recorded but explicitly labelled **informational** — it is the
check that produced the bad GO, so it is never allowed to decide a verdict.

```
# healthy tree
python3 tools/assert_tribunal_runs.py
  help exit=0 (informational) · real run exit=0 · verdict PASS   → EXIT 0

# the branch I wrongly approved
python3 tools/assert_tribunal_runs.py --ref hotfix/required-n-power \
        --picks audit_dashboard/data/dashboard_data.json --expect-fail
  help exit=0 (informational) · real run exit=1
  TypeError: build_report() got an unexpected keyword argument 'require_alpha'
             at alpha_engine/audit3_tribunal.py:1991
  verdict FAIL (expected FAIL)                                   → EXIT 0
```

That is the whole point of the change: the exact branch I approved is now rejected
automatically, on the exact line, with no human required to remember why.

## 8. COMS check-in

The cross-PC loopback gateway is down (`connection refused` on 8788); the live bus is
`AGENT_FOLDERFRAMEWORK/COMMUNICATION/coms` on **192.168.2.52:1883**, seats
`deepseek-v4-flash` and `mentions/all`. **49 messages** were waiting. Fleet intel that
changed my actions:

- `PR #972` killed the `require_alpha` TypeError on main — main is healthy; do not re-fix.
- `#965` **DO NOT MERGE** (15 conflicts). `#977` (kilo) safe, 4 files, +192/−0.
- Hermes' TAA numbers **retracted**: 0.88 Sharpe / −19% MaxDD → 0.727 / −44.6%.
- **`COMS send --retain` is last-writer-wins per topic, not an append log.** I therefore
  used two distinct topics and left `mentions/all` alone rather than clobbering a peer's
  retained verdict.

Sent and verified by reading back off the broker (a send prints "sent" even when dropped):

- `notes/audit3-publish-stall-and-sleeve-gate-20261120` — **1,673 bytes** retained
- `inbox/gx10-c9b9/findtorontoevents_antigravity-ca/kilo` — **878 bytes** retained
  (retracts his earlier ACK of the hotfix before he merges it)

## 9. Deliverables

| Path | What |
|---|---|
| `reports/patches/2026-11-20-hourly-pipeline-sleeve-gate-and-audit-publish.patch` | **393 lines, 3 files, 1 deletion line.** Applies clean to `origin/main @b62624b39d5` |
| `reports/patches/2026-11-20-sleeve-gate-on-main.patch` | Prerequisite, 123 lines, additive only |
| `tools/assert_tribunal_runs.py` | New runtime smoke gate |
| `updates/2026-11-20-audit-publish-stall-and-sleeve-gate-wiring.md` | The mandated fix doc |
| `updates/2026-11-20-postdeploy-verify-and-sleeve-gate-replay.md` | Post-deploy verification: nothing had landed |
| `reports/FINAL_VERDICT_PRE_MAIN_2026-11-20.md` | Verdict + §1b correction + retraction |
| `updates/2026-11-20-session-final-notes-audit-pipeline-and-sleeve-gate.md` | This file |

The combined patch is **one deletion line** total (the invocation being replaced).
Everything else is additive, so it cannot revert another agent's landed work.

Verification run against a clean `origin/main` worktree:

```
git apply --check  → OK
after apply:  deploy uploads /audit/data: True
              build passes --sleeves:   True
              tool present:             True
yaml.safe_load → OK, 11 steps · bash -n → exit 0 · deploy heredoc compiles
real run exit 0 · sleeves 10 · rankable 0 · flagged 10 · denylist_hits present
```

## 10. Open items and who owns them

1. **Apply the combined patch.** Three files, one deletion line; it fixes the publish
   split and wires the gate in one commit. No owner yet — that is the single blocking item.
2. **Delete the `audit3_ledger.json` upload from `audit-dashboard.yml`.** After the patch
   two workflows write `/audit/data`. Both deploy from `main`, so newest bytes usually win,
   but a dashboard run whose checkout predates a ledger commit can still overwrite with
   older bytes for one cycle. Owner: Kilo Linux CLI — I don't own that file.
3. **Pin `/audit2`** to a single ledger path and add it to `tools/assert_surface_parity.py`,
   which currently asserts `/audit` vs `/audit3` only. `/audit2` renders whichever entry of
   its fallback chain resolves first.
4. **`global_trial_count` still has no principled definition.** Unresolved.
5. **Add `assert_tribunal_runs.py` to CI** on pull requests so the gate runs without a
   human remembering to.

## 11. Limitations — stated, not hidden

- The patch is **shelf-ware**. Parity is RED at the end of this session.
- The sleeve gate is inert until `alpha_engine/audit3_tribunal.py` is patched; the workflow
  warns by name rather than pretending.
- Local `n_rows=3500` vs ~8,769 live: the local 34 MB `dashboard_data.json` is a different
  vintage from the payload the cron fetches. Gate arithmetic and wiring are unaffected;
  this is not a reproduction of a live run.
- **The primary checkout was in flux.** `origin/main` moved `3af1336` → `b62624b39d5`, and this
  tree reported `feat/kilo-todo-sweep-final` @ `2a34571` at one point while another agent
  worked in it. Local `main` is `5f77e770a30` and is **stale by 4 lines** in
  `.github/workflows/audit3-ledger.yml` — which is why every edit was made in a throwaway
  worktree at `origin/main`, never in the shared tree. **Confirm what is checked out before
  committing from that directory.**
- Seat ambiguity: `deepseek-v4-flash` on `review-main` has work history not present in my
  session record. I did not act on it.

## 12. Security — needs a human

Commit `b5f42b39ec1` leaked a **plaintext DB password into 14 files on a public repo**.
Rotation is a human action and is still outstanding. Nothing in this session touched it.

## 13. How to re-verify any claim above

```bash
# the patch is clean and produces the intended change
git worktree add -f /tmp/v origin/main --detach
cd /tmp/v && git apply --check ~/…/2026-11-20-hourly-pipeline-sleeve-gate-and-audit-publish.patch

# a ref actually runs (never trust --help)
python3 tools/assert_tribunal_runs.py --ref origin/main
python3 tools/assert_tribunal_runs.py --ref hotfix/required-n-power \
        --picks audit_dashboard/data/dashboard_data.json --expect-fail

# surfaces agree
python3 tools/assert_surface_parity.py
```

Every number in this document came from one of those commands against a committed or
live artifact. Re-run them rather than trusting this file.
