# 2026-04-30 — Penny skyrocket detector wired into /audit

## Summary

`alpha_engine/strategies/skyrocket_detector.py` (593 LOC, SIDU-pattern penny
stock detector) was a fully-built orphan with no scheduled emitter. This PR
wires it into the audit pipeline:

- New workflow `.github/workflows/penny-skyrocket-runner.yml` runs the
  detector daily on weekdays at 14:48 UTC.
- `alpha_engine/data/skyrocket_picks.json` registered as the
  `skyrocket_detector` source in `audit_trail.dashboard_generator.JSON_PICK_SOURCES`.

## Why this PR exists

Per [Gemma4-cloud's audit](updates/2026-04-30-penny-meme-integration-pr-plan.md):
the detector exists with sophisticated SIDU pattern detection (40% TP /
15% SL / 5-day max hold; backtest claims 311% gain) but is not invoked by
any scanner or workflow. It has been sitting unused since `4c65e6698a`
(roughly 2 weeks).

This is a PR-LIFT-style wire-up — analogous to PR #544
(TradingAgents emitter) — without touching the detector's logic. The
detector emits picks under:

- `source_system="skyrocket_detector"`
- `strategy="skyrocket_detector"`
- `asset_class="EQUITY"`
- `category="penny"` ← concept tag for Cursor's audit-concepts integration
- `direction="LONG"`, `signal_type="BUY"`
- `max_hold_days=5` → SWING via `cross_aggregation/timeframe_classifier.py`
  (the timeframe classifier wired in PR #545 already handles this via the
  `max_hold_days` field check, no new mapping needed)

## Naming collision (avoided)

There is an unrelated CRYPTO ML project at `skyrocket_detector/` (root
directory) with its own workflow at `.github/workflows/skyrocket-detector.yml`.
The new workflow name is `Penny Skyrocket Detector` and the file is
`penny-skyrocket-runner.yml` to keep the two systems clearly separate.
The pinned regression test
`test_workflow_invokes_correct_module` enforces this.

## What this PR does NOT do

- No backtest validation. Gemma4-cloud cited "311% gain on SIDU" but I did
  NOT independently re-run that backtest; treat it as a claim, not a
  verification. Once the detector accumulates n>=20 closed picks the
  forward-validator will produce real metrics.
- No score-floor adjustment. The detector's internal threshold of
  `score >= 50` is preserved (raised from 25 in commit history; backtest
  showed 30% WR at 25 → 50%+ at 50).
- No watchlist expansion. Default watchlist of 40 small-cap tickers is
  kept; can be overridden via the workflow's `inputs.symbols` for ad-hoc
  scans.
- No concept-taxonomy stamping. The pick's `category="penny"` field is
  the raw input; the `concept_family="penny_stock"` derivation lands when
  Cursor's Phase 1 helper ships.
- No env-flag gate. Rationale: the detector's score threshold (>=50) is
  a strong natural gate (typical scans emit 0-2 picks). The workflow's
  cron is daily-only, so cost is bounded. If picks prove noisy, the
  follow-up flips the workflow `concurrency.cancel-in-progress: false` to
  `true: false` — i.e. just disable the cron.

## Files

- `.github/workflows/penny-skyrocket-runner.yml` (new, 84 LOC)
- `audit_trail/dashboard_generator.py` (+15 LOC — JSON_PICK_SOURCES entry + comment)
- `tests/test_skyrocket_detector_wireup.py` (new, 8 tests)
- `updates/2026-04-30-skyrocket-detector-wireup.md` (this doc)

## Verification

After merge + first cron run (next weekday 14:48 UTC), expect:

1. `alpha_engine/data/skyrocket_picks.json` to exist in repo (committed
   by the runner via `safe_push.sh`).
2. If any tickers in the watchlist meet the `score >= 50` threshold:
   picks emit under `source_system="skyrocket_detector"`,
   `category="penny"`, `asset_class="EQUITY"` on /audit.
3. Empty scans are normal — the detector is highly selective. Watch the
   workflow run summary for the `picks: N` count.

## Risk: LOW

- Pure additive wire-up; no existing strategy or pick path is changed.
- Dashboard reader (`_safe_json` → `_extract_picks`) gracefully handles
  missing or empty JSON files. If the workflow never runs, the source
  appears with 0 picks (no error).
- Workflow uses existing `safe_push.sh` retry-with-rebase script, so
  concurrent commits to `alpha_engine/data/` (e.g. by
  `alpha-engine-live.yml`) cannot deadlock.
- Naming collision with `skyrocket_detector/` (crypto-ML) explicitly
  guarded by test `test_workflow_invokes_correct_module`.

## Sequence note

This PR is the second in a series the user requested. Order:

1. PR #545 ✓ — TF classifier + BOND env + PEAD persistence (2026-04-30, merged)
2. **PR #546 (this) — Penny skyrocket detector wireup**
3. PR #547 (next) — UEPS active-sync workflow fix (1-line `git add`)
4. PR #548 — TF=LONG_TERM dashboard label
5. PR #549 — Concept taxonomy Phase 1 (Cursor's `assign_concept_fields`)

Each PR is independent + verifiable; no cross-dependencies.
