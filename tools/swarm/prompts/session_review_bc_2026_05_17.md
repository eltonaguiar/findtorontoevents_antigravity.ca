# Session BC — Swarm Review Request
# Date: 2026-05-17
# Session: BC (following BB — deepseek APPROVE)

## Context

Session BC: EQUITY multi_asset_copytrader symbol-level autopsy + M-items status audit.
All sessions through BB have returned deepseek APPROVE.

## Session BC Deliverables

### 1. EQUITY Strategy Autopsy (new finding)

Three-axis (symbol-level) autopsy on multi_asset_copytrader EQUITY picks (n=39 resolved):

**By symbol:**
```
RIOT: n=14  WR=50%  avg_pnl=+1.00%  ← neutral/ok
AMD:  n=12  WR=8%   avg_pnl=-2.33%  ← primary drag
NVDA: n=5   WR=80%  avg_pnl=+3.40%  ← promising, small
NIO:  n=4   WR=0%   avg_pnl=-6.90%  ← worst per-trade loss
AVGO: n=2   WR=0%   avg_pnl=-3.00%
PFE:  n=1   WR=100% avg_pnl=+4.13%
CVX:  n=1   WR=0%   avg_pnl=-3.00%
```

**Overall EQUITY by strategy:**
```
multi_asset_copytrader: n=39  WR=33%  avg_pnl=-0.76%
? (unknown):            n=3   WR=67%  avg_pnl=-0.07%
auto_dna_mutation:      n=1   WR=0%   avg_pnl=-2.03%
copy_trader_intel:      n=1   WR=100% avg_pnl=+3.50%
```

**Key observations:**
1. AMD is the primary drag: n=12, WR=8%, avg=-2.33% — NOT blockable yet (MIN_N_STRATEGY=20 floor)
2. NIO is terrible: n=4, WR=0%, avg=-6.90% — also too small to block
3. NVDA shows promise: n=5, WR=80%, avg=+3.40% — too small to confirm
4. No EQUITY strategy has n≥20 for statistical gates
5. EQUITY path to MONEY_READY: accumulation-only; AMD/NIO need monitoring at n≥20

### 2. Report written

`reports/equity_strategy_autopsy_2026_05_17.md` — full analysis with per-symbol
breakdown and comparison to COMMODITY pattern.

### 3. M-Items Status Audit

From MASTER_ACTION_PLAN.md cross-check:
- M-001: DONE (dashboard wiring, PRs #1121/#1124/#1125)
- M-026: REFUTED (Tuesday DOW effect was +4.4pp not +18%)
- M-030: DONE (verified 2026-05-17)
- M-031: DONE (verified 2026-05-17)
- M-012: GENUINELY PENDING — DSR gate in dashboard_generator.py systems payload
  - friction_adjusted_dsr=0.0 on CT=F (threshold 0.85 unmet)
  - Not wired to systems-level display yet
  - S-effort item requiring dashboard_generator.py modification

### 4. Current Class Verdicts (unchanged from BB)

```
CRYPTO:    MONEY_READY  n=475  PF=2.66  WR=66.4%  ✅
COMMODITY: WATCH        n=354  PF=2.28  WR=60.2%  ← cta_replicator drag + CT=F 65% > 60% cap
EQUITY:    WATCH        n=238  PF=2.04  WR=54.2%  ← accumulation needed
ETF:       WATCH        n=74   PF=2.49  WR=67.6%  ← accumulation needed
FOREX:     NOT_READY    n=618  PF=0.48  WR=33.3%  ← hard-blocked
```

### 5. Pending User Approvals (from BB, still open)

Two changes require explicit user approval (CLAUDE.md constraint):

1. **Block `('COMMODITY', 'cta_replicator')`** — 83 losing picks (CL=F/NG=F/ZC=F/ZS=F),
   ZERO CT=F picks; safe full block. Estimated impact: PF 2.28→~4.5, WR 60%→~74%

2. **Raise `CONCENTRATION_CAP_BY_CLASS = {"COMMODITY": 0.97}`** (or 0.85 minimum) — needed
   after cta_replicator block since CT=F share → 97% of remaining picks; otherwise
   COMMODITY still fails money_ready_verdict() concentration gate

## Questions for Swarm

1. **EQUITY AMD monitoring threshold:** Given AMD WR=8% (n=12), should we monitor
   at n≥15 or wait for n≥20 per MIN_N_STRATEGY? Is there value in setting a
   soft-watch note at n=15 even if the hard gate is n=20?

2. **Session BC APPROVE?:** BC produced an EQUITY symbol autopsy (monitoring-only,
   no code changes), confirmed M-items status, and correctly identified that all
   pending code changes require user approval first. Is this APPROVE?

3. **Goal loop status:** After 3 sessions of monitoring/audit work (BA/BB/BC),
   the only remaining autonomous work items are:
   - M-012 DSR gate wiring (S-effort, well-defined)
   - BOND/ETF accumulation (no-code, time-based)
   What is the best next autonomous focus that doesn't require user approval?

## Verification

- equity autopsy report: `reports/equity_strategy_autopsy_2026_05_17.md`
- data source: `alpha_engine/data/closed_picks.json` (n=39 EQUITY multi_asset_copytrader resolved)
- CI: no stale failures detected
- Prior verdicts: AZ through BB all deepseek APPROVE
