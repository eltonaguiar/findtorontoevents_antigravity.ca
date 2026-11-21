# H-149 — EQUITY mid-cap gross profitability — verdict

**Status: UNTESTED (data gap). Not a pass, not a rejection.**
Run: 2026-11-21 · tool `tools/h149_midcap_gross_profitability.py` · artifact
`reports/h149_midcap_gross_profitability_2026-11-21.json`
Renumbered from H-146 on 2026-11-21 (ID collision — see below).

---

## 0. Why this is H-149 and not H-146

The hypothesis was registered as `H-146` against `origin/main`, where the highest
committed id was `H-145`. After registering, the working tree was found to hold
an uncommitted block from another agent covering `H-144`…`H-148`, in which
**H-146 is the ETF `execution_cost_gate`**. Registering a second hypothesis under
that id would have produced two different hypotheses with one identifier, which
the registry rules forbid.

The entry moved to `H-149` = max id observed across `origin/main`, this branch,
and the dirty working tree, plus one. **The hypothesis itself is unchanged**;
only the id moved. Registries are append-only and ids are never reused, so the
`H-146`…`H-148` range stays reserved for the other agent's block whether or not
it ever lands.

The same working-tree block also contains **duplicate ids of its own**: `H-144`
appears twice (CRYPTO `position_timeframe_selection`, already committed, and ETF
`residual_mean_reversion`) and `H-145` appears twice (ETF
`exit_geometry_time_exit` and COMMODITY `calendar_spread_reversion`). That is
flagged here rather than silently fixed, because it belongs to that block.

---

## 1. Declared deviations from the pre-registered spec

M-107 pre-registration only means something if the run is held against what was
filed. **Three of the four spec elements were not implemented literally.** They
are listed here because a deviation discovered later looks like p-hacking, and a
deviation declared up front does not.

| spec element | pre-registered | actually run | why |
|---|---|---|---|
| fundamentals cadence | most recent **quarterly** statement filed strict before D | most recent **annual 10-K** only | XBRL 10-Q facts mix quarterly and year-to-date frames; summing them to a trailing-twelve-month figure is a bug farm. Annual 10-K is unambiguous and is the standard Novy-Marx basis. |
| portfolio construction | hold the **top quintile** equal-weight | full cross-section scored; top **decile** reported separately | the harness needs every in-band name's score to test winner/loser separation. A top-quintile-only book yields too few records to bucket. |
| exit | first month-end **≥20 calendar days** after entry, **≤60** | **40 trading days** | same cadence simplification; 40 trading days ≈ 57 calendar days, inside the 20–60 band but not on the pre-registered clock. |
| entry price | **next session open** after month-end close | month-end **close** | daily adjusted closes only; no intraday or open series in the free path. |

**This matters less than it normally would, because the run returned no verdict
at all.** Nothing was rescued by the drift: the annual-10-K / full-cross-section
variant could not produce a single scorable window, so there is no result whose
significance depends on which spec was followed. The literal spec is still
untested and remains the next required run.

---

## 2. Look-ahead guard

Every fundamental fact is used only if its SEC `filed` date is **strictly
before** the rebalance date. This is the reason the tool reads XBRL
`companyfacts` instead of `yfinance`: `yfinance` returns today's restated
statements with no filing date, so it cannot satisfy the rule at all. The
existing Piotroski tool in this repo (`tools/backtest_piotroski_fscore.py`)
carries exactly that caveat in its own docstring.

---

## 3. Data actually obtained

| quantity | value |
|---|---|
| SEC filers in the ticker pool | 10,399 |
| CIKs sampled (random, seed 149) | 150 |
| names with ≥2 annual 10-K carrying GrossProfit **and** Assets | 49 |
| names with usable price data | **47** |
| month-end rebalance dates in 2016-01-01…2025-12-31 | 120 |
| rebalances with ≥5 in-band names | 93 |
| rebalances skipped as too sparse | 27 |
| in-band observations | 567 |
| resolved records | **556** |
| round-trip cost | 20 bp (declared fallback — the repo slippage model was not importable on this path) |

---

## 4. Harness result — zero scorable windows

`tools/edge_stability_harness.py` was imported **unmodified** from its file path
and its own `_windows()` / `_window_eff()` did the bucketing. `--self-check`
asserts the thresholds are still the published ones and passed:

```
EFF_MIN=0.30  MIN_WINDOW_N=80  MIN_STABLE_WINDOWS=3   unmodified=True
```

| measure | value |
|---|---|
| windows at 14 days | 91 |
| windows meeting `MIN_WINDOW_N=80` | **0** |
| windows scored | **0** |
| strong windows | 0 |
| **verdict** | **UNTESTED** |

556 records spread over 91 windows is **6.1 records per window** against a floor
of 80. The harness needs ≥15 winners and ≥15 losers *inside* a window to compute
an effect size, so it returned `None` for every window. There is no eff to read
in either direction.

**Exact data gap:** 7,280 records needed for 80/window; 556 present; **shortfall
6,724 records**, i.e. **13.1× the current name count**. Meeting it means roughly
600 SEC filers surviving the fundamentals filter, or a longer price history, or
both.

---

## 5. The one economic readout that is legitimate

The top-decile book is reported because it is the pre-registered trading rule,
and it is informative even though it cannot be gated:

| book | n | net mean per 40d | win rate |
|---|---|---|---|
| top decile (gpa z ≥ 1.28) | 90 | **+1.4218%** | 62.22% |
| bottom decile (gpa z ≤ −1.28) | 14 | **+1.2506%** | 35.71% |
| long-top minus long-bottom | — | **+0.1712%** | — |

**The bottom decile also made money.** Over this sample the low-quality names
returned +1.25% per 40 days, so the +1.42% earned by the high-quality names is
almost entirely market drift shared by both legs, not selection. The part that
is actually attributable to the signal — the long/short spread — is
**0.17% per 40 days**, roughly a twelfth of the drift and smaller than the 0.20%
round-trip cost.

Cost survival looks healthy (0.879 at 20 bp, 0.757 at the 40 bp stress) but that
number is **not evidence**, because it measures what fraction of the gross return
survives cost and the gross return here is beta. A cost-survival figure computed
on a beta-driven return says nothing about whether the signal survives costs.

This is the honest summary: at the maximum density the free data supports, the
signal's own contribution is indistinguishable from zero and is smaller than the
cost of trading it.

---

## 6. Verdict

**UNTESTED.** Per the registry's own rule, fewer than 5 windows of ≥80 picks is a
data gap, not a pass. No claim is made in either direction.

What would change it:

1. **Density.** ~600 names through the fundamentals filter, or a 15-year window,
   to reach 80 records/window. Only then does the eff test mean anything.
2. **The literal spec.** Quarterly statements, top quintile, 20–60 calendar-day
   exits, next-open entry — the version actually filed.
3. **Factor regression.** MKT/SMB/HML/RMW are declared as the benchmark but are
   not regressed out here. Given that both deciles earned the same drift, a
   factor-neutral re-measurement is the single most likely thing to reduce the
   apparent result to zero — which is what the L/S column already suggests.

---

## 7. Limits (declared, not corrected)

- Universe is a random sample of **currently registered** SEC filers. Firms that
  delisted and stopped filing entirely are under-represented: survivorship bias
  is reduced, not eliminated.
- Financials and REITs are included, and GP/A is not meaningful for them.
- Annual 10-K only; intra-year updates are ignored, lagging the signal by up to
  a year.
- The round-trip cost is a declared 20 bp fallback, not the repo's measured
  per-class slippage.
