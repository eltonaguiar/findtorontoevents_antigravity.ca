# Session AL — Swarm Review Request
# Date: 2026-05-17
# Session: AL (following AK — APPROVE)

## Context

Session AL primary focus: verification and next-step investigation following M-037 bug fix (Session AK).

## AK Summary (deployed before AL)

Fixed M-037 bug where `ml_score=0` was treated as "below floor" instead of "not populated", causing ALL CRYPTO active picks to show `active=0` in dashboard. Fix: `if _m037_ml is not None and _m037_ml > 0`. Swarm AK APPROVED with 2 conditions both applied (epsilon comment + boundary test for 0.001).

## Session AL Findings

### 1. CI is GREEN (confirmed)
- Latest CI Tests run: success (databaseId: 25994411552, completed ~15:17 UTC)
- All 4941 tests pass, 37 skipped, 1 xfailed
- M-037 boundary tests (3 new in AK) all green

### 2. Bond Scanner — Running OK, Low Historical PF

**Finding:** ETF & Bond Scanner workflow runs successfully daily. Bond picks are committed to repo. Current state:
- `alpha_engine/data/active_picks_bond.json`: 8 picks generated 11:46 UTC
- All 8 picks pass quality gates (confirmed via `passes_active_gate()`)
- Dashboard BOND: n=12 resolved, WR=50%, PF=0.66 — below T2 floor
- BOND verdict: INSUFFICIENT_DATA (CB-30d n=0)

**Bond picks currently active:**
- 3× `bond_yield_momentum` SELL (TLT, IEF, TLH) — confidence=0.58
- 3× `bond_mean_reversion` BUY (TLT, IEF, LQD) — confidence=0.67-0.70
- 2× `bond_yield_curve_slope` (TLT SELL, IEF BUY) — confidence=0.59-0.66

**PF=0.66 concern:** The 12 resolved bond picks have worse PF than break-even. This is a genuine strategy quality issue, not a data pipeline bug. The `bond_connors_rsi2` strategy (Session AF) was backtested at WR=50% PF=1.34 (WATCH status).

### 3. EQUITY "WATCH" Instead of "MONEY_READY"

**Finding:** EQUITY money_ready_verdict = "WATCH" despite T1 performance (WR=54.2%, PF=2.04).

**Root cause:** money_ready_verdict requires ≥2 strategies with n≥20 for PBO/SPA validation. EQUITY has:
- n=240 resolved picks across 114 strategies → avg ~2 picks/strategy
- DSR: n=7 too small
- PBO: need ≥2 strategies with n≥20, got 0
- SPA: no strategies with n≥20

**Implication:** EQUITY is producing good results (T1) but statistical tests can't be computed because picks are spread too thin across many strategies.

**Concentration concern:** `top_symbol_share: 0.5714` for NIO — 57% of EQUITY picks are NIO (from money_ready_verdict concentrations field). This may be correct (kimi_riseoftheclaw focuses on NIO) but suggests a narrow strategy base.

### 4. Dashboard Active Picks = 0

**Finding:** Dashboard generated at 14:21 UTC (before M-037 commits at ~14:30 UTC) shows `active=0` for all classes. This is expected — the Unified Audit Dashboard workflow runs every hour. Next regeneration (~15:21 UTC) should show CRYPTO active > 0 from non-ML sources.

### 5. FOOLPROOF Status

All remaining FOOLPROOF items are externally blocked:
- COT CFTC pipeline: needs external data feed
- Per-class ml_score gate ≥55: ml_score not populated upstream  
- FRED GDP/ISM macro overlay: FRED API key needed
- `bond_scanner.py --merge` manually: workflow IS already doing this (item is stale)

The `bond_scanner.py --merge` FOOLPROOF item (line 146) is stale — the ETF & Bond Scanner workflow runs this daily. No manual action needed.

### 6. feed_hygiene.py Soft-Fill Analysis

**Swarm AK+1 recommendation**: fix upstream CRYPTO sources to emit `ml_score=None` instead of `ml_score=0`. Analyzed and decided NOT to change feed_hygiene.py soft-fill for these reasons:
- `_SCHEMA_SOFT_DEFAULTS = {"ml_score": 0.0}` fills missing/None ml_score with 0.0
- Changing to None would break `sig.get("ml_score", 0.0)` calls (would return None not 0.0)
- M-037 gate fix (treating 0 as sentinel) is sufficient and correct
- Belt-and-suspenders change not justified given risk of breaking other gates

## Questions for Swarm

1. **BOND PF=0.66 remediation**: With 12 resolved picks and PF=0.66, what's the right action? Options:
   a) Continue accumulating (natural variance at n=12)
   b) Review bond strategy quality gates (add bond-specific gates)
   c) Block bond_scanner temporarily until strategy is validated
   d) Change bond strategies (move away from yield momentum)

2. **EQUITY concentration**: NIO at 57% of EQUITY picks is concerning for production use. Should we add a per-symbol concentration cap specifically for EQUITY, or is this already handled by `concentration_cap.py`?

3. **EQUITY WATCH → MONEY_READY path**: With 114 strategies and n=240 total, no strategy has n≥20. This means the money_ready_verdict can never become MONEY_READY via statistical tests without strategy consolidation. Should we:
   a) Lower the PBO threshold (from n≥20 to n≥10)?
   b) Focus EQUITY on 2-3 proven strategies and block the rest?
   c) Accept WATCH as the verdict until natural accumulation reaches threshold?

4. **feed_hygiene.py sentinel decision**: Was the decision to NOT change the soft-fill correct? Any concerns with using 0.0 as a sentinel that M-037 treats as "not populated"?

5. **Overall verdict**: Is Session AL APPROVE?

## Verification

- CI Tests: success (25994411552)
- Bond picks gate test: 8/8 pass
- FOOLPROOF items: all remaining are external-blocked or stale
- M-037 fix confirmed working in tests

## Current Dashboard State (14:21 UTC — 1h stale)

| Class | n | WR | PF | CB-30d WR | CB-30d n | Verdict |
|-------|---|----|----|-----------|----------|---------|
| EQUITY | 240 | 54.2% | 2.04 | 59.8% | 84 | WATCH |
| COMMODITY | 228 | 85.5%* | 7.71* | 56.9% | 65 | WATCH |
| CRYPTO | 6,836 | 47.8% | 1.44 | 46.1% | 2,881 | MONEY_READY |
| ETF | 74 | 67.6% | 2.49 | 68.2% | 44 | WATCH |
| FOREX | 98 | 37.8% | 2.23 | 48.5% | 33 | NOT_READY |
| BOND | 12 | 50.0% | 0.66 | N/A | 0 | INSUFFICIENT_DATA |

*COMMODITY PF=7.71 inflated by COT dedup; CB-30d WR=56.9% is authoritative
