# Per-asset-class profitability programme — Implementation Plan (Part B, corrected)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans`. Steps use `- [ ]` checkboxes.
>
> **This file supersedes Part B of [`plans/2026-11-24-wire-excluded-cohort-summary.md`](plans/2026-11-24-wire-excluded-cohort-summary.md).** Part A of that file (the excluded-cohort wiring, Tasks 1–5) remains valid and should be executed as written. Part B there was drafted against an assumed schema; the real schema falsified it, and this file replaces it.

**Goal:** Make the per-class verdicts re-derivable and drift-guarded, so the settled programme tally can only move on measured evidence — and make visible how far each class is from the forward-evidence bar that INVESTABLE requires.

**Architecture:** The audit3 ledger already computes and stores a `verdict` per class. The job is therefore **not** to recompute verdicts, but to (a) independently re-derive them from the stored statistics as a consistency check, (b) pin them so silent drift fails a gate, and (c) measure the forward-evidence gap. Read-only over committed data; no database dependency.

**Tech Stack:** Python 3 stdlib (`json`, `argparse`, `pathlib`), pytest, GitHub Actions.

---

## Measured facts (read from the ledger, not assumed)

Source: [`docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json`](docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json).

1. The ledger has a top-level `classes` array starting at `:1554`. Each element is one asset class and **already contains `verdict` and `reasons`**.

2. The real per-class schema is:

| Field | Example (CRYPTO) | Line |
|---|---|---|
| `asset_class` | `"CRYPTO"` | `:1556` |
| `n` | `6926` | `:1557` |
| `required_n` | `917` | `:1558` |
| `wr`, `wr_ci` | `0.3939`, `[0.3824, 0.4054]` | `:1561` |
| `pf`, `pf_basis` | `0.7886`, `"net"` | `:1566` |
| `pf_cost_pct` | `0.0994` | `:1569` |
| `net_expectancy_pct` | `-0.4183` | `:1572` |
| `net_ci_pct` | `[-0.699, -0.1602]` | `:1573` |
| `net_ci_pct_2x` | `[-0.7984, -0.2595]` | `:1582` |
| `stress_2x_ok` | `false` | `:1586` |
| `split_half` | `{stable, first_half_mean, second_half_mean}` | `:1588` |
| `top_symbol_share` | `0.0858` | `:1601` |
| `top_source_share` | `0.5866` | `:1602` |
| `verdict` | `"KILL"` | `:1604` |
| `alpha_gate` | `{alpha_ci_lo, alpha_coverage_ok, status, passed}` | `:1624` |

3. **Fields I wrongly assumed and must not use:** `net_pf` (real name is `pf` with `pf_basis == "net"`), `net_2x_pf` (real signal is `stress_2x_ok` / `net_ci_pct_2x`), `split_half.h1_net_ci` (real names are `first_half_mean` / `second_half_mean`), `oos_folds_positive` and `top_date_share` (absent from class rows).

4. **A coverage gate already exists**: `alpha_gate.alpha_coverage_ok` (`:1628`) and `alpha_gate.status` (`:1629`). Do not build a second one.

5. The `classes` array holds **7** entries (CRYPTO, EQUITY, ETF, FOREX, BOND, COMMODITY, FUTURES), whereas the settled programme tally is stated over **14 rows**. These are different scopes — the 14-row tally is not the 7-row class array. **Reconciling that scope difference is a deliverable, not an assumption.**

6. Verdicts currently stored: CRYPTO `KILL` (`:1604`), EQUITY `WEAK` (`:1684`), ETF `WEAK`, FOREX `WEAK`, BOND `KILL`, COMMODITY `WEAK`, FUTURES `INSUFFICIENT_N` (`:2082`).

---

## Task B1: Ledger verdict auditor

**Files:**
- Create: `tools/class_verdict_audit.py`
- Test: `tests/test_class_verdict_audit.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_class_verdict_audit.py`. Fixtures mirror the real CRYPTO row shape from `:1555-1633`.

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.class_verdict_audit import rederive, audit  # noqa: E402


def row(**kw):
    """A class row shaped exactly like ledger classes[] entries."""
    base = {
        "asset_class": "TEST",
        "n": 6926,
        "required_n": 917,
        "wr": 0.3939,
        "pf": 0.7886,
        "pf_basis": "net",
        "net_expectancy_pct": -0.4183,
        "net_ci_pct": [-0.699, -0.1602],
        "net_ci_pct_2x": [-0.7984, -0.2595],
        "stress_2x_ok": False,
        "split_half": {"stable": False, "first_half_mean": -0.2871,
                       "second_half_mean": -0.5496},
        "top_symbol_share": 0.0858,
        "top_source_share": 0.5866,
        "verdict": "KILL",
        "alpha_gate": {"alpha_ci_lo": -0.9095, "alpha_coverage_ok": False,
                       "status": "unproven", "passed": False},
    }
    base.update(kw)
    return base


def test_insufficient_n_wins():
    assert rederive(row(n=37)) == "INSUFFICIENT_N"


def test_negative_ci_and_low_pf_is_kill():
    assert rederive(row()) == "KILL"


def test_negative_ci_but_pf_above_floor_is_weak():
    assert rederive(row(pf=0.95)) == "WEAK"


def test_positive_ci_but_fails_2x_stress():
    assert rederive(row(net_ci_pct=[0.10, 0.40], pf=1.2,
                        stress_2x_ok=False)) == "CANDIDATE_CAP_2X_COST"


def test_positive_ci_2x_ok_but_unstable_halves():
    assert rederive(row(net_ci_pct=[0.10, 0.40], pf=1.2, stress_2x_ok=True,
                        split_half={"stable": False,
                                    "first_half_mean": 0.2,
                                    "second_half_mean": -0.1})
                   ) == "CANDIDATE_CAP_HALVES"


def test_concentration_caps():
    assert rederive(row(net_ci_pct=[0.10, 0.40], pf=1.2, stress_2x_ok=True,
                        split_half={"stable": True,
                                    "first_half_mean": 0.2,
                                    "second_half_mean": 0.2},
                        top_symbol_share=0.61)) == "CANDIDATE_CAP_CONCENTRATION"


def test_clean_row_is_candidate_never_more():
    v = rederive(row(net_ci_pct=[0.10, 0.40], pf=1.2, stress_2x_ok=True,
                     split_half={"stable": True,
                                 "first_half_mean": 0.2,
                                 "second_half_mean": 0.2},
                     top_symbol_share=0.2))
    assert v == "CANDIDATE"
    assert v not in ("PROVEN", "INVESTABLE")


def test_audit_flags_a_mismatch():
    r = row(verdict="WEAK")          # stored says WEAK, stats say KILL
    out = audit([r])
    assert out[0]["stored"] == "WEAK"
    assert out[0]["rederived"] == "KILL"
    assert out[0]["match"] is False


def test_audit_passes_when_consistent():
    out = audit([row()])             # stored KILL, rederived KILL
    assert out[0]["match"] is True
```

- [ ] **Step 2: Run to confirm failure**

Run: `python3 -m pytest tests/test_class_verdict_audit.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.class_verdict_audit'`

- [ ] **Step 3: Implement**

Create `tools/class_verdict_audit.py`:

```python
#!/usr/bin/env python3
"""Independently re-derive each class verdict stored in the audit3 ledger.

The ledger already records a ``verdict`` per class. This tool recomputes that
verdict from the stored statistics using a documented ladder and reports any
disagreement. It exists so the programme tally cannot silently drift: a stored
verdict that no longer follows from its own numbers is a defect, not a result.

This does NOT produce a new verdict for the programme. It audits the existing
one. Backtest statistics can at best justify CANDIDATE; nothing here can grant
INVESTABLE.

Usage:
    python3 tools/class_verdict_audit.py
    python3 tools/class_verdict_audit.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = (ROOT / "docs" / "audit_review_2026-11-22" / "_raw"
          / "audit3_audit3_ledger.json")

MIN_N = 100
PF_KILL_FLOOR = 0.8
CONCENTRATION_CAP = 0.60


def _num(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def rederive(row: dict) -> str:
    """Recompute the ladder verdict from a class row's own statistics."""
    n = int(_num(row.get("n"), 0) or 0)
    if n < MIN_N:
        return "INSUFFICIENT_N"

    ci = row.get("net_ci_pct") or []
    lo = _num(ci[0]) if isinstance(ci, (list, tuple)) and ci else None
    pf = _num(row.get("pf"))

    if lo is None:
        return "UNMEASURABLE"
    if lo <= 0:
        return "KILL" if (pf or 0) < PF_KILL_FLOOR else "WEAK"

    if not row.get("stress_2x_ok"):
        return "CANDIDATE_CAP_2X_COST"

    halves = row.get("split_half") or {}
    if not halves.get("stable"):
        return "CANDIDATE_CAP_HALVES"

    if (_num(row.get("top_symbol_share"), 0) or 0) >= CONCENTRATION_CAP:
        return "CANDIDATE_CAP_CONCENTRATION"

    return "CANDIDATE"


def audit(rows) -> list[dict]:
    """Return one record per class comparing stored vs re-derived verdicts."""
    out = []
    for row in rows:
        stored = row.get("verdict")
        derived = rederive(row)
        out.append({
            "asset_class": row.get("asset_class") or "?",
            "n": row.get("n"),
            "pf": row.get("pf"),
            "net_ci_lo": (row.get("net_ci_pct") or [None])[0],
            "coverage_ok": ((row.get("alpha_gate") or {})
                            .get("alpha_coverage_ok")),
            "stored": stored,
            "rederived": derived,
            "match": stored == derived,
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
    rows = audit(ledger.get("classes") or [])
    if args.json:
        print(json.dumps(rows, indent=1))
        return 0
    bad = 0
    for r in rows:
        flag = "OK " if r["match"] else "DRIFT"
        if not r["match"]:
            bad += 1
        print(f"{flag:<6}{r['asset_class']:<12}n={r['n']:<7}"
              f"stored={r['stored']:<14}rederived={r['rederived']}")
    print(f"\n{len(rows)} classes, {bad} mismatch")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_class_verdict_audit.py -v`
Expected: `9 passed`

- [ ] **Step 5: Run against the real ledger**

Run: `python3 tools/class_verdict_audit.py`
Expected: 7 class lines plus a summary. **Record the actual mismatch count.** A mismatch is a real finding about the ledger, not a bug in the tool — do not "fix" the tool to agree with the ledger.

- [ ] **Step 6: Commit**

```bash
git add tools/class_verdict_audit.py tests/test_class_verdict_audit.py
git commit -m "feat(verdicts): audit stored class verdicts by re-deriving from their own stats

Read-only over the committed ledger. Asserts nothing about the programme
tally; reports DRIFT when a stored verdict no longer follows its numbers."
```

---

## Task B2: Pin the ledger's shape

**Files:**
- Create: `tests/test_ledger_class_schema.py`

The bug that produced this corrected plan was assuming field names. This test makes that class of assumption fail loudly.

- [ ] **Step 1: Write the schema test**

Create `tests/test_ledger_class_schema.py`:

```python
import json
from pathlib import Path

import pytest

LEDGER = (Path(__file__).resolve().parent.parent / "docs"
          / "audit_review_2026-11-22" / "_raw" / "audit3_audit3_ledger.json")

pytestmark = pytest.mark.skipif(not LEDGER.exists(),
                                reason="committed ledger not present")

REQUIRED = ["asset_class", "n", "pf", "pf_basis", "net_ci_pct",
            "net_ci_pct_2x", "stress_2x_ok", "split_half",
            "top_symbol_share", "verdict", "alpha_gate"]


@pytest.fixture(scope="module")
def classes():
    return json.loads(LEDGER.read_text(encoding="utf-8"))["classes"]


def test_classes_is_a_non_empty_list(classes):
    assert isinstance(classes, list) and classes


def test_every_class_row_has_the_fields_we_rely_on(classes):
    for row in classes:
        missing = [k for k in REQUIRED if k not in row]
        assert not missing, f"{row.get('asset_class')} missing {missing}"


def test_pf_basis_is_net_so_pf_is_comparable(classes):
    # If pf_basis ever becomes 'gross', the ladder's PF test silently changes
    # meaning. Fail loudly instead.
    for row in classes:
        assert row["pf_basis"] == "net", row.get("asset_class")


def test_split_half_uses_first_second_half_mean(classes):
    for row in classes:
        sh = row["split_half"]
        assert "first_half_mean" in sh and "second_half_mean" in sh


def test_alpha_gate_carries_a_coverage_flag(classes):
    for row in classes:
        assert "alpha_coverage_ok" in row["alpha_gate"], row.get("asset_class")
```

- [ ] **Step 2: Run it**

Run: `python3 -m pytest tests/test_ledger_class_schema.py -v`
Expected: `5 passed`. If a test fails, the ledger changed shape — **stop and re-measure before trusting any other task in this plan.**

- [ ] **Step 3: Commit**

```bash
git add tests/test_ledger_class_schema.py
git commit -m "test(ledger): pin the class row schema the verdict ladder depends on"
```

---

## Task B3: Reconcile 7 class rows against the 14-row tally

**Files:**
- Create: `reports/class_tally_reconciliation_2026-11-24.md`

This is the deliverable that stops the programme from confusing two different scopes.

- [ ] **Step 1: Measure both sides**

Run: `python3 tools/class_verdict_audit.py --json > /tmp/audit.json && python3 -c "
import json
a=json.load(open('/tmp/audit.json'))
print('classes[] rows:', len(a))
for r in a: print(' ', r['asset_class'], r['stored'])
import collections
print(collections.Counter(r['stored'] for r in a))
"`

- [ ] **Step 2: Count the ledger's other scopes**

Run: `python3 -c "
import json
l=json.load(open('docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json'))
for k in ('classes','segments','cells'):
    v=l.get(k)
    print(k, len(v) if isinstance(v,list) else 'absent')
"`

- [ ] **Step 3: Write the reconciliation**

Create `reports/class_tally_reconciliation_2026-11-24.md`. It must contain, all pasted from the runs above with no paraphrase:

```markdown
# Class tally reconciliation (2026-11-24)

## Two different scopes

- `classes[]` in the audit3 ledger: <N> rows, verdicts <Counter output>.
- The settled programme tally: `0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)`.

These are NOT the same population. <Explain, from the measured counts, what the
14 rows are drawn from — classes, segments, cells, or a mix — and therefore why
7 does not reconcile to 14 by arithmetic.>

## Measured verdicts per class

<paste the per-class lines>

## Does the settled tally still hold?

<State whether the measured class verdicts are consistent with the settled tally
under a stated mapping, or whether they contradict it. If they contradict it, do
NOT change the tally — record the contradiction and stop.>

## Mapping used

| Class verdict | Contributes to |
|---|---|
| `KILL`, `WEAK` | NOT_INVESTABLE |
| `INSUFFICIENT_N` | UNKNOWN |
| `CANDIDATE*` | candidate only; never INVESTABLE |
| nothing | INVESTABLE (no ladder output grants it) |
```

- [ ] **Step 4: Commit**

```bash
git add reports/class_tally_reconciliation_2026-11-24.md
git commit -m "docs(verdicts): reconcile 7 class rows against the 14-row programme tally"
```

---

## Task B4: Cost headroom per class, from real fields

**Files:**
- Create: `tools/class_cost_headroom.py`
- Create: `reports/cost_headroom_2026-11-24.md`
- Test: `tests/test_class_cost_headroom.py`

- [ ] **Step 1: Write the failing test**

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.class_cost_headroom import headroom  # noqa: E402


def test_headroom_is_the_ci_low_distance_to_break_even():
    # net_ci_pct low = -0.699 means the CI itself is below zero: no headroom.
    assert headroom({"net_ci_pct": [-0.699, -0.1602],
                     "pf_cost_pct": 0.0994})["headroom_pct"] == 0.0


def test_positive_ci_reports_distance_from_zero():
    out = headroom({"net_ci_pct": [0.25, 0.60], "pf_cost_pct": 0.0994})
    assert out["headroom_pct"] == 0.25


def test_cost_is_reported_alongside_headroom():
    out = headroom({"net_ci_pct": [0.25, 0.60], "pf_cost_pct": 0.0994})
    assert out["cost_pct"] == 0.0994
    assert out["cost_exceeds_headroom"] is False


def test_cost_exceeding_headroom_is_flagged():
    out = headroom({"net_ci_pct": [0.02, 0.30], "pf_cost_pct": 0.0994})
    assert out["cost_exceeds_headroom"] is True
```

- [ ] **Step 2: Run to confirm failure**

Run: `python3 -m pytest tests/test_class_cost_headroom.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

Create `tools/class_cost_headroom.py`:

```python
#!/usr/bin/env python3
"""How much cost a class can absorb before its measured edge reaches zero.

Reads only stored ledger statistics: ``net_ci_pct`` (already net of cost) and
``pf_cost_pct`` (the cost actually charged). The headroom is how far the CI's
lower bound sits above zero; if the measured cost already exceeds that headroom,
the class dies under any wider spread.

Usage:
    python3 tools/class_cost_headroom.py
    python3 tools/class_cost_headroom.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = (ROOT / "docs" / "audit_review_2026-11-22" / "_raw"
          / "audit3_audit3_ledger.json")


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def headroom(row: dict) -> dict:
    ci = row.get("net_ci_pct") or []
    lo = _num(ci[0]) if isinstance(ci, (list, tuple)) and ci else 0.0
    cost = _num(row.get("pf_cost_pct"))
    h = round(lo, 4) if lo > 0 else 0.0
    return {
        "headroom_pct": h,
        "cost_pct": round(cost, 4),
        "cost_exceeds_headroom": cost > h,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.ledger)
    if not path.exists():
        print(f"ledger not found: {path}", file=sys.stderr)
        return 2
    rows = json.loads(path.read_text(encoding="utf-8")).get("classes") or []
    out = [dict(asset_class=r.get("asset_class"), **headroom(r)) for r in rows]
    if args.json:
        print(json.dumps(out, indent=1))
        return 0
    for r in out:
        flag = " DIES" if r["cost_exceeds_headroom"] else ""
        print(f"{r['asset_class']:<12}headroom={r['headroom_pct']:<9}"
              f"cost={r['cost_pct']}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_class_cost_headroom.py -v`
Expected: `4 passed`

- [ ] **Step 5: Generate and write the report**

Run: `python3 tools/class_cost_headroom.py`

Create `reports/cost_headroom_2026-11-24.md` pasting that output verbatim, then naming explicitly every class with `cost_exceeds_headroom: true` — those die under any wider spread than the ledger already charged.

- [ ] **Step 6: Commit**

```bash
git add tools/class_cost_headroom.py tests/test_class_cost_headroom.py \
        reports/cost_headroom_2026-11-24.md
git commit -m "feat(cost): per-class headroom between measured edge and charged cost"
```

---

## Task B5: Forward-evidence readiness

**Files:**
- Create: `tools/forward_evidence_gap.py`
- Create: `reports/forward_readiness_2026-11-24.md`

This is the only route to INVESTABLE. From `tools/class_backtest_sweep.py:109`: *"Backtest data can never exceed CANDIDATE."*

- [ ] **Step 1: Implement the gap reporter**

Create `tools/forward_evidence_gap.py`:

```python
#!/usr/bin/env python3
"""Report how far each class is from the forward evidence INVESTABLE requires.

INVESTABLE cannot be granted by backtest (see class_backtest_sweep.py:109). It
needs forward rows whose out-of-sample CI stays positive after 2x cost. This
tool counts forward observations per class and reports the shortfall against a
threshold, so the gap is measured rather than assumed.

Forward rows are read from a JSONL file if present. If it is absent, every
class is reported at zero and the tool exits 3 — a measured absence, not an
error to be hidden.

Usage:
    python3 tools/forward_evidence_gap.py
    python3 tools/forward_evidence_gap.py --path reports/forward_observations.jsonl
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


def count_rows(path: Path) -> Counter:
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
    counts = count_rows(path)
    if not counts:
        print(f"no forward observations at {path}", file=sys.stderr)
        print("Every class is at 0 forward rows, so INVESTABLE is unreachable "
              "until forward evidence accumulates.", file=sys.stderr)
        return 3
    for cls, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        gap = max(0, args.threshold - n)
        print(f"{cls:<14}{n:>7}  " + ("READY" if gap == 0 else f"needs {gap}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it**

Run: `python3 tools/forward_evidence_gap.py`
Expected: a table, **or** exit `3` with the explicit absence message. Exit 3 is a legitimate measured finding. Record whichever occurs.

- [ ] **Step 3: Write the readiness report**

Create `reports/forward_readiness_2026-11-24.md` with the verbatim output and one unambiguous sentence, in this form:

> As of 2026-11-24, **\<N\>** classes have \>=100 forward observations. No class can be INVESTABLE while the backtest ladder caps out at CANDIDATE, so the count of INVESTABLE classes is structurally 0 regardless of how many backtests are run.

If `N = 0`, say so plainly. Do not soften it and do not propose another backtest as the remedy.

- [ ] **Step 4: Commit**

```bash
git add tools/forward_evidence_gap.py reports/forward_readiness_2026-11-24.md
git commit -m "feat(verdicts): measure the forward-evidence gap to INVESTABLE"
```

---

## Task B6: Drift gate

**Files:**
- Create: `tools/verdict_drift_gate.py`
- Create: `tests/test_verdict_drift_gate.py`
- Create: `.github/workflows/class-verdict-gate.yml`
- Create: `reports/verdict_baseline.json` (generated, never hand-written)

- [ ] **Step 1: Write the failing test**

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.verdict_drift_gate import compare  # noqa: E402


def test_no_change_passes():
    ok, msg = compare({"A": "KILL"}, {"A": "KILL"})
    assert ok and msg == "no drift"


def test_silent_change_fails_and_names_the_class():
    ok, msg = compare({"A": "KILL"}, {"A": "CANDIDATE"})
    assert not ok
    assert "A" in msg and "KILL" in msg and "CANDIDATE" in msg


def test_new_class_is_a_note_not_a_failure():
    ok, msg = compare({"A": "KILL"}, {"A": "KILL", "B": "WEAK"})
    assert ok
    assert "B" in msg


def test_vanished_class_is_a_note_not_a_failure():
    ok, msg = compare({"A": "KILL", "B": "WEAK"}, {"A": "KILL"})
    assert ok
    assert "B" in msg
```

- [ ] **Step 2: Run to confirm failure**

Run: `python3 -m pytest tests/test_verdict_drift_gate.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

Create `tools/verdict_drift_gate.py`:

```python
#!/usr/bin/env python3
"""Fail when a class verdict changes without the change being announced.

The programme has had verdicts move when the ledger refreshed. This gate pins
the stored verdicts to a baseline file and fails on any change to a class that
already existed. A newly appearing class, or one that disappears, is reported
as a note so a scope change does not masquerade as a verdict flip.

Usage:
    python3 tools/verdict_drift_gate.py --baseline reports/verdict_baseline.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.class_verdict_audit import LEDGER  # noqa: E402


def compare(baseline: dict, current: dict) -> tuple[bool, str]:
    problems, notes = [], []
    for cls, was in baseline.items():
        now = current.get(cls)
        if now is None:
            notes.append(f"{cls} disappeared")
        elif now != was:
            problems.append(f"{cls}: {was} -> {now}")
    for cls in current:
        if cls not in baseline:
            notes.append(f"{cls} is new ({current[cls]})")
    if problems:
        return False, "verdict changed: " + "; ".join(problems)
    return True, " ".join(notes) if notes else "no drift"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--ledger", default=str(LEDGER))
    args = ap.parse_args(argv)

    base_path, ledger_path = Path(args.baseline), Path(args.ledger)
    for p in (base_path, ledger_path):
        if not p.exists():
            print(f"missing input: {p}", file=sys.stderr)
            return 2

    baseline = json.loads(base_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    current = {r.get("asset_class"): r.get("verdict")
               for r in ledger.get("classes") or []}
    ok, msg = compare(baseline, current)
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_verdict_drift_gate.py -v`
Expected: `4 passed`

- [ ] **Step 5: Generate the baseline from measurement**

Run:

```bash
python3 -c "
import json
l=json.load(open('docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json'))
b={r['asset_class']:r['verdict'] for r in l['classes']}
json.dump(b, open('reports/verdict_baseline.json','w'), indent=1, sort_keys=True)
print(b)
"
```

Never hand-edit this file. It must be the ledger's own stored verdicts, or it records an assumption.

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
      - 'tools/class_verdict_audit.py'
      - 'tools/verdict_drift_gate.py'
      - 'reports/verdict_baseline.json'

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
      - name: Install test deps
        run: python -m pip install --quiet pytest pyyaml
      - name: Unit tests
        run: |
          python -m pytest tests/test_class_verdict_audit.py \
            tests/test_class_cost_headroom.py \
            tests/test_verdict_drift_gate.py \
            tests/test_ledger_class_schema.py -q
      - name: Schema pin
        run: python -c "import pytest,sys; sys.exit(pytest.main(['tests/test_ledger_class_schema.py','-q']))"
      - name: Verdict drift
        run: python tools/verdict_drift_gate.py --baseline reports/verdict_baseline.json
      - name: Stored vs re-derived consistency
        run: python tools/class_verdict_audit.py
```

- [ ] **Step 7: Validate the YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/class-verdict-gate.yml')); print('YAML OK')"`
Expected: `YAML OK`. If PyYAML is missing, install it rather than skipping — a workflow that does not parse is a silent failure.

- [ ] **Step 8: Commit**

```bash
git add .github/workflows/class-verdict-gate.yml tools/verdict_drift_gate.py \
        tests/test_verdict_drift_gate.py reports/verdict_baseline.json
git commit -m "feat(verdicts): daily gate failing on unannounced verdict drift"
```

---

## Execution order

1. **B1** — the auditor. Everything else uses it.
2. **B2** — schema pin. Cheap, and it is the guard against the exact error this plan corrected.
3. **B3** — reconciliation report. The headline deliverable: 7 vs 14, measured.
4. **B4** — cost headroom. Read-only, no blockers.
5. **B5** — forward gap. Expect exit 3; that is the finding.
6. **B6** — the gate. Depends on B1 being green.

## Blocker handling

| Situation | Action |
|---|---|
| Ledger file absent | Stop. Write one line per task noting `ledger absent: <path>`. Fabricating verdicts is forbidden. |
| `pf_basis` is not `"net"` | Stop at B2 — the PF comparison changes meaning. Report it. |
| `stress_2x_ok` missing | B1 returns `CANDIDATE_CAP_2X_COST` conservatively; record the missing field. |
| `forward_observations.jsonl` absent | Expected. Tor B5 records `0 forward rows` as the result. |
| PyYAML unavailable | Install it; do not skip YAML validation. |
| Huge `cells` array makes the ledger slow to parse | Read `classes` only; never load the whole file twice in one command. |

## Programme guardrails

- **The settled tally does not move because a document says so.** Only measured output from B1/B3 plus forward rows from B5 can justify a change.
- **No backtest can produce INVESTABLE.** `class_backtest_sweep.py:109` states it; B1 enforces it structurally.
- **Never cite a field without reading it.** This plan exists because six assumed field names were wrong. B2 pins them.
- **Every report states provenance:** which ledger, which run, which date.
