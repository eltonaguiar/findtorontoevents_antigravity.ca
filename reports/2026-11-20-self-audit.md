# Self-audit — subq-savant-1.4 / SUBQ seat, 2026-11-20

HEAD at audit time: `9c8f709cc78 per-asset-class edge review: purged split, OOS eval, variance-vs-direction check`
Branch: `docs/zoo-audit-consolidation-log`

---

## WORST FINDING

**Every one of my Phase A–D changes exists only in the working tree. Nothing is
staged, nothing is committed on any branch, and one deliverable I claimed does
not exist on disk at all.**

- `git diff --cached --stat` is empty — zero staged changes.
- 12 of the 14 files in my scope have `commits_touching=0` when queried with
  `git log --all` — they are untracked (2 of them: `tests/test_performance_scored_row.py`,
  `tools/build_audit2_per_class_panel.py`, `tests/test_audit2_per_class_panel.py`,
  `updates/2026-11-20-audit2-per-class-panel.md`, `updates/2026-11-20-database-schema-review.md`,
  `reports/2026-11-20-audit2-audit3-recon.md`, `reports/2026-11-20-phase-d-backtest-diagnosis.md`,
  `plans/2026-11-20-audit2-per-class-enhancement-plan.md`) or tracked-but-modified
  (`alpha_engine/resolved_closed_view.py`, `alpha_engine/audit3_tribunal.py`,
  `audit_dashboard/audit2.html`, `audit_dashboard/audit2.js`, `.github/workflows/audit3-ledger.yml`).
- `reports/2026-11-20-phase-a-live-verification.md` — **commits_touching=0, on-disk=MISSING.**
  It was listed as a deliverable and it is not there. Either it was never
  written or it was deleted. I cannot tell which from the tree.

This is a single point of loss for a day's work in a tree shared with other
agents. See Part 4, question 6.

---

## PART 1 — Inventory of uncommitted state

### Classification

**(a) MINE — 14 candidates, actual state per file**

| file | status code | lines changed | staged? | committed anywhere? |
|---|---|---|---|---|
| `alpha_engine/resolved_closed_view.py` | ` M` | +106 / −3 | no | tracked; my edits uncommitted |
| `alpha_engine/audit3_tribunal.py` | ` M` | +300 / −48 | no | tracked; my edits uncommitted |
| `.github/workflows/audit3-ledger.yml` | ` M` | +88/− (248 total) | no | tracked; my edits uncommitted |
| `audit_dashboard/audit2.html` | ` M` | +15 | no | tracked; my edits uncommitted |
| `audit_dashboard/audit2.js` | ` M` | +61 | no | tracked; my edits uncommitted |
| `tests/test_performance_scored_row.py` | `??` | n/a (new) | no | **never committed** |
| `tests/test_audit2_per_class_panel.py` | `??` | n/a (new) | no | **never committed** |
| `tools/build_audit2_per_class_panel.py` | `??` | n/a (new) | no | **never committed** |
| `updates/2026-11-20-audit2-per-class-panel.md` | `??` | n/a (new) | no | **never committed** |
| `updates/2026-11-20-database-schema-review.md` | `??` | n/a (new) | no | **never committed** |
| `reports/2026-11-20-audit2-audit3-recon.md` | `??` | n/a (new) | no | **never committed** |
| `reports/2026-11-20-phase-d-backtest-diagnosis.md` | `??` | n/a (new) | no | **never committed** |
| `plans/2026-11-20-audit2-per-class-enhancement-plan.md` | `??` | n/a (new) | no | **never committed** |
| `reports/2026-11-20-phase-a-live-verification.md` | — | — | — | **DOES NOT EXIST** |

**(b) NOT MINE** — the rest of the tree. 26 tracked files modified, ~100 untracked
entries. Representative: `probabilistic_sharpe_engine.py`, `audit_trail/dashboard_generator.py`,
`tools/skyrocket_reverse_eng.py`, `html templates`, many `reports/`, `updates/`, `plans/`,
`alpha_engine/cost_gate.py`, `paper_trading/live_sim/`, `.wakeup_watch_state.json`, and
`audit_dashboard/data/audit3_ledger.json` (41,532 lines changed — generated data).
Not touched by me.

**(c) UNCLEAR** — `alpha_engine/audit3_edge_hunt.py` (` M`, 55 lines). I wired it into CI
in Phase C, but I did not write a 55-line change to the module body itself today by my own
account, and whether the body hunk is mine or another agent's I cannot prove from the tree
alone.

### Critical question: what is unrecoverable if the tree is lost right now?

| recoverable | unrecoverable |
|---|---|
| Nothing. | All 8 untracked new files (2 test files, panel builder, 5 docs) — they exist only here. |
| | All 5 tracked-file edits — the committed versions exist, but my edits do not. |

**Unrecoverable count: 13 of 13 existing files.** Zero of my Phase A–D content is
committed anywhere. A `git checkout .` plus `git clean -fd` would erase all of it.

### Entanglement with another agent's work

I cannot cleanly separate by timestamp. Modification times are **not** a reliable
discriminator in this tree:

```
2026-11-20T17:15 .github/workflows/audit3-ledger.yml
2026-11-20T17:13 audit_dashboard/audit2.js / audit2.html
2026-11-20T17:08 tools/run_anti_overfit_audit.py, tools/anti_overfit_audit_sidecar.py,
                 .github/workflows/audit-dashboard.yml,
                 alpha_engine/resolved_closed_view.py, alpha_engine/audit3_tribunal.py
2026-11-20T16:48 probabilistic_sharpe_engine.py, audit_trail/dashboard_generator.py,
                 alpha_engine/validation/sharpe_metrics.py
```

`resolved_closed_view.py` and `audit3_tribunal.py` share the **exact same mtime
(17:08)** as `run_anti_overfit_audit.py`, `anti_overfit_audit_sidecar.py` and
`audit-dashboard.yml` — files that are not in my scope. Either a bulk
checkout/touch set them all, or another agent wrote to my files in the same
minute. I cannot distinguish those two cases from the tree.

Contents matter more than mtimes, and on contents:

- `resolved_closed_view.py` — all 109 changed lines read as one coherent change:
  a provenance triple, `is_performance_scored_row()`, and a rewiring of
  `default_exclusion_reason()` to call it. No foreign hunk is visible.
- `audit3_tribunal.py` — 12 hunks, 348 lines. Roughly 3 added lines reference
  the shared predicate; ~9 reference `ALPHA_*` / `alpha_gate` / `selection_alpha` /
  `quantiles` and introduce **new constants `ALPHA_MIN_N = 20` and
  `ALPHA_MIN_COVERAGE = 0.50`**, and change `apply_selection_alpha_gate()`'s
  return type from `None` to `dict[str, Any]`. That is a real behavioural change
  to a gate, and it is not part of what I described as my Phase A work.

**Finding:** before committing anything, the tribunal diff must be attributed
hunk-by-hunk. Committing it whole would carry someone else's gate change (or an
unattributed one of mine) under my name.

---

## PART 2 — Claim verification, re-run now

All commands run against the current dirty tree.

1. **My two test files** — `pytest tests/test_performance_scored_row.py tests/test_audit2_per_class_panel.py -v`:
   **25 passed in 0.15s** (15 + 10). Both still pass.
2. **Wider slice** — `pytest tests/ -q -k "audit2 or audit3 or closed_view or per_class or performance_scored"`:
   **269 passed, 6 skipped, 7108 deselected, 1 warning in 12.06s.**
   (I previously reported 254 passed / 6 skipped. The count has moved — the
   slice is not a fixed set, it grows as others add tests. Both are true
   statements about different moments; the current number is 269.)
3. **Workflow YAML** — parses. Top-level keys: `name`, `True`, `permissions`,
   `concurrency`, `jobs` (`True` is the `on:` key, normal under YAML 1.1).
4. **Panel builder on the real payload** —
   `python3 tools/build_audit2_per_class_panel.py --ledger /tmp/selfaudit/ledger.json --payload audit_dashboard/data/dashboard_data.json`
   → `per_class_verdicts: 7 classes from payload_slice_canonical_predicate (3500 rows)`.
   Block metadata: `schema=audit2.per_class_verdicts.v1`, `mode=canonical`,
   `rows_source=payload_slice_canonical_predicate`, `rows_counted=3500`.
   Actual classes:

   | class | n | verdict_word | profit_factor |
   |---|---|---|---|
   | CRYPTO | 2070 | KILL | 1.3131 |
   | EQUITY | 690 | WEAK | 1.2289 |
   | ETF | 503 | WEAK | 1.0707 |
   | FOREX | 199 | WEAK | 0.6578 |
   | BOND | 28 | WEAK | 0.5631 |
   | COMMODITY | 9 | inconclusive | 1.032 |
   | FUTURES | 1 | inconclusive | 0.0 |

   Note on provenance: this ran through the **payload-slice fallback**, not the
   canonical rows sidecar — no `resolved_closed_picks_net.json` exists in the
   repo, so the workflow's preferred `--rows` path is still unexercised
   end-to-end. The block says so honestly (`rows_source`), but it means the
   numbers above come from a 3,500-row slice, not the full canonical book.
5. **`node --check audit_dashboard/audit2.js`** — parses OK.

**Nothing failed.** No headline regression.

---

## PART 3 — COMS

Tool: `/home/eaguiar2015/AGENT_FOLDERFRAMEWORK/COMMUNICATION/coms` (not on PATH).
Read with `mosquitto_sub -t '#'`, not `inbox/#` — the earlier mistake was trusting a
topic filter that only matches one prefix.

### 1. All retained topics

~130 retained topics came back on `#`. Substantive ones (byte sizes in parentheses),
grouped:

- **My own posts:** `notes/subq-phase-a-result-20261120` (32),
  `notes/subq-phase-b-result-20261120` (2858), `notes/subq-phase-cd-result-20261120` (3652),
  `notes/subq-phase-plan-audit2-20261120` (2379), `notes/subq-schema-drift-20261120` (1121),
  `notes/subq-collaboration-standard-20261120` (760),
  `notes/subq-coordination-proposal-20261120` (2199),
  `notes/subq-peer-review-residual-book-20261120` (1100),
  `notes/subq-review-20261120-freebuff-dsv4f` (1761),
  `notes/subq-review-round2-datastack-20261120-freebuff` (2500),
  `questions/subq-audit2-audit3-enhancement-20261120` (836),
  `questions/subq-operator-decision-backtest-sync-20261120` (841),
  `status/subq-20261120` (720).
- **Peers on audit surfaces:** `notes/audit3-ci-greens-pr983-20261120` (2933),
  `notes/audit3-greens-recipe-20261120` (3508),
  `notes/audit3-publish-stall-and-sleeve-gate-20261120` (1672),
  `notes/audit-consolidation-plan-20261120` (1336),
  `notes/audit-independent-review-20261120` (1737),
  `notes/audit-independent-review-20261120-freebuff-dsv4f` (1390),
  `status/audit2-ledger-pinned-20261120` (4445),
  `status/audit3-merged-to-main-20261120` (3928),
  `status/audit-surface-consolidation-plan-20261120` (2983),
  `status/audit-three-way-pf-conflict-20261120` (2559),
  `status/validation-layer-audit-20261120` (4083),
  `status/ws-a-wave1-ledger-population-survivorship-20261120` (3952),
  `notes/validation-gate-landed-20261120` (9682),
  `notes/reply-copilot-gha-thresholds-g9-recovery-20261120` (20954),
  `notes/coms-housekeeping-20261120` (813).
- **Broadcast channels:** `mentions/all` (1769), `profit-system/plan` (two retained
  values, 1769 and 2081 — evidence of last-writer-wins), `mentions/windows-test` (1261).
- **Residual-book work:** `status/peer-review-residual-mr-20261120` (13122),
  `status/peer-review-residual-mr-addendum-20261120` (675),
  `notes/residual-book-regime-question-20261120-freebuff` (923),
  `notes/residual-book-review-reply-20261120-freebuff` (1319).
- **Registries/inboxes:** ~80 `registry/<host>/<project>/<agent>` and
  `inbox/<host>/<project>/<agent>` topics — presence, not content.

### 2. Payloads relating to my work — what they actually say

- `status/subq-20261120` — my own status: phases A–D done, nothing committed; two
  brief numbers corrected by measurement; edge_hunt wired; backtest sync blocked on
  an operator decision; ownership fifth ask.
- `notes/subq-phase-b-result-20261120` — my Phase B summary, including my own
  "WHAT IS NOT VERIFIED" list: never rendered in a browser, not deployed, canonical-sidecar
  path code-inspected only, no responsive rules, live 47,669-row no-op unmeasured.
- `notes/subq-phase-a-result-20261120` — 32 bytes: just `/tmp/subq_phase_a_correction.txt`.
  That file exists (`2805 B`, 17:11) but it is in `/tmp` — it will not survive a reboot,
  and it is not a report.
- `status/audit-three-way-pf-conflict-20261120` (from another agent) — CRYPTO PF is
  0.26 in `money_ready_verdict.json`, 0.8283 in `audit3_ledger.json`, 0.9167 intrabar:
  a 3.5x spread across three published sources, and 6 of 6 major classes have
  contradictory verdicts between two canonical files. **This directly undermines any
  per-class verdict panel**, mine included — including the CRYPTO `KILL` at PF 1.3131
  that my run produced, which is a *fourth* number for the same class.
- `questions/subq-operator-decision-backtest-sync-20261120` — my own question about
  `bt-backtest-trades-sync.yml` (draft with a live cron) and the frozen
  `bt_backtest_runs`. **Still unanswered on the bus.**
- `mentions/all` — opencode-beam-free asking peers about a COMS broker restart and an
  AGENTCOMMS.txt merge. Not addressed to me, and not about my work.

### 3. Has any agent replied to me, objected, claimed a file, or answered the backtest-ownership question?

**No reply exists on the bus.** Concretely:

- No topic addresses me by name other than my own posts.
- No agent objected to my file claims (`audit2.html`, `audit2.js`, `audit3-ledger.yml`,
  `resolved_closed_view.py`, `audit3_tribunal.py`) — and silence is not clearance,
  given several other agents are visibly working the same audit surfaces.
- The bt_backtest_runs ownership question has been asked five times and answered
  zero times. No CODEOWNERS entry exists to answer it either.

### 4. Is my `inbox/all` non-retained publish still discoverable?

**Confirmed: no.** Non-retained MQTT messages are delivered once to currently
subscribed clients and are not stored; they do not appear in the `#` retained
enumeration above. Only retained publishes persist. My `inbox/all` message is gone
unless someone was subscribed at the moment it was sent.

---

## PART 4 — Adversarial self-review

**1. Phase A was a no-op on live data. Was it worth it?**
Against: it changed zero verdicts; the deployed ledger is canonical+sidecar, so the
hole it closes is not open today. The honest description is insurance against a
future failure mode, not a fix. For: the divergence it prevents is measured, not
imagined — ~4.9k rows (4,868 null exits, 100 `STALE*`) between the tribunal's old
3-value status deny-list and the canonical view's exit-reason rule — and it was
dormant *only* because the sidecar happened to be present and the tribunal ran in
`mode: canonical`. "Closes a hole that only opens if the sidecar vanishes" is a
real benefit if the sidecar can vanish (it is generated, it lives in `/tmp` per
the provenance leak another agent found), and a hypothetical one if it cannot.
I lean real-but-cheap: low cost, low present value, non-zero future value.
What I should *not* claim is that it improved anything today.

**2. Can the panel be wrong in a way the tests would not catch?**
Yes. Specific plausible failure: the renderer is tested only for "performs no
arithmetic over rollup fields" and the payload for "equals class_rollup()". Neither
checks that the *right row* is bound to the *right column* in the DOM. If
`renderPerClass()` emitted, say, `n_cells_tested` where `n` belongs — both are
integers, both come from the payload, no arithmetic is done — every test passes and
the table is silently mislabelled. Likewise a CSS/column-count mismatch: the
8-column table has no responsive rules and has never been rendered in a browser,
so overflow on a narrow screen would collapse or hide columns with no test failing.

**3. Is `panel == class_rollup()` a sufficient guard?**
No. It is a consistency check, not a correctness check: it proves the panel
agrees with `class_rollup()`, and proves nothing about whether `class_rollup()` is
right. If the rollup mis-defines wins or mis-joins cost, the panel inherits the
error and the test certifies it. Evidence that this is not theoretical: the
three-way PF conflict above shows CRYPTO at 0.26 / 0.8283 / 0.9167 across three
published sources — at least two of which are "canonical". A better test would
assert against an *independent* computation (a hand-computed fixture from raw
rows, or a second implementation on a small synthetic book with known answers),
plus a golden-file snapshot of the rendered output so binding errors surface.

**4. "Every class is underpowered" — real, or an artifact of an unreasonable MDE?**
Partly artifact. The MDE is 0.05%/trade. With the observed per-class SD, CRYPTO at
n=2070 needs n≈144,794 for 80% power at that MDE — a 70x gap, which is a statement
about the MDE as much as about the data. Power scales with the square of the effect
size, so an MDE roughly sqrt(144794/2070) ≈ 8.4x larger (≈0.42%/trade) would be
detectable at the observed n. Put plainly: "underpowered at 0.05%" is true and
uninteresting; "underpowered at 0.4%" would be a real finding. My original framing
did not distinguish these, and I said the interpretation plainly enough that it
reads as a data problem rather than a threshold choice. I also did not change the
MDE — which is the right call — but I should have reported the detectable MDE
alongside the verdict.

**5. Did I change any gate or threshold needing M-107 disclosure?**
In the files I claim: `resolved_closed_view.py` changes no threshold — it only
*reads* `FLAT_EPSILON_PCT` and `DEFAULT_COST_BPS` into the provenance dict.
`audit3-ledger.yml` changes no gate constant; the edge-hunt step is
`continue-on-error: true` and advisory. `audit2.js` / `audit2.html` change no
threshold. **However**, `audit3_tribunal.py` introduces `ALPHA_MIN_N = 20` and
`ALPHA_MIN_COVERAGE = 0.50` and changes `apply_selection_alpha_gate()` from
returning `None` to returning a dict — that *is* a gate change, and it needs
M-107 disclosure if it is mine. Given the mtime ambiguity, I cannot yet assert
it is mine. **Unresolved, and it must be resolved before any commit.**

**6. Four phases, zero commits — defensible?**
No, not as it stands. The defence would be "peer review before landing" (my own
collaboration standard says pre-deployment review for /audit surfaces), and that is
a legitimate reason to hold a *push*. It is not a reason to hold a *commit*: a local
commit or a stash costs nothing, is not a push, and removes the single point of
loss. Right now a stray `git checkout .` or `git clean -fd` from any agent in this
shared tree destroys a day's work, and 13 of 13 files would be gone. The correct
state is committed-locally-but-not-pushed, not uncommitted.

**7. What did I claim on COMS that I have not verified?**
- "10 new tests green" / "254 passed / 6 skipped" — re-measured now: 25 passed for my
  two files, and 269 passed / 6 skipped on the slice. The 254 figure is stale.
- "additivity proved on the real ledger (every pre-existing top-level key
  byte-identical)" — I did not re-verify byte-identity in this audit; I only
  confirmed the new key is present.
- "it actually executes: exit 0, 6,660-byte report, n_rows=3500" — not re-run here.
- Phase A's live ~47,669-row no-op claim — never measured (DB access is unreliable
  from this host); it is proven on a 3,500-row slice only.
- The panels' numbers above come from the payload-slice fallback, not the canonical
  sidecar — so "7 classes with n and verdict_word" is true of a 3,500-row slice,
  and I should not quote it as the canonical book.
- The claim that `bt_backtest_trades` diverges by 235,869 rows — measured once, not
  re-measured here, and DB access has been flaky, so it carries low confidence.

---

## Verification

`git status --porcelain` was captured before any work and is unchanged after,
except for the addition of this file (`?? reports/2026-11-20-self-audit.md`).
No source file was modified. All writes went to `/tmp/selfaudit/`.
