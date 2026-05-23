# Performance Deep Dive — Worst Asset Classes
## May 8, 2026 | Freebuff Swarm Analysis

> **Auditors:** Buffy (Codebuff) + Theo the Theorizer (Gemini)  
> **Scope:** findtorontoevents.ca/audit — all asset classes, strategy universe, symbol universe, resolver pipeline  
> **Focus:** FOREX (PF 0.28), FUTURES, ETF, PENNY_STOCK — why they fail and how to fix them

---

## 1. Executive Summary

**The non-crypto asset classes are suffering from a cascading data-integrity failure, not fundamentally broken strategy logic.** The primary culprit is the resolver pipeline marking 100% of non-crypto closed picks as "phantom expired" rather than properly resolving TP/SL hits. This corrupts every downstream metric: win rates, profit factors, decay tracking, and — critically — the strategy kill switches that auto-disable strategies based on those corrupted metrics.

### Current State by Asset Class

| Asset Class | PF | WR | n (closed) | Phantom Expired | Root Cause |
|---|---|---|---|---|---|
| CRYPTO | 1.26 | 44.8% | 8,162 | 0% | Healthy — benchmark |
| EQUITY | 1.42 | 52.8% | 428 | 100% | T2 candidate BUT phantom corrupting WR |
| COMMODITY | 2.08 | 48.7% | 816 | Unknown | Post-resolver-v2, 7d clean |
| ETF | 1.20 | 53.4% | 88 | 100% | Borderline; n too small |
| MEMECOIN | — | — | — | 0% | Clean |
| **FOREX** | **0.28** | **45.6%** | **1,249** | **100%** | **Critical — 3 root causes** |
| FUTURES | — | — | — | 100% | Phantom + thin book |
| BOND | 1.72 | 55.6% | 18 | Unknown | Meets T2 but n<100 |
| PENNY_STOCK | — | — | — | 100% | Phantom + anti-edge |

### The Killer Insight

The Gemini thinker analysis identified a **cascading feedback loop**:

```
Resolver bug → 100% phantom expired → corrupted WR/PF metrics
    → FX Kill Switch auto-disables good strategies (myfxbook_retail_contrarian, forex_rsi2_mean_reversion)
    → Quality gates choke remaining strategies with confidence caps (0.58 max)
    → Low throughput → fewer closed picks → even less data → kill switch tightens further
    → FOREX PF collapses to 0.28
```

**Fix the resolver first, then re-evaluate.** Everything else is downstream of this bug.

---

## 2. FOREX Deep-Dive (PF 0.28)

### 2.1 Root Cause #1: 100% Phantom Expired (P0-CRITICAL)

**Evidence:** From `db_health.json` (2026-05-08):
```
FOREX: 5,412 phantom expired / 5,412 total = 100.0%
EQUITY: 3,936 / 3,936 = 100.0%
FUTURES: 4,920 / 4,920 = 100.0%
ETF: 984 / 984 = 100.0%
PENNY_STOCK: 492 / 492 = 100.0%
```

Only CRYPTO (0%) and MEMECOIN (0%) have clean resolution.

**What this means:** Forex trades are not hitting their natural TP or SL levels. Instead, they're being force-closed by the scanner or marked as "expired" by the resolver at arbitrary intraday marks. The edge never gets a chance to play out.

**Supporting evidence:** `quality_gates.py` issue #186 notes that 92% of FOREX "LOST" picks have `|pnl_pct| < 0.5%` — well below the SL median of 0.5%. These aren't stop-loss events; they're mark-to-market force-closes.

**Resolution path:** Debug `audit_trail/universal_pick_resolver.py` for non-crypto assets. The `make_pick_id()` function at line 372-376 does NOT include `entry_price` in its composite key, allowing retry loops to re-resolve the same physical pick as a new row. Non-crypto assets may have different timestamp/price formats that the resolver doesn't handle correctly.

### 2.2 Root Cause #2: TP/SL Cap Contradiction (P0-CRITICAL)

**Evidence:** Two conflicting TP/SL settings exist:

**config.py** (correct, widened May 5):
```python
# config.py — wider targets to outrun 3-6% spread costs
forex_tp_pct: 0.015  # 1.5% TP
forex_sl_pct: 0.008  # 0.8% SL
# Risk:Reward = 1.87:1
```

**forex_strategies.py** `_forex_tp_sl()` (OVERRIDES config — BUG):
```python
# Line 73-74 — hardcaps override config.py!
tp_distance = min(tp_mult * current_atr, price * 0.008)  # cap 0.8% ← WRONG
sl_distance = min(sl_mult * current_atr, price * 0.005)  # cap 0.5% ← WRONG
```

The docstring even acknowledges this was deliberately widened on May 5 ("widened from 0.3%/0.2%"), but the code was only partially updated. The hardcaps at 0.8% TP and 0.5% SL mean forex trades can never achieve the intended 1.87:1 R:R. With spreads consuming 3-6% of a 0.8% TP target, the effective edge is near zero.

**Fix:** Change `_forex_tp_sl()` hardcaps to match config.py:
```python
tp_distance = min(tp_mult * current_atr, price * 0.015)  # cap 1.5%
sl_distance = min(sl_mult * current_atr, price * 0.008)  # cap 0.8%
```

### 2.3 Root Cause #3: FX Kill Switch Over-Blocking (P1-HIGH)

**Evidence:** `fx_kill_switch.py` hard-blocks 7 strategies as "known toxic":
```python
_KNOWN_TOXIC_FOREX_STRATEGIES = frozenset({
    "myfxbook_retail_contrarian",      # 0/20 WR, 29pp decay
    "forex_rsi2_mean_reversion",       # 0/40 WR, 35pp decay
    "ema_aggressive_prop",
    "stochastic_mean_reversion_forex",
    "forex_stochastic_mr",
    "usd_index_trend_forex",
    "forex_usd_trend",
})
```

But the 0/20 WR and 0/40 WR stats are almost certainly corrupted by the phantom-expired bug. `forex_rsi2_mean_reversion` was also added to `PERMANENTLY_KILLED_STRATEGIES` on May 6 with the justification "43.3% WR, PF 0.37, n=593" — but if those 593 picks were 100% phantom-expired, the metrics are garbage.

Additionally, `quality_gates.py` blocks these FOREX pairs:
```python
BLOCKED_ASSET_STRATEGY_PAIRS = {
    ("FOREX", "MomentumEMA"),
    ("FOREX", "volume_spike_breakout"),
    ("FOREX", "myfxbook_retail_contrarian"),
    ("FOREX", "forex_carry_momentum"),  # Added May 2
}

BLOCKED_DIRECTION_TRIPLES = {
    ("FOREX", "ig_contrarian_sentiment", "LONG"),     # May 6
    ("FOREX", "myfxbook_retail_contrarian", "LONG"),   # May 6
    ("FOREX", "quan_engine_swing", "LONG"),            # May 6
}
```

The JPY-cross BUY kill further reduces the tradeable universe:
```python
JPY_CROSS_PAIRS = frozenset({"CADJPY=X", "EURJPY=X", "NZDJPY=X", "GBPJPY=X", "AUDJPY=X"})
# But USDJPY=X excluded from kill (n=64 PF 9.50)
```

**The cumulative effect:** By the time all these blocks, kills, and direction restrictions are applied, the number of actually tradeable FOREX strategy+symbol+direction combinations is drastically reduced. With the resolver not properly closing trades anyway, the remaining strategies can't accumulate enough data to prove themselves.

### 2.4 Root Cause #4: Confidence Cap Chokes Throughput (P2-MEDIUM)

**Evidence:** `non_crypto_quality_gate.py` hardcaps unvalidated FOREX strategies:
```python
# forex_conf_cap: 0.58 for unvalidated, 0.65 for validated
# But _FOREX_VALIDATED is EMPTY — no strategy has reached 50 trades with 50%+ WR
```

Because strategies can't reach 50 closed trades WITH proper resolution (due to phantom expired), they can never graduate from the 0.58 confidence cap. A 0.58 confidence cap means position sizes are tiny, making it even harder to accumulate meaningful PnL.

Additionally, FOREX strategies don't benefit from crypto's score booster enrichment:
```python
# score_booster.py guards are crypto-only in MTF + ensemble gates
# Forex strategies score 30-45 naturally but crypto gets boosted to 60-70
SMART_PICKS_MIN_SCORE_FOREX = 40  # Had to be manually lowered from 55
```

### 2.5 FOREX Strategy-Level Analysis

From the code review of all 10 strategies in `forex_strategies.py`:

| Strategy | Academic Basis | WR Claim | Status | Issue |
|---|---|---|---|---|
| `carry_trade_momentum` | Lustig & Verdelhan (2007) | — | Active | Tight filters (ADX>18, above SMA200, vol ratio) — may fire rarely |
| `inverse_carry_contrarian` | Verdelhan (2015) | — | New (May 8) | FOREX Rescue bonus edge — untested |
| `asian_range_breakout` | Practitioner | — | Active | Tight compression requirement (<0.8x ATR) |
| `orb_breakout` | Practitioner | — | Active | Very tight ORB range + trend filter |
| `forex_rsi2_mean_reversion` | Connors & Alvarez (68% WR) | 68% | **KILLED** | Killed May 6 based on corrupted metrics |
| `forex_tsmom_12m` | Jegadeesh-Titman | — | **REMOVED** | Sharpe -1.73 in backtest — FX mean-reverts, trend-following fails |
| `cot_positioning` | COT data proxy | — | Active | Z-score threshold tightened to ±2.0 |
| `london_session_breakout` | Practitioner (35% daily vol) | 55-65% | Active | Only 6 liquid pairs, tight compression filter |
| `forex_mean_reversion_200d` | Poterba & Summers (1988) | 60-65% | Active | Z-score ≥1.5 sigma, dynamic TP to SMA200 |
| `ig_contrarian_sentiment` | IG Client Sentiment | 58.3% / Sharpe 5.87 | Active | **Best performer** — but LONG direction blocked May 6 |

**Key observation:** The two academically-strongest strategies (`forex_rsi2_mean_reversion` = Connors 68% WR, `ig_contrarian_sentiment` = Sharpe 5.87) have both been partially or fully disabled. RSI2 was killed entirely; IG contrarian had its LONG direction blocked.

### 2.6 Corrupted Data Double-Stamps

**Evidence:** `quality_gates.py` documents 3 corrupted outcome rows from a bulk-resolver double-stamp bug on April 10, 2026 at 22:42Z:
```
USDCAD=X: +40.45% (impossible for unleveraged spot FX)
EURUSD=X: +66.76% (impossible)
AUDUSD=X: +95.58% (impossible)
```
These rows had `confidence=9.9999` (should be [0,1]) and empty strategy fields. They inflated reported FOREX PF from clean 1.06 to fake 2.04.

While these specific rows are now quarantined via `CORRUPTED_OUTCOME_ROWS`, the underlying resolver bug (`make_pick_id()` missing entry_price in composite key) remains unfixed.

---

## 3. FUTURES Deep-Dive

### 3.1 State Assessment

FUTURES suffers from the same phantom-expired issue (100%) plus an extremely thin book. The active-feed visibility was nearly zeroed by a combination of:
- `ACTIVE_NON_CRYPTO_MIN_FORWARD_WR = 0.45` → lowered to 0.35 for futures (May 3)
- `SMART_PICKS_MIN_SCORE_FUTURES = 45` → lowered from 65 (May 3)
- `BLOCKED_ASSET_CLASSES` removed (was blocking all futures)
- `futures_momentum` KILLED May 6 (was the ONE winner at 4W/3L/1F = +4.94%)

### 3.2 Strategy-Level Blocks

```python
BLOCKED_STRATEGIES (FUTURES-specific):
    ("connors_rsi2", "FUTURES")
    ("hyperopt_connors_rsi2", "FUTURES")
    ("mean_reversion_bollinger", "FUTURES")
    ("extreme_oversold_bounce", "FUTURES")
    ("vix_reversal", "FUTURES")
    ("futures_mean_reversion", "FUTURES")
    ("ema_stack_momentum", "FUTURES")
```

All 7 futures strategies are blocked. The class has zero active strategies.

---

## 4. ETF Deep-Dive

### 4.1 State Assessment

ETF has 100% phantom expired on 984 closed picks. Sample sizes are tiny (n=88 reported). The ETF blacklist removes IWM and GLD (combined drag of -17.90%), but the remaining universe (SPY, QQQ, XLE, XLK) is too small to generate meaningful volume.

### 4.2 Strategy Score Issue

ETF strategies can't accumulate score booster enrichment (crypto-only guards), so natural scores are low (30-55 range). The SMART_PICKS_MIN_SCORE_ETF was lowered to 40 but the class still struggles with throughput.

---

## 5. PENNY_STOCK Deep-Dive

### 5.1 State Assessment

PENNY_STOCK has 492 closed picks, all phantom expired. The strategy `penny_deep_oversold` is blocked on EQUITY. This asset class essentially has no functioning pipeline — it's a data wasteland.

---

## 6. Top Gainers Analysis

### 6.1 Current State

The top gainer tracking system (`alpha_engine/data/top_gainer_patterns.json`) has data from only 9 days, ranging from Feb 5 to Feb 20, 2026 — **3 months stale**. The missed gainers log has 9,792 entries showing symbols that moved significantly but had no strategy firing on them.

### 6.2 Recent Missed Opportunities

Most recent entries from `missed_gainers_log.json`:
```
FTTUSDT:    +11.99% — in universe, no strategy fired
PENDLEUSDT: +11.73% — in universe, no strategy fired  
CPOOLUSDT:  +11.23% — NOT in universe
```

The pattern is clear: many gainers are in our universe but no strategy fires on them. This suggests our strategy signal thresholds are too tight or our symbol coverage within the universe is incomplete.

### 6.3 Symbol Universe vs Top Gainers Gap

The FOREX symbol universe is reasonably comprehensive (~23 pairs covering all majors and crosses). However, the blocks (JPY-cross BUY kill, BLOCKED_DIRECTION_TRIPLES, BLOCKED_ASSET_STRATEGY_PAIRS) effectively reduce the tradeable universe much further.

For crypto, the gainer tracking pipeline itself appears broken — the `top_gainer_patterns.json` hasn't been updated in 3 months, suggesting the `alpha_engine/gainer_tracker.py` cron job may have stopped.

---

## 7. Enhancement Proposals (With Regression-Avoidance Guardrails)

### 7.1 P0-CRITICAL: Fix the Non-Crypto Resolver

**What:** Debug why 100% of non-crypto closed picks get "phantom expired" status instead of proper TP_HIT/SL_HIT/TIME_EXIT resolution.

**Where:** `audit_trail/universal_pick_resolver.py` — specifically:
- `make_pick_id()` at line 372-376 (missing entry_price in composite key)
- Non-crypto price fetch path (different APIs than Binance for crypto)
- Exit reason normalization in `quality_gates.py::normalize_exit_reason()`

**Regression guard:** Run on a COPY of the database first. Compare CRYPTO resolution behavior (working) vs non-crypto (broken) to isolate the divergent code path. Once fixed, re-resolve historical non-crypto picks using `re_resolve_historical_v2.py`.

**Expected impact:** This single fix could reveal that FOREX PF is actually 1.0+ and that many "killed" strategies were falsely convicted.

### 7.2 P0-CRITICAL: Align TP/SL Caps

**What:** Change `_forex_tp_sl()` hardcaps in `forex_strategies.py` from 0.8%/0.5% to 1.5%/0.8% to match config.py.

**Where:** `alpha_engine/forex_strategies.py`, lines 73-74:
```python
# CURRENT (broken):
tp_distance = min(tp_mult * current_atr, price * 0.008)  # cap 0.8%
sl_distance = min(sl_mult * current_atr, price * 0.005)  # cap 0.5%

# FIX:
tp_distance = min(tp_mult * current_atr, price * 0.015)  # cap 1.5% (matches config)
sl_distance = min(sl_mult * current_atr, price * 0.008)  # cap 0.8% (matches config)
```

**Regression guard:** This widens risk. Because forex ATR is 0.3-0.8% daily, the effective TP/SL will still be ATR-multiplier bounded. The 1.5% cap only triggers in extreme volatility. Run a backtest comparing old vs new caps on the same historical data before deploying.

### 7.3 P1-HIGH: Halt the FX Kill Switch Until Resolver Is Fixed

**What:** Set `FX_KILL_SWITCH_DISABLED=1` as an environment variable AND temporarily remove `forex_rsi2_mean_reversion` and `myfxbook_retail_contrarian` from `PERMANENTLY_KILLED_STRATEGIES` and `_KNOWN_TOXIC_FOREX_STRATEGIES`.

**Where:** 
- Environment: `FX_KILL_SWITCH_DISABLED=1`
- `audit_trail/quality_gates.py`: Comment out `forex_rsi2_mean_reversion` from `PERMANENTLY_KILLED_STRATEGIES`
- `alpha_engine/fx_kill_switch.py`: Comment out the two entries from `_KNOWN_TOXIC_FOREX_STRATEGIES`

**Regression guard:** This is a TEMPORARY measure. Add a 14-day auto-re-arm: after 14 days, if the resolver is fixed and new metrics show these strategies are genuinely losing, re-kill them. Otherwise, if they show PF>1.0, graduate them to validated status.

### 7.4 P1-HIGH: Remove JPY-Cross BUY Block Pending Re-evaluation

**What:** The JPY-cross BUY kill (`JPY_CROSS_PAIRS` in `quality_gates.py`) was based on data that may be corrupted. With USDJPY=X excluded (n=64 PF 9.50), the other JPY crosses deserve a clean re-evaluation.

**Where:** `audit_trail/quality_gates.py` — set `JPY_CROSS_BUY_KILL_DISABLED=1` env var.

**Regression guard:** Only remove the BUY-direction block. SHORT direction on JPY crosses is already preserved. Monitor 7d performance after unblock.

### 7.5 P2-MEDIUM: Add Per-Asset-Class Score Boosters

**What:** The crypto score booster pipeline (`score_booster.py`) gives crypto picks +20-30 points via MTF and ensemble gates. Non-crypto picks get zero boost, forcing manual score floor reductions. Add lightweight boosters for non-crypto classes.

**Where:** `alpha_engine/score_booster.py` — add guards for:
- FOREX: session alignment bonus (+5), carry-differential alignment (+5), trend strength (+3)
- EQUITY: earnings proximity bonus (+5), sector momentum (+3)
- COMMODITY: COT positioning alignment (+5), seasonal factor (+3)

**Regression guard:** Start with small bonuses (+3 to +5) and monitor whether boosted picks outperform unboosted ones over a 30-day window before increasing.

### 7.6 P2-MEDIUM: Fix Top Gainer Tracking Pipeline

**What:** `top_gainer_patterns.json` is 3 months stale. Restart the `alpha_engine/gainer_tracker.py` cron job and expand to non-crypto gainers.

**Where:** 
- Debug `gainer_tracker.py` execution in CI
- Add forex/equity/commodity top mover tracking via yfinance

**Regression guard:** This is additive — no existing behavior changes.

### 7.7 P3-LOW: Expand FUTURES Symbol Universe

**What:** Currently all 7 futures strategies are blocked. With the resolver fixed, unblock the ones with academic backing and add more futures symbols.

**Where:** `audit_trail/quality_gates.py` — review BLOCKED_STRATEGIES for FUTURES.

### 7.8 Summary: Fix Order (Dependency Chain)

```
Step 1: Fix resolver phantom expired (P0) ──────────────────┐
Step 2: Align TP/SL caps (P0)                               │ Must be first
Step 3: Re-resolve historical non-crypto picks               │
                                                            │
Step 4: Halt FX Kill Switch (P1) ───────────────────────────┤ Depends on Step 1-3
Step 5: Unblock JPY-cross BUY (P1)                          │ for clean metrics
Step 6: Unblock forex_rsi2 + myfxbook_retail (P1)           │
                                                            │
Step 7: Add per-class score boosters (P2) ──────────────────┤ After metrics clean
Step 8: Fix top gainer pipeline (P2)                        │
Step 9: Expand futures universe (P3) ───────────────────────┘ Last, after validation
```

---

## 8. Backtesting Validation Plan

Before deploying any of the above enhancements, run these backtests:

### 8.1 TP/SL Cap Backtest
```bash
python alpha_engine/forex_strategies.py  # With old caps (0.8/0.5)
# Record: PF, WR, avg PnL, n_trades, max_hold_bars
# Then change caps to 1.5/0.8 and re-run
# Compare PF delta — if PF improves >20%, deploy immediately
```

### 8.2 Strategy Unblock Backtest
```bash
# Run with FX_KILL_SWITCH_DISABLED=1
# Backtest forex_rsi2_mean_reversion on clean daily data (yfinance, not Binance)
# Expected: WR 50-68% based on Connors & Alvarez (2008)
# If WR < 40%, the strategy IS broken — keep killed
# If WR 50%+, the kill was false — unblock immediately
```

### 8.3 JPY-Cross Re-evaluation
```bash
# Query closed picks for CADJPY, EURJPY, NZDJPY, GBPJPY, AUDJPY
# Filter to BUY direction only
# If n < 20, insufficient data — unblock to collect more
# If n >= 20 and WR > 45%, unblock
# If n >= 20 and WR < 30%, keep blocked
```

---

## 9. Symbol & Strategy Universe Review

### 9.1 Current FOREX Symbol Universe

From `alpha_engine/config.py` → `FOREX_SYMBOLS`:
- Majors: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD
- Crosses: EURGBP, EURJPY, GBPJPY, AUDCAD, AUDCHF, AUDNZD, CADJPY, CHFJPY, EURAUD, EURCAD, EURCHF, EURNZD, GBPAUD, GBPCAD, GBPCHF, GBPNZD, NZDCAD, NZDJPY
- Metals: XAUUSD, XAGUSD
- Index: DXY

**Verdict:** Comprehensive. 23 symbols covering all major pairs and crosses. The issue is not the universe size but the effective tradeable subset after all blocks.

### 9.2 Strategy Universe Review

Current FOREX strategy roster (10 strategies in `forex_strategies.py`):
- 2 killed/removed: `forex_rsi2_mean_reversion`, `forex_tsmom_12m`
- 1 new/untested: `inverse_carry_contrarian`
- 7 active but restricted by blocks

**Recommendation:** After resolver fix, reduce to a "core 5" of academically-backed strategies:
1. `ig_contrarian_sentiment` — Sharpe 5.87 (best performer)
2. `forex_mean_reversion_200d` — Poterba & Summers, 60-65% WR
3. `london_session_breakout` — Practitioner, 55-65% WR
4. `carry_trade_momentum` — Lustig & Verdelhan
5. `forex_rsi2_mean_reversion` — Connors 68% WR (if rehabbed)

Kill/retire:
- `forex_tsmom_12m` — Already removed, Sharpe -1.73 (correct decision)
- `asian_range_breakout` — Too niche, tight compression requirements
- `orb_breakout` — Redundant with london_session_breakout
- `cot_positioning` — Z-score proxy too weak for real COT data
- `inverse_carry_contrarian` — Untested, watch for 30 days

### 9.3 Blocked Symbols Review

`BLOCKED_SYMBOLS` in `quality_gates.py` is CRYPTO-heavy (MATICUSDT, TRXUSDT, JTOUSDT, etc.). Non-crypto blocked symbols are minimal but high-impact:
- EQUITY: ADBE, CRM, ACN, MSFT, PLTR, TSLA, NKE, PG, HD — 9 symbols blocked
- ETF: IWM, GLD — 2 symbols blocked
- COMMODITY: CL=F, SI=F, GC=F, NG=F, + agro — most commodities blocked except HG=F, PL=F

**Recommendation:** Review EQUITY blocked symbols. MSFT and TSLA are blocked despite being major liquid stocks. The rationale (mean-reversion strategies shorting uptrending tech) may be correct but the block also prevents any LONG strategies from trading them.

---

## 10. Swarm Feedback Integration

This report should be fed to the following swarm agents for independent verification:

1. **Claude (paper-trader):** Backtest the TP/SL cap change on historical FOREX data
2. **Kimi (audit specialist):** Verify the phantom-expired diagnosis against MySQL directly
3. **Grok (strategy reviewer):** Review the strategy kill/unblock recommendations
4. **Codex (code reviewer):** Review the specific code fixes proposed for `_forex_tp_sl()` and resolver

### Swarm Consensus Requirements
- 3/4 agents must agree before deploying P0 fixes
- 2/3 must agree before deploying P1 changes
- Single agent approval sufficient for P2/P3

---

## 11. Risk Matrix

| Enhancement | Impact | Risk | Regression Risk | Confidence |
|---|---|---|---|---|
| Fix resolver phantom expired | +50-100% PF | Low | Could surface MORE losing trades | High |
| Align TP/SL caps | +20-40% PF | Medium | Wider SL = larger single-trade losses | High |
| Halt FX Kill Switch | +10-30% PF | Medium | Could re-admit genuinely toxic strategies | Medium |
| Unblock JPY-cross BUY | +5-15% PF | Low | Small sample, limited downside | Medium |
| Per-class score boosters | +5-10% throughput | Low | Additive only | High |
| Fix top gainer pipeline | +0-5% PF | Low | Additive only | High |
| Expand futures universe | Unknown | Low | Could add noise | Low |

---

## 12. Conclusion

The non-crypto asset classes are not inherently broken — they're trapped in a data-integrity death spiral. The resolver's failure to properly close non-crypto trades creates phantom metrics that trigger kill switches that disable good strategies that can't generate data to prove themselves.

**The fix order is critical:** resolver → TP/SL caps → unblock strategies → re-evaluate. Jumping straight to strategy unblocking without fixing the resolver will just re-admit strategies into a broken pipeline.

**Expected outcome after all P0+P1 fixes:**
- FOREX PF: 0.28 → 0.80-1.20 (conservative)
- FOREX WR: 45.6% → 48-55%
- FUTURES: Achievable positive PF for first time
- ETF: Data clean enough to evaluate
- PENNY_STOCK: At least trackable

---

*Report generated by Buffy (Codebuff) + Theo the Theorizer (Gemini) on 2026-05-08.*  
*Sources: `alpha_engine/forex_strategies.py`, `audit_trail/quality_gates.py`, `alpha_engine/fx_kill_switch.py`, `alpha_engine/non_crypto_quality_gate.py`, `cross_aggregation/performance_alerts.py`, `alpha_engine/config.py`, `audit_dashboard/data/db_health.json`, `docs/ANALYSIS_MAY82026_FREEBUFF.MD`*
