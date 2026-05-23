# Comprehensive Statistical Edge Analysis & Strategic Recommendations

**Date:** 2026-05-16  
**Analyst:** Kimi Code CLI  
**Data Sources:** `audit_dashboard/data/dashboard_data.json` (2026-05-16T03:55:28Z), `ejaguiar1_backtests` snapshot via local JSON, `audit_trail/quality_gates.py`, `alpha_engine/production_scanner.py`, swarm research outputs (2026-05-16T06:51Z runs), `DAILY_IDEAS_PROMPTS.MD`, `AGENT_PROMPT_LIBRARY.md`  
**Scope:** Per-asset-class validation, blocked symbol infrastructure, unblock criteria, safety gates, prompt library audit

---

## Executive Summary

This session executed Phase 2.1–2.3 of the `ASSET_CLASS_VALIDATION_AND_EDGE_IMPROVEMENT_PLAN.md` for EQUITY, inspected the full blocked-symbol infrastructure, audited two prompt libraries, and identified **three P0 issues** that are actively destroying edge right now:

1. **Blocked symbol leak** — 8 blocked symbols still active in live picks despite a recent `production_scanner.py` fix
2. **EQUITY confidence inversion** — LOW-confidence picks outperform HIGH-confidence by 32 percentage points WR
3. **FOREX structural failure** — PF 0.27, the worst-performing asset class, with no live recovery protocol

The infrastructure for blocking, unblocking, and rehabilitation is surprisingly mature (BLOCKED_STRATEGIES, PENDING_UNBLOCK_REVIEW, COT dedup, 6-stage rehab pipeline), but the **wiring between pipelines is incomplete** — fixes in one code path don't propagate to all source systems.

---

## Phase 2.1–2.3: EQUITY Validation (Completed)

### Data Integrity
| Check | Result | Threshold | Status |
|-------|--------|-----------|--------|
| Ghost rows (CLOSED + null pnl/exit) | 0 / 252 | <0.1% | ✅ Pass |
| Future-dated entries | 0 / 252 | 0 | ✅ Pass |
| Asset class mismatch | 4 symbols dual-tagged (GLD, SPY, QQQ, IWM as ETF+EQUITY) + CT=F as COMMODITY+FUTURES | <0.5% | ✅ Pass |

### Statistical Edge — Aggregate (n=252)
| Metric | Value | Tier 1 Gate | Tier 2 Gate | Status |
|--------|-------|-------------|-------------|--------|
| n | 252 | ≥100 | ≥30 | ✅ Pass |
| Win Rate | 54.0% (56.7% excl flat) | ≥55% | ≥50% | 🟡 Near T1 |
| Profit Factor | 1.974 | ≥1.50 | ≥1.15 | ✅ T1 |
| Mean PnL% / trade | +1.35% | — | — | ✅ Positive EV |
| Total PnL% | +341.22% | — | — | ✅ Strong |

**Tier Verdict: TIER 2 QUALIFIED, approaches TIER 1.**

### 🚨 Critical Finding: Inverted Confidence Relationship

| Confidence Bucket | n | WR | PF | Total PnL% |
|-------------------|---|----|----|------------|
| **LOW** | 84 | **70.2%** | **4.307** | **+290.41%** |
| MID | 84 | 53.6% | 1.334 | +45.60% |
| **HIGH** | 84 | **38.1%** | **1.041** | **+5.22%** |

The confidence model for EQUITY is **systematically miscalibrated**. This is not random noise — it's a 32-percentage-point inversion that suggests the model conflates volatility or position size with probability of success. Fixing this is the single fastest path to Tier 1 for EQUITY.

### Strategy Inventory
- **Top 3 by edge:** `donchian-stock-breakout` (78.6% WR, PF 7.13), `rs-breakout-scout` (72.7% WR, PF 6.86), `vol-contraction-scout` (78.6% WR, PF 6.41)
- **Active concentration risk:** 59.5% of live EQUITY picks (22 of 37) are `magic_formula_x_piotroski_x_acquirers` — a strategy with no closed-track record in the dataset
- **Direction bias:** 249 LONG / 3 SHORT (extreme long skew)

### Monthly Trend
| Month | n | WR | Avg PnL% | Total PnL% |
|-------|---|----|----------|------------|
| 2026-02 | 12 | 8.3% | -2.60% | -31.21% |
| 2026-03 | 94 | 46.8% | -0.13% | -12.04% |
| 2026-04 | 96 | 72.9% | +2.95% | +283.45% |
| 2026-05 | 50 | 42.0% | +2.02% | +101.03% |

April was an exceptional breakout month (earnings + momentum alignment). May is moderating but still positive.

---

## Cross-Asset-Class Snapshot (from dashboard_data.json)

| Class | n | WR | PF | Status | Top Action |
|-------|---|----|----|--------|------------|
| CRYPTO | 2,966 | 46.2% | 1.299 | 🟡 Stable | Kill `quan_engine` volume, cap at 12% |
| EQUITY | 252 | 54.0% | 1.974 | 🟢 T2→T1 | Fix confidence inversion |
| ETF | 105 | 57.1% | 1.320 | 🟡 Borderline T2 | Sector rotation overlay |
| FOREX | 96 | 36.5% | 2.063 | 🔴 Misleading* | *Last-20 WR 15%; aggregate inflated by small n + flat exits |
| COMMODITY | 67 | 55.2% | 1.923 | 🟢 T2 (post-dedup) | Add trend-confirmation gate |
| BOND | 12 | 50.0% | 0.662 | 🔴 Thin sample | Accumulate to n≥100 |
| FUTURES | 2 | 100% | ∞ | ⚪ Ignore | n=2, meaningless |

*FOREX aggregate PF 2.063 is misleading — the class is genuinely sub-floor when excluding flat exits and zero-weight positions.

---

## Blocked Symbol Infrastructure Audit

### What's Working
1. **BLOCKED_SYMBOLS** (quality_gates.py:1571) — 23 symbols with forensic evidence, actively maintained
2. **BLOCKED_STRATEGIES** (quality_gates.py:1814) — 30+ strategy-class pairs, added `opposite_day` and `ema_crossover` (CRYPTO) today
3. **PENDING_UNBLOCK_REVIEW** (quality_gates.py:1763) — Formal 3-stage protocol (SHADOW → PROBATION → FULL) with review dates
4. **COT_DEDUP_SYSTEMS** (quality_gates.py:1801) — PR-#994, 72h guard active
5. **BLOCKED_STRATEGY_SYMBOL_PAIRS** (quality_gates.py:2015) — Fine-grained blocking

### What's Broken: The Leak

Despite a BLOCKED_SYMBOLS filter added to `production_scanner.py` (line ~5990, dated 2026-05-16), **8 blocked symbols remain active** in `active_picks.json` with timestamps *after* the fix:

| Symbol | Source | Timestamp | Leak Reason |
|--------|--------|-----------|-------------|
| TRXUSDT | super_signals | 06:17Z | Bypasses production_scanner pipeline |
| TRXUSDT | ml_crypto_pred | 05:31Z | Bypasses production_scanner pipeline |
| ICPUSDT | quan_engine | 06:21Z | Bypasses production_scanner pipeline |
| NVDA | kimi_riseoftheclaw | 05:05Z | Bypasses production_scanner pipeline |
| TSLA | multi_asset_copytrader | 06:06Z | Bypasses production_scanner pipeline |
| ADBE | ueps | 05:46Z | **Intentional UEPS bypass** (long-horizon) |
| HD | ueps | 05:46Z | **Intentional UEPS bypass** (long-horizon) |
| TSLA | ueps | 05:46Z | **Intentional UEPS bypass** (long-horizon) |

**Root cause:** The production_scanner fix only covers one emission pipeline. Other source systems (`super_signals`, `quan_engine`, `ml_crypto_pred`, `multi_asset_copytrader`, `kimi_riseoftheclaw`) emit picks that never pass through `production_scanner.py::main()`.

**UEPS bypass is by design** (`_ueps_long_horizon_bypass_active` in quality_gates.py:2548), but it's being applied to **performance-based blocks** (ADBE, TSLA, HD) rather than **data-quality blocks** (MATICUSDT, KATUSDT). A 3-year horizon doesn't fix structural anti-edge.

### Recommended Fix
Move the BLOCKED_SYMBOLS check into `audit_trail/quality_gates.py::passes_active_gate()` so it executes for **all** source systems. Preserve the UEPS bypass **only** for data-quality blocks (delisted, redenominated, broken feeds), not for performance-based blocks (draining symbols, low WR).

---

## Symbol Unblock Criteria (Consolidated Protocol)

### Hard Blocks (Never Unblock)
| Symbol | Reason |
|--------|--------|
| MATICUSDT | Delisted, phantom TIME_EXIT trades, 0% WR across 1,057 trades |
| UUSDT | Broken symbol, 0% WR |
| XMR / XMRUSDT | Most destructive symbol, -115% PnL |
| KATUSDT | Token redenomination, 13x price jump |

### 3-Stage Rehabilitation

| Stage | Criteria | Position Size | Duration |
|-------|----------|---------------|----------|
| **SHADOW** | n≥10 post-block, WR≥50%, PF≥1.3 | 0% (track only) | 14 days |
| **PROBATION** | n≥20, WR≥52%, PF≥1.3, Wilson LB≥45% | 50% Kelly | 14 days |
| **FULL UNBLOCK** | n≥30, WR≥52%, PF≥1.2, slope>0, regime-safe | 100% Kelly | Permanent |

### Current Candidates in PENDING_UNBLOCK_REVIEW

| Symbol | Stage | Metrics | Next Action |
|--------|-------|---------|-------------|
| **CT=F** | PROBATION | n=43, WR 81.4%, PF 6.33 | Promote to PROBATION now. Write rehab doc. |
| **IMXUSDT** | PROBATION-ready | n=29, WR 62.1%, PF 2.54, Wilson LB 46.8% | 1 more trade → PROBATION |
| **DYDXUSDT** | SHADOW | n=16, WR 93.8%, PF 19.05 | Verify not a data artifact before promoting |
| **TRXUSDT** | SHADOW | n=24, WR 50%, PF 2.42 | **CRITICAL:** Verify -10,064% historical PnL was a resolver bug, not real |
| **NVDA** | Review due | Blocked 2026-04-15, 30d elapsed | Assess post-block performance; recent data shows 80% WR (4/5) |

---

## Prompt Library Audit

### DAILY_IDEAS_PROMPTS.MD (1,027 lines)
**Verdict: Archive.**
- Concatenated outputs from Mercury, Cerebras, Claude, Gemini, Kimi — massive duplication
- Same 3 prompts (pipeline audit, edge SQL, strategy mutation) repeated 6+ times with different formatting
- Cut-off sentences, malformed markdown, user's own request appended to end (line 960)
- Only unique value: Prompt #9's institutional-grade technique checklist (regime detection, walk-forward, risk budgeting)

### AGENT_PROMPT_LIBRARY.md (801 lines, Downloads)
**Verdict: Keep, but fix data errors first.**
- Well-structured, 20 prompts in 5 sections, clear acceptance criteria
- 10-week roadmap is reasonable
- **Factual errors that will mislead agents:**
  - Claims CRYPTO has confidence inversion (conf≥0.90 → 14.4% WR) — **EQUITY** has the inversion, not CRYPTO
  - States EQUITY PF 1.55 — live data shows **1.974**
  - States FOREX PF 0.86 — live data shows **0.27–0.85**
- **Duplicates existing infrastructure:**
  - Prompt 2D (COT dedup) — already live in PR-#994
  - Prompt 3B (Inversion) — partially implemented via BLOCKED_STRATEGIES
  - Prompt 3D (Necromancer) — overlaps with 6-stage rehab pipeline
  - Prompt 4B (Edge alerts) — overlaps with hourly audit system

**Recommendation:** Use AGENT_PROMPT_LIBRARY.md as a **wiring guide** for connecting existing pieces, not as a build-list.

---

## Prioritized Action Plan

### P0 — This Week (Edge Destroyers)

**1. Fix EQUITY Confidence Inversion**
- Add penalty in `audit_trail/quality_gates.py::passes_smart_gate()`:
```python
if asset_class == "EQUITY" and confidence > 0.7:
    penalties.append("equity_overconfidence_penalty:-15")
```
- Run 14-day shadow test
- Expected impact: WR lift from 54% → 57%+, pushing into Tier 1

**2. Fix Blocked Symbol Leak**
- Move BLOCKED_SYMBOLS check into `passes_active_gate()` (universal pipeline)
- Restrict UEPS bypass to data-quality blocks only
- Verify no blocked symbols in next `active_picks.json` generation

**3. Promote CT=F to PROBATION**
- Meets all criteria (n=43, WR 81.4%, PF 6.33)
- Write `updates/2026-05-16-CT=F-rehab-probation.md`

### P1 — Next 2 Weeks (Edge Amplifiers)

**4. CRYPTO Source Volume Cap**
- Cap `quan_engine` at 12% of CRYPTO active volume (currently ~18%, PF 0.70)
- Add to `alpha_engine/config.py`:
```python
SOURCE_VOLUME_CAP = {
    "quan_engine": {"CRYPTO": 0.12},
}
```

**5. FOREX Carry + EMA Filter**
- Implement DAILY_IDEAS_PROMPTS.MD #8 filter: LONG only when EMA(20) > EMA(50) AND positive rate differential
- Add session filter: London-NY overlap only
- Run original vs. inverted A/B pilot for 30 days

**6. EQUITY Concentration Guard**
- Cap any single strategy at 25% of asset-class exposure until n≥30 closed trades
- Diversify out of `magic_formula_x_piotroski_x_acquirers` (currently 59.5% of active EQUITY)

### P2 — Month 2 (Systematic Improvements)

**7. ETF Sector Rotation Overlay**
- Relative strength momentum across 11 sector ETFs
- Expected PF lift: 1.33 → 1.50 (13% improvement)

**8. VIX + Yield Curve Filter Pilot**
- Backtest shows `AND_vix22.0_yc0.25` yields 82% WR, PF 25.5, Sharpe 3.48
- 30-day paper pilot before live deployment

**9. DNA Mutation Engine Wiring**
- Port AGENT_PROMPT_LIBRARY.md Prompt 3A JSON schema to existing `alpha_engine/strategy_mutation_engine.py`
- Weekly evolution loop with fitness scoring

**10. Auto-Unblock Review Job**
- GitHub Actions job that checks PENDING_UNBLOCK_REVIEW daily
- Auto-promotes symbols meeting criteria from SHADOW → PROBATION
- Surfaces review-due symbols on dashboard

---

## Appendices

### A. Tools & Commands Reference

| Task | Command / File | Notes |
|------|----------------|-------|
| Edge SQL (local) | `python tools/edge_by_asset_class.py` | Uses dashboard_data.json, no DB needed |
| Asset analysis | `python tools/analyze_asset_classes.py` | Produces JSON + MD |
| Quality gates | `audit_trail/quality_gates.py:passes_smart_gate` | Per-class floors |
| Blocked check | `python -c "from audit_trail.quality_gates import BLOCKED_SYMBOLS; print(BLOCKED_SYMBOLS)"` | Live set |
| Forward test | `alpha_engine/forward_validator.py --class <AC> --window 90d` | 90d window |
| Dashboard regen | `python -m audit_trail.dashboard_generator` | After any change |

### B. Data Limitations
- Direct MySQL connection to mysql.50webs.com blocked from current IP (142.198.176.179)
- Analysis uses `audit_dashboard/data/dashboard_data.json` (CI-refreshed, 16.66 MB, generated 2026-05-16T03:55:28Z)
- `ejaguiar1_backtests.bt_backtest_runs` last imported 2026-03-06 — may be stale for CRYPTO incubator strategies

### C. Sign-off

- [x] EQUITY Phase 2.1–2.3 complete
- [x] Blocked symbol infrastructure audited
- [x] Unblock criteria consolidated
- [x] Prompt libraries reviewed
- [x] P0/P1/P2 action plan defined
- [x] Documented in `updates/2026-05-16-comprehensive-edge-analysis-and-recommendations.md`

---

*Medical-grade rule: Document every fix. No undocumented changes. Test before any live exposure.*
