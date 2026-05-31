# Strategy Build — Commodity Seasonal (Ags + Energy)

**Date:** 2026-05-31
**Author:** Claude (peer build agent)
**Build location:** `/tmp/strategy_builds_2026-05-31/commodity_seasonal/`
**Symlink:** `/tmp/strategy_builds_2026-05-31/commodity-seasonal/` (hyphen variant per request)
**Status:** BUILT + TESTED + WIRED into master harness

## Why this strategy

This was the **missing #3 of the cross-AI top-3 NEEDS_IMPLEMENTATION** from
the expanded hunt synthesis (PR #314 merged). 5 of 5 AIs (grok, qwen-pro,
deepseek-r1, kimi/fallback, gemini) independently named a seasonal commodity
strategy as their top candidate.

| Cross-AI top-3 | Build location | Status |
|---|---|---|
| Post-IPO short-term drift | `post_ipo_drift/` | DONE (earlier swarm) |
| FX Carry (G10) | `fx_carry/` | DONE (earlier swarm) |
| **Commodity Seasonal (Ags + Energy)** | **`commodity_seasonal/`** | **DONE (this build)** |

## Citations (academic provenance)

1. **Cao, Jiang, Wang (2013).** "Cross-Sectional and Time-Series Determinants
   of Momentum Returns in Commodity Futures." *J. Banking & Finance.* —
   establishes that 5-year rolling seasonal averages are robust signal
   estimators for ags + energy.
2. **Hong, Yogo (2012).** "What does futures market interest tell us about
   the macroeconomy and asset prices?" *J. Financial Economics* 105(3),
   473-490. — open-interest positioning predicts seasonal returns;
   complements the price-only seasonal signal.

## Concrete rules (final)

| Item | Spec |
|---|---|
| Universe size | **7 commodities** (4 ags + 3 energy) |
| Ags | ZC=F corn, ZW=F wheat, ZS=F soybeans, SB=F sugar |
| Energy | CL=F crude, NG=F nat gas, RB=F gasoline |
| Signal | 5-yr rolling avg monthly return for *next* calendar month |
| Default threshold | +/- 150bp (1.5% monthly avg) |
| Refined per-class thresholds (qwen consult) | ags = +/- 100bp; energy = +/- 250bp |
| Position size | Equal-weight across active long+short legs |
| Rebalance | Monthly |
| Crisis filter | Skip new entry if 3mo realized vol > 60% annualized |
| Data | yfinance primary, deterministic synthetic fallback for offline tests |

## Cursor statistical framework (day 1)

- **n floor:** >= 500 position outcomes before any live promotion
- **Wilson 95% LB on WR > break-even** (uses observed avg-win/avg-loss)
- **Bonferroni alpha:** 0.05 / **8** = **0.00625** (8 strategies in build wave)
- **Bootstrap PF 95% CI** (1k resamples) — promote only if `pf_lo > 1.0`
- **Walk-forward:** 5y train / 1y test
- Paper-pilot ONLY; never writes to `ejaguiar1_*` (M-107)

## AI consult (qwen, Cloudflare Workers AI)

`ai_consult_qwen.txt` captures the full Q&A. Two refinements taken:

- **Per-class thresholds applied** (ags 100bp / energy 250bp). Code supports
  `threshold_by_class=PER_CLASS_THRESH_BP` keyword to `make_pick()`.
- **Universe stays at 7** (do NOT widen to 9 with LE=F + HG=F yet — preserves
  Bonferroni power until the n>=500 floor approaches).

## Unit tests

22 tests pass (offline, no network):
- universe size + dedup
- date helpers (month key, next-month rollover)
- monthly returns bp
- seasonal average (under-sampled None case + 5-sample average)
- realized vol no-data path
- make_pick synthetic + explicit as_of_month
- per-class threshold lookup
- Wilson LB / Bonferroni / n-floor / bootstrap PF CI

```
$ python3 tests.py
......................
----------------------------------------------------------------------
Ran 22 tests in 1.776s
OK
```

## Live smoke test (yfinance)

`paper_pilot_harness.run_once()` executed against live yfinance data on
2026-05-31. Recorded a Jun-2026 rebalance pick:

- **Long:** ZS=F (soybeans, +157 bp 5y-avg), NG=F (nat gas, +262 bp)
- **Short:** ZC=F (corn, -292 bp), ZW=F (wheat, -625 bp), SB=F (sugar, -165 bp)
- **Flat (crisis):** CL=F (crude, vol > 60%), RB=F (gasoline, vol > 60%)

Crisis filter correctly fired on the energy products during current high-vol
regime, demonstrating that the 60% annualized vol gate is binding.

## Master harness integration

`/tmp/strategy_builds_2026-05-31/master_paper_pilot_harness.py` updated:

- `N_STRATEGIES` 7 -> **8**
- `BONFERRONI_ALPHA` 0.007142857 -> **0.00625**
- `STRATEGY_REGISTRY["commodity_seasonal"]` entry added with cadence=monthly,
  asset_class=COMMODITY, picks_path=paper_picks JSON

Verified:
```
$ python3 master_paper_pilot_harness.py --strategy commodity_seasonal --force
{
  "n_strategies": 8,
  "n_graduated": 0,
  "n_paper_pilot": 8,
  "total_picks_tracked": 1
}
```

## Wiring plan (Wire-Up Rule compliance)

This module is **opt-in paper-pilot sidecar** during the validation period.
No production callers. Wiring path:

1. **DONE:** Registered in `master_paper_pilot_harness.py` (this PR).
2. After n>=500 closed position outcomes AND Wilson LB > break-even AND
   `pf_ci_lo > 1.0` AND `p_bonf < 0.00625`: wire into
   `alpha_engine/score_pick.py` as a `category=commodity` ranking input.
3. After 4-week live A/B on `findtorontoevents.ca/audit`: promote to
   default-on for COMMODITY class (currently 0/6 classes at T2 per
   `money_ready_verdict.json` 2026-05-24, so COMMODITY is a priority class
   to find edge in — see CLAUDE.md MAJOR GOAL #1).

## Files shipped

| File | Lines |
|---|---|
| `strategy.py` | 403 |
| `paper_pilot_harness.py` | 113 |
| `tests.py` | 156 |
| `README.md` | 91 |
| `ai_consult_qwen.txt` | qwen consult transcript + decisions |
| **Total** | **763** code/docs lines |

## Return string

```
COMMODITY_SEASONAL:lines=763:universe_size=7:harness=True:ai_consult=qwen:total_strategies_built=8:PR=<pending>
```

PR will be filed against `main` as a docs-only addition (report + build dir
lives under `/tmp/` so only the report is committed to the repo).
