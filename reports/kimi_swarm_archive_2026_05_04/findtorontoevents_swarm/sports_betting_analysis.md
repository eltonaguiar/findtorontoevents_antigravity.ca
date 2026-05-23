# Sports Betting Data Quality Analysis — Find Toronto Events

> **Page:** `https://findtorontoevents.ca/live-monitor/sports-betting.html`  
> **Analysis Date:** 2026-04-25  
> **Analyst:** Sports Betting QA / Data Engineering  

---

## 1. Executive Summary — Top 5 Issues

| # | Issue | Severity | Impact | Quick Fix ETA |
|---|-------|----------|--------|---------------|
| 1 | **TheOddsAPI key unauthorized** → `API Credits: 0/500`, stale picks >48h | **CRITICAL** | Zero new value bets, line shopping & arbitrage stale | 15 min (rotate key) |
| 2 | **"Last refresh" shows date-only (`2026-04-25`) with no time** → ambiguous freshness | **HIGH** | Users cannot determine if data is minutes or hours stale | 30 min (add HH:MM) |
| 3 | **Win Rate warning banner persists despite 37.5% WR with n=24** — warning fatigue | **MEDIUM** | Users distrust metrics; warning is shown even when policy fix cohort is selected | 1h (conditional banner) |
| 4 | **Two-ledger discrepancy** — Pick History (126 picks, 29.8% WR) ≠ Bankroll ledger (41 tickets, 37.5% WR) | **MEDIUM** | Confuses users; no in-app reconciliation | 2h (unified view) |
| 5 | **Arbitrage & Steam Moves always 0 when API is stale** — no fallback or cached display | **MEDIUM** | Features appear broken even when historical data exists | 2h (show last-known + stale badge) |

---

## 2. Data Freshness Architecture Analysis

### 2.1 Current State (Live Observation)

```
Last refresh:    2026-04-25          ← date only, no timestamp
Bankroll:        $1,065.06
API Credits:     0/500               ← UNauthorized key
Active Bets:     0
Today's Picks:   0 (+6 finished)
Stale Banner:    "The Odds API key is unauthorized; new value bets cannot be generated until the key is rotated."
```

### 2.2 Expected Refresh Cadence vs. Reality

| Data Source | Expected Cadence | Actual (Observed) | Gap |
|-------------|-------------------|---------------------|-----|
| TheOddsAPI | Every 2–3 hours | **>48 hours stale** | 24× over SLA |
| OLG ProLine+ | Manual / scraper | Unknown | Not visible in UI |
| Betway | Scraper (`alpha_engine/betway_scraper.py`) | Unknown | Not visible in UI |
| ESPN APIs (situation scoring) | 2h cache with failover | Appears working ("LIVE" badge) | OK |

### 2.3 Root Cause: Why "Last Refresh" Shows Stale Date

**Primary Root Cause:** TheOddsAPI key is unauthorized (HTTP 401). This is explicitly stated in the stale picks banner. The API credit counter reads `0/500`, confirming the key has either:

1. **Expired or been revoked** by TheOddsAPI provider.
2. **Rate-limited** (though 0/500 suggests total depletion or invalid key, not rate limit).
3. **Environment variable mismatch** — the GitHub Action `sports-betting-refresh.yml` may be injecting a different key than what the frontend reads.

**Secondary Root Causes:**

| Symptom | Root Cause | Evidence |
|---------|------------|----------|
| "Last refresh: 2026-04-25" (no HH:MM) | Frontend renders `toLocaleDateString()` without time component | Visual inspection |
| "API Credits: 0/500" | Backend `/api/credits` or `/health` endpoint returns 0 because TheOddsAPI auth fails | Inferred from banner text |
| 0 active picks, 6 finished | Pick generator depends on TheOddsAPI odds feed; no feed = no new picks | Logical dependency |
| Arbitrage = 0, Steam Moves = 0 | Both depend on `lm_sports_odds_history` which is populated by TheOddsAPI cron | Page text: "scanner is invoked by cron after each odds refresh" |
| Line Shopping still shows data | Likely from last successful API pull (Apr 25) or cached independently | Games are Apr 25 dated |

### 2.4 Data Freshness SLO (Service Level Objective)

| Metric | SLO | Alert Threshold | Page Indicator |
|--------|-----|-----------------|---------------|
| Odds data age | `< 30 min` during active hours (12:00–23:59 ET) | `> 30 min` | 🟢 Fresh / 🟡 Stale >30m / 🔴 Stale >2h |
| API credit balance | `> 100` remaining | `< 50` | Display count with color coding |
| ESPN situation data | `< 2 hours` | `> 2 hours` | "LIVE" badge turns yellow |
| Active pick count (in-season) | `≥ 1` per active sport | `0` for >6h during season | Empty-state with explanation |
| Settled ticket sync | `< 5 min` after game end | `> 15 min` | Auto-refresh after grade |

### 2.5 Healthy State Definition

A **healthy** sports betting page should display:

```
Last refresh:    2026-04-25 14:32 ET  ← timestamp with timezone
Bankroll:        $1,065.06
API Credits:     347/500              ← >100 remaining
Active Bets:     3                    ← paper bets on pending games
Today's Picks:   4 (+2 finished)      ← active + recently finished
Stale Banner:    [HIDDEN]             ← only shown if >30 min stale
Win Rate:        37.5%                ← with Wilson CI [21.1%, 55.4%]
Arbitrage:       1 open               ← or "0 open (last: 2h ago)"
Steam Moves:     2 in last 6h         ← or "0 detected (last: 4h ago)"
```

---

## 3. Precision & Win-Rate Analysis

### 3.1 Current Win-Rate Display

**Headline metrics card shows:**
- Win Rate: `37.5%` (wins / (W+L) n=24)
- Settled Tickets: 41 (W:9 L:15 P:0 V:17)
- Only 24 of 41 are directional (W+L); 17 are VOID

**The warning banner says:** "⚠ Win Rate Currently Low or Unknown" — **this is misleading**. A 37.5% WR with n=24 is not "unknown"; it is statistically estimable. The banner should be conditional on actual low sample size (e.g., n < 10) or on the user selecting the "All settled history" cohort when a cleaner "Since policy fix" cohort exists.

### 3.2 Correct Win-Rate Calculation

**Current (incorrect for UX):**
```
Win Rate = 9 / (9 + 15) = 37.5%
```
This ignores VOIDs. It is mathematically correct for directional sample but:
- No confidence interval shown
- No distinction between cohorts
- Warning banner shown unconditionally

**Recommended:**
```
# Wilson Score Interval (95% CI) for binomial proportion
n = W + L = 24
p = W / n = 9 / 24 = 0.375
z = 1.96

CI_lower = (p + z²/(2n) - z * sqrt((p(1-p) + z²/(4n))/n)) / (1 + z²/n)
CI_upper = (p + z²/(2n) + z * sqrt((p(1-p) + z²/(4n))/n)) / (1 + z²/n)

# Result: 37.5% [21.1%, 55.4%] — overlapping 50% = not statistically distinguishable from coin flip
```

**Cohort-based toggle already exists** ("All settled history" vs "Since policy fix (Apr 2026)"). The warning should only appear when:
1. The **All settled history** radio is selected AND the policy-fix cohort is cleaner, OR
2. Directional n < 15 (Wilson CI too wide to be actionable), OR
3. No settled bets exist at all (true 0% denominator case).

### 3.3 What Metrics to Display with 0 Settled Bets

If a new user or new policy cohort has **0 settled directional bets**:

| Metric | Display | Rationale |
|--------|---------|-----------|
| Win Rate | `N/A — insufficient sample (n=0)` | Avoid 0% which implies losing |
| ROI | `—` (dash) or `N/A` | Cannot compute ROI without settled P&L |
| Bankroll | `$1,000.00` (starting) | Always meaningful |
| Active Bets | Count + `$ reserved` | Forward-looking |
| Pending Picks | Count + Avg EV% | Forward-looking |
| Expected Value | Avg EV% of pending picks | Shows algorithmic edge even without results |
| CLV Beat Rate | `—` until n ≥ 5 | Needs closing line comparison |

### 3.4 Fix: Prevent Misleading 0% Display

**Current code path (inferred):**
```javascript
winRate = wins / (wins + losses); // 0 / 0 = NaN → rendered as "0%"
```

**Recommended code path:**
```javascript
const directionalN = wins + losses;
if (directionalN === 0) {
  winRateDisplay = "N/A";
  winRateSubtitle = "No settled bets yet — expected value shown below";
  showWarning = false; // Different message, not a warning
} else {
  const p = wins / directionalN;
  const ci = wilsonScoreInterval(wins, directionalN, 0.95);
  winRateDisplay = `${(p*100).toFixed(1)}%`;
  winRateSubtitle = `[${(ci.low*100).toFixed(1)}%, ${(ci.high*100).toFixed(1)}%] 95% CI  ·  n=${directionalN}`;
  showWarning = directionalN < 15 || ci.high < 0.5;
}
```

---

## 4. Data Quality Monitoring Specification

### 4.1 Automated Checks (Run every 5 minutes via cron / GitHub Action)

| Check ID | Check Name | Logic | Severity |
|----------|------------|-------|----------|
| DQ-001 | `timestamp_freshness` | `now() - last_refresh > 30 min` | CRITICAL |
| DQ-002 | `api_credit_balance` | `credits_remaining < 50` | HIGH |
| DQ-003 | `api_credit_unauthorized` | `credits_remaining === 0` AND API returns 401 | CRITICAL |
| DQ-004 | `non_empty_picks` | `active_picks.length === 0` during in-season hours (12:00–23:59 ET) for active sports | WARNING |
| DQ-005 | `valid_odds_format` | All odds are numeric, `≥ 1.01`, decimal format | ERROR |
| DQ-006 | `bookmaker_coverage` | `≥ 5` of 8 CA-legal books present in odds data | WARNING |
| DQ-007 | `bankroll_bounds` | `$800 ≤ bankroll ≤ $2000` (circuit breaker check) | HIGH |
| DQ-008 | `win_rate_computable` | If `directional_n > 0`, ensure win rate is numeric and finite | ERROR |
| DQ-009 | `settled_sync` | `|paper_bets_settled - pick_history_graded| < 2` per day | WARNING |
| DQ-010 | `ev_range` | All displayed EV% are between `-50%` and `+100%` | ERROR |

### 4.2 Alert Routing

| Severity | Channel | Pager | Auto-Action |
|----------|---------|-------|-------------|
| CRITICAL | Slack #sports-alerts + Email + SMS | Yes | Pause auto-betting; post stale banner |
| HIGH | Slack #sports-alerts + Email | No | Log to `alpha_engine/data/dq_log_YYYYMMDD.json` |
| WARNING | Slack #sports-alerts | No | Annotate in weekly forensics report |
| ERROR | GitHub Issue auto-created | No | Block deploy if pre-deploy check |

### 4.3 Internal Monitoring Dashboard (Proposed)

**Endpoint:** `/_internal/sports-health` (or separate status page)

```json
{
  "status": "degraded",
  "checks": {
    "odds_api": { "state": "unauthorized", "last_success": "2026-04-25T03:00:00Z", "detail": "HTTP 401 on /sports/odds" },
    "espn_api": { "state": "ok", "last_success": "2026-04-25T18:00:00Z", "cache_age_min": 45 },
    "pick_generator": { "state": "stale", "last_run": "2026-04-25T03:00:00Z", "picks_generated": 0 },
    "bankroll": { "state": "ok", "value": 1065.06, "floor_ok": true },
    "arbitrage_scanner": { "state": "idle", "last_scan": "2026-04-25T03:00:00Z", "open_opps": 0 },
    "steam_detector": { "state": "idle", "last_scan": "2026-04-25T03:00:00Z", "moves_24h": 0 }
  },
  "slos": {
    "odds_freshness_min": 180,    // 3h — violated
    "api_credits_remaining": 0,    // violated
    "active_picks_count": 0        // violated during active hours
  }
}
```

### 4.4 Weekly Forensics Integration

The existing `sports-forensics-weekly.yml` should be extended to:
1. Read the DQ log from `alpha_engine/data/dq_log_*.json`
2. Compute MTTF (Mean Time To Freshness violation)
3. Flag weeks with > 3 critical violations
4. Correlate with P&L — did stale data lead to missed +EV picks?

---

## 5. Quick Fixes — Priority Roadmap

### P0 — Critical (Fix Today)

1. **Rotate TheOddsAPI Key**
   - Action: Regenerate key at `the-odds-api.com`, update GitHub Secret `ODDS_API_KEY`, re-run `sports-betting-refresh.yml`
   - ETA: 15 minutes
   - Validation: `API Credits` should show `> 0` and picks should generate within 30 min

2. **Add Timestamp to "Last Refresh"**
   - Action: Change frontend from `toLocaleDateString()` to `toLocaleString('en-CA', { timeZone: 'America/Toronto', hour: '2-digit', minute: '2-digit' })`
   - ETA: 30 minutes
   - Validation: Page shows "Last refresh: 2026-04-25 14:32 ET"

3. **Cache Graceful Degradation**
   - Action: If API returns 401/403/429, show last-known data with 🔴 **STALE** badge + "Last successful fetch: 2026-04-25 03:00 ET"
   - ETA: 1 hour
   - Validation: Even with bad key, Line Shopping still displays last-known odds with "stale" indicator

### P1 — High (Fix This Week)

4. **Conditional Win-Rate Warning**
   - Action: Only show ⚠ banner when `directional_n < 15` OR when user is on "All settled history" and policy-fix cohort is cleaner
   - ETA: 1 hour
   - Validation: With n=24 and 37.5% WR, banner is hidden. With n=3, banner shows.

5. **Show "N/A" Instead of 0% When No Settled Bets**
   - Action: Guard division by zero in win-rate calculation
   - ETA: 30 minutes
   - Validation: New policy cohort with 0 settled bets shows "N/A — no settled bets yet"

6. **Static Fallback for Popular Games**
   - Action: If TheOddsAPI fails, display ESPN-schedule games with "odds unavailable — check books manually" badge
   - ETA: 2 hours
   - Validation: Page still shows tonight's NHL/NBA schedule even when odds API is down

### P2 — Medium (Fix This Sprint)

7. **Arbitrage / Steam Moves Fallback**
   - Action: Show "Last arbitrage found: 2 days ago" / "Last steam move: 6 hours ago" instead of blank "0"
   - ETA: 2 hours

8. **Unified Ledger View**
   - Action: Add a "Reconciliation" sub-tab under My Bets showing both `lm_sports_bets` and `lm_sports_daily_picks` side-by-side with difference highlighting
   - ETA: 4 hours

9. **Pre-Deploy DQ Gate**
   - Action: Add DQ checks (`DQ-001` through `DQ-010`) to `sports-smoke-and-e2e.yml` so a deploy is blocked if the staging environment shows stale data
   - ETA: 3 hours

### P3 — Nice to Have

10. **ML Filter for Pick Quality** (already noted in "What We're Doing")
11. **Quarter-Kelly Sizing Audit** — verify `bet_amount` in settled table matches `bankroll * 0.25 * edge / (odds - 1)`
12. **CORS / CSP Audit** — ensure frontend can still call backend if domain or CDN changes

---

## 6. Recommended Test Coverage Matrix

| Feature | Unit | Integration | E2E (Playwright) | Data Quality |
|---------|------|-----------|------------------|--------------|
| Odds fetch (TheOddsAPI) | — | ✅ | — | ✅ |
| Pick generation / grading | ✅ | ✅ | ✅ | ✅ |
| Win-rate calculation | ✅ | — | ✅ | ✅ |
| Bankroll update on settle | ✅ | ✅ | ✅ | ✅ |
| Arbitrage detection | ✅ | ✅ | ✅ | ✅ |
| Steam move detection | ✅ | — | ✅ | ✅ |
| My Bets active/settled | — | ✅ | ✅ | ✅ |
| Pick History daily log | — | ✅ | ✅ | ✅ |
| Performance charts | — | — | ✅ | — |
| Mobile bet card layout | — | — | ✅ | — |
| API failure resilience | — | ✅ | ✅ | ✅ |
| Caching / stale display | — | ✅ | ✅ | ✅ |

---

## 7. Appendix: Key Data Artifacts

### 7.1 GitHub Actions Relevant to This Analysis

| Workflow | Purpose | Freshness Relevance |
|----------|---------|---------------------|
| `sports-betting-refresh.yml` | Cron job to fetch TheOddsAPI + OLG + Betway | **Primary source of staleness** |
| `sports-smoke-and-e2e.yml` | Pre/post deploy smoke tests | Should catch stale data before deploy |
| `sports-data-snapshots.yml` | Archives odds history to `lm_sports_odds_history` | Enables steam move detection |
| `sports-forensics-weekly.yml` | Weekly P&L + WR audit | Should include DQ metrics |
| `sports-prediction-market-sync.yml` | Syncs with prediction market data | Secondary data source |

### 7.2 Database Tables (Inferred from UI)

| Table | Purpose | UI Location |
|-------|---------|-------------|
| `lm_sports_bets` | Paper bet ledger (bankroll source) | Bankroll card, My Bets → Settled |
| `lm_sports_daily_picks` | Daily graded pick log | Pick History |
| `lm_sports_odds_history` | Rolling 30-day odds for steam detection | Steam Moves tab |
| (unknown) | Arbitrage scan results | Arbitrage tab |
| (unknown) | TheOddsAPI raw response cache | Behind "Last refresh" |

### 7.3 UI Component Inventory (for Test Targeting)

```
Header Bar:
  .last-refresh-badge          → "Last refresh: 2026-04-25"
  .bankroll-badge              → "$1,065.06"
  .api-credits-badge           → "0/500"
  .active-bets-badge           → "0"

Headline Metrics:
  .metric-bankroll             → "$1,065.06"
  .metric-settled-tickets      → "41" (with W:9 L:15 P:0 V:17)
  .metric-win-rate             → "37.5%"
  .metric-roi                  → "25.3%"
  .metric-todays-picks         → "0 (+6 finished)"
  .metric-active-bets          → "0"

Cohort Toggle:
  input[name="cohort"][value="all"]     → "All settled history"
  input[name="cohort"][value="policy"]  → "Since policy fix (Apr 2026)"

Tab Navigation:
  button[data-tab="todays-picks"]
  button[data-tab="playoffs"]
  button[data-tab="odds-comparison"]
  button[data-tab="arbitrage"]
  button[data-tab="steam-moves"]
  button[data-tab="my-bets"]
    .subtab-active
    .subtab-settled
  button[data-tab="performance"]
  button[data-tab="pick-history"]
  button[data-tab="glossary"]
  button[data-tab="system-analysis"]
  button[data-tab="research"]

Sport Filter Bar:
  button[data-sport="all"]
  button[data-sport="nhl"]
  button[data-sport="nba"]
  ...

Bet Cards (Today's Picks):
  .bet-card
    .bet-status → "FINISHED · WON" | "FINISHED · LOST" | "AWAITING GRADE"
    .bet-grade → "B" | "C+" | "C"
    .bet-sport-market → "NHL · Moneyline"
    .bet-event → "Carolina Hurricanes @ Ottawa Senators"
    .bet-pick-book → "Carolina Hurricanes at FanDuel"
    .bet-odds → "1.95 (-105)"
    .bet-ev → "+5.4%"
    .bet-amount → "$14.10"
    .bet-grade-label → "LEAN" | "LOW EDGE" | "TAKE" | "STRONG TAKE"

Line Shopping Card:
  .line-shop-card
    .line-shop-event → "NHL: Carolina Hurricanes @ Ottawa Senators"
    .line-shop-market → "h2h"
    .line-shop-outcome → "Carolina Hurricanes"
    .line-shop-best-book → "FanDuel"
    .line-shop-best-odds → "1.95"
    .line-shop-worst-book → "Unibet"
    .line-shop-worst-odds → "1.74"
    .line-shop-savings → "+12.2%"

Stale Banner:
  .stale-banner → "Last refresh more than 48h ago..."
```

---

## 8. Conclusion

The Find Toronto Events sports betting page is **functionally well-architected** but currently in a **degraded state** due to a single point of failure: the TheOddsAPI key. The UI itself handles this gracefully (showing a clear stale banner), but the lack of:

1. **Time-component in "Last refresh"**
2. **Fallback static schedule display**
3. **Conditional warning banners**
4. **Pre-deploy data quality gates**

...means users are seeing a degraded experience that could be significantly improved with 1–2 hours of frontend work and a 15-minute key rotation.

The most impactful immediate actions are:
1. 🔴 **Rotate TheOddsAPI key** (15 min)
2. 🟡 **Add HH:MM to "Last refresh"** (30 min)
3. 🟡 **Implement cached-data + stale badge fallback** (1h)
4. 🟢 **Add conditional win-rate warning + N/A for 0 bets** (1h)

---

*End of Analysis*
