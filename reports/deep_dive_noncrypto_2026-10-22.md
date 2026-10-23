# FOREX and EQUITY Performance Failure — Evidence Review (2026-10-22)

## Scope and method

Bounded, read-only review of the public `/audit/data/money_ready_verdict.json`,
`/audit/data/intrabar_truth_by_class.json`, and
`/audit/data/intrabar_sym_dir_fwd.json` snapshots, plus the existing recovery
reports cited below. No local generators, scanners, database writes, code
changes, or credentials were used. The parent task's lifecycle repair was
explicitly out of scope; its module and tests were not inspected.

The public snapshots were fetched on 2026-10-22. The verdict was generated at
`2026-10-22T20:38:45.925100Z`; the two intrabar sidecars at
`2026-10-22T20:34:44Z` and `2026-10-22T20:34:45Z`. The JSON does not identify
the start date or a rolling horizon. Therefore all current results below are
described as cumulative through the named snapshot, with the measurement
window otherwise unspecified. `n` means the count reported by that specific
payload/cohort; counts from different cohorts are not interchangeable.

## Current class-level finding

| Class | n | Timeframe | First-touch WR | First-touch PF | Other evidence |
|---|---:|---|---:|---:|---|
| FOREX | 568 | Cumulative through verdict snapshot; start/window unspecified | 31.69% | 0.6465 | `avg_pnl_pct=-0.1096`; verdict `NOT_READY`; expectancy `-0.008391`; MDD `0.9826` |
| EQUITY | 233 | Cumulative through verdict snapshot; start/window unspecified | 56.65% | 0.8642 | `avg_pnl_pct=-0.1753`; verdict `NOT_READY`; expectancy `-0.00021`; MDD `0.9999` |

Primary citations: `money_ready_verdict.json::classes.FOREX.intrabar_truth`,
`classes.EQUITY.intrabar_truth`, `classes.*.details`, and
`intrabar_truth_by_class.json::by_class.{FOREX,EQUITY}`. The intrabar sidecar
explicitly describes its method as first-touch, SL-wins-ties, bad-geometry
excluded. The MDD and expectancy values above are quoted in source units; no
additional unit conversion is assumed.

Neither class has a consistent profitable aggregate in this snapshot. FOREX
has both a low win rate and PF below 1. EQUITY's win rate is above 50%, but PF
below 1 and negative reported expectancy mean its wins do not compensate for
its losses. Recency is not the blocker: both verdict records say the latest
pick is within 48 hours, while their performance and risk gates still fail.

There is a consequential outcome-method discrepancy for EQUITY: the same
verdict snapshot reports the daily cohort at `n=118`, WR `61.02%`, PF `1.2624`,
but its selected intrabar cohort at `n=233`, WR `56.65%`, PF `0.8642`; the
payload flags this divergence. Both cohorts are cumulative through the verdict
snapshot and give no start date. These are different cohort counts, so the
values should not be compared as if they were paired trades; nevertheless,
the daily view would give a more favorable verdict impression than the
first-touch view. FOREX daily outcomes are also not profitable
(`n=403`, WR `37.22%`, PF `0.3542`; cumulative through the verdict snapshot),
versus intrabar (`n=568`, WR `31.69%`, PF `0.6465`; same snapshot, window
unspecified). These paired source views both fail PF 1.

## Symbol and strategy evidence

The symbol/direction/strategy rows below are from
`intrabar_sym_dir_fwd.json::by_key`. The payload describes these as
first-touch forward statistics but does not provide the forward interval or
the start date. Each row is therefore labeled cumulative through its
`2026-10-22T20:34:45Z` snapshot, timeframe otherwise unspecified.

| Class | Symbol / direction / strategy | n | Timeframe | WR | PF |
|---|---|---:|---|---:|---:|
| FOREX | AUDJPY / LONG / `forex_rsi2_mean_reversion` | 32 | Cumulative through sidecar snapshot; window unspecified | 6.2% | 0.108 |
| FOREX | AUDUSD / LONG / `forex_rsi2_mean_reversion` | 16 | Cumulative through sidecar snapshot; window unspecified | 12.5% | 0.171 |
| FOREX | GBPJPY / LONG / `forex_rsi2_mean_reversion` | 30 | Cumulative through sidecar snapshot; window unspecified | 16.7% | 0.238 |
| FOREX | CADJPY / LONG / `forex_rsi2_mean_reversion` | 36 | Cumulative through sidecar snapshot; window unspecified | 5.6% | 0.076 |
| FOREX | USDJPY / LONG / `forex_rsi2_mean_reversion` | 24 | Cumulative through sidecar snapshot; window unspecified | 12.5% | 0.204 |
| FOREX | EURUSD / LONG / `forex_rsi2_mean_reversion` | 19 | Cumulative through sidecar snapshot; window unspecified | 5.3% | 0.091 |
| FOREX | USDCHF / SHORT / `forex_rsi2_mean_reversion` | 17 | Cumulative through sidecar snapshot; window unspecified | 11.8% | 0.195 |
| FOREX | USDCAD / SHORT / `forex_rsi2_mean_reversion` | 15 | Cumulative through sidecar snapshot; window unspecified | 13.3% | 0.209 |
| FOREX | CADJPY / SHORT / `forex_rsi2_mean_reversion` | 15 | Cumulative through sidecar snapshot; window unspecified | 80.0% | 4.57 |
| EQUITY | AAPL / LONG / `vt_equity_two_day_rsi_reversal` | 113 | Cumulative through sidecar snapshot; window unspecified | 94.7% | 49.3 |
| EQUITY | AAPL / LONG / all strategies (`*`) | 121 | Cumulative through sidecar snapshot; window unspecified | 90.9% | 13.32 |
| EQUITY | MSFT / LONG / all strategies (`*`) | 10 | Cumulative through sidecar snapshot; window unspecified | 20.0% | 0.5 |

This is mixed symbol evidence, not class-level validation. The FX RSI2
mean-reversion LONG rows are consistently weak across the listed pairs, while
the CADJPY SHORT row points the other way on a much smaller cohort; direction
and sample selection matter. The AAPL strategy result is an exceptional
single-symbol lead, not proof of a repeatable equity edge: the same snapshot's
whole EQUITY class fails PF, expectancy, and risk gates, and the class-level
top source is `UNKNOWN` with a `0.9576` share (source field as reported).
MSFT's all-strategy aggregate also does not support broad equity profitability.
The sidecar does not establish independent feed replication, an explicit
calendar window, or why the very large AAPL PF is so different from the class
aggregate. Keep it as a replay/audit lead only.

## Evidence-supported source autopsy

1. **The class-level failures are real in the current first-touch payload.**
   The two intrabar class records have PF below 1 and are marked `FAIL`.
   FOREX also has low WR; EQUITY has a higher WR but still loses on PF and
   reported expectancy. These facts support "not profitable in this cohort,"
   not the stronger claim that no future strategy can work.
2. **Outcome definitions materially affect EQUITY's appearance.** The
   verdict's daily EQUITY view is profitable by PF while its selected
   first-touch cohort is not, and the payload raises a divergence flag.
   Current evidence cannot attribute that discrepancy to a specific code
   defect or trade-lifecycle cause; that causal investigation is out of scope.
3. **Attribution is a material blind spot.** In the current snapshot,
   `top_source=UNKNOWN` accounts for `0.8759` of FOREX's source share
   (`n=568`, cumulative through verdict snapshot, window unspecified) and
   `0.9576` of EQUITY's (`n=233`, same timeframe definition). This prevents a
   convincing source-by-source explanation of the class losses.
4. **The statistical gates are not a substitute for missing independent
   breadth.** FOREX has one strategy eligible for the current strategy-level
   tests; its PBO is null because at least two strategies with `n>=20` are
   required, SPA has no pass, and DSR fails. EQUITY has one strategy tested;
   DSR and SPA pass in the verdict payload, but PF, expectancy, bootstrap
   interval, MDD/CVaR, and the single-source check fail. Its PBO is also null
   for insufficient eligible strategy count. Both gate records are
   cumulative through the verdict snapshot, with the start/window
   unspecified.

## Read-only repository evidence for lifecycle concern

At the follow-up request, I read only the committed `origin/main` version of
`copy_trader_intel/generate_dashboard_data.py` (commit
`b5e46d0dfce4853ead16d7277a69651a1ebb0551`), not the working-tree version.
These are verbatim excerpts with source line numbers:

```python
# copy_trader_intel/generate_dashboard_data.py, origin/main lines 868-876
    closed_files = ['closed_trades.json', 'highscore_closed_picks.json', 'clone_closed_picks.json', 'consensus_closed_picks.json']
    for cf in closed_files:
        c_picks = load_json(CT_DATA / cf) or []
        if isinstance(c_picks, list):
            all_picks.extend(c_picks)
        elif isinstance(c_picks, dict):
            # sometimes wrapper dicts
            all_picks.extend(c_picks.get('picks', []))
    # Deduplicate by id (prefer CLOSED statuses over OPEN)
```

```python
# copy_trader_intel/generate_dashboard_data.py, origin/main lines 1113-1125
        clone_audit_picks.append({
            "symbol": sym,
            "direction": direction,
            "entry_price": entry,
            "current_price": current_price,
            "pnl_pct": round(pnl, 2),
            "take_profit": cp.get("take_profit"),
            "stop_loss": cp.get("stop_loss"),
            "confidence": round(clone_score, 1),
            "source_system": "copy_trader_clones",
            "strategy": cp.get("strategy", "clone_unknown"),
            "status": "OPEN",
            "timestamp": cp.get("timestamp", datetime.now(timezone.utc).isoformat()),
```

The first excerpt shows closed-pick files being appended to `all_picks`; the
second shows generated clone audit rows assigned `OPEN`. Together these source
lines substantiate a lifecycle/stale-closed-resurrection concern for
investigation. They do not by themselves prove that a specific closed row is
reopened in a published metric; that requires matching row IDs through the
output path. No proposed edits or tests were inspected.

The current payload does **not** establish whether spread/financing assumptions,
market regime, signal quality, data-provider coverage, or execution timing
caused the losses. Those remain testable hypotheses, not findings. The high
`day_concentration` values reported by the intrabar sidecar are also worth
tracking—FOREX `0.164` (`n=568`) and EQUITY `0.446` (`n=233`), cumulative
through the intrabar snapshot, window unspecified—but the JSON does not define
the scale in enough detail here to infer a concentration threshold breach.

## Reconciliation with existing investigations

- `reports/equity_source_reconcile_2026-05-18.md` documented a historical
  cross-source discrepancy: EQUITY `n=240` in one dashboard view versus
  `n=44` in a local ledger, with non-comparable WR/PF across sources. Its
  snapshot is 2026-05-18 and its interval is unspecified; it is evidence that
  cohort identity has previously been a problem, not a current metric.
- `reports/equity_watch_root_cause_2026_05_17.md` similarly described
  mismatched sample availability for statistical testing. Those May figures
  are superseded by the October public snapshots and should not be blended
  with them.
- `reports/deep_dive_FOREX_2026-05-31.md` recorded a historical FOREX
  policy-clean cohort of `n=28`, WR `28.57%`, PF `0.037`, with a
  snapshot-defined but otherwise unspecified window. It also flagged
  source/strategy concentration and included external validation options.
  That source autopsy is useful as a hypothesis list, but it is not confirmed
  by the current October `UNKNOWN` source attribution.
- `reports/2026-06-06-money-ready-screen-clean-cohort.md` explicitly treated
  screened leads as candidates rather than proven edges and required
  first-touch validation before paper-pilot. Its June cohort is historical;
  no June metric is treated as current here.

## External replication alternatives

These are independent *checks to run later*, not signals to trade or evidence
of profit:

| Class | Independent comparison | What it can test | Key caveat |
|---|---|---|---|
| FOREX | Rebuild signal timestamps and first-touch exits from a second spot-quote source; compare with CME currency-futures direction and timestamp data. | Whether pair/direction results survive a different quote source, session boundary, and bar construction. | Futures basis/roll and spot spreads/rollover are not interchangeable; include executable costs and financing. |
| FOREX | Compare frozen directional calls with CFTC/CME positioning and managed-futures references such as DBMF/KMLM, as suggested in the 2026-05-31 deep dive. | Whether a source-independent macro/trend context corroborates or contradicts a signal. | These are context/benchmark series, not ground truth for an individual FX trade. |
| EQUITY | Reconstruct picks against an independent split/dividend-adjusted daily/intraday provider and a point-in-time universe; compare with SPY and relevant sector ETF returns. | Corporate-action, timestamp, universe-selection, and benchmark-relative sensitivity, especially for the AAPL lead. | Vendor coverage and adjusted-price policies differ; preserve the exact historical universe and never select symbols using future membership. |
| Both | Keep a sealed, chronological holdout and compare frozen picks with a simple predeclared benchmark under the same costs and holding period. | Whether any observed edge persists out of sample instead of being a retrospective symbol/strategy winner. | Do not retune on the holdout or treat benchmark underperformance as proof of absolute profitability. |

## Paper-only 30 / 60 / 90 day recovery plan

No production gate changes, live trades, scanner runs, or strategy promotions
are proposed.

- **Days 0–30 — Establish comparable evidence.** After the separately owned
  lifecycle repair is complete, capture immutable, timestamped paper cohorts
  with explicit class, symbol, side, strategy, source, entry/exit reason,
  quote/bar provider, and cost assumptions. Reconcile daily and first-touch
  outcomes on the *same trade IDs*. Do not modify the entry rules during this
  baseline. Resolve `UNKNOWN` source attribution before claiming an emitter
  autopsy. Run the external quote/adjusted-price comparisons above in
  shadow/paper mode.
- **Days 31–60 — Frozen forward observation.** Continue the unchanged paper
  cohort through different calendar months; report per-class and
  symbol×direction×strategy results with explicit dates, `n`, first-touch
  outcomes, spread/slippage/rollover costs, drawdown, and benchmark-relative
  returns. Keep source/provider and market-regime slices separate. Retain
  losing and expired outcomes; do not tune against the accumulating holdout.
- **Days 61–90 — Independent replay and decision record.** Re-run the frozen
  cohort against the second data source and sealed benchmark, document
  differences trade-by-trade, and publish a read-only result. Continue
  paper-only unless every acceptance criterion below is met; otherwise
  preserve the fail/insufficient result and identify the unresolved evidence
  gap rather than relaxing a gate.

## Risk register

| Risk | Evidence / class, n, timeframe | Severity | Control |
|---|---|---|---|
| Daily-versus-first-touch cohort divergence | EQUITY daily `n=118` and intrabar `n=233`, cumulative through verdict snapshot, window unspecified; PF `1.2624` versus `0.8642` | High | Compare same trade IDs and lifecycle timestamps before interpreting dashboard summaries. |
| Unknown source attribution | FOREX `n=568`, source share `0.8759`; EQUITY `n=233`, source share `0.9576`; cumulative through verdict snapshot, window unspecified | High | Require non-unknown emitter/source lineage in paper records and in every postmortem. |
| Single-symbol outlier mistaken for an edge | AAPL / LONG / `vt_equity_two_day_rsi_reversal`, EQUITY `n=113`, WR `94.7%`, PF `49.3`; cumulative through sidecar snapshot, window unspecified | High | Independently replay and keep a sealed holdout; do not promote from this row. |
| Small symbol-direction cohorts and multiple comparisons | FOREX `forex_rsi2_mean_reversion` rows above have `n=15–36`; cumulative through sidecar snapshot, window unspecified | High | Freeze hypotheses before testing; report all symbol/direction cells and correct for multiple testing. |
| Execution/cost-model mismatch | Both classes; current snapshot-level data does not establish provider-level spread, financing, or fill fidelity; timeframe unspecified | Medium-high | Recompute paper outcomes with independent executable-cost assumptions, including FX rollover. |
| Stale historical diagnosis applied as current | Historical reports dated 2026-05-17 through 2026-06-06; their windows are not comparable to October | Medium | Keep prior reports as hypotheses only; use the October public snapshot for current status. |

## Acceptance criteria — remain paper-only

Do not describe either class or a symbol/strategy as consistently profitable
unless the evidence package satisfies all of the following:

1. Trade-level source, class, symbol, side, strategy, and lifecycle timestamps
   are attributable; daily and first-touch cohorts reconcile on identical
   trade IDs, and no unexplained `UNKNOWN` source dominates the result.
2. The frozen out-of-sample paper cohort spans at least three calendar months,
   has at least 30 resolved observations per month and at least 100 total
   resolved observations for the evaluated class/strategy. Symbol-level claims
   are also reported by side and strategy; low-`n` cells remain explicitly
   exploratory.
3. Outcomes use first-touch validation, count expired/unresolved outcomes
   honestly, exclude invalid geometry, and include realistic spread,
   slippage, and—for FX—rollover/financing costs.
4. Any money-readiness review meets the existing Tier-2 floor and all
   applicable current statistical, risk, recency, and concentration gates:
   PF at least 1.5, WR at least 50%, MDD at most 20%, with positive net
   expectancy and no failed applicable validation. Passing a win-rate or one
   significance test alone is insufficient.
5. Results reproduce on an independent data source and a sealed holdout
   without changing the entry/exit rules. Passing these criteria permits only
   a documented paper-pilot review; this report does not authorize real-money
   sizing.

## Source index

- Public verdict:
  `https://findtorontoevents.ca/audit/data/money_ready_verdict.json`
  (`generated_at=2026-10-22T20:38:45.925100+00:00`).
- Public class intrabar summary:
  `https://findtorontoevents.ca/audit/data/intrabar_truth_by_class.json`
  (`generated_at=2026-10-22T20:34:44Z`).
- Public symbol/direction/strategy intrabar summary:
  `https://findtorontoevents.ca/audit/data/intrabar_sym_dir_fwd.json`
  (`generated_at=2026-10-22T20:34:45Z`).
- Historical context: `reports/equity_source_reconcile_2026-05-18.md`,
  `reports/equity_watch_root_cause_2026_05_17.md`,
  `reports/deep_dive_FOREX_2026-05-31.md`, and
  `reports/2026-06-06-money-ready-screen-clean-cohort.md`.

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
