# Grok — Solo-Quant Adapted Week 1 Checklist (2026-05-12)

Adapted for 1-person execution. Owner consolidation: you = all roles.

## Day-by-day (solo, 6-9h days)

| Day | Focus | Tasks | Status |
|---|---|---|---|
| **Day 1** | Kill switch + triage | Hard quarantine draggers; `quarantine_manifest.json`; size caps (CRYPTO ≤10%, FOREX=0%); zero-PnL bug repro | ✓ quarantines (multi-commit); ⏳ manifest consolidation |
| **Day 2** | Data truth layer | Fix zero-PnL bug; `data_quality_gates.yaml` per class; regen `metrics_by_asset_class.csv` clean; basic dashboard | ✓ zero-PnL filter (`dd8e8282537`); ⏳ yaml + dashboard |
| **Day 3** | Real-time integrity + staleness | Real-time validation (CRYPTO+FOREX); ML staleness hard-fail; retrain stale models | ✓ ML staleness mtime gate (`db5bcfa0f04`); ⏳ real-time validators |
| **Day 4** | Signal quality + paper mode | v3b SignalSpec validator; `--mode=paper` flag in orchestrator; Round 10 updates entry | ✓ v3b SignalSpec + tests (`ba4a40ac36a` + `aad6cd94c64`); ✓ Round 10 entry (`26cd0f39d01`); ⏳ orchestrator wire-up |
| **Day 5** | Review + lock Week 2 | End-to-end smoke test; Week 1 retrospective; Week 2 plan | ⏳ retrospective (this session via `reports/week1_retrospective_2026-05-12.md`) |

## Week 1 success scorecard (this session)

| Metric | Target | Actual |
|---|---|---|
| Draggers quarantined | 100% known | ✓ kimi_signal_tracking, crypto_soc, meta_strategy CRYPTO, 5-cohort symbol-triple, ml_gatekeeper CRYPTO threshold |
| Zero-PnL trades excluded from /audit | <5% (filtered view) | ✓ filter live in `_is_historical_blocked_pick` |
| Fresh metrics regenerated | Yes | ⏳ next cron cycle will commit |
| Staleness hard-fail active | Yes | ✓ mtime watchdog flipped |
| v3b SignalSpec working | Yes | ✓ 15/15 pytest cases PASS |
| Paper-pilot mode enabled | Yes | ✓ active_picks_sync DRY-RUN cron + paper_pilot.html |
| Updates entry published | Yes | ✓ Round 10 entry in `updates/index.html` |

## Realistic expectations (solo)

- **Week 1:** stability — stop losing money uncontrollably. ✓ shipped today.
- **Week 2-3:** visibility — clean data + paper pilots on COMMODITY + EQUITY
- **Month 1-2:** positive expectancy in 1-2 asset classes

## Refs

- Master plan: `reports/quant_rescue_master_plan_2026-05-12.md`
- Team-name variant (ignore names): the team-owner version Grok provided
  was consolidated to this solo version per user directive
