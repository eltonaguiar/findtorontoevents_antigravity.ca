# Session Review — 2026-05-17 Session U

## Context
Multi-session autonomous trading-edge audit for findtorontoevents.ca/audit.
All work is on the `alpha_engine/` + `tools/` + `audit_trail/` stack.

## Work Completed This Session

### M-061: money_ready_verdict() — Per-class DSR+PBO+SPA unified verdict
- File: `alpha_engine/money_ready_verdict.py` (NEW, committed)
- `tests/test_money_ready_verdict.py` (NEW, 6/6 passing)
- Output as of 2026-05-17:
  - COMMODITY = MONEY_READY (n=354, WR=60.2%, PF=2.28, DSR=PASS, SPA=PASS)
  - EQUITY = WATCH [DASH] (n=240, WR=53.3%, PF=1.97, DSR=FAIL — WR<55%)
  - CRYPTO = WATCH (n=631, WR=66.6%, PF=0.76 — big losers wiping wins)
  - ETF = WATCH [DASH] (n=74, WR=67.6%, PF=2.41 — n<MIN_N_CLASS=100)
  - FOREX = NOT_READY (n=932, WR=25.6%, PF=0.35)
  - BOND = INSUFFICIENT_DATA (n=12, WR=50%, PF=0.54 via dashboard fallback)
  - FUTURES = NOT_READY (n=203, WR=3.0%, PF=0.06)

### PBO N/A fix (MIN_STRATEGIES_FOR_PBO=5)
- PBO returns N/A when fewer than 5 strategies — prevents spurious FAIL on COMMODITY (2 strategies)
- Committed to `alpha_engine/money_ready_verdict.py`

### Dashboard fallback
- When closed_picks.json has <MIN_N_CLASS picks, money_ready_verdict() reads dashboard_data.json
- Fixes EQUITY showing n=44 instead of n=240 (root cause: closed_picks only = local MySQL subset)

### Gate 7c: COMMODITY confidence floor = 0.55
- `audit_dashboard/hc_filter.js`: `commodityConfidenceMin: 0.55`
- `audit_trail/quality_gates.py`: BLOCKED_DIRECTION_TRIPLES += (FOREX, multi_asset_copytrader, LONG)
- Committed e26a0fcad5

### White's Reality Check + Winsorization
- `tools/whites_reality_check.py`: added `winsorize_returns()` ±5σ flag
- 9 strategies pass both raw and winsorized: edge is not driven by outlier returns
- Committed 40fd0a8357

### pending_spa_scan.py (NEW, now on main: a7fab78fb9)
- `tools/pending_spa_scan.py`: scans strategies with 5≤n<20 (below SPA testability threshold)
- 4 alerts: combined_confidence (n=19, WR=31.6%), cta_commodity_momentum_term (n=11, WR=0%), 2 ML CRYPTO stacks (n=12, WR=16.7%)

### CRYPTO root cause analysis
- APEUSDT SHORT: SL at $0.121 but exit at $0.2098 (73% past stop) → stops NOT being honored
- TRXUSDT LONG: genuine -79% price crash
- Without those 2: elite CRYPTO PF runs 2-60+
- Recommendation: P0 stop-loss enforcement audit in execution layer

### Reports committed
- `reports/money_ready_verdict_2026-05-17.md` + `.json`
- `reports/whites_reality_check_winsorized_2026-05-17.md`
- `updates/index.html`: new entry for sessions Q/R/S/U milestones

## Key Open Questions for Swarm Review

**Q1: EQUITY gate mismatch**
Dashboard says EQUITY ACTIVE + sizing=YES, but money_ready_verdict() returns WATCH (DSR=FAIL, WR=53.3% < 55% threshold). Should EQUITY be sized down until WR hits 55%? Or is the gate too strict for EQUITY (institutional WR benchmarks accept 52%)?

**Q2: CRYPTO stop-loss P0**
APEUSDT SHORT exited at $0.21 vs SL at $0.121 (73% past stop). This means the live execution system is NOT honoring stops. What files in the execution path should be audited? Where does `alpha_engine/` hand off to the live trade executor? Is there a stop_loss_monitor.py or similar?

**Q3: combined_confidence strategy governance**
`combined_confidence` has n=19, WR=31.6% — 1 pick away from SPA threshold but already failing WR. Should this be pre-blocked (BLOCKED_ASSET_STRATEGY_PAIRS) now, or wait for n=20 to let SPA formally decide? Risk: letting a losing strategy accumulate 1 more pick to "prove" it's bad.

**Q4: pending_spa_scan integration**
`tools/pending_spa_scan.py` runs standalone. Should it be wired into the nightly quality gate scan (e.g., called by `audit_trail/quality_gates.py` or `dashboard_generator.py`)? Where in the pipeline should governance-before-threshold alerts appear on the dashboard?

**Q5: FUTURES NOT_READY (WR=3%)**
FUTURES shows n=203, WR=3%, PF=0.06 — catastrophically bad. Is this a data pipeline issue (futures symbols not resolving correctly, expiry dates causing false losses), a strategy failure, or a classification error? Should FUTURES picks be classified under their underlying asset class instead (e.g., CT=F under COMMODITY)?

**Q6: signal_tracker accuracy 59.3% vs 65% target**
`OPTIMIZATION_REPORT.md` at repo root (auto-generated 2026-05-17T09:09Z) shows 8 tweaks applied but still 5.7% below target. Which asset classes are dragging accuracy? Are any of the disabled signals (SOL-USD, DOGE-USD, GBP-USD) recoverable with better timeframes vs permanent kills?

## Data Sources (READ-ONLY, never invent)
- `audit_dashboard/data/dashboard_data.json::performance.asset_class_health`
- `audit_trail/quality_gates.py::BLOCKED_ASSET_STRATEGY_PAIRS`
- `alpha_engine/money_ready_verdict.py`
- `tools/pending_spa_scan.py`
- `OPTIMIZATION_REPORT.md` (auto-generated, repo root)

## Required Output Format
```json
{
  "questions": [
    {
      "id": "Q1",
      "verdict": "pre-block|wait|needs-data|already-handled",
      "reasoning": "...",
      "recommended_action": "...",
      "files_to_change": ["..."]
    }
  ],
  "additional_action_items": [
    {"priority": "P0|P1|P2", "description": "...", "owner": "claude-code|pa-console|human"}
  ],
  "blocker_risks": ["..."]
}
```
