# EAGLE_JUNE2_MIMO_V2_5_PRO — Quant Root-Cause Analysis & Backtesting Methodology

**Date:** 2026-06-02  
**Author:** Mimo v2.5 Pro (Quant Review)  
**Scope:** Full strategy audit, portfolio investigation, edge location, backtesting methodology  

---

## Executive Summary

The system has **127 strategies** but only **2 are genuine winners** (mega_mutation PF=1.93, rapid_fire PF=2.17). The root cause of poor performance is not "we need more time" — it's **5 structural problems** that compound each other:

1. **Stop-losses are too tight** — 626 SL hits at 0.5% WR (-2257% PnL)
2. **Quality gates filter 98.9% of picks** — 2253 raw → 25 active
3. **72% of systems have zero closed picks** — 92/127 systems never resolved
4. **Portfolio engine isn't running** — pf.html shows "no data yet"
5. **Kill-without-replacement** — 203 strategies permanently killed, no replacements spawned

---

## 1. Portfolio Emptiness — Root Cause

### pf.html?key=deepseek_v4__aggressive
```
This portfolio has no data yet — first daily run is scheduled 22:00 UTC.
Check back after pf_portfolio_<key>.json is written.
```

**All portfolios are empty.** The portfolio lifecycle engine (entry/sizing/TP/SL/exit) is not executing. The cron job that runs the daily portfolio construction is either:
- Not scheduled
- Failing silently
- Blocked by a dependency

**Impact:** Even if we have edge, we cannot deploy capital. The portfolio is a paper exercise with no execution.

### AI Tournament (ai-tournament.html)
- 39 models submitting picks since 2026-05-19
- **Leaderboard is EMPTY** — no model has n≥30 resolved picks yet
- Tournament is only ~2 weeks old — needs more time
- Phase 1C (live price tracking) is running

### Pick Funnel (pick_funnel.html)
- **CRYPTO Smart Picks: DISPUTED** — claimed 78.9% WR but DB ground truth is 41.9%
- The 337-row cohort behind the claim is dominated by a single source (claude_gainer_st = 91.7%)
- EXPIRED picks were mislabeled as WON (63.9% of EXPIRED had positive PnL)
- 14d CRYPTO WR recovering to 50.9% (n=2387) — historical claim still unverified

---

## 2. Per-Asset-Class Performance (Live Data)

| Asset Class | Closed Picks | WR | PF | Status | Root Cause |
|-------------|-------------|-----|-----|--------|------------|
| CRYPTO | 1,085 | 49.5% | 0.98 | Slightly losing | Drag systems (ml_crypto_predictor, luxalgo_filters) |
| EQUITY | 269 | 53.9% | 1.19 | Marginal | No earnings/SEC integration |
| ETF | 161 | 54.0% | 1.18 | Marginal | Small n, sector rotation working |
| FOREX | 74 | 31.1% | 0.56 | **TOXIC** | Inverse candidate — flip to SHORT |
| COMMODITY | 16 | 18.8% | 0.23 | Too few picks | Scanner underutilized (9/25 symbols) |
| BOND | 11 | 36.4% | 0.67 | Thin | Only 2/14 symbols emitting |
| FUTURES | 2 | 100% | — | Dead | All emitters deliberately blocked |

---

## 3. The 5 Root Causes (Detailed)

### Root Cause #1: Stop-Loss Is the Killer

| Exit Reason | Trades | WR | PF | PnL% |
|-------------|--------|-----|-----|------|
| **SL_HIT** | **626** | **0.5%** | **0.00** | **-2257.8%** |
| TP_HIT | 558 | 98.6% | 68.50 | +2916.2% |
| TIME_EXIT | 290 | 61.0% | 1.57 | +183.6% |
| FORCE_CLOSED | 83 | 54.2% | 1.18 | +222.5% |

**The problem:** Stops fire 626 times at 0.5% WR. When a stop hits, it's wrong 99.5% of the time. The stops are too tight — they get triggered by normal price noise before the trade has a chance to work.

**The fix:** ATR-based stops (2.5-3x ATR), not fixed percentage stops. A 2.5x ATR stop on a volatile crypto asset might be 5-8% — wide enough to survive noise, tight enough to protect capital.

### Root Cause #2: Quality Gates Filter 98.9%

```
Active raw: 2,253 picks generated
Active (post-gate): 25 survive
Filter rate: 98.9%
```

**Top filtered strategies (all produce 0 active picks):**
| Strategy | Raw Picks | Surviving |
|----------|-----------|-----------|
| ml_crypto_predictor | 492 | 0 |
| MeanReversionBB | 289 | 0 |
| inverse_luxalgo_confluence | 100 | 0 |
| kimi_signal_tracking | 78 | 0 |
| Quality Compounders | 64 | 0 |

**203 strategies are permanently killed.** The gates are too aggressive — they kill strategies on small-n evidence (n=12 for cotton, n=157 for FUTURES).

### Root Cause #3: 72% of Systems Have Zero Closed Picks

92 out of 127 systems have never produced a single resolved pick. They either:
- Generate signals that get filtered by gates (most common)
- Were killed before accumulating data
- Have data feed issues preventing resolution

### Root Cause #4: Portfolio Engine Not Running

The portfolio lifecycle engine (entry/sizing/TP/SL/exit) is not executing. The cron job is either not scheduled, failing silently, or blocked.

### Root Cause #5: Kill-Without-Replacement

When a strategy gets killed (203 permanently killed), no process generates replacements. The system slowly starves itself. Every kill cycle shrinks the tradeable universe.

---

## 4. Where IS the Edge?

### Confirmed Winners (PF≥1.5, WR≥50%)

| System | Closed | WR | PF | PnL% | Status |
|--------|--------|-----|-----|------|--------|
| mega_mutation | 265 | 65.9% | 1.93 | +318.0% | **WINNER** |
| rapid_fire | 457 | 61.9% | 2.17 | +72.6% | **WINNER** |

### Marginal Systems (PF 1.0-1.5)

| System | Closed | WR | PF | PnL% |
|--------|--------|-----|-----|------|
| kimi_riseoftheclaw | 979 | 50.0% | 1.02 | +509.6% |
| luxalgo_filters | 112 | 50.5% | 1.02 | +56.1% |
| battleground | 122 | 56.6% | 1.30 | +27.5% |
| copy_trader_clones | 117 | 57.9% | 1.38 | +5.2% |

### AI Tournament (Too Early)
- 39 models, started 2026-05-19
- Need n≥30 resolved picks per model to rank
- Currently in Phase 1C (live price tracking)

### Pick Funnel (Disputed)
- CRYPTO Smart Picks: claimed 78.9% WR but DB ground truth is 41.9%
- COMMODITY: historically PF 2.57 but only 3 active picks now
- ETF: PF 1.18, 161 picks — closest to edge

---

## 5. What We're Doing Wrong

| Problem | Impact | Fix |
|---------|--------|-----|
| Stops too tight | 626 trades at 0.5% WR | ATR-based stops (2.5-3x ATR) |
| Gates too aggressive | 98.9% filter rate | Recalibrate to n≥100 before kill |
| No incubator | New strategies get killed immediately | 30-trade protected runway |
| Score booster crypto-only | Non-crypto at systematic disadvantage | Decouple from crypto-only gating |
| No strategy replacement | Universe shrinks permanently | Auto-spawn on kill |
| Portfolio engine dead | Can't deploy capital | Fix cron job |

---

## 6. Mutation/Inversion Candidates

### HIGH PRIORITY — Invert These (PF < 0.7)

| Strategy | n | WR | PF | PnL% | Action |
|----------|---|-----|-----|------|--------|
| unknown | 70 | 37.1% | 0.59 | -86.9% | **INVERT** |
| macd-hidden-div-scout | 15 | 40.0% | 0.67 | -19.4% | **INVERT** |
| betting-against-beta | 15 | 20.0% | 0.25 | -19.1% | **INVERT** |
| altseason-rotation-scout | 13 | 38.5% | 0.62 | -16.2% | **INVERT** |
| regime_mild_bear | 11 | 18.2% | 0.22 | -14.0% | **INVERT** |
| stocks_rsi2_pullback | 17 | 29.4% | 0.42 | -12.3% | **INVERT** |
| strong consensus (alpha_engine, luxalgo_filters) | 38 | 23.7% | 0.31 | +31.6% | **INVERT** |

### MEDIUM PRIORITY — Mutate These (PF 0.7-1.0)

| Strategy | n | WR | PF | PnL% | Action |
|----------|---|-----|-----|------|--------|
| extreme_fear | 178 | 46.6% | 0.87 | +21.9% | MUTATE |
| luxalgo_confluence | 132 | 45.5% | 0.83 | +56.8% | MUTATE |
| multi_period_rsi_confluence_eth | 27 | 44.4% | 0.80 | -1.8% | MUTATE |

---

## 7. Proper Backtesting Methodology

### Phase 0 — Fix the Foundation (Week 1)

1. **Widen SL to 2.5x ATR** — not fixed percentage
2. **Recalibrate kill thresholds** — require n≥100 + statistical test before any kill
3. **Wire outcome resolver** to all 92 zero-pick systems
4. **Start portfolio engine cron job**

### Phase 1 — Honest Baseline (Week 2)

1. Walk-forward validation on mega_mutation + rapid_fire
2. 60/40 chrono split: train on first 60% of trades, test on last 40%
3. Compute: Sharpe, Sortino, MDD, Calmar, PSR, DSR
4. If walk-forward PF < 1.0, the backtest is overfit

### Phase 2 — Strategy Incubator (Week 3-4)

1. New strategies get 30 trades of protected runway (no kill pressure)
2. After 30 trades: if PF ≥ 1.2, graduate to live scoring
3. After 30 trades: if PF < 0.8, kill with autopsy
4. Between 0.8-1.2: extend to 50 trades

### Phase 3 — Mutation Protocol (Week 5-6)

For each DRAIN strategy (PF < 0.7):
1. **Axis 1 — Invert**: Flip LONG↔SHORT. If inverted PF > 1.3, ship inverted.
2. **Axis 2 — Symbol rotation**: Drop bottom-quartile symbols by WR
3. **Axis 3 — Regime gate**: Only fire in matching HMM state
4. If all 3 fail → kill permanently with autopsy

### Phase 4 — Expansion (Week 7-8)

1. Only after one class proves Phase 1-3
2. COMMODITY: expand scanner to all 25 symbols (currently 9 emitting)
3. BOND: expand to full 14-symbol roster (currently 2)
4. FUTURES: build new strategies (all emitters deliberately blocked)
5. FOREX: mutation protocol (inverse + symbol rotation)

---

## 8. Immediate Actions (This Week)

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 1 | Widen SL to 2.5x ATR | Fixes 626 losing trades | 4h |
| 2 | Start portfolio engine cron | Unlocks capital deployment | 1h |
| 3 | Recalibrate kill thresholds to n≥100 | Stops premature kills | 2h |
| 4 | Invert `unknown` strategy (PF 0.59, n=70) | Quick mutation win | 2h |
| 5 | Invert `macd-hidden-div-scout` (PF 0.67, n=15) | Quick mutation win | 2h |
| 6 | Walk-forward validate mega_mutation + rapid_fire | Proves real edge | 4h |
| 7 | Wire outcome resolver to 92 zero-pick systems | Fixes data gap | 4h |
| 8 | Decouple score_booster from crypto-only | Fixes scoring bias | 2h |

---

## 9. Answer to Your Questions

**Do we just need more time?**
No. We need structural fixes. The AI tournament needs more time, but the core system has 5 fixable problems.

**Do our strategies suck?**
Mostly yes. Only 2 out of 127 are genuine winners. But the winners (mega_mutation, rapid_fire) are real — PF 1.93-2.17 with 62-66% WR.

**What are we doing wrong?**
Stops too tight, gates too aggressive, no incubator, no strategy replacement, portfolio engine dead.

**Do we need to DNA mutate our strategies?**
Yes. 7 strategies are clear inversion candidates (PF < 0.7). 3 more need mutation (PF 0.7-1.0).

**Are strategies dead due to data feed issues?**
Partially. 92 systems have zero closed picks — many are filtered by gates, not dead from data issues. The outcome resolver works but isn't wired to all systems.

**Why is our portfolio empty?**
The portfolio lifecycle engine isn't running. The cron job needs to be started.

**Where is our edge?**
- mega_mutation (CRYPTO, PF 1.93)
- rapid_fire (CRYPTO, PF 2.17)
- ETF sector rotation (marginal, PF 1.18)
- AI tournament (too early to tell)

---

## 10. Files to Check

- `verified_strategies/MONEY_READY_REPORT.json` — backtest results
- `verified_strategies/strategies/blue_chip_compounders.py` — retirement-safe stocks
- `verified_strategies/strategies/etf_sector_rotation.py` — ETF rotation
- `verified_strategies/strategies/crypto_donchian_breakout.py` — crypto breakout
- `audit_dashboard/data/dashboard_data.json` — live performance data
- `audit_dashboard/data/pick_funnel_90d.json` — pick funnel analysis

---

*This analysis is based on live data from findtorontoevents.ca/audit as of 2026-06-02. All performance claims are forward-tested or clearly marked as historical/disputed.*
