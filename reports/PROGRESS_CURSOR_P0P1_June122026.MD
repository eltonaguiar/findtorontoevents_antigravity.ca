# Progress Tracker — Audit Edge Hunt P0/P1 (Cursor)

**Agent:** Cursor (Composer)  
**Started:** 2026-06-12  
**Branch:** `feat/p1-progress-tracker` (worktree: `.worktrees/p1-progress`)  
**Base PR:** #570 (`feat/p0-next-steps-batch`)  
**North star:** Goal #1 — honest intrabar measurement on `/audit`, stop bleed, grow probation sleeves

---

## Session snapshot (2026-06-12)

| Metric | Status |
|--------|--------|
| Asset classes **PROVEN** (n≥100, Tier-2, intrabar) | **0 / 8** |
| **PROBATION** sleeve | `luxalgo_confluence × CRYPTO × SHORT` (n=38, WR 71.1%, PF 2.21) |
| luxalgo SHORT emitter | **Fixed in #570** (fallback NEAR/SOL/AVAX when scanner empty) |
| picks-now forward WR | **Refreshed in #570** (was 21.1% / n=19 stale → 31.9% / n=206 local) |
| Hidden edge on filter combos | **None** (pass-hunter on intrabar ledger) |

---

## PR status

| PR | Branch | State | Contents |
|----|--------|-------|----------|
| **#562** | `feat/audit-edge-hunt-session-docs` | OPEN | Session docs, pass-hunter, action plan, skill |
| **#565** | `feat/p0-m036b-long-block-luxalgo` | OPEN | Superseded by #570 |
| **#570** | `feat/p0-next-steps-batch` | OPEN | M-036b, luxalgo fallback, kill wiring, tournament n excl, picks-now refresh |
| **TBD** | `feat/p1-progress-tracker` | IN PROGRESS | P1-1 sym×dir intrabar FWD WR, P1-5 FOREX F1 gate, P1-6 stale banner, this tracker |

---

## Phase 0 — Stop bleeding

| ID | Action | Status | Evidence / notes |
|----|--------|--------|------------------|
| P0-1 | luxalgo SHORT emission | **DONE (#570)** | `june2026_research_candidates.py` fallback when scanner empty |
| P0-2 | Block CRYPTO sized LONG (M-036b) | **DONE (#570)** | `CRYPTO_BLOCKED_DIRECTIONS_SIZED`, quality_gates exempts forward_test_only |
| P0-3 | Hourly intrabar reresolve GHA | **DONE (main)** | `audit-dashboard.yml` runs `reresolve_intrabar_signal_outcomes.py` |
| P0-4 | Kill fear-greed CRYPTO LONG | **DONE (#570)** | `emitter_discipline.HARD_KILL_STRATEGIES` expanded |
| P0-5 | Refresh picks-now track record | **PARTIAL** | JSON refreshed in #570; need GHA `picks-now-live-pnl.yml` to stay fresh post-merge |

### P0 reproducers (last run)

```bash
# luxalgo SHORT fallback (after #570 merge)
python3 -c "from alpha_engine.june2026_research_candidates import _generate_luxalgo_short_v2; print(len(_generate_luxalgo_short_v2()))"

# M-036b tests
python3 -m pytest tests/test_crypto_gates_p0.py tests/test_emitter_discipline_p0b.py -q

# intrabar truth timestamp
python3 -c "import json; print(json.load(open('audit_dashboard/data/intrabar_truth_by_class.json')).get('generated_at'))"
```

---

## Phase 1 — Measurement honesty

| ID | Action | Status | Owner files | Done when |
|----|--------|--------|-------------|-----------|
| P1-1 | Star/Track **symbol×direction intrabar FWD WR** | **DONE (this PR)** | `tools/build_intrabar_sym_dir_stats.py`, `dashboard_generator.py`, `template.html`, GHA | Active picks show `sym_dir_fwd_wr` from `at_signal_outcomes.intrabar_*` when n≥3 |
| P1-2 | Tournament MISPRICED visibility | **PARTIAL (#570)** | `ai-tournament.html` | n excl column shipped; full MISPRICED row drill-down optional |
| P1-3 | pick_funnel Smart Picks DB refresh | **OPEN** | Hourly job + `pick_funnel_90d.json` | Nav matrix matches DB |
| P1-4 | COMMODITY gap-fade intrabar replay | **OPEN** | pass-hunter / replay harness | OHLC proxy PF confirmed or rejected |
| P1-5 | FOREX block **F1=CONTRARIAN** live | **DONE (M-038)** | `quality_gates.py` | Sized FOREX with F1=CONTRARIAN rejected at gate |
| P1-6 | Portfolio history stale banner | **DONE (banner)** | `portfolio_history.html` | Visible 🚨 banner until intrabar regen |
| P1-A | Verdict UI intrabar-only | **OPEN** | plan in `docs/plans/2026-06-12-P1A-intrabar-only-verdict-ui-plan.md` | — |

---

## Phase 2 — Institutional playbook (backlog)

| ID | Action | Status |
|----|--------|--------|
| P2-1 | Focus 2 classes (CRYPTO luxalgo SHORT + COMMODITY gap-fade) | OPEN |
| P2-2 | Kill 12/16 june2026 v2 emitters without intrabar support | OPEN |
| P2-3 | Monkey test + stress matrix before PROBATION→PROVEN | OPEN |
| P2-4 | Growth-stock screener → picks-now | OPEN |
| P2-5 | research_index → hypothesis registry wire-up | OPEN |

---

## This session deliverables (feat/p1-progress-tracker)

- [x] `reports/PROGRESS_CURSOR_P0P1_June122026.MD` (this file)
- [x] `tools/build_intrabar_sym_dir_stats.py` → `audit_dashboard/data/intrabar_sym_dir_fwd.json`
- [x] GHA step after `build_intrabar_truth_by_class.py`
- [x] `dashboard_generator.py` stamps `sym_dir_fwd_wr` / `sym_dir_fwd_n`
- [x] `template.html` Track column prefers intrabar sym×dir when n≥3
- [x] `quality_gates.py` M-038 FOREX F1=CONTRARIAN block
- [x] `tests/test_forex_f1_gate_p1.py` (5/5 pass)
- [x] `portfolio_history.html` stale surface banner
- [x] `updates/2026-06-12-p1-progress-tracker-batch.md`

---

## Verification checklist (before PR)

```bash
cd .worktrees/p1-progress
python3 -c "import py_compile; py_compile.compile('tools/build_intrabar_sym_dir_stats.py', doraise=True)"
python3 -c "import py_compile; py_compile.compile('audit_trail/dashboard_generator.py', doraise=True)"
python3 -m pytest tests/test_forex_f1_gate_p1.py tests/test_crypto_gates_p0.py -q
node tools/check_syntax.js audit_dashboard/template.html   # if available
node tools/check_syntax.js audit_dashboard/portfolio_history.html
```

**Do not run locally:** `dashboard_generator`, `money_ready_verdict.py`, `check_active_picks.py`, `smart_picks_engine.py`

---

## Changelog

| Date (UTC) | Event |
|------------|-------|
| 2026-06-12 19:50 | PR #570 opened (P0 batch) |
| 2026-06-12 ~20:00 | Created `feat/p1-progress-tracker` worktree; started P1-1/P1-5/P1-6 |
| 2026-06-12 ~20:xx | P1 batch: sym×dir intrabar stats, M-038 FOREX gate, portfolio stale banner |

---

## Related docs

| File | Purpose |
|------|---------|
| `reports/ACTION_PLAN_CURSOR_June122026_AUDIT_EDGE_HUNT.MD` | Canonical action plan |
| `reports/SESSION_COMPLETE_CURSOR_June122026_AUDIT_EDGE_HUNT.MD` | Full session wrap |
| `PLAN_INSIGHTS_CURSOR_June122026_638PM.MD` | Evidence-backed findings |
| `docs/todos/PM_ACTIONS_JUNE12_2026.md` | PM backlog tables |
