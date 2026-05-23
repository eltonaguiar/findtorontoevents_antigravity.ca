# EQUITY Pick Generation Bottleneck Autopsy — 2026-05-19

**Scope:** Why does `asset_class_health.EQUITY` show n=5 resolved picks when the
circuit-breaker reports 55.1% WR on n=89?

**TL;DR Root Cause:** `stocks_rsi2_pullback` — the dominant EQUITY strategy (80% of
raw volume) — is listed in `BLOCKED_ASSET_STRATEGY_PAIRS` in
`audit_trail/quality_gates.py` (line 2707). This causes `_is_historical_blocked_pick()`
to filter 54 of 68 EQUITY closed picks out of the ac_breakdown aggregation,
collapsing the dashboard view to n=5. The block was justified at n=37/WR=38%
(2026-05-16) but MySQL now shows n=73 with WR=50.7% — above the 45% charter floor
and tracking toward T2.

---

## Data collected

### active_picks.json EQUITY snapshot
- 12 EQUITY picks in `alpha_engine/data/active_picks.json` (all OPEN)
- Strategies: `stocks_rsi2_pullback` ×10, `futures_connors_rsi2` ×1, `cta_cross_asset_tsmom` ×1

### MySQL trading_picks (EQUITY)
| Strategy | OPEN | WON | LOST | WR | Avg age (OPEN) |
|---|---|---|---|---|---|
| stocks_rsi2_pullback | 1,157 | 37 | 36 | **50.7%** | 39–53 days |
| stocks_ema_golden_cross | 191 | 0 | 2 | 0% | — |
| cta_cross_asset_tsmom | 106 | 0 | 0 | — | — |
| smart_money_accumulation | 58 | 0 | 6 | 0% | — |

**OPEN age issue:** 1,157 `stocks_rsi2_pullback` picks have been OPEN for 39–53 days.
Resolved picks close in 0–5 days (avg 0.6 days). The outcome resolver is not
processing `trading_picks` for these old OPEN rows. This is a second contributor to
low n.

### MySQL at_raw_picks EQUITY (30-day)
- Total raw EQUITY picks: 4,918 per 30 days
- Zero banned; 39 stale
- Pass rate to consensus: **~0%** (pick_flow shows `no_consensus` as top rejection)

### MySQL at_pick_flow_daily EQUITY
| Date | raw_emitted | rejected | consensus | Rejection reason |
|---|---|---|---|---|
| 2026-05-18 | 74 | 0 | **0** | — |
| 2026-05-17 | 86 | 0 | **0** | — |
| 2026-05-16 | 85 | 0 | **0** | — |
| 2026-05-12 | 222 | 120 | 0 | no_consensus |
| 2026-05-11 | 188 | 122 | 0 | no_consensus |

Since May 13, zero EQUITY consensus picks have been generated. Note that
`rejected_total=0` on May 16–18 with `consensus=0` suggests the aggregator is
**not running the consensus step at all** for EQUITY on those days, or the picks
arrive too late in the aggregation window.

### Dashboard: _is_historical_blocked_pick breakdown
Of 68 EQUITY closed picks in `alpha_engine/data/closed_picks.json`:
- **54 blocked** by `("EQUITY", "stocks_rsi2_pullback")` in `BLOCKED_ASSET_STRATEGY_PAIRS`
- **5 blocked** by `NVDA` in `BLOCKED_SYMBOLS`
- **4 blocked** by `smart_money_accumulation` in `PERMANENTLY_KILLED_STRATEGIES`
- **5 survive** → n=5 in dashboard, WR=20% (2W/3L)

### EQUITY allowlist vs. actual strategy emitters (7d)
| Strategy | Raw picks | In allowlist? |
|---|---|---|
| stocks_rsi2_pullback | 214 | **No** (blocked) |
| regime_mild_bear | 27 | No |
| smart_money_accumulation | 26 | Yes (but perm-killed) |
| regime_strong_bear | 18 | No |
| smart_money_consensus | 12 | Yes |
| stocks_ema_golden_cross | 3 | Yes |
| keltner-bounce | 1 | Yes |
| markov_zone_transition | 1 | Yes |

Only ~15 of ~340 EQUITY raw picks/week pass through an **allowlisted + non-killed**
strategy. Of those, none are reaching consensus (multiple sources must agree).

---

## Root Causes (ranked)

### RC-1: stocks_rsi2_pullback wrongly excluded from dashboard aggregate
**File:** `audit_trail/quality_gates.py` line 2707
**Evidence:**
- Block justified: n=37, WR=38%, PF=0.97 (2026-05-16)
- Current MySQL: n=73, WON=37, LOST=36, **WR=50.7%** — above 45% charter floor
- This one entry removes 54/68 EQUITY closed picks from the dashboard aggregate
- Restoring it would push EQUITY n: 5 → **59** (immediately thin_sample tier)

**Why n=59 and not 73:** The closed_picks.json only captures the 68 forward-tested
picks that the local resolver processed. MySQL has 1,157 OPEN picks that have never
been resolved (see RC-3).

### RC-2: Consensus pipeline generating 0 EQUITY picks since May 13
**Evidence:**
- `at_filter_log` shows `no_consensus` as only rejection reason
- `at_pick_flow_daily`: May 16–18 shows 74–86 raw picks, 0 rejected, 0 consensus
- `at_consensus_picks`: last EQUITY pick was May 12 (2 picks)
- The aggregator runs are completing (137 COMPLETED in 7 days) but producing 0 EQUITY consensus
- The regime_* strategies (regime_mild_bear, regime_strong_bear, etc.) are not in the
  EQUITY allowlist in `smart_picks_engine.py` (line 443–465) — they generate 27+18+13+1=59
  picks/week that go nowhere

**Immediate sub-cause:** The aggregator's consensus engine requires multiple source
systems to agree on the same symbol+direction. EQUITY sources (AlphaEngine=310,
smart_money=16, KIMI_ClawResearch=9) rarely overlap on the same symbol.

### RC-3: 1,157 OPEN picks sitting unresolved (39–53 days old)
**Evidence:** MySQL shows 1,157 `stocks_rsi2_pullback` OPEN picks from late March to early April
averaging 44 days old. Resolved picks in the same strategy close in avg 0.6 days (TP/SL hit).
The outcome_resolver is NOT processing `trading_picks` table rows for these old open positions.

This means ~1,157 picks worth of resolution data are invisible to the dashboard.
If even 50% resolve to WON, that's 578 EQUITY wins ready to surface.

---

## Top 3 Actionable Fixes

### Fix 1: Remove stocks_rsi2_pullback from BLOCKED_ASSET_STRATEGY_PAIRS (RC-1)
**File:** `audit_trail/quality_gates.py` lines 2702–2707  
**Change:** Delete or comment out the `("EQUITY", "stocks_rsi2_pullback")` entry.  
**Justification:** n=73 WON=37 LOST=36 WR=50.7% — block criteria (WR<45%, PF<1.0) no longer met.  
**Expected impact:** EQUITY dashboard n: 5 → 59 (thin_sample tier immediately), unblocking forward data flow.  
**Risk:** If the n=73 MySQL data is from before the block was imposed (picks created pre-May-16),
the real post-block WR may still be sub-floor. Mitigation: check closed_at dates.
**Also required:** Remove from the smart_picks_engine allowlist check — the strategy is already
in the EQUITY `allowlist` set (line 449) so picks WILL pass through once the historical block is lifted.

### Fix 2: Add regime_* strategies to EQUITY allowlist in smart_picks_engine.py (RC-2)
**File:** `alpha_engine/smart_picks_engine.py` lines 448–456  
**Change:** Add `"regime_accumulation"`, `"regime_mild_bull"`, `"regime_strong_bull"`,
`"regime_mild_bear"`, `"regime_strong_bear"` to the EQUITY `allowlist` dict.  
**Justification:** These strategies emit 408 raw EQUITY picks/month (largest non-rsi2 volume)
but are blocked at the allowlist gate before scoring. No historical stats available to
judge edge — they need to be admitted to accumulate data.  
**Expected impact:** +60 EQUITY raw picks/week reaching the scoring pipeline; consensus
probability rises as more strategies see the same symbols.  
**Risk:** Regime strategies may be poorly calibrated for equity; monitor WR for 30 days.
Low risk since they flow to score-gating first.

### Fix 3: Run outcome_resolver against trading_picks for stale OPEN picks (RC-3)
**File:** `alpha_engine/outcome_resolver.py` or new script  
**Change:** Query `trading_picks` where `category='EQUITY' AND status='OPEN'
AND created_at < NOW() - INTERVAL 7 DAY` and resolve via current price + TP/SL comparison.  
**Justification:** 1,157 OPEN picks age 39–53 days are never resolving. If TP/SL levels
were hit during this period, outcomes are lost forever.  
**Expected impact:** Could unlock 500–800 EQUITY resolved picks for dashboard scoring.
Even at the historical WR=50.7%, this would push EQUITY to n>500 (stable tier).  
**Risk:** Historical price lookup may be unavailable for old dates; be careful not to
assume picks are LOST just because they're old — use actual TP/SL price comparison.

---

## Expected pick volume after each fix

| Fix | Current n | After Fix | Status Tier |
|---|---|---|---|
| None (baseline) | 5 | — | insufficient_data |
| Fix 1 only | 5 | 59 | thin_sample |
| Fix 1 + Fix 2 | 5 | ~75–90 (30d) | thin_sample → candidate |
| All 3 fixes | 5 | 500+ | candidate → stable |

---

## Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| stocks_rsi2_pullback post-block WR actually sub-45% | Medium | Verify closed_at > 2026-05-16 in MySQL; n=only 3 post-block closes available — use PENDING_UNBLOCK_REVIEW not instant restore |
| regime_* strategies have poor edge on EQUITY | Medium | Shadow track (forward_test_only=True) for 30 days before hard-adding |
| Bulk resolver creates ghost rows from stale data | Low | Only resolve if TP or SL was definitively hit (price crossed threshold) |
| Removing block inflates WR with pre-block bad trades | Low | ac_breakdown already looks at pnl_pct > 0/< 0, not status; pre-block trades are already in closed_picks.json and counted |

---

## Reproducer commands

```bash
# Verify stocks_rsi2_pullback current stats in MySQL
python -c "
import mysql.connector
conn = mysql.connector.connect(host='mysql.50webs.com', user='ejaguiar1_stocks',
    password=os.environ['DB_PASS_STOCKS'], database='ejaguiar1_stocks', connection_timeout=15)  # REDACTED 2026-05-20: was hardcoded; use env var only
c = conn.cursor()
c.execute(\"SELECT status, COUNT(*), ROUND(AVG(pnl_pct),4) FROM trading_picks WHERE category='EQUITY' AND strategy='stocks_rsi2_pullback' GROUP BY status\")
print(c.fetchall())
"

# Verify the historical block is removing 54 picks
python -c "
import json, sys
sys.path.insert(0,'.')
from audit_trail.dashboard_generator import _is_historical_blocked_pick
with open('alpha_engine/data/closed_picks.json', encoding='utf-8', errors='replace') as f:
    closed = json.load(f)
eq = [p for p in closed if str(p.get('asset_class','')).upper()=='EQUITY']
blocked = [p for p in eq if _is_historical_blocked_pick(p)]
print(f'EQUITY blocked: {len(blocked)}/{len(eq)}')
"
```

---

## Recommended Priority Order

1. **P1 (today):** Move `stocks_rsi2_pullback` to `PENDING_UNBLOCK_REVIEW` with
   review date 2026-05-26. Do NOT restore immediately — use the mutation protocol.
   The n=3 post-block resolved picks are insufficient for a clean verdict.
2. **P1 (today):** Add regime_* strategies to EQUITY allowlist (shadow mode first).
3. **P2 (this week):** Write a stale-OPEN resolver script targeting EQUITY `trading_picks`
   rows older than 7 days using yfinance historical prices.
4. **P3 (ongoing):** Monitor EQUITY circuit_breaker daily until n≥50 is stable.

---

*Generated: 2026-05-19 by Claude Code equity autopsy agent*
*Sources: alpha_engine/data/closed_picks.json, audit_trail/quality_gates.py,*
*alpha_engine/smart_picks_engine.py, MySQL (trading_picks, at_raw_picks, at_consensus_picks,*
*at_pick_flow_daily, at_filter_log)*
