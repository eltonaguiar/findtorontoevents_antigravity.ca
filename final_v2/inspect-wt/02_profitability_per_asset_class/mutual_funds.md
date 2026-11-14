# MUTUAL FUNDS — how to get profitable (deepAI)

## My measured truth (live, 2026-11-14)
- Active: **2 picks total** (FCNTX, FBGRX — mutual-fund share classes), zero repricing possible
  (no exchange quotes), 0 closed ever.
- Session-1 audit: `money_ready` claims "1/1 classes ready" on essentially empty data —
  the class is vaporware with a green badge (my `fixspec_mutual_fund_vaporware` specifies
  the file:line fix).

## Peer consensus
finpredict roadmap states it cleanly: **no intraday edge is possible** (monthly NAV, no
mark-to-market); de-advertise. finpredict-v3 and flaxen-hair list the same coverage gap.
No peer proposes building this class — and none should.

## My plan
1. **De-advertise (`NOT_BUILT`)** — remove from money-ready math, show coverage=0 honestly.
   Fixspec already written; it is a label change, not a data project.
2. **Do not build a live pick class.** Monthly NAV cannot support TP/SL intrabar resolution,
   the resolver pipeline, or any of this system's machinery — building it would manufacture
   more fake 0% rows (the exact defect class this audit spent the day proving).
3. **If (and only if) someone insists:** the sole defensible product is a **monthly
   tactical-rotation backtest vs a risk-matched benchmark** — a research note, never a
   live-pick surface, never counted in money-ready stats.

**Tradable today: NO — permanently, by instrument nature.** The profitable move for this class
is subtraction: fewer classes reported honestly beats more classes faking coverage.
