# Per-Asset-Class Profitability Plans — finpredict-v4

**Date:** 2026-11-15 (AM)
**Source grounds:** Every audit round (final_2026_11_14 → final_v4), money-maker methodology, peer phase-10b reports, SubQ endpoint evaluation, and famous-algorithm research.
**Core truth:** 0/8 tracked classes pass Tier-2 money-ready gates today. The path to profitability is not "more strategies" — it's *measurement first, beta vs alpha separation, and long-term trend as the only grounded edge family*.

---

## Shared Preconditions (ALL classes)

1. **Fix measurement first** — QA gate (`tools/qa_ledger.py`) must validate every PnL against real market data before any class is trusted. PnL=0% stale-equal rows, blank fields, and unresolved TIME_EXIT rows must be flagged. Without this, every class verdict is provisional.
2. **Separate beta from alpha** — the core deployable is beta (index exposure). Alpha research runs separately under strict promotion gates.
3. **Pre-registered hypothesis protocol** — every strategy tested is pre-registered with a trial ID; the pass threshold is cost-adjusted, OOS, with effective N. No cherry-picking.
4. **Never size real money until a class clears all gates** on ≥90 days paper.

---

## 1. MUTUAL FUNDS — Plan

**Status:** Zero coverage today (no NAV cache, no ranker, no production path). Explicitly not a prediction class.
**Highest-probability, lowest-risk path (≈85% deliverability).**

| Step | Action | Evidence |
|------|--------|---------|
| S1 | Build the **allocation core**: VTI 70% / BND 15% / SGOV 15% (or FXAIX/FXNAX/FZROX) | Index beta + bond income + T-bill floor |
| S2 | Screen: ER ≤0.20%, no load, no 12b-1, AUM ≥$1B, turnover ≤20%, tracking error ≤0.25% | Vanguard/Fidelity low-cost index funds |
| S3 | Optional tactical sleeve: **Faber 200-day MA** trend filter on the core ETFs (monthly rebalance) | Faber 2007; ~10%+ alpha vs B&H, lower drawdown |
| S4 | Deliver an **asset-allocation scorecard** (benchmark-relative expected return) | Not alpha; honest beta capture |

**Why this wins:** it captures the equity risk premium and bond income over multi-year horizons. It does not require the prediction system to work. This is the "boring" answer and it is correct.

---

## 2. EQUITY (US) — Plan

**Status:** Best research slot, but SPY gate FAILED (median excess −0.57%, beat-SPY 45.5%, t=1.05 → NO_ALPHA_BETA). Only cost-clearing class (3.23× round-trip).

| Step | Action | Evidence |
|------|--------|---------|
| E1 | Route the **Faber 200-day MA / long-term trend** on broad indices (SPY/QQQ) — the credible edge | Faber; long-term trend = grounded |
| E2 | Keep **momentum factor** (Clenow/AQR-style cross-sectional, vol-targeted) as a research sleeve | Momentum = strongest documented anomaly, but crashes; must vol-manage |
| E3 | Re-run the SPY benchmark test **only after measurement is clean** — if it still fails, EQUITY is beta, hold the index | Pre-registered gate |
| E4 | Do NOT chase intraday RSI-2 / scalping (failed; cost-fragile) | Connors RSI-2 degraded |

**Why:** long-term trend is the one academically-supported equity edge. Intraday mean-reversion is cost-fragile.

---

## 3. CRYPTO — Plan

**Status:** Highest volume, PF ~0.74-0.80 after fill fixes, WR ~33%. Highest risk.

| Step | Action | Evidence |
|------|--------|---------|
| C1 | Fix the fill/measurement bugs **first** (gap-aware fill attached, resolve kimi leak) — else all crypto numbers lie | B3/B14 |
| C2 | Forward-test only the **POSITION horizon** sub-bucket (PF 3.18, WR 69.7%, n=33) with frozen rules, n≥100 | Positive sub-bucket is the only hope |
| C3 | If PF ≥1.3, WR ≥55% at n=100 cost-inclusive → scale at 1% then 2-3%; else wind down | Pre-registered gate |
| C4 | Use **momentum/trend** (not short-term scalp) as the signal family | Trend = grounded; scalp = losing mode |

**Why crypto is hardest:** extreme volatility + measurement debris. Treat it as a conditional experiment, never as a core allocation.

---

## 4. ETF — Plan

**Status:** Zero live picks today; intraday TP/SL proven structurally broken (WR 2.2%). Strongest OOS profile historically.

| Step | Action | Evidence |
|------|--------|---------|
| T1 | **Retire intraday ETF strategies** permanently | WR 2.2% conclusive |
| T2 | Build the **monthly dual-momentum / tactical rotation** (Antonacci Dual Momentum or Faber rotation) on SPY/QQQ/IWM/TLT/GLD | Momentum + trend = grounded |
| T3 | Use as a **satellite diversifier** in the allocation core, not a stand-alone signal | Low-frequency rotation |

**Why:** ETFs are the right vehicle for the grounded trend/momentum family, at monthly frequency, not intraday.

---

## 5. FOREX — Plan

**Status:** Weakest class; PF ~0.035-0.85, breakeven gap −16pp. No DSR survivors.

| Step | Action | Evidence |
|------|--------|---------|
| F1 | Keep **hard-disabled** until measurement is clean (too many forged TIME_EXIT rows) | 96.6% null PnL |
| F2 | If resumed, test **carry + trend** (TSMOM 12m) at low frequency, with swap-cost accounting | Carry/trend = grounded; contrarian sentiment = anti-skill |
| F3 | Do NOT trade intraday sessions | All session-scalp engines fail |

**Why:** FOREX's only defensible edges are the macro carry/trend premia, which are low-frequency.

---

## 6. BOND — Plan

**Status:** n far below floor (n=18), contaminated. FRED data unblock needed.

| Step | Action | Evidence |
|------|--------|---------|
| B1 | Unblock **FRED** feed to accumulate n ≥60 | Bond scanner needs data |
| B2 | Test **duration rotation / 200-day trend on TLT** at monthly frequency | Trend = grounded |
| B3 | Use only as ballast in the allocation core (BND), not a stand-alone prediction | Bond = yield income |

---

## 7. COMMODITY / FUTURES — Plan

**Status:** Historical PF ~1.78 but unproven; COT gate failed 4/4; futures plumbing-blocked.

| Step | Action | Evidence |
|------|--------|---------|
| G1 | **Retire COT contrarian** (gate failed) | 4/4 pre-registered checks failed |
| G2 | Build **CTA trend / 200-day MA** on real futures (TSMOM), paper-track 30d | Moskowitz; Winton/AHL audited |
| G3 | Only unblock after real feed + paper track; low n blocks promotion | n<60 |

---

## 8. MULTI-ASSET / META / OPTIONS — Plan

**Status:** Meta-permutation overfit; 0DTE scalping = losing mode.

| Step | Action | Evidence |
|------|--------|---------|
| M1 | **Stop mining meta-strategies** (170 ledgers already; more trials = more false positives) | B8 |
| M2 | Use only **diversified trend/CTA portfolio construction** (low correlation across classes) | Institutional CTA model |
| M3 | Drop options/0DTE scalping | Cost-driven losing mode |

---

## Summary: Priority Order (highest probability × lowest risk first)

| Priority | Class | Role | Probability | Risk |
|----------|-------|------|-------------|------|
| 1 | Mutual funds / broad ETFs | **Beta core** | ~85% deliverability | Low |
| 2 | EQUITY (long-term trend) | Alpha research | ~60% | Moderate |
| 3 | Futures CTA trend | Alpha research | ~30% | High (leverage) |
| 4 | CRYPTO POSITION | Conditional experiment | ~20% | High |
| 5 | ETF rotation | Satellite diversifier | ~30% | Moderate |
| 6 | FOREX/BOND/COMMODITY | Blocked until data clean | <10% | High |

**Bottom line:** the deployable path is beta (index exposure). The research path is long-term trend/momentum. Everything else waits for clean measurement.
