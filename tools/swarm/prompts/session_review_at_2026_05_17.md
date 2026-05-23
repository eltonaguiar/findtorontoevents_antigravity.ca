# Session AT — Swarm Review Request
# Date: 2026-05-17
# Session: AT (following AS — APPROVE)

## Context

Session AT: Post-AS cleanup round. Fixed 1 failing test (FOREX session gate time-dependency),
corrected a misleading FOREX_COPYTRADER_ENABLE comment (WR was wrong by ~4x), and
confirmed current state of all asset classes.

## Session AT Changes

### 1. Test Fix: FOREX Session Gate Time-Dependency (M-078)

**Problem:** `test_baseline_usdjpy_passes` was an isolation test for the source-symbol gate
(BLOCKED_SOURCE_SYMBOL_PAIRS). It disabled FOREX_HARD_DISABLE, FOREX_DIRECTIONAL_GATE_ENABLED,
and CONCENTRATION_CAP_ENABLED — but NOT the M-078 FOREX session gate (forex_session_gate).

M-078 blocks FOREX picks outside 08-16 UTC (fail-closed). The test uses `datetime.now()` for the
pick timestamp, causing the test to fail when run after 16 UTC.

**Fix:** Added `monkeypatch.setenv("FOREX_SESSION_GATE_DISABLED", "1")` to the isolation test —
consistent with the other 3 class-wide FOREX gate disables already present. The test is specifically
for the source-symbol gate, not the session gate.

**Verification:** 11/11 tests pass in test_cta_replicator_symbol_gate.py.

### 2. Correction: FOREX_COPYTRADER_ENABLE Comment Was Wrong

**Problem:** `quality_gates.py` had a comment:
```python
# FOREX_COPYTRADER_ENABLE=1 (default OFF, shadow): bypasses this gate ONLY
# for source_system=multi_asset_copytrader — last-30d WR=64.7%, PF=1.87
# (2026-05-17 recovery; see reports/forex_copytrader_recovery_2026_05_17.md).
# Enable only after multi_asset_copytrader FOREX reaches n≥30 per-source.
```

**Actual performance from closed_picks.json:**
- multi_asset_copytrader FOREX: n=696, WR=16.5%, PF=0.23 (all-time)
- The 64.7% WR figure was erroneous — FOREX closed_picks lack closed_at timestamps
  so any date filter fails silently and returns all 696 picks

**Fix:** Comment updated to say "DO NOT ENABLE — all-time closed_picks shows WR=16.5%,
PF=0.23, n=696." FOREX_COPYTRADER_ENABLE remains OFF (correct).

### 3. Asset Class Status Audit (No Code Changes)

Current state from money_ready_verdict():

| Class | Verdict | PF | WR | n | Blocker |
|-------|---------|----|----|---|---------|
| CRYPTO | MONEY_READY ✅ | 2.60 | 68.2% | 475 | — |
| COMMODITY | WATCH ⏳ | 2.15 | 60.2% | 354 | concentration_capped (CT=F 65.25% > 60% cap) |
| EQUITY | WATCH ⏳ | 2.04 | 54.2% | 238 | no strategy n≥20 (multi_asset_copytrader blocked, WR=33.3%) |
| ETF | WATCH ⏳ | 2.49 | 67.6% | 74 | no strategy n≥20 in closed_picks |
| FOREX | NOT_READY ❌ | 0.48 | 33.3% | N/A | FOREX_HARD_DISABLE=1 (default) |
| BOND | INSUFFICIENT_DATA | 0.66 | 50.0% | 12 | n too small |

**COMMODITY path:** Both pending user approvals (AO) still needed:
1. Block `cta_cross_asset_tsmom` for COMMODITY → reduces CT=F share
2. `CONCENTRATION_CAP_BY_CLASS = {"COMMODITY": 0.85}` → raises cap

**EQUITY note:** `multi_asset_copytrader` is the only EQUITY strategy with n≥20 (n=39) but it's
correctly blocked (WR=33.3%, PF=0.69). The DSR/PBO/SPA statistical checks can't run because no
eligible (unblocked) EQUITY strategy has n≥20. This is a genuine sample-size issue, not a bug.

**Dashboard discrepancy:** Dashboard shows CRYPTO PF=1.44/WR=47.9% (n=6842) while
money_ready_verdict shows PF=2.60/WR=68.2% (n=475). This is expected: dashboard includes all
strategies (including blocked ones like quan_engine PF=0.70), money_ready_verdict filters by
`_load_blocked()`. The money_ready_verdict is the investment decision signal.

### 4. DAILY_IDEAS Audit

| Item | Status |
|------|--------|
| Dispatch ab_analysis.yml for multi_asset_cot | ab_analysis runs daily on schedule — dispatching manually would duplicate |
| BTC UTC-hour filter 08-09 death zone / 22 peak | Done (M-073, Session AA) |
| Swap confidence → trust_score HIGH_CONVICTION gate | M-034 confidence-inversion already implements this for CRYPTO |
| FOREX hard-disable enforcement check | Confirmed: default ON via _truthy(FOREX_HARD_DISABLE, "1") |
| Procure GLASSNODE_API_KEY + CFTC_API_KEY | Operator action — still pending |

## Pending User Approvals (same as AO/AP)

1. **Block `cta_cross_asset_tsmom` for COMMODITY** — WR=12.7%, n=71
2. **`CONCENTRATION_CAP_BY_CLASS = {"COMMODITY": 0.85}`** — CT=F at 65.25% concentration

Both are required for COMMODITY MONEY_READY.

## Questions for Swarm

1. **Test isolation hygiene**: When testing one specific gate in isolation (source-symbol gate),
   the fix pattern of monkeypatching `GATE_DISABLED=1` for sibling gates is clean. Is there any
   concern with this approach, or should we instead use fixed timestamps in test pick fixtures?

2. **FOREX_COPYTRADER comment**: The prior WR=64.7% figure was confidently cited in the code
   comment (with a named report). That report may not exist or may have been incorrect.
   Should we audit other comments in quality_gates.py that cite specific performance figures
   to verify they're still accurate?

3. **EQUITY WATCH unblocking path**: The only path to EQUITY MONEY_READY statistical tests
   passing is accumulating n≥20 per strategy for ≥2 unblocked strategies. Current state:
   only 1 strategy (multi_asset_copytrader, WR=33.3%) has n≥20 and it's correctly blocked.
   Is there any intervention (e.g., targeted scanning for EQUITY-performing strategies) that
   would accelerate accumulation, or just wait?

4. **Overall verdict**: Is Session AT APPROVE?

## Verification

- Tests: 11/11 pass in test_cta_replicator_symbol_gate.py; 128/128 full suite before test fix
- CI: in progress on main (triggered by pushes)
- Commits: FOREX session gate test fix, FOREX_COPYTRADER comment correction
- Prior swarm verdicts: AQ/AR/AS all deepseek APPROVE
