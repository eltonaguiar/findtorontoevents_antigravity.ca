# Peer Review — the finpredict family (v1, v2, v3, v4) + sibling audits

**Verdict: CORROBORATED.** Four independent methods, one conclusion. Their internal disagreements are
about counts and populations, never about whether the system is profitable. Two of their statements
are now factually stale; one of their self-corrections is exemplary.

## Why their FAIL verdicts are credible

| Dimension | finpredict v1 | v2 | v3 | v4 | Mine (independent) |
|---|---|---|---|---|---|
| Workflows | 365 | 365 | — | 365 | 365 (361 active, 4 disabled, 20 never run) |
| Ledger state | FAIL | FAIL | FAIL | FAIL | FAIL |
| Multiple testing | flagged | quantified | flagged | flagged | DSR/PBO per family |
| Money-ready | 0/9 | 0/9 | 0/9 | 0/9 | 0 emitters at Bonferroni 2.82e-4 |
| Direction of error | losses understated | losses understated | same | same | same (−1.90% displayed vs tracked) |

I arrived at my numbers from the payload + workflow API, not from their documents, and the roots
agree: frozen 0% PnL, zombie EXPIRED rows, single-source domination, unresolved picks, and a
multiple-testing burden that no emitter clears.

## Where their counts differ (and it doesn't matter)

- **Active picks:** v1/v2/v3 say 20 curated / ~4,148 raw; I measured 10 displayed vs **4,361** tracked
  at −1.90%. Different snapshot minutes and different dedup keys. Neither is "wrong"; neither changes
  the verdict.
- **Closed-window PF:** mine is 30d PF 0.804, Σ −443.1pp at WR 41.8%; deepAI's 30d is PF 0.80,
  Σ −424pp; v2 reports −333.2% over n=751 for 14d. Same PF, different windows. The convergence of PF
  at 0.80 across three independent computations on different windows is the strongest single fact in
  this whole review round.

## Stale statements (now corrected by evidence)

1. **v2's `PEER_CROSSREF.md` says** the `audit/live-audit-2026-11-14` branch and the deepAI archives
   are *"NOT PRESENT on this Linux host; not on origin."* That was true at 16:05Z. **It is on origin
   now** — verified via `git for-each-ref` and `git ls-tree` (75 files under `2026-11-14/`). The
   branch also cannot be merged: it is based on `f54efb3b4ac` (2026-06-06) and is 23,488 files apart
   from `main`.
2. **v4's "0 active picks / dashboard_data.json 26d stale"** is a stale-snapshot artifact, as v1/v2
   already established. I confirmed the live endpoint returns `generated_at` same-day with 3,500
   `recent_closed` rows and 20 curated actives. v4's *underlying* point (Alpha Engine unhealthy) is
   correct; its headline count is not.

## Exemplary behaviour worth preserving

- **flaxen-hair retracted its own claim** after finding `dbpasses.txt` at `/home/eaguiar2015/dbpasses.txt`
  rather than in-repo: it printed the retraction inline instead of quietly editing. That is the
  standard the rest of this round should be held to.
- **v2's veto list** (no `DELETE` of ghost rows, no `UPDATE TIME_EXIT → LOST, pnl=0.0`, no mass
  rewrite, no unblocking FUTURES/COMMODITY without a feed) is correct and I endorse all of it. Any
  fix that fabricates an outcome to clean a denominator is worse than the defect it removes.
- **v2's correction table** (248 dup groups / 297 extra rows / 177 entry-differing OPEN / 7 classes
  WR>100%) is the most useful reconciliation artifact produced by any peer, and it matches my
  `summary_picks` finding that wins+losses exceed resolved.

## Disagreements I hold against the family

- **v2 treats "backbone = v2, checklist = scratch QW-ALL-1..9" as settled.** It isn't: the sequencing
  is right, but the acceptance tests are mostly "field exists", not "number is honest". My plan
  (`02_my_findings/2026-11-14-quant-remediation-plan.md`) replaces them with falsifiable gates —
  e.g. `resolved + expired + open = emissions` and "a synthetic null panel must reject ≥95%".
- **Nobody in the family fixed `resolution_method`.** It is `None` for 100% of the 3,500-row
  `recent_closed` ledger. Until that exists, every PF any peer computes — including deepAI's
  reproduced variant C — is a PF of unknown exit provenance. This is the highest-value single field
  in the entire review round.
