# PRE-REGISTRATION — H-239 (CRYPTO) and H-240 (EQUITY): monthly top-gainer persistence

**Filed:** 2026-11-23, before any monthly run. **Rule:** M-107. **Status at filing:** REGISTERED, UNTESTED.

Both hypotheses are **not yet runnable**. The observation requirement below is written *here, now*,
so that a future run cannot choose its own minimum after seeing the answer. That is the entire
point of filing this before the data.

---

## 0. Why these are separate from H-237 / H-238

H-237 (daily chase) and H-238 (weekly swing) already returned **REFUTED** on the same universe and
the same features. A monthly version is a *different horizon*, not a re-test of a killed family, so
it earns its own IDs. But it inherits two hard constraints from those kills:

1. **The feature list is frozen to what the weekly model already used.** No new feature enters
   because it looked good monthly. Crypto: `dollar_vol` + `vol1m`. Equity: `dollar_vol` + `volratio`.
2. **The benchmark is the universe mean, never SPY.** A long-only selection rule that cannot beat
   its own average pick is buying the market with extra steps (the H-237 lesson).

If a monthly run re-selects features, or swaps the benchmark to SPY, the verdict is void.

---

## 1. The observation requirement (the thing this document exists to fix)

**Minimum: 48 scored monthly periods, with ≥ 15 symbols carrying a monthly return in every period.**

Derivation, done in advance from the base rate rather than assumed:

- A "top gainer" month is defined as membership in the **top 13.5% of the cross-section** for that
  month (13.5% is the base rate the weekly panel actually produced, not a round number). With a
  `top_frac = 0.10` panel the base rate is 10%.
- The effect worth detecting is a **2× lift** over base (p1 = 2·p0). One-sided α = 0.05, power = 0.80,
  two-proportion comparison:

  | base rate p0 | required n (monthly periods) |
  |---|---|
  | 0.135 (top 13.5%) | **48** |
  | 0.10 (top decile)   | **69** |

  At p0 = 0.135: `(1.645·√(0.135·0.865) + 0.8416·√(0.27·0.73))² / 0.135² = 48.0`.
  At p0 = 0.10: `(1.645·0.3 + 0.8416·0.4)² / 0.01 = 68.9`.

- Therefore: **< 48 periods ⇒ no verdict may be issued.** The status stays `UNTESTED` with
  `reason: DATA_GAP_INSUFFICIENT_PERIODS`. It is never "no edge found", and never a pass.
  Between 48 and 68 periods the test is admissible only if the base rate is ≥ 13.5%; otherwise
  it is underpowered and must say so in the same sentence as its result.

**What is available today:** the 6-year daily panel used by H-237/H-238 (`period="6y"`, 1,506
trading days, 2020-11-23 → 2026-11-20) yields **≈ 71 monthly periods** — the *count* bar is met.
The 105-week crypto panel used by `reports/weekly_winners_2026-11-15.md` yields **≈ 24 months** —
the count bar is **NOT** met, and no monthly crypto verdict may be issued on that panel.

## 2. Signal definitions (exact, so someone else can build them)

### H-239 — CRYPTO
- **Universe:** the 37 `-USD` pairs in the weekly panel, plus any pair the frozen panel's source
  (Yahoo daily) returns for ≥ 48 months. Additions must be listed in the run report; the universe
  is written to the artifact, never implied.
- **Signal at month-end t:** `z(dollar_vol) + z(vol1m)` computed from data **strictly before t**
  (`z` = cross-sectional standard score; `dollar_vol` = 63-day median dollar volume;
  `vol1m` = 21-day realised vol). Sign convention is the one the weekly holdout model used, kept
  unchanged even though it is counter-intuitive: **high `dollar_vol` positive, high `vol1m` negative.**
- **Entry:** equal weight the top 10% by signal at the first session after month-end.
- **Exit:** the session after the next month-end (hold one calendar month).
- **Cost:** 20 bp round trip assumed (crypto taker, `reports/top_picks_per_class_and_overall_2026-11-23.md`);
  **must also be reported at 42.64 bp** (measured retail taker) and must keep ≥ 60% of gross.

### H-240 — EQUITY
- **Universe:** the frozen 118-name list in `tools/top_gainer_test.py` (`UNIVERSE`), unchanged.
- **Signal at month-end t:** `z(dollar_vol) + z(volratio)` (someone else's vol ratio: 5-day mean
  volume / 63-day mean volume), data strictly before t.
- **Entry / exit / benchmark:** identical to H-239 (top decile, one-month hold, universe mean).
- **Cost:** 0.98 bp round trip (`reports/equity_cost_hml.json`, the measured Questrade number);
  **must also be reported at 12.0749 bp** and keep ≥ 60% of gross.

## 3. Test statistic (one, fixed)

Mean **excess** bp per monthly period of the selected decile vs the equal-weighted universe, with a
**moving-block bootstrap 95% CI** (block = 3 months, 4,000 resamples, fixed seeds). Secondary
reported-only diagnostics: rank-IC per feature per month, hit rate of the selected decile, and
Jensen alpha vs SPY (so beta is never hidden).

## 4. Acceptance / kill

- **ACCEPTED (weak):** CI lower bound > 0 on excess vs universe mean **and** net/gross ≥ 0.60 **and**
  ≥ 48 scored periods **and** ≥ 15 symbols of breadth per period.
- **REFUTED:** CI includes zero or net/gross < 0.60 on a sample meeting the count bar.
- **UNTESTED:** fewer than 48 scored periods, or fewer than 15 symbols in any period.

**A PASS is never labelled PROVEN.** Both universes are names liquid *today*, so a pass is
survivorship-flattered and must carry `WEAK_PASS_SURVIVORSHIP_FLAGGED`. A FAIL needs no such
caveat — survivorship inflates long-only results, so it can only make a fail less likely.

## 5. Stated in advance: what would make me refuse to run this

- A universe that cannot reach 48 monthly periods (⇒ H-239 as currently instrumented, 24 months).
- Any month where the signal is computed with same-month data (look-ahead).
- Any post-hoc feature swap, benchmark swap, or hold-period change.
- Reporting the monthly result next to the weekly one as if the horizons were interchangeable.
  They are different bets with different costs, and the monthly cost drag is 1/21st of the daily one.

## 6. What is NOT claimed

No capital allocation follows from either hypothesis at any verdict. Both are cross-sectional
selection tests on survivor-conditioned universes; neither is advice.
