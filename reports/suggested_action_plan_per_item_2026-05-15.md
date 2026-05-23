# Suggested Action Plan per Enhancement Item (2026-05-15)

Source: `reports/enhancement_plan_per_asset_class.md` plus the consolidated scope notes in `reports/asset_class_enhancements_pr_scopes_2026-05-15.md`.

Use this as an execution checklist. Each item should ship in a small PR with a production caller, a verification command, and its own `updates/` note when code changes are made.

## Execution Order

1. Ship cross-cutting safety and observability first: M-013, M-041, M-044, M-049, M-043.
2. Then unblock the best current edge: EQUITY VIX/large-cap work, COMMODITY COT/cotton validation, CRYPTO drag controls.
3. Keep weak or thin classes in shadow/pilot mode: FOREX, BOND, FUTURES.
4. Treat pure research modules as opt-in sidecars until backtests and production callers are ready.

## EQUITY / ETF

### M-009 - PEAD Strategy on EQUITY top-100
- Suggested action: Build a small PEAD sidecar first, limited to top-100 liquid equities and a two-day post-earnings window.
- Wire-up target: `score_pick`, `passes_active_gate`, and the EQUITY scanner path only after backtest evidence clears the bar.
- Verification: Backtest top-100 symbols with resolved outcomes; require PF > 1.5, WR > 50%, and n >= 100 before live sizing.
- Risk/dependency: Needs a real earnings calendar source; do not use placeholder earnings dates.

### M-026 - EQUITY day-of-week tilt
- Suggested action: Add `EQUITY_DOW_TILT=1` as a disabled-by-default flag, then apply the Tue/Wed tilt in `score_booster.py`.
- Wire-up target: `score_booster.py` and downstream payload telemetry.
- Verification: Compare 30-day live tape with and without the tilt; require WR lift >= 0.5 percentage points without worse drawdown.
- Risk/dependency: Small effect size, so keep it as a score adjustment, not a hard gate.

### M-013 - ConcentrationChecker production wire-up
- Suggested action: Promote `ConcentrationChecker` into `passes_active_gate` as a shared hard cap.
- Wire-up target: `audit_trail/quality_gates.py` for all asset classes that produce sized picks.
- Verification: Add tests for symbol concentration, class concentration, and insufficient-data behavior.
- Risk/dependency: Coordinate with position sizing work so a block does not conflict with later sizing reductions.

### M-006 - HIGH_CONVICTION dashboard swap
- Suggested action: Change the dashboard filter definition from raw confidence to `trust_score >= 0.6`.
- Wire-up target: `audit_dashboard/template.html` and any dashboard payload label/tooltip.
- Verification: Local dashboard smoke test plus a before/after count check; HIGH_CONVICTION n should not swing by more than 10% unless explained.
- Risk/dependency: Make the UI label explicit so users know the filter is trust-score based.

### M-036 - ETF universe expansion
- Suggested action: Expand the ETF universe gradually, starting with XLF/XLE/XLK and any high-liquidity sector ETFs already supported by data.
- Wire-up target: `alpha_engine/config.py`, scanner symbol lists, and dashboard classification.
- Verification: Rung-5 sizing only until PF > 1.5 and n >= 150; confirm no one symbol dominates PnL.
- Risk/dependency: Pair with concentration caps so XLE or another sector cannot dominate the ETF tile.

### M-023 - sector_dual_momentum_12_1
- Suggested action: Build this as an opt-in research sidecar before production wiring.
- Wire-up target: `tools/research/sector_dual_momentum.py` first; later `score_pick` or ETF scanner path if validated.
- Verification: Walk-forward test 12-1 momentum across sector ETFs with out-of-sample periods.
- Risk/dependency: PR must include a clear wiring plan if it remains sidecar-only.

### M-017 - Position sizer rebuild
- Suggested action: Rebuild `alpha_engine/position_sizer.py` as a stand-alone module with volatility target and max-per-name rules.
- Wire-up target: `score_pick` reporting first, then production sizing only after shadow logs look stable.
- Verification: Unit tests for caps, vol target, missing volatility, and class overrides.
- Risk/dependency: Do not couple it to unresolved PR dependencies; keep the first PR observational if possible.

## COMMODITY

### M-021 - COT lag-corrected re-run and paper pilot
- Suggested action: Apply the real three-day COT publication lag, then rerun the historical analysis before expanding live use.
- Wire-up target: resolver or data-prep layer that reads COT fields, not the dashboard display layer.
- Verification: Require WR >= 50% on lag-corrected history and a 30-pick paper pilot before scaling.
- Risk/dependency: COT dedup/inflation risk must be addressed before claiming COMMODITY edge quality.

### M-039 - Cross-commodity spread research
- Suggested action: Implement crude/natgas pair spread as a research module with a double-sort or carry/momentum design.
- Wire-up target: `tools/research/commodity_carry_momo.py` first; production scanner only after validation.
- Verification: Backtest spread legs separately and combined; check borrow/roll assumptions and concentration impact.
- Risk/dependency: This is research until live data and execution assumptions are proven.

### M-050 - Cotton live pilot
- Suggested action: Charter CT=F as a Stage-F pilot with daily reconciliation and fixed acceptance criteria.
- Wire-up target: existing COMMODITY scanner path and dashboard pilot annotation.
- Verification: 30 live picks, rolling PF > 1.5, WR > 50%, and no data-quality exceptions before scaling.
- Risk/dependency: Avoid over-weighting cotton until the COT lag and contract classification are clean.

### M-048 - Frontend Binance API-call ban and audit
- Suggested action: Remove any direct Binance calls from frontend code and route market data through backend/proxy paths.
- Wire-up target: `audit_dashboard/` frontend code and any API helper used by the dashboard.
- Verification: Static search for `binance.com` and Playwright console/network checks.
- Risk/dependency: Backend proxy must use the required multi-source failover chain.

### M-052 - PBO/CPCV harness
- Suggested action: Build the overfitting harness once, then run COMMODITY through it first because current numbers are strongest but COT-inflated.
- Wire-up target: `tools/validation/` or `tools/research/`, then report outputs consumed by dashboard/data reports.
- Verification: Produce PBO/CPCV metrics per strategy and fail strategies with unstable out-of-sample results.
- Risk/dependency: This should not change live picks in the first PR.

### M-051 - Multi-model swarm ensemble
- Suggested action: Keep this opt-in until measurement proves a WR/PF improvement over the current ensemble.
- Wire-up target: swarm runner configuration and shadow scoring output, not live gates.
- Verification: A/B shadow run by persona/model with n, WR, PF, latency, and cost.
- Risk/dependency: Avoid adding cost or transport fragility to production pick generation.

## CRYPTO / FUTURES

### M-001 - BTC UTC-hour death-zone filter
- Suggested action: Add a flagged `_hour_filter()` in `score_booster.py` that rejects 08-09Z and boosts 22Z only for validated BTC paths.
- Wire-up target: CRYPTO score booster and telemetry.
- Verification: Backtest and 30-day live rejection log; require drawdown reduction >= 10% without PF decay.
- Risk/dependency: Start as shadow/flagged because hour effects can decay.

### M-004 - CRYPTO drag autopsy and auto-quarantine
- Suggested action: Quarantine sub-PF/high-volume source systems automatically, with luxalgo and quan caps handled explicitly.
- Wire-up target: `audit_trail/quality_gates.py`, `tools/per_source_volume_cap.py`, and `production_scanner.py`.
- Verification: Next cron should show capped source volume and class PF not worse; add tests for volume/PF thresholds.
- Risk/dependency: Do not quarantine a source without enough resolved n unless the kill-gate evidence is sufficient.

### M-034 - Confidence-inversion gate
- Suggested action: Add a gate that penalizes or inverts confidence when validation metadata contradicts the agent claim.
- Wire-up target: `passes_active_gate` and payload fields that expose validation status.
- Verification: Unit test validated, failed-validation, and missing-validation cases.
- Risk/dependency: Missing validation should degrade cautiously, not silently invert every pick.

### M-027 - FUTURES Thursday short momentum
- Suggested action: Keep this as a shadow sidecar until n > 30; do not size from n=9.
- Wire-up target: FUTURES scanner path after classification is fixed.
- Verification: Track Thursday short picks separately with n, WR, PF, and drawdown.
- Risk/dependency: Depends on FUTURES classification fix so futures picks stop being routed to COMMODITY.

### M-028 - Drift-pause auto-flip dry run
- Suggested action: Add drift-pause as dry-run only, emitting `sizing_allowed=false` recommendations without physically blocking fills at first.
- Wire-up target: `audit_trail/quality_gates.py` and dashboard payload.
- Verification: Replay historical drift breaches; compare recommended pauses to realized drawdown.
- Risk/dependency: Coordinate with M-049 before allowing physical halts.

### M-049 - Kill-switch RED to physical halt verification
- Suggested action: Prove that RED/HALT status actually prevents fills in every production and paper-trading path.
- Wire-up target: `passes_active_gate`, scanner emit path, paper-trading pre-execute path, and CI audit tests.
- Verification: Add a CI test with synthetic RED state; expected result is no emitted/sized/executed pick.
- Risk/dependency: This is a P0 safety item and should precede larger sizing changes.

## FOREX

### M-007 - FOREX_HARD_DISABLE env switch
- Suggested action: Add `FOREX_HARD_DISABLE=1` default-on and an explicit override condition.
- Wire-up target: `alpha_engine/config.py`, `audit_trail/quality_gates.py`, and FOREX scanner output.
- Verification: With default env, FOREX emissions are zero; override requires carry PF > 1.0 and WR > 45% on 30-day roll.
- Risk/dependency: Keep mutate-before-kill documentation linked so the class is paused, not silently abandoned.

## BOND

### M-020 - Walkforward validator output path
- Suggested action: Mirror the COMMODITY walk-forward output pattern for BOND.
- Wire-up target: BOND walk-forward result writer and dashboard consumer.
- Verification: Confirm files are created, parsed, and shown without running dashboard generators locally.
- Risk/dependency: Add any new workflow-invoked path to the audit-dashboard path registry.

### M-024 - `ust_tsmom_level` BOND TSMOM
- Suggested action: Implement a simple TLT/IEF/SHY trend-following signal in shadow mode.
- Wire-up target: `alpha_engine/bond_strategies.py` and the non-crypto scanner path.
- Verification: Walk-forward test plus live shadow n growth; require PF > 1.0 before considering production sizing.
- Risk/dependency: BOND n is tiny, so avoid hard conclusions until sample size improves.

### M-032 - FRED macro filter wire-up
- Suggested action: Add FRED configuration and cached macro regime context, then use it as a filter or score modifier.
- Wire-up target: config, BOND/EQUITY/COMMODITY strategy readers, and freshness checks if persisted.
- Verification: Unit test no-key behavior, cache behavior, and fallback behavior.
- Risk/dependency: Do not repeatedly call FRED during scanner loops; cache and rate-limit it.

## CROSS-ASSET / INFRASTRUCTURE

### M-002 - DB Freshness Guardian workflow
- Suggested action: Add a lightweight scheduled workflow that runs freshness checks and emits dashboard-readable status.
- Wire-up target: `.github/workflows/db-freshness-guardian.yml`, `tools/db_freshness_check.py`, and `audit_dashboard/data/db_freshness.json`.
- Verification: Run workflow manually, confirm stale DBs fail clearly and fresh DBs pass.
- Risk/dependency: Ensure credentials are env/secret-only and no generated data causes CI loops.

### M-005 - Cross-DB strategy/system key consistency audit
- Suggested action: Schedule `tools/cross_db_consistency.py` daily and report mismatches as warnings or failures based on severity.
- Wire-up target: `.github/workflows/cross-db-audit.yml`.
- Verification: Dry-run against available DBs and produce a concise artifact/report.
- Risk/dependency: Do not block production on transient DB access until the check is stable.

### M-014 - Confidence schema 0-1 normalizer
- Suggested action: Clamp and normalize confidence at dashboard payload normalization boundaries.
- Wire-up target: `dashboard_generator._normalize_pick` and tests around pick payloads.
- Verification: Synthetic payloads with 0-1, 0-100, string, missing, and invalid confidence.
- Risk/dependency: Coordinate with trust-score migration so confidence and trust are not conflated.

### M-042 - Cursor verification-matrix scaffold
- Suggested action: Build the matrix generator as a report-only tool that records evidence per item.
- Wire-up target: `tools/build_verification_matrix.py` and `reports/verification_matrix.json`.
- Verification: Generated JSON includes item_id, claim, evidence, command, result, confidence, and blocker.
- Risk/dependency: Keep it read-only and avoid scanning huge files naively.

### M-044 - Canonical gate-policy parity test
- Suggested action: Extend tests so every gate config reader agrees on enabled/disabled gates and thresholds.
- Wire-up target: test suite around config readers and gate policy loaders.
- Verification: CI fails if any duplicate config source drifts.
- Risk/dependency: Run before adding more gates to avoid multiplying policy drift.

### M-045 - Pre-work observability PR
- Suggested action: Wire existing scaffold outputs for slippage, safety status, and protocol state into payloads before relying on them for decisions.
- Wire-up target: `score_pick`, `passes_active_gate`, and dashboard payload.
- Verification: Payload contract test plus dashboard rendering smoke.
- Risk/dependency: Observability first; physical blocking belongs in later safety PRs.

### M-046 - Validation-harness PR
- Suggested action: Create deterministic validation commands for payload schema, gate parity, and freshness preconditions.
- Wire-up target: `tools/validation/` and CI workflow steps.
- Verification: Each command exits non-zero on a synthetic bad fixture and zero on a good fixture.
- Risk/dependency: Keep tests fast enough for PR validation.

### M-047 - Sprint-sizing correction
- Suggested action: Update planning docs to mark resolver backfill as a two-week effort, not a weekend task.
- Wire-up target: master TODO/report docs only.
- Verification: Documentation diff only; no runtime tests required.
- Risk/dependency: Prevents over-committing on high-risk resolver work.

### M-043 - DB credentials env-var-only enforcement
- Suggested action: Add a secret-scanning job to PR validation and document required environment variables.
- Wire-up target: GitHub Actions PR workflow using `gitleaks` or `trufflehog`.
- Verification: Synthetic secret fixture fails in a controlled test; repo scan passes after cleanup.
- Risk/dependency: Never print secrets in logs; rotate any credential found in history.

### M-041 - Slippage validator, safety_status, and protocol_state wire-in
- Suggested action: Add callers for existing scaffolds so safety metadata is produced on every scored/gated pick.
- Wire-up target: `score_pick`, `passes_active_gate`, and dashboard payload normalization.
- Verification: Unit tests for missing slippage data, red safety status, and protocol-state transitions.
- Risk/dependency: Pair with M-049 before enforcing physical halt behavior.

### M-030 - last_signal_date in `systems` payload
- Suggested action: Add `last_signal_date` to the systems payload and render it in dashboard freshness/staleness views.
- Wire-up target: `dashboard_generator` and dashboard consumer.
- Verification: Payload schema test and dashboard smoke; stale systems should be visible.
- Risk/dependency: Use resolved signal timestamps, not file modification time.

### M-031 - readiness.by_class payload
- Suggested action: Add class-level readiness state fields that reflect n, PF, WR, gate state, and sizing permission.
- Wire-up target: `dashboard_generator` payload and `/audit` consumer.
- Verification: Contract test with healthy, blocked, insufficient-n, and disabled classes.
- Risk/dependency: Keep names stable because dashboard filters may depend on them.

## PR Bundling Suggestion

- PR-A Safety Core: M-013, M-041, M-044, M-049.
- PR-B Data/Infra Hygiene: M-002, M-005, M-030, M-031, M-043, M-045, M-046.
- PR-C EQUITY/ETF Edge: M-006, M-009, M-017, M-023, M-026, M-036.
- PR-D COMMODITY Validation: M-021, M-039, M-050, M-052, M-051.
- PR-E CRYPTO/FUTURES Controls: M-001, M-004, M-027, M-028, M-034.
- PR-F FOREX/BOND Rehab: M-007, M-020, M-024, M-032.

Keep each implementation PR to five files or fewer where practical. If a bundle becomes too broad, split by production caller rather than by documentation category.
