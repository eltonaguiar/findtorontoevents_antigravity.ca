# Ban Protocol Audit — 2026-05-19

**Agent:** Explore subagent (adf5203d83a253da4)  
**Scope:** `audit_trail/quality_gates.py` — BLOCKED_SOURCE_SYSTEMS, BLOCKED_ASSET_STRATEGY_PAIRS, BLOCKED_SYMBOLS, BLOCKED_DIRECTION_TRIPLES, PROBATION_STATUS, PENDING_UNBLOCK_REVIEW

---

## Finding 1: Documentation Completeness — PARTIALLY DOCUMENTED (CRITICAL GAPS)

| Block List | Total | With Review Dates | Coverage |
|---|---|---|---|
| BLOCKED_SYMBOLS | 23 | 7 (via PENDING_UNBLOCK_REVIEW) | 30% |
| BLOCKED_SOURCE_SYSTEMS | 17 | 0 | 0% |
| BLOCKED_ASSET_STRATEGY_PAIRS | 100+ | 0 (comments only) | 0% |
| BLOCKED_DIRECTION_TRIPLES | 15+ | 0 | 0% |
| PROBATION_STATUS | 1 | 1 (LUXALGO_CONFLUENCE) | 100% ✓ |

**PROBATION_STATUS** is the only block type with proper review machinery (review_date field, reblock_trigger logic, full metrics dict).

---

## Finding 2: Automatic Re-Review — NO MECHANISM EXISTS

- Only `PROBATION_STATUS` has `reblock_trigger` logic (WR<50% on n≥20 OR n stagnates <5 new picks in 14d)
- Zero automation for BLOCKED_SYMBOLS, BLOCKED_SOURCE_SYSTEMS, BLOCKED_ASSET_STRATEGY_PAIRS
- No scheduled jobs, monitor loops, or alert system in quality_gates.py
- Hypothesis registry (H-series, M-107) does NOT cross-reference blocked symbols for re-testing

---

## Finding 3: Stale / Overdue Reviews

**Overdue review dates (as of 2026-05-19):**

| Symbol | Review Date | Status | Days Overdue |
|---|---|---|---|
| TRXUSDT | 2026-05-30 | SHADOW (PENDING_UNBLOCK_REVIEW) | +11 |
| CVX | 2026-05-30 | PROBATION_STATUS | +11 |
| XOM | 2026-05-30 | SHADOW (PENDING_UNBLOCK_REVIEW) | +11 |
| NVDA | 2026-08-01 | PENDING_UNBLOCK_REVIEW | future (73d) |
| JTOUSDT | 2026-08-01 | PENDING_UNBLOCK_REVIEW | future (73d) |
| XLMUSDT | 2026-08-01 | PENDING_UNBLOCK_REVIEW | future (73d) |
| ICPUSDT | 2026-08-01 | PENDING_UNBLOCK_REVIEW | future (73d) |
| RENDERUSDT | 2026-08-01 | PENDING_UNBLOCK_REVIEW | future (73d) |

**Permanently blocked risk:** ~147 entries (all 23 BLOCKED_SYMBOLS not in PENDING list, all 17 BLOCKED_SOURCE_SYSTEMS, 100+ BLOCKED_ASSET_STRATEGY_PAIRS) have zero review cadence.

---

## Finding 4: Duplicate/Redundant Blocks

| Issue | Location | Assessment |
|---|---|---|
| CVX in both EQUITY_BLOCKED_SYMBOLS + PROBATION_STATUS | lines ~1967, ~7272 | INCONSISTENCY — remove from EQUITY_BLOCKED_SYMBOLS on next unblock promotion |
| KATUSDT/TRXUSDT comment "MERGED above" but still in BLOCKED_SYMBOLS | line ~2419 | STALE COMMENT |
| cta_commodity_momentum_term in BLOCKED_SOURCE_SYSTEMS + PF_REGISTRY_POLICY_EXCLUDED | multiple | INTENTIONAL defense-in-depth |
| futures_momentum in PERMANENTLY_KILLED + MONITORED_FUTURES_STRATEGIES | per session DA | INTENTIONAL (monitor-only for stats) |

---

## Finding 5: Threshold Inconsistency — CRITICAL LOGIC BUG

Current thresholds (scattered across 5+ locations):

| Stage | min_n | min_wr | min_pf | Location |
|---|---|---|---|---|
| SHADOW | 10 | 50% | 1.3 | line ~1959 |
| PROBATION | 20 | 52% | 1.3 | line ~1962 |
| FULL (comment) | 30 | 52% | **1.2** | line ~1993-1995 |

**Bug:** FULL unblock requires PF≥1.2, but PROBATION requires PF≥1.3. A symbol could pass FULL while failing PROBATION — logically backwards. FULL should be stricter (PF≥1.5).

**Thresholds scattered across:** SMART_PICKS_MIN_SCORE (line 412), SMART_PICKS_MIN_TRUST_SCORE (line 792), `active_non_crypto_forward_wr_floor()` (lines ~1689-1710), unblock criteria comment (lines ~1993-1995). No single config constant.

---

## Finding 6: Unblock Mechanism

3-Stage Protocol documented at line ~1958:
1. **SHADOW** — passive monitoring, no live picks
2. **PROBATION** — 50% sizing, live picks allowed, tracked in PROBATION_STATUS dict
3. **FULL** — unrestricted, requires `updates/YYYY-MM-DD-symbol-rehab-<SYMBOL>.md`

Only 1 symbol (LUXALGO_CONFLUENCE) has been promoted through this process. No reblock triggers defined for SHADOW or FULL stages (only PROBATION has `reblock_trigger`).

---

## Finding 7: Gate Enforcement Summary

All blocks are hard-reject by default via gate functions:

| Block Type | Gate Function Location | Fail-Open Env Override |
|---|---|---|
| BLOCKED_SOURCE_SYSTEMS | lines ~8283-8285 | `UNIVERSAL_BLOCKED_SYMBOLS_GATE_DISABLED` |
| BLOCKED_SYMBOLS | lines ~7114-7119 | UEPS long-horizon bypass option |
| EQUITY_BLOCKED_SYMBOLS | lines ~7272-7276 | `EQUITY_SYMBOL_GATE_DISABLED` |
| BLOCKED_ASSET_STRATEGY_PAIRS | lines ~7975-7980 | — |
| BLOCKED_DIRECTION_TRIPLES | lines ~6447-6451 | `DIRECTION_TRIPLE_GATE_DISABLED` |

---

## 5 Concrete Optimization Recommendations

### Rec 1 (HIGH): Create unified block registry JSON
Create `audit_trail/blocked_registry.json` with structured schema per block entry:
```json
{
  "symbol": "MATICUSDT",
  "blocked_date": "2026-04-02",
  "block_reason": "delisted, phantom TIME_EXIT trades",
  "stats_at_block": {"n": 424, "wr": 0.0, "pf": null, "pnl_pct": -63.6},
  "review_date": "2026-07-02",
  "stage": "SHADOW",
  "unblock_criteria": {"min_n": 30, "min_wr": 0.52, "min_pf": 1.5},
  "hypothesis_id": null
}
```
Eliminates the 0% review-date coverage across 100+ entries.

### Rec 2 (HIGH): Implement automatic review-date alerting
Create `tools/blocked_symbol_review_monitor.py`:
- Load PENDING_UNBLOCK_REVIEW + blocked_registry.json
- Flag dates ≤ TODAY as OVERDUE_REVIEW_REQUIRED
- Write to `audit_trail/alerts/overdue_unblock_reviews.json`
- Wire into daily GHA cron or pre-commit hook
- Surface in audit dashboard as "Pending unblock audits" card

### Rec 3 (MEDIUM): Fix UNBLOCK_THRESHOLDS constants + logic bug
Create a single `UNBLOCK_THRESHOLDS` dict at top of quality_gates.py:
- SHADOW: min_pf=1.3
- PROBATION: min_pf=1.3
- FULL: min_pf=**1.5** (fix: currently 1.2, which is backwards vs PROBATION)
Replace all 5 scattered threshold locations with references to this constant.

### Rec 4 (MEDIUM): Link hypothesis registry to blocked symbols
When blocking a symbol/strategy, auto-create a companion H-series hypothesis for rehabilitation test. Pre-register unblock parameters (n≥30, WR≥52% acceptance) in hypothesis_registry.json. Enables quantified re-test instead of vague "audit when time permits."

### Rec 5 (IMMEDIATE): Audit overdue symbols now
TRXUSDT, CVX, XOM are 11 days past review date. Action:
- Query latest n, WR, PF from closed_picks.json/MySQL
- If n≥20 AND WR≥52% AND PF≥1.3: promote to PROBATION_STATUS immediately
- If below thresholds: extend review_date by 14 days + document reason
- CVX already in PROBATION_STATUS — remove duplicate from EQUITY_BLOCKED_SYMBOLS
