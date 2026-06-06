# Edge Hunt P1 Complete — Pilots, pf_registry, FOREX DB Wire (2026-06-06)

Session continuation after the 6-class subagent edge hunt. Goal #1: surface tradeable statistical sleeves per asset class without waiting months for forward n→100.

## Shipped This Session

### 1. pf_registry outcomes ingest (fixed + enabled)

**Problem:** `PF_REGISTRY_INCLUDE_OUTCOMES=1` loaded 9,815 `at_pick_outcomes` rows but `MeanReversionBB` never appeared in `by_asset_class_strategy_policy_clean_net`.

**Root cause (two bugs):**
- `source_system = "at_pick_outcomes"` made `_strategy()` collapse all rows to one key
- `v1::signal_validation::...` pick_ids truncated to `v1::signal` in `_trade_date()`, collapsing 168 distinct rows

**Fix:** `tools/build_pf_registry.py` — full `v1::` pick_id in `_trade_date()`; no `source_system` override on outcomes rows.

**GHA:** `.github/workflows/audit-dashboard.yml` → `PF_REGISTRY_INCLUDE_OUTCOMES: '1'` on hourly build.

**Verified:**
```
MeanReversionBB EQUITY — n=175, WR=54.9%, PF=1.73 (policy-clean net)
source: mysql:at_pick_outcomes (single-source flagged)
```

### 2. EQUITY MeanReversionBB unblock (re-applied after silent revert)

Removed `("EQUITY", "MeanReversionBB")` from `BLOCKED_ASSET_STRATEGY_PAIRS` in `audit_trail/quality_gates.py`. CRYPTO pair stays blocked.

Paper pilot: `verified_strategies/paper_pilot/equity_bb_pilot.py` (day_count=15; 0 BB signals today — no oversold names).

### 3. Three daily paper pilots in eagle_suite cron

`tools/run_verified_pilots_daily.py` runs daily:
- `equity_bb_pilot.py --one-shot`
- `equity_pead_drift_pilot.py --one-shot` (PEAD_DRIFT_MAX_DAYS=30 → XYZ + NVDA drift)
- `forex_carry_g10_pilot.py --one-shot --write-db`

### 4. FOREX carry pilot `--write-db` fix

**Broken:** `_write_basket_to_db` was defined *after* `if __name__ == "__main__"`, so `--write-db` never ran (NameError / unreachable code). `result["basket"]` key also missing.

**Fixed:** `verified_strategies/paper_pilot/forex_carry_g10_pilot.py` — moved `main()` to file end; return `legs` in result; `--write-db` writes 6 basket legs to `trading_picks`.

**Verified:** `[DB] Inserted/updated 6 pick(s)` on 2026-06-05 run.

### 5. Live deploy

```bash
PF_REGISTRY_INCLUDE_OUTCOMES=1 python3 tools/build_pf_registry.py
PYTHONPATH=. python3 tools/money_ready_snapshot.py
python3 tools/deploy_audit_files.py --only audit_data
```

Live: https://findtorontoevents.ca/audit/data/money_ready_verdict.json

---

## Current Verdict Snapshot (2026-06-05)

| Class | Verdict | Best sleeve | n | PF | Tradeable? |
|-------|---------|-------------|---:|---:|------------|
| CRYPTO | NOT_READY | `battleground_ml_relaxed_mut` | 31 | 4.07 | Micro 0.25× only |
| EQUITY | NOT_READY | `MeanReversionBB` | 175 | 1.73 | Paper pilot + resolver grade |
| FOREX | INSUFFICIENT_DATA | `forex_carry_g10` (backtest) | 197 mo | 1.59 | Paper; 0/30 forward closes |
| ETF | — | `etf_verified_dual_momentum` | 0 fwd | 2.75 OOS | Paper only |
| COMMODITY | FAIL | — | — | — | Hold |
| BOND | — | `bond_tlt_ief_v3` | — | 1.29 bt | Scanner wired |

**Headline:** 0/6 classes MONEY_READY (correct gate behavior).

---

## Tradeable This Week (0.25× micro only)

- **CRYPTO:** `battleground_ml_relaxed_mut` + `crypto_liquidity_wick_reversal_v1`
- **EQUITY:** `MeanReversionBB` (paper) + PEAD drift (XYZ/NVDA)
- **FOREX:** `forex_carry_g10` paper basket (6 legs in DB); await 30 monthly closes
- **Everything else:** paper/backtest only, 0% live sizing

---

## Monitoring Flags

| Flag | Status |
|------|--------|
| CRYPTO 48h resolver | **0 closed / 137 active** — hold class-wide size-up |
| FOREX pilot forward | **0/30 monthly closes** (day_count=18, first close at July rebalance) |
| mega_mutation | HOLD unblock until ~2026-06-12 |
| `yahoo_analyst_consensus` | PERMANENTLY_KILLED — do not re-enable |
| `hs_lb_None` in CRYPTO top_sleeves | Investigate — should be blocked artifact |

---

## Remaining (P1/P2)

- [ ] FOREX: accumulate 30 forward monthly closes on `forex_carry_g10` → operator review for T2
- [ ] EQUITY BB pilot: log first 10 forward closes in `equity_bb_paper_log.jsonl`
- [ ] CRYPTO: monitor 48h panel until resolver unstuck
- [ ] mega_mutation recheck ~2026-06-12
- [ ] Do not size CRYPTO class-wide (policy_clean PF≈0.99)

---

## Reproduce Commands

```bash
python3 verified_strategies/paper_pilot/equity_bb_pilot.py --one-shot
PEAD_DRIFT_MAX_DAYS=30 python3 verified_strategies/paper_pilot/equity_pead_drift_pilot.py --one-shot
python3 verified_strategies/paper_pilot/forex_carry_g10_pilot.py --one-shot --write-db
PF_REGISTRY_INCLUDE_OUTCOMES=1 python3 tools/build_pf_registry.py
PYTHONPATH=. python3 tools/money_ready_snapshot.py
python3 tools/deploy_audit_files.py --only audit_data
python3 tools/run_verified_pilots_daily.py
python3 tools/strategy_tier_tracker.py --min-n 15
```

---

## Related Docs

- `updates/2026-06-06-pf-registry-outcomes-dedup-fix.md` — dedup bug detail
- `updates/2026-06-06-p1-forex-pilot-pf-registry-wrap.md` — pilot cron + outcomes gate
- `updates/2026-06-06-next-steps-execution-wrap.md` — prior session wrap
- `reports/edge_hunt_ALL_CLASSES_v2_2026-06-06.md` — master synthesis
- `reports/forex_carry_backtest_extended_20260606.json` — FOREX backtest n=197
