# PR #2: Universal Blocked Symbol Gate + UEPS Bypass Restriction

**Branch:** `fix/blocked-symbol-universal-gate`  
**Files:** `audit_trail/quality_gates.py`  
**Type:** Security fix / leak patch  
**Priority:** P0 — Active data leak  
**Expected Impact:** Eliminates 8 blocked symbols currently live in `active_picks.json`

---

## Problem

Despite a `BLOCKED_SYMBOLS` filter added to `alpha_engine/production_scanner.py` (2026-05-16), **8 blocked symbols remain active** in `active_picks.json` with timestamps *after* the fix:

| Symbol | Source | Timestamp | Leak Path |
|--------|--------|-----------|-----------|
| TRXUSDT | super_signals | 06:17Z | Bypasses production_scanner |
| TRXUSDT | ml_crypto_pred | 05:31Z | Bypasses production_scanner |
| ICPUSDT | quan_engine | 06:21Z | Bypasses production_scanner |
| NVDA | kimi_riseoftheclaw | 05:05Z | Bypasses production_scanner |
| TSLA | multi_asset_copytrader | 06:06Z | Bypasses production_scanner |
| ADBE | ueps | 05:46Z | UEPS bypass (performance block) |
| HD | ueps | 05:46Z | UEPS bypass (performance block) |
| TSLA | ueps | 05:46Z | UEPS bypass (performance block) |

**Root cause:** The production_scanner fix only covers **one** emission pipeline. Other source systems never pass through it, so their picks skip the block entirely. Additionally, the UEPS long-horizon bypass (`_ueps_long_horizon_bypass_active`) was applying to **all** blocked symbols, including performance-based blocks (ADBE, TSLA, HD) that have structural anti-edge regardless of holding period.

---

## Solution

### Change 1: Universal BLOCKED_SYMBOLS Gate in `passes_active_gate()`

Add an early rejection in `passes_active_gate()` — the admission function called by **all** source systems before a pick reaches `active_picks.json`:

```python
if os.environ.get("UNIVERSAL_BLOCKED_SYMBOLS_GATE_DISABLED", "0") != "1":
    _sym_active = str(pick.get("symbol", "") or "").upper().strip()
    if _sym_active in BLOCKED_SYMBOLS and not _ueps_long_horizon_bypass_active(pick):
        logger.info(
            "Pick rejected: blocked symbol %s (universal gate)",
            _sym_active)
        return False
```

**Why `passes_active_gate`:** This function is the **universal admission gate**. Every pick — regardless of source system — must pass it to be displayed or acted upon. By placing the block here, we close the leak for super_signals, quan_engine, ml_crypto_pred, multi_asset_copytrader, and kimi_riseoftheclaw simultaneously.

**Kill-switch:** `UNIVERSAL_BLOCKED_SYMBOLS_GATE_DISABLED=1` allows instant rollback if the gate causes unexpected side effects.

### Change 2: Restrict UEPS Bypass to Data-Quality Blocks Only

Modify `_ueps_long_horizon_bypass_active()` to only bypass for symbols blocked due to **data quality** (delisted, broken feed, redenomination), not **performance** (structural anti-edge):

```python
_data_quality_only_blocks = frozenset({
    "MATICUSDT",  # delisted
    "UUSDT",      # broken symbol
    "XMR",        # most destructive
    "XMRUSDT",    # alias
    "KATUSDT",    # redenomination 13x jump
})
if _ueps_sym not in _data_quality_only_blocks:
    return False
```

**Rationale:** A 3-year holding horizon does not fix a strategy that loses on every trade. ADBE (5.6% WR, -85.5% PnL), TSLA (26.7% WR, -24.4% PnL), and HD (10% WR, -35% PnL) are blocked because the strategies **consistently lose money on them**, not because of data corruption. UEPS should not bypass these.

---

## Verification Plan

1. **Immediate:** Run `python tools/db_freshness_check.py` or inspect next `active_picks.json` generation
   - Expected: 0 blocked symbols in active picks
   - Previously: 8 blocked symbols leaking

2. **7-day shadow:** Monitor `picks.active` count daily
   - Expected: No blocked symbols reappear
   - If any blocked symbol appears: investigate which pipeline bypassed the gate

3. **UEPS-specific:** Monitor UEPS active picks for ADBE, TSLA, HD
   - Expected: These symbols no longer appear in UEPS output
   - MATICUSDT, KATUSDT may still appear (data-quality bypass preserved)

---

## Rollback

- `UNIVERSAL_BLOCKED_SYMBOLS_GATE_DISABLED=1` — disables the new gate
- `UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED=0` — disables UEPS bypass entirely (reverts to pre-UEPS behavior)

---

## Related Files

- `alpha_engine/production_scanner.py` — Existing scanner-side filter (partial fix)
- `updates/2026-05-16-comprehensive-edge-analysis-and-recommendations.md` — Full audit
- `audit_trail/quality_gates.py` — This PR's target file

---

## Sign-off

- [x] Fixes active data leak (8 symbols)
- [x] Universal gate (all source systems)
- [x] UEPS bypass restricted to data-quality blocks
- [x] Kill-switches included
- [x] Documented in `updates/2026-05-16-PR-2-blocked-symbol-universal-gate.md`
