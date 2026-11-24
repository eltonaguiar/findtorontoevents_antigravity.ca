# Pilot-rate extrapolation: provenance correction

**Date:** 2026-11-23 · **Author:** this agent · **Kind:** self-correction of my own words.

This note corrects figures **I** have been quoting. It corrects no one else's document.
The documents on `main` that state the pilot's status (`docs/edge_research/25_DRAFT_RANKED_LIST_2026-11-23.md`,
`docs/edge_research/26_FINAL_RANKED_LIST_2026-11-23.md`) are correct as written; the error is in my
repetition of them with numbers that are not theirs.

---

## 1. The claim under correction

I have stated, as if they were recorded facts:

- pilot `n≥20 ~2026-12-03`
- pilot `n≥100 ~2027-01-25`
- `~1.5 closes/day`

**None of these is a statement on `main`.** The two dates and the rate are **my own arithmetic**,
extrapolated from a handful of observed closes. They are not measured, not recorded, and not in any
committed document.

## 2. The derivation, shown

The input is the committed paper log
`verified_strategies/paper_pilot/crypto_intraday_sim_paper_log.jsonl`, which **is** on `main`
(`git cat-file -e origin/main:...` → exit 0). As of pre-merge `origin/main`
`20a029e6434790488507defc731c8a8fc1f3b24e` it holds **12 lines**, of which exactly **5 are
`"event": "CLOSE"` rows**:

| Exit timestamp | CLOSE rows |
|---|---|
| `2026-11-20T12:00:00+00:00` | 3 |
| `2026-11-22T12:00:00+00:00` | 2 |

The earliest entry in the log is `2026-11-19T16:00:00+00:00`; the latest exit is
`2026-11-22T12:00:00+00:00` (the file's last committed row date is `2026-11-22`).

- **`~1.5 closes/day`** = 5 closes ÷ (3 days from 2026-11-19 to 2026-11-22) ≈ 1.67, or ÷ 3.33 days from the
  earliest entry to the last exit ≈ 1.5. The figure depends on which window I pick, which is itself a
  sign the sample is too small to carry it.
- **`n≥20 ~2026-12-03`** = 15 more closes at ~1.5/day = 10 days from 2026-11-22.
- **`n≥100 ~2027-01-25`** = 95 more closes at ~1.5/day = ~63 days from 2026-11-22.

Reproduce the counts yourself with:
`git show origin/main:verified_strategies/paper_pilot/crypto_intraday_sim_paper_log.jsonl | grep -c '"event": "CLOSE"'`

Note that the log *is* reachable, but the 1.5/day rate is a choice I made from it, not a value the file
records — so the **dates** are not reproducible from the repo, only my arithmetic is.

## 3. What `main` actually records

- `docs/edge_research/25_DRAFT_RANKED_LIST_2026-11-23.md:110`:
  > **Earliest resolution:** the day-30 checkpoint from registration (2026-11-19) is **2026-12-19**, day-60 is **2027-01-18**; the date for n ≥ 100 is `UNMEASURED` (0 closes so far, no observed close rate).
- `docs/edge_research/25_DRAFT_RANKED_LIST_2026-11-23.md:107`:
  > **Net PF CI-LB:** `UNMEASURED` — with zero closed rows there is no PF, hence no CI.

So `main` records the n≥100 date as **`UNMEASURED` because no close rate is recorded** — the opposite of
me quoting a date for it.

**Correct gates from `main`** (`25_DRAFT_RANKED_LIST_2026-11-23.md:110`; the day-30 date is repeated at
`26_FINAL_RANKED_LIST_2026-11-23.md:61`):

- day-30 gate: **2026-12-19**
- day-60 gate: **2027-01-18**

## 4. Honest conclusion

Five closes cannot support a rate. Two of the three days in the window produced no closes, and the rate
changes by ~10% depending on where the window is started. The extrapolated dates (`~2026-12-03`,
`~2027-01-25`) should **not** be relied on, and I should stop quoting them.

The only defensible statement is:

> **The pilot is accumulating closes at a rate too low to reach a judgement threshold inside the current
> gate window, and the exact date is unknown.**

That is a statement about the *rate being inadequate*, which 5 closes over 3 days does support (the
day-30 gate is 2026-12-19, ~27 days out, and ~20 closes at 1.5/day would be needed to even assess the
n≥20 judgement; the n≥100 clause is plainly out of reach in that window). It is **not** a claim about a
specific date, which I cannot support.

---

**Provenance:** log row counts and timestamps read from
`origin/main:verified_strategies/paper_pilot/crypto_intraday_sim_paper_log.jsonl` at
`20a029e6434790488507defc731c8a8fc1f3b24e`; `UNMEASURED` and gate dates cited to
`docs/edge_research/25_DRAFT_RANKED_LIST_2026-11-23.md:110` (and `:107`), with `26_FINAL_RANKED_LIST_2026-11-23.md:61`
repeating the day-30 date. The derivation arithmetic is mine and is shown above so it can be checked.
