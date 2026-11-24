# 2026-11-20 — Restore green `CI Tests` on `main` (audit3 alpha-scope, 6 red tests)

**Goal advanced:** #1 (audit performance surface) — a red `CI Tests` gate on `main`
blocks every other PR in the queue from merging, including all trading-quality work.

## What was broken

`main` (base `7ab67511177`) had **6 failing tests across 3 files**, all in the
`/audit3` selection-alpha kill-tribunal surface:

| File | Failing tests |
|---|---|
| `tests/test_selection_alpha_coverage.py` | `test_by_class_is_published`, `test_bar_coverage_is_published`, `test_existing_keys_still_published` |
| `tests/test_audit3_g8_defaults.py` | `test_g8_demotes_a_strategy_cell_proven_only_by_class_alpha`, `test_g8_accepts_same_scope_strategy_alpha` |
| `tests/test_audit3_falsifiers.py` | `test_zero_selection_alpha_cannot_prove_a_cell` |

These were **two orthogonal bugs**, not one — which is why neither in-flight branch
alone could turn the suite green:

### Bug A — `ALPHA_PASSTHROUGH_KEYS` was 7 keys, the consumer test locks 11

`alpha_engine/audit3_tribunal.py` on `main` defined:

```python
ALPHA_PASSTHROUGH_KEYS = ("covered", "n_universe", "overall", "generated_at", "schema", "source", "note")
```

The coverage test asserts `by_class`, `by_slice`, `bar_coverage`, and `missing` are
also published. A prior hotfix (PR #972) added the *symbol* — enough to kill the
`ImportError: cannot import name 'ALPHA_PASSTHROUGH_KEYS'` — but not enough to pass.

### Bug B — `apply_selection_alpha_gate` was the pre-G8 contract

On `main` the function signature was `def apply_selection_alpha_gate(bucket, alpha) -> None`.
Four consequences, each matching one failing assertion:

1. Returns `None` → tests doing `summary["demoted"]` raise
   `TypeError: 'NoneType' object is not subscriptable`.
2. Only looks up `by_class` / `by_slice`; the finest scope must be `by_strategy`.
3. **Fails open** — early-returns when lookup dicts are empty, so a cell backed by
   *zero* alpha survives as `PROVEN_T2` (the `assert 'PROVEN_T2' != 'PROVEN_T2'` fail).
4. Writes `alpha_gate={alpha_ci_lo, passed}` with **no `"status"` key**, so
   `cell["alpha_gate"]["status"] == "unproven"` raises `KeyError`.

## What changed

Single file, `alpha_engine/audit3_tribunal.py` (+94 / −42):

1. **`ALPHA_PASSTHROUGH_KEYS` widened to 11 keys** —
   adds `by_class`, `by_slice`, `bar_coverage`, `missing`.
2. **`demote_proven_without_alpha()` + `apply_selection_alpha_gate()` replaced** with the
   scope-aware G8 implementation:
   - returns a summary dict `{applied, tested, demoted, scopes}`;
   - lookup ladder `by_strategy` → `by_slice` → `by_class`, recording the resolved
     scope in `alpha_gate["scope"]` (`strategy` / `class_proxy` / `class`);
   - **fails closed** — a cell with no qualifying alpha is demoted, never left PROVEN_T2;
   - uses existing `ALPHA_MIN_N = 20` / `ALPHA_MIN_COVERAGE = 0.50` constants.
3. **`alpha_gate["status"]`** added — `"proven"` / `"unproven"`.

## How it was verified

Differential test on the same machine, same base commit, patch off vs on
(`-m "not integration and not network"`, matching the CI filter):

```
bare main failures:    75
patched failures:      69
=== FIXED by patch (present bare, gone patched) ===
tests/test_audit3_falsifiers.py::test_zero_selection_alpha_cannot_prove_a_cell
tests/test_audit3_g8_defaults.py::test_g8_accepts_same_scope_strategy_alpha
tests/test_audit3_g8_defaults.py::test_g8_demotes_a_strategy_cell_proven_only_by_class_alpha
tests/test_selection_alpha_coverage.py::test_bar_coverage_is_published
tests/test_selection_alpha_coverage.py::test_by_class_is_published
tests/test_selection_alpha_coverage.py::test_existing_keys_still_published
=== NEWLY BROKEN by patch (must be empty) ===
(empty)
```

- **Exactly the 6 tests real CI reported** are fixed — confirmed against
  `gh run view 44649438938 --log-failed | grep FAILED`, which listed precisely these 6.
- **Zero regressions.**
- Targeted run on the 3 failing files + 3 sibling audit3 files: **77 passed, 0 failed (3.95s)**,
  reproduced on two independent bases (`80c116ae361` and `7ab67511177`).
- 8 downstream modules importing `audit3_tribunal`: **72 passed**.
- `python3 -m py_compile alpha_engine/audit3_tribunal.py` → OK.
- `python3 -m alpha_engine.audit3_tribunal --help` → OK.
- `require_alpha` pass-through from the earlier hotfix is preserved (2 occurrences).

The 69 remaining local failures are **pre-existing and environmental** (missing gitignored
data fixtures such as `combined_book/data/kfrench/`, absent optional packages). They do
not appear in CI — the CI check-run listed only the 6 above.

## Known follow-up (not fixed here)

`demote_proven_without_alpha()` lands **defined but not called** — the call site at
~line 1753 invokes `apply_selection_alpha_gate()` and discards its summary. This is
deliberate scope-limiting (keep the diff to the green-CI fix), but it must be resolved
before this matures: either wire the summary into the `require_alpha` missing-sidecar
path so demotions are logged/attributed, or delete the dead helper.

## Reproducer

```bash
python3 -m pytest tests/test_selection_alpha_coverage.py tests/test_audit3_falsifiers.py \
  tests/test_audit3_g8_defaults.py tests/test_audit3_tribunal.py \
  tests/test_audit3_expectancy_gates.py tests/test_audit3_selection_alpha.py -q
```
