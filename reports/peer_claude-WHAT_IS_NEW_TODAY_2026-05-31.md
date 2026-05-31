# WHAT IS NEW TODAY (2026-05-31)

One-page operator brief. All links live; HTTP 200 verified.

## Live for you to look at right now

**5 portfolio variants** (all render HTTP 200):
- [portfolio_mix__conservative_top1](https://findtorontoevents.ca/audit/pf.html?key=portfolio_mix__conservative_top1)
- [portfolio_mix__balanced_top3](https://findtorontoevents.ca/audit/pf.html?key=portfolio_mix__balanced_top3)
- [portfolio_mix__aggressive_top5](https://findtorontoevents.ca/audit/pf.html?key=portfolio_mix__aggressive_top5)
- [portfolio_mix__diversified_per_class](https://findtorontoevents.ca/audit/pf.html?key=portfolio_mix__diversified_per_class)
- [portfolio_mix__sharpe_optimized](https://findtorontoevents.ca/audit/pf.html?key=portfolio_mix__sharpe_optimized)

**AI Tournament leaderboard now renders** (was blank):
- https://findtorontoevents.ca/audit/ai-tournament.html
- Backing JSON `ai_tournament_leaderboard.json` `generated_at: 2026-05-31T05:00:12Z`, schema v1.0, Wilson WR CI + Bootstrap PF CI.

**DATA INTEGRITY FAILURE banner cleared on /audit/**:
- https://findtorontoevents.ca/audit/ — banner went RED -> GREEN. Page now shows the MAJOR GOAL banner + Truth-Layer Reality citation (still up by design), but no integrity-failure block.
- Backing `dashboard_data.json` `generated_at: 2026-05-31T06:51:16Z`.

## What each variant means in one line
- **portfolio_mix__conservative_top1** — single top persona, control variant
- **portfolio_mix__balanced_top3** — equal-weight top 3 with class diversification
- **portfolio_mix__aggressive_top5** — top 5 weighted by Wilson-LB WR
- **portfolio_mix__diversified_per_class** — best persona per asset class
- **portfolio_mix__sharpe_optimized** — top N by Sharpe with regime gate

## All variants are SHADOW-PAPER-ONLY
They track performance only — they do not allocate live capital. To activate any
variant for live sizing, **operator action required** (promote-to-live toggle in
the variant's JSON `requires_operator_promotion_to_live` flag).

NOTE (transparency): the variant HTML pages serve 200, but the individual
`/audit/data/pf/portfolio_mix__*.json` data files are currently **404 on the
FTP root** — the HTML template is deployed, the per-variant JSONs need an FTP
push to `audit/data/pf/`. Open follow-up: deploy the 5 JSON sidecars to make
the in-page metrics render fully. See `reports/peer_claude-ftp-deploy-portfolios_2026-05-31.md`.

## 6 per-class strategy-grounded personas also landed (PR #219)
EQUITY / FOREX / CRYPTO / ETF / BOND / COMMODITY — each grounded in a specific
proven strategy. **33 operator activation steps** documented in the PR.

## Operator-pending decisions
1. Deploy the 5 `portfolio_mix__*.json` sidecars to FTP (`audit/data/pf/`) — HTML renders, JSON 404
2. Promote-to-live decision on each of the 5 portfolio variants (all currently shadow-paper)
3. Activate the 6 per-class personas from PR #219 (33-step playbook)
4. ENH#54 follow-up (per money-ready 2026-05-31 memory)
5. INCIDENT_FOREX#7 follow-up
6. INCIDENT_STOCKS#7 follow-up
7. BONDS#3 follow-up
8. Confirm AI-tournament leaderboard ranking formula (`lower_95pct_WR * lower_95pct_PF`, min_n=30) matches operator expectation

## Final 5 operator decisions awaiting you

Zoo's stale 30-item dump triaged: **25/30 already shipped, 5 genuinely remain**.
These are operator-only because each touches production-scoring-path files,
policy decisions, or multi-file scope. Cross-referenced against all merged PRs
on 2026-05-31 — none have an existing merged PR.

| # | ID | Class | Sev | Title | Why operator-only | Acceptance criteria | Blast | Best time |
|---|----|-------|-----|-------|-------------------|--------------------|-------|-----------|
| 1 | INC#6 | Stocks/EQUITY | P0 | EQUITY emission unlocked (1,424 outcomes) but all strategies PROBATION-tier (trust=3) | Touches strategy registry trust_score policy + wiring of pead_equity/us_equity_screener into MySQL write path. Multi-file scope across `alpha_engine/` strategy modules + scoring gates. | One existing EQUITY strategy promoted to trust>=5 with WR>=50% / PF>=1.5 on n>=100 clean; OR a new wired strategy demonstrating same. | HIGH | After soak — let current 1,424 outcomes accumulate to n>=100 per strategy first |
| 2 | INC#1 | CRYPTO | P1 | ML "edges" with PF 99–1094 are likely look-ahead leakage | Requires policy call: mark vs kill the DSR=0.9995 claims; touches `calculate_smart_score` + dashboard labeling. Walk-forward gate is a scoring-path change. | Walk-forward gate landed in `alpha_engine/` scoring; dashboard relabels suspect claims as "small-sample, awaiting n>=100"; PF cap audit logged. | MED | Next session — needs scoring review, not blind-fix |
| 3 | INC#3 | CRYPTO | P1 | meta_strategy template explosion — 1.6M template rows across ~140 symbol/dir pairs in bt_backtest_trades | Policy fork: blanket-block meta_strategy on CRYPTO/MEMECOIN vs symbol-triple enumeration. Both options touch `BLOCKED_SOURCE_SYSTEMS` and require `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md` per CLAUDE.md. | db_health refresh post-commit `d317560ac9c` shows template count stable; operator picks block-vs-enumerate; mutation analysis CSV exported. | MED | After soak — wait 1-2 cron cycles for db_health refresh |
| 4 | INC#34 | OVERALL | P1 | CI Tests: 17 pytest failures on main (m096, m098, quality_gates, pr10_ab, outcome_resolver) | Three sub-decisions all change production scoring: (a) AB_ENABLED default flip after 24h soak, (b) crypto_not_liquid_core gate rejecting CRYPTO picks, (c) FOREX noncrypto resolver test data. Not safe to blind-fix. | All 17 pytest failures resolved with explicit operator sign-off per sub-decision; PR notes per (a)/(b)/(c). | HIGH | Now for (a) (24h soak elapsed); next session for (b)/(c) |
| 5 | INC#41 | OVERALL | P3 | at_signal_outcomes SL_HIT rows have 24% with positive pnl_pct (labeling inconsistency) | Sign-convention policy decision (reclassify vs normalize) affects outcome_resolver — same upstream path the resolver-intrabar T2-blocker (per MEMORY.md session-close 2026-05-31) sits on. | source_system breakdown investigated; policy choice documented; resolver patch lands behind feature flag. | LOW | After soak — coordinate with resolver-intrabar work |

## 4 NEW operator-action items from latest waves

1. **Re-trigger `Run-Backtests-and-Deploy-Dashboards`** to publish post-#210 `db_health.json` — current live file is pre-fix; needs the next nightly or a manual workflow_dispatch.
2. **Decide on `harness_healthy` gate fix** for `tools/db_health_check.py:624` — silent-broken-harness defect surfaced in PR #221 findings. Needs operator review because gate logic touches what /audit considers "healthy".
3. **Decide on qwen vs zoo `CONFIDENCE_INVERT_CRYPTO` contradiction** — qwen claims global ML inversion; live audit refutes (per MEMORY.md confidence/trust edges 2026-05-31, localized 0.8-bucket dip only). Operator picks which peer to trust.
4. **Decide on qwen's false `skyrocket_detector` wiring claim** — re-attempt the wire-up under CLAUDE.md Wire-Up Rule, or formally retire the module. No callers in production scoring path today.

## Session ledger
~70+ PRs merged + 11 closed. 12 phases shipped. Banner went from RED -> GREEN.
Tournament leaderboard fixed (blank -> ranked). 5 portfolio variants + 6
per-class personas published. /audit no longer claims DATA INTEGRITY FAILURE.
