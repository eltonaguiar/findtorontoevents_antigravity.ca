# HC Gate Config Parity — Full Changelog

**Branch:** `fix/hc-gate-config-parity-2026-04-22`
**Date:** 2026-04-22
**Scope:** Synchronize HC gate parameters across JSON↔JS↔Python, add pick schema auditing, calibrate per-asset-class thresholds, clean up scratch files and gitignore.

---

## Problem

Three parity mismatches existed between the source-of-truth config (`config/hc_gate_params.json`) and its JS/Python mirrors (`audit_dashboard/hc_filter.js` and `tools/dashboard_hc_rules.py`). Additionally, the HC gate config lacked per-asset-class floors for Commodity, Futures, Bond, and ETF, and there was no tooling to audit pick schema health or measure rolling HC impact.

---

## Files Changed

### `config/hc_gate_params.json`
**Why:** Source-of-truth for all HC gate parameters. Updated to v4 (2026-04-21).

| Parameter | Before | After | Rationale |
|-----------|--------|-------|-----------|
| `trustScoreMinCrypto` | 6 | 4 | Crypto trust data is sparse; floor 6 was filtering out valid picks |
| `forwardWRMinPctCrypto` | 45 | 40 | Same reason — crypto forward-WR sample too small at 45 |
| `scoreFloorCrypto` | 55 | 45 | Aligned with equity floor parity; crypto scores are naturally lower |
| `forwardWRMinPctForex` | 55 | 60 | Forex has larger sample → tighter WR floor appropriate |
| `scoreFloorForex` | 40 | 60 | Forex picks were leaking low-score entries; raised to match observed edge |
| `scoreFloorEquity` | 50 | 45 | Slight relaxation after 3500-pick backtest showed 45 as optimal |
| `independentGroupsMin` | _(absent)_ | 3 | New key — prevents bypass of independent-consensus gate when key missing |
| `scoreFloorCommodity` | _(absent)_ | 35 | New — commodity asset class had no floor |
| `scoreFloorFutures` | _(absent)_ | 35 | New — futures asset class had no floor |
| `scoreFloorBond` | _(absent)_ | 35 | New — bond asset class had no floor |
| `scoreFloorETF` | _(absent)_ | 35 | New — ETF asset class had no floor |

---

### `audit_dashboard/hc_filter.js`
**Why:** Front-end HC evaluation logic. Must mirror `hc_gate_params.json` exactly.

- **`scoreFloorEquity`**: Changed fallback from `50` → `45` (both in `HC_GATE_PARAMS_EMBEDDED` and `evaluateHcGates1to9`)
- **`trustScoreMinCrypto`**: Changed fallback from `6` → `4`
- **`independentGroupsMin`**: Changed fallback from `0` → `3` (was silently bypassing the gate when key missing)
- **Asset-class floor lookups**: Standardized `scoreFloorAC` and `fwdFloorAC` to use per-asset-class params with safe defaults for new asset classes (Commodity, Futures, Bond, ETF)

---

### `tools/dashboard_hc_rules.py`
**Why:** Backend HC evaluation logic. Must mirror `hc_gate_params.json` exactly.

- **`scoreFloorEquity`**: Changed in both `_EMBEDDED_DEFAULTS` dict and `evaluate_hc_gates_1_to_9` from `50` → `45`
- **`trustScoreMinCrypto`**: Changed in `trust_floor` calculation from `6` → `4`
- **`independentGroupsMin`**: Changed default from `0` → `3` in `ig_min` calculation
- **Asset-class floor lookups**: Synchronized `scoreFloorAC` and `fwdFloorAC` fallback logic to match JS

---

### `tools/audit_pick_schema.py` *(NEW)*
**Why:** No tool existed to audit pick data for schema health (missing fields, stale entries, malformed records).

- Scans active picks and validates required fields are present and correctly typed
- Reports schema violations and stale entries
- Used in CI pipeline to catch data drift before it affects dashboard rendering

---

### `tools/hc_rolling_impact.py` *(NEW)*
**Why:** No tool existed to measure rolling-window impact of HC gate changes on WR/PF.

- Computes rolling 30/60/90-day WR and profit factor for HC-passing picks
- Compares pre/post gate change performance
- Used to validate that parameter calibration improved (not just shifted) outcomes

---

### `audit_dashboard/template.html`
**Why:** Dashboard rendering must reflect new HC gate behavior and display improvements.

- **Profit Factor cap**: Changed from 999 → 99.9 to avoid absurdly large PF values in display
- **Score bucket labels**: Renamed from "S-Tier (70+)" to "Score band S (70+)" etc. to avoid confusion with HF tiers
- **Non-crypto aggregate**: Now respects `_PERF_RECENT_N` parameter for recent-N filtering
- **Trust floor display**: Now dynamically reads from config instead of hardcoded values

---

### `docs/MERCURY2_HC_VALIDATION_PIPELINE.md`
**Why:** Pipeline documentation was outdated — didn't reference the new audit tools or v4 params.

- Added usage examples for `audit_pick_schema.py` and `hc_rolling_impact.py`
- Updated parameter table to reflect v4 values
- Added validation flow diagram showing parity check between JSON↔JS↔Python

---

### `.gitignore`
**Why:** `tradingview-mcp/` is a separate repo cloned inside the project, should not be tracked.

- Added `tradingview-mcp/` entry

---

### `docs/reports/hc_audit_2026-04-20.md` *(NEW)*
**Why:** Audit trail report documenting the state of HC gates before the fix was applied.

- Captures pre-fix WR, PF, and trust distribution by asset class
- Serves as baseline for measuring improvement

---

### `updates/2026-04-20-hc-dashboard-audit-trust-parity-fixes.md` *(NEW)*
**Why:** Documents the first round of parity fixes (trust threshold alignment, config completeness, signal group sync).

- Trust threshold alignment in template.html
- Per-asset FWD/score floors added for all asset classes
- `ai_challenge` group synced with `hc_filter.js`
- PF cap and score bucket naming changes

---

### `updates/2026-04-21-hc-gate-parity-fixes.md` *(NEW)*
**Why:** Documents the second round of parity fixes (scoreFloorEquity, trustScoreMinCrypto, independentGroupsMin).

- Three specific parity mismatches identified and resolved
- Post-fix HC performance metrics: 40.1% baseline WR → 61.1% HC WR, PF 2.37
- Parity verification results

---

### `updates/2026-04-21-deep-strategy-investigation-by-asset-class.md` *(NEW)*
**Why:** Diagnostic investigation that motivated the parameter changes.

- Analyzed 3,500 closed picks by asset class
- Identified that crypto trust floor was too aggressive (filtering valid picks)
- Identified that forex score floor was too lenient (leaking low-edge picks)

---

### `updates/2026-04-21-hyrotrader-edge-failures-fixes.md` *(NEW)*
**Why:** Documents edge-case failures found in Hyrotrader scoring and their fixes.

- Specific Hyrotrader edge failure patterns and root causes
- Applied fixes to scoring logic

---

## Files Deleted (Scratch Cleanup)

The following temporary scratch files were deleted during this work:
- `tmp_cg_analysis.py` — one-off Claude Gainer analysis script
- `tmp_check_parity.py` — parity check utility (functionality now in `audit_pick_schema.py`)
- `tmp_hc_rolling.json` — data snapshot (replaced by `hc_rolling_impact.py`)
- `tmp_fix_manifest.py`, `tmp_fix_py.py`, `tmp_fix_trust.py` — ad-hoc fix scripts
- `apply_godlike_fixes.py`, `apply_godlike_fixes_v2.py` — one-off batch fix scripts
- 19 other `tmp_*.py` files across project root and `alpha_engine/`

---

## Validation

- ✅ Python syntax check passed on `tools/audit_pick_schema.py`
- ✅ Python syntax check passed on `tools/dashboard_hc_rules.py`
- ✅ Python import test passed on `tools.audit_pick_schema`
- ✅ Python import test passed on `tools.dashboard_hc_rules`
- ✅ Parity check: JSON↔JS↔Python values now match for all 3 previously mismatched keys
- ✅ Post-fix HC WR: 61.1% (baseline 40.1%), PF: 2.37

---

## Commit History (this branch)

1. `b2dfe89964` — diag: deep strategy investigation by asset class (n=3500)
2. `7e205b2ee3` — fix(hc-gate): calibrate HC filter params + add pick schema audit + clean gitignore
3. `7a054b672c` — fix(hc-gate): parity sync JSON→JS/PY for scoreFloorEquity, trustScoreMinCrypto, independentGroupsMin
