# Peer review — Daily Idea #5: 200d MA / EMA / HMA strategy tracking

**Date:** 2026-05-31
**Author:** Claude Opus 4.7 (subagent)
**Source idea:** `/tmp/user_ideas_2026-05-31.json` index 4
**Slug:** `200d-ma-strategy-tracking`

## Verbatim idea (user)

> Start a buy when stock Price above 200 day Simple moving average, sell when price goes below it. Start some strategy tracking under https://findtorontoevents.ca/audit/ai_leaderboard.html across each asset class ... Hull Moving Average, EMA, and simple moving average.

**What to investigate:** Wire SMA-200 / EMA-200 / HMA-200 trend strategies across all asset classes into the strategy registry with 1-2% risk overlay; surface on `ai_leaderboard.html`.

## Hypothesis

- **H1 (user):** A simple regime filter (price > 200-day SMA → long; below → flat/short) produces a real, positive, hedge-fund-tier edge per asset class.
- **H2 (user variants):** EMA-200 and HMA-200 versions improve responsiveness without sacrificing PF / WR.

## Punchline (read first)

**The idea is already implemented and rigorously tested.** `audit_dashboard/data/ma_strategy_leaderboard.json` (schema `ma-strategy/v2`, generated 2026-05-29) contains 8 MA variants × 6 asset classes = 48 cells with walk-forward OOS, never-touched holdout, survivorship adjustment, and a golden-gate (PF≥2.5, Sharpe≥0.8, n≥50, beats B&H, holdout PF≥1.5).

**`n_golden = 0`.** Zero of the 48 cells survives the gate. The strong-looking OOS PFs (2.0-2.4 on EQUITY / CRYPTO) **all collapse on the never-touched 10% holdout** (PF 0.01-1.19), the classic in-sample-optimization-failure signature. None of the variants beats buy-and-hold OOS in any class.

## Methodology

a. **Hypothesis to test:** does an MA-200 family produce tier-2+ edge per asset class?
b. **Test surface:** `audit_dashboard/data/ma_strategy_leaderboard.json` (authoritative), `at_large_backtest_results.ema_crossover`, `bt_backtest_trades` MA-family strategies.
c. **Time window:** 6y lookback, 60/40 IS/OOS split, walk-forward 5 folds, most-recent 10% never-touched holdout.
d. **Stats:** Wilson lower bound on pooled WR, OOS confidence intervals, walk-forward worst-fold PF, survivorship adjustment (5% synthetic total-loss trades), Bonferroni for 48-cell family.

## Raw evidence — A. The authoritative leaderboard

Source: `audit_dashboard/data/ma_strategy_leaderboard.json`
Methodology (from JSON `methodology` block):

- "OOS (walk-forward median across 5 folds + worst fold). Single 60/40 OOS is secondary. Most-recent 10% is a never-touched holdout."
- "Multiple comparisons: 8 variants x 6 classes; expected ~1.0 golden by chance under no-edge null."
- "UNIVERSE is current-listed only -> survivorship-biased; pf_oos_survivorship_adj injects 5% synthetic total-loss trades."

### Classic200 (SMA-200, the literal idea)

| Class     | OOS n | OOS WR | OOS PF | Sharpe | Holdout n | Holdout PF | WF worst | Surv-adj PF | Beats B&H | Golden |
|-----------|------:|-------:|-------:|-------:|----------:|-----------:|---------:|------------:|-----------|:------:|
| EQUITY    |   147 |  44.9% |   2.10 |   1.93 |        32 |       0.71 |     1.44 |        1.61 | **No** (B&H CAGR 35.9% vs strat 27.1%) | **No** |
| ETF       |   145 |  48.3% |   1.80 |   1.87 |        41 |       0.88 |     0.79 |        1.13 | No | No |
| CRYPTO    |   154 |  29.2% |   2.00 |   1.09 |        41 |       1.09 |     0.00 |        1.73 | No | No |
| FOREX     |   106 |  31.1% |   0.70 |  -0.96 |        20 |       1.65 |     0.45 |        0.33 | No | No |
| COMMODITY |   112 |  42.9% |   1.22 |   0.52 |        32 |       1.48 |     0.54 |        0.97 | No | No |
| BOND      |   133 |  43.6% |   0.98 |  -0.05 |        40 |       0.37 |     0.28 |        0.45 | No | No |

### EMA200

| Class     | OOS n | OOS WR | OOS PF | Holdout PF | WF worst | Surv-adj PF | Golden |
|-----------|------:|-------:|-------:|-----------:|---------:|------------:|:------:|
| EQUITY    |   160 |  43.1% |   2.22 |       1.19 |     0.80 |        1.74 | No |
| ETF       |   172 |  45.9% |   1.84 |       0.78 |     0.98 |        1.19 | No |
| CRYPTO    |   189 |  36.0% |   2.08 |   **0.01** |     0.85 |        1.77 | No |
| FOREX     |   125 |  35.2% |   0.73 |       1.06 |     0.63 |        0.34 | No |
| COMMODITY |   128 |  39.1% |   1.10 |       1.91 |     0.37 |        0.85 | No |
| BOND      |   140 |  38.6% |   0.88 |       0.38 |     0.01 |        0.44 | No |

### HMA200 (Hull MA, the user's third variant)

| Class     | OOS n | OOS WR | OOS PF | Holdout PF | WF worst | Surv-adj PF | Golden |
|-----------|------:|-------:|-------:|-----------:|---------:|------------:|:------:|
| EQUITY    |   115 |  42.6% |   2.40 |       0.87 |     0.95 |        1.68 | No |
| ETF       |   134 |  33.6% |   1.26 |       1.54 |     0.61 |        0.78 | No |
| CRYPTO    |   155 |  30.3% |   2.15 |       0.40 |     0.66 |        1.79 | No |
| FOREX     |    83 |  37.3% |   1.42 |       0.53 |     0.30 |        0.53 | No |
| COMMODITY |   122 |  32.8% |   1.26 |       1.27 |     0.53 |        0.97 | No |
| BOND      |   101 |  37.6% |   1.03 |       0.16 |     0.76 |        0.43 | No |

### Other tested variants

Identical pattern across `RespEMA50` (EMA-50), `LagHull16` (HMA-16, large n: EQUITY 425 / CRYPTO 415), `MedHull50` (HMA-50), `DualCross` (50/200 SMA cross — the classic Golden Cross), `Buff200` (SMA-200 with 0.75% buffer). **Every single one fails golden-gate on every asset class.**

`LagHull16` has the largest sample (n_oos ≥ 295 every class) — even there, OOS Sharpe is negative on FOREX/BOND (-2.67 / -0.38), holdout PF crashes on CRYPTO (1.58 → 0.42), and no class beats B&H.

## Raw evidence — B. Live SQL cross-check (`at_large_backtest_results.ema_crossover`)

Per-symbol pool (CRYPTO only — universe of 5 majors, 225 parameter-grid configs):

```sql
SELECT symbol, SUM(total_trades) tt, SUM(wins) w, SUM(losses) l,
       ROUND(SUM(wins)/NULLIF(SUM(wins+losses),0)*100,2) wr,
       ROUND(AVG(profit_factor),3) avg_pf,
       ROUND(AVG(total_return)*100,3) avg_ret_pct,
       ROUND(AVG(max_drawdown)*100,2) avg_mdd
FROM at_large_backtest_results
WHERE archetype='ema_crossover' AND profit_factor < 99 AND profit_factor > 0
GROUP BY symbol ORDER BY tt DESC;
```

| Symbol  | n_trades | WR     | Avg PF | Avg Return | Avg MDD |
|---------|---------:|-------:|-------:|-----------:|--------:|
| BNB-USD |       94 | 57.14% |  1.598 |    -1.537% |   -3.42% |
| SOL-USD |       80 | 50.68% |  1.712 |    -0.631% |   -4.90% |
| ETH-USD |       67 | 44.78% |  0.250 |    -8.458% |   -2.77% |
| XRP-USD |       46 | 36.59% |  1.294 |    -5.061% |   -5.96% |
| BTC-USD |       18 | 50.00% |  2.564 |     0.792% |   -0.47% |

**Pooled honest (PF in (0,99) — excludes sentinel cap):** wins=139, losses=144, **n=283, WR=49.12%, Wilson 95% LB = 43.34%.** Average total-return across configs: -3.30%. 53.3% of configs have negative total return.

The raw `at_large_backtest_results` view headline "avg PF 25.8 / avg Sharpe 22.7" is an **artifact**: 152 of 225 configs have only 2 trades, and PF=99 is a sentinel cap for "no losses recorded yet." The median PF is 0.814; the distribution is bimodal at the sentinel.

## Raw evidence — C. `bt_backtest_trades` MA cohort

```sql
SELECT strategy, status, COUNT(*) n
FROM bt_backtest_trades
WHERE strategy IN ('cta_golden_cross_200','MACrossover','GoldenCross',
                   'futures_ema_stack_momentum','EmaRibbon','super_hma_breakout_volume',
                   'ema_stack','MACDCrossover','cta_cross_asset_tsmom')
GROUP BY strategy, status;
```

| Strategy                   | Status | n       | n_with_pnl |
|----------------------------|--------|--------:|-----------:|
| cta_cross_asset_tsmom      | OPEN   | 433,951 |          0 |
| cta_golden_cross_200       | OPEN   | 115,600 |          0 |
| MACDCrossover              | OPEN   | 414,806 |          0 |
| futures_ema_stack_momentum | OPEN   | 232,916 |          0 |
| MACrossover                | OPEN   |  90,644 |          0 |
| EmaRibbon                  | OPEN   |  69,091 |          0 |
| GoldenCross                | OPEN   |  10,076 |          0 |
| super_hma_breakout_volume  | OPEN   |   1,968 |          0 |
| ema_stack                  | CLOSED |      10 |         10 |

**Plumbing failure:** 1.37 million MA-family backtest rows exist with status=OPEN and NULL pnl. The literal 200-day-cross strategy (`cta_golden_cross_200`) has 115,600 trades but 0 resolved. This is consistent with `project-money-ready-2026-05-31` MEMORY: "money-ready bottleneck is PLUMBING, not strategies."

## Statistical sanity

- Family-wise multiple comparisons: 48-cell MA leaderboard. Per JSON methodology, "expected ~1.0 golden by chance under no-edge null." **Observed: 0 golden.** Below the null expectation.
- Bonferroni-adjusted α at family-wise 0.05 ≈ 0.001. None of the OOS PFs survive that gate once holdout/survivorship adjustments are applied.
- Walk-forward worst-fold PF < 1.0 for **every** class on every variant except Classic200-EQUITY (1.44). The single survivor has a holdout PF of 0.71 (still kills it).
- The visually best cell (HMA200-EQUITY OOS PF 2.40) has WF worst 0.95 and holdout PF 0.87 — classic in-sample overfit pattern.

## Cross-check against today's NO_EDGE verdict

Today's `money_ready_verdict.json` (2026-05-24) says 0/6 classes pass T2. Idea #5 hypothesizes MA-200 family rescues the picture. Possibilities:

1. **MA-200 quietly produces edge somewhere** → would contradict NO_EDGE. **Refuted by ma_strategy_leaderboard.json.**
2. **Cousin strategies (EMA pullbacks, trend-follow) show edge** → would support the idea. **Refuted** by `at_large_backtest_results` (pooled WR 49.1%, avg return -3.3%).
3. **The MA edge is real but not measurable yet (plumbing)** → consistent with NO_EDGE. The 115k OPEN cohort *could* eventually move the verdict; today it cannot.

**Conclusion:** The investigation strengthens today's NO_EDGE verdict. The user's idea is conceptually reasonable (DBMF/KMLM managed-futures funds run trend overlays) but our own measurements — using best-practice walk-forward + holdout — already say it doesn't survive.

## Verdict per CLAUDE.md tier system

**Headline: NO_EDGE for the SMA-200 / EMA-200 / HMA-200 family as a literal long-only flip rule.**

- n_golden = 0/48. Zero variants × classes pass institutional or even retail tier with survivorship-adjusted, walk-forward-validated metrics.
- Best honest cell: **Classic200 EQUITY** — OOS n=147, WR 44.9%, PF 2.10, survAdj-PF 1.61, Sharpe 1.93, **but** holdout PF 0.71, WF-worst 1.44, does not beat B&H (27.1% vs 35.9% CAGR). Counts as **SHADOW_CANDIDATE** at most.
- Best cousin cell (live SQL): **BNB-USD ema_crossover** WR 57.14% n=94 PF 1.60, but avg return **negative** (-1.54%). **SHADOW_CANDIDATE / suspect** (cherry-pick of one of 5 CRYPTO majors).

**Confidence: HIGH.** Two independent data sources (curated leaderboard + raw param-grid) give the same answer.

## Recommended next step

1. **DO NOT promote to live or shadow-pilot as a money-maker.** The data already exists and says NO_EDGE.
2. **DO update `ai_leaderboard.html` to surface `ma_strategy_leaderboard.json`** with a clear "NO GOLDEN PASS — 0/48 cells survive holdout" banner. The dataset is wasted if it isn't visible. (This is the actionable Goal #1 piece of the user's idea.)
3. **DO investigate / fix `cta_golden_cross_200` resolver.** 115,600 OPEN rows is the largest single MA-family plumbing failure. Even if the verdict ends up NO_EDGE there too, it removes "open_bloat" from db_health and lets us speak honestly.
4. **KILL candidates per Mutation Three-Axis Protocol:**
   - `EmaRibbon`, `MACrossover` — sustained OPEN-only bloat with no resolution path.
   - `at_large_backtest_results.ema_crossover` — n=525 trades, pooled negative return, 53% of configs unprofitable.
5. **External replication for honesty:** DBMF / KMLM monthly returns are the cheapest external check. If managed-futures funds running trend overlays show only single-digit annualized returns with ~12% MDD, that's the realistic ceiling — not the 2.0+ PF the in-sample numbers tease.

## Files of interest

- `audit_dashboard/data/ma_strategy_leaderboard.json` — **authoritative answer to this idea** (already exists)
- `audit_dashboard/ai_leaderboard.html` — target surface (idea asks for this)
- `ejaguiar1_backtests.bt_backtest_trades` — 1.37M OPEN MA-family rows (plumbing)
- `ejaguiar1_backtests.at_large_backtest_results` — `ema_crossover` archetype (cross-check)
- `reports/money_ready_verdict.json` (2026-05-24) — today's NO_EDGE baseline
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — required before any kill

## One-line return

`IDEA5:slug=200d-ma-strategy-tracking:verdict=NO_EDGE:n=283:wr=49.1:pf=0.81:wilson_lb=43.3:recommend=surface-leaderboard-and-fix-resolver-do-not-promote`
