# Wire excluded-cohort measurement into the dashboard payload — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the coverage bias numeric by emitting a `coverage.excluded_summary` object in `dashboard_data.json` that reports the size and realised PnL of the cohort the dashboard drops, so the retained book stops being un-auditable.

**Architecture:** Keep the logic pure and testable in [`audit_trail/excluded_cohorts.py`](audit_trail/excluded_cohorts.py) by adding one thin wrapper (`coverage_excluded_summary`) over the existing `summarize_excluded`. The generator then makes a single-line call at payload-assembly time, passing the already-in-scope `auto_expired` list. Nothing is recomputed, no row counts change, and the change is strictly additive to the payload.

**Tech Stack:** Python 3 stdlib only (`collections`, `typing`), pytest, GitHub Actions (`ci-tests.yml`).

---

## Measured context (why this plan looks the way it does)

These are verified facts from the current checkout, not from the briefing:

1. `summarize_excluded()` exists at [`audit_trail/excluded_cohorts.py:31`](audit_trail/excluded_cohorts.py:31) and returns `{"total_excluded": int, "by_reason": {...}}`.
2. It keys each row on `exclude_reason` / `_exclude_reason` / `"unknown"` — **it does not read `_auto_expired`**. The generator stamps `p["_auto_expired"] = True` at [`audit_trail/dashboard_generator.py:9787`](audit_trail/dashboard_generator.py:9787). Therefore `reason="auto_expired"` **must** be passed explicitly, or 100% of rows land in the `unknown` bucket and the metric is silently wrong.
3. `auto_expired` is constructed at [`audit_trail/dashboard_generator.py:9784`](audit_trail/dashboard_generator.py:9784) inside `generate()`, which spans `:14707–18688`. The payload literal is at [`audit_trail/dashboard_generator.py:17120`](audit_trail/dashboard_generator.py:17120) — **same function, so `auto_expired` is already in scope**. No plumbing, no new parameters.
4. The payload has **no** top-level `coverage` key today (only `summary.auto_expired_excluded`, an integer at `:17157`). So adding `coverage` cannot collide.
5. The bare name `excluded_summary` *does* already exist — but as a differently-shaped dict (`{"too_stale": 43}`) inside [`alpha_engine/data/smart_picks_monitor.json:12`](alpha_engine/data/smart_picks_monitor.json:12). That is a different document from `dashboard_data.json`, so no conflict; still, the note text below states the shape explicitly so a future reader does not confuse the two.
6. `tests/**` is already listed in the CI path filter at [`.github/workflows/ci-tests.yml:25`](.github/workflows/ci-tests.yml:25) and `:44`. **A new file under `tests/` is gated with no workflow edit.** The briefing's "add a ci-tests gate" step is unnecessary — verified, not assumed.
7. [`tools/excluded_cohorts_report.py:67`](tools/excluded_cohorts_report.py:67) already names this exact work as the fix: *"Wire `excluded_cohorts.summarize_excluded()` into `dashboard_generator` at the auto-expired split to make the bias numeric."*

### Scope boundary (deliberate, YAGNI)

Only the **auto-expired** cohort is measured. The other exclusion sites (`invalid_closed_count`, `mirror_dupe_count`) do not have their rows in hand at payload time — only counters — so they are **out of scope** and the payload says so via `"scope": "auto_expired_only"`. Do not attempt to reconstruct them.

---

## Task 1: Pure payload shaper

**Files:**
- Test: `tests/test_excluded_cohorts_coverage.py`
- Modify: [`audit_trail/excluded_cohorts.py`](audit_trail/excluded_cohorts.py) (append one function after `summarize_excluded`, which ends at `:89`)

- [ ] **Step 1: Write the failing test**

Create `tests/test_excluded_cohorts_coverage.py` with exactly this content:

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audit_trail.excluded_cohorts import coverage_excluded_summary  # noqa: E402


def R(sym, pnl=None, cls="CRYPTO", dirn="LONG", **kw):
    d = {"symbol": sym, "pnl_pct": pnl, "asset_class": cls, "direction": dirn}
    d.update(kw)
    return d


def test_empty_cohort_reports_zero_not_null():
    out = coverage_excluded_summary([])
    assert out["total"] == 0
    assert out["n_with_pnl"] == 0
    assert out["by_reason"] == {}
    assert out["scope"] == "auto_expired_only"


def test_reason_is_forced_onto_every_row():
    # The generator stamps `_auto_expired`, which summarize_excluded cannot see.
    # If reason were not forced, these would land under "unknown".
    rows = [R("A", 1.0, _auto_expired=True), R("B", -2.0, _auto_expired=True)]
    out = coverage_excluded_summary(rows)
    assert list(out["by_reason"]) == ["auto_expired"]
    assert out["by_reason"]["auto_expired"]["n"] == 2
    assert out["total"] == 2


def test_total_and_n_with_pnl_are_both_exposed():
    rows = [R("A", 1.0), R("B", 3.0), R("C", None)]
    out = coverage_excluded_summary(rows)
    assert out["total"] == 3
    assert out["n_with_pnl"] == 2
    assert out["by_reason"]["auto_expired"]["mean_pnl_pct"] == 2.0


def test_missing_pnl_yields_null_win_rate_not_zero():
    out = coverage_excluded_summary([R("A", None)])
    assert out["by_reason"]["auto_expired"]["win_rate"] is None
    assert out["n_with_pnl"] == 0


def test_note_states_the_measurement_is_partial():
    out = coverage_excluded_summary([R("A", 1.0)])
    assert "auto-expired" in out["note"]
    assert "not the full" in out["note"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_excluded_cohorts_coverage.py -v`
Expected: FAIL with `ImportError: cannot import name 'coverage_excluded_summary'`

- [ ] **Step 3: Write minimal implementation**

Append to the end of [`audit_trail/excluded_cohorts.py`](audit_trail/excluded_cohorts.py) (after line 135, the end of `split_auto_expired`):

```python
def coverage_excluded_summary(
    rows: Iterable[Mapping[str, Any]],
    reason: str = "auto_expired",
) -> dict[str, Any]:
    """Payload-sized view of one excluded cohort, for ``coverage.excluded_summary``.

    ``reason`` is applied to every row. The dashboard generator stamps rows with
    ``_auto_expired``, which :func:`summarize_excluded` does not read, so passing
    the reason explicitly is what keeps this out of the ``unknown`` bucket.

    Covers ONE cohort only. The mirror-duplicate and invalid-row exclusions are
    counters by payload-assembly time, not rows, so they are not included here.
    """
    summary = summarize_excluded(rows, reason=reason)
    by_reason = summary["by_reason"]
    return {
        "scope": f"{reason}_only",
        "total": summary["total_excluded"],
        "n_with_pnl": sum(b["n_with_pnl"] for b in by_reason.values()),
        "by_reason": by_reason,
        "note": (
            "Cohort of auto-expired picks dropped before metrics. Reports the "
            "full auto-expired cohort only, not the full set of rows the build "
            "excludes. Compare its mean against the retained book to size "
            "selection risk."
        ),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_excluded_cohorts_coverage.py -v`
Expected: `5 passed`

- [ ] **Step 5: Verify the existing suite still passes**

Run: `python3 -m pytest tests/test_excluded_cohorts.py tests/test_excluded_cohorts_report.py tests/test_excluded_cohorts_coverage.py -v`
Expected: all pass (16 tests: 7 + 4 + 5). The append is non-breaking because no existing symbol changed.

- [ ] **Step 6: Commit**

```bash
git add audit_trail/excluded_cohorts.py tests/test_excluded_cohorts_coverage.py
git commit -m "feat(coverage): add coverage_excluded_summary payload shaper

Forces the reason key so _auto_expired rows are counted under
auto_expired rather than silently falling into the unknown bucket."
```

---

## Task 2: Emit the key in the dashboard payload

**Files:**
- Modify: [`audit_trail/dashboard_generator.py`](audit_trail/dashboard_generator.py) — add import, then insert the `coverage` block into the payload literal
- Test: `tests/test_dashboard_coverage_wiring.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_dashboard_coverage_wiring.py` with exactly this content. It is a source-scan test: importing `dashboard_generator` pulls in the whole scanner stack, so we assert on the source contract instead of executing it.

```python
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(HERE, "audit_trail", "dashboard_generator.py")


def _src():
    with open(GEN, encoding="utf-8") as fh:
        return fh.read()


def test_imports_the_shaper():
    assert "coverage_excluded_summary" in _src()


def test_payload_carries_a_coverage_key():
    src = _src()
    # The key must appear as a payload-level literal, not only inside summary.
    assert re.search(r'^\s{8}"coverage": \{', src, re.M), \
        "no top-level coverage block in the payload literal"


def test_coverage_block_is_fed_the_auto_expired_list():
    src = _src()
    assert "coverage_excluded_summary(auto_expired)" in src, \
        "coverage block is not wired to the auto_expired cohort"


def test_auto_expired_is_built_before_the_payload():
    src = _src()
    build_at = src.index("auto_expired.append(p)")
    payload_at = src.index('"coverage": {')
    assert build_at < payload_at, "auto_expired built after payload; out of scope"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_dashboard_coverage_wiring.py -v`
Expected: FAIL on `test_imports_the_shaper` (and the coverage-key tests).

- [ ] **Step 3: Add the import**

In [`audit_trail/dashboard_generator.py`](audit_trail/dashboard_generator.py), find the existing `audit_trail` import block near the top (the module already imports from `audit_trail.*`). Add:

```python
from audit_trail.excluded_cohorts import coverage_excluded_summary
```

If the file instead aliases the package, use the same style as its neighbours — do not invent a new import convention.

- [ ] **Step 4: Insert the payload block**

In the payload literal, immediately after the `"summary": { ... },` block closes at [`audit_trail/dashboard_generator.py:17227`](audit_trail/dashboard_generator.py:17227) and before `"systems": systems,` at `:17228`, insert exactly:

```python
        # Coverage honesty (2026-11-24): the auto-expired cohort is dropped
        # before every metric, so its size and realised PnL were unmeasurable
        # from the payload. summarize_excluded() had no caller in the
        # generator; tools/excluded_cohorts_report.py flagged the gap.
        # Additive only — no existing key or count changes.
        "coverage": {
            "excluded_summary": coverage_excluded_summary(auto_expired),
        },
```

Resulting indentation must be 8 spaces for the key, matching `"summary"` and `"systems"`.

- [ ] **Step 5: Run the wiring tests**

Run: `python3 -m pytest tests/test_dashboard_coverage_wiring.py -v`
Expected: `4 passed`

- [ ] **Step 6: Prove the file still parses and the append is syntactically clean**

Run: `python3 -c "import py_compile; py_compile.compile('audit_trail/dashboard_generator.py', doraise=True)" && echo OK`
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add audit_trail/dashboard_generator.py tests/test_dashboard_coverage_wiring.py
git commit -m "feat(coverage): emit coverage.excluded_summary in dashboard payload

Wires the previously-uncalled summarize_excluded() into the generator at
the auto-expired split. Additive: no existing payload key changes."
```

---

## Task 3: Surface the new key in the audit tool

**Files:**
- Modify: [`tools/excluded_cohorts_report.py`](tools/excluded_cohorts_report.py)
- Test: `tests/test_excluded_cohorts_report.py` (add one test, do not alter existing ones)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_excluded_cohorts_report.py`. That file already imports `json`, `subprocess`, `sys` and defines `HERE = Path(__file__).resolve().parent.parent` at module level (`:1-6`), so reuse those — do NOT add an `os` import.

```python
def test_reports_payload_coverage_block_when_present(tmp_path):
    p = tmp_path / "payload.json"
    p.write_text(json.dumps({
        "coverage": {
            "excluded_summary": {
                "scope": "auto_expired_only",
                "total": 42,
                "n_with_pnl": 0,
                "by_reason": {"auto_expired": {"n": 42}},
                "note": "partial",
            }
        }
    }))
    r = subprocess.run([sys.executable,
                        str(HERE / "tools" / "excluded_cohorts_report.py"),
                        "--payload", str(p), "--coverage"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "42" in r.stdout
    assert "auto_expired_only" in r.stdout


def test_coverage_flag_returns_3_when_block_absent(tmp_path):
    p = tmp_path / "payload.json"
    p.write_text(json.dumps({"picks": {"recent_closed": []}}))
    r = subprocess.run([sys.executable,
                        str(HERE / "tools" / "excluded_cohorts_report.py"),
                        "--payload", str(p), "--coverage"],
                       capture_output=True, text=True)
    assert r.returncode == 3
    assert "no coverage.excluded_summary" in r.stderr
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_excluded_cohorts_report.py::test_reports_payload_coverage_block_when_present -v`
Expected: FAIL — `unrecognized arguments: --coverage` and exit code 2.

- [ ] **Step 3: Implement the flag**

In [`tools/excluded_cohorts_report.py`](tools/excluded_cohorts_report.py), add the argument next to the existing `--json` at `:49`:

```python
    ap.add_argument("--coverage", action="store_true",
                    help="print the payload's coverage.excluded_summary block")
```

Then, immediately after `payload = json.loads(...)` at `:52`, insert:

```python
    if args.coverage:
        block = (payload.get("coverage") or {}).get("excluded_summary")
        if not isinstance(block, dict):
            print("payload has no coverage.excluded_summary "
                  "(generator not wired for this artifact)", file=sys.stderr)
            return 3
        print(f"scope  {block.get('scope')}")
        print(f"total  {block.get('total')}")
        print(f"n_with_pnl  {block.get('n_with_pnl')}")
        for _k, _v in (block.get("by_reason") or {}).items():
            print(f"  {_k:<20}{_v.get('n'):>7}")
        return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_excluded_cohorts_report.py -v`
Expected: all pass, including the pre-existing 4.

- [ ] **Step 5: Commit**

```bash
git add tools/excluded_cohorts_report.py tests/test_excluded_cohorts_report.py
git commit -m "feat(coverage): add --coverage flag to excluded_cohorts_report

Prints the new payload block, or says plainly when the artifact predates it."
```

---

## Task 4: Verify against a real payload

**Files:** none modified — this is a measurement gate.

- [ ] **Step 1: Run the whole affected suite**

Run: `python3 -m pytest tests/test_excluded_cohorts.py tests/test_excluded_cohorts_report.py tests/test_excluded_cohorts_coverage.py tests/test_dashboard_coverage_wiring.py -v`
Expected: all pass.

- [ ] **Step 2: Check whether a fresh payload exists locally**

Run: `ls -l audit_dashboard/data/dashboard_data.json 2>/dev/null || echo NO_LOCAL_PAYLOAD`

- [ ] **Step 3a: If a payload exists, inspect it for the key**

Run: `python3 tools/excluded_cohorts_report.py --payload audit_dashboard/data/dashboard_data.json --coverage`
Expected either:
- `exit 3` with `payload has no coverage.excluded_summary (generator not wired for this artifact)` — correct and expected, because the artifact predates the change; record this as the finding, **do not** call it a failure, or
- `scope auto_expired_only` plus a non-zero `total` — the measurement is live.

- [ ] **Step 3b: If no payload exists, prove the shaper on synthetic data**

Run:

```bash
python3 -c "
from audit_trail.excluded_cohorts import coverage_excluded_summary
print(coverage_excluded_summary([{'symbol':'BTCUSDT','pnl_pct':0,'direction':'LONG','_auto_expired':True}]))
"
```

Expected: a dict with `scope='auto_expired_only'`, `total=1`, `by_reason={'auto_expired': ...}`.

- [ ] **Step 4: Record the measured result**

Write the actual command output into the doc created in Task 5, under `## Verification`. Do not paraphrase — paste the exit code and the first line.

---

## Task 5: Document the change

**Files:**
- Create: `updates/2026-11-24-coverage-excluded-summary-wiring.md`

Per this workspace's AGENTS.md rule (*"Every code fix you make MUST be documented in a `.MD` file… No undocumented fixes"*).

- [ ] **Step 1: Write the doc**

Create `updates/2026-11-24-coverage-excluded-summary-wiring.md`:

```markdown
# Coverage excluded-summary wiring (2026-11-24)

## What was broken

`audit_trail.excluded_cohorts.summarize_excluded()` had no caller in
`audit_trail/dashboard_generator.py`. The dashboard dropped the auto-expired
cohort before computing every metric, but never published that cohort's size or
realised PnL, so nobody reading `dashboard_data.json` could tell whether the
retained book was flattered by the exclusions. `tools/excluded_cohorts_report.py`
already flagged this and named the fix.

## What changed

- `audit_trail/excluded_cohorts.py`: added `coverage_excluded_summary()`, a thin
  payload shaper over `summarize_excluded()`. It forces `reason="auto_expired"`
  because the generator stamps `_auto_expired` — a key `summarize_excluded()`
  does not read — so without the explicit reason every row would be counted
  under `unknown`.
- `audit_trail/dashboard_generator.py`: added a top-level
  `coverage.excluded_summary` object to the payload, built from the
  `auto_expired` list already in scope at payload-assembly time.
- `tools/excluded_cohorts_report.py`: added `--coverage` to print the new block,
  and to say plainly when an artifact predates the wiring.

## Scope

Auto-expired cohort only. The mirror-duplicate and invalid-row exclusions exist
only as counters by payload time, so they are not measured here and the payload
says so (`scope: auto_expired_only`).

## Verification

<paste the literal output of Task 4 Step 3a/3b and the pytest summary here>
```

- [ ] **Step 2: Commit the doc with the fix**

```bash
git add updates/2026-11-24-coverage-excluded-summary-wiring.md
git commit -m "docs(coverage): record excluded-summary wiring and its verification"
```

---

## Additive-proof checklist (run before declaring done)

- [ ] `python3 -m pytest tests/test_excluded_cohorts.py tests/test_excluded_cohorts_report.py tests/test_excluded_cohorts_coverage.py tests/test_dashboard_coverage_wiring.py -q` — green.
- [ ] `python3 -c "import py_compile; py_compile.compile('audit_trail/dashboard_generator.py', doraise=True); py_compile.compile('audit_trail/excluded_cohorts.py', doraise=True); py_compile.compile('tools/excluded_cohorts_report.py', doraise=True)"` — no output.
- [ ] `grep -n "summary.auto_expired_excluded" audit_trail/dashboard_generator.py` still present — the pre-existing integer was not replaced.
- [ ] The diff touches exactly four files: `audit_trail/excluded_cohorts.py`, `audit_trail/dashboard_generator.py`, `tools/excluded_cohorts_report.py`, and the tests/doc. `git diff --stat` confirms no data files and no workflow files.
- [ ] Multi-leg orders: none in scope.

---

## Out of scope — do not do these here

- Editing `.github/workflows/ci-tests.yml`. `tests/**` is already a trigger path (`:25`, `:44`); a new test file is gated for free. Adding a `tools/` path entry is a separate concern.
- Backfilling `mirror_dupe_count` / `invalid_closed_count` rows into the summary.
- Changing any verdict, tally, or the settled `0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN` programme state.
- Pushing to a branch containing other authors' commits (AGENTS.md Safety rule).

---
---

# Part B — SUPERSEDED. Do not execute this section.

> **Use [`plans/2026-11-24-class-profitability-programme.md`](plans/2026-11-24-class-profitability-programme.md) instead.**
>
> This Part B was drafted against an assumed ledger schema. Reading
> [`docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:1555-1633`](docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:1555) falsified
> six field names (`net_pf` is really `pf`; `net_2x_pf` does not exist —
> the signal is `stress_2x_ok`; `split_half.h1_net_ci` is really
> `first_half_mean`/`second_half_mean`; `oos_folds_positive` and
> `top_date_share` are absent from class rows) and showed that every class row
> already carries its own `verdict` plus an `alpha_gate.alpha_coverage_ok` flag.
> Tasks 6–12 below would have re-derived data that already exists, using keys
> that do not exist. **Part A (Tasks 1–5) is unaffected and remains correct.**
>
> ---
>
> Everything from here to the end of this file is retained only as a record of
> the falsified draft. Do not follow it.

# Part B (falsified draft) — Path to proven profitability per asset class

**Premise correction first.** The settled programme tally is `0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN` across 14 rows. This part does **not** attempt to overturn that tally by argument. It makes the tally *re-derivable from code* so that any future change is forced through a measured gate instead of a claim. If a class is going to become INVESTABLE, it must clear a fixed ladder in [`tools/class_backtest_sweep.py:108`](tools/class_backtest_sweep.py:108) **and** a forward window — never a re-reading of the same closed rows.

**The ladder is already written down.** From [`class_backtest_sweep.py:108-122`](tools/class_backtest_sweep.py:108), in order:

| Condition | Verdict |
|---|---|
| `n < 100` | `INSUFFICIENT_N` |
| `net_ci_lo <= 0` and `net_pf < 0.8` | `KILL` |
| `net_ci_lo <= 0` otherwise | `WEAK` |
| `net_2x_pf < 1.0` | `CANDIDATE_CAP_2X_COST` |
| `halves` not both positive | `CANDIDATE_CAP_HALVES` |
| `top_symbol_share >= 0.60` or `top_date_share >= 0.35` | `CANDIDATE_CAP_CONCENTRATION` |
| `oos_folds_positive < total-1` | `CANDIDATE_CAP_WALKFORWARD` |
| else | `CANDIDATE` |

The docstring at `:109` is the key constraint: **`Backtest data can never exceed CANDIDATE.`** So no amount of backtesting can produce INVESTABLE. That is the structural reason the tally sits at 0, and why the programme must spend its effort on *forward* evidence, not more backtests.

### Known blockers and the workaround for each

| Blocker | Evidence | Workaround |
|---|---|---|
| B1 The sweep needs live MySQL | [`class_backtest_sweep.py:135-146`](tools/class_backtest_sweep.py:135) imports `pymysql` + `tools.db_env.get_stocks_creds()` | **Do not block on the DB.** Run the sweep from the committed ledger sample at `docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json`, which already carries per-class `net_ci_pct`, `net_ci_pct_2x`, `split_half`, and `wr_ci` (`:1554-2106`). Add a `--from-ledger` path so the ladder can be evaluated with zero DB access. |
| B2 Costs are per-class and easy to forget | `slip = ledger["conventions"]["slippage_pct_by_class"]`, `default_cost = 0.12` at `:140-141` | Always read cost from the ledger's `conventions` block. Never hardcode. |
| B3 No forward evidence exists for most classes | `INSUFFICIENT_N` at `n < 100`; FOREX n=264 and BOND n=37 in the cited ranking | Treat "insufficient n" as the *finding*, not a nuisance. Report it as `UNKNOWN` per the settled tally. |
| B4 Verdicts drift when the ledger refreshes | Ledger is regenerated by the hourly dashboard build | Stamp every verdict with `ledger_generated_at` + `repo_sha` and re-derive on a schedule; fail the run if a class's verdict changed without a data change. |
| B5 Prior briefing asserted artifacts that do not exist | `CONTEST/`, `COVERAGE_LIMITS.md`, `check_excluded_summary.py`, `verification-tests.yml` all absent | Verify every path with a tool call before citing it. This is now a standing rule in this plan. |

---

## Task 6: Offline ladder evaluator (unblocks B1)

**Files:**
- Create: `tools/class_verdict_from_ledger.py`
- Test: `tests/test_class_verdict_from_ledger.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_class_verdict_from_ledger.py`:

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.class_verdict_from_ledger import verdict_for_class  # noqa: E402


def cls(**kw):
    base = {"n": 500, "net_ci_pct": [-0.10, 0.30], "net_pf": 1.2,
            "net_ci_pct_2x": [-0.25, 0.10], "net_2x_pf": 1.05,
            "split_half": {"h1_net_ci": [0.0, 0.2], "h2_net_ci": [0.0, 0.2]},
            "top_symbol_share": 0.2, "top_date_share": 0.1,
            "oos_folds_positive": 4, "oos_folds_total": 5}
    base.update(kw)
    return base


def test_insufficient_n_wins_first():
    assert verdict_for_class(cls(n=37)) == "INSUFFICIENT_N"


def test_negative_ci_low_pf_is_kill():
    assert verdict_for_class(cls(net_ci_pct=[-0.9, -0.1], net_pf=0.71)) == "KILL"


def test_negative_ci_ok_pf_is_weak():
    assert verdict_for_class(cls(net_ci_pct=[-0.2, 0.1], net_pf=0.95)) == "WEAK"


def test_dies_at_double_cost():
    assert verdict_for_class(cls(net_2x_pf=0.98)) == "CANDIDATE_CAP_2X_COST"


def test_dies_on_split_half():
    assert verdict_for_class(
        cls(split_half={"h1_net_ci": [0.1, 0.3], "h2_net_ci": [-0.2, 0.05]})
    ) == "CANDIDATE_CAP_HALVES"


def test_dies_on_concentration():
    assert verdict_for_class(cls(top_symbol_share=0.61)) == "CANDIDATE_CAP_CONCENTRATION"


def test_dies_on_walkforward():
    assert verdict_for_class(cls(oos_folds_positive=2)) == "CANDIDATE_CAP_WALKFORWARD"


def test_clean_row_is_candidate_and_never_more():
    v = verdict_for_class(cls())
    assert v == "CANDIDATE"
    # Structural: backtest cannot produce anything above CANDIDATE.
    assert v != "PROVEN"
    assert v != "INVESTABLE"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_class_verdict_from_ledger.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.class_verdict_from_ledger'`

- [ ] **Step 3: Write the implementation**

Create `tools/class_verdict_from_ledger.py`:

```python
#!/usr/bin/env python3
"""Evaluate the fixed verdict ladder from a committed audit3 ledger.

Why this exists: ``tools/class_backtest_sweep.py`` needs live MySQL to rebuild
per-class stats. The ledger already carries the same statistics as a snapshot
(``classes[].net_ci_pct``, ``net_ci_pct_2x``, ``split_half``, ``wr_ci``), so the
ladder can be applied with zero database access. That removes the DB as a
blocker for re-deriving the per-class verdicts.

The ladder is a COPY of ``class_backtest_sweep.verdict_for``. It is duplicated
rather than imported because that module imports pymysql at call time and this
one must run in a bare CI container. ``tests/test_class_verdict_parity.py``
keeps the two in lockstep.

Usage:
    python3 tools/class_verdict_from_ledger.py
    python3 tools/class_verdict_from_ledger.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = (ROOT / "docs" / "audit_review_2026-11-22" / "_raw"
          / "audit3_audit3_ledger.json")


def _lo(ci):
    """Lower bound of a two-element CI, or None when absent/malformed."""
    if isinstance(ci, (list, tuple)) and len(ci) == 2:
        try:
            return float(ci[0])
        except (TypeError, ValueError):
            return None
    return None


def verdict_for_class(row: dict) -> str:
    """Apply the fixed ladder. Mirrors class_backtest_sweep.verdict_for()."""
    n = int(row.get("n") or 0)
    if n < 100:
        return "INSUFFICIENT_N"
    if (_lo(row.get("net_ci_pct")) or -1.0) <= 0:
        return "KILL" if float(row.get("net_pf") or 0) < 0.8 else "WEAK"
    if float(row.get("net_2x_pf") or 0) < 1.0:
        return "CANDIDATE_CAP_2X_COST"
    halves = row.get("split_half") or {}
    h1 = _lo(halves.get("h1_net_ci"))
    h2 = _lo(halves.get("h2_net_ci"))
    if h1 is None or h2 is None or h1 <= 0 or h2 <= 0:
        return "CANDIDATE_CAP_HALVES"
    if float(row.get("top_symbol_share") or 0) >= 0.60:
        return "CANDIDATE_CAP_CONCENTRATION"
    if float(row.get("top_date_share") or 0) >= 0.35:
        return "CANDIDATE_CAP_CONCENTRATION"
    pos = int(row.get("oos_folds_positive") or 0)
    tot = int(row.get("oos_folds_total") or 0)
    if tot and pos < max(1, tot - 1):
        return "CANDIDATE_CAP_WALKFORWARD"
    return "CANDIDATE"


def evaluate(ledger: dict) -> list[dict]:
    out = []
    for row in ledger.get("classes") or []:
        cls = row.get("asset_class") or row.get("class") or "?"
        out.append({
            "asset_class": cls,
            "n": row.get("n"),
            "net_pf": row.get("net_pf"),
            "verdict": verdict_for_class(row),
        })
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.ledger)
    if not path.exists():
        print(f"ledger not found: {path}", file=sys.stderr)
        return 2
    ledger = json.loads(path.read_text(encoding="utf-8"))
    rows = evaluate(ledger)
    if args.json:
        print(json.dumps(rows, indent=1))
    else:
        for r in rows:
            print(f"{r['asset_class']:<14}{str(r['n']):>7}{str(r['net_pf']):>9}"
                  f"  {r['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_class_verdict_from_ledger.py -v`
Expected: `8 passed`

- [ ] **Step 5: Prove it runs with no database**

Run: `python3 tools/class_verdict_from_ledger.py`
Expected: one line per class. If it exits `2` with `ledger not found`, that is a real finding — record it and skip to Task 7 Step 4, which recovers the stats another way.

- [ ] **Step 6: Commit**

```bash
git add tools/class_verdict_from_ledger.py tests/test_class_verdict_from_ledger.py
git commit -m "feat(verdicts): evaluate the per-class ladder from the committed ledger

Removes the live-MySQL dependency from re-deriving class verdicts. The
ladder is duplicated from class_backtest_sweep so this runs in a bare
CI container."
```

---

## Task 7: Keep the two ladders in lockstep

**Files:**
- Create: `tests/test_class_verdict_parity.py`

This is the guard against the exact failure mode that has bitten this programme repeatedly: two copies of a rule drifting apart silently.

- [ ] **Step 1: Write the parity test**

Create `tests/test_class_verdict_parity.py`:

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.class_verdict_from_ledger import verdict_for_class as from_ledger  # noqa: E402


def _sweep_verdict(r):
    """Import lazily: class_backtest_sweep touches pymysql only inside main()."""
    from tools.class_backtest_sweep import verdict_for
    return verdict_for({
        "n": r["n"],
        "net_ci_lo": r["net_ci_pct"][0],
        "net_pf": r["net_pf"],
        "net_2x_pf": r["net_2x_pf"],
        "halves_positive": (r["split_half"]["h1_net_ci"][0] > 0
                            and r["split_half"]["h2_net_ci"][0] > 0),
        "top_symbol_share": r["top_symbol_share"],
        "top_date_share": r["top_date_share"],
        "wf": {"oos_folds_positive": r["oos_folds_positive"],
               "oos_folds_total": r["oos_folds_total"]},
    })


BASE = {"n": 500, "net_ci_pct": [-0.10, 0.30], "net_pf": 1.2,
        "net_2x_pf": 1.05,
        "split_half": {"h1_net_ci": [0.05, 0.2], "h2_net_ci": [0.05, 0.2]},
        "top_symbol_share": 0.2, "top_date_share": 0.1,
        "oos_folds_positive": 4, "oos_folds_total": 5}


CASES = [
    {"n": 37},
    {"net_ci_pct": [-0.9, -0.1], "net_pf": 0.71},
    {"net_ci_pct": [-0.2, 0.1], "net_pf": 0.95},
    {"net_2x_pf": 0.98},
    {"split_half": {"h1_net_ci": [0.1, 0.3], "h2_net_ci": [-0.2, 0.05]}},
    {"top_symbol_share": 0.61},
    {"top_date_share": 0.40},
    {"oos_folds_positive": 2},
    {},
]


def test_ladders_agree_on_every_case():
    for patch in CASES:
        r = dict(BASE)
        r.update(patch)
        assert from_ledger(r) == _sweep_verdict(r), f"diverged on {patch}"
```

- [ ] **Step 2: Run it**

Run: `python3 -m pytest tests/test_class_verdict_parity.py -v`
Expected: `1 passed`. If it fails, the two ladders have genuinely diverged — fix `class_verdict_from_ledger.verdict_for_class` to match the sweep, since the sweep is the authority.

- [ ] **Step 3: Commit**

```bash
git add tests/test_class_verdict_parity.py
git commit -m "test(verdicts): pin ledger ladder in lockstep with the sweep ladder"
```

---

## Task 8: Re-derive the tally and diff it against the settled one

**Files:**
- Create: `reports/class_tally_2026-11-24.md`

- [ ] **Step 1: Produce the measured verdicts**

Run: `python3 tools/class_verdict_from_ledger.py --json > /tmp/verdicts.json && python3 -c "
import json,collections
rows=json.load(open('/tmp/verdicts.json'))
print(collections.Counter(r['verdict'] for r in rows))
for r in rows: print(r['asset_class'], r['n'], r['verdict'])
"`

- [ ] **Step 2: Compare against the settled tally**

The settled programme state is `0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)`. The ladder has no `INVESTABLE` or `UNKNOWN` token, so map explicitly and **state the mapping in the report**:

- `CANDIDATE*` → contributes to a *candidate count*, never INVESTABLE.
- `KILL`, `WEAK` → `NOT_INVESTABLE`.
- `INSUFFICIENT_N` → `UNKNOWN`.

- [ ] **Step 3: Write the report**

Create `reports/class_tally_2026-11-24.md` with this skeleton, filling every `<...>` from the actual command output — **no placeholder may survive**:

```markdown
# Per-class verdict re-derivation (2026-11-24)

**Method:** fixed ladder from `tools/class_backtest_sweep.py:108`, applied
offline to the committed ledger by `tools/class_verdict_from_ledger.py`.
No live database. No new backtest.

## Measured

<paste the Counter line and the per-class table verbatim>

## Mapping to the settled tally

| Ladder verdict | Programme token |
|---|---|
| `CANDIDATE*` | candidate only, never INVESTABLE |
| `KILL`, `WEAK` | NOT_INVESTABLE |
| `INSUFFICIENT_N` | UNKNOWN |

Settled tally (unchanged, quoted for comparison): `0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)`.

## Agreement or divergence

<state exactly which classes disagree with the settled tally and why>

## What would have to be true for a class to become INVESTABLE

It must clear the ladder **and** accumulate >=100 forward rows in which the
out-of-sample CI lower bound stays above zero after 2x cost. The ladder itself
cannot grant INVESTABLE — `class_backtest_sweep.py:109` says backtest data can
never exceed CANDIDATE.
```

- [ ] **Step 4: Commit**

```bash
git add reports/class_tally_2026-11-24.md
git commit -m "docs(verdicts): re-derive per-class tally from ledger and diff vs settled"
```

---

## Task 9: Cost sensitivity — where the edge dies

**Files:**
- Create: `reports/cost_sensitivity_2026-11-24.md`

The PROVEIT work already established that commission drag is the dominant term at small account sizes ($5/trade ≈ 34.1% annual drag at $300 vs 1.0% at $10,000). Task 9 makes that per-class and reproducible here.

- [ ] **Step 1: Read the per-class costs**

Run: `python3 -c "
import json
l=json.load(open('docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json'))
print(json.dumps(l['conventions']['slippage_pct_by_class'], indent=1))
"`

- [ ] **Step 2: Compute per-class break-even cost**

Run:

```bash
python3 -c "
import json
l=json.load(open('docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json'))
slip=l['conventions']['slippage_pct_by_class']
for r in l['classes']:
    cls=r.get('asset_class') or r.get('class')
    ci=r.get('net_ci_pct') or [None,None]
    if ci[0] is None: continue
    cost=slip.get(cls,0.12)
    # headroom = how much the round-turn cost could rise before CI low hits 0
    print(f'{cls:<13} cost={cost:<6} ci_lo={ci[0]:<8} headroom={round(-ci[0],4)}')
"
```

- [ ] **Step 3: Write the report**

Create `reports/cost_sensitivity_2026-11-24.md` stating, per class: measured round-turn cost from the ledger, the CI lower bound, and the headroom in percentage points before the edge dies. Classes whose `headroom` is smaller than their own cost are the first to collapse under a real broker's spread — name them explicitly.

- [ ] **Step 4: Commit**

```bash
git add reports/cost_sensitivity_2026-11-24.md
git commit -m "docs(cost): per-class break-even headroom before the edge dies"
```

---

## Task 10: Coverage gate on the verdict

**Files:**
- Modify: `tools/class_verdict_from_ledger.py`
- Test: `tests/test_class_verdict_from_ledger.py` (append)

A verdict computed on 24% of a class's population is not a verdict. The CRYPTO figure in the review repo was 24.2% coverage — the headline class is mostly unmeasured.

- [ ] **Step 1: Append the failing test**

```python
def test_low_coverage_downgrades_verdict_to_unknown():
    row = cls()
    out = verdict_for_class_with_coverage(row, covered=240, universe=1000)
    assert out["verdict"] == "UNKNOWN_LOW_COVERAGE"
    assert out["coverage_pct"] == 24.0


def test_adequate_coverage_keeps_ladder_verdict():
    out = verdict_for_class_with_coverage(cls(), covered=800, universe=1000)
    assert out["verdict"] == "CANDIDATE"
```

- [ ] **Step 2: Run it to confirm failure**

Run: `python3 -m pytest tests/test_class_verdict_from_ledger.py -v`
Expected: FAIL with `NameError: verdict_for_class_with_coverage`.

- [ ] **Step 3: Implement the wrapper**

Add to `tools/class_verdict_from_ledger.py`:

```python
MIN_COVERAGE_PCT = 50.0


def verdict_for_class_with_coverage(row: dict, covered, universe) -> dict:
    """Ladder verdict, downgraded to UNKNOWN when the class is thinly covered.

    A class measured on a small slice of its population cannot support a
    confident verdict either way; saying UNKNOWN is more honest than WEAK.
    """
    try:
        cov = round(float(covered) / float(universe) * 100, 2) if universe else 0.0
    except (TypeError, ValueError, ZeroDivisionError):
        cov = 0.0
    base = verdict_for_class(row)
    verdict = base if cov >= MIN_COVERAGE_PCT else "UNKNOWN_LOW_COVERAGE"
    return {"verdict": verdict, "ladder_verdict": base, "coverage_pct": cov}
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_class_verdict_from_ledger.py tests/test_class_verdict_parity.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add tools/class_verdict_from_ledger.py tests/test_class_verdict_from_ledger.py
git commit -m "feat(verdicts): downgrade to UNKNOWN below 50 percent class coverage"
```

---

## Task 11: Wire the whole thing into a gate

**Files:**
- Create: `.github/workflows/class-verdict-gate.yml`
- Create: `tools/tally_regression_gate.py`
- Test: `tests/test_tally_regression_gate.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tally_regression_gate.py`:

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.tally_regression_gate import compare  # noqa: E402


def test_identical_tallies_pass():
    ok, msg = compare({"A": "KILL", "B": "WEAK"}, {"A": "KILL", "B": "WEAK"})
    assert ok and msg == ""


def test_silent_verdict_change_fails():
    ok, msg = compare({"A": "KILL"}, {"A": "CANDIDATE"})
    assert not ok
    assert "A" in msg and "KILL" in msg and "CANDIDATE" in msg


def test_new_class_is_reported_not_failed():
    ok, msg = compare({"A": "KILL"}, {"A": "KILL", "B": "WEAK"})
    assert ok
    assert "B" in msg
```

- [ ] **Step 2: Run to confirm failure**

Run: `python3 -m pytest tests/test_tally_regression_gate.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

Create `tools/tally_regression_gate.py`:

```python
#!/usr/bin/env python3
"""Fail when a class verdict changes without the underlying data changing.

The programme has repeatedly published a verdict, then had it silently move
because the ledger refreshed. This gate pins verdicts to a baseline file and
reports any drift, so a change must be deliberate and reviewed.

Usage:
    python3 tools/tally_regression_gate.py --baseline reports/tally_baseline.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.class_verdict_from_ledger import evaluate, LEDGER  # noqa: E402


def compare(baseline: dict, current: dict) -> tuple[bool, str]:
    """Return (ok, message). Silent changes fail; new classes only warn."""
    problems, notes = [], []
    for cls, was in baseline.items():
        now = current.get(cls)
        if now is None:
            notes.append(f"{cls}: disappeared from the ledger")
        elif now != was:
            problems.append(f"{cls}: {was} -> {now}")
    for cls in current:
        if cls not in baseline:
            notes.append(f"{cls}: new class ({current[cls]})")
    if problems:
        return False, "verdict changed: " + "; ".join(problems)
    return True, " ".join(notes)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--ledger", default=str(LEDGER))
    args = ap.parse_args(argv)

    baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    current = {r["asset_class"]: r["verdict"] for r in evaluate(ledger)}
    ok, msg = compare(baseline, current)
    print(msg or "no drift")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_tally_regression_gate.py -v`
Expected: `3 passed`

- [ ] **Step 5: Create the baseline from measured state**

Run: `python3 tools/class_verdict_from_ledger.py --json | python3 -c "
import json,sys
rows=json.load(sys.stdin)
json.dump({r['asset_class']:r['verdict'] for r in rows},
          open('reports/tally_baseline.json','w'), indent=1)
print('baseline written from measured ledger')
"`

Do **not** hand-write `tally_baseline.json`. It must be the tool's own output, or it records an assumption instead of a measurement.

- [ ] **Step 6: Create the workflow**

Create `.github/workflows/class-verdict-gate.yml`:

```yaml
name: Class Verdict Gate

on:
  schedule:
    - cron: '17 6 * * *'
  workflow_dispatch:
  pull_request:
    paths:
      - 'docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json'
      - 'tools/class_verdict_from_ledger.py'
      - 'reports/tally_baseline.json'

permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  gate:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Unit tests
        run: |
          python -m pytest tests/test_class_verdict_from_ledger.py \
            tests/test_class_verdict_parity.py \
            tests/test_tally_regression_gate.py -q
      - name: Verdict drift gate
        run: python tools/tally_regression_gate.py --baseline reports/tally_baseline.json
```

- [ ] **Step 7: Validate the YAML parses**

Run: `python3 -c "
import yaml
yaml.safe_load(open('.github/workflows/class-verdict-gate.yml'))
print('YAML OK')
"` (if PyYAML is absent: `python3 -c "import json,sys; print('skip: no PyYAML')"` and note it)

- [ ] **Step 8: Commit**

```bash
git add .github/workflows/class-verdict-gate.yml tools/tally_regression_gate.py \
        tests/test_tally_regression_gate.py reports/tally_baseline.json
git commit -m "feat(verdicts): daily gate that fails on unannounced verdict drift"
```

---

## Task 12: Forward-evidence counter (the only route to INVESTABLE)

**Files:**
- Create: `tools/forward_rows_by_class.py`
- Create: `reports/forward_readiness_2026-11-24.md`

B4 and the `:109` docstring mean INVESTABLE requires forward rows, not backtest. This task measures how far each class is from the `n >= 100` forward threshold so the gap is visible rather than assumed.

- [ ] **Step 1: Write the counter**

Create `tools/forward_rows_by_class.py`:

```python
#!/usr/bin/env python3
"""Count forward-observation rows per asset class from the forward ledger.

INVESTABLE cannot be granted by backtest (class_backtest_sweep.py:109). It
needs forward rows whose out-of-sample CI stays positive after 2x cost. This
tool reports how far each class is from the n>=100 forward threshold.

Usage:
    python3 tools/forward_rows_by_class.py
    python3 tools/forward_rows_by_class.py --path reports/forward_observations.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "reports" / "forward_observations.jsonl"
THRESHOLD = 100


def count(path: Path) -> Counter:
    c: Counter = Counter()
    if not path.exists():
        return c
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        cls = str(row.get("asset_class") or row.get("class") or "UNKNOWN").upper()
        c[cls] += 1
    return c


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", default=str(DEFAULT))
    ap.add_argument("--threshold", type=int, default=THRESHOLD)
    args = ap.parse_args(argv)

    path = Path(args.path)
    c = count(path)
    if not c:
        print(f"no forward observations at {path}", file=sys.stderr)
        print("Every class is at 0 forward rows; INVESTABLE is unreachable "
              "until forward evidence accumulates.", file=sys.stderr)
        return 3
    for cls, n in sorted(c.items(), key=lambda kv: -kv[1]):
        gap = max(0, args.threshold - n)
        state = "READY" if gap == 0 else f"needs {gap} more"
        print(f"{cls:<14}{n:>7}  {state}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it**

Run: `python3 tools/forward_rows_by_class.py`
Expected either a per-class table, or exit `3` with the explicit message that forward evidence is absent. **Exit 3 is a legitimate measured finding**, not a failure — record it.

- [ ] **Step 3: Write the readiness report**

Create `reports/forward_readiness_2026-11-24.md` recording, per class, forward row count vs the 100 threshold, and stating plainly: *"0 classes have forward evidence sufficient to support INVESTABLE on 2026-11-24"* if that is what the run shows. Do not soften it.

- [ ] **Step 4: Commit**

```bash
git add tools/forward_rows_by_class.py reports/forward_readiness_2026-11-24.md
git commit -m "feat(verdicts): measure forward rows per class against the 100-row gate"
```

---

## Part B execution order and blocker handling

Run in this order. Each task is independently committable, so a blocker in one does not stop the rest.

1. **Task 6** — removes the MySQL blocker (B1). If the ledger path is missing, stop and find the ledger before continuing; every later task reads it.
2. **Task 7** — locks the duplicated ladder. Do not skip; this is the anti-drift guard.
3. **Task 8** — produces the measured tally diff. This is the headline deliverable.
4. **Task 9** — cost headroom. Needs only the ledger; no blockers.
5. **Task 10** — coverage downgrade. Needs the per-class covered/universe numbers; if the ledger lacks them, record `coverage unavailable` per class rather than inventing a value.
6. **Task 11** — the gate. Depends on 6 and 7 being green.
7. **Task 12** — forward readiness. Expected to report a wide gap; that is the finding.

**If the ledger is absent or malformed:** stop Part B at Task 8 Step 1, write `reports/class_tally_2026-11-24.md` containing only the measured failure (`ledger missing: <path>`), and do not fabricate verdicts. A missing input is a result.

**If `pymysql` is unavailable:** irrelevant to Part B — nothing after Task 6 touches the database by design. That is the point of Task 6.

---

## Programme-level guardrails

- **Never** change `0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN` by editing a document. It may only move when Task 8's measured output plus Task 12's forward rows justify it, and the diff must show the evidence.
- **Never** cite a path in a report without having listed or read it in the same session. The prior briefing's five absent artifacts are the reason this rule exists.
- **Never** let a backtest produce `INVESTABLE`. `class_backtest_sweep.py:109` forbids it structurally; if a future edit removes that line, that edit is the bug.
- Every report must state its provenance: which ledger, which `repo_sha`, which run date.
