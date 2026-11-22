# H-149 — EQUITY mid-cap gross profitability — verdict

**Status: REJECTED (harness-admissible, negative and unstable; factor alpha zero).**
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

### 5b. Factor regression — the tilt is exposure, not alpha

The pre-registered benchmark is MKT/SMB/HML/RMW, so the honest question is
whether the book's return survives those four being partialled out. Regressed
the top-quintile book's monthly excess return on the Fama-French 5-factor
monthly file (Ken French data library, cached at
`tools/cache/ff5_monthly.csv`), with the 40-day net return restated as a monthly
equivalent at 21/40 and assigned to the month the position is held:

| fit | n | alpha | alpha t | MKT | SMB | HML | RMW | R² |
|---|---|---|---|---|---|---|---|---|
| overlapping monthly | 77 | **+0.033%/mo** | **0.04** | 0.48 | **+1.33** | **−0.73** | −0.41 | 0.415 |
| every 2nd month (no overlap) | 39 | **−0.901%/mo** | **−0.78** | — | — | — | — | — |

**Alpha is zero.** t = 0.04 on the full series and −0.78 on the overlap-free
series, so the 0.96% mean per 40-day hold is not compensation for a quality
signal — it is a **small-cap (−HML, +SMB)** tilt riding in a $2B–$10B band. This
is the honest reading of the +2.04% top-decile figure above, and it agrees with
the harness rejecting 11 windows against 4.

Caveats, stated rather than buried: consecutive formations overlap by ~10
trading days (hence the every-second-month fit), the t-stats are classical OLS
without Newey-West, and the regression is on the book the tool actually holds
(top quintile), not on the decile reported in §5.

### 5c. Delisting returns — the left tail is not truncated at exit

The bottom bucket's 49 observations looked like a truncation artifact, so the
exit rule was changed: a name whose price series ends inside the holding window
now exits at its **last available close** and is charged a declared **−30%**
haircut (the Shumway/Warther convention for performance delistings) instead of
being silently dropped. `build_records(..., delist_haircut_pct=)` carries the
penalty, and the payload records the bottom bucket with and without it.

**Nothing changed: 0 of 10,230 records exit on their last trade.** The full
2,600-CIK re-run reproduces every number in §4 and §5 exactly, with
`bottom_bucket_with_haircut == bottom_bucket_without_haircut` (n = 49, −15.74%).

The truncation is one level earlier. 759 names clear the annual-10-K filter but
only 711 have any usable price series, so **48 names are dropped at entry** — and
the failures are warrants, units and delisted tickers (`XBPEW`, `NEOVW`, `NIVFW`,
`AIDX`, `LIVG`). They never enter the book, so they cannot appear in the bottom
bucket either. The consequence is the one that matters for §5: the +17.78%
long/short spread is still a **survivor-subset artifact on both legs**, and the
−15.74% bottom mean is a lower bound on distress rather than a measurement. Fixing
it needs a delisted-ticker price source, which the free yfinance path does not
have — no code change can recover it.

---

## 6. Verdict

**REJECTED.** With 66 scorable windows, 71 windows clearing the density floor
and 11 strong negative against 4 strong positive, this is the harness's own
rejection rather than a data gap. The prior run's UNTESTED verdict was a density
artefact, now resolved.

What would still be worth doing (none of it rescues this variant):

1. **The literal spec** — quarterly statements, top quintile, 20–60 calendar-day
   exits, next-open entry. Registered as **H-150** (`PRE-REGISTERED`, not yet
   implemented): none of the four deviations above transfer to it, so H-149's
   rejection does not speak for it.
2. ~~Factor regression~~ — done in §5b. Alpha is zero; the return is a size and
   value tilt. No further work here can rescue the annual-10-K variant.
3. ~~Delisting returns~~ — done in §5c. The exit is no longer truncated (0
   records affected); what remains unrecoverable is the 48 names with no price
   series at all, which need a delisted-ticker price source, not a code change.

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
- The factor regression's overlapping fit carries autocorrelated residuals, and
  the book it regresses is the top quintile rather than the decile in §5.
- 48 of the 759 fundamentals-usable names have no price series at all (warrants,
  units, delisted tickers) and are excluded at entry, so both legs of the
  long/short spread are survivor subsets.

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
