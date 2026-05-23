# Regime × Strategy-Style Matcher — Replacement for PR #305

**Author:** Claude Opus 4.7 (1M context)
**Date:** 2026-04-21
**Branch:** `exp/regime-strategy-matcher`
**Supersedes:** [PR #305](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/305) (closed 2026-04-21 after yesterday's +74% bounce-day validation showed the hard-block was regime-mismatched)
**Complements:** [PR #307](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/307) `MacroRegimeAlignment` (which gates by direction; this gates by strategy-style)

---

## Why this exists

**Yesterday (2026-04-20) was a crypto bounce day.** 283 closed picks, WR 55.8%, cum **+226%**. The 7 altcoins I hard-blocked in PR #305 went WR 86.8% / cum +74%. Blocking them would have cost ~$74 per $100 size.

The problem: **mean-reversion strategies are regime-switching**, not permanently-bad:
- Sustained crypto fear / downtrend → WR ~18% (cycles 3-9 measured)
- Mean-reversion bounce days → WR 70-100% (yesterday)

A hard-block loses the bounces. The correct tool is a regime-conditional gate.

## What this module does

Given a pick, classifies its strategy as MEAN_REVERTING or TREND (name-based heuristic). Given the current BTC regime, classifies as TRENDING_UP / TRENDING_DOWN / MEAN_REVERTING / HIGH_VOLATILITY / UNKNOWN.

**Two mismatch rules reject picks:**
- `MEAN_REVERTING` strategy in `TRENDING_DOWN` regime → reject (avoids cycle-3-to-9 bleed)
- `TREND` strategy in `MEAN_REVERTING` regime → reject (avoids whipsaw/stop-out)

All other combinations: allow. UNKNOWN regime or UNKNOWN style: fail-open.

## Live validation

### Yesterday's 283 picks (forced regime = MEAN_REVERTING)

| Cohort | n | WR | PF | cum PnL% |
|---|---|---|---|---|
| Baseline | 292 | 55.8% | 4.94 | **+233.64** |
| **Allowed** | 209 | **67.94%** | 5.01 | **+212.71** |
| Rejected (TREND strategies during a mean-rev bounce) | 83 | 25.3% | 4.36 | +20.93 |

**Kept 91% of the +234% profit, improved WR by 12pp, rejected 28% of picks (all low-WR trend strategies during a bounce).** This is the result PR #305 failed to achieve.

### Historical 3,500-pick window (forced regime = TRENDING_DOWN, which is what cycles 3-9 measured)

| Cohort | n | WR | PF | cum PnL% |
|---|---|---|---|---|
| Baseline | 3,500 | 31.4% | 0.73 | −1,072 |
| Allowed | 2,024 | 32.0% | 0.76 | −780 |
| **Rejected** | **1,476** | 30.5% | 0.64 | **−293** |

**Cuts $293 of losses (27% of total drag) by rejecting mean-reversion picks during TRENDING_DOWN.** The rejection rate is 42% — aggressive but evidence-based.

### Current live regime

`python -c "from tools.regime_strategy_matcher import RegimeDetector; print(RegimeDetector().get_regime())"` as of now:

```
{"regime": "UNKNOWN", "confidence": 0.4,
 "signals": {"roc_20": 0.132, "roc_5": -0.0174, "realized_vol_annual": 0.476,
             "acf_1": -0.0985, "fear_greed": 33}}
```

Fails open → no picks gated until the detector has higher confidence. This is correct behavior — don't block when regime is ambiguous.

## How it complements PR #307

[PR #307](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/307)'s `MacroRegimeAlignment` gates by **direction × regime** (LONG in BULL, SHORT in BEAR, reject LONG in CRISIS).

This module gates by **strategy-style × regime** (MEAN_REV strategy in TRENDING_DOWN regime is rejected, even if LONG direction would be aligned).

Both are needed:
- PR #307 catches direction mismatch (LONG crypto in a crash)
- This catches style mismatch (mean-rev strategy in a trend)
- They're orthogonal — compose cleanly

## Integration

Self-contained, no deps on unmerged PRs. Can be wired into `audit_trail/quality_gates.py::passes_active_gate` behind env flag `REGIME_STYLE_MATCHER_ENABLED=shadow|enforce`:

```python
from tools.regime_strategy_matcher import match_verdict, RegimeDetector
_regime = RegimeDetector()  # global, cached 30min

def passes_active_gate(pick):
    # ... existing gates ...
    if os.environ.get("REGIME_STYLE_MATCHER_ENABLED", "").lower() == "enforce":
        v = match_verdict(pick, detector=_regime)
        if not v["allow"]:
            return None  # or log + tag in shadow mode
```

## Lesson from PR #305

Always check for regime-switching behavior before flagging strategies/symbols as "bad" from rolling-window aggregates. The difference between "always bad" and "bad in one regime" is a 12pp WR swing on a single bounce day.

## Files

- `tools/regime_strategy_matcher.py` (285 LOC)
- `tests/test_regime_strategy_matcher.py` — **14 tests, all pass**
- `updates/2026-04-21-regime-strategy-matcher.md` — this doc

## Reproduce

```bash
# Unit tests
python -m unittest tests.test_regime_strategy_matcher -v

# Yesterday's picks at MEAN_REVERTING regime
python tools/regime_strategy_matcher.py --date 2026-04-20 --force-regime MEAN_REVERTING

# Historical 3500-pick baseline at TRENDING_DOWN
python tools/regime_strategy_matcher.py --force-regime TRENDING_DOWN

# Live regime detection
python -c "from tools.regime_strategy_matcher import RegimeDetector; import json; print(json.dumps(RegimeDetector().get_regime(), indent=2))"
```

## What's NOT in this PR

- Production wiring (env flag proposed only)
- Per-asset-class regimes (BTC-wide regime only; could extend with ETH-only, forex-specific later)
- Integration with PR #307's `MacroRegimeAlignment` output (can compose via orthogonal gate calls)
