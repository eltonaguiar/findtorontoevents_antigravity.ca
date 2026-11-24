# audit2 per-class verdict panel — Phases A, B, C

Date: 2026-11-20
Status: implemented in the working tree. **NOT deployed, NOT pushed, NOT seen in a browser.**

---

## Phase A — one predicate for "is this row performance-scored"

**What was broken.** The tribunal had two ways to decide which rows count for
performance scoring, and they did not agree. Its fallback path used a weaker
3-value status deny-list, while the canonical view used the fuller
`_NON_PERFORMANCE_EXITS` set. Two code paths, two definitions of the same
question — so the tribunal and /audit could score different rows and quietly
disagree about the same ledger.

**What changed.** One predicate, `is_performance_scored_row()`, in
[`alpha_engine/resolved_closed_view.py`](../../alpha_engine/resolved_closed_view.py).
The tribunal calls it in both modes. The standalone fallback keeps working but
now raises a `RuntimeWarning` and applies identical logic, instead of silently
differing from the canonical path.

**How it was verified.**
- Test written first and observed failing: 13 failures, and **no ImportError** —
  the failures were behavioural, not a missing symbol.
- 15 new tests for the predicate.
- 34 tribunal tests, 17 closed_view tests.
- **0 verdict / 0 n / 0 magnitude changes across 170 cells** on identical input.

### The correction (read this before quoting any number)

An earlier figure of **4,968 disagreeing rows** was circulated. It was an
**overstatement** and should not be repeated.

The predicate only drops a NULL-`exit_reason` row when that row *also* lacks a
close marker *and* a terminal status. On the 3,500-row export slice, all 23
NULL/UNKNOWN exit rows were **kept** via `closed_at`. The real disagreement is
therefore far smaller than 4,968.

The live ~47,669-row canonical set was **never measured**. This host is denied
access to `ejaguiar1_stocks`:

```
Access denied ... 1045
```

So the no-op claim is supported by the 170-cell comparison on identical input
and by the 3,500-row slice — not by a measurement of the live canonical set.

---

## Phase B — per-class verdict panel on /audit2

**What was built.** A per-class panel that reports **verdicts, deliberately not
signals**. An audit surface that emits signals stops being independent from the
thing it audits; a verdict ("this class is distinguishable from luck, or is
not") can be checked against the ledger, while a signal would compete with it.

Components:
- `tools/build_audit2_per_class_panel.py` — joins `class_rollup()` to the
  ledger's classes/cells.
- An additive `per_class_verdicts` key on the ledger payload. Nothing existing
  is moved or renamed.
- A new section in `audit2.html`.
- `renderPerClass()` in `audit2.js`.
- A workflow step in `.github/workflows/audit3-ledger.yml`.
- `tests/test_audit2_per_class_panel.py` — 10 tests, including an
  exact-equality reconcile against `class_rollup()` and a static guard that the
  JS performs no arithmetic (the numbers arrive pre-computed; the browser only
  formats them).

---

## Phase C — wiring the dead validator

**What was broken.** `alpha_engine/audit3_edge_hunt.py` does real work —
alpha-vs-beta separation, point-in-time gate replay, power analysis — and was
referenced by **zero** workflow files. It enforced nothing. A validator nobody
runs is documentation, not a gate.

**What changed.** Two steps added to `.github/workflows/audit3-ledger.yml`,
directly after the "Build audit3 ledger" step:

1. **Edge hunt (alpha vs beta, PIT replay) — advisory**, with
   `continue-on-error: true`. It runs
   `python3 alpha_engine/audit3_edge_hunt.py --picks /tmp/audit3/dashboard_data.json --out /tmp/audit3/edge_hunt.json`,
   mirrors the `set +e` / `rc=$?` idiom of the selection-alpha step, and emits an
   `::error` annotation (not a failure) when the report is missing or empty.
2. **Upload edge hunt report**, `if: always()`, `actions/upload-artifact@v4`,
   artifact name `audit3-edge-hunt`.

**Position.** The module reads the live snapshot at `/tmp/audit3/dashboard_data.json`,
not the ledger, so it would work earlier too. It sits after the ledger build so it
reads exactly the snapshot the ledger was scored from, and so a ledger failure
still leaves an edge-hunt report for that run.

**Why `continue-on-error`.** Its outputs do not exist yet. Gating a pipeline on
something that has never run reliably is how a pipeline goes red for no reason.

**Why an artifact and not `audit_dashboard/data/`.** Nothing consumes the report
yet. Adding an unconsumed file to the `[skip ci]` commit would widen the
commit/deploy loop surface for no reader. An artifact is durable and inspectable
without touching the published tree.

**Untouched.** `require_alpha` and every existing gate are unchanged. A COMS
message reports `audit3-ledger.yml` is GREEN again after `require_alpha` landed
and says not to re-fix it — this change is purely additive.

**How it was verified.**
- YAML parses: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/audit3-ledger.yml'))"`
  — PyYAML 6.0.1 is available here. The workflow loads to 14 steps, with the edge
  hunt at index 8 and the artifact upload at index 9.
- The module actually executes in this environment:
  `python3 alpha_engine/audit3_edge_hunt.py --help` prints its usage and exits 0.
  A full run against the local 3,500-row snapshot
  (`audit_dashboard/data/dashboard_data.json`) exited 0 and wrote a 6,660-byte
  `audit3.edge_hunt.v1` report with `n_rows=3500`. Its headline was
  "A point-in-time gate beats its own past: prior-record filter discriminates
  without leakage". Real output from that run included a CRYPTO beta section
  (long +0.787%, short -0.287%, residual selection alpha +0.400%), 249 mirror
  pairs (mean sum +2.679%, corr -0.186), and a power section where every class
  was UNDERPOWERED (e.g. CRYPTO n=2070 vs needed 144,794 at the pre-declared
  0.05%/trade MDE).
- Test slice: `python3 -m pytest tests/ -q -k "audit2 or audit3 or closed_view or per_class or performance_scored"`
  → **269 passed, 6 skipped, 7108 deselected** in 12.02s. The 6 skips are
  unrelated (missing `arch` package, removed helpers).

---

## What remains unverified

Stated plainly, because none of these were observed:

- **The live no-op claim.** The ~47,669-row canonical set was never measured —
  this host cannot reach `ejaguiar1_stocks` (`Access denied ... 1045`). The
  no-op is shown on identical input (170 cells) and on the 3,500-row slice only.
- **Browser rendering of the panel.** `renderPerClass()` has never been seen
  running. Its correctness rests on tests, not on observation.
- **Actual deployment.** Nothing here was deployed or pushed.
- **The canonical-sidecar rows path.** The workflow passes `--rows` only when
  `/tmp/audit3/resolved_closed_picks_net.json` was fetched; that path has not
  been exercised end-to-end.
- **Responsive behaviour of the 8-column table.** Not tested at any viewport
  width.
- **The edge-hunt steps in CI.** They were validated locally (YAML parse, module
  execution); no workflow run was triggered, so the artifact upload itself is
  unproven.
