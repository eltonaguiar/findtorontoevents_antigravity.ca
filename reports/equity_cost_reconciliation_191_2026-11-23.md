# Equity round-trip cost — reconciled on the same 191 names

**Run:** 2026-11-23 · **Tool:** `tools/equity_cost_reconcile_191.py` (cached 1-min bars, no network) ·
**Artifact:** `reports/equity_cost_reconcile_191_2026-11-23.json` · **Universe:** the identical 191
names from `reports/equity_cost_hml.json` (`per_symbol`).

## The dispute, stated fairly

| claim | value | estimator | universe | what it actually is |
|---|---|---|---|---|
| mine (Freebuff) | **12.0749 bp** RT | median **1-min bar range** | 13 mega caps / ETFs | a rigorous **UPPER BOUND** on the quoted spread, presented as "measured cost" |
| peer | **1–5 bp** | Corwin-Schultz + SEC, incl. an optional 4.0 bp slippage term | 191 S&P names | a **point estimate** (CS) plus an assumption |

Both were arithmetically right. Neither was a cost estimate of the same thing, on the same names. That
is exactly why they couldn't agree.

## Same 191 names, same bars, three estimators

| estimator | n usable | median RT bp | p25 | p75 | p90 | max |
|---|---|---|---|---|---|---|
| Corwin-Schultz (point) | 65 / 191 | **0.7696** | 0.2833 | 1.4106 | 2.4494 | 5.0561 |
| Roll (point, upward biased) | 190 / 191 | **3.8064** | 1.5124 | 5.8939 | 8.2528 | 12.7419 |
| median 1-min bar range (**upper bound**) | 190 / 191 | **7.1744** | 5.1586 | 9.6687 | 13.4103 | 32.1092 |

Distribution of the bound across the 191: **21.6%** of names are under 5 bp, **86.3%** under 12.0749 bp,
**98.5%** have a Corwin-Schultz spread under 5 bp.

## What this settles

1. **12.0749 was an upper bound, quoted as a cost.** On the same 191 names the like-for-like bound is
   **7.17 bp** — so 12.07 is **1.68× the like-for-like bound** and was measured on the *most liquid 13
   names*, where a bound should be *tighter*, not looser. The difference is that mine used a live
   5-day window; the cache here is a different 5-day window. Either way, a bound is not an estimate and
   should never have been used as one.
2. **The peer's "1–5 bp" is the Corwin-Schultz band, and CS is only usable on 65 of 191 names** —
   volatility swamps it elsewhere (it floors to 0.0 on 126 names). Their band is right where it applies
   and silent where it doesn't.
3. **The bracket on n=191 is [0.98, 7.38] bp**, with Roll as the central estimate:

| quantity | bp RT | status |
|---|---|---|
| CS + SEC fee | **0.9756** | measured spread, 65 names only ⇒ **floor** |
| Roll + SEC fee | **4.0124** | measured, 190 names, upward biased ⇒ **central** |
| bar range + SEC fee | **7.3804** | rigorous bound ⇒ **ceiling** |
| 2× cost stress on the central | **8.0248** | the number the 2×-cost gate should be run at |

4. **Why the old "4.98 bp" is not verdict-grade** (from `tools/cost_of_record.py`): 0.7696 is measured,
   0.206 is the statutory SEC fee, and **4.0 is an unsourced slippage assumption**. It happens to land
   near the Roll estimate (4.01), which is a coincidence, not corroboration. The bracket above says the
   same thing with the assumption made explicit.

## What is still unmeasured (unchanged, and it is not the spread)

- **Commission** — no broker statement, no fill data anywhere in this repo. Zero only by assumption.
- **ECN** — zero only on smart-routed orders; direct-routed pays.
- **Impact beyond the spread** — order/ADV is ~1e-5 for a $100k book over these names, so it is small,
  but it is inferred, not measured.
- **Realised fills** — do not exist. Every figure here is an estimator on bars.

## Recommendation

Set the **cost of record for EQUITY at 4.01 bp round trip (n=191, Roll + SEC fee)**, with the bracket
**0.98 … 7.38** carried alongside, and run the 2×-cost gate at **8.02 bp**. Do not quote 12.0749 as a
measured cost again; it is a bound on a different, more liquid sample. Nothing in the published verdicts
moves: at 0.98 bp and at 8.02 bp, H-201 still passes cost and fails multiplicity, and every other class
is bounded by something other than equity cost.
