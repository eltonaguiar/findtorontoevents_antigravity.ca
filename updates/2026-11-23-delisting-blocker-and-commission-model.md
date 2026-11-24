# Delisting-aware universe: blocked on source, and commission: modelled not measured

**Date:** 2026-11-23
**Files:** `reports/delisting_data_probe_20261123.json`, `tools/equity_commission_model.py`,
`reports/equity_commission_model_20261123.json`
**Status:** one request cannot be satisfied as asked (no source); one is satisfiable but not as a measurement

Two asks arrived together, and both turn on the same distinction: what the data can support
versus what a label can be made to say.

## 1. A delisting-aware universe — BLOCKED, with evidence

**The ask:** replace the survivorship-flagged 44-name universe with a delisting-aware one, so the
H-201 pod's PASS becomes nameable.

**Why it cannot be done here.** A delisting-aware universe is not built by relabelling; it is
built by *including the names that died*. So I probed whether any available source can return
their prices: 12 tickers that genuinely stopped trading in or after the window
(TWTR, ATVI, VMW, SPLK, PXD, HES, K, DISCA, ANTM, FRC, SIVB, BBBY) plus two known survivors as
controls.

| Result | Count |
|---|---|
| Genuinely delisted names probed | 12 |
| Delisted names with any usable series | **0** |
| Controls that resolved (proves the fetch path works) | 2 of 2 |

Every delisted ticker returned `0 bars` with `possibly delisted; no timezone found`. The controls
returned 1,269 bars each, so this is not a broken fetch — the data does not exist on this source.

BBBY is the trap worth naming: it returned **89 bars starting 2026-07-17**. That is a different
issuer reusing a dead symbol. Accepting it would inject a fabricated history into a universe whose
entire purpose is bias control — the failure mode dressed as the fix.

**What I deliberately did not do:** invent a universe by injecting a synthetic death rate. A
simulated hazard is a legitimate *sensitivity test* — "how much would delisting have to hurt to
erase the edge?" — but it is not a replacement universe, and calling it one is precisely the
relabelling the flag exists to prevent.

**Consequence:** the verdict stays capped at `CANDIDATE_SURVIVORSHIP_FLAGGED`. The count bar is
met; its purpose is not. A KILL stays admissible, because failing to clear zero *despite* upward
bias is the stronger result.

**What would unblock it:** CRSP, Norgate, Polygon (with delisted), or Tiingo — keyed. None is.
This is the same blocker already logged as COMS ask A1, now carrying a probe instead of an
assumption.

## 2. Equity commission — modelled, and the scalar assumption is falsifiable

**The ask:** measure the commission component so the pod's cost basis stops being an assumption.

**It still is an assumption, and I will not call it anything else.** No broker fill with a
commission field exists anywhere in this repo; the paper surfaces record prices, not fees. What I
could do is make the assumption *checkable*: `tools/equity_commission_model.py` converts published
per-share schedules into basis points across the ticket sizes a 3-name pod actually trades.

The result is not a single number, and that is the finding:

| Schedule | bp/side range | median | cells at or below 1 bp |
|---|---|---|---|
| IBKR fixed ($0.005/sh, $1 min) | 0.400 .. 10.000 | 4.000 | **8 of 30** |
| IBKR tiered ($0.0035/sh, $0.35 min) | 0.140 .. 3.500 | 1.400 | 12 of 30 |
| Zero-commission retail | 0.000 | 0.000 | 30 of 30 |

(I first wrote the fixed row as 0.20–10.00 / median 1.00 / 16 of 30 from memory. The tool says
otherwise, and the tool is what is committed.)

**The binding constraint is the minimum ticket fee, which is not scale-invariant.** The $1.00
floor alone is 10 bp on a \$1,000 ticket, 4 bp at \$2,500, 1 bp at \$10,000 and 0.4 bp at \$25,000.
So `commission_bp_per_side: 1` is honest at \$10k+ tickets and materially optimistic below \$2,500 —
by 3 to 9 bp on the fixed schedule.

**And the per-share basis is price-dependent at fixed notional**, which is the part a single
scalar hides completely: at \$25,000, a \$500 stock costs 0.40 bp but a \$10 stock costs 5.00 bp,
because the fee is charged per share and a low price buys more of them. Commission is therefore a
function of (broker, ticket size, share price), and `1` is not an estimate of it — it is a guess
that happens to land in the middle of the distribution.

**Consequence for the pod:** 11 bp/side (10 slip + 1 commission) may understate total cost on
small tickets. The fix is not a new scalar; it is to **state the ticket size** alongside the cost
basis, because without it the figure is not reproducible and cannot be checked by a reader.

**Label discipline:** every output carries `MODEL_NOT_MEASURED` and a `do_not_report_as:
"measured equity cost"` field. A modelled number that gets quoted as measured is how a cost
assumption becomes a false precision.

## Verification

- `python3 tools/equity_commission_model.py` → 90 cells written to
  `reports/equity_commission_model_20261123.json`; ranges and floor table above are its output,
  not hand-copied.
- Delisting probe: 14 tickers fetched live; 2 controls resolved with 1,269 bars each, confirming
  the fetcher itself works before concluding the delisted names are absent.
- `py_compile` on the new tool.

## Limits

- The commission schedules are **inputs I typed from published fee tables**, not observations of
  this programme's own trading. They bound the question; they do not answer it.
- The zero-commission schedule hides its cost in spread and payment-for-order-flow, which the
  measured 6.04 bp/side spread already contains — so 0 bp commission plus 6.04 spread is not
  automatically cheaper than 1 bp commission plus 6.04 spread.
- Nothing here changes the H-201 verdict. It is still 15 days, still below its own 20-day gate.
