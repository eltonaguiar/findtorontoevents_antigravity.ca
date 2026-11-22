# R1 — ETF SLIPPAGE RECONCILIATION

**Question (from PART15 §6.1):** audit2/audit3 states *"ETF slippage measured ≈234%
of per-trade PnL (monthly cadence only, intraday cost artefact)"* and marks ETF
`WEAK`. My cost-horizon ladder measures SPY 1D breakout at **+22.87 bp gross
versus ~4 bp taker cost** — cost is ~17% of gross, not 234%. Can both be true?

**Verdict: YES — they are different objects, and the underlying ledger data
supports both. But the specific "234%" figure is not reproducible from the
ledger, and that should be fixed.**

---

## 1. The actual ledger numbers (not the dashboard's rendering)

Source: `audit_dashboard/data/audit3_ledger.json`, ETF class entry,
`generator_version: audit3.v2`, `git_sha: b5cf3a8b4957`,
`input_sha256: 55106c5a…`, `population: canonical`, `population_rows: 8769`.

| field | value |
|---|---:|
| n | 590 |
| **gross_expectancy_pct** | **+0.0468 % = +4.68 bp** |
| **mean_cost_pct** | **0.0511 % = 5.11 bp** |
| **net_expectancy_pct** | **−0.0043 % = −0.43 bp** |
| wins / wr | 253 / 42.88% |
| PF | 0.9963 |
| Sharpe | −0.0015 |
| DSR (n_trials 658) | 0.0008 |
| PBO-relevant: sr0 | 0.129 |
| split_half | first +0.024, second −0.0327 → **unstable** |
| recency window | 148 trades, window_net_mean **−0.3281%** |
| top_source_share | **96.27%** (single source) |
| required_n | 3,388,052 |
| verdict | **WEAK** |

Cost model from `provenance.cost_model`:
`ETF=0.05` (5 bp round-trip), with the 2× stress gate doubling it.

---

## 2. The reconciliation

**audit3 scores the average *published pick*.** Its ETF basket has a **gross edge
of +4.68 bp per trade against 5.11 bp of cost**. Cost is **109% of gross**, and
net expectancy is −0.43 bp. On that object, audit3's `WEAK` verdict and the
"cost dominates" framing are **correct and I agree with them entirely**.

**My ladder scores one specific strategy family** — a 20-bar Donchian breakout on
SPY at daily bars with 2:1 ATR exits and a 10-bar hold — at **+22.87 bp gross per
trade**.

**+22.87 bp versus +4.68 bp.** The breakout family has roughly **5×** the gross
edge per trade of audit3's average ETF pick. That is the entire reconciliation:

> The ETF **class average** is marginal and cost-finishes it (−0.43 bp net).
> A **specific family inside the class** (breakout continuation) has enough
> gross edge per trade to clear cost. A class verdict and a family verdict are
> different claims, and they are both true here.

This is also **internally consistent with audit3's own design**: the same ledger
marks ETF `WEAK` at class level *and* marks `POD-EQUITY-BREAKOUT` as its only
`pre_registered` pod, with the note that breakout continuation is *"the one
family where this system already shows positive out-of-sample statistics."*
audit3 already knows the class and the family differ. My ladder independently
confirms the family.

---

## 3. The "234%" figure is not reproducible from the ledger

I could not derive 234% from these fields. Candidate denominators:

| expression | value |
|---|---:|
| cost ÷ gross = 0.0511 / 0.0468 | **109%** |
| **2× cost ÷ gross** = 0.1022 / 0.0468 | **218%** ← closest |
| cost ÷ \|net\| = 0.0511 / 0.0043 | 1,188% |
| cost ÷ \|recency net\| = 0.0511 / 0.3281 | 15.6% |

**2× cost ÷ gross = 218%** is the closest match to the quoted 234%, which
suggests the dashboard figure is the **2× stress** cost relative to gross on a
slightly different subset or rounding.

**Recommendation for audit3's maintainers:** state the denominator explicitly
next to the number. "234% of per-trade PnL" is ambiguous between gross, net,
2×-cost and dollar PnL, and as written it reads as a contradiction of any
positive ETF result. **A number whose denominator is unstated is not citable.**

This is a documentation defect, not a maths defect. The ledger is fine.

---

## 4. `required_n = 3,388,052` — sanity check (PART15 R7, resolved here)

Almost certainly correct, not a bug. With gross − cost ≈ −0.43 bp and
`mde_pct = 0.3282` at n=590, the observed effect is ~76× smaller than the
minimum detectable effect at the sample size actually available. `required_n`
scales with `(MDE/effect)²`, so a near-zero effect produces an astronomically
large requirement. The honest reading is not "we need 3.4M trades" — it is
**"this effect is indistinguishable from zero and no feasible sample will
distinguish it."**

**Recommendation:** when `required_n` exceeds some threshold (say 100× the
current n), print `EFFECT_INDISTINGUISHABLE_FROM_ZERO` instead of a number that
looks like a to-do item.

---

## 5. Two things in the ETF entry that concern me more than the slippage

1. **`top_source_share = 96.27%`** — one source supplies 96% of ETF trades. The
   `WEAK` verdict is therefore a verdict on **one emitter**, not on ETF. It
   should be labelled `SINGLE_SOURCE` and the class verdict should not be read
   as a statement about ETF strategies in general.
2. **`recency.window_net_mean = −0.3281%`** over 148 trades against a full-sample
   net of −0.0043%. The recent quarter is ~76× worse than the full-sample
   average. Whatever this emitter is doing, it has degraded sharply. That is
   more actionable than the class verdict.

---

## 6. Net effect on my PART15 conclusions

**Unchanged, and strengthened in one respect.**

- The cost wall stands: audit3's own ETF numbers (gross 4.68 bp, cost 5.11 bp)
  are a *fourth* independent confirmation that gross edge is real and cost
  exceeds it at this horizon.
- My ladder's finding is narrower than it looked in PART15: it does **not**
  contradict audit3's ETF verdict, because audit3 is describing the class
  average and I am describing one family.
- The daily-breakout family remains the only trading family I would consider
  funding, and PART15 §4.1's caveat still governs it: **SPY's edge is post-2010
  only (first-half t = 0.47).**

No claim in PART15 needs retraction. One claim needs *narrowing*, and this
document is the narrowing.
