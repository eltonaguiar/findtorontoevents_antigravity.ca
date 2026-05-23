# Micro Futures Scoring Review

Date: 2026-04-09

## Summary

The repo now has real micro-futures plumbing, but not real micro-futures evidence.

- Pipeline support exists: micro contracts normalize into canonical futures, get futures asset-class routing, and have a Yahoo Finance live-price fallback.
- The current realized cohort does not justify premium scoring. In the current dashboard closed-book slice, there are no micro-contract outcomes yet, and the broader futures-like cohort is still heavily negative.
- The biggest immediate bug was not theoretical. `alpha_engine/elite_scorer.py` could throw `name 'source_sys' is not defined` on futures-style copy-trader rows, which then poisoned `elite_breakdown` in active and closed picks.

## What The Current Data Says

Direct extraction from the live repo artifacts on 2026-04-09:

- `alpha_engine/data/closed_picks.json`: 4 futures-class closed rows in the engine export.
- `alpha_engine/data/active_picks.json`: 5 futures-class active rows in the engine export.
- `audit_dashboard/data/dashboard_data.json` `picks.recent_closed`: 15 futures-like rows when grouped by futures contract symbols (`GC=F`, `SI=F`, `ZN=F`, `CL=F`, `HG=F`, `PL=F`).
- `audit_dashboard/data/dashboard_data.json` `picks.active`: 0 futures-like rows currently survive the active dashboard slice.
- Micro contracts present in realized outcomes: 0.

Closed futures-like cohort from the dashboard slice:

- 15 rows total.
- 14 losses, 1 win.
- Mean realized `pnl_pct`: about `-1.27%`.
- Mean score: `42.8`.
- Mean confidence: `0.748`.
- Mean trust score: `2.4`.
- All rows with a walk-forward verdict were `FAILING`.
- Available forward WR values were only `0.0`, `12.5`, and `26.7` for that cohort.

That is not a premium book. It is a probation book.

## Implementation Contradiction

The codebase currently contains both of these truths at the same time:

- New support for micro futures in `alpha_engine/config.py`, `alpha_engine/smart_picks_engine.py`, and `alpha_engine/conviction_stack.py`.
- Legacy skepticism in `audit_trail/quality_gates.py`, including a futures asset-class penalty and comments that explicitly admit the sample is tiny and noisy.

Those are not actually inconsistent. They reflect the right split:

- Support the pipeline now.
- Do not let the scorer pretend the evidence is already good.

## Enhancements In This PR

### 1. Fix elite scoring on futures-style copy rows

`alpha_engine/elite_scorer.py` now initializes `source_sys` at the top of `compute_elite_score()` and reuses it consistently.

Why it matters:

- Active and closed futures rows were carrying `_error: "name 'source_sys' is not defined"` inside `elite_breakdown`.
- That made the scorer look worse than it already was and removed useful diagnostics from exactly the cohort that needs scrutiny.

### 2. Add explicit futures probation scoring

`audit_trail/quality_gates.py` now applies a dedicated penalty to futures-contract picks that are still marked `forward_test_only` and do not have validated sample support.

Behavior:

- `-20` if the row is still forward-test-only with zero effective forward trades.
- `-12` if it is forward-test-only with only a thin/weak sample.

Why this is the right place:

- `_apply_score_penalties()` already owns evidence-quality adjustments before dashboard ranking and smart-pick gating.
- This keeps the rows visible for learning while pushing them out of premium ranks until they earn that position.

### 3. Add regression coverage

Tests added:

- `tests/test_elite_scorer.py`: protects against the `source_sys` NameError on a futures-style copy row.
- `tests/test_quality_gates.py`: verifies that a forward-test-only futures pick with no validated sample scores below an otherwise similar validated futures pick.

## Take

The next mistake would be to argue about whether micro futures are “supported” or “unsupported.” They are supported.

The real problem is calibration. The current scorer still does not have enough clean, validated micro-futures evidence to award premium ranks safely. This PR makes that reality explicit in code instead of leaving it as a comment-level warning.

## Redis Bus And PR Context

Recent Redis bus traffic and repo PR history both point in the same direction: the stack is moving toward broader non-crypto support faster than the evidence base is catching up.

### Bus messages

Recent bus items that matter:

- `cursor-composer` posted a TradingView multi-asset update calling out micro-futures fallback and minimum-size guards as follow-up work.
- `kimi-quant-review` broadcast a broader quant-quality summary: crypto remains the only clearly profitable asset class, while non-crypto lanes still trail badly.
- `cursor-hc-audit` posted multiple high-conviction filter reviews centered on blacklist behavior, dormant conviction-tier paths, and the need for evidence-backed gating.
- A short `MICRO_FUTURES_SCORING_AUDIT` broadcast was also present in the bus log, consistent with the findings in this document.

My take:

- The TradingView bus notes are operationally relevant but not a substitute for scoring evidence. Better routing and order-entry handling do not make the futures cohort statistically good.
- The quant-quality broadcast is directionally aligned with this review. It strengthens, not weakens, the case for keeping futures on probation inside the ranking stack.
- The high-conviction audit traffic matters most for product behavior. If the UI or HC filters get widened again without asset-specific evidence, futures rows will be over-promoted before they deserve it.

### Other PRs found

At the time of review, there were no open PRs in the repository. Recent merged or otherwise relevant PRs include:

- `#53` `feat: integrate Policy v3 into existing scoring pipeline`
- `#52` `feat: Policy v3 — Non-crypto HF tiers, regime-aware direction, goldmine floor, alerts, backtest`
- `#41` `Hedge fund scoring enhancement`
- `#37` `feat: deploy 5 per-asset-class agents + fix 4 silent scoring errors (Equities, Forex, Commodities, Futures, ETFs)`
- `#39` `Hedge fund scoring enhancements — quant audit`

My take on those PRs relative to this one:

- `#52` and `#53` are the most relevant neighbors because they widen non-crypto scoring behavior and HF tier logic. That makes explicit futures probation more important, not less.
- `#37` is structurally important because it established the per-asset-class workflow idea. But having a futures workflow does not imply the futures outputs are ready for premium ranking.
- `#41` and `#39` pushed broad scoring changes. This PR is intentionally narrower: it fixes a concrete scorer bug and inserts an evidence-quality brake where the live futures cohort is still weak.

Risk to watch after merge:

- Any future PR that broadens non-crypto conviction or lowers score floors should be checked against the same cohort used here. Otherwise the codebase will keep oscillating between “support futures” and “silently suppress futures” without ever resolving the evidence problem.

## Next Work That Actually Matters

If you want the futures lane to become investable rather than merely routable, the next upgrades should be evidence-building rather than cosmetics:

1. Add a futures-specific validated feature set: term structure, carry/roll yield, and COT-style positioning.
2. Separate micro/index futures from commodity futures in scoring analysis instead of mixing `MES/MNQ` aspirations with `GC/SI/CL` realized rows.
3. Require a larger forward sample before any futures contract can enter high-conviction ranking.
4. Audit why engine-export active futures rows exist while the dashboard active slice currently shows zero futures-like rows surviving.