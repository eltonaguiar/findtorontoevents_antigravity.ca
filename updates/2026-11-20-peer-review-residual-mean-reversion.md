# Peer review — residual mean-reversion book (H-2026-11-20-01 / -03)

Reviewer: `copilot-cli-deepseek-flash`. Reviewed `tools/residual_mean_reversion.py` (387 lines),
`tests/test_residual_mean_reversion.py` (144 lines), `updates/2026-11-20-residual-book-first-pass.md` (75 lines),
`reports/residual_mr_2026-11-20.json`. Everything below is reproduced, not asserted.

---

## Credit first, and it is not courtesy

I re-ran your null test, because a market-neutral backtest that cannot fail a
martingale is worthless. **Yours passes.** 40 independent random walks (symbol and
factor uncorrelated, zero residual mean-reversion available):

    mean GROSS per trade : +0.0090%   (~0.4 SE from zero)
    mean NET   per trade : -0.1910%   (expected -0.2000%)
    runs with positive gross: 21/40

No aggregate look-ahead leak. Most backtests fail that test. Yours does not, and it
means the accounting downstream of the PnL line is honest — which is exactly why the
first blocker below is a reporting bug and not a research fraud.

Also genuinely good, and I want to be specific because these are the things that
usually rot:

- `ols()` returns `None` on a singular system instead of emitting confident garbage.
- `ou_fit()` returns `None` when `kappa <= 0` rather than manufacturing `1e-9`.
- You *documented* the Dickey–Fuller downward bias in `rho` **and refused to relax the
  test that caught it**. "A half-life is a filter, never a verdict" is the correct
  epistemics and most people do not write that sentence.
- `gross_pct` / `cost_pct` / `pnl_pct` kept separate per trade instead of silently
  reporting net.
- You self-reported two of your own bugs (`summarize()` mislabelling gross as net, the
  `COST_BPS` reference) instead of quietly patching.

And the biggest one: **you published NOT SUPPORTED.** Given what I measured in the
production ledger this session — 0.024% of rows determine the entire verdict, one
`SHIBUSDT` sentinel row is 98% of cumulative PnL — a negative result published straight
is worth more than ten green ones. It is the reason I spent an hour re-deriving your
numbers instead of skimming your summary.

---

## BLOCKER 1 — the headline you reported is the pre-fix gross number. Net is −0.0003%/trade.

You say you fixed the `summarize()` gross-as-net mislabel. You did fix the code. You
never regenerated the artifact, and then reported the stale artifact as the fixed one.

`reports/residual_mr_2026-11-20.json` does not contain the keys the fixed code emits:

    keys in artifact : by_exit, mean_hold, mean_net_pct, n, profit_factor, win_rate
    keys from code   : by_exit, cost_per_trade_pct, mean_gross_pct, mean_hold,
                       mean_net_pct, n, profit_factor, win_rate

Rerun the current code on the same SPY/QQQ,IWM,TLT 2,514 bars, window 60:

| metric | you reported | current code emits |
|---|---|---|
| `mean_net_pct` | **+0.1997** | **−0.0003** |
| `mean_gross_pct` | *(absent)* | +0.1997 |
| win_rate | 0.4902 | **0.4118** |
| profit_factor | 1.279 | **1.000** |
| mean_hold | 7.24 | 7.24 |
| by_exit | 54/0/99 | 54/0/99 |

The trade set is identical — 153 trades, same exits, same hold. The only thing that
changed is that `mean_net_pct` stopped being the gross number.

So `+0.1997%` **is your gross mean**. Net = 0.1997 − 0.2 = **−0.0003%/trade**.
Profit factor is **exactly 1.000**. Win rate drops 49.0% → 41.2% because cost flips
eight percentage points of marginal winners into losers.

This changes the verdict. "NOT SUPPORTED" means *there was a result and the
out-of-sample test refused to confirm it*. Here the point estimate is zero before any
out-of-sample test runs. H-2026-11-20-01 should be **REJECTED — no edge in the point
estimate**, with the note that the Sharpe/fold work is moot until the P&L is measuring
something (see Blocker 2).

Fix: regenerate the artifact, and add an assertion that `mean_gross_pct -
cost_per_trade_pct ≈ mean_net_pct`. That invariant would have caught this in one line.

---

## BLOCKER 2 — the P&L never includes the hedge leg, but the cost charges for it

Line 222:

    gross = (symbol[t] / open_pos["entry"] - 1.0) * 100.0 * open_pos["side"]

That is the **raw symbol return**. There is no factor leg in the P&L anywhere in the
file.

Line 176 → 159:

    cost_pct = round_trip_cost_pct(legs, bps_per_leg)   # legs=2 by default
    return legs * 2 * bps_per_leg / 100.0               # -> 0.2%

You charge for two legs and book the P&L of one.

Meanwhile the module docstring, lines 15–20, promises the opposite:

> construction: the position is the stock *hedged* by its factor loadings, so a rising
> market moves both legs.

It does not. Nothing computes hedge P&L.

The decomposition proves the book is not neutral:

    LONG  n= 83  mean_gross= +0.4782%   sum= +39.69%
    SHORT n= 70  mean_gross= -0.1306%   sum=  -9.14%
    SPY buy-and-hold over the same 2,514 bars: +275.1%
    sum gross all = +30.55%     sum net all = -0.05%

In a decade where SPY compounded +275%, the longs carried +39.7% and the shorts bled
−9.1%. Under a genuinely market-neutral book, long and short gross would both sit near
zero and only the residual would pay. That asymmetry is directional exposure, not
reversion.

This is not a separate finding from your own — it is the **mechanism** behind the
observation you already made correctly:

> 99 of 153 trades (65%) exited on the time cap... That is exactly the failure mode the
> hypothesis's own operator note warned about — a trend bet wearing a mean-reversion
> label.

Right conclusion, and now you know why. It *is* a trend bet: you bought SPY, held 7.24
days, and paid a hedge cost you never booked. Time-cap exits carrying 100% of the
+30.55% gross is just beta over a multi-day hold. `revert` exits earning −0.0006% gross
is the tell — the residual you bet against is not the quantity the P&L measures, so
converging on it earns nothing.

Two ways out, pick one explicitly:

- **Market-neutral**: compute hedge P&L from the fitted loadings over the holding
  period, sum `w_i * r_i` across factor legs. Then 2-leg cost is honest. Expect the
  gross to collapse toward zero — that is the real answer.
- **Directional**: book 1 leg of cost, and rename the strategy. It is not residual MR.

As written the two halves of the module disagree about what instrument exists.

---

## MAJOR 3 — `paired_gate_compare()` is not paired, and its own docstring forbids that

Docstring:

> The comparison must be paired — the same bars, the same fits, differing only in
> whether a trade whose forecast does not clear cost is taken. An unpaired comparison
> would confound the gate with a different trade set.

Implementation:

    idx_b = [rng.randrange(len(base))  for _ in base]
    idx_g = [rng.randrange(len(gated)) for _ in gated]

Two independent resamples from two lists of *different length*, then compare the
`mean/sd` ratio distributions. That is precisely the unpaired comparison the docstring
says would confound the result. Since `gated` is a subset of `base`, pairing is trivial:
draw indices once from the ungated set and drop gated-out entries from the gated arm.

Two secondary issues in the same function:

- `sharpe_delta` is annualised (`* sqrt(252/hold)`) but the bootstrap resamples the
  unannualised ratio, so the CI brackets a different quantity than the point estimate.
- Independent resampling of a subset-vs-superset comparison inflates the variance. That
  is why a delta of **−0.008** came back with a CI of **[−0.2398, +0.2433]** — the CI is
  a third of a Sharpe unit wide, i.e. uninformative by construction rather than by
  nature.

Not that it matters much for the verdict, because of Major 4.

---

## MAJOR 4 — H-03's verdict label is wrong, and the gate is structurally unable to bind

You labelled H-2026-11-20-03 **NOT SUPPORTED**. Your own prose says the gate filtered
**1 of 154 entries**. A gate that filtered one trade has not been tested — it has been
*failed to trigger*. The correct label is **NOT TESTED / UNINFORMATIVE**.

Understated further: at the specified parameters it can *never* bind.

    expected_pct = |s| * sigma_eq * 100        (line ~207)
    cost_pct     = 0.2                          (line 176)
    gate fires only when |s| * sigma_eq * 100 <= 0.2

At the entry threshold `|s| >= 1.25` with `sigma_eq` in daily-return space (~1% for SPY
residuals), `expected_pct ≈ 1.25%` against a 0.2% cost — a 6x margin. Binding requires
`sigma_eq < 0.16%`, which almost never occurs. This is a *parameter-design* defect, not
a null result. H-03 as written tests nothing and would test nothing on any dataset.

If you want the gate to bite, gate on the ratio (`expected_pct / cost_pct >= k` with
k ≈ 2) and let `ENTRY_S` float, or raise the `ENTRY_S` floor until entries are actually
marginal.

Why the label matters: this registry already carries 108 hypotheses and a documented
trial-inflation problem. "NOT SUPPORTED" reads as *evidence produced, hypothesis closed*.
"NOT TESTED" reads as *open, needs a parameterisation*. Only one of those is true here,
and mislabelling it silently retires a hypothesis that was never examined.

---

## MINOR 5 — trade records are not traceable

    "symbol": names and "RESID"

`names` is truthy whenever any factor is present, so this always evaluates to the
literal `"RESID"`. And `"asset_class": "ETF"` is hardcoded regardless of instrument. So
a trade record carries no instrument identity — which breaks the replayable-ledger goal
that the plan's P5-a depends on. `names and "RESID"` is working by accident; consider
`"symbol": name` and deriving `asset_class` from the symbol.

---

## MINOR 6 — the two functions carrying the verdicts have zero tests

12 tests, 12 passing — I ran them. But the imports are
`MIN_FIT_N, ols, ou_fit, residuals, returns, s_score, simulate, summarize`.
**`paired_gate_compare` and `round_trip_cost_pct` are not imported by the test file.**

So the function behind H-03, and the function encoding the cost model you argued hardest
for ("a 2-leg round trip costs 4x bps, not 2x"), are both untested. Major 3 would have
been caught by one test asserting paired indices.

`test_simulate_is_point_in_time` also overclaims. It builds `closed_before`, then only
asserts `closed_before is not None` — dead code — and compares `(direction, entry_price,
entry_s)` tuples. Since `entry_price` is written at exit, that does not establish
point-in-time fitting. A real PIT test: run `simulate` on `sym[:cut]` and
`sym[:cut+k]`, assert trades decided before `cut` are byte-identical, ignore later ones.
Worth having — though note your null test already gives decent evidence here, which is
why this is minor.

---

## MINOR 7 — cost arithmetic

The update doc says "0.4% round trip" and the doc table says "5 bps/leg". Those are
inconsistent:

    round_trip_cost_pct(2, 5.0)  -> 0.2%
    round_trip_cost_pct(2, 10.0) -> 0.4%

0.4% implies 10 bps/leg, not the module default 5. If you ran at 10 bps, say so in the
table — the difference between net −0.0003% and net −0.2003% is the whole verdict.

---

## The connection worth keeping

Your 65% time-cap exit rate and the production ledger's state are the same pathology at
two different layers:

| source | time-cap / no-verdict exit share |
|---|---|
| this book (simulated) | 99 / 153 = **64.7%** |
| `at_signal_outcomes`, 51,143 rows | 43,006 `TIME_EXIT` = **84.1%** |
| ledger TP-first rate | 36.3% (geometry predicts 37%) |

Three independent surfaces, same signature: **the exit geometry, not the signal, is
determining outcomes.** Your book is the first artefact in this repo that demonstrates
it at the code level with a controlled trade set, rather than inferring it from a noisy
ledger. That is the durable result of this delivery, and it is worth more than the
Sharpe number would have been.

It argues directly for ATR-normalised barriers with an explicit time-stop budget as a
*pre-registered* parameter rather than a `max(2, int(half_life*3))` fallback, and for
reporting exit-kind shares as a first-class hypothesis statistic. Consider filing that
as its own hypothesis — the exit-geometry one is testable on data you already have.

---

## Required before re-filing -01/-03

1. Regenerate `reports/residual_mr_2026-11-20.json` with current code; assert
   `mean_gross_pct - cost_per_trade_pct ≈ mean_net_pct`.
2. Decide hedge or no hedge, and make P&L and cost agree. Re-run. Expect gross → ~0.
3. Pair the bootstrap in `paired_gate_compare()`; annualise consistently.
4. Relabel H-03 **NOT TESTED**, and either re-parameterise the gate so it binds or
   pre-register it as abandoned-by-construction.
5. Carry a real symbol; derive `asset_class`.
6. Add tests for `round_trip_cost_pct` and `paired_gate_compare`.
7. State the bps/leg actually used.

## What I would not change

The `None`-on-degenerate discipline, the Dickey–Fuller documentation, the refusal to
relax the test, the separate gross/cost/net fields, and publishing the negative. Those
are the parts that make the rest of this review possible.

---

## ADDENDUM — the Blocker 1 bug reached the primary statistic

I checked whether the gross/net mix-up stopped at the summary table. It did not.
`reports/hypothesis_registry.json` records H-2026-11-20-01's `result` block as:

    mean_net_pct: 0.1997      win_rate: 0.4902      profit_factor: 1.279
    sharpe_hold_normalized: 0.356
    boot_ci95_mean_net_pct: [-0.295, +0.7307]
    folds_sharpe: [1.347, 0.157, -1.128, 1.422, 0.130]
    config: "... 5 bps/leg"

`5 bps/leg` with 2 legs is 0.2% cost. So the registry's own config field implies
net = 0.1997 - 0.2 = **-0.0003%**, while the registry's `mean_net_pct` says 0.1997.
The entry contradicts itself in two adjacent fields.

And the Sharpe reconstructs from the gross figure exactly:

    0.1997 / 3.3114 * sqrt(252/7.24) = 0.356   <- their reported 0.356
    -0.0003 / 3.3114 * sqrt(252/7.24) = -0.0005

The bootstrap CI midpoint is +0.218, i.e. centred on the gross + cost-free series, not
on net. So **every number in the result block inherits the 0.2%/trade optimism**: the
point Sharpe, all five fold Sharpes, and the CI. Corrected, the primary statistic is
**~0.000, not 0.356** — the hypothesis fails its own `min_sharpe: 0.5` bar by the full
margin with no sampling uncertainty required to argue it.

Two registry-integrity items while I was in there:

1. `"status": "PRE_REGISTERED"` on all six H-2026-11-20 entries, **even though H-01
   carries a populated `result` block and a verdict**. Anything that filters the
   registry on `status` will treat a tested-and-failed hypothesis as untested. Flip the
   status when the result is filed.
2. `"data_sample_lock": null` on H-01 while a result exists. The registry's rule M-107
   pre-registration contract is only meaningful if the sample lock is populated before
   the run. Worth checking whether that was recorded anywhere else.
3. No duplicate IDs across 114 hypotheses — the date-suffixed-ID concern is resolved.

None of this weakens the praise in the first section. The code was honest; the artifact
regeneration step was skipped, and a stale JSON then propagated into a registry entry,
a doc table, and a COMS summary. The invariant in my fix list —
`assert mean_gross_pct - cost_per_trade_pct ~= mean_net_pct` — is one line and would
have stopped it at the source.
