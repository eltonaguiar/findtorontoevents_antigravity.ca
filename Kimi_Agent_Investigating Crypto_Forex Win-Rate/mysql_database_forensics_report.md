# MYSQL DATABASE FORENSICS REPORT - DATA INTEGRITY INVESTIGATION

**Database:** mysql.50webs.com → ejaguiar1_stocks  
**Investigation Date:** 2026-03-25  
**Purpose:** Analyze why crypto/forex win rates are not reflecting copied traders' performance

---

## SECTION 1: DATABASE SCHEMA ANALYSIS

### Tables in ejaguiar1_stocks Database

| Table | Written By | Purpose |
|-------|------------|---------|
| `at_discord_notifications` | audit_trail/mysql_client.py | Every Discord send (picks, TP/SL hits) |
| `at_discord_gate_log` | audit_trail/mysql_client.py | Gate decisions (pass/reject with reason) |
| `at_local_picks` | audit_trail/backfill_local_sources.py | Backfill from local SQLite/JSON |
| `at_audit_events` | audit_trail/backfill_local_sources.py | Audit event log |
| `at_signal_outcomes` | audit_trail/backfill_local_sources.py | Signal outcome tracking |
| `at_filter_log` | audit_trail/backfill_local_sources.py | Pick filter decisions |
| `strategy_registry` | audit_trail/build_strategy_registry.py | Strategy metadata catalog |

---

## SECTION 2: CRITICAL DATA FLOW GAPS

### ❌ MISSING DATA IN MYSQL
1. Full pick lifecycle (open → price update → close) for most systems
2. Win/loss outcomes from dashboard_payload
3. Strategy performance metrics
4. Consensus agreement data
5. Portfolio P&L tracking

### ✅ WHAT IS BEING WRITTEN TO MYSQL
- Discord notification events (at_discord_notifications)
- Gate pass/reject decisions (at_discord_gate_log)
- Backfilled local picks (at_local_picks) - PARTIAL
- Basic audit events (at_audit_events)
- Signal outcomes - PARTIAL/INCOMPLETE
- Filter decisions (at_filter_log)
- Strategy registry metadata (strategy_registry)

---

## SECTION 3: COPY TRADER DATA ANALYSIS

### Copy Trader Systems with No Outcome Resolution

| System | Active | Closed | WR% | Issue |
|--------|--------|--------|-----|-------|
| copy_trader_intel | 10 | 49 | 0.0%* | No outcome resolution |
| copy_trader_highscore | 0 | 19 | 0.0%* | No outcome resolution |
| copy_trader_clones | 0 | 40 | 0.0%* | No outcome resolution |
| copy_trader_consensus | 4 | 13 | 0.0%* | No outcome resolution |

*Systems show 0.0% WR because no price validation runs for these picks

### Copy Trader Picks Have
- ✅ entry_price field
- ✅ take_profit field
- ✅ stop_loss field
- ❌ NO outcome resolver running

### Proven Profitable Copy Traders

| Trader | Picks | WR% | Avg PnL | Verdict |
|--------|-------|-----|---------|---------|
| NMTD_25M (Hyperliquid) | 16 | 81.2% | +2.0% | KEEP |
| whale_123M_87roi (HL) | 4 | 100% | +3.0% | KEEP |
| binance_smart_money | 24 | 45.8% | -0.9% | KILL |
| All Bitget traders | 5 | 0% | -3.2% | KILL |

### Root Cause of Copy Trader Issues
1. copy_trader_intel picks are on-chain verified from Hyperliquid/Binance/BingX
2. copy-trader-forward-test.yml workflow exists but only tracks portfolio PnL
3. Individual pick outcomes are NOT resolved (no TP_HIT/SL_HIT tracking)
4. The alpha_engine has copy_trader_bridge.py and cta_bridge.py
5. BUT dashboard_generator.py does NOT list copy_trader_intel in JSON_PICK_SOURCES

---

## SECTION 4: SYSTEMS WITH 0% WIN RATE

**TOTAL: ~1,400+ closed picks with NO win/loss tracking**

| System | Active | Closed | WR% | Issue |
|--------|--------|--------|-----|-------|
| quan_engine | 5 | 47 | 0.0%* | No TP/SL validation |
| copy_trader_intel | 10 | 49 | 0.0%* | No outcome resolution |
| copy_trader_highscore | 0 | 19 | 0.0%* | No outcome resolution |
| copy_trader_clones | 0 | 40 | 0.0%* | No outcome resolution |
| copy_trader_consensus | 4 | 13 | 0.0%* | No outcome resolution |
| rapid_fire | 79 | 334 | 0.0%* | No outcome resolution |
| predictions | 0 | 324 | 0.0%* | No outcome resolution |
| goldmine_stocks | 37 | 14 | 0.0%* | No outcome resolution |
| kimi_signal_tracking | 11 | 169 | 0.0%* | No PnL calculation |
| revival_* (7 systems) | 0 | 284 | 0.0%* | No outcome resolution |
| genetic_programmer | 0 | 50 | 0.0%* | No outcome resolution |
| ensemble_evolver | 0 | 25 | 0.0%* | No outcome resolution |
| mape_evolver | 0 | 27 | 0.0%* | No outcome resolution |

---

## SECTION 5: PREDICTION MARKET SIGNALS - COMPLETELY DISCONNECTED

**CRITICAL FINDING: prediction_market_agents is NOT connected to anything**

Location: prediction_market_agents/data/
- whale_signals.json (5 active signals)
- consensus_signals.json (2 active signals)
- momentum_signals.json

**STATUS:**
- ❌ ZERO external scripts reference prediction_market_agents
- ❌ Not in dashboard_generator.py JSON_PICK_SOURCES
- ❌ No outcome resolution
- ❌ Active signals are being generated but completely ignored

---

## SECTION 6: DATA ARCHITECTURE PROBLEM

**PRIMARY AUDIT STORE:** Local SQLite (data/audit_trail.db)  
**SECONDARY STORE:** MySQL (ejaguiar1_stocks) - Discord audit + backfill only

```
Pick Generators ──▶ Local SQLite DB ──▶ Dashboard (Primary)
      │                    │
      │             ┌──────▼────────┐
      └────────────▶│ MySQL Backfill│
                    │ (Partial)     │
                    └───────────────┘
```

**PROBLEM:** MySQL is NOT the source of truth for:
- Pick lifecycle tracking
- Win/loss outcomes
- Performance metrics
- Consensus data

---

## SECTION 7: WHY WIN/LOSS OUTCOMES AREN'T BEING RECORDED

### Root Causes

1. **NO OUTCOME RESOLVER FOR COPY TRADERS**
   - copy_trader_intel has entry/exit prices but no resolution logic
   - copy-trader-forward-test.yml only tracks portfolio-level PnL
   - Individual pick outcomes never calculated

2. **PRICE VALIDATION GAP**
   - claude_gainer_st has TP_HIT/SL_HIT resolution (working)
   - Most other systems have NO price validation pipeline
   - 50+ systems have closed picks but 0% WR

3. **DATA FLOW ARCHITECTURE FLAW**
   - Local SQLite is primary audit store
   - MySQL is secondary (Discord + infrequent backfill)
   - Win/loss outcomes computed in dashboard, not written back to DB

4. **MISSING INTEGRATION POINTS**
   - dashboard_payload has outcomes but doesn't write to MySQL
   - at_signal_outcomes table exists but not populated in real-time
   - No automated outcome resolution workflow

5. **ORPHAN DATA FILES**
   - 43 orphan files with 713 items (~966 KB unreferenced data)
   - Systems like prediction_market_agents completely disconnected
   - Closed pick files not integrated into dashboard

---

## SECTION 8: RECOMMENDATIONS TO FIX DATA INTEGRITY

### IMMEDIATE (P0 - Data Loss Prevention)

| Priority | Action | Impact |
|----------|--------|--------|
| 1 | Add copy_trader_intel to dashboard_generator.py JSON_PICK_SOURCES | 39 active picks + 455 sub-file picks currently invisible |
| 2 | Create outcome resolver for copy_trader_intel picks | Wire into price validation pipeline |
| 3 | Add prediction_market_agents to dashboard | 5 whale + 2 consensus signals being lost |
| 4 | Integrate closed pick files | 312 luxalgo + 105 multi_asset results |

### SHORT-TERM (P1 - Data Completeness)

| Priority | Action | Impact |
|----------|--------|--------|
| 5 | Create real-time outcome sync from dashboard to MySQL | Write resolved outcomes to at_signal_outcomes |
| 6 | Add price validation to quan_engine, rapid_fire, predictions | 1,400+ picks with no outcome resolution |
| 7 | Fix KIMI double-counting | Remove duplicate from JSON_PICK_SOURCES |

### LONG-TERM (P2 - Architecture)

| Priority | Action | Impact |
|----------|--------|--------|
| 8 | Make MySQL the primary audit store | Real-time write path for all pick events |
| 9 | Create automated outcome resolution workflow | Scheduled job to resolve TP/SL |
| 10 | Add data integrity monitoring | Alert when picks have no outcome |

---

## SECTION 9: SUMMARY OF FINDINGS

### Critical Issues
1. ~1,400+ closed picks have NO win/loss tracking (0% WR displayed)
2. copy_trader_intel has real picks but no outcome resolution
3. prediction_market_agents is completely disconnected
4. MySQL is secondary store - outcomes computed in dashboard not written back
5. 50+ systems wired to dashboard but no price validation running

### Data Gaps
- at_signal_outcomes: Missing ~1,400+ records
- at_local_picks: Partial/stale backfill only
- at_discord_notifications: Working (Discord events logged)
- at_discord_gate_log: Working (gate decisions logged)
- strategy_registry: Working (metadata catalog)

### Win/Loss Tracking Status
- ✅ Working: 26 systems with real WR tracking
- ❌ Broken: ~50 systems with closed picks but 0% WR
- ⚠️ Dormant: ~39 systems with 0 active + 0 closed picks

---

*Report generated from analysis of 8 documentation files covering 240+ workflows, 115 dashboard systems, and 14,000+ closed picks.*
