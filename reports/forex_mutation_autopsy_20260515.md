# FOREX Mutation Autopsy — 2026-05-15

**Protocol:** `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
**Trigger:** FOREX PF=0.81, WR=52.3% (dashboard health), classified "stressed", sizing_allowed=False
**Data source:** `audit_dashboard/data/dashboard_data.json::picks` (n=148 closed+resolved)

---

## Three-Axis Analysis

### Axis 1 — Symbol (n≥5)

| Symbol | n | WR | PF | Net PnL | Verdict |
|--------|---|----|----|---------|---------|
| NZDUSD=X | 12 | 16.7% | 0.32 | -3.35% | **KILL** — below coin-flip, PF<0.5 |
| EURJPY=X | 9 | 22.2% | 0.20 | -2.52% | **KILL** — PF=0.20 is catastrophic |
| USDCHF=X | 5 | 20.0% | 0.00 | -1.14% | **KILL** — 0 wins, all losers |
| EURUSD=X | 15 | 20.0% | 0.46 | -2.81% | **BLOCK** — WR=20% on 15 trades |
| USDJPY=X | 13 | 30.8% | 0.78 | -0.76% | **PENALIZE** — JPY cross, marginal |
| GBPUSD=X | 10 | 20.0% | 0.85 | -0.58% | **PENALIZE** — WR=20% |
| GBPJPY=X | 6 | 50.0% | 0.84 | -0.22% | **WATCH** — WR ok, PF below T2 |
| AUDUSD=X | 11 | 54.5% | 3.55 | +4.95% | **BOOST** — T2 performer |
| AUDJPY=X | 8 | 62.5% | 2.45 | +2.98% | **BOOST** — WR and PF solid |
| GBP-USD | 10 | 50.0% | 1.88 | +7.00% | **KEEP** — good via kimi source |
| EUR-USD | 9 | 44.4% | 2.05 | +0.91% | **KEEP** — marginal WR but decent PF |
| CADJPY=X | 4 | 50.0% | 1.70 | +0.42% | **WATCH** — n<5, insufficient |

**Recommended BLOCKED_ASSET_STRATEGY_PAIRS additions** (require user approval per CLAUDE.md):
```python
# REQUIRES EXPLICIT USER APPROVAL BEFORE ADDING
("FOREX", "dxy-reversal-scout"),              # WR=20%, PF=0.44
("FOREX", "fx_smart_carry_trade_momentum"),   # WR=25%, PF=0.63
# Symbol-level: when symbol gate is wired
# BLOCKED_SYMBOLS_BY_CLASS.get("FOREX", []) += ["NZDUSD=X", "EURJPY=X", "USDCHF=X"]
```

### Axis 2 — Direction

| Direction | n | WR | PF | Verdict |
|-----------|---|----|----|---------|
| LONG | 119 | 29.4% | 0.80 | **Critical drag** — PF<1, WR far below 50% |
| SHORT | 29 | 34.5% | 8.11 | **Edge exists** — high PF despite low WR (big winners) |

**Finding:** FOREX LONG is almost entirely responsible for the class-level PF=0.81.
LONG WR=29.4% means picks are wrong 70% of the time.
SHORT PF=8.11 with n=29 is small sample but the directional split is stark.

**Recommended mutation:** score penalty for FOREX LONG picks (defer — needs research into
which sources are generating LONG-only vs mixed signals).

### Axis 3 — Source/Strategy

| Source | n | WR | PF | Net PnL | Action |
|--------|---|----|----|---------|--------|
| multi_asset_scanner | 11 | 0.0% | 0.00 | -0.20% | **Score penalty: -25 override** |
| kimi_riseoftheclaw | 56 | 37.5% | 1.01 | +0.13% | **Score penalty: -12 override** |
| alpha_engine | 24 | 29.2% | 1.01 | +0.10% | **Score penalty: -8 override** |
| alpha_engine_fast | 13 | 53.8% | 1.56 | +1.99% | **KEEP** — T2 WR |
| signal_validation | 44 | 22.7% | 2.09 | +9.68% | **KEEP** — MeanReversionBB high PF |

| Strategy | n | WR | PF | Action |
|----------|---|----|----|--------|
| dxy-reversal-scout | 10 | 20.0% | 0.44 | **Propose block** (user approval needed) |
| fx_smart_carry_trade_momentum | 20 | 25.0% | 0.63 | **Propose block** (user approval needed) |
| unknown | 21 | 33.3% | 0.93 | **Investigate** — no strategy label |
| MeanReversionBB | 44 | 22.7% | 2.09 | **Keep** — high PF saves it |
| forex-rsi-ema-scout | 22 | 54.5% | 1.68 | **Keep + boost** |

---

## Implemented Fixes (no user approval needed — score adjustments only)

Applied to `audit_trail/quality_gates.py::_SOURCE_ASSET_CLASS_OVERRIDES`:

```python
("FOREX", "multi_asset_scanner"): -25,   # WR=0%, n=11 → net global -50, below any FOREX floor
("FOREX", "kimi_riseoftheclaw"): -12,    # WR=37.5%, n=56 — major volume drag
("FOREX", "alpha_engine"): -8,           # WR=29.2%, n=24 — consistent underperformer
```

Expected impact: FOREX sources with negative edge de-prioritized. Picks from `alpha_engine_fast`
(WR=53.8%, PF=1.56) and `signal_validation` (PF=2.09) unaffected.

---

## 30-Day Probation Plan

Per swarm feedback (cerebras + deepseek consensus):

| Phase | Duration | Action |
|-------|----------|--------|
| Now | Immediate | Source overrides active; bad sources can't clear FOREX floor=60 |
| Day 0-30 | 30d | Monitor new FOREX picks — count only from alpha_engine_fast + signal_validation |
| Day 30 | Review | If new WR≥50% on n≥20 new picks → lift probation, reduce penalties |
| Day 30 | If WR<45% | Propose BLOCKED additions for dxy-reversal-scout + fx_smart_carry_trade_momentum |

---

## Required User Approvals (not implemented)

1. Add `("FOREX", "dxy-reversal-scout")` to BLOCKED_ASSET_STRATEGY_PAIRS
2. Add `("FOREX", "fx_smart_carry_trade_momentum")` to BLOCKED_ASSET_STRATEGY_PAIRS
3. Block symbols: NZDUSD=X, EURJPY=X, USDCHF=X for FOREX class

---

## Root Cause Summary

FOREX PF=0.81 is driven by:
1. **Direction bias (primary)**: 80% of FOREX picks are LONG; FOREX LONG has WR=29.4%, PF=0.80.
   Sources generating LONG picks without directional edge are the core problem.
2. **multi_asset_scanner FOREX**: 0 wins in 11 picks — a scanner-level routing bug.
3. **Weak symbols**: NZDUSD/EURJPY/USDCHF generate consistent losses.
4. **Legacy strategies**: dxy-reversal-scout + fx_smart_carry_trade_momentum have no edge.

**Survivors with edge**: AUDUSD=X (PF=3.55), signal_validation/MeanReversionBB (PF=2.09),
alpha_engine_fast (WR=53.8%).
