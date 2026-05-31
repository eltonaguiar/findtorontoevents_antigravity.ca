# Batch Incident Resolution #2 — 2026-05-31

**Status:** 6 incidents resolved (42→34 OPEN, 9→6 P0+OPEN).

## Approach

Many OPEN incidents had already been fixed in code but their DB status was never updated. Only 2 of 6 required new code changes. The other 4 were code-already-done + DB-status-only updates.

## Incidents Resolved

| # | Class | ID | Severity | Title | Fix Type |
|---|-------|---|----------|-------|----------|
| 1 | BONDS | 2 | P0 | Antigravity_bond: 0% WR — kill emission | Code-done (kill switch in non_crypto_policy.py) |
| 2 | STOCKS | 1 | P0 | PEAD equity stuck in shadow mode | Code-done (promoted to probation) |
| 3 | STOCKS | 5 | P1 | Penny/meme names pollute EQUITY | New code (classification split) |
| 4 | FUTURES | 1 | P3 | BANNED futures strategies cleanup | Code-done (blocked in 8+ paths) |
| 5 | FOREX | 5 | P1 | FOREX aggregates losers | Code-done (PR6 consolidation) |
| 6 | OVERALL | 23 | P1 | Multi-AI wrong COMMODITY consensus | New code (leakage boilerplate) |

## Code Changes

### 1. `alpha_engine/config.py` — EQUITY/PENNY classification split
detect_asset_class() now checks EQUITY_SYMBOLS[symbol]["cat"]. Penny/meme-tagged symbols return "penny" instead of "equity".

### 2. `tools/consult_multi.py` — Leakage-context boilerplate
Mandatory concentration-risk + hypothesis_registry check appended to every prompt. Prevents ungrounded multi-AI consensuses.

### 3. `tools/audit_pick_funnel/seed_incidents_enhancements.py` — Status sync
6 OPEN→RESOLVED transitions. Prevents nightly seed from reverting DB statuses.

## Verification
- BOND: kill switch active in non_crypto_policy.py:579
- PEAD: in non_crypto_policy.py with allow_without_forward=True, wired in production_scanner.py, dedicated tests exist
- FUTURES BANNED: blocked in 8+ code paths
- FOREX: PR6 consolidation (cta_cross_asset_tsmom SHORT + carry_trade only)
- Penny/meme: detect_asset_class('GME') → "penny"
- Leakage boilerplate: injected in consult_multi.py main()

## Remaining P0+OPEN

| Class | Title |
|-------|-------|
| COMMODITIES | 11.9% WR / PF 0.29 |
| COMMODITIES | COT DSR=1.0 vs BLOCKED reconciliation |
| COMMODITIES | PF/WR contaminated by pre-clean COT |
| OVERALL | smart_picks_engine confidence weights |
| OVERALL | Profitable-but-filtered picks |
| STOCKS | EQUITY PROBATION-tier + mistagged picks |
