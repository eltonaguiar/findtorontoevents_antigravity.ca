# B19 — Pair-level exception carve-out for proven (strategy, symbol) pairs

**Date:** 2026-05-02  
**Goal:** #1 (phenomenal performance)  
**Risk:** MEDIUM (default-OFF gate change; requires explicit opt-in)

## Problem

The Smart Picks gate (`passes_smart_gate`) filters picks using strategy-level
aggregate stats. When a strategy has proven pair-specific edge that its
strategy-wide average understates, genuinely profitable picks get blocked.

**Verified case:** `atr_percentile_gate BTCUSDT LONG`
- n=25 closed picks, WR=84.0%, Wilson 95% lower bound=65.3%
- Expected value per unit risk: +0.605 (WR × R:R − loss probability)
- Currently **blocked by the R:R < 1.5 floor** (actual R:R=0.91)
- R:R-based rejection is incorrect when WR is this high — the R:R gate
  assumes ~50% WR baseline, not 84%

## Solution

A hard-coded registry in `alpha_engine/pair_exceptions.py` stores `(strategy, symbol, direction)` triples that meet:
- Wilson 95% lower bound ≥ 60%
- n ≥ 20 closed picks

When `PAIR_EXCEPTION_CARVE_OUT_ENABLED=1`, registry entries bypass the
score-floor, R:R-floor, and forward-WR-floor checks in `passes_smart_gate`
and `passes_active_gate`. They are tagged `exception_carve_out=True` on /audit.

## What's NOT bypassed

Even with the flag ON, carve-outs do NOT bypass:
- `BANNED` trust tier (catastrophic trust block)
- `BLOCKED_SYMBOLS` (data quality issues)
- `is_strategy_blocked` (deliberately killed strategies)
- `SCALP` mode gate (24.8% empirical WR kill zone)
- `panic` health gate

## Files changed

| File | Change |
|---|---|
| `alpha_engine/pair_exceptions.py` | NEW — registry + `should_pair_exception_pass()` |
| `audit_trail/quality_gates.py` | Add carve-out check in `passes_active_gate` + `passes_smart_gate` |
| `tools/derive_pair_exceptions.py` | NEW — weekly analysis tool to propose candidates |
| `tests/test_quality_gates.py` | 6 new B19 tests |

## Initial registry

```python
PairExceptionEntry(
    strategy="atr_percentile_gate",
    symbol="BTCUSDT",
    direction="LONG",
    n=25, wr_pct=84.0, wilson_lb_pct=65.3,
    verified_date="2026-04-30",
)
```

## Activation

```bash
export PAIR_EXCEPTION_CARVE_OUT_ENABLED=1
```

Default-OFF. Operator flips on after reviewing the initial candidate list.

## Adding new entries

1. Run `python tools/derive_pair_exceptions.py --check-current` weekly
2. Review candidates meeting Wilson lb ≥ 60% / n ≥ 20
3. Submit a code-change PR modifying `alpha_engine/pair_exceptions.py`
   (auto-writes to the registry are explicitly prohibited)

## Source

- Queue doc: `reports/REMAINING_ACTION_ITEMS_2026_04_30.md` row 32 (B19)
- Multi-AI feedback: `reports/feedback/B19-*.md`
- Verification: `atr_percentile_gate BTCUSDT LONG` in `audit_dashboard/data/dashboard_data.json` recent_closed pool
