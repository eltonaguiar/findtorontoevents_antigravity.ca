# Strategy Investigation: `stocks_competition`

**Date:** 2026-04-14  
**Authors:** Claude (Antigravity bot) + Cursor Cloud Agent  
**Status:** Rehab ruled out. **Awaiting user sign-off for hard block** per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.  
**Recommendation:** Add `stocks_competition` to `BLOCKED_SOURCE_SYSTEMS` in `audit_trail/quality_gates.py` and sync in `audit_dashboard/template.html`.

---

## Evidence

### Realized performance (canonical `dashboard_data.json`, 2026-04-14)

| Metric | Value |
|--------|-------|
| Total picks | 310 (raw), 210 (after definitive-exit + dedup) |
| Win rate | **28.1%** (21.9pp below 50% baseline) |
| Profit factor | **0.593** |
| Expectancy | **-1.54% per trade** |
| p-value (vs 50%) | **< 0.0001** |
| Platform baseline (all sources) | WR 45.6%, PF 1.26, Exp +0.25% |

This is 17.5pp below baseline WR and PF 0.593 vs platform 1.26 — a statistically significant loss-maker.

### 3-axis autopsy (`tools/mutation_analysis.py`)

| Axis | Finding |
|------|---------|
| Direction flip | **Not found** — insufficient trades on both sides |
| Timeframe flip | **Not found** — no timeframe variance exploitable |
| Symbol variance | **Not found** — WR is uniformly low across all symbols |

`stocks_competition` is absent from ALL rehabilitation sections. Other systems (claude_gainer_st, multi_asset_copytrader) DO show actionable mutations — stocks_competition does not.

### Sub-strategy breakdown

| Strategy | N | WR | Outcome |
|----------|---|-----|---------|
| **Breakout Momentum** | 39 | **56.4%** | ✅ Worth saving |
| Bollinger MR | 65 | 50.8% | ⚠️ Borderline |
| Short-Term Reversal | 39 | 35.9% | ❌ Losing |
| Consecutive Beats | 39 | 25.6% | ❌ Losing |
| **Value + Quality** | 48 | **6.2%** | ❌ Kill or inverse |
| ML Ranker | 46 | 31.8% | ❌ Losing |
| Earnings Drift | 19 | 15.8% | ❌ **Inverse confirmed (PF 2.07)** |

### Recommended action

**Option A (preferred):** Block `stocks_competition` as a system, but extract `Breakout Momentum` as a standalone strategy via `kimi_riseoftheclaw` or a new source system. This preserves the one sub-strategy that works.

**Option B:** Add to `BLOCKED_SOURCE_SYSTEMS` entirely. Simple, immediate.

### Proposed code change (for user approval)

```python
# audit_trail/quality_gates.py — BLOCKED_SOURCE_SYSTEMS
BLOCKED_SOURCE_SYSTEMS = {
    # ... existing ...
    "stocks_competition",  # 2026-04-14: n=210 WR 28.1% PF 0.593 p<0.0001
                           # 3-axis autopsy: no direction/timeframe/symbol rehab path
                           # Investigation: docs/strategy_audits/stocks_competition_2026-04-14.md
}
```

Plus matching entry in `audit_dashboard/template.html`'s `BLOCKED_SYSTEMS` set.

---

## LOST Exit-Reason Correction (from Claude's PR #188)

**Important context for this investigation:** Claude's forensic analysis (Issue #186, PR #188) proved that `LOST` exit labels are NOT equivalent to `SL_HIT`. The data:

- 92% of forex LOST picks have |pnl| < 0.5% (well below forex SL median of 0.5%)
- 60% exit within 0.1% of entry price — positions never moved
- Root cause: copy-trader scraper writes binary `outcome: "WON"|"LOST"` which leaks into `exit_reason` via dashboard_generator.py fallback chain

This means the "definitive exits only" filter used in earlier analyses was excluding real losses, inflating PF. The honest all-picks numbers (from the live dashboard) should be used as the ground truth for strategy evaluations.

---

*Per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` escalation ladder stage 5.*
