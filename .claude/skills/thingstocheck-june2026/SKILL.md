---
name: thingstocheck-june2026
description: Use when investigating the /audit dashboard for hidden edges, debugging why no per-asset-class picks are profitable, checking picks-now.html forward-tested performance, ai-tournament.html model leaderboard staleness, portfolio_history.html staleness, ai_leaderboard.html missing models, pick_funnel.html accuracy, research_index.html coverage, and "high-conviction" / "smart picks" / "best score" / "proven only" filter logic. Also for "why is the forward WR only 21%?" and "which filter combination surfaces a real edge?"
---

# Things to Check — June 2026 Audit Investigation

## Overview

Cross-cutting investigation skill for the /audit dashboard surfaces. The user wants to know:
1. Is there a hidden edge buried in some filter combination?
2. If not, why are NO per-asset-class picks profitable (not even one class)?
3. Why is `picks-now.html` forward-tested WR only 21%?
4. Why is `ai_leaderboard.html` mostly empty (only claude-opus-4.7 has data)?
5. Why is `ai-tournament.html` "NOT MONEY-READY" everywhere?
6. Is `portfolio_history.html` worth resurrecting?
7. Is `pick_funnel.html` accurate?
8. Are `kimi_direct`'s numbers biased by a single-snapshot resolver?
9. Is `gpt4_1`'s 55.6% WR real?
10. Are there data-quality issues like reverse-stock-splits inflating WR or active-pick-limits biasing?

## Key Webpages

| URL | Purpose | Investigation surface |
|---|---|---|
| https://findtorontoevents.ca/audit/ | Master dashboard | Filter combinations: high-conviction, smart picks, proven only, best score, star, active picks |
| https://findtorontoevents.ca/audit/picks-now.html | Best possible picks right now | Forward-tested performance panel; growth-stock-screener style valuation factors |
| https://findtorontoevents.ca/audit/portfolio_history.html | Per-portfolio P&L over time | Staleness check; is it still being updated? |
| https://findtorontoevents.ca/audit/pick_funnel.html | Honest funnel for "is there an edge?" | Accuracy cross-check |
| https://findtorontoevents.ca/audit/ai_leaderboard.html | Best model leaderboard | Why is it stale / only 1 model has data? |
| https://findtorontoevents.ca/audit/ai-tournament.html | All AI models, NOT MONEY-READY label | kimi_direct + gpt4_1 cross-check |
| https://findtorontoevents.ca/audit/research_index.html | All research notes | Are we leveraging it? |
| https://findtorontoevents.ca/audit/verified_alpha.html | Curated "verified" picks | What's the bar? |
| https://findtorontoevents.ca/audit/us_equity_picks.html | US equity picks | long-term value / swing plays / closed holds sub-tabs |

## When to Use

- "Is there a hidden edge on /audit?"
- "Why are we 0/7 classes profitable?"
- "Why is picks-now WR only 21%?"
- "Investigate the audit dashboard"
- "Audit pick performance and fix issues"
- "Debug forward-tested performance"
- Any investigation involving: ai_leaderboard, ai-tournament, portfolio_history, pick_funnel, picks-now, research_index, verified_alpha, us_equity_picks, high-conviction, smart picks

## Database Schema Quick-Ref

- **mysql.50webs.com:3306 / ejaguiar1_stocks** — `at_raw_picks`, `at_signal_outcomes`, `at_consensus_picks`, `trading_picks`, `at_pick_outcomes`, `at_filter_log`, `pick_summary`, `pf_registry`
- **mysql.50webs.com:3306 / ejaguiar1_backtests** — `bt_backtest_trades`, strategy backtest results
- **mysql.50webs.com:3306 / ejaguiar1_backups** — read-only backups for destructive ops (ALWAYS backup first)

## Debug Order (the right sequence)

1. **Read the live HTML** of the page (via `curl -sL`) — get the actual rendered content, not the marketing copy
2. **Cross-reference the JSON truth surfaces** in `audit_dashboard/data/`: `money_ready_verdict.json`, `pf_registry.json`, `entry_conditions_forward.json`, `picks_now.json`, `ai_tournament_*.json`, `ai_tournament_leaderboard.json`, `ai_tournament_picks_latest.json`
3. **Cross-reference the MySQL truth**: pick count, WR, PF, asset_class breakdown per source/strategy/symbol
4. **Identify the divergence** between "what the page says" and "what the data says"
5. **Root-cause the divergence** (resolver bug? backfill contamination? active-pick-limit? reverse-split?)
6. **Recommend the fix** with file:line + reproducer command

## Common Failure Modes (the "we keep hitting these" list)

- **Single-snapshot resolver contamination**: a model emits one pick, resolver runs once on stale data, WR computed from 1 row → 100% or 0%. Fix: minimum n threshold or backfill with intrabar OHLC.
- **Reverse-stock-split contamination**: stock had a 10:1 split, entry_price=$50, exit_price=$5, resolver says -90% loss, but the stock didn't actually lose 90%. Fix: split-aware price feed.
- **Active-pick-limit bias**: per-strategy or per-source limit caps the number of LIVE picks. Resolver's denominator doesn't include the cap'd-out rows. Fix: include cap'd rows as "never closed" with neutral pnl.
- **Single-source concentration**: 91.7% of "Smart-Picks" come from one source → not an edge, a counting artifact.
- **Soft-resolution inflation**: TIME_EXIT at close counts as WON if close>entry, even if position was underwater 95% of the hold.
- **Time-window cherry-pick**: WR computed on a 7-day window where 3 picks happened to win.
- **Missing sign-flip quarantine**: strategy flips LONG→SHORT mid-history, resolver doesn't catch the flip, PnL doubles.
- **Forward lane reclassification lag**: intrabar resolver changes OPEN → EXPIRED, but the forward lane's WR is computed before the reclassification.

## Output Convention

When this skill is invoked, the deliverable is a `PLAN_INSIGHTS_<MODEL>_<DATE>_<TIME>.MD` file in the repo root (or `docs/`) — with sections for:
- **Accomplishments (this session)** — bullets, file:line cited
- **Findings** — what's broken, with the data that proves it
- **Next Steps (P0/P1/P2)** — actionable, with reproducer
- **Areas for Further Improvement** — bigger swings, longer horizons

Filename: `PLAN_INSIGHTS_MINIMAX_June122026_634pm.MD` (24h format, EST local)
If file exists, append `_A`, `_B`, etc. before `.MD`.

## Anti-Fabrication Rules (MANDATORY)

- Never cite a pick count, WR, or PF you have not read from JSON or run a live MySQL query to verify
- Never claim a model has "data" without showing the row count
- Never say a strategy is "losing" without computing the actual loss amount
- Never declare a page "stale" without comparing `generated_at` to `now()`

## Related Skills

- `audit-pick-flow` — the 7-stage pick pipeline + gate logic + per-table case studies (USE THIS FIRST for pipeline questions)
- `money-maker-readyv2` — money-ready verdicts, TIER definitions, FALSIFICATION bars
- `db-schema` — table structures, joins, conventions
- `consult-minimax` / `consult-multi` — multi-AI peer review / swarm consensus on edge claims
