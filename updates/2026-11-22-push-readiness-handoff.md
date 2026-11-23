# Push-readiness handoff — 8 programme commits (2026-11-22)

**Status: NOTHING WAS PUSHED.** This document is a verification record only. The push
decision belongs to the human. No remote ref, no `origin/main`, and no working-tree file
was modified by this verification pass.

Verified at: 2026-11-22T23:25Z, workspace `/home/eaguiar2015/findtorontoevents_antigravity.ca`.

---

## Headline

**Yes for 7 of 8, with one recorded scope deviation.** All 8 commits resolve, all 8 have
the stated parent, all 8 are unmerged relative to `origin/main`, and none carries a
foreign path from the known-foreign list. Commit 6 (`559e7795320`) is content-clean but
was **not requested** — see the `SCOPE_DEVIATION` section. If the human wants strict
brief compliance, push 7 and drop that one.

---

## 1. The 8-commit table (verified)

| # | Commit | Branch | Parent | Files | +/- | Purpose | Result |
|---|--------|--------|--------|-------|-----|---------|--------|
| 1 | `24db34304c9` | `push/m2-forex-cost-2026-11-22` | `1c15c5d7d` ✔ | 9 | +7739 / −4 | M2 FOREX cost measured (Sunday-reopen upper bound); no verdict moved | **PASS** |
| 2 | `692d30d7e62` | `m2-residual/fx-cost-overlap-scheduler` | `24db34304c9` ✔ | 5 | +1001 / −46 | Weekday London/NY-overlap scheduler + guard for FOREX cost | **PASS** |
| 3 | `3f76b104066` | `m1-equity-cost-measurement` | `692d30d7e62` ✔ | 7 | +1693 / −4 | M1 EQUITY cost measured (upper bound); no verdict moved | **PASS** |
| 4 | `87a2e0cbe2f` | `m3-cost-triage-2026-11-22` | `3f76b104066` ✔ | 12 | +1561 / −0 | M3 triage: 0 of 6 UNKNOWN rows are cost-addressable | **PASS** |
| 5 | `649aa763afd` | `research/m1-provenance-repair` | `87a2e0cbe2f` ✔ | 8 | +1548 / −19 | Provenance repair: 12.07 bp was real, the artifact was stale + tripwire test | **PASS** |
| 6 | `559e7795320` | `research/m1-provenance-repair` (same branch as 5) | `649aa763afd` ✔ | 1 | +80 / −0 | **Unrequested** `docs/EDGE_CANDIDATES_2026-11-22.md` | **PASS (SCOPE_DEVIATION)** |
| 7 | `8229bb6d015` | `closing-edge-programme-2026-11-22` | `649aa763afd` ✔ | 1 | +177 / −0 | Definitive answer doc 23 | **PASS** |
| 8 | `59f536ce2a5` | `reconcile/tally-enumeration` | `8229bb6d015` ✔ | 5 | +287 / −21 | Tally reconciled by enumeration (0 INV / 10 NOT_INV / 4 UNK over 14 rows) + consistency test | **PASS** |

Every parent matches the brief exactly. `git cat-file -t` returned `commit` for all 8
(no dangling or unreachable objects).

### Sibling relationship (commits 6 and 7)

`559e7795320` and `8229bb6d015` **both** have parent `649aa763afd`. They are **siblings**,
not a chain. Consequences:

- Each is independently pushable to its own ref. Neither depends on the other.
- `59f536ce2a5` (commit 8) descends from `8229bb6d015` (commit 7), **not** from
  `559e7795320`. So dropping commit 6 leaves the chain 1→2→3→4→5→7→8 fully intact.
- The brief's "intended order" list is a reading order, not a linear history; the
  handoff record should not imply 6 precedes 7 in ancestry.

---

## 2. File-list audit against the allowlist

Known-foreign paths checked in every commit: `paper_trading/live_sim/**`,
`reports/weekly_scorecard/*`, `reports/PROTOCOL_V1_ACKS.md`, `___HELL_HEALTH_OPENCODE.MD`,
`alpha_engine/production_scanner.py`, `tools/provenance_resolver.py`,
`plans/2026-11-22-coms-review-and-todos.md`, `docs/TODO_LEDGER_2026-11-22.md`,
`tools/todo_wakeup_runner.py`, `.todo_wakeup_state.json`.

**Result: no `FOREIGN_PATH_PRESENT` in any of the 8 commits.** All 8 are clean on the
known-foreign list.

One item needs explanation rather than a bare pass. Commits 3 and 4 do touch
`docs/audit_review_2026-11-22/{02_EQUITY,03_ETF,04_FOREX,05_COMMODITY,06_BOND,09_PENNY_STOCK,10_MEMECOIN,11_INDEX}.md`.
The brief flags those as "another author's pre-existing edits". Inspection of the diffs
shows the hunks are this programme's own cost-measurement annotations: each adds a
`[SRC: reports/equity_cost_measurement/…json]` line under the `## 6 Cost reality`
heading, carrying the M1/M3 numbers (12.07 bp equity, TLT 2.51 bp, SPY 8.31 / QQQ 12.07 /
IWM 7.75 / DIA 5.59 bp, DOGE 6.79 bp with SHIB rejected as tick truncation, and
`NO_INSTRUMENT_IN_REPO` for penny stocks). They are additive, one-to-two-line, and
attributed to the programme's own artifacts. They are therefore **not** foreign content,
but they do mean these 8 dossier files are part of the programme's footprint and a human
reviewing the push should know it. The separate dirty working-tree copies of the same
files (`git status` shows them modified) are the concurrent agent's and were **not**
included in any of the 8 commits.

---

## 3. Ancestry / merge check

`origin/main` at verification time: **`128fa19794f`** (`128fa19794fcb292858bdac40129d69e184c94ea`).

The brief quoted `5bbcbe1f7c8a` → `b75fcd0c573`; both exist locally, and `origin/main` has
since moved again to `128fa19794f`. The moving target is exactly why the check is done by
ancestry, not by sha equality.

| Commit | `merge-base --is-ancestor origin/main <sha>` |
|--------|----------------------------------------------|
| `24db34304c9` | **false** |
| `692d30d7e62` | **false** |
| `3f76b104066` | **false** |
| `87a2e0cbe2f` | **false** |
| `649aa763afd` | **false** |
| `559e7795320` | **false** |
| `8229bb6d015` | **false** |
| `59f536ce2a5` | **false** |

**All 8 false, as expected.** `origin/main` is not an ancestor of any of them, so none of
them contains `origin/main`'s history and no merge of `origin/main` is implied. The
converse (is any of them an ancestor of `origin/main`?) is also false: none of the 8 is
already in `origin/main` history, and `git branch -r --contains <sha>` returns empty for
all 8, i.e. no remote branch contains any of them yet.

---

## 4. No history rewrite is implied

Pushing each commit to its **own new branch ref** (`refs/heads/<branch>`):

- **cannot rewrite `origin/main`** — a refspec naming a different ref never touches it;
- **cannot force-update any existing remote branch** — none of these refs exist remotely
  (`git branch -r --contains` is empty for all 8), so each push is a create, not an update;
  a create-only push needs no force and a non-fast-forward rejection is impossible;
- **cannot delete anything** — no refspec uses a leading `:` (the delete form).

Already-pushed ref from this work: `push/phase2-round-2026-11-22`.
- Remote (`refs/remotes/origin/push/phase2-round-2026-11-22`): **`1c15c5d7d07`**
- The local `refs/heads/push/phase2-round-2026-11-22` has been advanced by a concurrent
  agent to **`9614cf15639`**, which is **31 commits ahead** of the pushed tip. Those 31
  commits are not mine and must not be pushed under this programme's name.
- Commit 1 (`24db34304c9`) is based directly on the pushed tip `1c15c5d7d07`, so it is a
  clean fast-forward extension of an already-pushed commit.

### Exact refspecs a human would run

Full set (all 8):

```
git push origin 24db34304c9:refs/heads/push/m2-forex-cost-2026-11-22
git push origin 692d30d7e62:refs/heads/m2-residual/fx-cost-overlap-scheduler
git push origin 3f76b104066:refs/heads/m1-equity-cost-measurement
git push origin 87a2e0cbe2f:refs/heads/m3-cost-triage-2026-11-22
git push origin 649aa763afd:refs/heads/research/m1-provenance-repair
git push origin 559e7795320:refs/heads/research/edge-candidates-2026-11-22
git push origin 8229bb6d015:refs/heads/closing-edge-programme-2026-11-22
git push origin 59f536ce2a5:refs/heads/reconcile/tally-enumeration
```

Note on commit 6: it shares the branch name `research/m1-provenance-repair` with commit 5.
Two commits cannot both land on one ref, so the refspec above gives it a distinct ref
(`research/edge-candidates-2026-11-22`). If it is excluded, that refspec is simply omitted.

Set that **skips commit 6** (`559e7795320`):

```
git push origin 24db34304c9:refs/heads/push/m2-forex-cost-2026-11-22
git push origin 692d30d7e62:refs/heads/m2-residual/fx-cost-overlap-scheduler
git push origin 3f76b104066:refs/heads/m1-equity-cost-measurement
git push origin 87a2e0cbe2f:refs/heads/m3-cost-triage-2026-11-22
git push origin 649aa763afd:refs/heads/research/m1-provenance-repair
git push origin 8229bb6d015:refs/heads/closing-edge-programme-2026-11-22
git push origin 59f536ce2a5:refs/heads/reconcile/tally-enumeration
```

---

## 5. `SCOPE_DEVIATION` — commit 6, `559e7795320`

- **File:** `docs/EDGE_CANDIDATES_2026-11-22.md` (1 file, +80)
- **What it is:** a read-only answer to "is there any positive net-of-cost candidate, and
  what about VALUE and PEAD?". Header states scope is this programme's own artifacts,
  read-only, not investment advice, and that an unmeasured field is written `UNKNOWN`,
  never guessed.
- **Content assessment:** honest. VALUE and PEAD are reported as `UNKNOWN` with
  `UNKNOWN / UNKNOWN / UNKNOWN / UNKNOWN / UNKNOWN` for universe / sample /
  bp-per-trade / deflation, explicitly because neither family appears in the 22-doc
  review's 14 rows. No number is quoted from code that was never run.
- **Stale-number caveat (not a defect of the commit, but worth knowing):** it was written
  before commit 8's reconciliation, so it states the pre-reconciliation tally
  `0 INVESTABLE / 8 NOT_INVESTABLE / 6 UNKNOWN`. The settled tally is
  `0 / 10 / 4 over 14 rows`. The document's conclusion is unchanged; only the counts moved.
- **Why it is a deviation:** it was not in the brief. The scope call is the user's.
- **Command to exclude it:** omit
  `git push origin 559e7795320:refs/heads/research/edge-candidates-2026-11-22`
  from the set above.

---

## 6. Operational consequence: `fx-cost-overlap.yml` is inert until pushed

`.github/workflows/fx-cost-overlap.yml` lives only in commit 2 (`692d30d7e62`), which is
unpushed. GitHub Actions runs workflows from the remote default/branch refs, so **this
scheduled job will never fire while the commit stays local.**

- It is scheduled weekdays, 13:00–16:00 UTC (`48 13`, `56 13`, `52 14`, …, `* * 1-5`),
  inside the London/NY overlap.
- Until it is pushed, **FX mean-reversion stays `UNKNOWN`** (break-even 4.3038 bp; the
  only cost number available is the Sunday-reopen upper bound).
- This is expected, not a silent failure. Nobody should wait for a weekday measurement
  that cannot fire.

---

## 7. What was excluded from the handoff commit

The shared working tree is dirty with a concurrent agent's work. These entries were
**not** included in the handoff commit:

- `___HELL_HEALTH_OPENCODE.MD`
- `docs/audit_review_2026-11-22/{02_EQUITY,03_ETF,04_FOREX,05_COMMODITY,06_BOND,09_PENNY_STOCK,10_MEMECOIN,11_INDEX}.md`
  (dirty copies)
- `docs/edge_research/{15_PROGRAMME_SCOREBOARD,22_FINAL_SYNTHESIS}_2026-11-22.md` (dirty copies)
- `paper_trading/live_sim/{bars/*.csv,runs.jsonl,state.json,trades.jsonl}`
- `reports/PROTOCOL_V1_ACKS.md`
- `docs/EDGE_CANDIDATES_2026-11-22.md`, `docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md`
- `plans/2026-11-22-coms-review-and-todos.md`
- `reports/equity_cost_measurement/`, `tests/test_edge_research_tally_consistency.py`,
  `tests/test_m1_cost_provenance.py`, `tools/equity_cost_measure.py`,
  `updates/2026-11-22-m1-{equity-cost-measurement,provenance-repair}.md`,
  `updates/2026-11-22-m3-cost-triage.md`

Only this handoff file was committed, on a new branch cut from `59f536ce2a5`, using a
temporary index so the shared working tree was never committed.
