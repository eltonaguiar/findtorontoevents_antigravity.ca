# M-033 Clarification Request — 2026-05-17

## Context

M-033 spec from MASTER_ACTION_PLAN:
"Hard-disable `claude_gainer_st` aggregator stale refresh + `last_signal_at` reconcile
— Refresh `systems` payload against live blacklist"

## Investigation Findings

### Two different things named claude_gainer_st

**1. BLOCKED STRATEGY (quality_gates.py:1234):**
```
"claude_gainer_st"  # 778/790 PROVEN picks, WR=26.5%, -355% total PnL
```
This is in BLOCKED_STRATEGIES and rejected in passes_active_gate via pick["strategy"].

**2. SOURCE SYSTEM (dashboard_generator.py:3779):**
```
"claude_gainer_st" reads from "claude_gainer_ml/tracker/short_term_active.json"
```
The SYSTEM has WR=69.6%, PF=2.62, resolved=148. Sub-strategies used: st_fear_greed_contrarian
(WR=73.4%), st_rsi_vol_bounce (WR=53.3%).

### Current state
- active_picks.json: 0 picks from claude_gainer* source systems
- short_term_active.json: 4 picks (ATOM, LTC, XRP, ADA) from sub-strategies (st_*)
- dashboard shows: claude_gainer_st system with 2 active picks, is_stale=False, last_signal_at=2026-05-17

### The gap
The picks from short_term_active.json have strategy="st_fear_greed_contrarian" (NOT
"claude_gainer_st"), so they pass BLOCKED_STRATEGIES gate in passes_active_gate.
But they're not reaching active_picks.json (0 shown there).

## Questions for Swarm

1. **What exactly should M-033 fix?**
   - (A) Mark claude_gainer_st SYSTEM as stale/blocked in dashboard when its source strategy is blocked?
   - (B) Disable short_term_scanner.py from refreshing short_term_active.json?
   - (C) Add source_system to BLOCKED check (not just pick["strategy"])?
   - (D) Something else — e.g. reconcile last_signal_at to show it's actually feeding no gate-passing picks?

2. **Should we touch the sub-strategy performance at all?**
   The st_fear_greed_contrarian sub-strategy (WR=73.4%, n=128) appears to be a GOOD edge.
   If M-033 disables the aggregator, we lose visibility into this edge.
   Should this sub-strategy be promoted to a standalone system instead?

3. **Priority vs. risk:**
   Given claude_gainer_st system currently shows no gate-passing active picks (0 in active_picks.json),
   is M-033 actively harmful today, or purely cosmetic (a stale last_signal_at showing the system
   looks active when it shouldn't)?

## Requested Output
Per-option recommendation with reasoning. Which fix is correct and lowest-risk?
