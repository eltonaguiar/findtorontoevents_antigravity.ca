# Money-Ready Blitz — 2026-06-05

## What Was Done

### 1. Feature Signal Emitters Enabled (5 asset classes → production)
Flipped `production_enable=False` → `True` across all 5 persona-factor emitters:

| Emitter | File | Asset Class | Pairs/Symbols | Signal Model |
|---------|------|-------------|---------------|--------------|
| Equity Momentum+Quality | `tools/feature_signals/equity_momentum_quality.py` | EQUITY | 40 US equities+ETFs | Jegadeesh-Titman 12-1 + Asness QMJ composite |
| Forex Carry+Momentum | `tools/feature_signals/forex_carry_momentum.py` | FOREX | 8 FX pairs | Lustig-Roussanov-Verdelhan carry + AMP 12-1 |
| Bond Duration Momentum | `tools/feature_signals/bond_duration_momentum.py` | BOND | 8 bond ETFs (TLT, IEF, SHY, TIP, LQD, HYG, AGG, BIL) | Ilmanen duration premium + AMP 12-1 |
| Commodity Term+COT | `tools/feature_signals/commodity_term_cot.py` | COMMODITY | 8 contracts (CL, NG, HG, GC, SI, ZW, ZS, ZC) | Erb-Harvey term structure + Sanders COT contrarian |
| ETF Sector Rotation | `tools/feature_signals/etf_sector_rotation.py` | ETF | 14 sector ETFs | Faber 2007 absolute + Antonacci 2014 relative momentum |

All gated behind `FACTOR_EMITTERS_ENABLED=1` env var. Next hourly cron on `feature-signals-hourly.yml` will emit new picks into `alpha_engine/data/active_picks.json`.

### 2. Mega-Mutation Unblock Analysis
Swarm verdict 4/4: **HOLD until June 12-16**. Key reasons:
- 95% of closed_at were NULL — PF=3.16 not verified on organic-timestamp trades
- Only 48h clean sign-coherence window (need 7-10 trading days)
- Last-10 WR=20% cluster not root-caused

### 3. DB Backup & Sync
- `trading_picks` (46,035 rows) → `ejaguiar1_backups`
- `at_pick_outcomes` (39,418 rows) → `ejaguiar1_backups`
- 423 missing resolved trading_picks synced into `at_pick_outcomes`
- bt_backtest_trades cross-DB sync **running** (GHA run 27019279488)

### 4. T1 Badge Warning Icons
Live on `/audit/ai-tournament.html` — every T1 badge now shows ⚠️ tooltip explaining single-snapshot resolver inflation.

### 5. Recency Gate
Wired into `money_ready_verdict.py` (shadow mode). Stamps `recency_ok`, `recency_days_since_last`, `_recency_warn` per class. Ready to enforce after observation.

### 6. GHA Infrastructure
- bt-backtest-trades-sync.yml activated (from .draft)
- Auto-shutdown-monitor: transient DB connectivity failure (not a config bug)
- Mirror workflow: timeout on FTP download; fix committed (exclude .git/vendor/next)

## Remaining Action Items

### P0 — Do First After bt Sync Completes
- [ ] Trigger pf_registry recompute: `python3 tools/build_pf_registry.py` (unblocked once bt sync finishes)
- [ ] Verify new picks hit `/audit` from the 5 enabled emitters

### P1 — This Week
- [ ] Mega-mutation: re-evaluate June 12-16 (sign coherence + live signal check)
- [ ] Flip recency gate from shadow → enforce (after observing clean shadow output for 48h)
- [ ] Feed-health-check: fix `ueps` bad numeric fields (or add `THRESHOLD_FREEZE` bypass)

### P2 — Next Sprint
- [ ] Analyst calls: debug why `analyst_active_calls.json` shows 0 active calls
- [ ] Equity PEAD wiring: connect `equity_pead_momentum.py` research output to production pipeline
- [ ] Add bond futures (ZB, ZN, ZF, ZT) to commodity_term_cot.py universe
- [ ] Remove `FOREX_ZERO_ALLOCATE` filter in `mysql_trading_sync.py` (blocks FOREX picks)

### P3 — Ongoing
- [ ] n-ramp: build equity n from 47 → 100+ (requires new data sources flowing)
- [ ] Cross-DB sync schedule: once dry-run verified, flip to dry_run=false on weekly cron
- [ ] Deep dives for EQUITY, FOREX classes (when n sufficient for statistical validity)
- [ ] Mega-mutation unblock: re-swarm June 12

## Key Decisions

| Decision | Status | Rationale |
|----------|--------|-----------|
| Production-enable factor emitters | **DONE** | Swarm review complete, 5/5 pass, all behind env var |
| Mega-mutation unblock | **HOLD** | 4/4 swarm models: wait 7-10 days |
| bt_backtest sync | **RUNNING** | 4M-row gap, enable weekly cron after dry-run verified |
| Recency gate enforce | **SHADOW** | Wait 48h of clean output before flipping |
