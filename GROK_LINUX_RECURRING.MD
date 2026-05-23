# Grok Linux Recurring Research Loop — Operator Guide

This document explains how the autonomous recurring research system runs on this Linux environment using Grok (the xAI CLI agent).

## Overview

There are currently two long-running scheduled research/health loops:

| Job ID            | Interval | Purpose                              | Status     |
|-------------------|----------|--------------------------------------|------------|
| `019e490182df`    | 30 minutes | Quant strategy research (6/8-gate loop) | Active    |
| `019e4933cbaa`    | 6 hours   | Site staleness + GitHub Actions health | Active    |

Both loops are managed via the Grok scheduler and run fully autonomously until manually stopped with `scheduler_delete`.

---

## 1. Main Research Loop (30-minute)

### What It Does
Every 30 minutes the agent:
- Creates a fresh `todo_write` for the firing (Firing N)
- Spawns 2–3 parallel subagents for deep work across asset classes (CRYPTO, EQUITY, H-017/liquidation, etc.)
- Runs main-thread actions (e.g., daily H-017 shadow collection)
- Updates all living reports
- Ends with a clear synthesis + next actions

### Where All Output Is Stored

#### Per-Firing Artifacts (most important)
- `reports/continual_research/6gate_validation/CYCLE_2026-05-21_FIRING{N}_SUMMARY.md`
  - The authoritative log for that specific 30-minute firing.
  - Contains kickoff, subagent results, synthesis, and citations.

#### Living / Cumulative Reports (updated every firing)
- `reports/CONTINUAL_STRATEGY_RESEARCH_BASELINE.md`
  - Master running document of all progress across all firings.
- `updates/2026-05-21-continual-6gate-asset-class-research/index.html`
  - The public, transparent "Research Log" (✅ What I Just Finished / 🔄 What I’m Working On / 📅 What I Plan to Work On Next).
- `updates/index.html`
  - Teaser card on the main updates page (updated on 10-run milestones).

#### Strategy Organization
- `reports/continual_research/6gate_validation/A_passed/` — Strategies that passed all 6/8 gates with supporting stats.
- `reports/continual_research/6gate_validation/B_failed/` — Strategies that failed one or more gates (with which gate and why).
- `reports/continual_research/6gate_validation/pending_fresh_backtest/` — Deep-dive sub-reports and work-in-progress.

#### Milestone Documentation (every 10 firings)
- Dedicated `.MD` file, e.g.:
  - `reports/continual_research/10_RUN_MILESTONE_FIRING_1-13_2026-05-21.md`
  - `reports/continual_research/10_RUN_MILESTONE_FIRING_14-20_2026-05-21.md`
- Corresponding green-bordered card is added to `updates/index.html`.

#### H-017 Liquidation Shadow Collector
- Daily snapshots: `reports/h017_shadow_collect_20260521.json` (overwritten daily, contains `run_ts`)
- Full history lives in the per-firing CYCLE summaries and the H-017 sub-reports.

---

## 2. How to Monitor the Loop Live

### Useful Commands

```bash
# See all active scheduled jobs
scheduler_list

# Watch the latest firing in real time
tail -f reports/continual_research/6gate_validation/CYCLE_2026-05-21_FIRING*.md | tail -100

# Check the master baseline
tail -30 reports/CONTINUAL_STRATEGY_RESEARCH_BASELINE.md

# Check current H-017 shadow state
cat reports/h017_shadow_collect_20260521.json

# View the public research log (best for humans)
# https://findtorontoevents.ca/updates/2026-05-21-continual-6gate-asset-class-research/
```

### Current Firing Number
Look at the highest `FIRING{N}` in the `CYCLE_*` files or just ask Grok:
> "What firing number are we on right now?"

---

## 3. The 10-Run Milestone Rule

User standing rule (enforced since Firing 13):

> For every 10 runs, create a dedicated milestone `.MD` document summarizing the batch and update the teaser card on `updates/index.html`.

Examples:
- F1–F13 → `10_RUN_MILESTONE_FIRING_1-13_2026-05-21.md`
- F14–F20 → `10_RUN_MILESTONE_FIRING_14-20_2026-05-21.md`

Next milestone target: **F30**.

---

## 4. Parallel 6-Hour Health Loop (019e4933cbaa)

Runs every 6 hours and performs:
- Staleness checks on `findtorontoevents.ca` and `findtorontoevents.ca/audit`
- GitHub Actions health audit (failed jobs without subsequent success, chronically cancelled jobs, etc.)
- Writes to `docs/GHA_SWARM_CURATED_REVIEW.md` when run via the swarm tool.

This loop is independent of the 30-minute research loop.

---

## 5. How the Loops Are Started

Both loops were created with the `scheduler_create` tool (with `recurring: true` and `fireImmediately: true`).

To stop a loop:
```bash
scheduler_delete --id 019e490182df     # 30-minute research
scheduler_delete --id 019e4933cbaa     # 6-hour health
```

To restart, use `scheduler_create` again with the same prompt payload.

---

## 6. Best Practices When Interacting

- **Let it run autonomously** most of the time. The loop is designed to be self-documenting.
- When you want to steer it, give high-level direction in the chat (e.g., "for the next few firings, prioritize the H-017 baby emitter and harness expansion").
- The agent will incorporate your guidance into the next `todo_write` and subagent planning.
- All work is **research-only** (no live trading) unless explicitly approved.

---

## 7. Quick Reference — Most Important Paths

| Purpose                        | Path |
|--------------------------------|------|
| Latest firing details          | `reports/continual_research/6gate_validation/CYCLE_2026-05-21_FIRING*.md` (highest N) |
| Master progress log            | `reports/CONTINUAL_STRATEGY_RESEARCH_BASELINE.md` |
| Public research log            | `updates/2026-05-21-continual-6gate-asset-class-research/index.html` |
| 10-run milestone documents     | `reports/continual_research/10_RUN_MILESTONE_FIRING_*` |
| H-017 daily shadow state       | `reports/h017_shadow_collect_20260521.json` |
| A/B strategy organization      | `reports/continual_research/6gate_validation/{A_passed,B_failed}/` |
| Full GHA health reports        | `docs/GHA_SWARM_CURATED_REVIEW.md` |

---

**Last updated:** 2026-05-21 (after F23 close)  
Maintained by the autonomous research loop itself. Update this file manually only when the loop architecture changes.