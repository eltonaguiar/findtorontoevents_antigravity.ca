# active_picks_sync PR #2 — Live Writer Design (2026-05-12)

PR #1 (`bf85c4a343c`) shipped the DRY-RUN scaffold + path-trigger. PR #3
(`9747f9594ec` cron wire) put it in the hourly job. **PR #2 flips the
verdict from JSON-only sidecar to actual MySQL UPDATE + closed_picks.json
append.**

This document is the design plan. Implementation deferred to next session
pending one successful workflow run that produces inspectable DRY-RUN
output (cron at :10 should fire with the wire from commit 452d2ca9b63).

## What changes

`alpha_engine/active_picks_sync.py` gains a `--live` flag (default OFF
for safety). When set, the `main()` loop:

1. Same SELECT + price-fetch + verdict-compute as DRY-RUN.
2. For each verdict where `new_status` is terminal:
   a. Call `audit_trail.mysql_client.mysql_close_trade(symbol, direction,
      exit_price, exit_reason, pnl_pct, closed_at)` to atomically UPDATE
      `trading_picks` for that (symbol, direction) tuple. Already
      carries the WON-vs-PnL sign-coherence guard from commit 22b677c1167.
   b. ALSO UPDATE `at_raw_picks` directly: `UPDATE at_raw_picks SET
      status=%s, exit_price=%s, pnl_pct=%s, exit_reason=%s, closed_at=NOW()
      WHERE id=%s AND status IN ('OPEN','ACTIVE')`. The id-based WHERE
      ensures idempotency on retry.
   c. Append the verdict dict to `closed_picks.json` via the
      dedup-by-id read-modify-write pattern (per Cerebras Q5).
3. Maintain a per-cycle metrics dict: `synced`, `tp_hits`, `sl_hits`,
   `time_exits`, `mysql_failures`, `json_failures`. Log at end of cycle.

## Cerebras consult recommendations adopted

Per agent `aad788a0785b6a601` (2026-05-12):

| Q | Engine answer | Adopted? |
|---|---|---|
| 1 | New workflow step before resolver, not inline call | ✓ (already wired in audit-dashboard.yml; PR #3) |
| 2 | MySQL UPDATE THEN JSON append per row, atomic | ✓ (this design) |
| 3 | Per-class MAX_HOLD_HOURS dict kwarg | ✓ (already in DRY-RUN scaffold; production retains) |
| 4 | Cap 1000 symbols/cycle, batch 100 + 1s delay | ✓ (already in DRY-RUN; production keeps) |
| 5 | Idempotent if stateless | ✓ (id-based WHERE on MySQL UPDATE + dedup-by-id on JSON) |

## Concurrency safety

Issue: `closed_picks.json` is committed by the GHA workflow. A second
runner reading the file mid-append → re-emitting the same id → duplicate.

Mitigation:
- Read JSON → parse → check if id present → skip OR upsert → write atomic
  (write to `.tmp` then rename).
- The audit-dashboard.yml workflow already serializes the resolver step
  + commit step, so two concurrent runs writing closed_picks.json are
  rare. But the safety check is cheap.

## Forward verification plan

After PR #2 ships:

1. Inspect first cron run log: `gh run view <id> --log | grep
   active_picks_sync` — confirm `synced=N>0`, `mysql_failures=0`.
2. SQL probe after one cycle: `SELECT COUNT(*) FROM at_raw_picks WHERE
   status IN ('WON','LOST','EXPIRED') AND closed_at > NOW() - INTERVAL 1
   HOUR` — expect N>0 if the writer is hot.
3. Check `db_health.json::outcome_coverage.raw_resolved_pct` over 6
   hourly cycles — expect 0.09% → 1-5% climb as the backlog drains.
4. Verify resolver continues to see fresh `closed_picks.json` entries
   and doesn't regress to "resolved 0 picks/run".

## Risk register

| Risk | Mitigation |
|---|---|
| Live writer mis-fires on a contradicting (TP_HIT, pnl<0) verdict | Already-shipped sign-coherence guard at mysql_close_trade:628 traps this; the new code logs the WARNING but writes the corrected status |
| 10,000+ ACTIVE rows in at_raw_picks → first cycle catastrophic | --max-symbols 200 cap per asset class per cycle (already in scaffold). Backlog drains gradually. |
| yfinance price unavailable for some symbol | verdict=None for that row; row stays OPEN; next cycle retries |
| MySQL connection drop mid-cycle | per-row try/except; partial progress recorded; `synced` counter shows progress |
| concurrent runner appending to closed_picks.json | atomic write to `.tmp` + rename; dedup-by-id read-modify-write |

## Out of scope for PR #2

- regime-gate for Step 3 fold_1 outlier (separate concern)
- BOND scanner production wiring (commit 5c7a8c43a27 already wired registry)
- ml_gatekeeper CRYPTO inversion (separate gate, commit c778f8f1696)
- enhanced_ml_crypto retraining (manual workflow_dispatch trigger)

## Sizing estimate

| Subsystem | LOC | Effort |
|---|---|---|
| Live-write branch in main() | 40 | 30 min |
| closed_picks.json atomic-append helper | 30 | 30 min |
| at_raw_picks UPDATE wrapper | 20 | 15 min |
| Per-cycle metrics + logging | 20 | 15 min |
| Workflow toggle (`--live` arg in yml) | 5 | 5 min |
| Tests (smoke + idempotency) | 60 | 1 h |
| **Total** | **~175 LOC + 60 LOC tests** | **~2h** |

## Status

**DESIGN COMPLETE.** Implementation queued for next session pending one
clean DRY-RUN cron output. The qwen3.5cloud Ollama consult (2026-05-12)
confirmed this as the #2 critical-path item; only the regime-gate Step 3
fix ranks ahead.

## Refs

- `alpha_engine/active_picks_sync.py` (DRY-RUN scaffold, `bf85c4a343c`)
- `audit_trail/mysql_client.py:601 mysql_close_trade` (canonical write path)
- Cerebras consult — agent `aad788a0785b6a601` (5-question design pass)
- `reports/ollama_consult_money_maker_synthesis_2026-05-12.md` (qwen3.5cloud rec #2)
- Investigator B `afe33bc49b6e69d87` (original root-cause of 0.09% raw coverage)
- `reports/db_evidence_graded_final_2026-05-08.md` — F1 cascade context

## NFA

Research surface only. PR #2 is a code-only DB-write change; no real-money
sizing impact until paper-pilot + regime-gate + ROR MC verdicts clear.
