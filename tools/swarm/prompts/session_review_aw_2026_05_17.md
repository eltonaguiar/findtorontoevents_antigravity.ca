# Session AW — Swarm Review Request
# Date: 2026-05-17
# Session: AW (following AV — APPROVE)

## Context

Session AW: State assessment after completing Sessions AU and AV. Both
previous sessions had deepseek APPROVE. This session summarizes the current
system state and outstanding items, seeking swarm direction on what to
prioritize next.

## Current money_ready_verdict State

| Class     | Verdict           | PF   | WR    | n   | Key Blocker |
|-----------|-------------------|------|-------|-----|-------------|
| CRYPTO    | MONEY_READY       | 2.54 | 66.4% | 443 | — (clean) |
| EQUITY    | WATCH             | 2.04 | 54.2% | 238 | No strategies with n≥20 after stocks_rsi2_pullback block (WR=38%/PF=0.97) |
| COMMODITY | WATCH             | 2.15 | 60.2% | 354 | CT=F concentration 65% > cap; needs user approval to fix |
| ETF       | WATCH             | 2.49 | 67.6% | 74  | No strategies with n≥20; time accumulation only |
| BOND      | INSUFFICIENT_DATA | 0.66 | 50.0% | 12  | n=12, below floor |
| FOREX     | NOT_READY         | 0.48 | 33.3% | 618 | WR inversion, hard-blocked |

## Session AV → AW Summary (all complete)

### Completed in AV (deepseek APPROVE, a3ce4ce4cd)
1. DYDXUSDT added to BLOCKED_SYMBOLS — 32 artifact picks excluded from CRYPTO stats
2. 9 FOREX test isolation failures fixed (M-078 session gate time-dependency)
3. `tests/conftest.py` global `FOREX_SESSION_GATE_DISABLED=1` — permanent isolation fix
4. Weekly filter report regenerated (reports/weekly_filter_2026-05-17.md)

### Actions Taken This Session (AW)
1. **ab_analysis.yml dispatched** — run #25999062203 in progress. This verifies
   whether COMMODITY `multi_asset_cot` PF=7.71 is real edge or artifact. Prior
   runs were cancelled. This is Priority #1 from DAILY_IDEAS.

2. **CI verified green** — no stale failures across all workflows.

3. **EQUITY blocker root-cause confirmed:**
   - `stocks_rsi2_pullback` (n=37) is in BLOCKED_ASSET_STRATEGY_PAIRS (WR=38%/PF=0.97)
   - After exclusion: only n=7 resolved EQUITY picks remain from non-blocked strategies
   - PBO/SPA gates report "no strategies with n≥20" — technically correct
   - The dashboard n=238 comes from `asset_class_health` (dashboard fallback)
   - EQUITY WATCH is correct and cannot be fixed by code — needs strategy accumulation

4. **tweaks_needed.json** — 8 entries (AUD-USD/BTC-USD/DOGE-USD/SOL-USD symbol disables
   and timeframe optimizations). No Python code references this file. It appears
   to be a stale artifact from a now-unused optimization system. No action taken.

## Pending Items Requiring User Approval

1. **Block `cta_cross_asset_tsmom` for COMMODITY** — WR=12.7% n=71
   - This would reduce CT=F concentration and potentially clear COMMODITY WATCH
   - Still needs explicit user approval per CLAUDE.md rule
   - From Session AO (2026-05-17)

2. **`CONCENTRATION_CAP_BY_CLASS = {"COMMODITY": 0.85}`** — CT=F at 65.25%
   - Alternative to blocking: raise per-class cap
   - Also needs explicit user approval
   - From Session AO (2026-05-17)

## Questions for Swarm

1. **EQUITY WATCH:** The only way to advance EQUITY to MONEY_READY is to accumulate
   n≥20 resolved picks from a non-blocked strategy. The dashboard shows PF=2.04
   WR=54.2% (good stats) but these come from the blocked `stocks_rsi2_pullback`.
   Should we: (a) wait for accumulation, (b) investigate if `smart_money_accumulation`
   (n=4 resolved) can be accelerated, or (c) look for other EQUITY strategies?

2. **COMMODITY ab_analysis:** If the ab_analysis confirms multi_asset_cot PF is real,
   what's the path from COMMODITY WATCH to MONEY_READY? The concentration cap
   (65% CT=F) is still the primary gate. User approval items above are the levers.

3. **tweaks_needed.json:** Should these 8 symbol-disable/timeframe entries be committed
   (as a data artifact cleanup) or deleted as stale files with no consumers?

4. **Overall verdict:** Is Session AW APPROVE? Is there any actionable item we're
   missing that the swarm can identify from the current state?

## Verification

- CI: 0 stale failures (verified 2026-05-17T18:26Z)
- CRYPTO: MONEY_READY at PF=2.54 (verified)
- ab_analysis workflow: dispatched run #25999062203 (in progress)
- Prior swarm verdicts: AR through AV all deepseek APPROVE
