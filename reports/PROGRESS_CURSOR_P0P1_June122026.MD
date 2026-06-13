# Progress Tracker — Audit Edge Hunt P0/P1 (Cursor)

**Agent:** Cursor (Composer)  
**Updated:** 2026-06-12 (batch 3 — P1-A UI steps 2–4)  
**Branch:** `feat/p1a-ui-steps-2026-06-12` (worktree: `.worktrees/p1a-ui-steps`)  
**PR:** TBD → main (stacked on #578)

---

## PR status (open)

| PR | Branch | Contents |
|----|--------|----------|
| **#570** | `feat/p0-next-steps-batch` | P0 M-036b, luxalgo fallback, kill wiring, tournament n-excl (partial) |
| **#572** | `feat/p1-progress-tracker` | P1-1 sym×dir intrabar, M-038 FOREX, portfolio banner |
| **#578** | `feat/p1-next-batch-2026-06-12` | P0-5 tripwire, P1-3 hourly funnel, P1-A verdict sizing Step 1, P1-4 gap-fade |
| **TBD** | `feat/p1a-ui-steps-2026-06-12` | P1-A Steps 2–4 UI, P1-2 tournament n-excl column |

---

## Phase 0

| ID | Action | Status |
|----|--------|--------|
| P0-1..P0-4 | Stop-bleed batch | **DONE** (main + #570) |
| P0-5 | picks-now track record freshness | **DONE (this PR)** — freshness tripwire on `picks_now_track_record.json` (26h); hourly rebuild already in `picks-now-live-pnl.yml` |

---

## Phase 1

| ID | Action | Status |
|----|--------|--------|
| P1-1 | sym×dir intrabar FWD WR | **DONE (#572)** |
| P1-2 | Tournament MISPRICED visibility | **DONE (batch 3)** — `n excl` column in ai-tournament.html |
| P1-3 | pick_funnel hourly DB refresh | **DONE (this PR)** — `extract_funnel.py` + `build_nav_surface_matrix.py` in audit-dashboard hourly |
| P1-4 | COMMODITY gap-fade intrabar replay | **DONE (this PR)** — `tools/replay_commodity_gap_fade_intrabar.py` |
| P1-5 | FOREX F1=CONTRARIAN block | **DONE (#572 M-038)** |
| P1-6 | Portfolio history stale banner | **DONE (#572)** |
| P1-A | Verdict UI intrabar-only sizing | **DONE Steps 1–4** — #578 Step 1 verdict; batch 3 health cards, filter, pf_registry discovery tier |

---

## Batch 3 deliverables (P1-A UI)

- [x] `audit_trail/dashboard_generator.py` — `enrich_health_with_intrabar_sizing()`
- [x] `audit_dashboard/template.html` — display_* intrabar vs discovery tags
- [x] `audit_dashboard/money_ready_filter.js` — intrabar class gate
- [x] `audit_dashboard/pick_funnel.html` — glossary intrabar sizing note
- [x] `tools/build_pf_registry.py` — `display_tier: discovery`
- [x] `audit_dashboard/ai-tournament.html` — n excl column
- [x] `updates/2026-06-12-p1a-ui-steps.md`

---

## Verification

```bash
cd .worktrees/p1a-ui-steps
python3 -m pytest tests/test_money_ready_intrabar_sizing_p1a.py -q
python3 -c "import py_compile; py_compile.compile('audit_trail/dashboard_generator.py', doraise=True)"
node tools/check_syntax.js audit_dashboard/template.html audit_dashboard/ai-tournament.html audit_dashboard/pick_funnel.html
```

---

## Changelog

| Date (UTC) | Event |
|------------|-------|
| 2026-06-12 | PR #572 — sym×dir intrabar, M-038, portfolio banner |
| 2026-06-12 | PR batch 2 — P1-3/P1-A Step 1/P1-4/P0-5 tripwire (#578) |
| 2026-06-12 | PR batch 3 — P1-A Steps 2–4 UI + tournament n-excl |
