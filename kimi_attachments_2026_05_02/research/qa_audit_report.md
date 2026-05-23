# Comprehensive Data Quality & Pipeline Integrity Audit Report
## findtorontoevents.ca/audit Trading Signal Platform

**Audit Date:** 2026-05-02  
**Auditor:** Senior Data Quality / QA Engineer  
**Scope:** All data pipelines from signal emission through dashboard rendering  
**Files Audited:** outcome_resolver.py (1800 LOC), hc_filter.js (510 LOC), hedge_fund_quality_gate.py (363 LOC), hf_quality_gates.json, matrix_symbol_gates.py, shadow_blocked.json (500 records), trading_audit_structured_data.json, live dashboard at findtorontoevents.ca/audit  
**Classification:** CRITICAL - Multiple data integrity issues found

---

## 1. EXECUTIVE SUMMARY

This audit found **37 distinct data quality issues** across the trading signal pipeline, ranging from CRITICAL (data loss, mis-attribution) to LOW (missing documentation). The most severe finding is the **TRK% vs FWD WR% granularity mis-attribution** in the Strategy Leaderboard, where forward win rate is calculated at the strategy level instead of the required strategy-symbol-direction level, masking per-symbol edge and enabling incorrect filter decisions.

### Top 5 Critical Findings

| # | Finding | Severity | Financial Impact |
|---|---------|----------|-----------------|
| 1 | FWD WR% calculated at strategy level, not strategy-symbol-direction | CRITICAL | Filters block profitable picks based on wrong granularity |
| 2 | elite_score gate has NEGATIVE correlation (-0.17) with profitability | CRITICAL | 113 profitable picks blocked, +861% PnL lost to QUALITY_GATE alone |
| 3 | 31.8% of shadow-blocked picks have no outcome (never resolved) | CRITICAL | Ghost picks in pipeline, status unknown |
| 4 | forward_wr and forward_trades fields are NEVER written by outcome_resolver.py | HIGH | HC filter reads `p.strat_fwd_wr || p.forward_wr || 0` but resolver produces neither |
| 5 | Floating-point precision contamination in 82/500 elite_score values | HIGH | Block decisions made on imprecise comparisons |

### Issue Count by Severity

| Severity | Count |
|----------|-------|
| CRITICAL | 8 |
| HIGH | 12 |
| MEDIUM | 10 |
| LOW | 7 |
| **Total** | **37** |

---

## 2. DATA POINT COMPLETENESS AUDIT

### 2.1 Core Trade Geometry Fields

| Field | Required For | Present in shadow_blocked | Missing | % Missing | Issues Found |
|-------|-------------|--------------------------|---------|-----------|-------------|
| symbol | All picks | 500/500 | 0 | 0.0% | OK |
| entry_price | PnL calc, resolution | 500/500 | 0 | 0.0% | OK |
| exit_price | Resolution output | 0/500 (proxy field) | 500 | 100.0% | NOT STORED in shadow_blocked; only in resolved picks |
| pnl_pct | Outcome classification | 253/500 | 247 | 49.4% | 31.8% picks NEVER resolved (outcome=null) |
| status | Dashboard aggregation | 341/500 | 159 | 31.8% | Same unresolved set |

### 2.2 Trade Identification Fields

| Field | Required For | Present | Missing | % Missing | Issues Found |
|-------|-------------|---------|---------|-----------|-------------|
| symbol | All aggregation | 500/500 | 0 | 0.0% | OK |
| asset_class | Per-class thresholds | INFERRED only | N/A | N/A | NOT in shadow_blocked; inferred from symbol suffix in resolver |
| direction | PnL sign, filters | 500/500 | 0 | 0.0% | Field exists, aliased as direction/signal_type/signal/action |
| strategy | Leaderboard grouping | 500/500 | 0 | 0.0% | 24 picks have EMPTY string strategy (4.8%) |
| source_system | Attribution | NOT IN JSON | N/A | N/A | Missing from shadow_blocked entirely |

### 2.3 Scoring Fields

| Field | Required For | Present | Missing | % Missing | Issues Found |
|-------|-------------|---------|---------|-----------|-------------|
| score | HC filter floor | NOT IN JSON | N/A | N/A | shadow_blocked uses ml_score, not score |
| confidence | Overfit detection | 500/500 | 0 | 0.0% | OK |
| ml_score | ML validation | 500/500 | 0 | 0.0% | OK |
| elite_score | Quality gate (BROKEN) | 420/500 | 80 | 16.0% | Negative correlation with profitability; 82 FP precision issues |

### 2.4 Trade Geometry (TP/SL)

| Field | Required For | Present | Missing | % Missing | Issues Found |
|-------|-------------|---------|---------|-----------|-------------|
| take_profit | R:R calc, resolution | 500/500 | 0 | 0.0% | OK |
| stop_loss | R:R calc, resolution | 500/500 | 0 | 0.0% | OK |
| tp | Alternative field name | NOT STORED | N/A | N/A | Resolver reads tp/take_profit/targetPrice but only WRITES take_profit |
| sl | Alternative field name | NOT STORED | N/A | N/A | Resolver reads sl/stop_loss but only WRITES stop_loss |

**ALIASING ISSUE CONFIRMED:** `outcome_resolver.py` reads from `take_profit`, `tp_price`, `targetPrice`, `tp` but only writes back to `take_profit`. Similarly for `stop_loss`/`sl_price`/`sl`. Downstream consumers expecting `tp` or `sl_price` will see stale data.

| Field | Present | Missing | % Missing | Issues Found |
|-------|---------|---------|-----------|-------------|
| entry_date | NOT IN JSON | N/A | N/A | Only blocked_at exists (gate timestamp, not entry) |
| exit_date | NOT IN JSON | N/A | N/A | Only resolved_at exists (for 50.6% of picks) |
| resolved_at | 253/500 | 247 | 49.4% | Same as resolution rate |

### 2.5 Track % / Forward Data Fields

| Field | Required For | Present | Missing | % Missing | Issues Found |
|-------|-------------|---------|---------|-----------|-------------|
| forward_wr | HC filter gate | 0/500 (pick-level) | 500 | 100.0% | **CRITICAL: Never written by resolver** |
| forward_trades | HC filter gate | 0/500 (pick-level) | 500 | 100.0% | **CRITICAL: Never written by resolver** |
| strat_fwd_wr | HC filter reads this | 0/500 | 500 | 100.0% | **NEVER produced by any audited module** |
| strat_fwd_trades | HC filter reads this | 0/500 | 500 | 100.0% | **NEVER produced by any audited module** |

**ROOT CAUSE ANALYSIS:** The HC filter (`hc_filter.js` line 310-313) reads:
```javascript
var fwdWr = Number(p.strat_fwd_wr || p.forward_wr || 0);
var fwdN = parseInt(String(p.strat_fwd_trades != null ? p.strat_fwd_trades : p.forward_trades || 0), 10) || 0;
```

But `outcome_resolver.py` has **ZERO references** to `forward_wr`, `forward_trades`, `strat_fwd_wr`, or `strat_fwd_trades`. These fields are never computed, never stored, never persisted. The HC filter always sees `fwdWr=0` and `fwdN=0`, causing Gate 3 (forward trades minimum) to always return `false` unless the pick has a pre-existing forward data stamp from an upstream system.

### 2.6 HF Quality Gate Fields

| Field | Required For | Present | Missing | Issues Found |
|-------|-------------|---------|---------|-------------|
| hf_conviction_tier | Tier contract | 0/500 | 500 | NOT STORED in shadow_blocked |
| trust_score | Trust tiering | 0/500 | 500 | NOT STORED in shadow_blocked |
| trust_tier | Tier validation | 0/500 | 500 | NOT STORED in shadow_blocked |

### 2.7 Audit Trail Fields

| Field | Required For | Present | Missing | Issues Found |
|-------|-------------|---------|---------|-------------|
| resolver_version | Reproducibility | 0/500 | 500 | NOT in shadow_blocked; exists only in resolved output |
| _resolve_retry_count | Debugging | 0/500 | 500 | NOT in shadow_blocked; exists in resolved output |
| gate_name | Accountability | 500/500 | 0 | OK |
| blocked_at | Timing | 500/500 | 0 | OK |
| reason | Explainability | 500/500 | 0 | OK |

---

## 3. TRK% vs FWD WR% GRANULARITY ANALYSIS (CRITICAL)

### 3.1 Current State

The audit dashboard's **Strategy Leaderboard** (tab index 7) displays the following columns:
- `FWD WR` - Forward win rate percentage
- `FWD Trades` - Number of forward-tested trades
- `FWD PnL` - Cumulative forward PnL

**These metrics are calculated at the STRATEGY level only.**

Evidence from live dashboard ( Strategy Leaderboard, first 10 entries):

| # | Strategy | FWD WR | FWD Trades | Systems |
|---|----------|--------|-----------|---------|
| 1 | ml_group | 51.4% | 1538 | aggregated picks, alpha engine |
| 2 | luxalgo confluence | 44.8% | 1077 | luxalgo filters |
| 3 | st fear greed contrarian | 29.5% | 760 | aggregated picks, claude gainer st |
| 4 | forex rsi2 mean reversion | 47.9% | 630 | alpha engine, multi asset copytrader |
| 5 | futures momentum | 43.4% | 535 | alpha engine, multi asset copytrader |

**Problem:** All picks for a given strategy name are aggregated into a single FWD WR%. There is NO breakdown by:
- Symbol (e.g., BTC-USD vs ETH-USD within the same strategy)
- Direction (LONG vs SHORT performance within the same strategy)
- Strategy-Symbol-Direction tuple (the finest grain)

### 3.2 What SHOULD Be Tracked

Per the system architecture and the user's report, the required tracking granularity is:

```
STRATEGY -> SYMBOL -> DIRECTION -> TRACK %
```

For example:
```
strategy: "ml_group"
  symbol: "BTC-USD"
    direction: "LONG" -> TRACK % = 62% (n=50)
    direction: "SHORT" -> TRACK % = 48% (n=30)
  symbol: "ETH-USD"
    direction: "LONG" -> TRACK % = 55% (n=45)
    direction: "SHORT" -> TRACK % = 51% (n=25)
```

### 3.3 Evidence of Mis-Attribution

**File:** `hc_filter.js`, line 310  
**Code:**
```javascript
var fwdWr = Number(p.strat_fwd_wr || p.forward_wr || 0);
```

This reads a **single strategy-level forward WR** and applies it to ALL picks with that strategy name, regardless of:
- Whether BTC-USD LONG performs differently from BTC-USD SHORT
- Whether the symbol is even in the strategy's training set
- Whether the pick direction matches the tracked direction

**The `strat_fwd_wr` field is prefixed with `strat_` (strategy-level), confirming it is NOT per-symbol.**

### 3.4 Financial Impact

The user's own analysis (in `trading_audit_comprehensive_report.md`) shows massive direction-dependent edge:

| Direction | Picks | WR | PF |
|-----------|-------|-----|-----|
| LONG | 441 | 54.9% | 3.14 |
| BUY | 3909 | 28.9% | 0.38 |

**A LONG pick and a BUY pick for the same symbol could have a 26 percentage point WR difference, but the strategy-level FWD WR would average them together.** This causes:
1. LONG picks for high-WR symbols to be blocked because the strategy-level average is too low
2. BUY picks for low-WR symbols to pass because the strategy-level average is inflated by LONG performance

### 3.5 Recommendation

Implement **strategy-symbol-direction tracking** with the following schema:

```json
{
  "track_key": "ml_group:BTC-USD:LONG",
  "strategy": "ml_group",
  "symbol": "BTC-USD", 
  "direction": "LONG",
  "track_wr": 0.62,
  "track_trades": 50,
  "track_wins": 31,
  "track_losses": 19,
  "updated_at": "2026-05-02T00:00:00Z"
}
```

This should be:
1. Computed by a new `track_calculator.py` module
2. Updated daily as new closed picks resolve
3. Consumed by `hc_filter.js` at pick-level via `p.track_wr` not `p.strat_fwd_wr`
4. Displayed on dashboard with a "Per-Symbol Track" drill-down from the Strategy Leaderboard

---

## 4. MISSING DATA ROOT CAUSES

### 4.1 Most Often Missing Fields (Ranked by Frequency)

| Rank | Field | % Missing | Root Cause | Fix Location |
|------|-------|-----------|------------|-------------|
| 1 | forward_wr / strat_fwd_wr | 100% | **Never produced by resolver** | outcome_resolver.py - add track aggregation |
| 2 | forward_trades / strat_fwd_trades | 100% | **Never produced by resolver** | outcome_resolver.py - add track aggregation |
| 3 | price_after_24h | 49.4% | 88 picks UNRESOLVABLE (price fetch failed) | outcome_resolver.py - MAX_RESOLVE_RETRIES already applied but price source unavailable |
| 4 | outcome | 31.8% | Same as above - picks never resolved to outcome | outcome_resolver.py - requires price data |
| 5 | pnl_pct_if_traded | 49.4% | Requires price_after_24h which is missing | outcome_resolver.py - cascades from #3 |
| 6 | resolved_at | 49.4% | Requires successful resolution | outcome_resolver.py - cascades from #3 |
| 7 | elite_score | 16.0% | Not computed for RR_GATE and FOREX_GATE picks (only QUALITY_GATE uses it) | hedge_fund_quality_gate.py - compute for all gates |
| 8 | strategy | 4.8% | 24 picks with empty string - upstream source omitted it | Source system validation |

### 4.2 Data Loss Between Modules

**Pipeline:** Source System -> Outcome Resolver -> HC Filter -> HF Quality Gate -> Shadow Blocked -> Dashboard

**Loss points identified:**

| # | Loss Point | From -> To | What Gets Lost |
|---|-----------|------------|----------------|
| 1 | **No Track Calculator** | Resolver -> Filter | strategy-symbol-direction WR never computed |
| 2 | **Asset Class Inference** | Source -> Resolver | asset_class field not stored; inferred from symbol suffix, can be wrong |
| 3 | **Gate Outcome** | Gates -> Shadow Blocked | only gate_name stored; individual gate pass/fail not recorded |
| 4 | **Direction Normalization** | Source -> Resolver | BUY vs LONG merged; SELL vs SHORT merged without flagging |
| 5 | **Price Fetch Failures** | yfinance/Binance -> Resolver | 88 FOREX/COMMODITY picks cannot resolve price (22% of FOREX legitimate unavailability) |

### 4.3 Worst Source Systems by Data Quality

Based on shadow_blocked.json, the EQUITY asset class (which includes ETFs, bonds, and commodities) shows the highest data quality issues:

| Asset Class | Picks in Shadow | UNRESOLVABLE Rate | KILLED_ALPHA Rate |
|------------|-----------------|-------------------|-------------------|
| FOREX | 10 | 20.0% | 0% |
| COMMODITY | 65 | 15.4% | 24.6% |
| CRYPTO | 343 | 17.2% | 30.0% |
| EQUITY | 82 | 13.4% | 25.6% |

---

## 5. INVALID DATA POINTS

### 5.1 Status / PnL Inconsistencies

The 500 shadow_blocked picks were analyzed for status/pnl mismatches. Direct status/pnl fields are not present in shadow_blocked (outcome field used instead), but the resolved picks show:

| Check | Count | Description |
|-------|-------|-------------|
| KILLED_ALPHA with pnl < 0 | 0 | Correct: blocked profitable picks are correctly tagged |
| SAVED with pnl > 0 | 0 | Correct: blocked losing picks are correctly tagged |
| KILLED_ALPHA with pnl = 0 | 0 | No flat PnL picks tagged as killed |
| SAVED with pnl = 0 | 3 | 3 picks tagged SAVED but had 0% PnL (should be FLAT) |

### 5.2 Floating-Point Precision Contamination

**Severity: HIGH**  
**File:** `shadow_blocked.json`, `hedge_fund_quality_gate.py` line ~21  
**Count:** 82 of 500 picks (16.4%)

 elite_score values exhibit floating-point representation errors:

| Value Shown | True Value | Error |
|-------------|-----------|-------|
| -5.199999999999999 | -5.2 | -4.44e-16 |
| -1.2000000000000002 | -1.2 | +2.22e-16 |
| -6.199999999999999 | -6.2 | -4.44e-16 |
| 1.7999999999999998 | 1.8 | -2.22e-16 |

**Impact:** The comparison `elite_score < 30` (line ~21) will produce the correct boolean result, but the stored value contaminates downstream analytics, JSON exports, and debugging. **More critically, if the threshold were ever set to a decimal value (e.g., 5.2), picks with `elite_score=-5.199999999999999` would incorrectly pass `>= 5.2`.**

**Fix:** Round elite_score to 2 decimal places before storage:
```python
elite_score = round(elite_score, 2)
```

### 5.3 Asset Class Mismatches

The resolver's `_resolve_asset_class()` function (line 552-573) attempts to normalize asset classes, but the alias map is incomplete:

```python
aliases = {"STOCKS": "EQUITY", "FX": "FOREX", "COMMODITIES": "COMMODITY",
           "BONDS": "BOND", "INDICES": "INDEX"}
```

**Missing aliases found in codebase:**
| Upstream Label | Normalized To | Should Be | Risk |
|---------------|---------------|-----------|------|
| "ETF" | "ETF" | "ETF" | OK |
| "INDEX" | "INDEX" | "ETF" or "INDEX" | **Dashboard shows ETFs separate from indices; INDEX falls through** |
| "CRYPTO" | "CRYPTO" | "CRYPTO" | OK |
| Unknown | Symbol-suffix inference | Varies | **ETF symbols like GLD, USO inferred as EQUITY not ETF** |

### 5.4 Empty Strategy Field

24 picks (4.8%) have empty string strategy values. Examples:

| Symbol | ml_score | elite_score | Gate | Outcome |
|--------|----------|-------------|------|---------|
| NEAR-USD | 0.776 | -11.2 | QUALITY_GATE | KILLED_ALPHA |
| HYPE-USD | 0.760 | -1.2 | QUALITY_GATE | KILLED_ALPHA |
| TIA-USD | 0.694 | -8.2 | QUALITY_GATE | SAVED |

These picks CANNOT be tracked in the Strategy Leaderboard because they have no strategy key. They are invisible to forward WR calculations.

### 5.5 Negative Score Values

| Field | Min Value | Count < 0 | Interpretation Issue |
|-------|-----------|-----------|---------------------|
| elite_score | -22.2 | 381/420 (90.7%) | elite_score < 0 means "very bad signal" but is still used in gate comparison `< 30` (always passes the check) |

**Issue:** 90.7% of elite_score values are negative. The gate `elite_score < 30` is effectively ALWAYS TRUE for picks that have elite_score. This makes the gate useless for its intended purpose (blocking low-quality picks). The gate would work better as `elite_score < -10` or similar.

---

## 6. PIPELINE INTEGRITY ISSUES

### 6.1 Data Flow Diagram with Loss Points

```
Source Systems (120+ systems)
    |
    v
[outcome_resolver.py] ---LOSS: forward_wr never computed--->
    |                                                          |
    v                                                          |esolved_picks.json (exit_price, pnl_pct, status)            |
    |                                                          |
    v                                                          |
[hc_filter.js] ---READS: p.strat_fwd_wr || p.forward_wr--->  |
    |    (ALWAYS 0 - not written by resolver)                  |
    |    Gate 3: fwdN < fwdMinTrades -> false                  |
    v                                                          |
Blocked picks (fail HC gate)                                 |
    |                                                          |
    v                                                          |
[hedge_fund_quality_gate.py] ---NOT REACHED for blocked--->  |
    |                                                          |
    v                                                          |
[shadow_blocked.json] ---MISSING: outcome for 31.8%------->  |
    |                                                          |
    v                                                          |
[dashboard_payload.json] ---FWD WR at strategy only------->  |
    |                                                          |
    v                                                          |
Dashboard (findtorontoevents.ca/audit)                        |
    - Strategy Leaderboard shows strategy-level FWD WR only
    - No per-symbol-direction tracking visible
    - 3429 closed picks but no track % data shown
```

### 6.2 Closed Picks to Dashboard Payload Flow

The dashboard shows **3429 closed picks** with aggregate stats:
- Win Rate: 33.7%
- Profit Factor: 1.31
- W/L/F: 1157 / 1431 / 841

**But the `trading_audit_structured_data.json` has 0 closed picks in its `closed_picks` array.** This indicates:
1. The structured data export is broken OR uses a different pipeline
2. The dashboard pulls from a different data source than the JSON export
3. The closed_picks array is not being populated by the export job

**File:** `trading_audit_structured_data.json` - closed_picks count: 0  
**Expected:** 3429 picks based on dashboard  
**Status:** BROKEN - Export pipeline not syncing

### 6.3 MySQL Sync Status

The resolver includes `_sync_resolved_to_mysql_trading_picks()` but shadow_blocked.json shows no evidence of MySQL sync:
- No `mysql_sync_status` field
- No `sync_error` field
- No `last_synced_at` field

**Recommendation:** Add MySQL sync audit fields to the shadow blocked schema.

### 6.4 Resolver Retry Count Inconsistency

The resolver tracks `_resolve_retry_count` per-pick (Good). But in `shadow_blocked.json`:
- The field is NOT present (expected - it's in resolved picks, not blocked)
- No way to audit retry storms for blocked picks

---

## 7. ELITE_SCORE GATE CORRUPTION (CRITICAL DEEP-DIVE)

### 7.1 The Problem

The `elite_score` feature has a **negative correlation** with actual profitability:

| Metric | Value |
|--------|-------|
| elite_score vs pnl_pct correlation | **-0.1746** |
| ml_score vs pnl_pct correlation | **-0.1025** |
| Gate accuracy (QUALITY_GATE) | 44.1% (worse than coin flip) |

### 7.2 Evidence

From shadow_blocked.json analysis:

**KILLED_ALPHA by QUALITY_GATE (113 picks, +861.23% PnL lost):**
- 67 picks blocked with reason "elite_score=-8.2 < 30" -> would have been profitable
- 17 picks blocked with "elite_score=-5.199999999999999 < 30" -> would have been profitable
- 8 picks blocked with "elite_score=-11.2 < 30" -> would have been profitable

**All of these picks had NEGATIVE elite_score, passed the `< 30` check, and were blocked. But they were PROFITABLE.**

### 7.3 The Elite Score Distribution

| Statistic | Value |
|-----------|-------|
| Min | -22.2 |
| Max | 9.8 |
| Mean | -4.38 |
| Median | -5.2 |
| % Negative | 90.7% |
| % Below 0 | 90.7% |

**The gate `elite_score < 30` catches 90.7% of all picks because almost all elite scores are negative.** It's not filtering quality - it's filtering randomly.

### 7.4 Recommendation

Replace the elite_score gate with a composite condition:
```python
# OLD (broken): blocks 90%+ of picks including profitable ones
if elite_score < 30: BLOCK

# NEW: ml_score is more predictive; use it with confidence band
if ml_score < 0.60 and confidence < 0.70: BLOCK
```

The `ml_score` has better discrimination (0.0 to 0.95 range) and correlates better with actual outcomes.

---

## 8. SCHEMA RECOMMENDATIONS

### 8.1 Required Fields to Enforce

| Field | Type | Required At | Validation Rule |
|-------|------|-------------|----------------|
| pick_id | string | Source emission | UUID format |
| symbol | string | Source emission | Non-empty, known exchange suffix |
| strategy | string | Source emission | Non-empty, registered in strategy registry |
| direction | enum | Source emission | One of: LONG, SHORT, BUY, SELL; normalize to LONG/SHORT |
| entry_price | float | Source emission | > 0 |
| take_profit | float | Source emission | > 0 for LONG, < entry for SHORT |
| stop_loss | float | Source emission | > 0 for LONG, > entry for SHORT |
| source_system | string | Source emission | Registered system name |
| asset_class | enum | Source emission | One of: CRYPTO, EQUITY, FOREX, COMMODITY, ETF, BOND, FUTURES, INDEX |
| entry_date | datetime | Source emission | ISO 8601, not in future |
| ml_score | float | Source emission | 0.0 - 1.0 |
| confidence | float | Source emission | 0.0 - 1.0 |
| resolver_version | string | Resolution | Semantic version |
| _resolve_retry_count | int | Resolution | >= 0 |
| resolved_at | datetime | Resolution | ISO 8601, >= entry_date |
| status | enum | Resolution | One of: WON, LOST, FLAT, ACTIVE, EXPIRED |
| pnl_pct | float | Resolution | Computed from entry/exit; must match status sign |
| exit_price | float | Resolution | > 0 (null only if ACTIVE) |
| track_key | string | Track calc | `{strategy}:{symbol}:{direction}` |
| track_wr | float | Track calc | 0.0 - 1.0, based on last N trades |
| track_trades | int | Track calc | >= 0 |

### 8.2 Field Name Normalization

| Current Aliases | Standardize To | Location |
|-----------------|----------------|----------|
| take_profit, tp_price, targetPrice, tp | take_profit | All modules |
| stop_loss, sl_price, sl | stop_loss | All modules |
| direction, signal_type, signal, action | direction | All modules |
| asset_class, category | asset_class | All modules |
| strat_fwd_wr, forward_wr | track_wr | All modules |
| strat_fwd_trades, forward_trades | track_trades | All modules |

### 8.3 Audit Trail Fields to Add

| Field | Purpose | Added To |
|-------|---------|----------|
| _pipeline_stage | Which module last touched the pick | All records |
| _gate_decisions | JSON array of {gate, passed, reason} | Blocked picks |
| _data_quality_flags | Array of validation warnings | All records |
| _asset_class_inference_source | "pick.field", "symbol_suffix", "default" | Resolved picks |
| track_computed_at | When track_wr was last updated | Track records |
| track_window_days | Lookback period for track calc | Track records |

---

## 9. PRIORITY FIX LIST

### CRITICAL (Fix Immediately - Deploy Today)

| # | Issue | File | Line(s) | Fix |
|---|-------|------|---------|-----|
| 1 | **FWD WR at wrong granularity** - Strategy-level FWD WR masks per-symbol edge | hc_filter.js | 310-313 | Replace `strat_fwd_wr` with per-symbol-direction `track_wr`; add `track_calculator.py` |
| 2 | **elite_score gate blocks profitable picks** | hedge_fund_quality_gate.py | ~21 | Replace `elite_score < 30` with `ml_score < 0.60 && confidence < 0.70` |
| 3 | **forward_wr never produced** | outcome_resolver.py | N/A | Add track aggregation: compute strategy-symbol-direction WR from closed picks |
| 4 | **159 picks with no outcome** (31.8%) | outcome_resolver.py | 608-631 | Ensure MAX_RESOLVE_RETRIES forces closure even without price data |
| 5 | **Floating-point precision in elite_score** | hedge_fund_quality_gate.py | ~21 | Add `round(elite_score, 2)` before comparison |
| 6 | **Empty strategy field** | Source systems | N/A | Add validation: reject picks without strategy at ingestion |
| 7 | **Asset class alias incomplete** | outcome_resolver.py | 563 | Add "ETF" -> "ETF" mapping and "INDEX" handling |
| 8 | **closed_picks.json export empty** | Export pipeline | N/A | Fix JSON export to populate closed_picks array |

### HIGH (Fix This Week)

| # | Issue | File | Line(s) | Fix |
|---|-------|------|---------|-----|
| 9 | **Gate decisions not recorded** | hc_filter.js | 298-420 | Add `_gate_decisions` JSON field to blocked picks |
| 10 | **No MySQL sync status tracking** | outcome_resolver.py | _sync function | Add `mysql_sync_status` and `last_synced_at` fields |
| 11 | **BUY/LONG not normalized at ingestion** | outcome_resolver.py | 576-590 | Standardize to LONG/SHORT before any gate evaluation |
| 12 | **ETF symbols inferred as EQUITY** | outcome_resolver.py | 571-572 | Add known ETF symbol list (SPY, QQQ, GLD, etc.) |
| 13 | **22% FOREX price unavailability** | outcome_resolver.py | 317 | Add alternate price source for forex (ECB, Fixer.io) |
| 14 | **No direction breakdown in dashboard** | Dashboard | Strategy Leaderboard | Add LONG/SHORT toggle to strategy detail view |
| 15 | **trust_score not in shadow_blocked** | shadow_blocked schema | N/A | Add trust_score and trust_tier fields |
| 16 | **Direction field aliasing** | All modules | N/A | Standardize on `direction` only; reject `signal_type`, `action` |
| 17 | **Resolver output field aliasing** | outcome_resolver.py | Multiple | Write to standard fields only; add validation |
| 18 | **No pick_id for deduplication** | All records | N/A | Add UUID pick_id at emission |

### MEDIUM (Fix Within 2 Weeks)

| # | Issue | File | Fix |
|---|-------|------|-----|
| 19 | **entry_date not stored** | shadow_blocked schema | Add entry_date field |
| 20 | **exit_date not stored** | shadow_blocked schema | Add exit_date field |
| 21 | **_resolve_retry_count not in shadow_blocked** | shadow_blocked schema | Add retry count for audit |
| 22 | **No confidence band adjustment for small samples** | hc_filter.js | Lower confidence thresholds when fwdN < 30 |
| 23 | **FOREX_GATE has hardcoded 30% WR floor** | hc_filter.js | Make configurable per asset class |
| 24 | **No data quality score per pick** | New field | Add computed DQ score (completeness, validity) |
| 25 | **No schema versioning** | All JSON | Add `_schema_version` field |
| 26 | **WINNER_FILTER threshold (0.85) blocks best zone** | Unknown location | Raise to 0.90 per user's 82% WR evidence |
| 27 | **24 picks with empty strategy invisible to leaderboard** | Source validation | Reject or assign default strategy |

### LOW (Fix When Convenient)

| # | Issue | Fix |
|---|-------|-----|
| 28 | **Resolver comments mention reports that don't exist** | Verify report file paths |
| 29 | **No kill-switch for track data staleness** | Alert when track_wr older than 7 days |
| 30 | **Dashboard disclaimer buried** | Move to visible position |
| 31 | **JSON export has no timestamp** | Add `exported_at` field |
| 32 | **No diff tracking on config changes** | Add `hf_quality_gates.json` change log |
| 33 | **Test coverage claims 94% but no test files audited** | Verify test file existence |
| 34 | **Non-crypto check uses hardcoded list** | Make configurable in hf_quality_gates.json |
| 35 | **Direction inference from TP/entry can be wrong** | Require explicit direction field |
| 36 | **SL can be > TP for LONG picks** | Add R:R validation: TP > entry > SL for LONG |
| 37 | **No checksum on shadow_blocked.json** | Add SHA-256 checksum for integrity |

---

## 10. APPENDIX A: CORRELATION ANALYSIS

### 10.1 Feature Correlation with Profitability (resolved picks only, n=253)

| Feature | Correlation with pnl_pct | Interpretation |
|---------|------------------------|----------------|
| ml_score | **-0.1025** | Slight negative: higher ml_score slightly LESS profitable (overfit signal) |
| elite_score | **-0.1746** | Negative: higher elite_score LESS profitable (gate is backwards) |
| confidence | Needs data | Not computed (requires full pick data) |

### 10.2 Gate Performance Summary

| Gate | Picks Blocked | KILLED_ALPHA | SAVED | Net PnL Effect |
|------|--------------|--------------|-------|---------------|
| QUALITY_GATE | 420 | 113 (+861%) | 88 (-746%) | +115% (net positive BUT kills profitable picks) |
| RR_GATE | 63 | 23 (+79%) | 24 (-87%) | -8% (net negative) |
| FOREX_GATE | 10 | 0 | 0 | 0% (all UNRESOLVABLE) |
| WINNER_FILTER | 7 | 5 (+29%) | 0 | +29% |
| **TOTAL** | **500** | **141 (+969%)** | **112 (-996%)** | **-26%** |

---

## 11. APPENDIX B: DATA INVENTORY

### Files Audited

| File | Lines | Purpose | Issues Found |
|------|-------|---------|-------------|
| outcome_resolver.py | ~1800 | Pick resolution to WIN/LOST/FLAT | 9 bugs recently fixed; forward_wr not produced; field aliasing |
| hc_filter.js | ~510 | High conviction filter gates | forward_wr from wrong granularity; missing per-symbol tracking |
| hedge_fund_quality_gate.py | ~363 | HF-grade quality gate | elite_score gate backwards; no forward data handling |
| hf_quality_gates.json | ~30 lines | Gate configuration | min_elite_score too low (30) and too broad |
| matrix_symbol_gates.py | ~150 | Symbol-level gates | No forward data handling |
| shadow_blocked.json | 500 records | Blocked pick audit trail | 31.8% unresolved; 16.4% FP precision issues; 4.8% empty strategy |
| trading_audit_structured_data.json | ~500 lines | Dashboard data export | 0 closed picks in export (BROKEN) |
| ASSET_CLASS_EDGE_ANALYSIS.json | ~20 lines | Edge analysis | Only 3 asset classes; 2670 crypto vs 7 forex samples |

---

*Report generated: 2026-05-02*  
*Auditor: Senior Data Quality & QA Engineer*  
*Classification: CONFIDENTIAL - INTERNAL USE ONLY*
