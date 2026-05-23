# B13 — Per-class HMM Regime Detection: Pre-Implementation Review
**Date:** 2026-05-06  
**Reviewer:** claude-sonnet-4-6 (self-review, loop §5 protocol)  
**Item:** B13 — Per-class HMM regime detection (Cursor Phase 6)  
**Source:** `reports/REMAINING_ACTION_ITEMS_2026_04_30.md` §6.5 + `reports/NEXT_SESSION_P0_DESIGN_SPECS_2026_04_29.md` Item 3  
**Soak gate:** B12 merged 2026-05-01 21:20 UTC → earliest code start **2026-05-08 21:20 UTC**  
**Bucket-C gate:** B5 (PR #843) must merge first (one-in-flight rule §2.3)

---

## A. Confirmed Assumptions

### File paths verified (2026-05-06 scan)

| Path | Exists? | Notes |
|---|---|---|
| `alpha_engine/data/regime_report.json` | ✅ | Schema: `regime`, `btc_rsi`, `btc_trend`, `sma_slope`, `volatility_pct`, `btc_price`, `atr`, `max_long`, `max_short`, `recommendation`, `timestamp`, `regime_raw`, `btc_24h_change_pct`, `regime_flip_detected` |
| `alpha_engine/regime_filter.py` | ✅ | Per-symbol ADX/Hurst/BB classifier with `get_regime(symbol)` and `should_enter(symbol, strategy_type)` |
| `alpha_engine/regime_router.py` | ✅ | Two-layer composite regime router |
| `scripts/regime_detector.py` | ✅ | HMM regime detection script |
| `alpha_engine/risk/regime_filter.py` | ❌ NEW | Must create; spec says ~120 LOC |
| `tests/test_regime_filter_sidecar.py` | ❌ NEW | Must create; spec says ~150 LOC, 12 tests |

### Hook point confirmed

The exact call site in `passes_active_gate` (`audit_trail/quality_gates.py`):
- Line `4012`: `def passes_active_gate(pick: Dict[str, Any]) -> bool:`
- Lines `4075-4079`: `_crypto_short_gate_block_reason` call + `return False` block
- Insert point: **after line 4079** (immediately after the existing crypto-short block)

```python
# Currently at 4075-4079:
    _short_block_reason = _crypto_short_gate_block_reason(pick)
    if _short_block_reason is not None:
        logger.debug("Pick rejected: %s (%s)", _short_block_reason, symbol)
        return False

# New B13 insertion goes here (lines 4080-4086):
    try:
        from alpha_engine.risk.regime_filter import passes_regime_filter
        _regime_block = passes_regime_filter(pick)
        if _regime_block is not None:
            logger.debug("Pick rejected: %s (%s)", _regime_block, symbol)
            return False
    except ImportError:
        pass
```

### regime_report.json schema confirmed

Current value of `regime` field: `"CHOPPY"` (as of 2026-05-06 scan).  
Enum values observed across sessions: `BULL`, `BEAR`, `CHOPPY`, `RANGING`, `NEUTRAL`.  
No per-asset-class sub-keys — single global regime signal (CRYPTO-focused).  
**Implication:** The per-class sidecar must use the same single regime for all classes. Non-CRYPTO classes default to permissive (allow all) in the initial ship; per-class regime enrichment is a follow-up item.

### Wire-Up Rule compliance

- `passes_active_gate` is called from `smart_picks_engine`, `production_scanner`, and `dashboard_generator`.
- The new `passes_regime_filter` call is **inside** `passes_active_gate` → satisfies Wire-Up Rule criterion 1 (wired to production path).
- Default-OFF (`REGIME_FILTER_ENABLED=0`) → no production behavior change at merge.

### Existing regime tests

- `tests/test_regime_direction_gate.py` — 5 tests, all pass
- `tests/test_regime_gate_keltner.py`, `test_regime_gate_squeeze.py`, `test_regime_strategy_matcher.py`, `test_regime_stratified_posterior.py` — all present
- `tests/test_quality_gates.py` — 55 tests, all pass (baseline)

---

## B. Surfaced Contradictions / Blockers

### B1. Single regime signal vs per-class design intent

The spec says "per-asset-class regime filter" but `regime_report.json` has only one `regime` field (CRYPTO-focused). For non-CRYPTO classes, the sidecar's `_ALLOW_MATRIX` must default to **allow-all** (no blocking) until per-class regime data is available from `regime_router.py` enrichment.

**Recommendation:** Ship with the single-regime read for CRYPTO, permissive stubs for FOREX/EQUITY/COMMODITY/FUTURES. Document the gap explicitly. Per-class regime enrichment (requiring `regime_router.py` output to include per-class keys) is a separate follow-up.

### B2. Design spec line numbers are stale

The spec references `_crypto_short_gate_block_reason` at `:3820`. Current file has `passes_active_gate` at `:4012`. The call site is at `:4075-4079`. Line numbers drifted ~255 lines from the spec date (2026-04-29). **Hook point verified above is correct.**

### B3. `REGIME_FILTER_LOG_ONLY` default should be `"1"` not `"0"`

The spec sets `REGIME_FILTER_LOG_ONLY` default to `1` (shadow / log-only mode). The implementation must check `os.environ.get("REGIME_FILTER_LOG_ONLY", "1")` — defaulting to `"1"` means the first flip of `REGIME_FILTER_ENABLED=1` is automatically shadow-mode. Operator must explicitly set `REGIME_FILTER_LOG_ONLY=0` to enable actual blocking. **This is correct and must be preserved.**

### B4. One-Bucket-C-in-flight rule

B5 (PR #843) is currently open. B13 cannot be coded until B5 merges per §2.3. Implementation target: **after B5 merges AND after 2026-05-08 21:20 UTC soak expires.**

---

## C. Recommended Implementation Deltas

### C1. `_ALLOW_MATRIX` initial values (spec had `...` placeholders)

Fill in the matrix for all 5 classes:

```python
_ALLOW_MATRIX = {
    "CRYPTO": {
        "BULL":    {"LONG": True,  "SHORT": False},
        "BEAR":    {"LONG": False, "SHORT": True},
        "CHOPPY":  {"LONG": True,  "SHORT": True},
        "RANGING": {"LONG": True,  "SHORT": True},
        "NEUTRAL": {"LONG": True,  "SHORT": True},
    },
    "FOREX": {  # permissive until per-class regime available
        "BULL":    {"LONG": True, "SHORT": True},
        "BEAR":    {"LONG": True, "SHORT": True},
        "CHOPPY":  {"LONG": True, "SHORT": True},
        "RANGING": {"LONG": True, "SHORT": True},
        "NEUTRAL": {"LONG": True, "SHORT": True},
    },
    "COMMODITY": {  # permissive stub — metals edge confirmed, don't block
        "BULL":    {"LONG": True, "SHORT": True},
        "BEAR":    {"LONG": True, "SHORT": True},
        "CHOPPY":  {"LONG": True, "SHORT": True},
        "RANGING": {"LONG": True, "SHORT": True},
        "NEUTRAL": {"LONG": True, "SHORT": True},
    },
    "EQUITY": {  # permissive stub
        "BULL":    {"LONG": True, "SHORT": True},
        "BEAR":    {"LONG": True, "SHORT": True},
        "CHOPPY":  {"LONG": True, "SHORT": True},
        "RANGING": {"LONG": True, "SHORT": True},
        "NEUTRAL": {"LONG": True, "SHORT": True},
    },
    "FUTURES": {  # permissive stub
        "BULL":    {"LONG": True, "SHORT": True},
        "BEAR":    {"LONG": True, "SHORT": True},
        "CHOPPY":  {"LONG": True, "SHORT": True},
        "RANGING": {"LONG": True, "SHORT": True},
        "NEUTRAL": {"LONG": True, "SHORT": True},
    },
    "ETF": {  # permissive stub
        "BULL":    {"LONG": True, "SHORT": True},
        "BEAR":    {"LONG": True, "SHORT": True},
        "CHOPPY":  {"LONG": True, "SHORT": True},
        "RANGING": {"LONG": True, "SHORT": True},
        "NEUTRAL": {"LONG": True, "SHORT": True},
    },
}
```

**Rationale:** Only CRYPTO has a regime signal with confirmed edge correlation. All other classes default to pass-all. This means at launch, `REGIME_FILTER_ENABLED=1` + `REGIME_FILTER_CRYPTO_ENABLED=1` only affects CRYPTO picks. FOREX/EQUITY/COMMODITY blocked-direction testing begins after per-class regime enrichment lands (future item).

### C2. Direction normalization

The existing `_crypto_short_gate_block_reason` checks `direction in ("SHORT", "SELL")`. The new sidecar must normalize similarly:

```python
direction = str(pick.get("direction") or pick.get("signal_type") or "").upper()
if direction in ("BUY",):
    direction = "LONG"
if direction in ("SELL",):
    direction = "SHORT"
```

### C3. Test class structure (12 tests)

| Test | Class | Description |
|---|---|---|
| `test_default_off_no_block` | `TestDefaultOff` | `REGIME_FILTER_ENABLED=0` → None always |
| `test_class_flag_off_no_block` | `TestDefaultOff` | Master=1 but `REGIME_FILTER_CRYPTO_ENABLED=0` → None |
| `test_log_only_no_block` | `TestLogOnly` | LOG_ONLY=1 → None even when matrix says block |
| `test_crypto_short_blocked_in_bull` | `TestCryptoMatrix` | ENABLED+CRYPTO_ENABLED+LOG_ONLY=0+BULL → SHORT blocked |
| `test_crypto_long_allowed_in_bull` | `TestCryptoMatrix` | BULL → LONG passes |
| `test_crypto_short_allowed_in_bear` | `TestCryptoMatrix` | BEAR → SHORT passes |
| `test_crypto_long_blocked_in_bear` | `TestCryptoMatrix` | BEAR → LONG blocked |
| `test_choppy_allows_both` | `TestCryptoMatrix` | CHOPPY → both LONG + SHORT pass |
| `test_missing_regime_report_no_block` | `TestMissingData` | No file → CHOPPY default → no block |
| `test_forex_always_passes` | `TestPermissiveClasses` | FOREX with any regime → None (permissive) |
| `test_equity_always_passes` | `TestPermissiveClasses` | EQUITY with BEAR regime → None (permissive) |
| `test_unknown_asset_class_passes` | `TestPermissiveClasses` | Unknown class → None |

### C4. Reuse existing test pattern

Extend `tests/test_quality_gates.py` with 2 regression tests confirming:
- The new call site in `passes_active_gate` doesn't break existing CRYPTO LONG picks
- ImportError from missing `alpha_engine.risk.regime_filter` is caught silently

---

## D. Net Verdict

**Ready-to-ship — blocked only by timing gates, not design gaps.**

- Hook point: confirmed, exact (quality_gates.py:4079)
- Wire-Up Rule: satisfied (wired to passes_active_gate)
- Risk classification: HIGH is correct (gating change), fully mitigated by default-OFF + LOG_ONLY=1 default + per-class flags
- Test plan: 12 sidecar tests + 2 regression tests in test_quality_gates.py
- Single gap: per-class regime data not available → permissive stubs for non-CRYPTO (acceptable for v1)

**Implementation dependencies:**
1. B5 PR #843 must be merged (Bucket-C single-in-flight rule)
2. 2026-05-08 21:20 UTC soak must expire
3. All flags default-OFF → zero production impact at merge
4. REGIME_FILTER_LOG_ONLY defaults to "1" → first activation is shadow-only

**Estimated effort:** 3-4h (spec-sized: ~120 LOC new file + 150 LOC tests + 10 LOC call site + doc)
