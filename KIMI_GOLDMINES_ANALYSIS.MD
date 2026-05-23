# KIMI Goldmine Analysis Report

**Date:** February 10, 2026  
**Analyst:** Kimi Code CLI  
**Scope:** Complete audit of all goldmine/prediction tracking systems across findtorontoevents.ca

---

## Executive Summary

You have **5 separate goldmine systems**, not 1. They are fragmented, duplicative, and mostly incomplete. The most visually impressive one (Windsurf) has **zero actual data** flowing to it.

| System | Location | Status | Data Quality |
|--------|----------|--------|--------------|
| Live Monitor Goldmine | `/live-monitor/` | ⚠️ Legacy | ~28 picks, 8 sources |
| Goldmine Cursor | `/goldmine_cursor/` | ⚠️ Partial | Best coverage of stocks |
| Antigravity | `/investments/goldmines/antigravity/` | ⚠️ Partial | Frontend for Cursor |
| Windsurf | `/investments/goldmines/windsurf/` | 🔥 **Fake UI** | **ZERO DATA** |
| KIMI (new) | `/investments/goldmines/kimi/` | ✅ New | 28 picks, JSON-based |

**Recommendation:** Pick ONE system, add missing harvest functions, delete the others.

---

## Detailed System Analysis

### 1. Live Monitor Goldmine

**Location:** `/live-monitor/goldmine-dashboard.html`  
**API:** `/live-monitor/api/goldmine_tracker.php`  
**Workflow:** `.github/workflows/goldmine-tracker.yml`

#### Architecture
- PHP 5.2 compatible backend
- 6 database tables: `gm_unified_picks`, `gm_system_health`, `gm_failure_alerts`, `gm_sec_insider_trades`, `gm_sec_13f_holdings`, `gm_news_sentiment`
- GitHub Actions runs daily at 7 PM EST + 1 PM EST intraday
- Tracks outcomes with TP/SL checks
- Has health monitoring + alerts

#### Data Sources (8 total)

| Source | Table/API | Asset Type | Status |
|--------|-----------|------------|--------|
| Consolidated Picks | `consensus_tracked` | Stocks | ✅ Active |
| Live Signals | `lm_signals` | Multi-asset | ✅ Active |
| Edge Dashboard | `lm_opportunities` | Multi-asset | ✅ Active |
| Meme Coins | `mc_winners` (cross-DB) | Crypto | ✅ Active |
| Sports Betting | `lm_sports_daily_picks` (cross-DB) | Sports | ✅ Active |
| Horizon Picks | `horizon_picks.php` API | Stocks | ✅ Active |
| Top Picks | `report_cache` | Stocks | ✅ Active |
| Penny Stocks | `penny_stocks.php` API | Stocks | ✅ Active |

#### Critical Gaps
- ❌ **NOT harvesting from `stock_picks`** (55+ individual algorithms)
- ❌ **NOT harvesting forex** (`fx_signals`, `fxp_pair_picks`)
- ❌ **NOT harvesting mutual funds** (`mf_selections`, `mf2_fund_picks`)
- ❌ **NOT harvesting crypto pairs** (`cp_signals`, `cr_pair_picks`)
- ❌ **CAN SLIM** methodology idle (0 picks)
- ❌ **ML Ensemble** idle (0 picks)

---

### 2. Goldmine Cursor

**Location:** `/goldmine_cursor/`  
**API:** `/goldmine_cursor/api/harvest.php`  
**Tables:** `goldmine_cursor_predictions`

#### Architecture
- PHP 5.2 compatible
- INSERT-only prediction ledger
- UUID-based prediction IDs (MD5 hash)
- Resolves outcomes via price data

#### Data Sources (4 total)

| Source | Table | Asset Type | Status |
|--------|-------|------------|--------|
| Stocks | `stock_picks` | Stocks | ✅ **ONLY system tracking 55+ algos** |
| Sports | `lm_sports_daily_picks` | Sports | ✅ Active |
| Crypto | `crypto_picks` | Crypto | ⚠️ Conditional (table may not exist) |
| Forex | `forex_picks` | Forex | ⚠️ Conditional (table may not exist) |

#### Key Insight
This is the **ONLY** system harvesting from `stock_picks` table, which contains predictions from 55+ individual algorithms. This is your most valuable data source that's being completely missed by other goldmines.

#### Critical Gaps
- ❌ **NOT harvesting mutual funds**
- ❌ **NOT harvesting meme coins**
- ❌ **NOT harvesting consensus picks**
- ❌ No health monitoring system
- ❌ No alerts framework

---

### 3. Antigravity Goldmine

**Location:** `/investments/goldmines/antigravity/`  
**API:** `/investments/goldmines/antigravity/api/unified_predictions.php`

#### Architecture
- Frontend dashboard for Goldmine Cursor data
- Uses `goldmine_cursor_predictions` table
- Provides leaderboard, hidden winners, system summary

#### Endpoints
- `?action=leaderboard` - Algorithm rankings
- `?action=hidden_winners` - Elite performers (55%+ WR, 30+ trades)
- `?action=system_summary` - Performance by system
- `?action=risk_dashboard` - Risk metrics

#### Status
Effectively a frontend layer on top of Goldmine Cursor. No independent data collection.

---

### 4. Windsurf Goldmine

**Location:** `/investments/goldmines/windsurf/`  
**Backend:** ❌ **NONE** (pure HTML/CSS/JS)

#### The Problem
This is the most visually impressive dashboard but has **NO ACTUAL DATA** flowing to it.

#### Hardcoded Claims (Not Real)
```
- "9 Prediction Engines" - Most are dead
- "15 GitHub Actions" - Many not feeding data  
- "119 API Endpoints" - Not integrated
- "636+ Assets Tracked" - False claim
- "10m Scan Frequency" - Only meme scanner runs this often
```

#### Active Alerts (Built-in)
```html
<div class="alert-bar critical">
  <strong>CAN SLIM:</strong> 0 picks imported — completely idle
</div>
<div class="alert-bar critical">
  <strong>ML Ensemble:</strong> 0 picks imported — no data flowing
</div>
<div class="alert-bar warning">
  <strong>Blue Chip Growth (tight):</strong> -29.89% return, 36.54% win rate
</div>
```

#### Verdict
**Delete this.** It's a pretty UI with no backend. The alerts are hardcoded admissions of failure.

---

### 5. KIMI Goldmine (Just Built)

**Location:** `/investments/goldmines/kimi/`  
**Client:** `kimi-goldmine-client.html`  
**Workflow:** `.github/workflows/kimi-goldmine-collector.yml`  
**Data:** `data/goldmine/unified_picks.json`

#### Architecture
- GitHub Actions-based (no server PHP needed)
- Commits data to JSON files in repo
- Client-side dashboard fetches from GitHub Raw
- PHP 5.2 compatibility issues with server version

#### Data Sources
- Database stock picks (limited)
- Meme coins (HAYDEN example)
- ESPN sports API

#### Status
- 28 picks total
- Fixed rendering issue (string vs number parsing)
- Completely separate from existing infrastructure
- **Redundant with existing systems**

---

## Coverage Matrix: What's Actually Being Tracked

| Asset Class | Table/Source | Live Monitor | Goldmine Cursor | Windsurf | Actual Status |
|-------------|--------------|--------------|-----------------|----------|---------------|
| **Stocks (consensus)** | `consensus_tracked` | ✅ | ❌ | ✅ | Tracked |
| **Stocks (55+ algos)** | `stock_picks` | ❌ | ✅ | ✅ | **ONLY Cursor** |
| **Stocks (CAN SLIM)** | Unknown | ❌ | ❌ | ❌ | **DEAD** |
| **Stocks (ML Ensemble)** | Unknown | ❌ | ❌ | ❌ | **DEAD** |
| **Meme Coins** | `mc_winners` | ✅ | ❌ | ✅ | Tracked |
| **Crypto Pairs** | `cp_signals`, `cr_pair_picks` | ❌ | ⚠️ | ✅ | Partial |
| **Forex** | `fx_signals`, `fxp_pair_picks` | ❌ | ⚠️ | ✅ | Partial |
| **Mutual Funds** | `mf_selections`, `mf2_fund_picks` | ❌ | ❌ | ✅ | **NOT TRACKED** |
| **Sports** | `lm_sports_daily_picks` | ✅ | ✅ | ✅ | Tracked |

**Key Finding:** You have 22+ prediction tools but only 5-8 are being tracked by any goldmine.

---

## Estimated Daily Pick Volume

| Category | Tools | Coverage | Est. Picks/Day |
|----------|-------|----------|----------------|
| **Stocks** | 15+ APIs/pages | ~10% | 100-500+ |
| **Crypto** | 2 tools | ~50% | 10-50 |
| **Forex** | 2 tools | 0% | 10-30 |
| **Mutual Funds** | 2 tools | 0% | 5-20 |
| **Sports** | 1 tool | 100% | 5-15 |
| **TOTAL** | **22+ tools** | **~10%** | **130-615+ picks/day** |

**You're tracking ~28-50 picks when you should be tracking THOUSANDS.**

---

## Recommendations

### Option A: Consolidate on Goldmine Cursor (RECOMMENDED)

Goldmine Cursor has the best architecture for expansion:
- Already harvests from `stock_picks` (your most valuable data)
- Clean INSERT-only ledger design
- UUID-based prediction tracking

**Action Items:**
1. ✅ Keep `/goldmine_cursor/` as THE goldmine
2. 🔧 Add harvest functions:
   - `consensus_tracked` (consolidated picks)
   - `mc_winners` (meme coins)
   - `fx_signals` / `fxp_pair_picks` (forex)
   - `mf_selections` / `mf2_fund_picks` (mutual funds)
   - `cp_signals` / `cr_pair_picks` (crypto pairs)
3. 🗑️ Delete `/investments/goldmines/kimi/` (redundant)
4. 🗑️ Delete `/investments/goldmines/windsurf/` (fake UI)
5. 🗑️ Delete `/investments/goldmines/antigravity/` (redundant frontend)
6. 🔀 Redirect `/live-monitor/goldmine-dashboard.html` to `/goldmine_cursor/`

**Effort:** 4-6 hours  
**Result:** Single source of truth with complete coverage

---

### Option B: Fix Live Monitor Goldmine

The original system has the most mature infrastructure:
- Health monitoring + alerts
- Outcome tracking with TP/SL
- Fundamentals enrichment (dividends, earnings)
- SEC data integration (13F, insider trades)

**Action Items:**
1. ✅ Keep `/live-monitor/` as THE goldmine
2. 🔧 Add harvest functions:
   - `stock_picks` (individual algorithms - CRITICAL)
   - `fx_signals` / `fxp_pair_picks` (forex)
   - `mf_selections` / `mf2_fund_picks` (mutual funds)
   - `cp_signals` / `cr_pair_picks` (crypto pairs)
3. 🗑️ Delete duplicate goldmines
4. 🔀 Update Windsurf to pull from Live Monitor API (or delete)

**Effort:** 6-8 hours  
**Result:** Most feature-complete system with full coverage

---

### Option C: Keep the Fragmented Mess (NOT RECOMMENDED)

**Current State Problems:**
- 5 different dashboards showing different data
- No single source of truth
- Windsurf showing fake "636+ assets"
- CAN SLIM and ML Ensemble completely dead
- KIMI goldmine duplicating effort
- Maintenance nightmare

---

## Database Schema Comparison

### Live Monitor (6 tables)
```
gm_unified_picks          - Main prediction archive
gm_system_health          - Daily performance snapshots
gm_failure_alerts         - Active alert system
gm_sec_insider_trades     - SEC Form 4 filings
gm_sec_13f_holdings       - Fund holdings
gm_news_sentiment         - News sentiment scores
```

### Goldmine Cursor (1 table)
```
goldmine_cursor_predictions - Main prediction ledger
```

### Antigravity (views)
```
v_algorithm_leaderboard   - Algorithm rankings
v_hidden_winners          - Elite performers
v_system_performance      - System summary
v_risk_dashboard          - Risk metrics
```

---

## GitHub Actions Workflows

| Workflow | Frequency | Purpose | Status |
|----------|-----------|---------|--------|
| `goldmine-tracker.yml` | Daily 7PM + 1PM | Archive, outcomes, health | ⚠️ Legacy but working |
| `kimi-goldmine-collector.yml` | Every 15 min | Collect predictions | ✅ New but redundant |
| `crypto-winner-scan.yml` | Every 15 min | Crypto scanning | ✅ Active |
| `meme-scanner.yml` | Every 10 min | Meme coin scanning | ✅ Active |
| `sports-betting-refresh.yml` | 5x daily | Sports odds | ✅ Active |
| `daily-stock-refresh.yml` | 2x daily | Stock refresh | ✅ Active |
| `daily-miracle-scan.yml` | Daily | Day trades | ✅ Active |
| `alpha-engine-daily-picks.yml` | Daily + Sunday | Alpha picks | ✅ Active |

---

## Missing Tables (Not Being Archived)

Based on schema analysis, these tables exist but are NOT being harvested:

| Table | Location | Description | Priority |
|-------|----------|-------------|----------|
| `stock_picks` | Main DB | 55+ algorithm predictions | **CRITICAL** |
| `fx_signals` | findforex2 | Forex signals | HIGH |
| `fxp_pair_picks` | findforex2/portfolio | Forex portfolio picks | HIGH |
| `mf_selections` | findmutualfunds | Mutual fund selections | MEDIUM |
| `mf2_fund_picks` | findmutualfunds2 | Mutual fund picks | MEDIUM |
| `cp_signals` | findcryptopairs | Crypto signals | HIGH |
| `cr_pair_picks` | findcryptopairs/portfolio | Crypto portfolio picks | HIGH |
| `alpha_picks` | Various | Alpha engine outputs | MEDIUM |
| `miracle_picks2` | findstocks | Miracle v2 scanner | MEDIUM |
| `miracle_picks3` | findstocks | Miracle v3 scanner | MEDIUM |

---

## Next Steps

1. **DECIDE:** Pick one goldmine system (recommend Goldmine Cursor or Live Monitor)
2. **AUDIT:** Run `harvest.php?debug=1` to see what's actually available
3. **ADD:** Missing harvest functions for uncovered tables
4. **DELETE:** The 4 duplicate/redundant goldmine systems
5. **VERIFY:** All 22+ prediction tools are being tracked

---

## Appendix: File Locations

```
/live-monitor/
  ├── goldmine-dashboard.html
  ├── goldmine-alerts.html
  └── api/
      ├── goldmine_tracker.php      (Main API)
      └── goldmine_schema.php       (6 tables)

/goldmine_cursor/
  ├── index.html
  └── api/
      ├── harvest.php               (Main harvester)
      ├── health_check.php
      ├── track_record.php
      └── weekly_scorecard.php

/investments/goldmines/
  ├── antigravity/
  │   ├── index.html
  │   └── api/
  │       └── unified_predictions.php
  ├── windsurf/
  │   └── index.html               (NO BACKEND)
  └── kimi/
      ├── kimi-goldmine-client.html
      ├── kimi-goldmine.html
      └── kimi_goldmine_collector.php

/.github/workflows/
  ├── goldmine-tracker.yml         (Live Monitor)
  └── kimi-goldmine-collector.yml  (KIMI)
```

---

**Report Generated:** February 10, 2026  
**Total Systems Analyzed:** 5  
**Total Data Sources Found:** 22+  
**Coverage:** ~10%  
**Recommendation:** Consolidate to 1 system
