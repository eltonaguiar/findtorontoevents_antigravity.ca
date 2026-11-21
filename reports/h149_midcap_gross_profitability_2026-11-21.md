# H-149 — EQUITY mid-cap gross profitability — verdict

**Status: REJECTED (harness-admissible, negative and unstable).**
Supersedes the 2026-11-21 UNTESTED run at 47 names, which had no scorable window.
Run: 2026-11-21 · tool `tools/h149_midcap_gross_profitability.py --sample-n 2600`
Artifact `reports/h149_midcap_gross_profitability_2026-11-21.json`

---

## 0. Why this is H-149 and not H-146

Registered as `H-146` against `origin/main`, where the highest committed id was
`H-145`. The working tree then turned out to hold an uncommitted block from
another agent in which **H-146 is the ETF `execution_cost_gate`**, so the entry
moved to `H-149` (max id across `origin/main`, this branch and the dirty tree,
plus one). The hypothesis is unchanged; only the id moved. That block also
carries duplicate ids of its own (`H-144` twice, `H-145` twice) — flagged, not
fixed.

---

## 1. Declared deviations from the pre-registered spec

M-107 pre-registration only means something if the run is held against what was
filed. **Three of the four spec elements are not implemented literally.**

| spec element | pre-registered | actually run | why |
|---|---|---|---|
| fundamentals cadence | most recent **quarterly** statement filed strict before D | most recent **annual 10-K** only | XBRL 10-Q facts mix quarterly and year-to-date frames; summing them into trailing-twelve-month is a bug farm. Annual 10-K is unambiguous and is the standard Novy-Marx basis. |
| portfolio construction | hold the **top quintile** equal-weight | full cross-section scored; top **decile** reported separately | the harness needs every in-band name's score to test winner/loser separation. |
| exit | first month-end **≥20 calendar days** after entry, **≤60** | **40 trading days** | ≈57 calendar days, inside the band but not on the pre-registered clock. |
| entry price | **next session open** after month-end close | month-end **close** | daily adjusted closes only; no open series in the free path. |

Unlike the earlier 47-name run, these deviations now sit under a **decisive**
result, so they matter: the literal spec (quarterly, top quintile, 20–60 day
clock, next-open entry) is **still untested**. What this run establishes is that
the annual-10-K / 40-day / full-cross-section variant has no stable edge — not
that the filed hypothesis is dead.

---

## 2. Look-ahead guard

Every fundamental fact is used only if its SEC `filed` date is **strictly
before** the rebalance date. This is why the tool reads XBRL `companyfacts`
rather than `yfinance`: `yfinance` returns today's restated statements with no
filing date, so it cannot satisfy the rule at all. `tools/backtest_piotroski_fscore.py`
carries that same caveat in its own docstring.

---

## 3. Data actually obtained

| quantity | value |
|---|---|
| SEC filers in the ticker pool | 10,399 |
| CIKs sampled (random, seed 149) | **2,600** |
| names with ≥2 annual 10-K carrying GrossProfit **and** Assets | **759** (29.2%) |
| names with usable price data | **711** |
| month-end rebalance dates, 2016-01-01…2025-12-31 | 120 |
| rebalances with ≥5 in-band names | **120** (0 skipped as sparse) |
| in-band observations | 10,446 |
| resolved records | **10,230** |
| records per rebalance | **86.7** |
| round-trip cost | 20 bp (declared fallback — the repo slippage model was not importable on this path) |

The 47-name run produced 556 records over 93 usable rebalances (6.1/rebalance)
against a harness floor of 80 per window. Scaling the sample 17× raised density
14.5× to **86.7 records/rebalance**, which clears the floor.

---

## 4. Harness result

`tools/edge_stability_harness.py` was imported **unmodified** from its file path;
`--self-check` asserts the published thresholds before any verdict is emitted:

```
EFF_MIN=0.30  MIN_WINDOW_N=80  MIN_STABLE_WINDOWS=3   unmodified=True
```

| measure | value |
|---|---|
| windows at 14 days | 118 |
| windows meeting `MIN_WINDOW_N=80` | **71** |
| windows scored | **66** |
| strong windows | **15** |
| strong positive / strong negative | **4 / 11** |
| same-sign stable | **False** |
| sign | **mixed** |
| gross edge | +1.1598% |
| net edge | +0.9598% |
| cost survival | 0.828 |
| **verdict** | **REJECTED** |
| stress (40 bp) net edge | +0.7598% · survival 0.655 · **REJECTED** |

Per-window effect sizes run from **−0.568 to +0.492** with no persistence: the
negative windows are not clustered in one regime, and the two largest negative
windows (−0.556, −0.568) sit among positive ones. **Eleven strong negative
windows against four strong positive is a rejection, not a promising lead that
needs more data.**

---

## 5. The economics, and the trap in the spread

| book | n | net mean per 40d | win rate |
|---|---|---|---|
| top decile (gpa z ≥ 1.2816) | 806 | **+2.0419%** | 42.06% |
| bottom bucket (gpa z ≤ −1.2816) | **49** | **−15.7378%** | 18.37% |
| long-top minus long-bottom | — | **+17.7797%** | — |

**The +17.78% long/short spread is not a result.** The bottom bucket holds 49
observations where a decile of 10,230 records should hold about 1,023: the
gross-profitability distribution is heavily left-skewed, so the left tail is a
handful of deeply loss-making firms, not a tradable decile. Shorting 49
distressed micro-cap observations over 10 years is not an implementable
strategy, and their −15.7% is consistent with distress/delisting rather than
with a monotone quality gradient.

The long-only top decile is +2.04%/40d at a **42% win rate** — the mean is
carried by a few large winners, and the harness's per-window eff is negative in
the majority of windows. Both readings point the same way: no stable edge.

---

## 6. Verdict

**REJECTED.** With 66 scorable windows, 71 windows clearing the density floor
and 11 strong negative against 4 strong positive, this is the harness's own
rejection rather than a data gap. The prior run's UNTESTED verdict was a density
artefact, now resolved.

What would still be worth doing (none of it rescues this variant):

1. **The literal spec** — quarterly statements, top quintile, 20–60 calendar-day
   exits, next-open entry. That is a different hypothesis and must be
   pre-registered as a new id.
2. **Factor regression** — MKT/SMB/HML/RMW are declared as the benchmark but not
   regressed out. A quality tilt that survives only through market beta is not
   quality.
3. **Delisting returns** — supply a delisting-return series so the left tail is
   measured rather than truncated; it cannot make the long-only book positive,
   but it would firm up the bottom-bucket number.

---

## 7. Limits (declared, not corrected)

- Universe is a random sample of **currently registered** SEC filers. Firms that
  delisted and stopped filing are under-represented, so survivorship bias is
  reduced, not eliminated.
- Financials and REITs are included; GP/A is not meaningful for them.
- Annual 10-K only; intra-year updates are ignored, lagging the signal by up to a
  year.
- Round-trip cost is a declared 20 bp fallback, not the repo's measured
  per-class slippage.
- `data.fundamentals_yield_pct` (27.3%) is computed **after** the price filter,
  so it understates the fundamentals yield (759/2,600 = 29.2%).

---

## 8. Reproduce

```bash
PF_REGISTRY_INCLUDE_OUTCOMES=1 python3 tools/h149_midcap_gross_profitability.py \
  --sample-n 2600 --out reports/h149_midcap_gross_profitability_2026-11-21.json
```

Deterministic: the CIK sample is `random.Random(149).shuffle(pool)[:2600]`, the
bootstrap in the harness is seeded, and SEC facts are cached under
`tools/cache/sec_companyfacts/` (untracked). A cold run takes ~8 minutes for
2,600 companyfacts files plus ~700 tickers of daily prices in 80-ticker chunks.
