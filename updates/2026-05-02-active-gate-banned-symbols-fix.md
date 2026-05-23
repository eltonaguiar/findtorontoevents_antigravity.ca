# 2026-05-02 — Active-Gate `CRYPTO_BANNED_SYMBOLS` Defense-in-Depth (Issue #622)

## What was broken

`CRYPTO_BANNED_SYMBOLS` (defined at `alpha_engine/hedge_fund_quality_gate.py:33`) lists symbols that must NEVER be traded — DOGEUSDT is entry #1.

The ban was enforced at exactly **one** place in the active-pick pipeline: `passes_hedge_fund_gate()`, called only from `audit_trail/quality_gates.py:passes_smart_gate()`.

But the dashboard's active-pick visibility filter is `passes_active_gate()` — which **never invoked the ban check**. Picks could fail the smart-gate and still appear in the active-picks list.

PR #613's Kimi review (merged 2026-05-02) observed DOGEUSDT in S-tier active picks — exactly this bug. It's the same exec-time-vs-generation-time gate bypass anti-pattern documented in `feedback_gate_at_execution_not_generation` and the 2026-04-28 `project_banned_tier_gate_bypass_2026_04_28` investigation.

## What changed

`audit_trail/quality_gates.py:passes_active_gate()` — added a defense-in-depth check immediately after the symbol/status validation (the same boundary every active pick crosses):

```python
try:
    from alpha_engine.hedge_fund_quality_gate import CRYPTO_BANNED_SYMBOLS
    if symbol.upper() in CRYPTO_BANNED_SYMBOLS:
        logger.debug(f"Pick rejected: symbol in CRYPTO_BANNED_SYMBOLS ({symbol})")
        return False
except ImportError:
    # Module not importable in this environment (test, alt build) — skip.
    pass
```

The try/except is so the dashboard remains importable in minimal environments where `alpha_engine.hedge_fund_quality_gate` isn't available; the ban is silently skipped in those environments rather than crashing the dashboard. (Production environments always have the import path available, so the ban is enforced.)

## Why defense-in-depth, not "fix the smart-gate path"

Per memory `feedback_gate_at_execution_not_generation` (2026-04-28 finding):

> Filter-named paper accounts (HIGHFWWRABV55_SCOREABOVE50_V4) bypass their filter because gate only runs at pick-generation; re-run at exec step.

Ban enforcement at one boundary is brittle — a future refactor or new code path could re-introduce the gap. Re-checking the ban at every gate boundary (active-gate AND smart-gate AND hedge-fund-gate) makes the system robust to future changes.

## Test plan

`tests/test_active_gate_banned_symbols.py` — 8 tests, all passing locally:

| Test | Pins |
|---|---|
| `test_dogeusdt_rejected_at_active_gate` | Issue #622 specific |
| `test_dogeusdt_rejected_even_with_s_tier_priority` | The exact scenario from PR #613 review |
| `test_dogeusdt_rejected_for_any_direction` | LONG/SHORT/BUY/SELL all rejected |
| `test_banned_symbol_lowercase_input_still_rejected` | Case-insensitive |
| `test_all_banned_symbols_are_rejected` | Full ban list, not just DOGEUSDT |
| `test_btcusdt_not_rejected_by_ban_check` | Negative control — non-banned symbols not false-positive |
| `test_ethusdt_not_rejected_by_ban_check` | Negative control |
| `test_active_gate_works_when_hedge_fund_module_unavailable` | Graceful ImportError handling |

## Wire-up

`passes_active_gate()` is the canonical active-picks visibility filter; called from `audit_trail/dashboard_generator.py` and other places. No additional wiring required — the ban check fires automatically on every dashboard refresh.

## Cross-links

- **Issue #622** (DOGEUSDT exec-time bypass)
- PR #613 (Kimi review — surfaced the issue)
- Memory: `feedback_gate_at_execution_not_generation`, `project_banned_tier_gate_bypass_2026_04_28`
- `alpha_engine/hedge_fund_quality_gate.py:33` — `CRYPTO_BANNED_SYMBOLS` source-of-truth
- `audit_trail/quality_gates.py:4900` — `passes_smart_gate` calls `passes_hedge_fund_gate` (existing enforcement point; preserved)

## Note on current data

At the time of this fix, `audit_dashboard/data/dashboard_data.json` shows 0 DOGEUSDT picks in active. The bug isn't actively biting in production right now (the upstream source-system that was emitting DOGEUSDT picks may have been throttled), but the gate gap remains. This PR closes the gap so future regressions can't reintroduce the contract violation.
