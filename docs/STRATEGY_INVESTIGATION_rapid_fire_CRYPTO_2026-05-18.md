# Strategy Investigation: rapid_fire CRYPTO/FOREX
**Date:** 2026-05-18 (Session CK) | Updated: 2026-05-18 (Session CU)
**Analyst:** Claude Code (Session CK → CU) + 3-engine swarm (deepseek/kilo/xai)
**Status:** ~~MONITOR~~ → **KILL RECOMMENDED** (pf_registry update shows deterioration)

---

## Summary

`rapid_fire` is a multi-class source system (asset_classes=['CRYPTO','FOREX']) with
borderline positive expectancy: WR=40%, PF=1.10, total_pnl=+23.6% on n=148 resolved picks.

**Recommendation: DATA QUALITY FLAG — Raw vs dashboard discrepancy. Pause paper sizing pending data audit.**
Dashboard shows WR=40.5%, PF=1.10 but also shows a second entry with PF=0.97 (negative).
Raw closed_picks.json shows WR=25.5%, PF=0.15 (n=196 CLOSED picks) — likely different calculation basis.
Do NOT block yet (insufficient clean data), but do NOT size for real money until data consistency is resolved.

---

## Performance Data (source: dashboard_data.json 2026-05-18T03:07:49Z)

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| n (resolved) | 148 | ≥100 | ✅ Sufficient |
| Win Rate | 40% | ≥50% | ❌ FAIL |
| Profit Factor | 1.10 | ≥1.5 (T2) | ⚠️ Sub-T2 |
| Total PnL | +23.6% | >0% | ✅ Positive |
| Avg PnL/pick | — | >0% | ✅ Positive |
| Avg Win | 4.33% | — | — |
| Avg Loss | 2.71% | — | — |
| Max Drawdown | 69.2% | ≤20% | ❌ FAIL |
| Last signal | 2026-05-18 | — | Still active |
| Blocked | False | — | Not blocked |

**Kelly check:** (WR × r - (1-WR)) / r = (0.40×1.60 - 0.60) / 1.60 = **(0.64-0.60)/1.60 = +0.025 (positive)**
→ Positive Kelly = positive expectancy = tradeable, but small edge.

**Risk/reward ratio:** avg_win/avg_loss = 4.33/2.71 = 1.60. A WR=40% with RR=1.60 breaks even
at exactly WR=(1/(1+1.60)) = 38.5%. System is marginally above breakeven.

---

## Contrast With Blocked Systems

| System | WR | PF | Total PnL | Kelly | Status |
|--------|----|----|-----------|-------|--------|
| super_signals | 33% | 0.65 | -85.6% | -0.095 | Block recommended |
| aggregated_picks | 35% | 0.93 | -8.9% | -0.026 | Block recommended |
| **rapid_fire** | **40%** | **1.10** | **+23.6%** | **+0.025** | **Monitor** |

Unlike super_signals and aggregated_picks, rapid_fire has:
- Positive total PnL (not destroying capital)
- Positive Kelly (system has edge, however thin)
- Higher win rate (40% vs 33-35%)

---

## Why Not T2-Ready

1. **WR=40%** is 10pp below the T2 floor of 50%. Even with a good RR ratio, low WR leads to
   long losing streaks and the observed MDD=69.2% (far above the 20% charter limit).

2. **PF=1.10** is the minimum viable; T2 requires PF≥1.5. The system would need to improve
   avg_win, improve WR, or reduce avg_loss by ~36% to reach T2.

3. **MDD=69.2%** is catastrophic for live trading. Even with positive Kelly, this cannot be
   sized using standard Kelly fractions at account level.

4. **Multi-class (CRYPTO+FOREX)**: If FOREX component has negative edge (dashboard shows FOREX
   PF=66.85 data artifact, likely broken), the CRYPTO component alone may be stronger. A
   CRYPTO-only filter test is warranted.

---

## Mutation Protocol Assessment

### Axis 1: Direction Filter
- If rapid_fire signals are LONG-dominant (typical for crypto momentum), filtering to LONG-only
  in a bull regime may improve WR. Dashboard does not provide directional breakdown.

### Axis 2: Symbol Filter
- CRYPTO: if rapid_fire FOREX is broken (WR artifact), CRYPTO-only may have PF≥1.5.
- Recommendation: export closed_picks CSV filtered to source_system='rapid_fire' and asset_class='CRYPTO'
  to compute CRYPTO-specific metrics.

### Axis 3: Time-of-Day Filter
- "rapid_fire" name suggests high-frequency / intraday timing dependency.
- If picks cluster in specific hours (e.g., high-liquidity windows 08-16 UTC), time filter may
  significantly improve WR. Requires timestamp data from pick_lifecycle_log.

**Verdict: Mutation viable — CRYPTO-only sub-filter is the highest-priority test.**

---

## Recommended Action

1. **Do NOT block** — positive Kelly and positive total PnL; system is not a drag.
2. **Paper-trade sizing only** — MDD=69.2% makes live sizing unsafe. If traded: cap at 1-2%
   per pick (far below Kelly) until WR improves.
3. **Run CRYPTO-only mutation** — export from closed_picks, compute CRYPTO-specific PF.
   If CRYPTO-only PF≥1.5 and WR≥50%, candidate for promotion to T2 filter.
4. **Next review:** 2026-08-18 (90 days). If CRYPTO-only mutation shows T2 metrics at n≥100,
   consider adding to weekly filter with reduced sizing.

---

## Impact on CRYPTO System-Wide Metrics

rapid_fire is NOT a significant drag:
- PF=1.10 is above 1.0 (positive contribution to system PF)
- Removing rapid_fire would slightly LOWER CRYPTO system-wide PF (losing a positive-PnL source)
- Contrast with super_signals (PF=0.65) and aggregated_picks (PF=0.93) which are active drags

No action required for system-wide CRYPTO PF improvement.

---

## Review Date

Review on 2026-08-18 (90 days). Key triggers for earlier review:
- CRYPTO-only sub-filter computed and shows T2 metrics → promote to weekly filter
- WR drops below 35% on next 50 picks → re-evaluate for block

---

## Addendum — Session CU (2026-05-18T22:00Z) — pf_registry policy-clean update

### Updated Data (pf_registry.json 2026-05-19T02:18:04Z, policy_clean_net)

| Metric | Old (CK, dashboard) | New (CU, pf_registry) | Change |
|---|---|---|---|
| n | 148 | **91** | −57 (dedup removed re-emissions) |
| WR | 40% | **33%** | −7pp |
| PF | 1.10 | **0.368** | −0.73 |
| Total PnL | +23.6% | **−13.07%** | NEGATIVE |
| Kelly | +0.025 | **−0.563** | NEGATIVE |

**Source discrepancy resolved:** the Session CK doc used `dashboard_data.json::performance` (raw, includes re-emissions). The pf_registry policy-clean view deduplicates re-emitted picks — same signal emitted multiple scan cycles counts once. Policy-clean n=91 is the authoritative count.

### Revised Kelly at n=91

- avg_win = 7.59% / 30 wins = **0.253% per win**
- avg_loss = 20.66% / 61 losses = **0.339% per loss**
- RR = 0.253/0.339 = **0.746** (wins smaller than losses)
- Kelly = (WR × RR − (1−WR)) / RR = (0.33 × 0.746 − 0.67) / 0.746 = **−0.563** (NEGATIVE)

### 3-Engine Swarm Recommendation

| Engine | Verdict | Reasoning |
|---|---|---|
| deepseek | BLOCK | n=91 ≥30, PF<0.5, evidence threshold met |
| kilo | BLOCK | Highest-ROI action; cleans CRYPTO PF |
| xai | (no response) | — |

### Kill Proposal

Add to `audit_trail/quality_gates.py::BLOCKED_ASSET_STRATEGY_PAIRS`:
```python
("CRYPTO", "rapid_fire"),  # n=91 WR=33% PF=0.37 Kelly=-0.56 — CU 2026-05-18
```

**Awaiting user approval per CLAUDE.md constraint (no BLOCKED_ASSET_STRATEGY_PAIRS edit without explicit approval).**
