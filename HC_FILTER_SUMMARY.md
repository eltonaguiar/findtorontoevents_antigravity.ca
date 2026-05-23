# HC Filter Bug Fixes & Test Coverage — Summary

> **Branch:** `fix/safe-push-hardening` → **PR #232** (merged)  
> **Date:** 2026-04-15  
> **Test Results:** 24/24 Python ✅ · 25/25 JS ✅ · 70/70 Playwright ✅ · Production browser verified ✅

---

## Bugs Fixed

### 1. `dashboard_hc_rules.py` Missing Per-Asset-Class Gates
The server-side Python HC filter lacked the per-asset-class FWD WR and Score floor gates that existed in `hc_filter.js`. This meant a FOREX pick with Score=35 could pass Python but fail JS, causing dashboard/server inconsistency.

**Fix:** Added `passesValidatedEdgePerClass()`-equivalent logic to `dashboard_hc_rules.py` with identical per-class thresholds read from the same config source.

### 2. FOREX Auto-Relax vs Gate 7b Conflict
A FOREX pick with `fwdN=15` and `confidence=0.88` would be:
- **Relaxed** by auto-relax (FWD WR threshold lowered from 55% → 50%) ✅
- **Immediately killed** by Gate 7b (confidence 0.85–0.95 band + fwdN < 30) ❌

The two gates cancelled each other out — auto-relax admitted the pick, then Gate 7b rejected it for the same small-sample reason.

**Fix:** Gate 7b now **skips** when `forexAutoRelax` is active (fwdN < 20), because the relaxed WR threshold already accounts for small samples. Gate 7a (extreme confidence >0.95) still applies regardless — auto-relax bypasses Gate 7b, NOT Gate 7a.

### 3. `template.html` Hardcoded Thresholds
`passesValidatedEdgePerClass()` in `template.html` hardcoded threshold values `0.45/0.55/0.50/55/50/40` — changing them in `hc_gate_params.json` or `HC_GATE_PARAMS_EMBEDDED` had no effect on the production dashboard.

**Fix:** All thresholds now read from `getHcGateParams()` / `HC_GATE_PARAMS_EMBEDDED`, so config changes propagate everywhere consistently.

### 4. `hcEdgeManifest()` Labels Were Static
The HC Edge Manifest panel displayed hardcoded threshold text like "FWD WR ≥ 45% + Score ≥ 55" — if config params changed, the labels would be wrong.

**Fix:** Labels now dynamically read from the same config params using string concatenation, staying in sync with `passesValidatedEdgePerClass()` and `hc_filter.js`.

---

## Per-Asset-Class Thresholds (Config-Driven)

| Class    | FWD WR Floor            | Score Floor | Auto-Relax? |
|----------|-------------------------|-------------|-------------|
| CRYPTO   | ≥ 45%                   | ≥ 55        | No          |
| EQUITY   | ≥ 55%                   | ≥ 50        | No          |
| FOREX    | ≥ 55% (50% if fwdN<20)  | ≥ 40        | Yes         |

---

## Gate 7a vs 7b Exception Logic

| Gate | Condition | FOREX Auto-Relax Bypass? |
|------|-----------|--------------------------|
| **7a** (extreme confidence) | `confidence > 0.95 AND fwdN < 30` | **No** — always applies |
| **7b** (confidence band) | `0.85 ≤ confidence ≤ 0.95 AND fwdN < 30` | **Yes** — skipped when auto-relax active |

**Gate 7b upper boundary:** fwdN=30 passes, fwdN=29 fails.

**Non-FOREX classes:** Gate 7b applies normally (no auto-relax bypass).

---

## Test Coverage

### Python (`tests/test_dashboard_hc_rules.py`) — 24/24 ✅

| # | Test | Category |
|---|------|----------|
| 1-6 | Existing HC gate tests (trust tier, fwd trades, score, etc.) | Baseline |
| 7-8 | FOREX fwdN≥20 needs FWD WR≥55%; fwdN<20 relaxed to 50% | Auto-relax |
| 9 | FOREX auto-relax bypasses Gate 7b (confidence 0.85-0.95) | Gate 7b exception |
| 10 | Gate 7b still applies to CRYPTO (no FOREX auto-relax) | Parity |
| 11 | Per-asset-class score floors: CRYPTO≥55, EQUITY≥50, FOREX≥40 | Score gates |
| 12 | Per-asset-class FWD WR floors: CRYPTO≥45%, EQUITY≥55%, FOREX≥55% | WR gates |
| 13 | FOREX auto-relax does NOT bypass Gate 7a (extreme confidence) | Gate 7a |
| 14 | FOREX Gate 7b upper boundary: fwdN=30 passes, fwdN=29 fails | Boundary |
| 15 | Config override: `forexRelaxedWRMinPct` via monkeypatch | Config-driven |

### JavaScript (`tests/test_hc_filter.js`) — 25/25 ✅

Matching JS tests for all 9 new test categories above, plus existing baseline tests.

### Integration

- **Playwright:** 70/70 mental-health-resources spec passes
- **Browser:** Production `findtorontoevents.ca/audit/` verified — manifest labels render correctly with dynamic values, no `undefined`/`NaN`, zero console errors related to HC filter

---

## Files Changed

| File | Change |
|------|--------|
| `audit_dashboard/hc_filter.js` | FOREX auto-relax bypasses Gate 7b; config-driven thresholds in `passesValidatedEdgePerClass()` |
| `tools/dashboard_hc_rules.py` | Matching Python parity for per-asset-class gates + FOREX auto-relax |
| `audit_dashboard/template.html` | `hcEdgeManifest()` labels now dynamic from config params |
| `tests/test_hc_filter.js` | 25 JS unit tests (9 new FOREX auto-relax + Gate 7b/7a tests) |
| `tests/test_dashboard_hc_rules.py` | 24 Python unit tests (9 new FOREX auto-relax + Gate 7b/7a tests) |

---

## Key Design Decisions

1. **Config-driven over hardcoded:** All threshold values now flow from a single config source (`HC_GATE_PARAMS_EMBEDDED` / `hc_gate_params.json`), eliminating drift between JS, Python, and the dashboard UI.

2. **Auto-relax bypasses Gate 7b only, not Gate 7a:** Gate 7a catches overconfidence (a separate concern from small samples) and should always apply. Gate 7b's small-sample confidence skepticism is the same concern auto-relax addresses — hence the bypass.

3. **fwdN<20 triggers auto-relax:** The boundary was chosen because below 20 forward trades, win-rate estimates are statistically unreliable. The relaxed threshold (50% vs 55%) provides a wider confidence interval.

4. **Trust score ≥8 bypasses Gate 2 for low scores:** FOREX picks with score=40 need `trust_score≥8` to pass Gate 2's compound floor (`score < 50 + trust < 8`). This prevents low-score FOREX picks from passing with low trust.

---

*Generated: 2026-04-15 · PR #232 merged*
