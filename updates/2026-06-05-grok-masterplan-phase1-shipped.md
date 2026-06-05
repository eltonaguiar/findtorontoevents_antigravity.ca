# Grok MASTERPLAN Phase 1 — Shipped 2026-06-05

**Source plan:** `MASTERPLAN_JUNE52026_GROK.MD`  
**Goal:** #1 — stop bleed, clean ingest contract, fresher recency panels, CRYPTO LONG gate

## What changed

| Area | File | Change |
|------|------|--------|
| Clean ingest | `tools/clean_ingest_v2.py` | Drift / RSPLIT / TP_HIT_REPLAY / MISPRICED rejects; `--sample N` audit |
| Tests | `tests/test_clean_ingest_v2.py`, `tests/test_promotion_gate_tier2.py` | Unit coverage |
| Promotion ladder | `audit_trail/promotion_gate.py` | `evaluate_forward_tier2()` — n≥100, WR≥55%, PF≥1.4, DSR, OOS ratio, regime |
| CRYPTO LONG | `audit_trail/quality_gates.py` | `CRYPTO_PRODUCTION_BLOCK_LONG=1` (default); exempt `_eagle4_flipped` |
| Recency CI | `.github/workflows/audit-dashboard.yml` | Runs `build_recency_summary.py` after dashboard_generator |
| AI leaderboard UI | `audit_dashboard/ai_leaderboard.html` | Frozen-book banner when n<50 or newest pick >14d |
| Leaderboard JSON | `tools/ai_attribution/build_ai_leaderboard.py` | Emits `pick_date_range` for UI |

## Verification

```bash
python3 -m pytest tests/test_clean_ingest_v2.py tests/test_promotion_gate_tier2.py -q
python3 -c "import py_compile; py_compile.compile('tools/clean_ingest_v2.py', doraise=True)"
python3 -c "import py_compile; py_compile.compile('audit_trail/promotion_gate.py', doraise=True)"
python3 tools/clean_ingest_v2.py --sample 100
python3 tools/audit_pick_funnel/build_recency_summary.py
python3 -m tools.ai_attribution.build_ai_leaderboard
```

## Operator follow-ups (not auto-applied)

1. **Pause tournament cron:** `gh workflow disable ai-tournament-pipeline.yml` (if still enabled)
2. **GHA variable:** `CRYPTO_PRODUCTION_BLOCK_LONG=1` (code default already ON)
3. **FTP after merge:** `python3 tools/deploy_audit_files.py --only pick_funnel` + ai_leaderboard data dir
4. **`trading_picks_v2` table:** run only after `ejaguiar1_backups` snapshot + parity report from `clean_ingest_v2 --sample 1000`

## Env knobs

- `CRYPTO_PRODUCTION_BLOCK_LONG=0` — re-enable LONG (not recommended until 14d LONG WR ≥45%)
- `CRYPTO_PRODUCTION_BLOCK_LONG_OVERRIDE=1` — emergency bypass
- `CLEAN_INGEST_REJECT_TP_HIT_REPLAY=0` — disable replay reject in validator