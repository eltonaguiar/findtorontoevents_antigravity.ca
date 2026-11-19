# audit3 — selection-alpha scope, multiplicity floor, and the forward ledger

**Date:** 2026-11-19 · **Landed:** `6abfa22364e` on `main`
**Area:** financial-prediction verdicts (`/audit3`, `audit3_ledger.json`)
**Companion:** `updates/2026-11-19-audit3-g8-scope-global-dsr-family-gates-forward-schedule.md`
(implementation log) and `COMMUNICATION/handoffs/` in `AGENT_FOLDERFRAMEWORK` (coordination).

This note is about **what the ledger is allowed to conclude about a strategy's edge**. It
does not add a strategy, change a threshold's value, or relax any gate. Every change makes
a verdict harder to earn, and each is tied to a defect that was live on `main` before this
commit.

---

## 1. A strategy was being proven by its asset class

**Defect.** `apply_selection_alpha_gate()` looked up alpha only at class level
(`by_class["CRYPTO"]`) and at class×direction (`by_slice["CRYPTO/LONG"]`). Every strategy
cell inside a class with positive alpha inherited that proof. A strategy whose entries
underperformed buy-and-hold — but whose asset class rose — could reach `PROVEN_T2`.

**Why it matters financially.** Selection alpha is the only number that separates skill
from beta: `alpha = pick net return − direction-adjusted buy & hold over the same window`.
A class-level number answers "did this asset class beat holding it?", not "did this
strategy's entries beat holding the same instrument?". Only the second is evidence of an
edge. This was the exact failure mode named in the 2026-11-19 review ("beta counted as
skill").

**Change.** The sidecar now emits `by_strategy`, keyed `CLASS/STRATEGY/DIRECTION`. The
gate proves a strategy cell only with same-scope alpha. A class number is recorded as
`class_proxy`: it is published, it informs, and it demotes — it never proves. Class
aggregate cells still use the class measurement (that is their own scope).

**How to read it.** Each cell now carries
`alpha_gate: {scope, alpha_ci_lo, alpha_n, need_n, alpha_coverage_ok, passed, status}`.
`status` is one of `proven | proxy | unmeasured | beta_dominant | insufficient_coverage`.
A `PROVEN_T2` with `status != "proven"` is a bug.

## 2. A small alpha sample could certify a large cell

**Defect.** The sidecar drops rows with no entry timestamp or no price bars. A 20-row alpha
sample could therefore "prove" a 500-row cell, with the gap invisible in the JSON.

**Change.** Proof requires `alpha_n >= max(20, 0.5 × cell.n)`. `alpha_n`, `need_n` and
`alpha_coverage_ok` are published per cell so the ratio is visible rather than implied.

**Reading it.** `insufficient_coverage` means the measurement exists but covers too little
of the cell. Do not lower the ratio to make a class pass; fix price coverage (see §6).

## 3. Multiplicity was corrected for the slice, not the search space

**Defect.** `n_trials` was the number of distinct cells in the loaded 3,500-row payload
(~45–100), not the live search space. The 2026-11-14 registry audit counted **658 distinct
strategies** (682 asset×strategy pairs, 2,218 strategy×symbol cells). G4 exists to correct
for the space actually searched; correcting for the slice lets overfits clear the bar.

**Change.** `GLOBAL_TRIAL_FLOOR = 658`; PROVEN_T2 pays `max(observed, 658)`.

**Why CANDIDATE is treated differently.** Applying 658 to every tier empties the forward
queue: a thin n=120 cell scores DSR 0.95 at 45 trials but 0.80 at 658, which is enough for
forward paper and not enough for promotion. CANDIDATE therefore uses the observed bucket
width (`dsr_local`), because CANDIDATE means "worth paper", not "a discovery". PROVEN still
pays the global correction.

**Observed effect.** Test cells with a 4.0/−0.6 payoff and 33% win rate now need roughly
n≥200 to reach `PROVEN_T2` (n=120 → DSR 0.83 → CANDIDATE; n=210 → DSR 0.99 → PROVEN).
That is the intended tightening, and it is why two pre-existing tests were re-sized rather
than re-asserted.

## 4. A missing alpha sidecar meant "all cells passed"

**Defect.** `audit3-ledger.yml` runs the alpha sidecar with `continue-on-error`/`|| true`,
and the sidecar exits 3 without writing output when price coverage is zero. The tribunal
then fail-opened — and still printed the gate's convention string, so the page implied a
criterion had been applied that had not run.

**Change.** The CLI passes `require_alpha=True`; `demote_proven_without_alpha()` demotes
`PROVEN_T2` to `CANDIDATE` and publishes `selection_alpha.gate.applied = false`. Library
callers and unit tests keep the old fail-open behaviour.

**Reading it.** A ledger where `gate.applied` is false means alpha was not measured. Treat
every cell as unproven, not as passed.

## 5. One verdict bucket skipped every gate

**Defect.** `source_families` (copytrader / polymarket / kalshi / ml_enhanced …) were
emitted straight from `evaluate_cell()` with no BH, no DSR/forward `_promote`, and no harm
gate. They were verdict-bearing rows on the page and the only bucket that could reach
`PROVEN_T2` on raw statistics alone.

**Change.** They now run BH, `_promote` and `apply_harm_gate`. If family numbers look worse
after this, the previous figures were uncorrected.

## 6. The forward ledger had no writer on a schedule

**Defect.** `reports/forward_observations.jsonl` held 430 rows, all `H-119`, written once
by hand (`5c0c42d`, 2026-11-19T07:20Z). Nothing scheduled the ingest, and it defaults to a
dry run. A forward ledger that does not accrue cannot mint a forward-based verdict.

**Change.** `.github/workflows/forward-observations-ingest.yml`, cron `41 */6 * * *`,
runs `--apply`, pins `ref: main`, commits the ledger, fails on `n_admissible == 0`, and
reports every `PROVEN_T2`/`CANDIDATE` cell that has no forward instrument.

**Honest limitation.** The ingest is condition-keyed (H-119, the equity-breakout pod). A
cell with no registered condition has no honest forward instrument, so the job reports the
coverage hole instead of fabricating shadow trades. Covering every cell is a registration
task per pod, not a code change.

## 7. Sidecar hygiene that changed measurements

- **BUY was mapped to `"?"`.** `edge_hunt._dir` normalises `BUY→LONG`; the sidecar used its
  own helper that returned `"?"`. BUY rows therefore got an **inverted** benchmark
  (`alpha = pnl + move`) and a `CLASS/STRAT/?` key that could never match a `/LONG` cell.
  Now normalised through `symbol_identity.direction_key`.
- **`issued_at` falls back to `closed_at`.** A row with only a close stamp produced
  `p0 == p1`, `move == 0`, `alpha == pnl` — a fabricated zero benchmark that a beta-only
  strategy could pass on. Such rows are now skipped and counted as
  `missing["degenerate_window"]`.

## What this does not fix

| Gap | Why it remains |
|---|---|
| At-issue gate stamping (P0-3) | A writer change; retroactive stamping recreates the leak. |
| Symbol-level alpha | No same-scope measurement exists, so symbol cells demote (fail-closed). |
| Forward coverage beyond H-119 | Needs one registered condition per pod. |
| Alpha vs tribunal row set | Alpha reads `picks.recent_closed`; the tribunal can score the canonical view. Coverage floor makes the gap visible; aligning inputs is a pipeline change. |
| `fx_prices` ends 2026-02-09 | 211 forex picks remain unmeasurable until backfilled or retired. |

## Validation

```
python3 -m pytest tests/test_audit3_tribunal.py tests/test_audit3_expectancy_gates.py \
  tests/test_audit3_edge_hunt.py tests/test_audit3_selection_alpha.py \
  tests/test_forward_observations_ingest.py tests/test_audit3_cost_basis.py -q
# 109 passed
```

*Not investment advice. These changes make it harder to call something profitable; they do
not make anything profitable.*
