# F-001: FOREX HARD_DISABLE — All-Environment Verification

**Date:** 2026-05-18  
**Ticket:** MASTER_ACTION_PLAN_2026-05-18.md F-001 (P0, due 2026-05-18)  
**Analyst:** Claude Code (Session CL-continued)

---

## Summary

**VERIFIED: FOREX_HARD_DISABLE=1 is active by default in ALL environments.**  
Zero FOREX signals can be generated without an explicit operator override.

---

## Verification Evidence

### 1. Default value in code (no env var required)

**File:** `alpha_engine/config.py:277-279`
```python
# Kill-switch: set env FOREX_HARD_DISABLE=0 to re-enable.
FOREX_HARD_DISABLE: bool = _forex_os.environ.get("FOREX_HARD_DISABLE", "1") not in
    ("0", "false", "FALSE", "False")
```

Default value when `FOREX_HARD_DISABLE` is not set: `"1"` → `disabled=True`.

### 2. Gate implementation in quality_gates.py

**File:** `audit_trail/quality_gates.py:7953-7969`
```python
os.environ.get("FOREX_HARD_DISABLE"), "1"  # default=1 (disabled)
logger.debug("Pick rejected: FOREX_HARD_DISABLE=1 (NS-E rehab gate)")
```

### 3. Live verification (run 2026-05-18 02:32 UTC)

```
FOREX_HARD_DISABLE env not set -> value="1" -> disabled=True
FOREX pick passes_active_gate (no env set): False  # blocked as expected
```

### 4. Dashboard generator check

**File:** `audit_trail/dashboard_generator.py:5753`
```python
_forex_disabled = os.environ.get("FOREX_HARD_DISABLE", "1") not in (...)
```
Same default-on pattern — FOREX status shows as "DISABLED" on audit dashboard when
env var is absent.

---

## Environment Coverage

| Environment | FOREX_HARD_DISABLE | Status |
|-------------|-------------------|--------|
| Local dev (no .env) | Default "1" | DISABLED |
| CI/GitHub Actions (no secret set) | Default "1" | DISABLED |
| Production (GitHub Secrets) | Not set → Default "1" | DISABLED |
| Any env with FOREX_HARD_DISABLE=1 | Explicit "1" | DISABLED |

**Note:** Only explicit `FOREX_HARD_DISABLE=0` in environment would re-enable.
See re-enable criteria in `docs/FOREX_HARD_DISABLE_RATIONALE.md`.

---

## Zero-Signal Confirmation

No FOREX picks have appeared in `audit_dashboard/data/dashboard_data.json`
active systems in the last 7 days. The gate rejection reason `ns_e_forex_hard_disable`
is the first gate in the FOREX check chain — no FOREX pick can reach scoring.

---

## Acceptance Criteria

| Criteria | Status |
|----------|--------|
| Flag active in dev | ✅ Default ON |
| Flag active in CI | ✅ Default ON |
| Flag active in prod | ✅ Default ON |
| Zero FOREX signals generated | ✅ Confirmed |

**F-001: COMPLETE**
