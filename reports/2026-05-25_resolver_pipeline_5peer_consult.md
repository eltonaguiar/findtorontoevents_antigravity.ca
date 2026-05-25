# Resolver Pipeline — 5-Peer Multi-AI Consult & Synthesis

**Date:** 2026-05-25
**Trigger:** User report — "signal_outcomes table is 82 days stale, AI tournament leaderboard empty (1,607 picks / 0 resolved across 10 models)"
**Panel:** Codex (OpenAI), Grok (xAI), Gemini (Google), Kimi K2.6 (NVIDIA NIM), Llama 3.3 70B (NVIDIA NIM — Cloudflare substituted out due to daily-neuron quota exhaustion)
**Status:** DIAGNOSIS COMPLETE — SCHEMA-DRIFT FIX APPLIED + AUX DEPLOY FIX APPLIED. Audit-mirror decision flagged for operator.

---

## TL;DR

The user's framing was wrong on every count except "the table is stale." Five independent peer AIs unanimously identified **three orthogonal issues**, not one:

1. `at_signal_outcomes` is a write-orphan audit-mirror table. No GitHub Actions workflow has ever invoked any of its 5 known writer scripts on a cron. 121 rows, last write 2026-03-04. **Not blocking the leaderboard.**
2. `tools/mysql_stale_picks_resolver.py` has been crashing daily since deployment with `OperationalError 1054: Unknown column 'asset_class' in 'field list'`. Schema-drift: the script references 4 columns that don't exist in `trading_picks` (`asset_class`, `tp_price`, `sl_price`, `resolved_at`). **The actual fixable bug.**
3. The AI tournament leaderboard is **healthy** — wrong table was queried. Live data: `tournament_picks` has 3,205 rows, 928 WIN + 798 LOSS + 1,479 OPEN, last resolved today (2026-05-25), 15 models active, zero stranded OPEN > 7d. **The "empty leaderboard" symptom is actually the AUX issue** — the regenerated HTML never gets FTP-uploaded.

Actions taken:
- **Patched** `tools/mysql_stale_picks_resolver.py` (SQL column-name fix; verified via live dry-run: 50 picks queried, 42 would resolve, 0 errors).
- **Added FTP deploy step** to `.github/workflows/ai-tournament-pipeline.yml` so the leaderboard HTML actually reaches findtorontoevents.ca.
- **Flagged for operator decision:** whether to add an `at_signal_outcomes` mirror to the live `outcome_resolver.py` (3 peers say yes, 1 says deprecate, 1 neutral) — see "Open question" below.

**Backfill warning (unanimous from all 5 peers):** do NOT backfill 82 days of `at_signal_outcomes` from current prices. That injects look-ahead bias into any forward-test edge derivation. The table should either stay sparse or only accept live-resolved rows going forward.

---

## Investigation — what the DB actually says

```
at_signal_outcomes      MAX(closed_at)=2026-03-04 08:47:58  COUNT=121
                        Sources: kimi_riseoftheclaw(39), kimi_signal_tracker(23),
                                 opposite_day(15), paper_trading(10), bundle_babies(6),
                                 Funding Rate Carry(4), paper_alpha_arena(4)...
                        → orphan audit-mirror, 5 manual writer scripts, 0 crons

tournament_picks        COUNT=3205, range 2026-05-19 → 2026-05-25
                        Status: WIN=928, LOSS=798, OPEN=1479
                        Last resolved: 2026-05-25
                        Models: 15 active (gemini_2_5_pro, llama4_scout, claude_opus_4_7,
                                glm4_7_flash, qwen3_6_max, grok3_direct, cursor_agent,
                                grok4_3, minimax_m2_5, mistral_large, deepseek_v4, grok3,
                                kimi_direct, deepseek_r1, deepseek_v3)
                        Stranded OPEN > 7d: 0

trading_picks           Last WON update: 2026-05-25 15:37:07
                        Last SL_HIT:     2026-05-25 15:37:57
                        Stranded OPEN > 7d: 83  (small backlog — what stale-resolver targets)
                        90d status mix: SL_HIT=1078, TP_HIT=828, TIME_EXIT=29865,
                                        OPEN=4126, WON=2364, LOST=3088, ...

trading_picks columns:  id, symbol, direction, strategy, entry_price, take_profit,
                        stop_loss, confidence, elite_score, trust_score, category,
                        source_system, status, pnl_pct, exit_price, created_at,
                        closed_at, exit_reason, updated_at, tp_fill_method
                        (NO asset_class, NO tp_price, NO sl_price, NO resolved_at)
```

## Code-trace findings

- `outcome-resolver.yml` runs hourly + succeeds, but writes JSON files (`alpha_engine/data/closed_picks.json`) — does NOT touch MySQL `at_signal_outcomes`.
- `consensus-outcome-tracker.yml` + `signal-recorder.yml` write SQLite, not MySQL.
- `ai-tournament-pipeline.yml` + `ai-tournament-price-tracker.yml` populate + resolve `tournament_picks` daily — healthy.
- `mysql-stale-picks-resolver.yml` fails daily at 04:00 UTC with column-name OperationalError → bug source.
- 5 files INSERT into `at_signal_outcomes` (`audit_trail/backfill_local_sources.py`, `paper_trading/mysql_sync.py`, `genome/progressive_promotion.py`, `tools/sql_edge_analyzer.py`, `generate_trade_logs.py`); ZERO are referenced by any workflow under `.github/workflows/`.

## Per-peer responses

The full per-peer transcripts are in `/tmp/resolver_consult/{codex,grok,gemini,kimi,llama}.out` on the runtime host. Summary of how each peer answered the five questions:

| Peer    | (a) Root cause framing                                                 | (b) Min-risk fix                                                                                       | (c) Verify                                              | (d) Leakage                                                       | (e) AUX                |
|---------|------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|---------------------------------------------------------|-------------------------------------------------------------------|------------------------|
| Codex   | 3 orthogonal issues; user wrong; leaderboard healthy                   | (i) patch schema-drift columns; REJECT (ii) mirror — would create divergent write surface; deprecate at_signal_outcomes | Patched SELECT against live DB, then trigger workflow   | Backfill from current prices = look-ahead; quarantine or skip      | Yes — add deploy step  |
| Grok    | 3 issues, same diagnosis                                               | (i) patch columns + (ii) add idempotent mirror in `outcome_resolver.py`                                | Manual resolver run + check both sinks                  | Same warning; require ex-ante provenance for any backfill          | Yes — add deploy step  |
| Gemini  | Same: 3 distinct failures                                              | Patch schema-drift + add mirror via INSERT in `outcome_resolver.py`                                    | Manual dry-run + verify backlog count                   | "Strictly forbidden"; backfill must use point-in-time OHLC          | Yes — final step       |
| Kimi    | Same diagnosis; explicitly notes leaderboard healthy                   | (i) patch columns; either skip or mirror via outcome_resolver                                          | `SELECT * FROM at_signal_outcomes ORDER BY created_at`  | Walk-forward only; do NOT use current prices                       | Yes                    |
| Llama   | Same; clean restatement                                                | Patch columns with SQL aliases; idempotent mirror after live resolution                                 | Patched SELECT + `gh workflow run`                      | Quarantine any reconstruction as `historical_backfill`              | Yes — call after rebuild |

**Unanimous on:** problem diagnosis (3 orthogonal issues), schema-drift fix, leakage warning, AUX deploy fix.
**Split on:** whether to add a write-mirror into `outcome_resolver.py`. Codex (the most cautious) recommends deprecating `at_signal_outcomes` instead because adding a second write surface that can diverge from `trading_picks` + JSON-source-of-truth is the same anti-pattern that created the orphan in the first place.

## Chosen approach

Apply only what is unambiguously consensus-safe:

1. **Schema-drift patch** — applied to `tools/mysql_stale_picks_resolver.py`. Uses SQL aliases (`category AS asset_class`, `take_profit AS tp_price`, `stop_loss AS sl_price`) so the rest of the module's dict keys keep working unchanged. UPDATE clause changed from `resolved_at=%s` to `closed_at=%s` (the equivalent column).
2. **AUX deploy fix** — added `FTP upload AI tournament artifacts` step to `.github/workflows/ai-tournament-pipeline.yml`, gated behind `if: ${{ !inputs.dry_run }}` and `continue-on-error: true`, modelled on the existing `incidents-enhancements-nightly.yml` pattern.
3. **`at_signal_outcomes` mirror — DEFERRED** to operator. The 3-vs-1 split is not strong enough consensus, and Codex's caution (creating a parallel write surface is what produced the orphan) is structurally sound. Flag for explicit decision in next session.

## Verification

Dry-run of patched resolver against live DB:

```
queried                       : 50
skipped_no_price              : 8
skipped_hold_not_elapsed      : 0
win                           : 13
loss                          : 29
errors                        : 0
dry_run                       : True
[DRY RUN] Would update 42 picks: 13 WIN, 29 LOSS
```

Zero `OperationalError`. The 8 skipped-no-price rows are real yfinance delistings (MATIC, APT) — expected, unrelated to the bug.

## Leakage risk (operator-facing)

The patched stale resolver uses `get_close_on_or_after(symbol, target_date)` where `target_date = created_at + hold_days`. This DOES use prices that came after pick generation, but that is the documented "stale-resolver" semantic — picks past their hold horizon get closed at their hold-horizon-day close. The resolver tags these rows with `exit_reason = f"stale_resolver_hold_{hold_days}d"`, which downstream forward-test code can (and should) filter out when computing live-edge metrics. This is acceptable; the real leakage trap is the separate `at_signal_outcomes` table whose 82-day gap **must not** be silently backfilled from today's prices.

## Open question for operator

Should `at_signal_outcomes` be:
- (A) deprecated entirely, redirecting downstream consumers to `tournament_picks` + `trading_picks` (Codex's recommendation), or
- (B) wired as an idempotent live mirror inside `alpha_engine/outcome_resolver.py` (Grok/Gemini/Kimi/Llama's recommendation)?

A search for downstream `SELECT ... FROM at_signal_outcomes` consumers is needed before deciding. Not blocking; AI tournament leaderboard is already healthy at the data layer, and the live HTML will refresh once the next `ai-tournament-pipeline.yml` cron run picks up the new FTP step (or on `workflow_dispatch`).
