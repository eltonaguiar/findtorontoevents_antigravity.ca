# EAGLE Remaining Items — Post Quick-Wins Backlog
**Model/Provider**: Cursor Composer  
**Date/Time**: 2026-05-27T02:25:00 EST  
**Parent**: `reports/EAGLE-2026-05-27T02-25-00_EST-cursor-composer-strategy-audit.md`

---

## P0 — Critical (Block Real Money)

### R-P0-01: Restart forward_validator
- **Symptom**: Frozen 270h+; 29M open positions; 0 CRYPTO closes in 48h
- **Fix**: EXPIRED-stamp stale backlog → batch restart `VALIDATOR_BATCH_SIZE=500`
- **Effort**: M (4–8h + monitoring)

### R-P0-02: WON/LOSS mislabel (2,531 rows)
- **Symptom**: `outcome_status=WON` but `pnl_pct<0`, avg −41%
- **Fix**: SQL relabel + outcome_resolver threshold audit
- **Effort**: S (1–2h)

### R-P0-03: PnL integrity re-resolve (39% mismatch)
- **Symptom**: `db_health.json` 10,501/26,945 sampled rows >1% drift
- **Fix**: `re_resolve_historical_v2.py` + republish `asset_class_health`
- **Effort**: L (1–2 days)

### R-P0-04: Ghost row dedup (56k+ duplicates)
- **Symptom**: MATICUSDT 20,474 dup rows
- **Fix**: UNIQUE(symbol, source_system, signal_timestamp) + migration
- **Effort**: M (4–8h)

### R-P0-05: trust_score backfill (99.99% NULL)
- **Symptom**: HC overlay unreproducible
- **Fix**: Backfill from `calculate_trust_score()` formula
- **Effort**: M (4–8h)

### R-P0-06: ML confidence retrain (long-term)
- **Symptom**: conf≥0.9 → 14% WR system-wide
- **Fix**: TimeSeriesSplit retrain; enable `CONFIDENCE_CALIBRATION_ENABLED=1` after resolver clean
- **Effort**: L (2–3 days)
- **Prereq**: R-P0-01, R-P0-03

---

## P1 — High Priority Edge

### R-P1-01: COMMODITY post-PR-#994 re-derive
- Re-aggregate COT picks; exclude over-emission; verify n≥20 PF≥1.5 before Tier claim
- Ref: `reports/asset_class_90day_plan_COMMODITY_2026-05-15.md`

### R-P1-02: Merge equity VIX regime sidecar
- Branch: `feat/equity-vix-regime-gate-sidecar-2026-05-13`
- Backtest: PF 5.37 / WR 75% VIX<20

### R-P1-03: pead_equity promotion (after 2026-06-14)
- WF-verified 62.2% OOS WR; currently `PEAD_EQUITY_ENABLED=0` shadow only

### R-P1-04: signal_outcomes refresh (82d stale)
- Nightly GHA schedule + identify writer chain

### R-P1-05: active_picks_sync module
- Closes INC-15; unblocks forward WR verification

### R-P1-06: Bonferroni on live promotion gate
- Wire `bonferroni_pass` from `top_edges.py` into `passes_smart_gate`
- Ref: incidents BACKLOG item from agent B

### R-P1-07: FRED_API_KEY for carry rates
- Enables live FOREX carry + BOND economic context (M-032)

---

## P2 — Medium Effort

### R-P2-01: Hot streak probation tier (not gate bypass)
- Table: `strategy_hot_streak` rolling 14d WR/PF
- Relax only `min_confidence` −0.05 when streak criteria met
- Never relax: RR, concentration, BLOCKED lists

### R-P2-02: Range oscillator gate module
- USDJPY BoJ ceiling, GC COT extreme, BTC funding mean-revert
- Opt-in sidecar per Wire-Up Rule

### R-P2-03: IPO scanner MVP
- EDGAR S-1 + lockup expiry + revenue filter
- 3h build; paper 30d before UI claims

### R-P2-04: FUTURES tile deprecation
- Reclassify =F symbols; remove misleading n=0 tile

### R-P2-05: audit_roadmap_items DB + seed script
- Schema in strategy-audit MD; migrate incidents JSON

### R-P2-06: IDEA-H Polymarket macro overlay extension
- Already 8,700 LOC wired; extend to equity/macro (560 LOC est.)

### R-P2-07: UEPS equity screener live writer
- Verify `_run_equity_scanner()` in production_scanner main loop

### R-P2-08: Swarm picks revival (13d stale)
- Debug GH workflow; restore ensemble emissions

---

## P3 — Research / 90-Day Plan Backlog

From `90day_gap_analysis_2026-05-15.md` still PENDING:

| M-# | Item | Class |
|---|---|---|
| M-001 | BTC UTC hour death-zone filter | CRYPTO |
| M-004 | CRYPTO drag autopsy + auto-quarantine | CRYPTO |
| M-008 | COT MATCH + DSR≥0.85 in active_gate | COMMODITY |
| M-009 | PEAD standalone strategy | EQUITY |
| M-020 | Walk-forward validator BOND output | BOND |
| M-021 | COT lag-corrected re-run | COMMODITY |
| M-022 | commodity_carry_momo sidecar | COMMODITY |
| M-023 | ETF dual momentum | ETF |
| M-024 | BOND TSMOM sidecar | BOND |
| M-025 | Overnight intraday reversal | EQUITY |
| M-026 | DOW tilt Tue/Wed bias | EQUITY |
| M-032 | FRED_API_KEY wire-up | BOND/FOREX |
| M-034 | Confidence inversion validation | CRYPTO |
| M-038 | MEMECOIN quarantine active_gate | CRYPTO |
| M-039 | Cross-commodity spread research | COMMODITY |
| M-007 | FOREX_HARD_DISABLE env | FOREX |

---

## Acceptance Criteria (Stage-Gate)

No class gets sizing increase until ALL of:
1. P0 data integrity items R-P0-01 through R-P0-03 closed
2. Class PF>1.3, WR>48%, n≥100 clean (post-noise-filter)
3. 14d recency panel non-degraded vs 90d
4. Bonferroni-pass on promoted filter cells
5. Concentration gate enforced (symbol ≤30% class PnL)

---

## Roadmap DB Next Steps

1. Run SQL DDL (`audit_roadmap_items` + links table) on `ejaguiar1_stocks`
2. Build `tools/audit_roadmap_seed.py` — ingest incidents JSON + EAGLE PR IDs
3. Add hourly sync in `audit-dashboard.yml` → merge into `incidents_enhancements_feed.json`
4. Update `incidents.html` to show `depends_on` chain + M-# column

---

*Cursor Composer — EAGLE remaining items 2026-05-27 EST*
