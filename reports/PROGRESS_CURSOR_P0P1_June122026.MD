# Progress Tracker — Audit Edge Hunt P0/P1 (Cursor)

**Agent:** Cursor (Composer)  
**Updated:** 2026-06-12 (batch 2)  
**Branch:** `feat/p1-next-batch-2026-06-12` (worktree: `.worktrees/p1-next-batch`)  
**PR:** TBD → main

---

## PR status (open)

| PR | Branch | Contents |
|----|--------|----------|
| **#570** | `feat/p0-next-steps-batch` | P0 M-036b, luxalgo fallback, kill wiring |
| **#572** | `feat/p1-progress-tracker` | P1-1 sym×dir intrabar, M-038 FOREX, portfolio banner |
| **TBD** | `feat/p1-next-batch-2026-06-12` | P0-5 tripwire, P1-3 hourly funnel, P1-A verdict sizing, P1-4 gap-fade replay |

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
| P1-2 | Tournament MISPRICED visibility | **PARTIAL (#570)** |
| P1-3 | pick_funnel hourly DB refresh | **DONE (this PR)** — `extract_funnel.py` + `build_nav_surface_matrix.py` in audit-dashboard hourly |
| P1-4 | COMMODITY gap-fade intrabar replay | **DONE (this PR)** — `tools/replay_commodity_gap_fade_intrabar.py` |
| P1-5 | FOREX F1=CONTRARIAN block | **DONE (#572 M-038)** |
| P1-6 | Portfolio history stale banner | **DONE (#572)** |
| P1-A | Verdict UI intrabar-only sizing | **DONE Step 1 (this PR)** — `money_ready_verdict.py` + template major-goal tiles |

---

## This batch deliverables

- [x] `alpha_engine/money_ready_verdict.py` — `sizing_source`, intrabar gates when n≥30
- [x] `audit_dashboard/template.html` — discovery vs sizing cohort labels
- [x] `.github/workflows/audit-dashboard.yml` — hourly pick_funnel + nav surface + freshness tripwires
- [x] `tools/replay_commodity_gap_fade_intrabar.py`
- [x] `tests/test_money_ready_intrabar_sizing_p1a.py`
- [x] `updates/2026-06-12-p1-next-batch.md`

---

## Verification

```bash
cd .worktrees/p1-next-batch
python3 -m pytest tests/test_money_ready_intrabar_sizing_p1a.py -q
python3 -c "import py_compile; py_compile.compile('alpha_engine/money_ready_verdict.py', doraise=True)"
python3 tools/replay_commodity_gap_fade_intrabar.py --stdout | head -30
node tools/check_syntax.js audit_dashboard/template.html
```

---

## Changelog

| Date (UTC) | Event |
|------------|-------|
| 2026-06-12 | PR #572 — sym×dir intrabar, M-038, portfolio banner |
| 2026-06-12 | PR batch 2 — P1-3/P1-A/P1-4/P0-5 tripwire |
