# TASKSFORGROK2 — live task log (2026-05-17)

Living delegation + status doc. Grok consulted for design/diagnosis;
repo investigation done by parallel Claude subagents; edits/commits by Claude.

## Session context

Reproduction-grade external audit of the CRYPTO trading aggregate found the
`/audit` PF 1.33 is contaminated. Evidence:
`reports/crypto_edge_artifact_audit_2026_05_17.md`. P0 fixes C2/C3/C4 committed
on branch `crypto-audit-c3c4-safe` (C2 `86634773262`, C3+C4 `a06bc177b2b`).

## Todo table — FINAL

| # | Task | Status |
|---|------|--------|
| T1 | Push branch + PR for C2/C3/C4 | ✅ DONE — **PR #1127** |
| T2 | C1 — fixed-TP ghost-row resolution | ✅ DIAGNOSED + FIX-DESIGNED — implementation = follow-up PR (verdict-changing, 8k-row migration) |
| T3 | D2 — `aggregated_picks` PF contradiction | ✅ ROOT-CAUSED — implementation = follow-up PR |
| T4 | PONG-verify consult-* skills | ✅ DONE — cursor-agent verified (answer field = `.result`); opencode/kilo hang without a provider, skills caveated |
| T5 | Worktree cleanup | ✅ DONE — `cae-c2-wt` removed |

## T2 — C1 findings (subagent, CONFIRMED)

Resolver credits a TP hit at the **nominal `take_profit`**, not a verified
fill — 3 of 4 paths:
- `outcome_resolver.py:531-540` `_scan_ohlc_for_touch` — `return {"price": tp}` (bar high/low used only as trigger).
- `outcome_resolver.py:879-890` crypto live-spot — `effective_exit = tp` overwrites real `live_price` (comment "Use TP as exit for accuracy" is the inverted-logic bug).
- `outcome_resolver.py:1565/1571` claude_gainer_ml — `exit_price = tp1/tp2`.
- `forward_validator.py:1254/1276` — `tp * (1 ± 0.0005)` fixed 5 bp; still a constant offset, not a real fill.
This pins every win's `pnl_pct` to exactly the TP distance → the audit's
"70% of wins at exactly +3.5%" artifact. Secondary: `TIME_EXIT` graded WON on
raw `pnl>0` in forward_validator vs per-class noise floor in outcome_resolver
vs `EXPIRED` in the MySQL sync — inconsistent.

**Fix design:** gap-aware observed fill in `_scan_ohlc_for_touch` (fill at
bar `open` when the bar gapped past TP, else TP) + same in the 2 sibling paths;
add `_tp_fill_method` flag (`NOMINAL_TP_LEGACY` / `OBSERVED`) to ~8k rows;
re-resolve non-destructively only where OHLC is still fetchable (existing
`_legacy_pnl_pct` stamping preserves old values); aggregators report
`nominal_tp_fill_share`. Do NOT silently re-resolve in place.

## T3 — D2 findings (subagent, ROOT-CAUSED)

`systems[]` (PF 4.49) is built from the **raw `closed` ledger** (402 resolved
for aggregated_picks); `system_clean_metrics` (PF 0.53) is built from
`resolved_closed` **after mirror-dedup + dead-strategy prune** (120 resolved).
282/402 (70%) of aggregated_picks' resolved rows are mirror duplicates the
codebase itself dedups for headline stats (`dashboard_generator.py:13794`,
comment: "critical fix for inflated WR/PnL"). The `systems[]` block was never
switched to the deduped pool. `aggregated_picks` is a synthetic re-tagger; its
+765 PnL is concentrated in 94-98%-WR LONG-only crypto sub-strategies =
double-counted mirror rows.

**Trust `system_clean_metrics`: aggregated_picks PF ≈ 0.53 — a LOSER**, not the
PF 4.49 winner `systems[]` claims. **Fix:** point the `systems[]` builder
(`dashboard_generator.py:13692`) at `deduped_closed`, or exclude
`aggregated_picks` from the systems leaderboard as a re-tagger.

## Progress log

- 2026-05-17 — doc created; C2/C3/C4 committed.
- 2026-05-17 — T1 PR #1127 opened. T4 done (cursor-agent verified, opencode/kilo caveated). T5 worktree removed.
- 2026-05-17 — T2 + T3 investigated by 2 parallel subagents + Grok; both root-caused with fix designs above. Implementation deferred to a follow-up PR — both are verdict-changing trading-ledger changes that need deliberate review, not a fire-and-commit.
