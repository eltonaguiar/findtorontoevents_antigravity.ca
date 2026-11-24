# COMS Handoff — audit3 financial-prediction review (2026-11-19)

Handoff from the `code` agent that completed the P0/P1 correctness pass. Read
this before touching the code. Companion docs (detailed findings, POC evidence)
live in the review repo `antigravity_review_Nov192026`:

- `05_KILO_REVIEW/P0_IMPLEMENTATION_STATUS.md`
- `05_KILO_REVIEW/P0_P1_RESEARCH_POC.md`
- `05_KILO_REVIEW/AUDIT3_NEXTGEN_ENHANCEMENTS.md`
- `NEXT_STEPS.md` (P0/P1/P2 ranked plan, with a status pointer at the top)

---

## 1. Where the work lives

**Source repo (canonical, where all changes are):**
`/home/eaguiar2015/findtorontoevents_antigravity.ca`

The source repo is on a **detached HEAD at `22c6cb4ced1`** (main tip, PR #909
merged). All changes below are **UNCOMMITTED** in the working tree.

**Changed files (8):**

| File | Change |
|---|---|
| `alpha_engine/audit3_tribunal.py` | P0-4 (G8 selection-alpha gate), P0-5 (DSR n_trials=global), P1-5 (G9 2×-cost stress gate) |
| `alpha_engine/audit3_edge_hunt.py` | P1-3 (`required_n_mde`, `power_analysis`, `"power_analysis"` report key) |
| `alpha_engine/forward_observations_ingest.py` | P1-4 (add `H-BABY-EQUITY-VT-PATTERN-SWEEP-001` condition + strategy/direction matching) |
| `alpha_engine/forward_validator.py` | P0-2 (retired-strategy blocklist defense-in-depth in `save_active_picks`) |
| `copy_trader_intel/multi_asset_copytrader_scraper.py` | P0-2 (blocklist filter in `save_results`) |
| `tests/test_audit3_expectancy_gates.py` | Updated two assertions (P0-5 provenance note; P1-5 stress-gate demotion) |
| `tests/test_forward_observations_ingest.py` | P1-4 regression test |
| `.github/workflows/audit3-denylist-watchdog.yml` | **NEW** P1-1 (independent denylist watchdog cron) |

---

## 2. What I accomplished

### Implemented & verified (all tests green)
- **P0-4 — selection alpha is a gate (G8).** `apply_selection_alpha_gate()`:
  PROVEN_T2 requires direction-adjusted selection-alpha bootstrap CI lower bound
  > 0, else demoted to CANDIDATE with `beta_dominant=True`; CANDIDATE without
  positive alpha is flagged `beta_dominant`. Wired onto strategy/symbol/class
  buckets. On the real book every class has CI lo < 0, so the whole book is
  correctly flagged beta-dominant.
- **P0-5 — DSR n_trials = global.** `n_trials = len(strat_groups)` (full
  search space) instead of the n≥20 survivor count. Provenance now exposes
  `n_trials_dsr` (179 on the real book).
- **P0-2 — retired-strategy blocklist → emission.** The `multi_asset_copytrader`
  scraper was writing retired strategies (`forex_rsi2_mean_reversion`,
  `futures_momentum`); added `is_blocked_pick` at the scraper save and as
  defense-in-depth in `forward_validator.save_active_picks`.
- **P1-1 — independent denylist watchdog.** New hourly workflow
  `audit3-denylist-watchdog.yml` checks the committed ledger with
  `--max-age-days 3`, independent of the `audit3-ledger` cron.
- **P1-3 — MDE-based required_n.** `required_n_mde(mde, sd)` is non-circular
  (pre-declared MDE 0.05%/trade × class SD), reported under `power_analysis`.
- **P1-4 — forward shadow emission.** Root cause: ingest `CONDITIONS` only had
  hypothesis H-119, so the pre-registered pod `POD-EQUITY-BREAKOUT` never got
  forward rows. Added its hypothesis + strategy/direction matching so equity/ETF
  breakout rows classify forward (will accrue for rows closing after
  `registered_at` 2026-11-19).
- **P1-5 — 2×-cost stress is a hard gate (G9).** PROVEN_T2→CANDIDATE and
  CANDIDATE→WEAK when `stress_2x_ok` is False.

### Verified as already done / research-only
- **P0-1 — crypto stop-fill overshoot.** Already implemented inline in
  `audit_trail/universal_pick_resolver.py` (`_gap_fill_price` + `_check_tp_sl_intrabar`,
  default-ON). `audit_trail/stop_fill.py` is a parallel unwired module.
- **P1-2 — reconciled ledger.** `alpha_engine/resolved_closed_view.py` already
  exists (committed in PR #904). The gap is **data**: `dashboard_data.json` is
  stale (Oct 23) and doesn't embed the full book, so the coverage reads
  "3,500 of 14,627". Fix = regenerate the payload, not new code.
- **P0-3 — at-issue stamping.** The leak it guards against is already closed by
  `pit_replay` + `gate_provenance` (which gate the headline on `pit_ok`). The
  `at_issue_strat_fwd_wr` coverage (6%) is a measurement-completeness item, not
  a decision bug. Lower priority.

---

## 3. What's next (recommended order)

1. **Merge/commit the current uncommitted work** (below). This is the
   single most important next step — the changes are not committed.
2. **P0-3** — at-issue stamping: make the pick writer snapshot walk-forward WR at
   issue time (architectural; not urgent).
3. **P2-2** — the forward clock: `POD-EQUITY-BREAKOUT` is pre-registered and now
   has an accruing path; start the 90-day hold-benchmark clock. The day-90 rule
   in `NEXT_STEPS.md` governs the kill/no-edge decision.
4. **P2-3** — resolve audit2 (fold into audit3 or deploy `06_AUDIT2_PAGE/`).
5. **P2-4** — choose ONE premium pod (TSMOM vs cross-sectional crypto).

---

## 4. How to test the changes

From the source repo root:

```bash
cd /home/eaguiar2015/findtorontoevents_antigravity.ca

# compile everything touched
python3 -c "import py_compile; py_compile.compile('alpha_engine/audit3_tribunal.py', doraise=True)"
python3 -c "import py_compile; py_compile.compile('alpha_engine/audit3_edge_hunt.py', doraise=True)"
python3 -c "import py_compile; py_compile.compile('alpha_engine/forward_observations_ingest.py', doraise=True)"

# core suites (all should pass; 111 passed together at handoff)
python3 -m pytest tests/test_audit3_tribunal.py \
  tests/test_audit3_expectancy_gates.py \
  tests/test_audit3_edge_hunt.py \
  tests/test_audit3_forward_gate.py \
  tests/test_forward_observations.py \
  tests/test_forward_observations_ingest.py \
  tests/test_audit3_selection_alpha.py \
  tests/test_audit3_enforcement.py \
  tests/test_audit3_evidence.py \
  tests/test_audit3_coverage_alpha.py \
  -q

# blocklist suites
python3 -m pytest tests/test_strategy_blocklist_goldmine_stocks.py \
  tests/test_strategy_blocklist_rapid_fire_macd.py \
  tests/test_forward_validator_aggregation_collision.py \
  -q
```

Integration POC (real book): run the tribunal with the alpha sidecar and compare
`n_proven` / `beta_dominant` / `alpha_gate` on the output:

```bash
mkdir -p /tmp/kilo
python3 -m alpha_engine.audit3_tribunal \
  --picks audit_dashboard/data/dashboard_data.json \
  --alpha reports/selection_alpha_2026-11-19.json \
  --confirmatory reports/audit3_confirmatory.json \
  --out /tmp/kilo/audit3_ledger_new.json
# expect: n_cells_total=179, n_trials_dsr=179, n_proven=0, all cells beta_dominant=True
```

---

## 5. Critical warnings / gotchas

1. **Uncommitted changes.** Everything is in the working tree only — commit
   before anything else. Do NOT use `git add -A` / `git commit -a`: the tree
   also contains unrelated dirty files that are **not mine**:
   - `___HELL_HEALTH_OPENCODE.MD` (pre-existing)
   - `config/api_model_roster.json` (background scanner)
   Stage only the 8 files listed in §1.
2. **Detached HEAD.** The source repo HEAD is detached. Create/checkout a branch
   before committing (e.g. `git checkout -b feat/audit3-p0-p1-correctness`).
3. **Directory mixup.** Two subagents (P1-3, P1-5) originally wrote to
   `.kilo/worktrees/lapis-chronometer` by mistake. I ported their changes to the
   source repo (`main`), so the canonical versions are in `main`. The worktree
   still has stray uncommitted copies — ignore or discard them; do not re-merge.
4. **P1-3 circular trap.** Do NOT replace the flat `n>=100` with a power-based
   `required_n` derived from the *observed* cell mean — it is circular and
   promotes small-n lucky cells (proven in the POC). Use `required_n_mde` with a
   pre-declared MDE only.
5. **Alpha gate + forward gate.** `n_proven` is currently 0 because the forward
   gate holds it there (no forward rows for `POD-EQUITY-BREAKOUT` yet). The G8
   alpha gate becomes decisive the moment a pod accrues forward rows and tries to
   promote.
6. **Stale data.** `dashboard_data.json` (Oct 23) and the committed
   `audit3_ledger.json` predate some merged PRs. Regenerate before making claims
   about KILL counts.
7. **Fail-open doctrine.** All the new gates (alpha, stress, denylist) are
   fail-open by design; the "independent watchdog" workflow is what turns silent
   fail-open into a loud CI failure.

---

## 6. Remaining P2 backlog (from NEXT_STEPS.md)

- P2-1: backfill FX prices or retire forex (E11)
- P2-2: pre-register `POD-EQUITY-BREAKOUT` + 90-day hold-benchmark clock
- P2-3: resolve audit2 (`/audit2` → audit3 "Method & Limits" or deploy `06_AUDIT2_PAGE/`)
- P2-4: choose ONE premium pod (TSMOM vs cross-sectional crypto)

*Not investment advice.*
