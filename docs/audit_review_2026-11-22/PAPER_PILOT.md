# Paper pilot for the one CANDIDATE cell — blocked, and exactly why

**Date:** 2026-11-22
**Cell:** `mega_mutation` family, the only `CANDIDATE` cell in the frozen ledger.
**Pod:** `POD-MEGA-MUTATION-CANDIDATE`, hypothesis `H-2026-11-22-01`, `n_forward` 0, status `observe`,
`eligible` false, registered in `audit_dashboard/data/audit2_pods.json`.

## What the cell actually is

From the frozen ledger capture `[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:32427]`
(`"family": "mega_mutation"`), the cell carries: n 128, WR 0.5547, PF net 1.7363, net CI
[0.0826, 2.0286], split-half stable (0.8415 then 1.3629), `top_symbol_share` 0.1953
`[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:32472]`, `top_source_share` 0.8203
`[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:32473]`, and `stress_2x_ok` false
`[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:32457]`.

## The blocker: the paper request cannot be filled

`AGENTS.md` (Fleet Coordination) requires five fields for a paper-trade request: symbol,
entry/limit price, TP, SL, and justification. This cell supplies exactly one of them.

| Required field | Value from the ledger | Status |
|---|---|---|
| symbol | not present | **MISSING** |
| entry / limit price | not present | **MISSING** |
| TP | not present | **MISSING** |
| SL | not present | **MISSING** |
| justification | `mega_mutation` family, CANDIDATE, n 128, PF net 1.7363 | present |

The cell has a `top_symbol_share` of 0.1953 but no `symbol` field, so even the leading symbol is
not named: the share says one symbol holds about a fifth of the trades, not which one. The cell has
no class field, no direction field, and no price levels. Entry, TP, and SL are exit geometry that
lives in the strategy definition, not in a performance summary.

## What is missing, precisely

**A `symbol` (and with it a class and a direction) attached to the `mega_mutation` cell, plus the
strategy's entry/TP/SL rule.** Any of the following would unblock it:

1. The `mega_mutation` strategy definition or emitter, which would name the universe and the exit
   rules. I did not locate it in this pass.
2. A per-trade dump behind the cell (the ledger aggregates 128 rows into one summary), from which
   the dominant symbol and the entry/exit prices could be read directly.
3. A decision by the owner to pre-register the pilot on a named instrument of choice, which would
   no longer be "the symbol the cell actually trades" and must be labelled as such.

## What I did NOT do

I did not invent a symbol, a price, or a level. A paper order on a guessed symbol would produce
forward rows that look like evidence for `mega_mutation` while measuring something else, and those
rows would then feed the forward gate. That is worse than no rows.

## Proposed next step

Resolve item 1 or 2 above, then emit the five-field request and let the existing 6-hourly ledger cron
advance `n_forward` from 0. The kill rule is already pre-registered in the pod:
`at n>=100: forward net PF CI-LB <= 1.0 OR selection alpha CI-LB <= 0`.
