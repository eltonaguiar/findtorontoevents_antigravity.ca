---
name: tv-portfolio-review
description: Review a TradingView paper portfolio — classify each holding's origin (findtorontoevents.ca/audit vs /audit/hyrotrader vs agent-swarm consensus), flag close candidates (lock profit / cut loss), and extract lessons-learned ("is /audit working? are the picks statistical-edge? are swarm picks working?"). Use after /tv-portfolio-extract. Aliases - tv-review, portfolio-review, tv-portfolio-audit, lessons-learned.
---

# tv-portfolio-review — origin attribution + lessons-learned per portfolio

> **MCP server:** [tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp) — the `mcp__tradingview-desktop__*` tool family.

Takes a `/tv-portfolio-extract` dump and answers, per portfolio: where did
each pick come from, which holdings should be closed, and is the pick engine
actually working. Read-only analysis — no trades; to close, hand off to
`/tv-close-positions`.

## Inputs

- The extract dump: `reports/tv_portfolio_<ACCOUNT>_<date>/dump.json` (or the
  per-account `reports/tv_portfolio_history_*/active_*.json` snapshots).
- Pick-source ledgers (the attribution truth set):
  - **B — /audit:** `audit_dashboard/data/dashboard_data.json` (`picks.active`,
    `picks.recent_closed`), `alpha_engine/data/active_picks.json`,
    `alpha_engine/data/smart_picks.json`. Source systems: `kimi_riseoftheclaw`,
    `regime_terminal`, `multi_asset_copytrader`, `combined_confidence_strategy`,
    `cta_replicator`, `genome`, etc.
  - **C — /audit/hyrotrader:** `audit_dashboard/data/hyrotrader_picks.json`,
    `hyrotrader_enhanced_picks.json`, `hyrotrader_journal.json`,
    `hyrotrader_short_term_entries.json`. Strategies: CCI Divergence,
    `hyrotrader_adx_vol_breakout`, CMF Cross, BB Squeeze, Multi-EMA — each with
    an ATR plan.
  - **A — swarm consensus:** `audit_dashboard/data/swarm_picks.json`,
    `consensus_tier_picks.json`, `copy_trader_intel/data/consensus_*`,
    `meta_strategy/swarm_consensus.py` output, `consensus_pick_builder.py`.

## Step 1 — origin attribution (process of elimination)

For EACH holding (symbol, direction, entry, account), classify the source:

1. **Portfolio-name heuristic.** Account name contains `hyrotrader` →
   strong prior for **C** (the holding should have come from the hyrotrader
   page). Name like `theswarm` → prior for **A**. `TRUSTOURSCORE` /
   `HIGHFWWRABV55_*` / `VERIFIEDALPHA` → audit-gated **B**.
2. **Exact match.** Search each ledger for the same symbol + direction with a
   close entry price / recent timestamp:
   - in a hyrotrader_*.json with an ATR plan → **C**.
   - in dashboard_data / active_picks with a `source_system` → **B** (record
     the source_system).
   - in swarm_picks / consensus_* → **A**.
3. **Elimination.** No exact match anywhere → fall back to the portfolio-name
   heuristic and label it `B?` / `C?` / `manual?`. Note it as low-confidence.
4. **Combination (D).** Most holdings are a mix — a hyrotrader strategy (C)
   running on an audit-scored symbol (B) that first surfaced in a swarm run
   (A). When ≥2 ledgers match, label **D** and list the contributors.

Output an attribution table: `account | symbol | dir | entry | origin (A/B/C/D)
| matched ledger + source_system | confidence`.

## Step 2 — close candidates

For each open holding compute `unrealized_pnl_pct` (from the dump). Flag:

- **Lock profit:** unrealized ≥ +60% of the way to TP, OR a standout winner
  (e.g. > +5-10%) where momentum has stalled.
- **Cut loss:** unrealized worse than −(SL distance × 0.8), OR thesis broken,
  OR the position is unprotected (no TP/SL — that is an immediate fix via
  `/tv-protect-position`, not a close).
- **Hold:** inside the TP/SL band, thesis intact.

Output: `symbol | unrealized% | TP/SL distance | verdict (LOCK / CUT / HOLD) |
reason`.

## Step 3 — lessons learned ("is the system working?")

Aggregate, per origin and per portfolio, using the dump's closed trades +
`dashboard_data.json::picks.recent_closed`:

- **Is /audit (B) working?** WR / PF / net PnL of B-origin closed picks.
  Compare to the charter Tier-2 floor (PF>1.5 / WR>50). Are they
  statistical-edge picks (n ≥ ~20, WR clearly above coin-flip after costs) or
  noise?
- **Is /audit/hyrotrader (C) working?** Same, for C-origin. The hyrotrader
  ADX/CCI/CMF strategies — do their live closes match their backtested
  confidence (82-90%)?
- **Are swarm picks (A) working?** WR/PF of A-origin. Is consensus adding
  edge, or are the consensus JSONs stale/empty (a pipeline-health flag)?
- **Per-portfolio verdict.** Which books are net-positive, which are bleeding,
  and does the bleed trace to one origin (e.g. C crypto bleeding while B
  equity wins)?

State each verdict with the `(origin | n | timeframe)` label and cite the
ledger path. Do not call an edge "working" on n < 20 clean closed trades.

## Step 4 — output

Write `reports/tv_portfolio_review_<UTCDATE>.md`:
1. Per-portfolio: attribution table + close-candidate table.
2. Cross-portfolio lessons: B / C / A working? statistical edge? — with
   numbers.
3. Ranked actions: protect any unprotected position first, then LOCK/CUT the
   flagged holdings, then note pipeline issues (stale consensus, mis-sourced
   picks).

## Hard rules

- A holding in a `hyrotrader`-named book that does NOT trace to a hyrotrader
  ledger is a **mis-sourced pick** — flag it explicitly; the book's name
  promises C-origin.
- Never declare "the system works" / "swarm works" on a thin sample — label
  `n` always.
- This skill reads + reports. Closing positions is `/tv-close-positions`;
  fixing unprotected ones is `/tv-protect-position`.

## Companion skills

- `/tv-portfolio-extract` — produce the dump this skill consumes
- `/tv-close-positions` · `/tv-protect-position` · `/money-maker-ready`
