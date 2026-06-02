# EAGLE2 operational next steps executed (2026-06-02)

**Goal #1** — daily operator loop + ETF forward pilot wiring (no capital promotion).

## What ran

| Step | Command | Result |
|------|---------|--------|
| Daily EAGLE bundle | `python3 tools/run_eagle_suite.py` | ok=True — money_ready, emitter census, pick pulse, admissibility, swarm verify |
| ETF paper pilot | `python3 tools/run_verified_pilots_daily.py` | ok=True — XLK BUY open (virtual forward book day-1) |
| Strategy admit | `etf_dual_momentum` | FORWARD_PILOT_ONLY, WF PASS OOS PF 1.21 |
| Nav matrix | `tools/audit_pick_funnel/build_nav_surface_matrix.py` | all surfaces `no-edge` (honest) |
| Resolver health | `tools/check_resolver_health.py` | overall YELLOW (stale open picks, forward_test columns pre-ALTER) |

## Shipped (this session)

1. **`verified_strategies/paper_pilot/etf_dual_momentum_pilot.py`** — daily virtual signal vs SPY; logs to `etf_dual_momentum_paper_log.jsonl`.
2. **`tools/etf_forward_stats.py`** — forward n / PF / WR gates → `reports/etf_forward_stats_latest.json`.
3. **`tools/run_verified_pilots_daily.py`** — orchestrates pilot + stats + `pilot_forward_dashboard.py` (CI workflow target).

## Forward pilot status

- **n_closed:** 0 (first OPEN logged 2026-06-02, symbol XLK)
- **promotion_ready:** false (needs n≥100, PF≥1.5, WR≥50%)
- **shadow_checkpoint:** false (needs n≥30)
- **Scanner merge:** OFF (`ETF_VERIFIED_DUAL_MOMENTUM_ENABLED` stays shadow/off)

## Capital decision (unchanged)

**NO-GO** production `/audit` sizing. Paper watch + ETF shadow pilot only.

## Daily cron (local or CI)

```bash
python3 tools/run_eagle_suite.py
python3 tools/run_verified_pilots_daily.py
```

GitHub: `.github/workflows/verified-pilot-daily.yml` at 06:15 UTC.

## Resolver hygiene follow-ups (YELLOW)

1. Run forward_test column ALTER on `ejaguiar1_stocks` per `tools/check_resolver_health.py` note.
2. Review stale open picks (STOCKS 333 estimated stale / 48h hold).
3. CRYPTO concentration red (`top_source_share=0.55`) — EAGLE2 Phase 0 gates on main.

## Deploy audit JSON (optional after local refresh)

```bash
python3 tools/deploy_audit_files.py --only pick_funnel
# uploads verified_edge_status, pilot_forward_dashboard, nav_surface_edge_matrix when configured
```

Refs: `reports/best_picks_swarm_review_2026-06-02.json`, `reports/eagle_suite_latest.json`, `reports/etf_forward_stats_latest.json`.
