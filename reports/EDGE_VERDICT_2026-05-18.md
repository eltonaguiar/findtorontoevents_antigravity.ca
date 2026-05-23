# Edge Verdict — 2026-05-18

**Authoritative.** Read this before re-running any per-asset-class edge hunt on
the existing pick ledger. Four agents (Claude, Grok, codebuff, FreeBuff) have
independently re-derived the same conclusion across 2026-05-15..18. This doc is
the stop-sign so a fifth does not burn the same hours.

## Verdict

**The system's current strategy set + pick ledger contains no durable,
real-money statistical edge.** This is not "we have not found it yet" — it is
the measured result of rigorous, walk-forward, leakage-controlled testing.

- Book reality: ~29% WR, PF ~0.74 net. Every gaudy PF is an artifact:
  CT=F COT-row-duplication leakage, `quan_engine_scalp` (−96000% cumulative
  crater), single-pair / single-symbol outliers.
- `tools/edge_stability_harness.py` ran every one of the 7 pipeline scores
  through a 5-window walk-forward gate. **ADMISSIBLE: NONE.** The score the
  dashboard ranks on (`elite_score`) has eff 0.06 — pure noise.

## What was tested and killed (with the method — so it is not re-litigated)

| Candidate | In-sample look | Kill method | Verdict |
|-----------|----------------|-------------|---------|
| `method_a_score` | eff 1.14, strong | walk-forward: inverts to eff 0.42 in the prior window | regime noise — DEAD |
| `risk_reward` | `rr<1.5` bucket +746% total | leakage-control (strip COT/CT=F) → n=17, −3%/pick; walk-forward flips sign every window | confound — DEAD |
| COT commercial-net z-score | SI/YM 63% hit pooled | 13yr real CFTC backtest, no look-ahead: 53.8% pooled, year-unstable, both contracts collapsed 2024 | regime-dependent — DEAD |
| `cot_positioning` strategy | PF 4.64, DSR 1.0, SPA-pass | concentration check: 85% CT=F; ex-CT=F n=20 WR 30% PF 0.51 | leakage artifact — DEAD |
| CRYPTO `ml_enhanced_*` | PF 41–999, SPA-pass | placeholder-stat artifact (near-zero avg_loss inflates mean; SPA can't detect) | artifact — DEAD |
| qlib `pv_corr30` | new factor (#1178) | 10-ETF clean-universe backtest: −0.14% tercile spread, 14+/19− years | DEAD |
| qlib `vol_ratio` | new factor (#1178) | clean-universe backtest: mixed-sign, not year-stable | DEAD |

Seven "edges" tested — six fake-positives caught **in analysis, before real
money.** That is the win condition of the kill-loop, not a failure.

## `realized_vol30` — tested, KILLED (the 7th and last)

`tools/qlib_factor_research.py` found `realized_vol30` the lone survivor of the
first screen (+0.60% tercile spread, 25+/8− years). It was then put through the
decisive test — `tools/realized_vol_signal_test.py`: realized_vol30 as an
actual cost-adjusted (5 bps round-trip) long/cash **timing signal**, 10 ETFs,
1994–2026, walk-forward.

**Result: NOT a tradeable edge.** Strategy beats buy-and-hold Sharpe on **1 of
10 ETFs** and wins **12 of 32 pooled years**. The +0.60% cross-sectional spread
is real but does not survive as a timing signal: the filter sits in cash ~64%
of weeks and forfeits the equity risk premium — lower Sharpe and far lower CAGR
than passive holding on 9 of 10 ETFs.

`realized_vol30` is the **7th candidate falsified.** The in-house edge search
is now conclusively exhausted — every testable candidate (pipeline scores, COT,
all three qlib factors) has been killed with walk-forward, cost-adjusted,
leakage-controlled testing.

**The fork has collapsed.** Option 1 (test more in-house candidates) is closed —
there are none left that aren't dead. Only two paths remain: **new signal
sources** (order-flow, options skew, alt-data — a build program) or
**paper-only** (freeze real-money pursuit; the system stays a research sandbox).

## What is durable (keep, build on)

- `tools/edge_stability_harness.py` — the admissibility gate. `is_admissible()`
  importable. **Rule: no score ranks or gates picks unless eff ≥ 0.30, same
  sign, ≥3 of 5 walk-forward windows.** Today zero scores pass.
- `tools/pick_traceback.py` — the discrimination analyzer.
- `tools/cot_edge_research.py` — re-runnable COT backtest.
- The kill-loop: `controlled-test → leakage-control → walk-forward`. Three
  rounds, three kills, zero fake edges shipped.

## Candidate queue — status

- **qlib factors** — TESTED (clean-universe backtest, not the noise ledger):
  `pv_corr30` dead, `vol_ratio` dead, `realized_vol30` borderline survivor
  (see above). qlib no longer needs a ledger backfill — `qlib_factor_research.py`
  tests factors directly.
- **Regime-conditioned scores** — still untestable: `closed_picks.json` carries
  regime on 3 / 8421 picks; the only regime timeseries
  (`regime_performance_history.json`) is 6 distinct days, one regime. Needs a
  regime-timeseries backfill before it can be tested.
- **qlib factors** (`pv_corr30` etc., shipped in #1178) — not in the ledger;
  need an OHLCV-factor backfill per pick.

Both are multi-hour builds, and the base rate after 3 straight kills is poor.
Re-testing more features **on a ledger that is itself noise** is low-EV.

## The strategic fork (decision required — not an analysis task)

1. **Feature-backfill build** — enrich the ledger with regime + qlib factors so
   the last two candidates become testable. Completes the in-house sweep
   honestly; if they also die, that is near-conclusive.
2. **New signal sources** — accept the existing emitters harvest noise; pursue
   genuinely new inputs (order-flow, options skew, alt-data). A program.
3. **Paper-only** — freeze real-money pursuit; the system stays a research /
   paper sandbox until the harness passes something. The honest default.

## Standing rule (stop the convergence trap)

Do **not** re-run "find the per-asset-class edge" on the existing ledger. It is
exhausted — measured, not guessed. Any future edge claim must clear
`edge_stability_harness.py` walk-forward **before** it is wired or sized. A
gaudy PF / DSR-pass / SPA-pass is necessary and nowhere near sufficient — all
three passed `cot_positioning`, which is a leakage artifact.
