---
name: audit-pick-flow
description: Use when tracing how a pick on findtorontoevents.ca/audit got there — what source emitted it, which gates it passed or was rejected by, why it is or is not in Smart Picks / High Conviction / Money Ready, or why a class shows the win-rate it does. Also for "which DB tables matter", per-asset-class pick-funnel case studies, and onboarding someone to the audit pipeline.
---

# Audit Pick Flow

## Overview

Every pick on `/audit` travels a fixed path: **source emitter → JSON → `at_raw_picks` → gate stack → `at_consensus_picks` → outcome resolver → dashboard category**. This skill traces any single pick through that path, runs per-asset-class funnel case studies, and tells you which MySQL tables to care about.

Core principle: a pick's position on `/audit` is fully explained by *which gate decisions it received*. If you can list the gates, you can explain the pick.

## When to Use

- "Why is BTCUSDT not in Smart Picks?" / "Why did this pick get rejected?"
- "What is the FOREX pick funnel for the past week?"
- "Which `ejaguiar1_stocks` tables do I need to understand?"
- Onboarding someone to the `/audit` pipeline.
- Building a per-asset-class case study (opened + closed picks).

Not for: editing gate logic (that's `quality_gates.py` directly), or sports/events picks (different pipeline).

## The Pipeline (7 stages)

```
1 EMIT      *_scanner.py / *_strategies.py / copy_trader_intel / coinglass  -> per-source JSON
2 INGEST    collect_all_picks() merges JSON -> at_raw_picks (the core ledger)
3 ACTIVE    quality_gates.passes_active_gate()  -> dashboard-visible or at_filter_log reject
4 SMART     quality_gates.passes_smart_gate() (= active gate + smart floors) + calculate_smart_score()
5 HC        tools/dashboard_hc_rules.passes_high_conviction_pick() — Gates 1-9 (JS twin: hc_filter.js)
6 CONSENSUS multi-source agreement -> at_consensus_picks
7 OUTCOME   outcome_resolver.py / forward_validator.py -> status + pnl_pct
```

The three `/audit` surfaces are **nested filters on the same picks**, not separate lists:
`Money Ready ⊂ High Conviction ⊂ Smart Picks ⊂ Active`. A pick falls out at the first gate it fails.

See `references/pipeline-map.md` for every gate with file:line, env kill-switch, and order.

## Quick Reference — trace a pick

```bash
# full flow of one pick (live MySQL, read-only)
python .claude/skills/audit-pick-flow/scripts/trace_pick.py --symbol BTCUSDT
python .claude/skills/audit-pick-flow/scripts/trace_pick.py --pick-id 145879

# per-asset-class funnel for a date range (the case-study query)
python .claude/skills/audit-pick-flow/scripts/pick_flow_funnel.py --days 7
```

Credentials: env `AUDIT_DB_HOST` / `AUDIT_DB_USER` / `AUDIT_DB_PASS`, or pass `--pw`.
Host `mysql.50webs.com`, db `ejaguiar1_stocks`.

## Quick Reference — the gate stack

| # | Gate | Where | Rejects |
|---|------|-------|---------|
| Active | `passes_active_gate` | `quality_gates.py:5774` | safety STOP, magnitude-insane, blocked symbols/sources, kill-gate, quarantine, FOREX-LONG, low elite_score |
| Smart | `passes_smart_gate` | `quality_gates.py:7545` | active gate + per-class score/WR floors, `forward_validated` required, CRYPTO LONG-only |
| Score | `calculate_smart_score` | `quality_gates.py:8399` | 0-100 ranking (not a gate) |
| HC | `passes_high_conviction_pick` | `tools/dashboard_hc_rules.py:368` | Gates 1-9: score floors, trust-tier blacklist, per-class FWD-WR, regime, walk-forward FAILING, ≥3-signal consensus |
| Money Ready | `money_ready_verdict` | `alpha_engine/money_ready_verdict.py` | per-CLASS verdict: n≥50, WR≥0.55, PF≥1.5, DSR≥0.95, PBO≤0.55 |

Every gate is env-var kill-switchable and fail-open. Gate config: `config/hc_gate_params.json`, `config/hf_conviction_tiers.json`.

## Which DB tables to care about

Full table guide: `references/db-tables.md`. The short list — only **8 tables in `ejaguiar1_stocks`** are on the pick-flow path; the other 315 are sports/mutual-fund/experiment noise.

| Table | Role |
|-------|------|
| `at_raw_picks` | core ledger — every raw pick, lifecycle, close |
| `at_filter_log` | every gate REJECTION (no PASS rows) |
| `at_consensus_picks` | picks that survived multi-source agreement |
| `at_signal_outcomes` | resolved entry/exit/pnl |
| `at_aggregation_runs` | one row per cycle |
| `trading_picks` | dashboard-facing store with score fields |
| `at_pick_audit_trail` | **new** — full per-gate trace (opt-in writer) |
| `at_pick_flow_daily` | **new** — nightly per-class funnel rollup |

`ejaguiar1_backtests` (6 tables) is a research archive — **not** on the live pick path.

## The audit-trail acceleration tables

`audit_integration/05_pick_audit_trail_schema.sql` adds two tables so a pick-flow audit
is one indexed query instead of a multi-table JSON join:

- **`at_pick_flow_daily`** — populated nightly by MySQL event `ev_pick_flow_daily_rollup`
  off `at_raw_picks`+`at_filter_log`. Works today, zero Python. `pick_flow_funnel.py` reads it.
- **`at_pick_audit_trail`** — full ordered PASS/REJECT trace per pick. Needs a Python writer.

### Wiring Plan (for `at_pick_audit_trail`)
Target caller: `audit_trail/quality_gates.py` — wrap each gate decision inside
`passes_active_gate` / `passes_smart_gate` with an opt-in `_emit_trace(pick, gate, decision)`
helper, env-gated by `PICK_AUDIT_TRAIL_ENABLED` (default OFF, sidecar — per the repo
Wire-Up Rule). Until that writer ships, `trace_pick.py` falls back to `at_filter_log`
(reject rows only). Expected wire-up: follow-up PR after this skill lands.

## UI element → pick-quality impact (the fast path)

Every button / tab / filter on `/audit` is a *filter over the same pick set*. To find
what any UI element does to pick quality:

1. **Identify the element** — `audit_dashboard/audit_frontend_manifest.json` is the
   codified list of all 47 buttons, 17 tabs, 31 filters, 10 ?Guide concepts (each with
   element id, handler, WIRED/ORPHANED status). Auto-refreshed daily by
   `tools/audit_frontend_manifest.py` (`.github/workflows/audit-frontend-manifest.yml`).
2. **Measure its pick-quality impact** — `tools/edge_finder.py` applies the element's
   filter and reports per-asset-class WR / PF / avg-pnl vs the unfiltered baseline:
   `python tools/edge_finder.py --surface smart_picks` (or `--filter "elite_score>=60"`).
   `--search` finds the field-threshold combo that maximizes PF.
3. **Trace one pick through it** — `scripts/trace_pick.py --symbol X` shows which gates
   that pick passed/failed, i.e. which surface it qualifies for.
4. **Full per-surface trace** — once the `at_pick_surface_eval` writer is wired, every
   pick carries `in_active / in_smart_picks / in_high_conviction / in_money_ready` flags
   + the frozen gate-input snapshot, so HC-vs-Smart-vs-Money-Ready divergence is one query.

Known result (2026-05-18): Smart Picks genuinely lifts CRYPTO/EQUITY into profit on its
filtered subset; the High Conviction button is not DB-verifiable (trust data missing);
the Money Ready *button* is orphaned (dead). See `reports/` for the per-button audit.

## Where /audit lives on GitHub + how it deploys

- **Repo:** `github.com/eltonaguiar/findtorontoevents_antigravity.ca`.
- **Source of `/audit`:** `audit_dashboard/` — edit `template.html` (NEVER `index.html`,
  which is generated). Filter JS: `hc_filter.js`, `money_ready_filter.js`.
- **Build:** `audit_trail/dashboard_generator.py` turns DB + JSON → `index.html` +
  `dashboard_data.json`. Gates: `audit_trail/quality_gates.py`.
- **Deploy:** `.github/workflows/audit-dashboard.yml` — hourly cron (`:10`),
  `generate-and-deploy` job runs the generator, commits the data, then **FTP-deploys to
  3 sites** (findtorontoevents.ca / tdotevent.ca / torontoevent.net). Not GitHub Pages.
- **An AI agent reviewing `/audit` starts at:** `audit_dashboard/template.html` (UI) +
  `audit_dashboard/audit_frontend_manifest.json` (element index) → `quality_gates.py`
  (gate logic) → `dashboard_generator.py` (build) → `audit-dashboard.yml` (deploy).

## Common Mistakes

- **Citing a JSON aggregate as "what the page shows"** — `/audit` tiles are live-computed in `template.html` JS; `by_asset_class` in `dashboard_data.json` is raw/pre-noise-filter. Use `asset_class_health` or `pf_registry.json` for verdict-grade numbers.
- **Trusting `pnl_pct` blindly** — non-crypto picks are often closed with `pnl_pct=0.0` placeholder (resolver gap); `closed_at` is frequently NULL even for terminal-status rows. Confirm with `trace_pick.py` before concluding.
- **Assuming Money Ready is a pick list** — it is a per-asset-CLASS statistical verdict, not per-pick. The `/audit` "💰 Money Ready" *button* is currently orphaned (no render path applies its filter); the Money Ready *tab* works.
- **Running dashboard generators locally** — they overwrite live HTML. `py_compile` only.

## Real-World Impact

Past-week (2026-05-11..18) live funnel: CRYPTO emitted ~8.7k picks/wk at ~35% WR / PF 0.17 on closed; non-crypto classes emit 10-540/wk but resolve to `pnl_pct=0` placeholders. Staleness (5,396) and no-consensus (1,600+) are the dominant rejection reasons. Full numbers: `reports/audit_pick_flow_case_study_2026_05_18.md`.
