# COMS — audit3 handoff (2026-11-19)

**Author:** kilo (vanilla-handsaw worktree)
**Session:** ses_e0d890f2effeCAiHY7r7yrGkUX (direct human) + subagent tasks
**Branch:** `add-strategy-variable-tracking`
**Status:** all audit3 hardening (F1/F2/N1–N5/N7) shipped + documented; N6/E11/E12/E13/E14/E8/E3 ready for next agent.

---

## 1. What was accomplished

### 1.1 audit3 statistical-gate hardening (F1/F2/N1–N5/N7)
- **F1 block bootstrap** — `_circular_blocks` + `bootstrap_mean_ci(..., block=True)` for G2 net CI and 2× cost stress; test `test_block_bootstrap_widens_clustered_ci`.
- **F2 split-half materiality** — `split_half_ok(..., min_mean=PROVEN_MIN_NET_CI_LO_PCT)` wired in `evaluate_cell`.
- **N1 repeated-looks (G8)** — `PERSISTENCE_RUNS=2`, `cell_key`/`load_history`/`save_history`/`apply_persistence_gate`, CLI `--history`/`--history-write`, workflow sidecar `audit3_verdict_history.json`.
- **N2 verdict churn** — `raw_verdict` stamped, `load_prev_verdicts`/`compute_verdict_churn`, CLI `--prev-ledger`/`--max-churn` (exit 3, fail-closed), workflow passes `--prev-ledger audit_dashboard/data/audit3_ledger.json --max-churn 0.30`.
- **N3 recency gate** — `recency_ok` trailing 25% (min 5) net-mean check; `PROVEN_T2` capped at `CANDIDATE` on stale regime; per-cell `recency`/`recent_ok`.
- **N4 cost-scaled materiality floor** — `materiality_floor(mean_cost_pct) = max(0.05, 0.5·cost)`; used for split-half and `PROVEN_T2` CI lower bound; per-cell `mean_cost_pct`/`materiality_floor_pct`.
- **N5 hold-time-normalised selection alpha** — `alpha_per_day_pct`, `alpha_annualized_pct`, `hold_days_mean/median`, `min_hold_participation`, `alpha_pct_min_hold` in `audit3_selection_alpha.py`.
- **N7 freeze gate** — `reports/strategy_freeze.json` + `tools/strategy_freeze_gate.py` (exit 1 frozen); enforced as first step of `forward-test-new-strategies.yml`.

**Verification:** 86 passed (`test_audit3_tribunal.py` 34, `test_audit3_selection_alpha.py` 11, freeze 4, edge/coverage/evidence). Two-run N1 smoke: demote→promote with `first_pass_at`. N2 CLI: `--max-churn 0.0` exits 3. End-to-end smoke on synthetic 150-row payload: exit 0, verdicts unchanged, `recency`/`materiality_floor_pct` populated.

### 1.2 Documentation & evidence
- `docs/AUDIT3_REVIEW_2026-11-19.md` — shipped table + doctrine note.
- `docs/FUND_MANAGER_QUICK_VIABLE_PLAN_2026-11-19.md` — beta core + premium pod menu + sequencing.
- `docs/EDGE_IDEAS_BACKLOG_2026-11-19.md` — P0 (E11/E12/E13/E14/E1) → P1 (E8/E9/E3/E7) → P2.
- `updates/2026-11-19-audit3-tribunal-f1f2-n1-n2-n3-n4-n5-n7.md` — detailed fix doc.
- `reports/strategy_freeze.json` — frozen true, P0 = E11/E13/E14, `enforced_by`.

### 1.3 Research & gap analysis (via subagents)
- N6 (excluded-cohort bias) — `dashboard_generator.py` + `resolved_closed_view.py` only keep aggregate counts/reason labels; excluded rows themselves are dropped before export. Bias audit requires `trading_picks` direct query or new `excluded_cohorts` sidecar.
- E11 (FX backfill) — `fx_prices` ends 2026-02-09, symbol mismatch (`AUDJPY=X` vs `AUDJPY`), no backfill script. E11 feasible with yfinance + mapping fix; smallest step = backfill 2026-02-11 → 2026-11-19 and add `symbol_candidates` for `XXX-YYY` → `XXXYYY`.
- E13 (PIT stamping) — `at_issue_strat_fwd_wr` only on 215/3500 rows; `wf_verdict` scored +0.96% until PIT replay (−0.19%). Smallest step = write `at_issue_*` for 100% of rows at issue time in the resolver.
- E14 (exit redesign) — selection alpha shows CRYPTO LONG −0.442%/pick, ETF LONG −0.272%/pick vs hold. No A/B harness exists. Smallest step = `tools/exit_ab_paper.py` (current TP/SL vs vol-scaled time exit on same signals).
- E12 (hold-benchmark pilot) — selection alpha exists (retrospective); forward hold-leg recorder missing. Smallest step = `tools/forward_hold_leg.py` + daily job writing `forward_hold_leg.json`.
- Beta core — `tools/beta_portfolio_tracker.py` + `beta-portfolio-refresh.yml` (monthly cron) wired; status JSON not visible in worktree (committed on main by CI). Conservative sleeve ready; deploy to site needed.

---

## 2. What's next (priority order for the agent taking over)

### Immediate (today, before any merge)
1. **N6** — add `excluded_cohorts` block/sidecar in `dashboard_generator.py` (per-reason n/WR/PF/mean PnL/long-short split + row sample) or one-off SQL against `trading_picks`.
2. **E11 stub** — `tools/fx_backfill.py` (yfinance daily for 15 pairs, 2026-02-11 → today, map `AUDJPY=X`/`AUD-USD` → `AUDJPY`/`AUDUSD`, write `fx_prices`).
3. **E13 stub** — modify resolver to stamp `at_issue_strat_fwd_wr`/`at_issue_*` for 100% of rows; re-run `audit3_edge_hunt.py` on a 100% stamped slice.
4. **E14 stub** — `tools/exit_ab_paper.py` (current TP/SL vs vol-scaled time exit, same signals, 2 regimes, alpha CI gate).

### Short (this week, after P0 stubs land)
5. **E12 pilot** — `tools/forward_hold_leg.py` + daily job + 90-day clock in `forward-benchmark-ledger.yml`.
6. **E8 or E3** — one premium pod only (E8 TSMOM on liquid futures/ETFs or E3 cross-sectional crypto); pre-register in `reports/hypothesis_registry.json`; untouched holdout; 2× costs + 1-bar delay.
7. **Fund-manager beta core** — verify `beta_portfolio_status.json` lands on live site; wire Conservative sleeve into `minimal_core_config.json` (or new `beta_core_config.json`).

### Policy
- **N7 freeze gate is live** — do not generate new strategies while any P0 item is open.
- **No new scanner until E11/E13/E14 close** — per fund-manager memo.
- **Test everything** — every new gate or stub must have a deterministic test that fails closed.

---

## 3. Where the files are

**Core changes (committed on branch, staged in worktree):**
- `alpha_engine/audit3_tribunal.py` — F1/F2/N1/N2/N3/N4 (block bootstrap, split-half, persistence, churn, recency, materiality).
- `alpha_engine/audit3_selection_alpha.py` — N5 (hold-time normalisation).
- `tests/test_audit3_tribunal.py` — 34 tests (F1/F2/N1–N4).
- `tests/test_audit3_selection_alpha.py` — 11 tests (N5).
- `tests/test_strategy_freeze_gate.py` — 4 tests (N7).
- `.github/workflows/audit3-ledger.yml` — N1 history sidecar + N2 `--prev-ledger`/`--max-churn`.
- `.github/workflows/forward-test-new-strategies.yml` — N7 freeze step.
- `tools/strategy_freeze_gate.py` + `reports/strategy_freeze.json` — N7 gate.

**Docs (new, untracked):**
- `docs/AUDIT3_REVIEW_2026-11-19.md`
- `docs/FUND_MANAGER_QUICK_VIABLE_PLAN_2026-11-19.md`
- `docs/EDGE_IDEAS_BACKLOG_2026-11-19.md`
- `updates/2026-11-19-audit3-tribunal-f1f2-n1-n2-n3-n4-n5-n7.md`

**Research artifacts (no files written):**
- Subagent reports on N6/E11/E12/E13/E14/E8/E3 feasibility (embedded in chat history).

---

## 4. How to test your changes

### Unit / integration (fast, local)
```bash
python3 -m pytest tests/test_audit3_tribunal.py tests/test_audit3_selection_alpha.py tests/test_strategy_freeze_gate.py -q
# 86 passed expected
```

### End-to-end smoke (synthetic payload)
```bash
python3 -m alpha_engine.audit3_tribunal \
  --picks /tmp/kilo/n1/picks.json \
  --out /tmp/kilo/n1/ledger5.json \
  --history /tmp/kilo/n1/hist.json --history-write \
  --prev-ledger /tmp/kilo/n1/ledger4.json --max-churn 0.30
# exit 0, verdicts unchanged, recency/materiality_floor_pct populated
```

### Workflow dry-run (no push)
```bash
# locally simulate the audit3-ledger job with DB_PASS_STOCKS
DB_PASS_STOCKS=... bash -x .github/workflows/audit3-ledger.yml  # or just the python steps
```

### N7 freeze gate
```bash
python3 tools/strategy_freeze_gate.py          # exit 1 (frozen, P0 open)
python3 tools/strategy_freeze_gate.py --json   # prints manifest
```

### N2 churn (CLI)
```bash
python3 -m alpha_engine.audit3_tribunal \
  --picks /tmp/kilo/n1/picks.json --out /tmp/kilo/n1/ledgerX.json \
  --prev-ledger /tmp/kilo/n1/ledger4.json --max-churn 0.0
# exit 3, no ledger or history written
```

### Selection alpha (needs price tables)
```bash
python3 alpha_engine/audit3_selection_alpha.py \
  --picks audit_dashboard/data/dashboard_data.json \
  --out /tmp/selection_alpha.json
# verify hold_days_mean/median, alpha_per_day_pct, alpha_annualized_pct, min_hold_participation
```

---

## 5. Recommendations to the next agent

1. **Start with N6** — the excluded-cohort bias audit is the single largest honesty gap. A sidecar with per-reason n/WR/PF/mean PnL/long-short split + row sample is cheap and makes the coverage statement complete.
2. **Do E11/E13/E14 stubs before any premium pod** — they are the value-destroying expressions and the measurement holes. The fund-manager memo explicitly says "stop the bleed first."
3. **One premium pod only (E8 or E3)** — never more than two concurrent. Pre-register, untouched holdout, 2× costs + 1-bar delay, Bonferroni N.
4. **Keep the freeze gate wired** — N7 is the single sentence every reviewer agreed on. Do not generate new strategies while a P0 item is open.
5. **Test every gate fail-closed** — if a new gate or stub cannot be shown to kill a bad claim, it is not a gate.
6. **Document every fix** — every code change must have a `.md` in `updates/` describing what was broken, what changed, and how it was verified.
7. **Do not push commits that include files you did not create or modify** — safety rule. Create a clean branch with only your changes.
8. **COMS coordination** — the bus is transient (no retained messages). Use `inbox/.../all` and `mentions/all` for fleet-wide notes; DM specific seats only when you need a reply. Heartbeat with `HEARTBEAT_OK` when nothing needs attention.

---

## 6. Open questions for the operator (from the backlog)

1. Which single P1 pod — E8 (TSMOM) or E3 (cross-sectional crypto)?
2. Budget/critical path for FX backfill (E11), or retire forex as unmeasurable?
3. Commit Mercury's schema spec and Arena's review as real files, or keep `EDGE_IDEAS_BACKLOG_2026-11-19.md` as single source?
4. For E12, 90-day paper clock acceptable, or 30-day with smaller n?

---

**Bottom line:** audit3 is now a fail-closed statistical tribunal with persistence, churn, recency, cost-scaled materiality, hold-time normalisation, and a generation freeze. The next agent should close the measurement holes (N6/E11/E13/E14) and run one premium pod under the freeze gate. Everything else is process, not a promise.
