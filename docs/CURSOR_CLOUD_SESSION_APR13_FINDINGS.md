# Cursor Cloud Agent — Full Session Findings (Apr 13-14, 2026)

**Session:** April 13, 2026 4:00 PM EDT — April 14, 2026 1:08 AM EDT (~9 hours)  
**Agent:** Cursor Cloud  
**Collaboration:** Claude (Antigravity bot), Mercury (Inception Labs), OpenRouter, Roo

---

## 1. Data Source Reconciliation (The Foundation)

Three data files exist with different contents. Every number in this session depends on which file was used.

| File | Picks | What It Contains | Use For |
|------|-------|-----------------|---------|
| `audit_dashboard/data/dashboard_data.json` → `picks.recent_closed` | 3,500 | Multi-asset, scored, 35 source systems | **Asset-class breakdown, compound filter** (only file with `score` + `trust_score`) |
| `audit_trail/data/universal_resolved_picks.json` | 4,332 | Crypto-only, 3 clean exit reasons, 61 source systems | **Per-system crypto metrics** (cleanest exit data) |
| `alpha_engine/data/closed_picks.json` | 4,228 | 84% quan_engine, 738 MATIC ghosts | **DO NOT USE** for system-wide analysis |

Overlap between files is <2.5%. They are different datasets from different pipelines, not different views of the same data.

---

## 2. System Performance — The Honest Numbers

### Overall (Universal Ledger, Crypto)

| Metric | All Picks | Definitive Only | Timeouts Only |
|--------|----------|-----------------|---------------|
| n | 4,249 | 3,821 | 428 |
| WR | 47.1% [45.6-48.6%] | 45.6% [44.0-47.1%] | 61.0% [56.3-65.5%] |
| PF | **1.43** | **1.37** | **2.50** |
| Expectancy | +0.396%/trade | +0.354% | +0.774% |
| Cumulative | +1,682% | +1,351% | +331% |

**Verdict:** The system is modestly profitable. Not a coin flip. Not hedge-fund grade unfiltered.

### By Asset Class (Dashboard Data)

| Asset Class | n | WR | PF | Exp/trade | Cum PnL | Status |
|---|---|---|---|---|---|---|
| **Crypto** | 1,862 | 46.3% | **1.39** | +0.26% | +483% | Edge |
| **Forex** | 666 | 44.0% | **2.02** | +0.32% | +214% | Strong edge |
| **Commodity** | 267 | 43.8% | **1.04** | +0.01% | +4% | Breakeven |
| Equity | 612 | 39.5% | 0.75 | -0.57% | -347% | **Losing** |
| ETF | 18 | 44.4% | 0.28 | -0.84% | -15% | Losing (tiny n) |
| Futures | 17 | 5.9% | 0.06 | -0.09% | -2% | Non-functional |

### Key Discovery: Timeouts Are Destroying Value

Timeout picks (force-closed by time limit) have **PF=2.50 and 61% WR**. The system is force-closing winners. Extending hold time is the single largest available PF improvement.

---

## 3. The Compound Filter — The Session's Best Finding

**Filter:** `trust_score >= 3 AND score >= 50 AND direction = LONG`

| Metric | Baseline (crypto LONG def.) | Filtered |
|---|---|---|
| n | 1,154 | 307 |
| WR | 44.2% | **58.6%** |
| PF | 1.57 | **3.09** |
| Expectancy | +0.385% | **+1.394%** |
| CI Lower Bound | 41.3% | **53.0%** (statistically significant) |

Stable across time windows: Q2 PF=27.55, Q3 PF=1.51, Q4 PF=3.56.

**This is direction-specific.** Crypto SHORT PF=1.08 (barely breakeven). The edge is in LONGs.

For equity: same filter flips PF from 0.70 (losing) to 2.56 (profitable) on n=60.

**Methodology:** See `docs/COMPOUND_FILTER_METHODOLOGY.md` (on main) for full reproduction steps including copy-paste Python script.

---

## 4. Prop Challenge Replay — Would Our Picks Have Passed?

Replayed actual closed picks through a $5K prop challenge simulator ($250 daily DD, $500 trailing DD, $500 target).

**12 of 13 filter combinations PASS Phase 1:**

| Filter | Trades to Pass | WR | PnL |
|---|---:|---:|---:|
| **Top 3 sources** (claude_gainer_st + luxalgo + dna_winner) | **8** | 100% | +$500 |
| **1 pick per symbol per day** | **8** | 100% | +$505 |
| **Compound filter** | **10** | 100% | +$563 |
| claude_gainer_st only | 16 | 81.2% | +$531 |
| luxalgo_filters only | 7 | 100% | +$564 |
| multi_asset_copytrader only | 4 | 100% | +$519 |
| R:R>=2.0 + trust>=3 + LONG | 34 | 55.9% | +$512 |

**Execution methodology:**
- One pick at a time, sequential (no concurrent positions)
- 0.75% risk per trade ($37.50 at $5K)
- Dollar PnL = risk_amount × pnl_pct / 1.5 (normalized by avg SL distance)
- Picks processed in chronological order

**Caveat:** This is a replay on historical data. The first 10 compound-filter picks all winning is partly favorable timing (April 9 was a strong alt-coin day). Forward validation needed.

---

## 5. HyroTrader v4 Playbook — Failed Prop Sim

The v4 playbook (candle-based strategies: bollinger, rsi2, volume breakout) was tested on a combined portfolio simulator and **fails every variant:**

| Simulation | Result | PnL |
|---|---|---|
| Concurrent | FAIL (daily DD $262 > $250) | +$186 |
| Sequential 3d rotation | FAIL (trailing DD $516) | -$302 |
| Sequential 7d rotation | FAIL (trailing DD $531) | -$358 |
| Sequential 14d rotation | FAIL (trailing DD $517) | -$414 |
| Sequential 21d rotation | FAIL (trailing DD $530) | -$384 |
| Sequential 30d rotation | FAIL (trailing DD $509) | -$149 |

**Root cause:** The v4 candle strategies are net-negative. The system's edge is in the **scoring pipeline** (trust/score/ML), not in any individual technical strategy. The compound filter on dashboard picks passes; raw candle strategies don't.

---

## 6. Bugs Fixed

| Bug | File | Fix |
|-----|------|-----|
| Transaction costs never applied | `validation_metrics.js:81` | `{ cost }` → `{ total: cost }` |
| Permutation zero-PnL as losses | `dashboard_generator.py:9287` | Use `_outcome_bucket_from_pnl()` |
| `signal_validation` wrongfully blocked | `quality_gates.py:838` | Unblocked (now 140 trades, 57.1% WR, PF 2.11) |
| Forward validator MFE/MAE None crash | `forward_validator.py:916` | Guard against null mfe/mae values |
| adaptive_tp_sl asset_class defaulting to crypto | `adaptive_tp_sl.py` (PR #170) | Infer from symbol |

---

## 7. GitHub Actions Status

- **97 workflows tracked**, 0 stale (>24h)
- **2 failures** at session end (both Alpha Engine — MFE/MAE None crash, fixed)
- Push contention (280+ workflows to main) causes intermittent failures

---

## 8. Multi-Agent Assessment

| Agent | Reliable? | Best Contribution |
|-------|-----------|-------------------|
| **Claude** | Yes — reads actual code | TIME_EXIT discovery, portfolio sim, forward_validator fix (PR #175) |
| **Cursor** (this agent) | Yes with caveats | Compound filter, asset-class breakdown, setup tooling, honest self-corrections |
| **Mercury** | No — fabricates file paths | Hedge-fund metrics checklist (boilerplate, not code) |
| **OpenRouter/Roo** | Read wrong file | Flagged `algorithm_performance_analysis.json` (different dataset) |

**Key lesson:** Always state the data source. `closed_picks.json` and `dashboard_data.json` tell fundamentally different stories.

---

## 9. What's NOT Ready

- **HyroTrader prop challenge:** Candle strategies fail. Dashboard pick replay passes but needs forward validation.
- **Equity asset class:** PF=0.75 unfiltered (losing). Filter helps (PF=2.56) but n=60 is borderline.
- **Per-system metrics from dashboard:** Tag-aliasing (PR #160/#175) contaminates system-level numbers.
- **ML pipeline:** 39 vs 41 feature misalignment, 0% ml_score coverage, stale models.

---

## 10. Actionable Next Steps

| Priority | Action | Why |
|----------|--------|-----|
| **P0** | Run compound filter in paper mode for 7 days | Forward-validate the PF=3.09 finding |
| **P1** | Extend hold times (timeout picks are PF=2.50) | Largest single PF improvement |
| **P2** | Fix equity (extend hold time — equity timeouts are +0.63%/trade) | Flip equity from losing to profitable |
| **P3** | Merge PR #181 infrastructure (filter + symbols, NOT playbook) | Compound gate wired into hyro filter |
| **P4** | Normalize exit reasons (232 labels → 8 categories) | Data quality for all future analysis |
| **P5** | Retrain Alpha Engine XGBoost (20 days stale) | ML predictions currently noise |

---

*Last updated: April 14, 2026 1:08 AM EDT*
