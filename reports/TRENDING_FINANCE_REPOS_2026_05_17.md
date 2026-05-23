# Trending Finance Repos — 2026-05-17 delta check

**Source:** user-pasted X post (`x.com/i/status/2055649685814030809`) — "fastest
growing GitHub finance repos this week."
**Question asked:** can any improve money-ready *predictions* per asset class?

## TL;DR — this list was already harvested

9 of the 10 repos are identical to `reports/TRENDING_FINANCE_REPOS_HARVEST_2026_05_03.md`
(2 weeks ago). That harvest already triaged all of them against the codebase.
**Do not re-harvest.** The two real findings below are the only net-new signal.

| Repo | 2026-05-03 verdict | Still valid? |
|------|-------------------|--------------|
| TradingAgents | SKIP — have `incubator/agents/*`; `tradingagents_emitter` already a pick source | yes |
| TradingAgents-CN | SKIP — Chinese A-share fork, no coverage | yes |
| Vibe-Trading | SKIP — equivalent; also already an MCP server in-session (`mcp__vibe-trading__*`) | yes |
| QuantDinger | SKIP — self-host Docker, wrong deploy model | yes |
| FinceptTerminal | SKIP — desktop Qt terminal, wrong shape | yes |
| daily_stock_analysis | MONITOR — multi-channel push pattern (EQUITY) | yes |
| scientific-agent-skills | EVAL — never triaged | **still open** |
| last30days-skill | SHIP — CRYPTO sentiment skill | **never shipped** |
| qlib | DEFER — alpha-factor module worth revisiting (EQUITY) | **never shipped** |
| **AI-Trader** | *not in prior harvest — new* | see below |

## Finding 1 — AI-Trader is the only delta, and it is a SKIP

`HKUDS/AI-Trader` (17.8k★, Python, HKU Data Science Lab) — "100% fully-automated
agent-native trading." It is an **autonomous execution system**: decision loop,
price fetch, order execution, monitoring.

**Verdict: SKIP for the stated goal.** It does not produce *better predictions*
— it is an execution wrapper. This stack is paper-first / NFA, signal-emit only
(execution is manual via TradingView paper accounts). Same wrong-shape verdict
as QuantDinger / Vibe-Trading. Nothing here lifts per-class PF/WR.

## Finding 2 — the real gap: the 2026-05-03 ship list was never shipped

The prior harvest's actionable items are **all still absent from the repo**
(verified 2026-05-17 via contents API):

- `tools/openbb*` — MISSING (P1: unified data, MCP-native, BOND/ETF/COMMODITY data quality)
- `.claude/skills/last30days-skill` — MISSING (P1: CRYPTO sentiment discovery)
- `alpha_engine/qlib_alpha*` — MISSING (P3: alpha-factor IC for EQUITY)

This is the **External-AI Input Audit lesson** (PR #1155, this session) repeating:
the bottleneck is repo-grounded *execution*, not another idea list. Harvesting
the same 10 repos a third time produces no lift.

## Recommendation

Of the 10, only **qlib's alpha-factor library** genuinely targets *prediction
quality* (validated factors → candidate scoring features). OpenBB improves
*data quality* (indirect lift). Everything else is LLM-orchestration or
execution infra — neither raises statistical edge.

**Do not start another orphan.** Pick exactly one and ship it end-to-end with a
production caller per the `CLAUDE.md` Wire-Up Rule:

1. **qlib alpha factors** — port 2-3 Alpha158/Alpha360 factors absent from our
   scoring, validate IC on the forward window, wire into `calculate_smart_score`.
   Target: EQUITY PF 1.41 → 1.5+. ~1 day incl. wiring + A/B.
2. **OpenBB-MCP** — unified data feed, opt-in sidecar in `dashboard_generator.py`
   ingestion behind `OPENBB_DATA_ENABLED=1`. Target: BOND/ETF/COMMODITY data
   completeness. ~half day.

Until one is committed-and-wired, no further trending-repo harvests — they
converge on the same list and none survive contact with the Wire-Up Rule.
