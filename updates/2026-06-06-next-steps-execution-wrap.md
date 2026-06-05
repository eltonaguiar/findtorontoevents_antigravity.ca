# Next Steps Execution Wrap — 2026-06-06

Continuation of edge-hunt P0/P1 actions from `updates/2026-06-06-edge-hunt-session-wrap.md`.

---

## Finished this pass

### Policy / gates
- **EQUITY `MeanReversionBB` unblocked** in `BLOCKED_ASSET_STRATEGY_PAIRS` (CRYPTO pair stays blocked)
- Live verdict now shows: `policy_blocked: false`, n=175, WR=54.9%, PF=1.82

### Code wire-ups
| File | Change |
|------|--------|
| `audit_trail/quality_gates.py` | Removed `("EQUITY", "MeanReversionBB")` block |
| `alpha_engine/bond_strategies.py` | Added `bond_tlt_ief_v3()` — 12-1m TLT/IEF/SHY momentum |
| `alpha_engine/bond_scanner.py` | Registered `bond_tlt_ief_v3` in STRATEGIES |
| `tools/feature_signals/orchestrator.py` | `COMMODITY_TERM_COT_ENABLED=1` (default) shadow lane |
| `alpha_engine/equity_pead_strategy.py` | Repo earnings cache + `PEAD_DRIFT_MAX_DAYS` env |

### Paper pilots (new)
| Pilot | Path | Status |
|-------|------|--------|
| MeanReversionBB | `verified_strategies/paper_pilot/equity_bb_pilot.py` | Running; 0 signals today (no BB oversold) |
| PEAD drift | `verified_strategies/paper_pilot/equity_pead_drift_pilot.py` | Running; signals when drift window active |

### Backtest acceleration
- **FOREX carry extended backtest** (2010–2026): **n=197, WR=60.4%, PF=1.59, UNLOCK_READY**
- Report: `reports/forex_carry_backtest_extended_20260606.json`
- Still blocked live by `FOREX_HARD_DISABLE=1` until 30d paper pilot

### Live deploy
- `money_ready_verdict.json` FTP-deployed via `tools/deploy_audit_files.py --only audit_data`
- EQUITY `top_sleeves`: MeanReversionBB (tradeable flag, resolver_grade)

---

## Tradeable @ 0.25× micro (updated)

| Class | Sleeve | n | WR | PF | Notes |
|-------|--------|---:|---:|---:|-------|
| CRYPTO | `battleground_ml_relaxed_mut` | 31 | 71% | 4.35 | Unblocked |
| CRYPTO | `crypto_liquidity_wick_reversal_v1` | 30 | 60% | 1.55 | Single-source |
| **EQUITY** | **`MeanReversionBB`** | **175** | **54.9%** | **1.82** | **Now unblocked + paper pilot** |

**0 classes MONEY_READY** (correct).

---

## Remaining action items

### P0 — This week
- [ ] Run `equity_bb_pilot.py --one-shot` daily; log first 10 closes
- [ ] Run `equity_pead_drift_pilot.py --one-shot` daily through July earnings
- [ ] CRYPTO 0.25× micro on battleground_ml_relaxed_mut + wick reversal only
- [ ] Monitor 48h resolver stall (CRYPTO 0 closed / 137 active)

### P1 — Next 2 weeks
- [ ] **FOREX:** Stand up `forex_carry_g10` 30d paper pilot (backtest UNLOCK_READY n=197)
- [ ] **FOREX:** Operator review before `FOREX_HARD_DISABLE=0`
- [ ] **BOND:** Confirm `bond_tlt_ief_v3` emits on next monthly momentum flip
- [ ] **COMMODITY:** Verify `commodity_term_cot` signals in feature_signals JSON after orchestrator refresh
- [ ] **pf_registry:** Merge `at_pick_outcomes` ingest (MeanReversionBB still absent from closed_picks.json)
- [ ] **mega_mutation:** Recheck ~2026-06-12 per swarm HOLD

### P2 — Hold / do not do yet
- [ ] Do not unban `stocks_rsi2_pullback` or `yahoo_analyst_consensus`
- [ ] Do not size CRYPTO class-wide (PF=0.99 policy_clean)
- [ ] Do not promote ml_enhanced family without per-variant SPA

---

## Reproduce

```bash
python3 verified_strategies/paper_pilot/equity_bb_pilot.py --one-shot
PEAD_DRIFT_MAX_DAYS=30 python3 verified_strategies/paper_pilot/equity_pead_drift_pilot.py --one-shot
python3 -m alpha_engine.bond_scanner
PYTHONPATH=. python3 tools/money_ready_snapshot.py
python3 tools/deploy_audit_files.py --only audit_data
```

**Live:** https://findtorontoevents.ca/audit/data/money_ready_verdict.json
