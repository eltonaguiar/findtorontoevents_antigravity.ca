# Independent Review — Audit3 (and audit2 plumbing), 2026-11-20

**Author:** Kilo (vanilla-handsaw worktree)
**Reviewed against:** `origin/main` @ ledger generated `2026-11-20T01:57:23Z`, plus local test runs in this worktree.
**Scope:** verify the claims in the 2026-11-19 COMS handoff / final summary and the 2026-11-20 draft notes; separate what is actually true from stale or unreproducible claims.

---

## 1. Method

- Read `COMS_AUDIT3_HANDOFF_2026-11-19.md`, `COMS_FINAL_SUMMARY_VANILLAHANDSAW_2026-11-19.md`, `updates/2026-11-20-COMS_INDEPENDENT_REVIEW.md`.
- Re-read the gate code in `alpha_engine/audit3_tribunal.py` and `alpha_engine/audit3_selection_alpha.py` and ran the three changed suites directly.
- Compared the **worktree** ledger (`generated_at 2026-11-19T06:11Z`) with the **`origin/main`** ledger (`generated_at 2026-11-20T01:57Z`) and checked live HTTP for the deploy claim.
- Ran the freeze gate to confirm fail-closed behaviour.

Every number below is either a direct measurement I made or is labelled as coming from the main ledger.

---

## 2. What I verified as TRUE

### 2.1 Gate implementations are present on the reviewed branch
| Claim | Evidence |
|---|---|
| F1 block bootstrap | `_circular_blocks` at `audit3_tribunal.py:221`; `bootstrap_mean_ci` at `:236` |
| F2 split-half materiality | `split_half_ok` at `:371` |
| N1 persistence | `PERSISTENCE_RUNS = 2` at `:123`; `apply_persistence_gate` at `:1063` |
| N2 churn | `compute_verdict_churn` at `:1139`; CLI `--max-churn` fail-closed |
| N3 recency | `recency_ok` at `:389` |
| N4 cost-scaled floor | `materiality_floor` at `:693` |
| N5 hold-time normalisation | `hold_days_mean`, `alpha_per_day_pct`, `alpha_annualized_pct`, `min_hold_participation` at `audit3_selection_alpha.py:211-217` |
| N7 freeze gate | `tools/strategy_freeze_gate.py`; exit code **1** (frozen) when run locally |

Workflow wiring confirmed: `.github/workflows/audit3-ledger.yml:201` passes `--history ... --history-write --persistence-runs 2 --prev-ledger audit_dashboard/data/audit3_ledger.json --max-churn 0.30`.

### 2.2 Tests
Local run, this worktree:
```
tests/test_audit3_tribunal.py        34 passed
tests/test_audit3_selection_alpha.py 12 passed
tests/test_strategy_freeze_gate.py    4 passed
                                      -----
                                      50 passed
```
Note: the handoff doc says "86 passed" then "49 for the three files". Measured here is **50** (the selection-alpha suite has 12 tests, not 11). Trivial, but the record should be exact.

### 2.3 Live ledger state (`origin/main`, 2026-11-20T01:57Z)
- `n_rows` 8,769; `valid_closed_picks` 7,942; `total_closed_picks` 16,372; `unscored_rows` 7,603; `zero_pnl_count` 134.
- Cells: 67 tested of 362 → **0 PROVEN, 0 CANDIDATE**, 59 WEAK, 8 KILL, 295 INSUFFICIENT.
- Symbols: 11 KILL, 58 WEAK, **0 CANDIDATE**. Classes: 2 KILL.
- Forward gate `H-119`: `n_forward` 430, `net_pf` 1.115, `pf_ci_lb` 0.9213, `ir` 0.0429, `benchmark_coverage` 0.798, `intrabar_first_touch_all` true, `excess_vs_benchmark_pct` 1.1646 (descriptor only), `eligible` false.
- Pods: `POD-EQUITY-BREAKOUT` `n_forward` 0 / `min_n` 100 / eligible false ("no forward rows"); `POD-CRYPTO-VWAP-REVERSION` 0 forward, observe-only.
- Doctrine object intact: innocent-until-proven-guilty, BH harm q ≤ 0.10, PF < 0.8 watch-flag only, nothing deleted.

---

## 3. Claims that are STALE or NOT REPRODUCIBLE

These appear in the draft notes (`updates/2026-11-20-COMS_INDEPENDENT_REVIEW.md`, `COMS_MESSAGE_2026-11-20.md`) and the 11-19 summary. They should not be carried forward as open defects.

| Claim | Reality (measured 2026-11-20) |
|---|---|
| "Audit2 deployment failure: CI uploads to `/audit/` which 404s; live is `/audit2/`" | **Not reproducible.** `https://findtorontoevents.ca/audit/audit2.html` → **200**; `https://findtorontoevents.ca/audit2/index.html` → **200**; `/audit2/audit2.html` → 404 (that path never existed). The workflow uploads `audit2.html` into `/{SITE_ROOT}/audit` (`audit-dashboard.yml:1286`), which is correct. |
| "`n_candidate` is 0 despite candidate symbols — add `n_candidate_symbols`" | **Already resolved.** Main's ledger now has `n_candidate_symbols: 0`, `n_weak_symbols: 58`, and an explicit `summary_scope` note; symbol verdicts are exactly `{KILL: 11, WEAK: 58}` with no CANDIDATE row. |
| "N5 selection alpha is code-only, not published" | **No longer true.** `ledger.selection_alpha.available = true` on main, with definition and source path populated. |
| "Coverage 105.26%" | Outdated figure. Current main ledger is worse: **8,769 scored vs 7,942 valid = 110.41%**. The defect is real, the number moved. |
| "46% dropped before scoring" | Already corrected previously to 41.2%; current main has 7,603 unscored of 16,372 total. |

---

## 4. Genuine remaining defects (ordered)

1. **P0 — coverage arithmetic is still impossible, and the headline is now silent.**
   `scored_rows` 8,769 > `valid_closed_picks` 7,942 → 110.41%. Worse, `scored_share_of_valid_pct` is `null` in the main ledger, so the public headline metric is missing rather than merely wrong. A `denominator_reconciliation` block (canonical kept/excluded per reason + the 430-row forward bucket) is still the fix. This is the single largest honesty gap.

2. **P1 — forward benchmark window still short.** H-119 `benchmark_coverage` 0.798 < the 0.90 rule, one of three independent failures (PF CI-LB 0.9213, IR 0.0429). Padding the ingest query past each symbol's latest exit (`BENCHMARK_LOOKAHEAD_MS`) and backfilling remains outstanding.

3. **P1 — zero-row pods cannot promote.** Both registered pods have `n_forward: 0`; `POD-EQUITY-BREAKOUT` is blocked purely by absence of forward rows. No scheduled ingest → the pod stays at zero regardless of strategy quality. Ingest scheduling is the actual blocker, not the gate.

4. **P1 — `excess_vs_benchmark_pct` is reported but explicitly not gated.** The ledger says so itself. Decide deliberately whether it gates; descriptor-only fields invite accidental over-reading.

5. **Policy — freeze still open.** `strategy_freeze_gate.py` exits 1 with E11/E13/E14 P0 items open. The E3 equity-breakout pod must not start while N7 is red. Verify E11/E13/E14 closure independently rather than trusting the manifest.

---

## 5. Recommendations

1. Fix the coverage reconciliation first, and publish `scored_share_of_valid_pct` again — a null headline is worse than a wrong one because it hides the problem.
2. Do not start E3 until (a) coverage reconciles and (b) the forward benchmark window reaches ≥90% on real rows.
3. Keep N7 wired and treat the freeze manifest as a claim to re-verify, not a fact.
4. Correct the two stale P0/P1 items above in whatever tracks peer findings, so the next agent does not spend a cycle on an already-fixed deploy path.
5. Keep the doctrine and the fail-closed test discipline; both are intact and worth preserving.

---

## 6. Reproduction commands

```bash
# tests (this worktree)
python3 -m pytest tests/test_audit3_tribunal.py tests/test_audit3_selection_alpha.py \
  tests/test_strategy_freeze_gate.py -q          # 50 passed

# freeze gate is fail-closed
python3 tools/strategy_freeze_gate.py; echo "exit=$?"   # exit=1

# main ledger headline numbers
git show origin/main:audit_dashboard/data/audit3_ledger.json | python3 -c "
import json,sys; d=json.load(sys.stdin); c=d['coverage']
print('scored', c['scored_rows'], 'valid', c['valid_closed_picks'],
      'pct', c['scored_share_of_valid_pct'])"

# deploy claim
curl -o /dev/null -s -w "%{http_code}\n" https://findtorontoevents.ca/audit/audit2.html   # 200
```

**Bottom line:** the statistics and gates on `main` are real and well-tested; the two headline "P0s" in the draft notes are one stale and one already fixed. The actual remaining honesty gap is the coverage denominator (now 110.4% and silently unpublished), followed by the forward-benchmark window and the un-scheduled pod ingest. Fix those before E3.
