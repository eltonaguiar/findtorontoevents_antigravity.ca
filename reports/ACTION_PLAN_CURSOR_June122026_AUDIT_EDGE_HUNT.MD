# Action Plan — Audit Edge Hunt (Cursor)

**Agent:** Cursor (Composer)  
**Date:** 2026-06-12 (EST)  
**Status:** Investigation complete · **Implementation not started**  
**PR:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/562  
**Branch:** `feat/audit-edge-hunt-session-docs` (worktree: `.worktrees/audit-edge-hunt-pr`)

---

## Executive summary

| Metric | Value |
|--------|-------|
| Asset classes **PROVEN** (n≥100, Tier-2, intrabar) | **0 / 8** |
| **PROBATION** sleeve | 1 — `luxalgo_confluence × CRYPTO × SHORT` (n=38, WR 71.1%, PF 2.21) |
| **Blocker** | Emitter ships **0** luxalgo SHORT picks; forward n not growing |
| `picks-now.html` forward WR | **21.1%** (stale 2026-06-09, n=19) |
| Hidden edge on `/audit` filters | **None found** |

**North star:** Ship P0 stop-bleed items this week, then P1 measurement honesty, then P2 velocity (2 focus classes only).

---

## Related documentation

| File | Purpose |
|------|---------|
| **This file** | Canonical **action plan** — what to do next |
| `reports/SESSION_COMPLETE_CURSOR_June122026_AUDIT_EDGE_HUNT.MD` | Full session wrap (tasks, findings, deep-dives) |
| `PLAN_INSIGHTS_CURSOR_June122026_638PM.MD` | Audit findings + evidence |
| `docs/todos/PM_ACTIONS_JUNE12_2026.md` | PM backlog (same priorities, table format) |
| `CURSOR_JUNE112026.MD` | Hostile master-loop review |
| `.claude/skills/thingstocheck-june2026/SKILL.md` | Repeatable investigation workflow |

---

## Phase 0 — Stop bleeding (this week)

**Goal:** Halt false-positive emission, restart honest forward measurement, fix the one probation sleeve.

| ID | Action | Owner files | Acceptance criteria | Plan doc |
|----|--------|-------------|---------------------|----------|
| **P0-1** | Fix **luxalgo SHORT emission** (scanner returns 0) | `alpha_engine/june2026_research_candidates.py`, `priority_picks_emitter.py` | `_generate_luxalgo_short_v2()` returns ≥1 pick; forward stamp accrues n | — |
| **P0-2** | **Block CRYPTO LONG** at emitter (M-036 extension) | `alpha_engine/config.py`, emitter discipline | Zero CRYPTO LONG in emitter dry-run; intrabar LONG not sized | `docs/plans/2026-06-12-P0C-m036-long-gate-plan.md` |
| **P0-3** | **Hourly intrabar reresolve** in GHA | `.github/workflows/` + `tools/reresolve_intrabar_signal_outcomes.py` | New `at_signal_outcomes` resolutions after 2026-06-10 | `docs/plans/2026-06-12-P0A-intrabar-hourly-reresolve-plan.md` |
| **P0-4** | Kill **fear-greed CRYPTO LONG** from daily batch | `st_fear_greed_contrarian_winner` source | No fear-greed CRYPTO LONG in daily 44-pick batch | — |
| **P0-5** | **Refresh picks-now** track record | `tools/picks_now_professional.py`, `resolve_picks_now.py`, `picks_now_track_record.json` | Panel updates daily; n>19; WR reflects intrabar resolver | — |

### P0 execution order

```
P0-1 luxalgo SHORT  →  P0-2 block CRYPTO LONG  →  P0-3 hourly reresolve
       ↓
P0-4 kill fear-greed LONG  →  P0-5 refresh picks-now
```

### P0 reproducers

```bash
# P0-1 luxalgo SHORT must emit
python3 -c "from alpha_engine.june2026_research_candidates import _generate_luxalgo_short_v2; print(len(_generate_luxalgo_short_v2()))"

# P0-2 emitter dry-run (no CRYPTO LONG)
python3 alpha_engine/priority_picks_emitter.py --dry-run 2>/dev/null | rg -i 'CRYPTO.*LONG' && echo FAIL || echo OK

# P0-3 intrabar truth freshness
python3 -c "import json; d=json.load(open('audit_dashboard/data/intrabar_truth_by_class.json')); print(d.get('generated_at'))"

# P0-5 picks-now track record
python3 -c "import json; t=json.load(open('audit_dashboard/data/picks_now_track_record.json'))['totals']; print(t)"
```

---

## Phase 1 — Measurement honesty (2 weeks)

**Goal:** UI and pipelines show symbol×direction forward truth, not strategy/registry inflation.

| ID | Action | Owner | Done when |
|----|--------|-------|-----------|
| **P1-1** | Star tab **symbol×direction FWD WR** | `audit_trail/dashboard_generator.py` | Active picks show per-pick forward WR from `at_signal_outcomes` |
| **P1-2** | Tournament **MISPRICED_ENTRY** visible | Leaderboard builder | gpt4_1 row shows excluded count beside headline WR |
| **P1-3** | **pick_funnel** Smart Picks DB refresh | Hourly job + `pick_funnel_90d.json` | Nav matrix matches DB ground truth table |
| **P1-4** | **COMMODITY gap-fade** intrabar replay | `tools/replay_harness.py` or pass-hunter | OHLC proxy PF 1.92 confirmed or rejected on intrabar |
| **P1-5** | FOREX block **F1=CONTRARIAN** live | Emitter + stamps | Contrarian FOREX not emitted |
| **P1-6** | **Portfolio history** regen or deprecate | `portfolio_history.html` generator | Stale banner or fresh intrabar-linked books |

| Plan | File |
|------|------|
| P1-A verdict UI | `docs/plans/2026-06-12-P1A-intrabar-only-verdict-ui-plan.md` |
| P1-B auto-kill tribunal | `docs/plans/2026-06-12-P1B-auto-kill-tribunal-plan.md` |

---

## Phase 2 — Institutional playbook (4 weeks)

**Goal:** Velocity over breadth — 2 focus classes, kill bad emitters, external replication before size.

| ID | Action | Reference |
|----|--------|-----------|
| **P2-1** | **2 focus classes** — CRYPTO luxalgo SHORT + COMMODITY gap-fade confirm | Master loop §2 |
| **P2-2** | Kill **12/16 june2026 v2 emitters** without intrabar support | `generate_forward_observation_picks()` audit |
| **P2-3** | **Monkey test + stress matrix** before PROBATION→PROVEN | Master loop Addendum B |
| **P2-4** | **Growth-stock screener** → picks-now | [starboi-63/growth-stock-screener](https://github.com/starboi-63/growth-stock-screener) |
| **P2-5** | **research_index → hypothesis registry** wire-up | Stop orphan reports |

| Plan | File |
|------|------|
| P0-B unified kill list | `docs/plans/2026-06-12-P0B-unified-kill-list-plan.md` |

---

## Deep-dive queue (spawn `reports/deep_dive_*`)

| Priority | Topic | Why |
|----------|-------|-----|
| **Now** | luxalgo SHORT emission failure | Only probation sleeve; 0 forward picks |
| **Now** | picks-now 21.1% WR + STRONG_BUY SL geometry | Public “best picks now” surface is misleading |
| **P1** | Tournament MISPRICED_ENTRY / reverse-split / sign-flip | User-called data-quality risks |
| **P1** | COMMODITY gap-fade external replication | DBMF/KMLM before size |
| **P2** | Portfolio history resurrection | Heavy EW losses; freeze vs regen |
| **P2** | ai_leaderboard throughput (43 engines, min_n=20) | Discovery surface underpowered |

---

## Current proven / probation state

| Class | Unit | Tier | n | WR | PF | Next action |
|-------|------|------|---|-----|-----|-------------|
| CRYPTO | luxalgo_confluence SHORT | **PROBATION** | 38 | 71.1% | 2.21 | **P0-1** emit + accrue to n=100 |
| COMMODITY | gold_overnight_gap_fade | **PROXY** | 108 (BT) | — | 1.92 | **P1-4** intrabar replay |
| All others | — | **NONE** | — | — | — | Do not size |

---

## Implementation checklist (for next PR)

- [ ] Create worktree from `main` after PR #562 merges
- [ ] Implement **P0-1** through **P0-5** in code (separate PR from docs)
- [ ] Run pass-hunter after P0-3: `python3 tools/strategy_pass_hunter.py`
- [ ] Regenerate verdict: `python3 alpha_engine/money_ready_verdict.py --json`
- [ ] Update this file §Status to **P0 in progress** / **P0 complete**

---

## Invoke investigation again

```bash
# Slash command (after merge)
/thingstocheck-june2026

# Or read skill directly
cat .claude/skills/thingstocheck-june2026/SKILL.md
```

Deliverable convention: new `PLAN_INSIGHTS_*` or update this **ACTION_PLAN** with date suffix if scope changes.
