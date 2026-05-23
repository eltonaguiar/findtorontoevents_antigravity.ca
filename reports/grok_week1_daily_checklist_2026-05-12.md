# Grok — Week 1 Daily Checklist (2026-05-12)

Operational addendum to `reports/quant_rescue_master_plan_2026-05-12.md`.
Day-by-day execution for Week 1 (Data Truth Layer + Dragger Quarantine).

## Day 1 — Data audit + zero-PnL count

- [✓] Zero-PnL artifact filter (commit `dd8e8282537`) — shipped
- [✓] WON-vs-PnL sign-coherence guard (commit `22b677c1167`) — shipped
- [ ] Run full ETL audit script `tools/data_audit/etl_checksum.py` — NEW SCRIPT
- [ ] Count + list all zero-PnL trades (per `reports/zero_pnl_backfill_sql_2026-05-12.md` Step 1 SQL)
- [ ] Deploy basic data-quality dashboard (red/yellow/green per table) — NEW

## Day 2 — Quarantine

- [✓] Symbol-triple block 5 cohorts (commit `597819d79c7`) — shipped
- [✓] meta_strategy CRYPTO blanket (commit `5c7a8c43a27`) — shipped
- [✓] kimi_signal_tracking blacklisted (prior commit `4a2d337a5dc`) — shipped
- [✓] crypto_soc 3 named draggers blocked — shipped
- [ ] `quarantined_emitters.json` consolidated registry — NEW
- [ ] `is_quarantined()` runtime helper in `quality_gates.py` — NEW
- [ ] Verify 0 trades from quarantined in next 48h production run

## Day 3 — ML staleness

- [✓] Mtime watchdog hard-fail (commit `db5bcfa0f04`) — shipped
- [ ] Manually trigger `enhanced-ml-crypto.yml workflow_dispatch(mode='train')` to confirm retrain
- [ ] Verify all .joblib mtimes <7d after one full cycle
- [ ] Run fresh `metrics_by_asset_class.csv` generation post-retrain

## Day 4 — v3b + paper-pilot routing

- [✓] v3b SignalSpec validator + 15 pytest cases (commits `ba4a40ac36a` + `aad6cd94c64`) — shipped
- [✓] Round 10 updates/index.html entry (commit `26cd0f39d01`) — shipped
- [ ] Wire v3b validator into `tools/research/orchestrator.py` input path (PR #2 of 4)
- [ ] `--mode=paper` flag in orchestrator routing
- [ ] active_picks_sync DRY-RUN evidence inspection (when first cron output lands)

## Day 5-7 — End-to-end + first metrics

- [ ] Test: new signal → v3b validation → paper-pilot routing → JSON sidecar
- [ ] Review first clean metrics (post zero-PnL filter + post dragger quarantine)
- [ ] Prepare COMMODITY + EQUITY paper-pilot configs
- [ ] First-week performance review report

## Success criteria by end of Week 1

- ✓ Zero-PnL filter active (artifact rows excluded from /audit aggregates)
- ✓ All known draggers blocked
- ✓ ML staleness mtime gate fires on stale models
- ✓ v3b SignalSpec scaffolding ready for production wire-up
- Dashboard reflects DB reality (truth-layer banner shipped commit `dd8e8282537`)

**Session status:** 4 of 7 days fully shipped. Day 1 ETL script + dashboard,
Day 2 quarantined_emitters.json consolidation, Day 4 v3b orchestrator
wire-up + Day 5-7 end-to-end are queued for next session.

## Refs

- Master plan: `reports/quant_rescue_master_plan_2026-05-12.md`
- All 30+ session commits today on origin/main
