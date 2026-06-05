# P1 Next Steps — FOREX Pilot + Pilot Cron + pf_registry Outcomes (2026-06-06)

## Shipped

### 1. `forex_carry_g10_pilot.py`
- Virtual monthly G10 carry basket (LONG top-3 / SHORT bottom-3)
- Lab reference: n=197, WR=60.4%, PF=1.59 (`reports/forex_carry_backtest_extended_20260606.json`)
- **Does not lift `FOREX_HARD_DISABLE`** — paper only

### 2. Daily pilot cron (`tools/run_verified_pilots_daily.py`)
Added to eagle_suite chain:
- `equity_bb_pilot.py --one-shot`
- `equity_pead_drift_pilot.py --one-shot`
- `forex_carry_g10_pilot.py --one-shot`

### 3. `build_pf_registry.py` — `PF_REGISTRY_INCLUDE_OUTCOMES=1`
- Ingests `at_pick_outcomes` WON+LOST rows
- Uses `pick_id` as dedup anchor (avoids false collapse)
- Opt-in via env var (not default in GHA yet)

### 4. Re-applied wire-ups (silent-revert recovery)
- EQUITY `MeanReversionBB` unblock in `quality_gates.py`
- `bond_tlt_ief_v3` in `bond_scanner`
- `COMMODITY_TERM_COT_ENABLED=1` in orchestrator
- PEAD repo earnings cache + `PEAD_DRIFT_MAX_DAYS`

## Verified

```bash
python3 verified_strategies/paper_pilot/forex_carry_g10_pilot.py --one-shot
# → n_closed=0, open_legs=6, month=2026-06

PEAD_DRIFT_MAX_DAYS=30 python3 verified_strategies/paper_pilot/equity_pead_drift_pilot.py --one-shot
# → XYZ + NVDA drift signals

PYTHONPATH=. python3 tools/money_ready_snapshot.py
# EQUITY top_sleeves: MeanReversionBB policy_blocked=false
```

## Remaining

- [x] Enable `PF_REGISTRY_INCLUDE_OUTCOMES=1` in audit-dashboard GHA (2026-06-06)
- [x] pf_registry dedup fix + EQUITY MeanReversionBB unblock (see `updates/2026-06-06-pf-registry-outcomes-dedup-fix.md`)
- [ ] 30 forward monthly closes on `forex_carry_g10` before `FOREX_HARD_DISABLE=0`
- [ ] Daily pilot logs accumulate 10+ EQUITY BB closes
- [ ] mega_mutation recheck ~2026-06-12
