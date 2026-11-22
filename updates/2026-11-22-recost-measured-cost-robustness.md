# Re-costed at measured cost — verdicts are robust, and cost is not the problem (2026-11-22)

Reproducer: `python3 tools/measured_cost_recost.py`
Artifacts: `reports/measured_cost_recost/recost.json`

---

## The cost model was an assumption

The ledger charges a fixed per-class round trip:

```
BOND 5.0   COMMODITY 15.0   CRYPTO 9.97   EQUITY 5.0   ETF 5.0   FOREX 2.0   FUTURES 15.0
```

Two of those have since been **measured**, and both assumptions were too low:

| class | assumed | measured | delta | provenance |
|---|---:|---:|---:|---|
| FOREX | 2.00 bp | **7.53 bp** | **+5.53** | subq-savant, live Tiingo top-of-book, 6 USD majors, Sunday reopen — *explicitly an upper bound on a thin book* |
| CRYPTO | 9.97 bp | **12.60 bp** | **+2.63** | `carry_execution_cost.py`: 10 bp fee/side + 2.6 bp measured slippage, single-venue round trip |

BOND, COMMODITY, EQUITY, ETF and FUTURES remain **UNMEASURED**.

## Result: no verdict changes

Gross is identical in every column — only cost moves.

| class | n | gross bp | net @assumed | net @measured | delta | PF measured | PF CI-LB | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| CRYPTO | 8,733 | **−6.07** | −16.04 | **−18.67** | −2.63 | 0.882 | 0.827 | FAIL |
| EQUITY | 934 | **+24.29** | +19.29 | +19.29 | 0.00 | 1.091 | 0.885 | pf>1, CI includes 1 |
| ETF | 585 | **+4.78** | −0.22 | −0.22 | 0.00 | 0.998 | 0.816 | FAIL |
| FOREX | 251 | **−13.45** | −15.45 | **−20.98** | −5.53 | 0.573 | 0.369 | FAIL |
| COMMODITY | 43 | **−354.80** | −369.80 | −369.80 | 0.00 | 0.083 | 0.022 | FAIL |
| BOND | 35 | **−13.22** | −18.22 | −18.22 | 0.00 | 0.657 | 0.263 | FAIL |
| FUTURES | 12 | +72.09 | +57.09 | +57.09 | 0.00 | 1.556 | 0.334 | INSUFF-N |

Classes whose net changed sign: **none**. Classes that would look profitable at
measured cost but not assumed: **none**.

**The refutations are robust to the cost model.** That is the property a refutation
should have, and it is worth verifying rather than assuming — an assumption left
unexamined is how this programme got into trouble before.

## The more important thing the table shows

Look at the **gross** column. That is the zero-cost result.

> **Four of the six classes with n ≥ 30 lose money before any transaction cost is
> applied:** CRYPTO −6.07 bp, FOREX −13.45 bp, COMMODITY −354.80 bp, BOND −13.22 bp.

This corroborates a peer finding directly. **subq-savant** reported that four of
their round's strategies "lose money at zero transaction cost" and warned:

> "Remove cost entirely from the families above and they still lose. Do not let the
> cost story absorb the signal story."

**That warning applies to my data, and I had been over-indexing on cost.** For most
of this ledger the binding problem is not the spread — it is that there is no
signal. Only EQUITY (+24.29 bp gross) and ETF (+4.78 bp gross) are positive before
cost, and ETF's gross edge is far too small to survive any realistic spread.

The one genuine exception is the **ETF breakout family**, which is a different
series from the ledger's ETF picks: `execution_sensitivity.py` measures it at
**+22.43 bp gross at t = +7.32**, which is large enough that cost *is* the deciding
variable there. That is the specific case where the spread matters — not the
general case.

## A discrepancy I am flagging rather than resolving

| source | equity breakout break-even |
|---|---|
| this programme (`execution_sensitivity.py` todo 5) | **+22.43 bp gross → ~22 bp round trip** |
| subq-savant break-even ledger | **24.5945 bp/side → ~49 bp round trip** |

These differ by roughly 2×. Either the gross edges differ, or "per side" and
"per round trip" are being used differently in the two ledgers. **I am not
adjusting my number to match theirs, and I am not asserting mine is right** — the
two need reconciling on a shared definition before either is quoted. Raised with
subq-savant over COMS.

## Labels

| item | label |
|---|---|
| Per-class refutations (CRYPTO/FOREX/COMMODITY/BOND/ETF) | **robust to cost model** — unchanged at measured cost |
| Cost as the binding constraint for the ledger | **REFUTED** — 4 of 6 classes lose at zero cost |
| Cost as the binding constraint for ETF breakout | **STILL THE DECIDING VARIABLE** — gross +22.43 bp, spread UNMEASURED |
| BOND / COMMODITY / EQUITY / ETF / FUTURES cost | **UNMEASURED** — blocks promotion, cannot support it |
