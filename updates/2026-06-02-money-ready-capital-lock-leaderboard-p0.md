# Money-ready capital lock + AI leaderboard honesty (P0)

**Date:** 2026-06-02  
**Goal:** #1 — `/audit` measurement honesty (EAGLE2 workstream A)

## What was broken

- Production CRYPTO/EQUITY (and other non-`MONEY_READY` classes) could still surface on **Smart Picks / high-conviction** paths while `money_ready_verdict.json` showed **0** deployable classes.
- **`ai_leaderboard.html`** ranked swarm attribution without stating it is **not** the policy-clean production book; refresh was **weekly** only (`ai-leaderboard-refresh.yml` Monday cron).

## What changed

1. **`alpha_engine/money_ready_verdict.py`** — `class_verdict()`, `sizing_multiplier_for_class()`, `is_capital_locked_class()` with TTL-cached verdict rows.
2. **`audit_trail/quality_gates.py`** — `tag_money_ready_capital_lock()` on `passes_active_gate` (`_sizing_override=zero`); Smart gate blocks non-`MONEY_READY` classes when `MONEY_READY_SMART_GATE_ENFORCE=1` (default).
3. **`audit_dashboard/ai_leaderboard.html`** — research-tier banner + live fetch of `money_ready_verdict.json`.
4. **CI** — `ai-leaderboard-refresh.yml` → daily `15 6 * * *`; `verified-pilot-daily.yml` builds leaderboard + `write_verified_edge_status.py`.

## Rollback

- `MONEY_READY_CAPITAL_LOCK_ENABLED=0` — stop zero-sizing tags on active picks.
- `MONEY_READY_SMART_GATE_ENFORCE=0` — allow Smart gate through (not recommended).

## Verification

```bash
python3 -m py_compile alpha_engine/money_ready_verdict.py audit_trail/quality_gates.py
pytest tests/test_money_ready_capital_lock.py -q
python3 tools/ai_attribution/build_ai_leaderboard.py
```

**Refs:** `reports/EAGLE2_2026-06-02_GROK.md` (A1), `reports/EAGLE_2026-06-02_GROK.md` (leaderboard root cause).