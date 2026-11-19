# COMS handoff — audit3 G8/DSR/family gates + forward ingest (2026-11-19)

**From:** Kilo (`vanilla-handsaw-audit3` worktree) · **To:** COMS / next audit3 implementer
**Branch:** `fix/audit3-alpha-scope` · **Base:** `3dfa66e` (main tip at time of work)
**Commits:** `b9dd4378e65` (first pass), `3844a4e34e2` (review fixes)
**Worktree:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/vanilla-handsaw-audit3`
**Status:** committed locally, **not pushed**, no PR opened.
**Companion review:** `antigravity_review_Nov192026/10_KILO_VANILLA_HANDSAW/VERIFICATION_P0P1.md`

---

## 0. Read this first

This handoff is about **four gate defects found by verifying commit `3dfa66e`**, not
about new strategies. The one-line summary: *the audit could still promote a cell on
market beta, correct its multiplicity for the wrong number of trials, leave one verdict
bucket completely ungated, and could never accrue forward evidence on a schedule.*

Nothing here changes a strategy, a threshold's value, or the honest verdict policy. The
intent is that each gate tests what its own docstring already claimed to test.

**Do not merge blind.** The single highest-risk change is §3 (require-alpha), because it
can demote every `PROVEN_T2` in a ledger run where the alpha sidecar is absent. That is
intended, but it is a visible change to the published page and should be seen before
merge.

---

## 1. G8 selection alpha must be measured at the same scope it proves

### Change
- `alpha_engine/audit3_selection_alpha.py` now emits `by_strategy`, keyed
  `CLASS/STRATEGY/DIRECTION`, floor 20 rows (same as `by_slice`).
- `apply_selection_alpha_gate()` looks up, in order: `by_strategy` (scope
  `strategy`), then `by_slice`/`by_class` (scope `class_proxy`).
- Only `scope == "strategy"` (for a strategy cell) or `scope == "class"` (for a class
  aggregate) can prove a cell. A `class_proxy` is recorded and demotes `PROVEN_T2`.
- The gate returns `{applied, tested, demoted, scopes}` and `build_report` publishes it
  under `selection_alpha.gate`.

### Why
At `3dfa66e`, `_alpha_lo(ac, direction)` read only `by_slice["CLASS/DIR"]` and
`by_class["CLASS"]`. Every strategy cell in a class with positive alpha inherited the
class's proof. P0-4's own acceptance criterion — "a beta-only 'profitable' cell cannot
reach PROVEN_T2" — was therefore false: a strategy that *underperformed* buy-and-hold
inside an *outperforming* class reached `PROVEN_T2`.

This is the exact failure the review names as root cause #1 (beta counted as skill). A
class-level number answers "did this asset class beat holding it?"; it cannot answer "did
this strategy's entries beat holding the same instrument over the same window?" Only the
second question is about skill.

### Implementation suggestion
1. Merge as-is; the producer and consumer key format are tested together.
2. Before merging, re-run the ledger once with `--alpha` and confirm
   `selection_alpha.gate.scopes.strategy > 0`. If it is 0, the sidecar is stale and every
   strategy cell will demote — check `audit3_selection_alpha.py` coverage, not the gate.
3. If a class has no strategy-level alpha because price coverage is thin, that is the
   gate working. Do **not** "fix" it by falling back to class alpha; add coverage.

### Risk / rollback
Low code risk, medium reporting risk (cells may lose `PROVEN_T2`). Rollback is reverting
the `_lookup` scopes; the sidecar's `by_strategy` field is additive and harmless.

### Verification
```
python3 -m pytest tests/test_audit3_tribunal.py -q
# test_selection_alpha_gate_rejects_a_class_proxy_for_a_strategy_cell
# test_selection_alpha_gate_accepts_strategy_level_proof
```

---

## 2. DSR multiplicity: global for PROVEN, bucket width for CANDIDATE

### Change
- Added `GLOBAL_TRIAL_FLOOR = 658` and `global_trial_count(*counts)`.
- `evaluate_cell(..., n_trials_local=...)` now emits `dsr` (global) and `dsr_local`.
- `_promote`: `PROVEN_T2` uses `dsr >= 0.95`; `CANDIDATE` uses `dsr_local >= 0.50`
  (when the bucket has ≥2 cells), else no floor.

### Why
At `3dfa66e`, `n_trials = len(strat_groups)` counted the distinct cells in the loaded
3,500-row payload slice (~45–60). The live registry is ~658 strategies (`MASTER_AUDIT.md`
2026-11-14: 658 strategies, 682 asset×strategy pairs, 2,218 strategy×symbol cells). G4
exists to correct for the search space; correcting for the slice under-corrects and lets
overfits clear the gate.

**The peer plan's literal version ("658 everywhere") has a second bug:** at 658 trials a
promising-but-unproven cell falls below the CANDIDATE `DSR >= 0.50` floor, so nothing
reaches forward paper — the "one-way ratchet to zero" the review criticises. Measured:
a thin n=120 cell scores DSR 0.95 at 45 trials, 0.80 at 658. CANDIDATE means "worth
forward paper", not "a discovery", so it should be judged against the breadth actually
observed.

### Implementation suggestion
- Keep the split. If you later add a per-bucket trial manifest, replace
  `GLOBAL_TRIAL_FLOOR` with a measured value and raise the floor only.
- Watch `summary.n_candidate` after the first run. If it collapses to 0, check whether
  `dsr_local` is being written at all (`"dsr_local" in cell`) before touching the 0.50
  threshold — a missing key silently falls back to the stricter global DSR.

### Risk / rollback
`GLOBAL_TRIAL_FLOOR` is a constant; if 658 is judged wrong, change the constant, not the
gate structure. Rollback = delete the floor (returns to slice counts).

### Verification
```
python3 -m pytest tests/test_audit3_tribunal.py -q
# test_proven_tier_pays_the_global_dsr_correction
# test_candidate_tier_uses_local_breadth_not_the_global_registry
# test_dsr_trial_count_never_below_the_registry_space
```

---

## 3. A missing alpha sidecar must not mean "all cells passed"

### Change
- `build_report(..., require_alpha: bool = False)`. The CLI passes `True`.
- New `demote_proven_without_alpha(buckets)`: demotes every `PROVEN_T2` to `CANDIDATE`,
  sets `beta_dominant`, adds a reason, and `selection_alpha.gate.applied` stays `false`.
- Library callers and tests keep the old fail-open behaviour.

### Why
`audit3-ledger.yml` runs the alpha sidecar with `continue-on-error: true` **and**
`|| true`, and `audit3_selection_alpha.py` exits 3 *without writing `--out`* when price
coverage is zero. The workflow then passes no `--alpha` and `build_report` fail-opened
silently — while still printing the G8 convention string. So a ledger could mint
`PROVEN_T2` with no alpha proof at all, and the page would say G8 was in force.

Fail-open is correct at runtime (a DB outage must not block publishing). Fail-open is
wrong at publication (an unmeasured criterion must not read as satisfied).

### Implementation suggestion
- Merge only after you have looked at one ledger run with the sidecar deliberately
  absent, and are happy that `n_proven = 0` and `gate.applied = false` is the message
  you want on the page.
- Optional follow-up: surface `selection_alpha.gate.applied` in `audit3.html` next to
  the class table so a reader can see whether G8 ran.

### Risk / rollback
Highest-visibility change in this handoff. Rollback = drop `require_alpha=True` from the
CLI call; the helper is inert without it.

### Verification
```
python3 -m pytest tests/test_audit3_tribunal.py -q
# test_require_alpha_demotes_proven_when_the_sidecar_is_missing
```

---

## 4. Alpha coverage must be proportionate to the cell

### Change
- `ALPHA_MIN_N = 20`, `ALPHA_MIN_COVERAGE = 0.50`.
- Proof now requires `alpha_n >= max(20, 0.5 * cell.n)`; `alpha_gate` publishes
  `alpha_n` and `alpha_coverage_ok`.

### Why
The alpha sidecar drops rows with no timestamp or no price bars. A 20-row alpha sample
could therefore "prove" a 500-row cell, with the gap invisible in the JSON. Thresholds
are a judgement call; the important part is that the ratio is published and enforced,
not hidden.

### Implementation suggestion
- If 50% is too strict for FOREX while `fx_prices` is stale (it ends 2026-02-09), do not
  lower the ratio. Fix the price coverage (E11) or let forex demote — that is the honest
  outcome until the data exists.

### Verification
```
# test_alpha_must_cover_enough_of_the_cell_to_prove_it
```

---

## 5. Direction and window normalisation in the alpha sidecar

### Change
- `audit3_selection_alpha.py` now normalises direction with
  `symbol_identity.direction_key` (BUY→LONG, SELL→SHORT).
- Rows with `issued_at >= closed_at` are skipped and counted as
  `missing["degenerate_window"]`.

### Why
Two silent corruptions found by adversarial review:
1. `edge_hunt._dir` maps `BUY → "?"`, while the tribunal maps `BUY → LONG`. BUY rows got
   an **inverted** benchmark (`alpha = pnl + move`) and a `CLASS/STRAT/?` key that could
   never match a `…/LONG` cell — so genuinely good BUY strategies were demoted, and class
   alpha was biased.
2. `issued_at` falls back to `closed_at`, so a row with only a close stamp gets
   `p0 == p1`, `move == 0`, `alpha == pnl`. That manufactures a zero benchmark and lets a
   beta-only strategy pass G8.

### Implementation suggestion
- Merge as-is. If you see `missing["degenerate_window"]` large, the fix is in the pick
  writer (stamp entry time at issue), not in the sidecar — do not relax the skip.
- Consider adding `degenerate_window` to the page's coverage note so the count is
  visible rather than buried in `missing`.

### Verification
```
python3 -m pytest tests/test_audit3_selection_alpha.py -q
# test_buy_direction_is_long_and_never_lands_in_a_question_mark_bucket
# test_rows_without_an_entry_stamp_get_no_zero_benchmark
```

---

## 6. Source-family cells were the one ungated verdict bucket

### Change
`build_report` now runs BH, `_promote` (FDR/DSR/forward) and `apply_harm_gate` on
`source_families`.

### Why
Families were emitted straight from `evaluate_cell()` and were verdict-bearing rows on
the page. They could reach `PROVEN_T2` on raw statistics alone, with no multiplicity,
forward or harm gate — the only bucket in the ledger with that property.

### Implementation suggestion
- No tuning needed. If `source_families` now look worse, that is the gates doing their
  job; the previous numbers were uncorrected.

---

## 7. The forward ledger needs a writer on a schedule

### Change
New `.github/workflows/forward-observations-ingest.yml`:
- cron `41 */6 * * *` (offset from `audit3-ledger` `:23 */6` and the watchdog `:45 *`)
- `actions/checkout` pinned to `ref: main`
- runs `python3 -m alpha_engine.forward_observations_ingest --apply --json`
- commits `reports/forward_observations.jsonl` (`[skip ci]`) only when
  `github.ref == refs/heads/main`
- fails hard when `n_admissible == 0`
- prints every `PROVEN_T2`/`CANDIDATE` cell that has no forward instrument

### Why
P1-4 was reported as done, but `reports/forward_observations.jsonl` held 430 rows, all
`H-119`, written once by commit `5c0c42d` at 2026-11-19T07:20Z. Nothing referenced the
ingest and it defaults to a dry run. A forward ledger that does not accrue cannot mint a
forward-based verdict; the module existing is not the same as the process running.

On "shadow emission for every cell incl KILL": the ingest is condition-keyed by
`CONDITIONS` (H-119, H-BABY-EQUITY-VT-PATTERN-SWEEP-001). A cell with no registered
condition has no honest forward instrument. The workflow therefore **reports** the
coverage hole instead of fabricating shadow trades. If COMS wants every cell covered, the
work is to register a condition per pod — not to synthesise rows.

### Implementation suggestion
1. Land the workflow, then run it once via `workflow_dispatch` and confirm the ledger row
   count grows and the commit lands on `main`.
2. If `n_admissible` is 0 on the first run, the cohort query or the DB secret is broken —
   do not "fix" it by relaxing the assertion.
3. Expect duplicates on re-runs: `row_id()` is deterministic, so `append()` dedupes by id.
   A green run with `added=0, duplicates>0` is healthy. A green run with
   `n_admissible=0` is not, which is why that case fails.
4. The `--apply` + `[skip ci]` commit pattern mirrors `audit3-ledger.yml`; keep the
   `git pull --rebase` retry loop if you edit it.

### Risk / rollback
Low. The workflow only appends to a JSONL ledger. Disable by removing the cron.

---

## Merge checklist for the next agent

1. `git fetch && git log --oneline 3dfa66e..fix/audit3-alpha-scope` → expect the two
   commits above.
2. Rebase onto current main (main moved to `3dfa66e` during this work; it will move
   again). Resolve conflicts in `audit3_tribunal.py` by keeping both sides' gates.
3. Run:
   ```
   python3 -m pytest tests/test_audit3_tribunal.py tests/test_audit3_expectancy_gates.py \
     tests/test_audit3_edge_hunt.py tests/test_audit3_selection_alpha.py \
     tests/test_forward_observations_ingest.py tests/test_audit3_cost_basis.py -q
   ```
   Expected: 79 passed.
4. Regenerate the ledger with `--alpha` and diff the verdict counts:
   `n_proven`, `n_candidate`, `selection_alpha.gate.*`. Report the delta before pushing.
5. Push to a PR. Do **not** push to `main` directly; this changes published verdicts.

## What this handoff does not fix

| Gap | Why left open |
|---|---|
| P0-3 at-issue stamping | A writer change, not a gate change. Retroactive stamping recreates the leak. |
| Symbol-level alpha | No measurement exists; symbol cells are demoted fail-closed. Next step is a per-symbol alpha, not a code tweak. |
| Forward coverage is one hypothesis wide | Needs a registered condition per pod (see §7). |
| Alpha vs tribunal row set | Alpha reads `picks.recent_closed`; the tribunal can score the canonical view. Coverage floor makes the gap visible; aligning both inputs is a pipeline change. |
| Blocklist fail-open | `forward_validator.py` wraps the filter in `except Exception: pass`; `_is_blocked_pick = None` on import failure. Make loud separately. |
| Pre-existing test pollution | 3 slippage tests fail only in a wide `-k` run (a global constant is mutated by another test). Reproduces without these commits. |

## Evidence

- `antigravity_review_Nov192026/10_KILO_VANILLA_HANDSAW/VERIFICATION_P0P1.md` — claim-by-claim
  verification of `3dfa66e` with file:line evidence.
- `updates/2026-11-19-audit3-g8-scope-global-dsr-family-gates-forward-schedule.md` — in-repo
  change log, including the second round of review fixes.
- `reports/forward_observations.jsonl` — 430 rows, all `H-119`, last written
  `2026-11-19T07:20Z` (the "no schedule" evidence).

*Not investment advice. No strategy, threshold value, or honest-verdict policy was
changed by this work.*
