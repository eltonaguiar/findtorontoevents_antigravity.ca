# Money-Ready Gates + Top Sleeves + GHA Fixes — 2026-06-05

## What was broken

1. **`alpha_engine/eagle_gates.py` corrupted** — line 1 was prose text (silent shared-tree revert), causing `SyntaxError` and breaking `money_ready_verdict` imports.
2. **Feed Health Check failing hourly** — live `dashboard_payload.json` had `ueps.unrealized_pnl_pct: null`; health check used `.get(key, 0.0)` which returns `None` when key exists → `float(None)` → `invalid_numeric_fields`.
3. **auto-shutdown-monitor failing** — workflow referenced non-existent `DB_USER_STOCKS` secret.
4. **ai-tournament MISPRICED banner understated contamination** — said 914; live DB has 4,154 `MISPRICED_ENTRY` rows.
5. **No per-strategy "top money-ready" surfacing** — aggregate class verdicts all `NOT_READY`/`INSUFFICIENT_DATA` but one T2 CRYPTO sleeve (`crypto_liquidity_wick_reversal_v1` n=30 PF=1.55) was invisible on `/audit`.

## What changed

| File | Change |
|------|--------|
| `alpha_engine/eagle_gates.py` | Restored from HEAD (P0 corruption fix) |
| `alpha_engine/money_ready_verdict.py` | Added `_top_money_ready_sleeves()` → `top_sleeves` in per-class JSON; MIN_N_CLASS=100 + bootstrap/WF shadow gates already present |
| `audit_dashboard/template.html` | Live JS renders WF/BOOT/STALE badges + top sleeve under each `data-mg-class` tile |
| `audit_dashboard/ai-tournament.html` | MISPRICED count 914 → 4,154 |
| `audit_trail/dashboard_payload_health.py` | `float(x or 0.0)` for nullable numerics |
| `.github/workflows/auto-shutdown-monitor.yml` | Hardcode `ejaguiar1_stocks` user (secret exists only for password) |

## Verification

```bash
python3 -m py_compile alpha_engine/eagle_gates.py alpha_engine/money_ready_verdict.py
PYTHONPATH=. python3 alpha_engine/money_ready_verdict.py --json | python3 -c "..."
# CRYPTO top_sleeves: crypto_liquidity_wick_reversal_v1 n=30 PF=1.55 (single-src flagged)
```

## Current money-ready state (honest)

- **MONEY_READY classes: 0** (correct — CRYPTO n=301 but WR/PF/boot fail)
- **Closest sleeve:** `crypto_liquidity_wick_reversal_v1` — T2 on paper, single-source artifact flagged
- **mega_mutation:** HOLD per 4/4 swarm — unblock ~June 12-16 after 7-10d clean sign-coherence + 1 post-fix signal
- **bt_backtest_trades sync:** 4M-row gap sync running in GHA (run 27019279488)

## Deploy

After merge: hourly audit-dashboard cron regenerates `money_ready_verdict.json`. For immediate surface updates:

```bash
python3 tools/deploy_audit_files.py --only ai_tournament
# template.html ships via audit-dashboard.yml cron or manual deploy_audit_files.py
```
