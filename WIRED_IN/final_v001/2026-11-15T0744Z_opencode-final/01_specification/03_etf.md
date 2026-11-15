# 01_SPECIFICATION — ETF (Exchange Traded Funds)

**Asset Class:** ETF (Exchange Traded Funds)
**Status:** BLOCKED — Cohort Mismatch + Zero Live Picks
**sizing_allowed:** false
**Source:** `alpha_engine/data/closed_picks.json`, `alpha_engine/data/active_picks_etf.json`, `alpha_engine/data/etf_decay_picks.json`, `alpha_engine/data/etf_sector_picks.json`, `reports/peer_claude-phase10b-money-maker-ETF_result_2026-05-31.md`, `updates/2026-05-13-money-maker-action-plan.md`

---

## 1. Algorithm Specification

### Strategies Attempted

| Strategy | File | Parameters | Entry Logic | Exit Logic | TP/SL | Result |
|----------|------|-----------|-------------|------------|-------|--------|
| `etf_dual_momentum` | `alpha_engine/etf_strategies.py` | MA(50)/MA(200), tp_mult=2.5, sl_mult=1.5 | LONG top ETF by 12m return if r12m>0 | SELL bottom ETF if r12m<-5% | ATR×2.5 / ATR×1.5 (RR≈1.67) | Not tested on real picks |
| `etf_sector_momentum` | `alpha_engine/etf_strategies.py` | SMA200, r3m>0, ADX | LONG top 3 sector ETFs where price>SMA200 | Exit on regime change | ATR×2.5 / ATR×1.5 (RR≈1.67) | Not tested on real picks |
| `etf_risk_parity_rotation` | `alpha_engine/etf_strategies.py` | SPY-TLT 30d corr | LONG TLT if TLT>SMA50 (risk-off); LONG SPY/QQQ if >SMA200 (risk-on) | Regime change | TLT: ATR×2.0/1.3; SPY: ATR×2.5/1.5 | Not tested on real picks |
| `etf_trend_following` | `alpha_engine/etf_strategies.py` | SMA50/SMA200, volume>0.8×20d avg | LONG on golden cross; SELL on death cross | Reverse cross | ATR×3.0 / ATR×1.5 (RR≈2.0) | Not tested on real picks |
| `etf_faber_tactical` | `alpha_engine/etf_strategies.py` | SMA200 (10-month) | LONG when Close>SMA200 | Close<SMA200 (trailing SMA stop) | TP=entry+4×distance(SMA200) → RR=4.0 | 1 closed pick (QQQ, LOST at -0.01%) |
| `etf_rsi2_pullback` | `alpha_engine/etf_strategies.py` | RSI(2), SMA50, volume>1M | BUY if RSI(2)<10 AND close>SMA50 | Fixed TP=4%, SL=-5% | TP=4%, SL=5% (RR=2.0) | Not tested on real picks |
| `etf_sector_dual_momentum` | `alpha_engine/etf_strategies.py` | 20-day high/low breakout | LONG top 3 where 12m return>0 AND >SPY 12m return | Opposite Donchian break | ATR×2.5 / ATR×1.5 | Not tested on real picks |
| `etf_cross_sectional_momentum` | `alpha_engine/etf_strategies.py` | 12m-1m return | LONG top 3 by 12m-1m return with positive absolute momentum | Opposite Donchian break | ATR×2.5 / ATR×1.5 | Not tested on real picks |

### Cost Model
- Commission: 1 bps per side
- Slippage: 1 bps per side
- Round-trip cost: 4 bps (4.0 bps total)
- Source: `run_simulation_backtest.py`

### Benchmark
- SPY total return (dividends adjusted)
- Equal-weight ETF buy-and-hold
- Source: `run_simulation_backtest.py`

### Walk-Forward Design
- Not yet implemented for ETF strategies
- Required: 5 folds, expanding window, 1yr train / 1yr test

---

## 2. Backtest Results (Ground Truth from closed_picks.json)

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/data/closed_picks.json`

| Metric | Value |
|--------|-------|
| Total closed ETF picks | **1** |
| Wins (WON) | 0 |
| Losses (LOST) | 1 |
| Win Rate | **0.0%** |
| Profit Factor | **0.00** |
| Gross Profit | +0.00% |
| Gross Loss | -0.0105% |
| Net PnL | -0.0105% |

### The Single ETF Closed Pick

| Symbol | Direction | Entry | Exit | PnL | Status | Strategy |
|--------|-----------|-------|------|-----|--------|----------|
| QQQ | LONG | 688.17 | ? | -0.0105% | LOST | `etf_faber_tactical` |

### Active ETF Picks

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/data/active_picks_etf.json`

| Metric | Value |
|--------|-------|
| Total active ETF picks | 14 |
| Status | All OPEN (unresolved) |
| Source | `etf_emitter_spike` |
| Strategies | `etf_dual_momentum`, `etf_sector_momentum`, `etf_faber_tactical`, `etf_rsi2_pullback`, `etf_sector_dual_momentum`, `etf_cross_sectional_momentum` |
| Symbols | SPY, QQQ, EFA, XLV, XLF, XLE, XOP, USO, VCSH, KWEB, SOLXX |

### ETF Decay Picks

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/data/etf_decay_picks.json`

| Metric | Value |
|--------|-------|
| Total picks | 3 (all OPEN) |
| Strategy | `leveraged_etf_decay` |
| Symbols | LABD, JDST, SOXS |
| Type | Short leveraged ETF decay harvest |
| TP/SL | TP=20%, SL=10% (RR=2.0) |
| Status | All OPEN, `forward_test_only: true` |
| Claimed backtest | WR 65-77%, PF 1.61-2.94, n=29-39 |

### ETF Sector Picks

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/data/etf_sector_picks.json`

| Metric | Value |
|--------|-------|
| Total picks | 14 (all OPEN) |
| Source | `etf_emitter_spike` |
| Status | All OPEN, no resolved outcomes |

### Leveraged ETF Decay Picks

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/data/leveraged_etf_decay_picks.json`

| Metric | Value |
|--------|-------|
| Total picks | 4 (all OPEN) |
| Symbols | JDST, LABD, SOXS (from 2026-04-04), DRIP |
| TP/SL | SL=10%, TP=20% (3x ETFs); SL=3%, TP=6% (2x ETFs) |
| Status | All OPEN, `forward_test_only: true` |
| Claimed backtest | WR 57-70%, PF up to 2.94, n=137-159 |

---

## 3. Claimed vs Actual — Does 56.1% WR / 1.34 PF Hold Up?

**Claim (from `updates/2026-05-13-money-maker-action-plan.md`, line 24):**

| Metric | Claimed | Actual (closed_picks.json) |
|--------|---------|---------------------------|
| n (closed picks) | 107 | **1** |
| Wins | — | 0 |
| Losses | — | 1 |
| WR | 56.1% | **0.0%** |
| PF | 1.34 | **0.00** |

**Actual ground truth from `closed_picks.json`:**

| Metric | Value |
|--------|-------|
| n (closed picks) | **1** |
| Wins | **0** |
| Losses | **1** |
| WR | **0.0%** |
| PF | **0.00** |
| Net PnL | -0.0105% |

**Conclusion: The claimed 56.1% WR / 1.34 PF does NOT hold up.** The actual closed_picks.json ground truth shows 0 wins, 1 loss, 0% WR, PF=0.00 on n=1.

---

## 4. ETF Cohort Mismatch — Official vs Registry PF Discrepancy

**YES, a significant ETF cohort mismatch exists:**

| Source | Claim | Reality |
|--------|-------|---------|
| `closed_picks.json` (ground truth JSON) | n=1 ETF closed pick, 0% WR, PF=0.00 | **Ground truth** |
| `updates/2026-05-13-money-maker-action-plan.md` | n=107, WR=56.1%, PF=1.34 | From `dashboard_data.json` / live DB, not committed JSON |
| `reports/peer_claude-phase10b-money-maker-ETF_result_2026-05-31.md` | pf_registry: PF=0.48, WR=50%, n=4 | Still fails T2 (n<<100) |
| `reports/peer_claude-phase10b-money-maker-ETF_result_2026-05-31.md` | live DB WON+LOST: n=18, WR=5.6%, PF=0.004 | Essentially no edge |
| `reports/peer_claude-phase10b-money-maker-ETF_result_2026-05-31.md` | live DB all non-null: n=22, WR=36.4%, PF=0.98 | Below 50% WR, PF<1.0 |

**Resolver bug:** 134 ETF TIME_EXIT rows have forced `pnl_pct=0.00000000` (forced zero), meaning ~134 "closed" ETF picks carry no real PnL data. The phase10b report states: "If resolver re-runs intrabar-correct on these, we likely get 80-100 usable closures overnight."

The `closed_picks.json` file only contains 1 ETF pick because the vast majority of ETF picks are either OPEN (159 in DB) or stuck at TIME_EXIT with zero PnL (134 in DB) — they never made it into `closed_picks.json` with resolved outcomes.

---

## 4. Phase 4 Proof Gates — Does Any ETF Strategy Pass?

**NO ETF strategy passes ALL Phase 4 proof gates.** Here's why:

| Gate | Requirement | ETF Status |
|------|-------------|------------|
| Walk-forward (OOS) | n ≥ 60+ trades, consistent folds | **FAIL** — n=1 closed pick total |
| DSR ≥ 0.95 | Deflated Sharpe Ratio ≥ 0.95 | **FAIL** — insufficient data |
| PBO ≤ 0.10 | Probability of Backtest Overfitting ≤ 10% | **FAIL** — no backtest results in closed data |
| Block-bootstrap CI excluding zero | 95% CI on mean return excludes 0 | **FAIL** — n=1 |
| Cost-adjusted PF ≥ 1.15 | After realistic costs (fees, spread, slippage) | **FAIL** — PF = 0.00 |

The action plan itself (line 164) admits: "ETF: Cleanest OOS profile (WF consistency 100%, OOS WR 75%, decay +23%) but n=88-100 is at floor." And the phase10b report states: "Without a real candidate at n≥10 with a non-degenerate pnl distribution, ETF has no MC-flagged real-edge candidate."

---

## 5. TP/SL Parameters by ETF Strategy

| Strategy | TP Method | SL Method | RR | Fixed % TP/SL |
|----------|-----------|-----------|-----|---------------|
| `etf_dual_momentum` | ATR×2.5 (cap 10%) | ATR×1.5 (cap 6%) | ~1.67 | None (ATR-based) |
| `etf_sector_momentum` | ATR×2.5 (cap 10%) | ATR×1.5 (cap 6%) | ~1.67 | None |
| `etf_risk_parity_rotation` | TLT: ATR×2.0; SPY: ATR×2.5 | TLT: ATR×1.3; SPY: ATR×1.5 | ~1.54 / ~1.67 | None |
| `etf_trend_following` | ATR×3.0 (cap 10%) | ATR×1.5 (cap 6%) | ~2.0 (min gate 1.50) | None |
| `etf_faber_tactical` | Entry + 4×distance(SMA200) | SMA200 value (trailing) | 4.0 | None (dynamic) |
| `etf_rsi2_pullback` | Entry × 1.04 | Entry × 0.98 | 2.0 | TP=4%, SL=5% |
| `etf_sector_dual_momentum` | ATR×2.5 | ATR×1.5 | ~1.67 | None |
| `etf_cross_sectional_momentum` | ATR×2.5 | ATR×1.5 | ~1.67 | None |

**Leveraged ETF decay (separate strategy):** 3x ETFs: SL=10%, TP=20% (RR=2.0); 2x ETFs (DRIP): SL=3%, TP=6% (RR=2.0).

---

## 6. Coherence Summary — All Contradictions

| Source | Claim | Reality |
|--------|-------|---------|
| `updates/2026-05-13-money-maker-action-plan.md` line 24 | ETF n=107, WR=56.1%, PF=1.34, T3 candidate | `closed_picks.json`: n=1, WR=0%, PF=0.00 |
| `reports/peer_claude-phase10b-money-maker-ETF_result_2026-05-31.md` pf_registry view | n=4, WR=50%, PF=0.48 | Still fails T2 (n<<100) |
| `reports/peer_claude-phase10b-money-maker-ETF_result_2026-05-31.md` live DB WON+LOST | n=18, WR=5.6%, PF=0.004 | Essentially no edge |
| `reports/peer_claude-phase10b-money-maker-ETF_result_2026-05-31.md` live DB all non-null | n=22, WR=36.4%, PF=0.98 | Below 50% WR, PF<1.0 |
| Sidecar `leveraged_etf_decay_picks.json` | PF up to 2.94, n up to 137 | All 4 picks OPEN, pnl_pct=null, forward_test_only |
| Sidecar `etf_decay_picks.json` | PF 1.61-2.94, n 29-39 | All 3 picks OPEN, forward_test_only |

---

## 7. Final Verdict: REJECT

**Reasoning:**

1. **Ground truth data is essentially empty:** `closed_picks.json` contains exactly **1 closed ETF pick** (QQQ via `etf_faber_tactical`, LOST at -0.01%). Zero wins, one loss, 0% WR, PF=0.00.

2. **Claimed metrics are fabricated or from a different data source:** The 56.1% WR / 1.34 PF / n=107 from the 2026-05-13 action plan does not appear in `closed_picks.json`. The phase10b result file confirms the best available view is PF=0.48 (n=4) from pf_registry, or PF=0.004 (n=18) from live DB WON+LOST.

3. **Resolver bug invalidates most ETF "closures":** 134 ETF picks are stuck at TIME_EXIT with forced `pnl_pct=0`, meaning the pipeline has not produced real resolved outcomes for the ETF class.

4. **No ETF strategy can pass Phase 4 gates:** With n=1 closed pick, no walk-forward, DSR, PBO, bootstrap CI, or cost-adjusted PF gate can be satisfied. Even the most optimistic sidecar backtest claims (PF up to 2.94) are forward_test_only with zero realized PnL.

5. **All 14 active ETF picks are OPEN/unresolved** (`active_picks_etf.json`), and `active_picks.json` / `active_picks_fast.json` contain zero ETF picks.

**File paths for every claim:**
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/data/closed_picks.json` — ground truth ETF pick count (1), WR (0%), PF (0.00)
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/data/active_picks.json` — 0 active ETF picks
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/data/active_picks_fast.json` — 0 active ETF picks
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/data/active_picks_etf.json` — 14 draft OPEN ETF picks
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/data/etf_decay_picks.json` — 3 OPEN leveraged ETF decay picks
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/data/etf_sector_picks.json` — 14 OPEN ETF sector picks
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/data/leveraged_etf_decay_picks.json` — 4 OPEN leveraged ETF decay picks (2026-04-04)
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/etf_strategies.py` — 8 ETF strategies with full entry/exit logic
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/updates/2026-05-13-money-maker-action-plan.md` line 24 — claimed ETF n=107, WR=56.1%, PF=1.34
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/peer_claude-phase10b-money-maker-ETF_result_2026-05-31.md` — phase10b result: PF=0.48/WR=50%/n=4 (registry), PF=0.004/WR=5.6%/n=18 (live DB)
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/peer_claude-phase10b-money-maker-ETF_plan_2026-05-31.md` — phase10b plan
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/backups/money-maker-readyv2.md.bak` — general guidance, no ETF-specific numbers

**Bottom line:** ETF has no proven edge. All apparent "wins" are artifacts of cohort mismatch, resolver bugs, or untested backtests. **ETF is BLOCKED.**
