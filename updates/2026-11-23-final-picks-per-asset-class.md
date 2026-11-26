# Final picks per asset class — delivered to antigravity_review_Nov192026

**Date:** 2026-11-23 · **Owner:** buffy (freebuff) · **Paper only, zero capital, not advice**

## What was asked

Drop final picks per asset class into a date-stamped folder in
`github.com/eltonaguiar/antigravity_review_Nov192026` on `main`, following whatever schema that
folder already uses for revisions.

## What was delivered

`2026-11-23/buffy-freebuff/PICKS.md` + `picks.json` in that repo, matching the schema the existing
`2026-11-23/README.md` defines: `symbol, n, gross_bp, cost_bp, net_bp, dsr, hold_days, gates
G1-G5, gates_passed, FAILS`, ticket size stated ($25,000) for every bp figure.

**Verdict: 0 of 10 pick objects pass all five gates.** EQUITY is 4/5, failing only G3; the five
ETF names are 2/5 with G1/G3/G4 *unmeasurable* rather than failed, because the R4b forward ledger is
empty until 2026-11-30; funding carry is 1/5 (cost is an assumed VIP0 tier); BTC beta is 0/5 and
killed. Six classes carry no pick at all, each with its blocking reason.

## How the numbers were produced (not copied from a dashboard)

- **EQUITY names are computed, not asserted.** Top 3 of the pod's frozen 44-name universe by
  6-month return at the 2026-11-19 close: **XLV +20.77%, KO +19.86%, MSFT +19.35%** (base
  2026-05-21, 44/44 names priced, 0 missing). The doc says explicitly that the pod's recorded book
  is the authority, not this recompute.
- **ETF ranking is computed** from the same cached CSVs the clock reads: **XLE +37.55%, XLV
  +18.24%, XLK +15.77%, IWM +14.32%, EFA +10.09%** (base 2025-11-18), all above the 4.32% hurdle.
  Note the clock's own tooling refuses a pre-`CLOCK_START` as-of date by design, so the ranking was
  taken from the cache read-only rather than by forcing `--allow-past`.
- **Both XLV appearances are flagged** as correlated exposure across two picks.

## Honesty constraints applied

- Gross/net are marked `UNMEASURED` where no forward record exists — the README forbids fabricated
  numbers and I did not annualise an empty ledger.
- The equity cost figure is **12.0749 bp** in my table, and the doc records that a peer measures
  **1–5 bp** on 191 names. It is flagged, not silently reconciled; k* = 50.9 survives either.
- The withdrawn 77-day DSR figure appears nowhere: 137 days at N=29 (C-029).
- Equity `net_bp` carries its basis (cost amortised over a 21-session rebalance). That partial
  turnover assumption is the only assumption in the row, and it is stated.

## Revision protocol (as the folder README requires)

Version 1 is `buffy-freebuff/`. Future updates either append a `## Revision <ISO timestamp>`
section to `PICKS.md` keeping the old one, or move the folder to `OLD/2026-11-23/buffy-freebuff-v1/`
and publish `buffy-freebuff-v2/`. Never overwrite silently.

## Scope note

Another agent's `README.md` and `kilo-vanilla-handsaw/` were untracked in that clone when I arrived.
I committed **only** `buffy-freebuff/` and left theirs untouched, so it is on whoever wrote them to
land them. The README's "Agents present" table therefore does not list me yet; adding the row would
have meant staging their file.
