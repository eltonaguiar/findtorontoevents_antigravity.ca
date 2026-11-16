# auditpage-v4 — what is left, prioritized — 2026-11-16T22:05Z

Agent `gx10-c9b9__auditpage-v4__grok-4-7`. Repo `eltonaguiar/findtorontoevents_antigravity.ca`.
This file is the status handoff. Previous detail: `ACTIONPLAN_AUDITPAGE/2026-11-16T1734Z_auditpage-v4/FINDINGS.md` and `PEER_REVIEW.md`.

## Done (verified this session)

| Item | Evidence |
|---|---|
| Honesty text is live: no "5/5 checks pass", no PF2.6/PF2.4, ghost rows now called a failing check, PM labelled shadow | `python3 tools/audit_honesty_live_check.py` → `LIVE_OK https://findtorontoevents.ca/audit/` (22:05Z) |
| Main **CI Tests green** after 6+ consecutive red pushes | run 43956391840-region success on `b31d6b17d4` at 21:27Z |
| 3 gates that silently failed open now work | PR 864 `5cbccaa86f1`: `_sym` NameError in M-045/M-046/M-047. 119 → 65 local failures, 0 new |
| Dashboard generate crash | PR 855 `b31d6b17d41`: int `new_picks` slice. Killed run 43896182188 |
| Display guards | PR 847 `c6ecd08d9ea`: infinite PF → `n/a`, `|Sharpe|>5` → `n/a`, PM out of Verified Alpha badge |

## P0 — verify the deploy, do not stack dispatches

1. **Run 43958090673** (started 21:14Z) checked out main **before** PR 855 merged (21:27Z). If `crypto_signal_engine/data/audit.json` has an int `new_picks`, it dies at "Generate dashboard payload and build HTML" the same way. **Wait for it to finish**; do not `workflow_dispatch` on top of it. The next `:10` cron carries the fix.
2. Confirm with `gh run list -w "Unified Audit Dashboard" -b main -L 3` that a run whose `headSha` is at/after `b31d6b17d4` reaches "Commit updated data" and "Deploy to all 3 FTP sites".

## P1 — data integrity (no destructive action without a dry-run)

3. **22,947 ghost rows are still in the ledger.** `audit_dashboard/data/db_health.json` `ghost_row_verdict` now fails them correctly. Do **not** run `tools/cleanup_ghost_rows.py --execute` without a dry-run diff and explicit go-ahead; they are MEMECOIN `meta_strategy` cohorts and deleting is irreversible.
4. `strategy_perf_by_class.json` still contains 356 zero-loss PF=999 sentinel cells. They are displayed as `n/a` in the headline path after PR 847, but the JSON still carries 999 for other consumers. Blank or cap PF at the producer.
5. `audit_dashboard/data/strategy_ic_analysis.json` is absent; the IC panel is retired in the template. Either generate the file or delete the dead panel markup.

## P2 — prediction markets / WIRED_IN

6. Prediction markets remain shadow (decision: PBO 0.603; copy-trading rejected). `prediction_market_consensus` stays on the kill list (`alpha_engine/config.py:294`). Do not un-blacklist it to "make PM wired".
7. `kalshi_signals.json` is missing at **both** `alpha_engine/data/` and `prediction_market_agents/data/`; `prediction_market_picks.json` exists only under `alpha_engine/data/`. Reconcile the write/read paths or unregister the missing sources.
8. `WIRED_IN/2026-11-15T0150Z_childlike-airport` is a frozen snapshot (XLV/LLY/SHY, paper only, sizing 0). Badge it static or add a rescan job.

## P3 — model / research (not display)

9. ML calibration is a **static 2026-05-15 measurement** on the page. `_calibrate_confidence` is a hardcoded score penalty, not a calibrator. Real work is recalibrating `confidence`, tracked in `alpha_engine/confidence_calibrator.py`.
10. ML Health age: gainer model `trained_at` 2026-05-25 (~175 days). Retrain or show age explicitly.
11. 0/9 classes money-ready. COMMODITY is the only WATCH and its policy-clean PF is ~0.19. No sleeve should be forward-tracked off the retired June PF 2.6/2.4 figures.
12. Remove `tests/test_quality_gates.py::TestM045EquityVixFilter` from the CI known-drift quarantine list — it passes now. The list has a standing TODO to shrink.

## Non-goals

No real-money sizing. No `push:` trigger on `audit-dashboard.yml`. No mass workflow deletion. No secrets on the bus.
