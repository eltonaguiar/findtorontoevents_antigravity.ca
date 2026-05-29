# PR5: Wire Bond Scanner Strategies + Kill antigravity_bond

**Date:** 2026-05-27
**Branch:** `fix/pr5-bond-scanner-wiring`
**Severity:** P0 (antigravity_bond 0% WR) + P2 (bond_scanner not wired)

## Problem

- `antigravity_bond`: 0% WR on n=9, PF 0.00, Sharpe -2.465 — still emitting picks
- `bond_scanner.py` has 7 strategies but only `bond_connors_rsi2` is in the allowlist
- Three strategies already killed (bond_mean_reversion, bond_yield_momentum, bond_yield_curve_slope — 0% WR)
- Three viable strategies (bond_duration_rotation, bond_ust_tsmom, bond_credit_spread_mean_reversion) not wired

## Changes

### File: `audit_trail/quality_gates.py`
- Added `antigravity_bond` to `PERMANENTLY_KILLED_STRATEGIES`

### File: `alpha_engine/non_crypto_policy.py`
- Added `bond_duration_rotation` (probation — TLT regime-based)
- Added `bond_ust_tsmom` (probation — FRED DGS10 momentum)
- Added `bond_credit_spread_mean_reversion` (probation — credit spread signals)

## Impact Analysis

- **BOND class:** antigravity_bond stops bleeding capital. Three new strategies add diversity.
- **Risk:** All three new strategies are on probation (allow_without_forward=True). Zero forward trades.
- **Expected:** BOND n grows from 11 toward 50+ within 2 weeks of scanner wiring.
- **Peer review:** Ring-2.6-1T recommended this exact approach. ✅ Implemented.

## Verification
1. Check `/audit/` BOND tab — antigravity_bond picks should stop appearing
2. New bond strategies should appear as probation-tier picks
3. Monitor BOND WR — target ≥55% on new strategies after 20+ trades
