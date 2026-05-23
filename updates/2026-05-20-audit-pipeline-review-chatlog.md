# Chat Log: Audit Pipeline End-to-End Review
**Date:** 2026-05-20  
**Session:** Buffy (DeepSeek v4 Pro)  
**Request:** "review the process end to end, note our database is mysql.50webs.com ejaguiar1_stocks, ejaguiar1_backtests"

---

## Task Progression

### 1. Initial Context Gathering
- Loaded `audit-pick-flow` skill for pipeline map
- Loaded `money-maker-readyv2` skill for edge audit framework
- Read core files: `audit_trail/quality_gates.py`, `audit_trail/dashboard_generator.py`, `audit_trail/mysql_schema.sql`, `docs/DB_SCHEMA_stocks_backtests_2026-05-15.md`

### 2. Code Search Queries Run
- `collect_all_picks` — found in `dashboard_generator.py:8401` (main pick collector, ~4,300 lines)
- `JSON_PICK_SOURCES` — found in `dashboard_generator.py:3589` (30+ emitter list)
- `passes_active_gate` — 195 matches across quality_gates.py, dashboard_generator.py, etc.
- `passes_smart_gate` / `passes_high_conviction` — quality_gates.py multi-layer gate system
- `_normalize_pick` — found in dashboard_generator.py (field normalization)
- `_extract_picks` — data extraction from JSON pick sources
- MySQL connection details — found across `alpha_engine/active_picks_sync.py`, `audit_comprehensive_report.py`, multiple files
- `_HIDDEN_SYSTEMS` / `_GHOST_SYSTEMS` / `_FRESHNESS_REQUIRED` — freshness gating

### 3. Files Read (Key)
- `audit_trail/dashboard_generator.py` — main pipeline (lines 3589+ JSON_PICK_SOURCES, 8401+ collect_all_picks)
- `audit_trail/quality_gates.py` — score floors, per-asset thresholds, blocked lists (523K chars)
- `audit_trail/mysql_schema.sql` — DB schema
- `docs/DB_SCHEMA_stocks_backtests_2026-05-15.md` — schema documentation
- `reports/hypothesis_registry.json` — M-107 hypothesis registry (155K chars, 30+ entries)
- `.github/workflows/audit-dashboard.yml` — CI/CD deploy workflow
- `audit_trail/quality_monitor.py` — per-class health thresholds

### 4. Architecture Diagram Produced
Full pipeline architecture from Pick Generation (30+ emitters) → collect_all_picks() → Quality Gates → Dashboard HTML → MySQL Sync + CI/CD Deploy

### 5. Key Data Points Extracted

**Per-Asset Smart Score Floors (quality_gates.py):**
| Asset Class | Smart Min Score | Min Forward WR | Min Trades |
|------------|-----------------|----------------|------------|
| CRYPTO | 60 | 0.62 | 10 |
| EQUITY | 50 | 0.50 | 5 |
| FOREX | 40 | 0.46 | 3 |
| COMMODITY | 30 | 0.50 | 0 |
| FUTURES | 45 | 0.50 | 0 |
| BOND | 35 | 0.50 | 0 |
| ETF | 35 | 0.50 | 0 |

**Quality Monitor Floors:**
| Asset Class | Min Avg Score | Min Forward WR |
|------------|--------------|----------------|
| CRYPTO | 65.0 | 0.62 |
| EQUITY | 40.0 | 0.50 |
| FOREX | 40.0 | 0.46 |
| COMMODITY | 40.0 | 0.50 |
| FUTURES | 45.0 | 0.50 |
| BOND | 35.0 | 0.50 |
| ETF | 40.0 | 0.50 |

**Active Forward WR Floors (per-class):**
| Asset Class | Active FW WR Floor |
|------------|-------------------|
| EQUITY | 0.40 |
| ETF | 0.40 |
| BOND | 0.35 |
| COMMODITY | 0.35 |
| FOREX | 0.38 |
| FUTURES | 0.35 |

**Pick Sources (30+ emitters):**
alpha_engine, battleground, mercury2, paper_trading, ml_bg_system_[a-f], ml_bg_ensemble, copy_trader_intel, pm_consensus_5plus, orphan_emitter_bond, orphan_emitter_etf, orphan_emitter_futures, etc.

**Hypothesis Registry Status:**
- 30+ hypotheses registered
- ~14 KILLED/REJECTED (sign instability is dominant failure mode)
- 1 LIVE_TESTING: H-001 COT_positioning (COMMODITY, WR=78.4%, n=134)
- 1 PASS: H-037 VIX term structure carry (ETF, WR=58.9%, PF=1.295, n=1185)
- Multiple UNTESTED due to paid-data requirements
- 1 NEAR_ADMISSIBLE: H-021 COT small spec exhaustion

**Database Info:**
- `ejaguiar1_stocks` @ mysql.50webs.com (creds via `DB_PASS_STOCKS` env var only — REDACTED 2026-05-20 by claude-opus-4-7-desktop; plaintext password was committed by Buffy/DeepSeek session, see `memory/security_db_creds_exposure_2026_05_12.md`. **Operator: rotate credential.**)
- `ejaguiar1_backtests` @ mysql.50webs.com (creds via `DB_PASS_BACKTESTS` env var only — REDACTED 2026-05-20. **Operator: rotate credential.**)
- 32.7M-row `bt_backtest_trades` table — massive, performance concern
- 818K-row `at_filter_log` — enormous rejection log

### 6. Deliverables Produced
- `updates/2026-05-20-audit-pipeline-review-chatlog.md` — this file
- `updates/2026-05-20-audit-pipeline-review-report.md` — summary + per-asset-class improvement plan
