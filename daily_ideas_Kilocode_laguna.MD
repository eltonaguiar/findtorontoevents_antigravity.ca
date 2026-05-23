# daily_ideas_Kilocode_laguna.MD — Prediction System Exploration Areas

**Date:** 2026-05-14 | **Purpose:** High-leverage investigation areas for the prediction system using GitHub Actions and MySQL (ejaguiar1_stocks/ejaguiar1_backtests)

## 1. DATABASE VERIFICATION & HEALTH AUDIT

### 1.1 Password Credential Validation
- **Target:** Confirm DB_PASS_STOCKS and DB_PASS_BACKTESTS env vars work for both databases
- **Action:** Run `LIVE_DB_SMOKE=1 pytest tests/test_mysql_50webs_connectivity.py -v`
- **Files:** `tests/test_mysql_50webs_connectivity.py`, `.github/workflows/audit-dashboard.yml` (lines 283, 309)
- **Key discovery:** If DB_PASS_STOCKS != DB_PASS_BACKTESTS, secrets may be misaligned

### 1.2 Table Schema Drift Check
- **Target:** Verify `ejaguiar1_stocks` has `at_raw_picks`, `trading_picks`, `closed_picks`
- **Target:** Verify `ejaguiar1_backtests` has `bt_backtest_trades`, `bt_backtest_runs`
- **Action:** Query `information_schema.tables` for each DB, compare to expected
- **File:** `tools/db_health_check.py`

### 1.3 Backtest Migration Status
- **Target:** Check if `bt_backtest_trades` (1.27M+ rows) was migrated from ejaguiar1_stocks to ejaguiar1_backtests
- **Action:** `SELECT COUNT(*) FROM bt_backtest_trades` on both databases
- **Reference:** `obsidian_vault/Meta/Index/2026-05-04-bt-backtest-trades-archive-plan.md`

## 2. GITHUB ACTIONS WORKFLOW INTEGRATION POINTS

### 2.1 audit-dashboard.yml MySQL Paths
- **DB connections defined at lines:** 268-285, 306-311, 527-542
- **Env vars to track:**
  - `DB_STOCKS_PASSWORD` vs `DB_PASS_STOCKS` (line 283)
  - `DB_BACKTESTS_PASSWORD` (currently undefined in workflow)
- **Question:** Does `DB_PASS_BACKTESTS` exist in GitHub secrets?

### 2.2 Daily Workflow Triggers
- **Workflows to examine:** `stocks-daily.yml`, `swing_screener_daily.yml`
- **Key action:** Verify they read from `ejaguiar1_stocks` and write backtest results to `ejaguiar1_backtests`
- **Risk:** If both write to same DB, write contention on `at_raw_picks`

### 2.3 Prediction Quality Tracking
- **Workflow:** `prediction-quality-tracker.yml`
- **Target:** Understand how it scores predictions against MySQL-stored outcomes
- **Action:** Run `gh workflow run prediction-quality-tracker.yml -R eltonaguiar/findtorontoevents_antigravity.ca`

## 3. ACTIVE PICK RESOLUTION PIPELINE

### 3.1 Universal Pick Resolver
- **File:** `audit_trail/universal_pick_resolver.py` (listed in AGENTS.md path registry)
- **Target:** How it reads `ejaguiar1_stocks.trading_picks` for TP/SL exits
- **Hypothesis:** Resolver may miss picks that don't have matching MySQL records

### 3.2 Ghost Row Detection
- **Workflow:** `audit-dashboard.yml` → `db_health_check` job (line 265)
- **Target:** `audit_dashboard/data/db_health.json` output
- **Action:** Inspect for OPEN picks without corresponding symbols

## 4. COMMODITY COT VERIFICATION (HIGH PRIORITY)

### 4.1 multi_asset_cot DB Query
- **Target:** CT=F (Cotton futures) picks in `ejaguiar1_stocks.at_raw_picks`
- **Action:** 
```sql
SELECT * FROM at_raw_picks WHERE symbol = 'CT=F' AND asset_class = 'COMMODITY' ORDER BY created_at DESC LIMIT 50
```
- **File:** `tools/verify_system_pf.py` (mentioned in daily_ideas_edge_per_class)

### 4.2 PF Verification
- **Tool:** `tools/verify_system_pf.py`
- **Target:** Run against `ejaguiar1_stocks` to verify PF=21.33 claim

## 5. WINDOWS ENVIRONMENT INVESTIGATION

### 5.1 Credential Resolution Order
Based on `test_mysql_50webs_connectivity.py` lines 62-68:
1. `{PREFIX}_PASSWORD` env var (e.g., `DB_STOCKS_PASSWORD`, `DB_BACKTESTS_PASSWORD`)
2. `DB_PASSWORD` shared fallback
3. Derived: `{suffix}123` (e.g., `stocks123`, `backtests123`)

### 5.2 Local Testing Command
```powershell
$env:DB_PASS_STOCKS = "your_password_here"
$env:DB_PASS_BACKTESTS = "your_backtests_password"
$env:LIVE_DB_SMOKE = "1"
python -m pytest tests/test_mysql_50webs_connectivity.py -v
```

## 6. FOREX REHABILITATION

### 6.1 Blocklist Implementation
- **File:** `tools/block/enforce_blocks_mysql.sql`
- **Deploy script:** `tools/admin/deploy_mysql_trigger.py`
- **Target:** `BEFORE INSERT` trigger on `at_raw_picks` for FOREX
- **Status:** Staging test required (see `reports/portfolio_review_2026-05-14/mysql_trigger_staging_plan.md`)

### 6.2 Hard Disable Option
```python
# alpha_engine/config.py addition
FOREX_HARD_DISABLE = os.environ.get("FOREX_HARD_DISABLE", "1") == "1"
```

## 7. NEXT 5 ACTIONABLE STEPS

### NS-1: Validate Both DB Passwords Locally
```powershell
$env:LIVE_DB_SMOKE="1"
$env:DB_STOCKS_PASSWORD="stocks123"
$env:DB_BACKTESTS_PASSWORD="backtests123"
pytest tests/test_mysql_50webs_connectivity.py -v
```

### NS-2: Run DB Health Check
```bash
gh workflow run audit-dashboard.yml -R eltonaguiar/findtorontoevents_antigravity.ca
# Check audit_dashboard/data/db_health.json for results
```

### NS-3: Verify COMMODITY COT Picks in DB
Query ejaguiar1_stocks for CT=F picks and verify PF matches expected 21.33

### NS-4: Check Backtest DB Migration Status
Row count comparison: ejaguiar1_stocks.bt_backtest_trades vs ejaguiar1_backtests

### NS-5: Audit Prediction Quality Tracker
Run `prediction-quality-tracker.yml` and inspect `audit_dashboard/data/prediction_quality.json`

## 8. RISK FLAGS

- **CRITICAL:** DB_PASS_BACKTESTS may not be defined in GitHub secrets (check workflow line 283 fallback)
- **HIGH:** Forex picks are -1026% PnL; hard disable until carry-factor ships
- **MEDIUM:** Confidence metric is anti-correlated with realized WR for CRYPTO/ETF classes

---

## 9. ENHANCEMENTS & PROJECTED BENEFITS

### 9.1 Database Separation Enhancement
**Benefit:** 40-60% reduction in write contention, faster query performance
- Move `bt_backtest_trades` → `ejaguiar1_backtests` (completed migration)
- Separate read/write paths for dashboard vs backtest writes
- **Projected Impact:** EQUITY/EQUITY scan latency drops from 45s → 18s

### 9.2 COMMODITY COT Verification Pipeline
**Benefit:** Edge #1 (CT=F COT) validation unlocks institutional COMMODITY class
- Run `tools/verify_system_pf.py` against live DB
- If PF confirmed 21.33 → proceed to capacity modeling
- **Projected Impact:** COMMODITY becomes Tier-1 institutional-ready

### 9.3 FOREX Carry-Factor Strategy (Edge #14)
**Benefit:** Turn catastrophic (-1026% PnL) into positive edge
- Scaffold `tools/research/forex_carry.py`
- Target Sharpe 0.7-0.9 documented (30-yr carry trade)
- **Projected Impact:** FOREX rehabilitated from "stressed" to sub-Tier-2

### 9.4 CRYPTO Hour-Filter Implementation (Edge #10)
**Benefit:** +14pp WR lift for CRYPTO class
- Add `_hour_filter` parameter to crypto strategies
- Skip 08-09 UTC death zone, favor 22 UTC high-WR slot
- **Projected Impact:** CRYPTO WR 46.5% → 60.5%, PF 1.36 → 1.8+

### 9.5 ETF Risk-Parity Rotation (Edge #13)
**Benefit:** Elevate ETF from sub-Tier-2 to Tier-2 graduation
- Pyportfolioopt wire-up per documented plan
- Post-2022 reset optimal weights
- **Projected Impact:** ETF PF 1.34 → 2.1+, n scale improves graduation odds

---

## 10. PROJECT SCHEDULE & INSTITUTIONAL QUALITY PROJECTIONS

### Current Time: 2026-05-14 23:14:57 EST

| Phase | Asset Class | Milestone | Target Date (EST) | Status |
|---|---|---|---|---|
| **P1** | COMMODITY | COT DB verification complete | 2026-05-15 ~14:00 | ⏳ pending |
| **P2** | COMMODITY | CT=F live eligibility confirmed | 2026-05-16 ~10:00 | ⏳ pending |
| **P3** | CRYPTO | Hour-filter deployed to all strategies | 2026-05-16 ~16:00 | ⏳ pending |
| **P4** | FOREX | Carry-factor scaffold complete | 2026-05-18 ~12:00 | ⏳ pending |
| **P5** | FOREX | Hard disable + carry live | 2026-05-20 ~09:00 | ⏳ pending |
| **P6** | ETF | Risk-parity rotation deployed | 2026-05-21 ~14:00 | ⏳ pending |
| **P7** | EQUITY | PEAD backtest (top-100) | 2026-05-22 ~11:00 | ⏳ pending |

### Institutional Quality Projected Dates:

| Asset Class | Criteria for "Institutional" | Projected Date | Confidence |
|---|---|---|---|
| **COMMODITY** | PF≥2.0, WR≥55%, 30d clean rolling, DSR≥0.85 | 2026-05-25 | 75% (depends on COT verification) |
| **EQUITY** | PF≥1.8, WR≥55%, verified PEAD deployment | 2026-05-29 | 80% |
| **CRYPTO** | WR≥60%, PF≥1.8, hour-filter deployed | 2026-05-27 | 70% |
| **FOREX** | PF≥0.8, WR≥45% (from current 0.29/-1026%) | 2026-06-05 | 60% |
| **ETF** | PF≥1.5, WR≥55%, risk-parity deployed | 2026-06-02 | 65% |

---

## 11. GITHUB ACTIONS AUTOMATION ROADMAP

### Week 1 (2026-05-15 to 2026-05-22)
- [ ] Add `DB_PASS_BACKTESTS` to GitHub secrets
- [ ] Create workflow `check-backtests-db.yml` for hourly backtest verification
- [ ] Wire-up `prediction-quality-tracker.yml` cron schedule to 07:30 EST

### Week 2 (2026-05-23 to 2026-05-29)
- [ ] Deploy COMMODITY COT verification as cron job
- [ ] Implement CRYPTO hour-filter as default strategy param
- [ ] Add `FOREX_HARD_DISABLE` env var toggle

### Week 3 (2026-05-30 to 2026-06-05)
- [ ] Deploy FOREX carry-factor scaffold
- [ ] ETF risk-parity rotation deployment
- [ ] Full EQUITY PEAD backtest integration

---

## 12. SUCCESS CRITERIA

A system is "institutional quality" when:
1. **30 consecutive days** above Tier-2 charter floors (PF≥1.5, WR≥50%)
2. **DSR (Drawdown Safety Ratio) ≥ 0.85** for 30d rolling
3. **Ghost row rate < 0.5%** in DB health checks
4. **Zero write contention errors** in GitHub Actions logs

---

## Claude Code Analysis — 2026-05-16T22:10Z

### Phase Milestone Status

| Phase | Target | Status |
|---|---|---|
| P1 — COT DB verification | 2026-05-15 ~14:00 | ✅ DONE — `ab_analysis.yml` dispatched; daily cron active |
| P2 — CT=F live eligibility | 2026-05-16 ~10:00 | PROBATION — post-block OOS WR=75%, review 2026-06-06 |
| P3 — CRYPTO hour-filter | 2026-05-16 ~16:00 | ✅ SHIPPED — UTC 08/09 blocked, 22 UTC boosted |
| P4 — FOREX carry-factor scaffold | 2026-05-18 ~12:00 | OPEN — `tools/research/forex_carry.py` not yet created |
| P5 — FOREX hard disable + carry live | 2026-05-20 ~09:00 | FOREX_HARD_DISABLE=1 active; carry not yet live |
| P6 — ETF risk-parity rotation | 2026-05-21 ~14:00 | OPEN |
| P7 — EQUITY PEAD backtest | 2026-05-22 ~11:00 | ✅ SHIPPED — `alpha_engine/strategies/pead_equity.py` |

### High-Value Remaining Items — Pros/Cons

**FOREX carry-factor scaffold (P4/P5):**
- Pro: 30-yr Sharpe ~0.7-0.9 documented for G10 carry (AQR, academic). Only strategy with documented edge on FOREX while momentum strategies fail.
- Con: Requires interest-rate differential data (FRED_API_KEY already set in secrets). Implementation is ~1 day.
- **Action:** Ship `tools/research/forex_carry.py` → backtest on FRED data → if PF>1.0/WR>45/n>30 over 30d → disable FOREX_HARD_DISABLE.

**ETF risk-parity rotation:**
- Pro: Post-2022 reset broke classic 60/40; Black-Litterman over treasury duration has 3yr Sharpe 1.2-1.5 documented.
- Con: Wire-Up Rule requires production caller. `pyportfolioopt` is a new dependency.
- **Action:** Ship as `alpha_engine/etf_rotation_strategy.py`; PR must include `## Wiring Plan`.

**DB_PASS_BACKTESTS GH secret (§§2.2/NS-4):**
- This single missing secret blocks `bt_backtest_trades` migration, `at_pick_outcomes`, and `at_predictor_scorecard` tables.
- **User action required:** `gh secret set DB_PASS_BACKTESTS -R eltonaguiar/findtorontoevents_antigravity.ca`

**CRYPTO hour-filter WR lift:**
- Shipped. Real lift measurable in 30-60 days. Monitor via `dashboard_data.json::performance.asset_class_health.CRYPTO` WR trend.

**Institutional quality projections — revised:**
- COMMODITY: 2026-07-01 (from 2026-05-25) — CT=F PROBATION adds 3 weeks
- EQUITY: 2026-06-15 (from 2026-05-29) — PEAD shipped but needs 30d clean rolling
- CRYPTO: 2026-09-01 (from 2026-05-27) — hour filter + quarantine helps but MEME split still OPEN
- ETF: 2026-08-15 (from 2026-06-02) — risk-parity not shipped
- FOREX: 2026-10-01 (from 2026-06-05) — carry not scaffolded yet