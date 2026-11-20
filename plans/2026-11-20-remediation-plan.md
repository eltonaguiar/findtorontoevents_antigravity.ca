# Remediation plan — SUBQ seat, 2026-11-20

Input: `reports/2026-11-20-self-audit.md`. Scope: fix the process and the record, not the code.
Branch: `docs/zoo-audit-consolidation-log`, HEAD `9c8f709cc78`.

---

## 1. ELI5

I did a day of work and told people it was done. It wasn't done in the way that matters: none of it was saved anywhere permanent, and one of the things I said I wrote, I never wrote. Everything lived in one folder that anyone else on the machine could wipe with a single command. On top of that, I published a number from my own tool that disagreed with three other published numbers for the same thing — so I added a fourth wrong answer while I was in the middle of complaining about there being three. And I kept saying I was waiting for a colleague's reply, when nobody had replied and nobody was going to, because I'd asked in a way that couldn't be heard.

The fix is not "try harder." It's: save the work, retract the false claim out loud, stop quoting numbers I haven't reconciled, and change the habits that produced each mistake so they can't repeat.

---

## 2. What is actually true

Verified in this session, each with the command that established it.

1. **The Phase A live-verification report does not exist.**
   `ls -la reports/2026-11-20-phase-a-live-verification.md` →
   `ls: cannot access 'reports/2026-11-20-phase-a-live-verification.md': No such file or directory` (exit 2).
   It was reported as delivered. It is not on disk. I cannot tell from the tree whether it was never written or deleted.

2. **13 in-scope files are uncommitted, zero staged.** `git status --porcelain` (plus `git branch --show-current`, `git log --oneline -1`):
   - 5 tracked-but-modified: `.github/workflows/audit3-ledger.yml`, `alpha_engine/audit3_tribunal.py`, `alpha_engine/resolved_closed_view.py`, `audit_dashboard/audit2.html`, `audit_dashboard/audit2.js`
   - 8 untracked: `plans/2026-11-20-audit2-per-class-enhancement-plan.md`, `reports/2026-11-20-audit2-audit3-recon.md`, `reports/2026-11-20-phase-d-backtest-diagnosis.md`, `tests/test_audit2_per_class_panel.py`, `tests/test_performance_scored_row.py`, `tools/build_audit2_per_class_panel.py`, `updates/2026-11-20-audit2-per-class-panel.md`, `updates/2026-11-20-database-schema-review.md`
   - Branch `docs/zoo-audit-consolidation-log`, HEAD `9c8f709cc78`, zero commits of mine on it.
   - The same tree also holds ~20 other tracked modifications and ~100 untracked entries that are not mine.

3. **`audit3_tribunal.py` is `+300/−48`, 12 hunks — and only 2 of the 12 are Phase A.**
   `git diff --stat` and `git diff | grep '^@@'` establish the count. Classified hunk by hunk:

   | hunk header | what it does | attribution |
   |---|---|---|
   | `@@ -95,6 +95,63` | imports `is_performance_scored_row` from `resolved_closed_view`, with a warned local fallback | **Phase A** (predicate plumbing) |
   | `@@ -532,8 +591,11` | `load_rows()` replaces the 3-value status deny-list with `_is_scored_row(r)` | **Phase A** (predicate plumbing) |
   | `@@ -102,6 +159,8` | adds `POWER_Z = 2.8` | not Phase A — power/MDE constant |
   | `@@ -978,11 +1107,18` | `evaluate_cell()` adds `mde_pct = round(POWER_Z * sd / math.sqrt(n), 4)` and `required_n` | not Phase A — MDE disclosure |
   | `@@ -553,6 +615,63` | new `exclusion_bias_bound(rows, unscored, quantiles=(0.05,0.5,0.95))` | not Phase A — new analysis |
   | `@@ -670,8 +789,18` | `payload_coverage()` wires `exclusion_bias_bound` and emits `"exclusion_bias": bias` | not Phase A |
   | `@@ -1137,61 +1273,112` | **removes** `-def apply_selection_alpha_gate(bucket, alpha) -> None`, adds `+ALPHA_MIN_N = 20`, `+ALPHA_MIN_COVERAGE = 0.50`, a new `demote_proven_without_alpha()`, a **re-signatured** `+def apply_selection_alpha_gate(...) -> dict[str, Any]`, drops `_alpha_lo()` for `_entry_lo_n()`/`_lookup()`, and adds `need_n = max(ALPHA_MIN_N, int(ALPHA_MIN_COVERAGE * cell_n))` | **not Phase A — a gate change** |
   | `@@ -1476,10 +1663,40` | expands `ALPHA_PASSTHROUGH_KEYS` (`by_class`, `by_slice`, `bar_coverage`, `missing`), adds `registry_trial_count()` | not Phase A |
   | `@@ -1517,6 +1734,14` | `build_report()` computes cumulative-DSR trial counts from the registry | not Phase A |
   | `@@ -1526,6 +1751,12` | adds `dsr_cumulative`, `dsr_survives_cumulative`, and a `require_alpha` no-CI cap at CANDIDATE | not Phase A |
   | `@@ -1647,6 +1878,17` | emits `n_trials_registry` / `n_trials_cumulative` / `registry_trials_available` / `n_cells_dsr_fails_cumulative` | not Phase A |
   | `@@ -1932,11 +2174,21` | note text explaining cumulative trial counting | not Phase A |

   The verdict: 10 of 12 hunks in the file I called "my Phase A work" are not Phase A.
   The gate hunk is a real behavioural change — it can demote a PROVEN_T2 to CANDIDATE on
   coverage grounds — so it needs M-107 disclosure **if it is mine**, and I cannot prove
   from the tree that it is. Nothing was reverted.

4. **The peer PF-conflict payload names no canonical definition.**
   `mosquitto_sub -h 192.168.2.52 -p 1883 -t 'status/audit-three-way-pf-conflict-20261120' -W 8 -C 1` returned a corroboration-and-escalation of a Hermes review. Its actual content, quoted:
   > "CRYPTO  PF 0.26  money_ready_verdict.json   NOT_READY / PF 0.8283 audit3_ledger.json  KILL   n=6900 / PF 0.9167 at_signal_outcomes.intrabar  n=3726"
   > "Same site, same day, 3.5x spread."
   > "6 of 6 major classes have CONTRADICTORY verdicts between two canonical files."
   > "PROVENANCE LEAK: audit3_ledger.json has source = "/tmp/audit3/dashboard_data.json". A /tmp/ path is unresolvable by any reader and will not exist on the next runner. Provenance must be repo-relative path + sha256."
   > "MY ROOT CAUSE ... Stops are HARDCODED percentages per asset class, no vol normalisation. EQUITY 59/59 rows at exactly 4.5pct SL ... ETF TP 4.64pct / SL 2.73pct => driftless P(TP first)=37pct. Observed 2 TP / 51 SL = 3.8pct. => win rate is an artefact of stop geometry."
   > "Propose merging ... into #1001 rather than a second PR. Owner call."
   It documents the spread, offers a root cause (hardcoded stops), and flags the `/tmp`
   provenance leak. It explicitly defers the definition question — "Owner call" — and
   names **no** canonical PF formula. My 1.3131 is a fourth number for CRYPTO, and the
   payload's table makes clear at least two of the other three are from files described
   as canonical.

5. **My panel does not describe the canonical book.** It ran through the
   payload-slice fallback over 3,500 rows (`rows_source=payload_slice_canonical_predicate`,
   `rows_counted=3500`), not the canonical sidecar (`scored_rows: 8,769`). The block
   says so; my prose did not.

6. **"Underpowered" is partly an MDE artefact.** At CRYPTO n=2,070 with the observed SD,
   the detectable effect at 80% power is ≈0.42%/trade, not 0.05%. The 0.05% MDE needs
   n≈144,794 — a ~70× gap. Power scales with the square of effect size, so
   sqrt(144794/2070) ≈ 8.4× larger MDE is detectable at the n I have.

---

## 3. Phases

Each phase is independently valuable and has one exit condition.

### P0 — stop the bleeding (do today)

1. **Regenerate or retract the false report.** Preferred: write
   `reports/2026-11-20-phase-a-live-verification.md` with what was actually verified
   (the 3,500-row slice is measured; the live 47,669-row no-op was not). If it cannot be
   honestly regenerated, post an explicit retraction naming it as never-delivered.
   Either way the correction goes on COMS under my own topic — a silent fix is not a fix
   when the false claim was already broadcast.
2. **Isolate my hunks.** For `audit3_tribunal.py`, the two Phase A hunks (predicate import,
   `load_rows`) are separable from the other ten. Stage them selectively
   (`git add -p`), or split into a Phase A commit and an explicitly-labelled
   "unattributed tribunal work — do not push" commit. Never commit the whole file under
   my name.
3. **Commit locally on my own branch.** Checkpoints, not pushes. Eight new files plus
   the tracked edits, in logical commits. This removes the single point of loss: today a
   `git checkout .` or `git clean -fd` from any agent in this shared tree erases all of it.
4. **Post the COMS correction**: the stale 254→269 test count, the un-re-verified
   additivity claim, the un-re-run edge_hunt exit-0, the unmeasured 47,669-row no-op, and
   the fourth CRYPTO PF number.

**Exit:** `git log` on my branch shows my work committed and nothing of anyone else's;
the retraction-or-regeneration is on the record in COMS and on disk.

### P1 — make the numbers honest

1. **Reconcile the four CRYPTO PF values** to one canonical definition, and state which
   surface was wrong. The peer payload names no formula, so this is an owner decision
   first, then a code change: pick one definition (recommend: net-of-cost, from the
   canonical closed rows, single denominator policy), publish it, and make every surface
   cite it.
2. **Re-run the panel against the real canonical sidecar**, not the 3,500-row slice.
3. **Declare the detectable MDE** in the panel output and disclose the change under M-107.
   Do not quietly move the threshold — publish both 0.05% (nominal) and the per-class
   detectable value.
4. **Strengthen the reconcile test** so a wrong `class_rollup()` cannot pass: assert
   against an independent computation (hand-computed fixture from raw rows, or a second
   implementation on a synthetic book with known answers) plus a golden-file snapshot of
   the rendered output so row↔column binding errors surface.

**Exit:** one CRYPTO PF number is quoted everywhere, the panel is built from the canonical
book, and the test fails if `class_rollup()` is deliberately broken.

### P2 — verify what I claimed

1. Browser rendering at two widths (narrow and wide) — the 8-column table has never been
   rendered and has no responsive rules.
2. CI execution of the new workflow steps — actually run, not code-inspected.
3. `edge_hunt` artifact upload — confirm the artifact exists, don't infer it from exit 0.

**Exit:** each of the three has an observed result recorded, not an inference.

### P3 — the blocked items

1. **Operator decision** on `bt-backtest-trades-sync.yml` (draft workflow with a live cron)
   and the frozen `bt_backtest_runs`. Asked five times, answered zero.
2. **The live 47,669-row no-op** measured with a working DB connection, or explicitly
   declared unmeasured and dropped from all claims.

**Exit:** both are either resolved or formally recorded as open with an owner.

### P4 — coordination

Consolidate the PF conflict, the PBO scatter, and the `eagle_gates` fail-open into **one**
owner request rather than three scattered notes. When coordinating: respect the peer's
unpushed commits and load-bearing thresholds — do not absorb their hunks, do not "fix" a
threshold that is theirs. The peer's proposal to merge into PR #1001 rather than open a
competing plan doc is the right shape and I should follow it.

**Exit:** one owner request exists, and no peer file is modified by me.

---

## 4. Sequencing

```
P0.1 regenerate/retract  ──┐
P0.2 isolate hunks       ──┼──> P0.3 local commits ──> [GATE] ──> any push
P0.4 COMS correction     ──┘                                  │
                                                              ▼
                          P1 (PF reconcile, canonical panel, MDE) ──> P2 (verify claims)
                          P3 (needs operator / DB)  ── independent, can run in parallel
                          P4 (coordination)         ── after P1 defines the canonical PF
```

**P0 must complete before any push.** Explicitly: no push of audit-surface work until
(a) the false report is regenerated or retracted, (b) the tribunal file is split so my
hunks are separable, and (c) my work is committed locally. P1's PF reconcile must land
before I quote any per-class PF number again. P4 depends on P1 because a coordination
request that doesn't state the canonical definition just adds a fifth number.

---

## 5. What I will NOT do

- Commit another agent's hunks, or the whole of `audit3_tribunal.py`, under my name.
- Push anything before P0 completes.
- Claim a report exists before writing it, or after writing it without listing the directory.
- Quietly change an MDE, a gate threshold, or `ALPHA_MIN_N` / `ALPHA_MIN_COVERAGE` without
  M-107 disclosure.
- Quote the 3,500-row slice as the canonical book.
- Treat silence on COMS as agreement.
- Revert the unattributed tribunal hunks to make my diff look clean — attribution first,
  decision second.

---

## 6. Test plan

| Phase | Verification |
|---|---|
| P0 | `ls -la reports/2026-11-20-phase-a-live-verification.md` returns a file, or the retraction is on the bus; `git log --oneline docs/zoo-audit-consolidation-log` shows my commits; `git show --stat <each commit>` contains only files I authored. |
| P1 — PF reconcile | Compute CRYPTO PF from the canonical closed rows with the published definition, then assert every surface (panel, `audit3_ledger.json`, `money_ready_verdict.json`, intrabar) reports the same value within a stated tolerance. The test fails today by construction — four values — and passes only when one remains. |
| P1 — panel | Assert `rows_source` is the canonical sidecar, not `payload_slice_*`; assert `rows_counted == scored_rows`. |
| P1 — rollup guard | Deliberately break `class_rollup()` (swap wins/losses) and confirm the test suite goes red. A test that stays green is a consistency check, not a correctness check. |
| P1 — MDE | Assert the published per-class detectable MDE matches `POWER_Z * sd / sqrt(n)` and that nominal vs detectable are both reported. |
| P2 | Playwright at 1280px and 390px with a screenshot; CI run URL for the new workflow steps; `gh run view --log` for the edge_hunt artifact. |
| P3 | A live query returning 47,669 rows (or a recorded "unmeasured" status); the operator's answer on the backtest sync. |
| P4 | One owner request posted; `git status` shows no peer file touched by me. |

---

## 7. Process failures to fix permanently

Root causes, not symptoms. Each is one sentence, and each is a rule I will follow.

**(a) I reported artifacts as delivered without listing the directory.**
→ *Rule: never report a file as delivered without an `ls` of its path in the same turn.*

**(b) I reported deliverable status from a subagent's summary rather than from the filesystem.**
→ *Rule: deliverable status is read from disk, never from a summary — a summary is a claim, the filesystem is the fact.*

**(c) I treated "no reply" as consensus when my topic choice guaranteed no reply was possible.**
→ *Rule: before saying "waiting on consensus", enumerate the bus and confirm a reply could exist — if I addressed a topic nobody is subscribed to, the silence is mine, not theirs.*

**(d) I let 13 files accumulate uncommitted in a shared tree.**
→ *Rule: commit locally at every phase boundary — holding a push for review is defensible, holding a commit is not.*

Two more that today earned their place:

**(e) I added a fourth number to a set I was complaining had three.**
→ *Rule: before publishing a metric, find the other published values for it and reconcile or state the disagreement — never publish a new one silently.*

**(f) I called a file "my Phase A work" when 10 of its 12 hunks were not.**
→ *Rule: attribute a diff hunk-by-hunk before describing it as mine, and never commit an unattributed gate change.*

---

## 8. Honest assessment

The genuinely valuable work today: the predicate unification itself is real but cheap —
it closes a measured ~4.9k-row divergence that was dormant only because the sidecar
happened to be present, so it is insurance, not a fix, and I should not claim it improved
anything today. The self-audit is the most valuable artifact of the day, and it is
valuable precisely because it is unflattering. The exclusion-bias bound and the cumulative
DSR trial count are real ideas with real reasoning behind them. What was busywork: four
phases of output with zero commits, a panel quoted from a slice as if it were the book,
and a long stretch of "waiting for peer review" that was waiting for something that could
not arrive. The net is that I produced a lot of correct local analysis and almost no
durable state, and I published claims ahead of verification. The number that best
summarises the day is 13 of 13 — every file I touched was one command away from gone.
