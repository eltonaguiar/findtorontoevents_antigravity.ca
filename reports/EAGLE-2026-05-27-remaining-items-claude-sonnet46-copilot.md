# EAGLE Remaining Items — Strategy Review 2026-05-27
**Model**: Claude Sonnet 4.6 (GitHub Copilot)  
**Date/Time**: 2026-05-27 EST  
**Purpose**: Items NOT in the quick-wins PR list — medium/large effort, research, or blocked items  

---

## P0 OPEN — Critical Pipeline Failures (Must Fix Before Any Sizing)

### REMAINING-P0-01: Restart forward_validator (CRITICAL)
**What**: `alpha_engine/forward_validator.py` frozen 270h+ (11+ days). 29.2M open positions backlogged. No picks have been closed in 11+ days.  
**Impact**: ALL asset class forward WR claims are unverifiable. Dashboard shows live-looking numbers but they're stale. EQUITY "57% WR" could be 20% — nobody knows.  
**Fix**: 
1. Set `EXPIRED` status on all picks older than `max_hold_days * 1.5` without close signal
2. Restart validator with rate-limited batch mode: `VALIDATOR_BATCH_SIZE=500`, `VALIDATOR_DELAY_S=0.5`
3. Add circuit breaker: if `(open_picks / closed_picks_24h) > 1000` → alert + auto-suspend new picks
**Owner**: DevOps + alpha_engine team  
**Effort**: M (4-8 hrs + monitoring)  

### REMAINING-P0-02: Fix `WON` Rows with Negative PnL (2,531 rows)
**What**: 2,531 rows have `outcome_status = WON` but `pnl_pct < 0`. Average PnL of WON rows = **-41.1%**. This is a mislabeling bug — outcome resolver marks `WON` based on a signal condition, not on actual profit.  
**Fix**:
```sql
-- Audit scope
SELECT COUNT(*), AVG(pnl_pct) FROM trading_picks WHERE outcome_status = 'WON' AND pnl_pct < 0;

-- Fix: re-label as LOSS where pnl_pct < 0 and outcome_status = WON
UPDATE trading_picks 
SET outcome_status = 'LOSS', updated_at = NOW() 
WHERE outcome_status = 'WON' AND pnl_pct < 0;
```
**Effort**: S (1-2 hrs, SQL + validation)  

### REMAINING-P0-03: Dedup 56,559 Ghost Rows (MATICUSDT 20,474 alone)
**What**: Identical rows emitted repeatedly for same symbol/strategy/timestamp. MATICUSDT has 20,474 duplicate rows. meta_strategy has 1.6M template rows.  
**Fix**:
1. Add unique constraint: `UNIQUE KEY uq_pick_signal (symbol, source_system, signal_timestamp)`
2. Run dedup migration: keep `MIN(id)` per group, delete rest
3. Add dedup check to emission pipeline before INSERT
**Effort**: M (DB migration + scanner fix, 4-8 hrs)  

### REMAINING-P0-04: Backfill `trust_score` on Closed Picks (99.99% NULL)
**What**: `trust_score` column is NULL on 99.99% of closed picks. High-Conviction overlay is therefore unreproducible — no way to audit which picks the HC system claims were "trustworthy".  
**Fix**: Backfill via `UPDATE trading_picks SET trust_score = <formula_output> WHERE trust_score IS NULL AND outcome_status IN ('WON','LOSS','EXPIRED')`. Formula should mirror `calculate_trust_score()` from `alpha_engine/trust_scorer.py`.  
**Effort**: M (backfill SQL + validation + regression test, 4-8 hrs)  

### REMAINING-P0-05: Fix ML Confidence Inversion System-Wide
**What**: `conf≥0.9 → WR 14.4%`. The ML pipeline inverts alpha — high confidence = bad pick. This is likely a training-data leakage or label-encoding issue in the upstream ML model.  
**Fix (short-term)**: Invert confidence contribution (see QW-01). Fix (long-term): Retrain classifier with proper time-series cross-validation (TimeSeriesSplit, no look-ahead), verify on OOS set.  
**Effort**: L (2-3 days for retraining + validation framework)  
**Prereq**: `signal_outcomes` table needs to be refreshed first (82 days stale)  

---

## P1 OPEN — High Priority, Medium Effort

### REMAINING-P1-01: Rebuild US Equity Screener (UEPS)
**What**: UEPS composite (US Equity Pick System) is documented but has no live writer. Zero EQUITY picks from dedicated equity screener in production.  
**Tasks**:
1. Verify if `production_scanner.py` has `_run_equity_scanner()` or equivalent in main loop
2. If missing, add equity routing: `equity_picks = run_equity_strategies(symbols=EQUITY_SYMBOLS_PRODUCTION)`
3. Wire into main pick flush with `category='EQUITY'`
**Effort**: M (2-4 hrs to verify + wire)  

### REMAINING-P1-02: Refresh `signal_outcomes` Table (82 Days Stale)
**What**: `signal_outcomes` last updated 2026-03-04 (82 days ago). All forward WR claims from backtesting are unverifiable against live outcomes.  
**Tasks**:
1. Identify the writer for `signal_outcomes` (likely `alpha_engine/outcome_resolver.py` or `audit_trail/universal_pick_resolver.py`)
2. Trigger a full refresh pass
3. Add GH Actions schedule: `signal_outcomes_refresh.yml` nightly
**Effort**: M (identify writer + trigger + schedule, 4-6 hrs)  

### REMAINING-P1-03: Revive Swarm Picks (13+ Days Stale)
**What**: `data/swarm_picks.json` not updated in 13+ days. Swarm workflow no longer emitting picks. The ensemble approach (multiple model consensus) was one of the better pick sources.  
**Tasks**:
1. Check `.github/workflows/` for swarm workflow
2. Identify why emissions stopped (rate limit? authentication? logic gate?)
3. Re-enable or redesign with explicit `swarm_picks_writer.py`
**Effort**: M (debugging + re-enable, 2-6 hrs)  

### REMAINING-P1-04: COT Historical Re-Derive (Remove Over-Emission)
**What**: COT over-emission (same weekly CFTC release counted as ~100 trades) inflated COMMODITY headlines. The go-forward dedup ledger (PR #961) fixes new emissions, but historical data is still corrupted.  
**Tasks**:
1. Run `python tools/cot_retroactive_dedup.py` (or create if missing) 
2. Flag pre-dedup COT picks as `data_quality_flag = 'COT_OVEREMIT'`
3. Exclude flagged rows from PF/WR calculations in `asset_class_health`
**Effort**: M (SQL + retroactive script, 4-8 hrs)  

### REMAINING-P1-05: sync_active_mysql_picks_to_json Missing
**What**: Upstream writer for `closed_picks.json` doesn't exist in the codebase. The file is referenced by the dashboard but nobody writes to it from MySQL.  
**Tasks**: Create `tools/sync_closed_picks_json.py` that queries `trading_picks WHERE outcome_status != 'ACTIVE'` and writes to `audit_dashboard/data/closed_picks.json`.  
**Effort**: S-M (new script, 2-4 hrs)  

---

## P2 — Medium Effort Improvements

### REMAINING-P2-01: Hot Streak Exemption Mechanism
**What**: No mechanism exists to give elevated weighting or reduced gate scrutiny to strategies that are currently on a hot streak (e.g., 10 consecutive wins).  
**Proposed Design**:
```python
# In quality_gates.py, add:
HOT_STREAK_EXEMPTIONS = {
    # source_system -> streak threshold -> gate relaxation
    "mega_mutation": (8, "score_floor -5"),       # 8+ wins → lower score floor by 5
    "dna_winner_picks": (6, "score_floor -3"),
    "kimi_riseoftheclaw": (5, "score_floor -2"),
}
def get_hot_streak_adjustment(source_system: str, db_conn) -> int:
    """Return score floor adjustment for strategy on hot streak."""
    ...
```
**Effort**: M (DB query + gate logic, 4-8 hrs)  
**Prereq**: forward_validator must be unfrozen (REMAINING-P0-01)  

### REMAINING-P2-02: Wire `WIN_RATE_TRAP_BLACKLIST` (Dead Code)
**What**: `WIN_RATE_TRAP_BLACKLIST` exists in `quality_gates.py` but the note at line 1690 says it is NEVER CHECKED in `passes_active_gate`. It's dead code — either wire it in or remove it.  
**Fix**:
```python
# In passes_active_gate(), add check:
if (symbol, source_system) in WIN_RATE_TRAP_BLACKLIST:
    return False, "win_rate_trap_blacklist"
```
Or if intentionally disabled, add a comment explaining why and remove the list.  
**Effort**: S (30 min to wire, or M to audit which pairs belong on the list)  

### REMAINING-P2-03: Walk-Forward Validator for Live Strategies
**What**: Walk-forward validation exists in `alpha_engine/walkforward_validator.py` but isn't run as part of CI/CD pipeline for live strategy assessment.  
**Tasks**: Add `.github/workflows/walkforward-validation.yml` — weekly run, exports results to `reports/wf_validation_YYYY-MM-DD.json`, fails CI if key strategy PF<1.0 on OOS set.  
**Effort**: M (workflow YAML + integration, 4-6 hrs)  

### REMAINING-P2-04: Range-Bound Asset Detection
**What**: No systematic detection of assets oscillating between 2 price levels (identified above for USDJPY, GC=F, BTCUSDT, NG=F). The patterns exist but we have no algorithmic capture of them.  
**Proposed**: `alpha_engine/range_oscillator_detector.py`
- Detect: `(high_52w - low_52w) / avg_52w < 0.30` = range-bound flag
- Entry: price within 2% of 52w low → LONG; within 2% of 52w high → SHORT
- Exit: price reverts 50% of range
**Effort**: M (new module + wire-up, 4-8 hrs)  

### REMAINING-P2-05: FOREX Add DXY Regime Awareness
**What**: FOREX strategies fire without knowing DXY direction. When DXY is in strong trend, mean-reversion FOREX strategies fail. Need DXY ETF (UUP) or DXY index as regime filter.  
**Fix**: In `alpha_engine/cta_fx_multifactor.py`, add `dxy_regime = "bull" if dxy_50ma > dxy_200ma else "bear"`. Only emit FOREX MR picks when `dxy_regime == "bear"` (range-bound DXY).  
**Effort**: S-M (data feed + filter, 2-4 hrs)  

### REMAINING-P2-06: Polymarket/Kalshi Signals for EQUITY (IDEA-H Extension)
**What**: DAILY_IDEAS.MD IDEA-H mentions prediction market signals. Currently only CRYPTO uses Polymarket signals. Extend to EQUITY (merger arbitrage, regulatory outcomes, earnings).  
**Tasks**: `alpha_engine/polymarket_equity_signals.py` — query Polymarket API for equity-related markets, generate LONG/SHORT signal on resolution probability extremes (>80% or <20%).  
**Effort**: M-L (API integration + signal logic + validation, 8-16 hrs)  

### REMAINING-P2-07: Options Flow Integration (IDEA-D)
**What**: DAILY_IDEAS.MD IDEA-D mentions options flow (unusual activity, dark pool). High-conviction signals from options market can lead equity directional moves by 1-3 days.  
**Sources**: Unusual Whales API / Tradier options chain (live Greeks) / CBOE put-call ratio  
**Tasks**: `alpha_engine/options_flow_signals.py` — detect unusual OI concentration + delta weighted flow, emit EQUITY signal when call-to-put flow exceeds 2σ.  
**Effort**: L (API integration + signal engineering, 16-24 hrs)  

### REMAINING-P2-08: FRED Live Rates for FOREX Carry
**What**: `FOREX_SYMBOLS` config has static `carry_yield_diff` values not tied to live FRED rates. When central banks change rates (BoJ 2024-2025 hikes), carry signals become stale and wrong.  
**Fix**: `tools/fred_rates_updater.py` — query FRED API for latest policy rates, update `carry_yield_diff` in config or DB at weekly cadence.  
**Effort**: S-M (FRED API + config updater, 2-4 hrs)  

---

## P3 — Large Research Projects (90-Day Horizon)

### REMAINING-P3-01: Grok Unified Scoring v3 (score_v3.py)
**What**: Replace the current multi-component score with a single Bayesian posterior: `P(win | features) → score_v3`. Removes the confidence inversion problem at root. Uses Platt scaling on logistic regression output calibrated against actual closed picks.  
**Effort**: XL (research + training pipeline + A/B test, 2-4 weeks)  
**Prereq**: signal_outcomes refresh + forward_validator unfrozen + n>=1000 closed picks per class  

### REMAINING-P3-02: CVaR Portfolio Constructor
**What**: Currently picks are sized by flat `sizing_allowed` flags. A CVaR-based portfolio constructor would allocate across picks such that the combined 99th percentile loss is bounded (e.g., max 5% drawdown per day).  
**References**: Rockafellar-Uryasev 2000 CVaR model; `skfolio` library available in repo  
**Effort**: XL (research + integration + walk-forward test, 3-6 weeks)  

### REMAINING-P3-03: Full EQUITY Universe Expansion to 100 LC + Factor Scoring
**What**: Current EQUITY_SYMBOLS = 18 names (10 large-cap + 8 speculative). A proper large-cap universe is 100+ names with fundamental factor scoring (Fama-French 5F).  
**Tasks**: Integrate free EDGAR API for fundamental data, build factor model, rank universe weekly.  
**Effort**: XL (2-4 weeks)  

### REMAINING-P3-04: IPO Scanner (Full Build)
**What**: PEAD-adapted IPO scanner using EDGAR S-1/424B4 + lockup expiry calendar + revenue trajectory.  
**Phases**: (1) lockup expiry list from SEC EDGAR, (2) PEAD signal on day +5 post-lockup, (3) revenue screen, (4) wire to production  
**Effort**: L (3-5 days)  

### REMAINING-P3-05: Mutual Fund Position Reporting (IDEA-C)
**What**: DAILY_IDEAS.MD IDEA-C — scan 13F filings for hedge fund position changes, use as leading indicators for large-cap moves (2-3 quarter lag in filings but still informative).  
**Effort**: L-XL (EDGAR 13F parser + signal lag model, 2-3 weeks)  

### REMAINING-P3-06: ML Retraining with Proper Time-Series CV
**What**: Current ML models (confidence scores) likely have look-ahead leakage from improper train/test splits (confirmed: PF 99-1094 on copy_trader_intel n=21 = overfitting). Need TimeSeriesSplit + anchored WF.  
**Effort**: XL (clean dataset + retrain all models, 2-4 weeks)  
**Prereq**: REMAINING-P0-01, REMAINING-P0-02, REMAINING-P1-02 all resolved  

---

## Dashboard & Incidents Items To Add

### New Incidents (Add to findtorontoevents.ca/audit/incidents.html)

| ID | Type | Priority | Title | Status |
|---|---|---|---|---|
| NEW-I-01 | INCIDENT | P1 | WIN_RATE_TRAP_BLACKLIST is dead code — never checked in passes_active_gate | OPEN |
| NEW-I-02 | INCIDENT | P1 | EQUITY production scanner routing missing — strategies may never be called | OPEN |
| NEW-I-03 | INCIDENT | P0 | 2,531 WON rows have negative PnL (avg -41.1%) — outcome mislabeling | OPEN |
| NEW-I-04 | INCIDENT | P1 | Swarm Picks abandoned — swarm_picks.json 13+ days stale | OPEN |
| NEW-I-05 | INCIDENT | P2 | IPO tile advertised on /audit but zero picks ever emitted | OPEN |
| NEW-I-06 | INCIDENT | P1 | signal_outcomes table 82 days stale — all forward WR claims unverifiable | OPEN |

### New Enhancements (Add to findtorontoevents.ca/audit/incidents.html)

| ID | Type | Priority | Title | Status |
|---|---|---|---|---|
| NEW-E-01 | ENHANCEMENT | P1 | Hot streak exemption mechanism — elevated weights for strategies on N-win streak | OPEN |
| NEW-E-02 | ENHANCEMENT | P2 | Range-bound oscillating asset detection (USDJPY/GC=F/BTCUSDT/NG=F patterns) | OPEN |
| NEW-E-03 | ENHANCEMENT | P1 | BTC UTC 08-09Z death-zone filter (M-001) — n>1000 memory-backed edge | OPEN |
| NEW-E-04 | ENHANCEMENT | P2 | FOREX DXY regime awareness — only emit MR signals when DXY range-bound | OPEN |
| NEW-E-05 | ENHANCEMENT | P1 | PEAD equity full promotion pipeline — 62.2% OOS WR strategy in shadow mode | OPEN |
| NEW-E-06 | ENHANCEMENT | P2 | Polymarket/Kalshi signals for EQUITY (merger arb, earnings outcomes) | OPEN |
| NEW-E-07 | ENHANCEMENT | P2 | Options flow integration for EQUITY (unusual call/put activity) | OPEN |
| NEW-E-08 | ENHANCEMENT | P3 | CVaR portfolio constructor — bounded daily drawdown allocation | OPEN |
| NEW-E-09 | ENHANCEMENT | P2 | FRED live rates updater for FOREX carry (replaces static values in config.py) | OPEN |
| NEW-E-10 | ENHANCEMENT | P3 | Walk-forward validation in CI/CD — weekly automated OOS report | OPEN |

---

## Proposed `roadmap_items` Database Table

```sql
-- Suggested new table for ejaguiar1_stocks
-- Replaces ad-hoc INCIDENT_* / ENHANCEMENT_* table pattern
-- Add to database as part of roadmap management upgrade

CREATE TABLE roadmap_items (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    item_type           ENUM('INCIDENT','ENHANCEMENT') NOT NULL,
    priority            ENUM('P0','P1','P2','P3') NOT NULL,
    status              ENUM('OPEN','TRIAGED','IN_PROGRESS','RESOLVED','WONT_FIX','DEFERRED') 
                        DEFAULT 'OPEN',
    asset_class         VARCHAR(50) DEFAULT 'OVERALL'
                        COMMENT 'CRYPTO|EQUITY|FOREX|BOND|COMMODITY|ETF|FUTURES|PENNY_MEME|OVERALL',
    title               VARCHAR(500) NOT NULL,
    description         TEXT,
    root_cause          TEXT        COMMENT 'What caused the incident / why the enhancement is needed',
    affected_file       VARCHAR(500),
    affected_function   VARCHAR(200),
    proposed_fix        TEXT        COMMENT 'Concrete code or SQL change',
    acceptance_criteria TEXT        COMMENT 'How do we know it is fixed / done?',
    effort_size         ENUM('XS','S','M','L','XL')
                        COMMENT 'XS<30min S<2h M<8h L<3d XL>=3d',
    category            ENUM('GATE','SCORING','DATA_FEED','METHODOLOGY','UI','PIPELINE','ML')
                        COMMENT 'What subsystem does this touch?',
    source_agent        VARCHAR(200)
                        COMMENT 'Claude session ID or model that filed this item',
    m_number            VARCHAR(20) COMMENT 'M-XXX master plan reference e.g. M-107',
    pr_ref              VARCHAR(200) COMMENT 'GitHub PR number or branch name',
    doc_url             VARCHAR(500) COMMENT 'Link to .md or updates page entry',
    verified_by_query   TEXT        COMMENT 'SQL or grep that reproduces the evidence',
    metrics_before      JSON        COMMENT '{pf: 0.81, wr: 29, n: 53}',
    metrics_after       JSON        COMMENT '{pf: 1.34, wr: 51, n: 38} after fix',
    created_at          TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP   DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    resolved_at         TIMESTAMP   NULL,
    target_resolve_date DATE        NULL,
    
    INDEX idx_priority_status (priority, status),
    INDEX idx_asset_class (asset_class),
    INDEX idx_category (category),
    INDEX idx_item_type (item_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='Unified roadmap — replaces ad-hoc INCIDENT_* and ENHANCEMENT_* tables';
```

### Seed Data (Initial Entries)
```sql
INSERT INTO roadmap_items (item_type, priority, status, asset_class, title, affected_file, effort_size, category, source_agent, m_number) VALUES
('INCIDENT', 'P0', 'OPEN', 'OVERALL', 'ML confidence inverted: conf>=0.9 → WR 14.4%', 'alpha_engine/smart_picks_engine.py', 'M', 'ML', 'claude-sonnet-4.6-copilot-2026-05-27', NULL),
('INCIDENT', 'P0', 'OPEN', 'OVERALL', 'forward_validator frozen 270h / 29.2M open positions backlogged', 'alpha_engine/forward_validator.py', 'M', 'PIPELINE', 'claude-sonnet-4.6-copilot-2026-05-27', NULL),
('INCIDENT', 'P0', 'OPEN', 'OVERALL', '2531 WON rows have avg pnl -41.1% (mislabeling bug)', 'audit_trail/universal_pick_resolver.py', 'S', 'DATA_FEED', 'claude-sonnet-4.6-copilot-2026-05-27', NULL),
('INCIDENT', 'P0', 'OPEN', 'OVERALL', '56559 ghost duplicate rows (MATICUSDT 20474 alone)', 'alpha_engine/production_scanner.py', 'M', 'PIPELINE', 'claude-sonnet-4.6-copilot-2026-05-27', NULL),
('INCIDENT', 'P0', 'OVERALL', 'OVERALL', 'trust_score NULL on 99.99% of closed picks', 'alpha_engine/trust_scorer.py', 'M', 'SCORING', 'claude-sonnet-4.6-copilot-2026-05-27', NULL),
('INCIDENT', 'P0', 'OPEN', 'FOREX', 'FOREX pnl_pct < -100% on 5 rows (worst: -106700%)', 'trading_picks (SQL)', 'XS', 'DATA_FEED', 'claude-sonnet-4.6-copilot-2026-05-27', NULL),
('INCIDENT', 'P1', 'OPEN', 'OVERALL', 'WIN_RATE_TRAP_BLACKLIST is dead code — never checked in passes_active_gate', 'audit_trail/quality_gates.py', 'S', 'GATE', 'claude-sonnet-4.6-copilot-2026-05-27', NULL),
('INCIDENT', 'P1', 'OPEN', 'EQUITY', 'EQUITY production scanner routing missing', 'alpha_engine/production_scanner.py', 'M', 'PIPELINE', 'claude-sonnet-4.6-copilot-2026-05-27', NULL),
('INCIDENT', 'P1', 'OPEN', 'OVERALL', 'signal_outcomes table 82 days stale', 'audit_trail/universal_pick_resolver.py', 'M', 'DATA_FEED', 'claude-sonnet-4.6-copilot-2026-05-27', NULL),
('INCIDENT', 'P1', 'OPEN', 'OVERALL', 'Swarm picks 13+ days stale / workflow abandoned', 'alpha_engine/swarm_picks_writer.py', 'M', 'PIPELINE', 'claude-sonnet-4.6-copilot-2026-05-27', NULL),
('INCIDENT', 'P2', 'OPEN', 'IPO', 'IPO tile advertised on audit but zero picks ever emitted', 'audit_dashboard/template.html', 'S', 'UI', 'claude-sonnet-4.6-copilot-2026-05-27', NULL),
('ENHANCEMENT', 'P1', 'OPEN', 'EQUITY', 'Promote pead_equity shadow→probation (62.2% OOS WR)', 'alpha_engine/production_scanner.py', 'M', 'PIPELINE', 'claude-sonnet-4.6-copilot-2026-05-27', NULL),
('ENHANCEMENT', 'P1', 'OPEN', 'ETF', 'Enable ETF sector rotation emitter (PF 2.05-3.22 backtest)', 'tools/etf_sector_emitter.py', 'XS', 'PIPELINE', 'claude-sonnet-4.6-copilot-2026-05-27', NULL),
('ENHANCEMENT', 'P1', 'OPEN', 'OVERALL', 'Hot streak exemption — elevated weights for N-win-streak strategies', 'audit_trail/quality_gates.py', 'M', 'GATE', 'claude-sonnet-4.6-copilot-2026-05-27', NULL),
('ENHANCEMENT', 'P1', 'OPEN', 'CRYPTO', 'BTC UTC 08-09Z death-zone filter M-001 (n>1000 backed)', 'alpha_engine/score_booster.py', 'S', 'GATE', 'claude-sonnet-4.6-copilot-2026-05-27', 'M-001'),
('ENHANCEMENT', 'P2', 'OPEN', 'OVERALL', 'Range-bound oscillating asset detection (USDJPY/GC-F/BTC)', 'alpha_engine/range_oscillator_detector.py', 'M', 'METHODOLOGY', 'claude-sonnet-4.6-copilot-2026-05-27', NULL),
('ENHANCEMENT', 'P2', 'OPEN', 'FOREX', 'FOREX DXY regime awareness — only emit MR on range-bound DXY', 'alpha_engine/cta_fx_multifactor.py', 'S', 'GATE', 'claude-sonnet-4.6-copilot-2026-05-27', NULL),
('ENHANCEMENT', 'P2', 'OPEN', 'EQUITY', 'Options flow integration for EQUITY (unusual call/put activity)', 'alpha_engine/options_flow_signals.py', 'L', 'METHODOLOGY', 'claude-sonnet-4.6-copilot-2026-05-27', 'IDEA-D'),
('ENHANCEMENT', 'P2', 'OPEN', 'EQUITY', 'Polymarket/Kalshi signals for EQUITY (merger arb, earnings)', 'alpha_engine/polymarket_equity_signals.py', 'L', 'METHODOLOGY', 'claude-sonnet-4.6-copilot-2026-05-27', 'IDEA-H'),
('ENHANCEMENT', 'P3', 'OPEN', 'OVERALL', 'CVaR portfolio constructor — bounded daily drawdown allocation', 'alpha_engine/cvar_portfolio.py', 'XL', 'METHODOLOGY', 'claude-sonnet-4.6-copilot-2026-05-27', NULL),
('ENHANCEMENT', 'P3', 'OPEN', 'OVERALL', 'ML retraining with proper TimeSeriesSplit (remove look-ahead)', 'ml_gatekeeper/gatekeeper.py', 'XL', 'ML', 'claude-sonnet-4.6-copilot-2026-05-27', NULL);
```

---

## Summary Metrics Targets Per Asset Class

| Class | Current PF | Current WR | Target PF | Target WR | Horizon |
|---|---|---|---|---|---|
| CRYPTO | 1.14 | 43% | 1.5+ | 50%+ | 30 days (after confidence inversion fix + source whitelist) |
| EQUITY | 1.57 | 51.9% | 2.0+ | 60%+ | 45 days (after VIX gate + penny removal + PEAD) |
| ETF | 0 picks | — | 2.05+ | 60%+ | 7 days (after emitter enabled) |
| COMMODITY | 0.31 (real) | 11% | 1.3+ | 48%+ | 60 days (after COT dedup historical clean) |
| FOREX | 0.81 | 37% | 1.3+ SHORT | 55%+ | 30 days (after LONG block + SHORT-only paper) |
| BOND | 0 (n=8) | 0% | Research only | — | 90 days (no sizing claim until n>=50) |
| FUTURES | 0 (zombie) | — | Merge/deprecate | — | 7 days |
| PENNY/MEME | 0.19 | 6.76% | Quarantine | — | Immediate |
| IPO | 0 | — | Build MVP | — | 2 weeks |

---

*Generated by Claude Sonnet 4.6 via GitHub Copilot — 2026-05-27 EST*  
*Companion to: `reports/EAGLE-2026-05-27-quick-wins-claude-sonnet46-copilot.md`*
