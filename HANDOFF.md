# HANDOFF — 2026-05-24 08:15 UTC

**Branch:** `plan/institutional-readiness-2026-05-24`
**Last commit:** `b9a3550b` feat(qwen): add /dropchat-multipc skill

---

## What's Done (COMMITTED)

| Commit | What |
|--------|------|
| `022a9809` | fix(ci): CI Tests + Decile Separation Test workflow fixes |
| `b19ad3d0` | log: CHATBIBLE protocol failure resolved (gateway restored by copilot) |
| `64179783` | fix(chatbible): systemd auto-start for gateway (no more manual restarts) |
| `b9a3550b` | feat(qwen): /dropchat-multipc skill wire-up |

## What's Done (NOT COMMITTED — agent swarm output)

### Code fixes (ready to commit):
- **`alpha_engine/outcome_resolver.py`** — direction-aware PnL for SHORT positions (was inverted)
- **`audit_trail/backfill_local_sources.py`** — sign-coherence guard (WON + negative PnL → LOST)
- **`tools/populate_picks.py`** — XLI/ETF asset_class validation via canonical classifier

### New tools (all tests pass):
| File | Tests | Purpose |
|------|-------|---------|
| `tools/cleanup_ghost_rows.py` | 24 passed | DRY_RUN ghost row cleanup for 56K spam rows |
| `tools/resolve_stale_open_picks.py` | 40 passed | Batch TIME_EXIT for 29M stale open picks |
| `tools/check_resolver_health.py` | (in test_resolver_health.py) | Resolver health check (GREEN/YELLOW/RED) |
| `tools/test_won_pnl_contradiction.py` | 12 passed | Tests for WON/PnL sign coherence |
| `tools/audit_won_picks.py` | — | DB audit for WON picks with negative PnL |
| `tools/dedup_tournament_picks.py` | — | Dedup ai_tournament_picks_latest.json |
| `tools/regenerate_stale_reports.py` | — | Regenerate stale audit reports |
| `tools/report_freshness_tracker.py` | 41 passed | Freshness scanner (found 94 RED files) |
| `tools/test_report_freshness.py` | — | Unit tests for freshness tracker |
| `tools/test_ghost_cleanup.py` | — | Unit tests for ghost cleanup |
| `tools/test_resolver_health.py` | — | Unit tests for resolver health |
| `tools/test_audit_framework.py` | 40 passed | Unit tests for audit framework |
| `tools/audit_test_framework/` (4 files) | — | Unified audit test framework package |
| `updates/2026-05-24-won-pnl-fix.md` | — | Documentation |
| `updates/2026-05-24-ghost-row-cleanup.md` | — | Documentation |
| `updates/2026-05-24-open-bloat-resolution.md` | — | Documentation |
| `updates/2026-05-24-report-freshness-framework.md` | — | Documentation |
| `updates/2026-05-24-xli-asset-class-fix.md` | — | Documentation |

### Test summary: **157 tests pass, 0 failures** across all suites.

### Reports generated:
- `reports/audit_test_results_2026-05-24.json` — 8 of 9 tests FAIL (expected, reflects known data issues)
- `reports/report_freshness_2026-05-24.json` — 94 RED, 8 YELLOW, 39 GREEN files

## Critical Issues Still Open

| Issue | Severity | Status |
|-------|----------|--------|
| 29.2M open picks (validator frozen 270h) | CRITICAL | Script built, needs `--execute` on live DB |
| 56,559 ghost rows (MATICUSDT quan_engine spam) | CRITICAL | Script built, needs `--execute` on live DB |
| 38.97% PnL mismatch rate | CRITICAL | Needs MySQL sync working first |
| WON picks avg PnL -41.13% | CRITICAL | Code fix ready (3 files), not committed |
| MySQL Trading Picks Sync red >24h | CRITICAL | Needs GitHub Secrets rotation / 50webs IP allowlist |
| XLI tagged as CRYPTO in tournament picks | HIGH | Code fix ready in populate_picks.py |
| 14 of 18 metrics (78%) below industry standard | HIGH | Requires strategy rebuild, not a code fix |
| ML calibration inverted (high conf = worst WR) | HIGH | Requires ML pipeline rebuild |
| ai-tournament-pipeline.yml chronic failure | MEDIUM | Failing every push since 06:46Z, workflow file issue |

## Gateway Status

- **Linux (this machine):** systemd service running, auto-starts on boot, auto-restarts on crash ✅
- **Windows desktop (192.168.2.32):** Still manual — needs Scheduled Task setup
- Gateway healthy on `192.168.2.32:8788` (desktop) and `127.0.0.1:8788` (local)

## Next Steps

1. Review swarm code changes: `git diff alpha_engine/outcome_resolver.py audit_trail/backfill_local_sources.py tools/populate_picks.py`
2. Commit swarm fixes + new tools if approved
3. Run `tools/cleanup_ghost_rows.py --execute` to clear ghost rows
4. Run `tools/resolve_stale_open_picks.py --execute` to time-exit stale picks
5. Rotate MySQL secrets in GitHub (P1 — sync has been down >24h)
