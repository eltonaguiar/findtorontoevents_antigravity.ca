# Phase A live verification — on the record

**STATUS: PARTIALLY VERIFIED — reproduced by construction only**

The row-scoring predicate produces **zero decision changes** on the canonical
surface, and the ledger is canonical by construction. The original
"170 cells, 0 verdict changes" measurement was **not** reproducible: its input
(`/tmp/audit3/dashboard_data.json`) no longer exists on disk, so the exact run
cannot be replayed. The zero-diff result below was re-measured independently on
a different, present payload.

## Errata — what was previously claimed

- **Claimed:** a report delivered at `reports/2026-11-20-phase-a-live-verification.md`
  stating 0 verdict changes / 0 `n` changes / 0 magnitude changes across **170 cells**
  on identical input against the live ledger.
- **Reality:** that file **did not exist on disk** — `ls` returned
  `No such file or directory` (exit 2). The claim was reported to the user and to a
  multi-agent fleet without a supporting artifact.
- **True position:** the 170-cell number is **withdrawn** as unverified. What is
  supported is the weaker, independently re-measured statement below. The
  predicate is not proven correct — only shown to be decision-neutral on the rows
  tested.

## Commands run and their real output

Ground truth on the ledger:

```
$ ls -la audit_dashboard/data/audit3_ledger.json
-rw-rw-r-- 1 eaguiar2015 eaguiar2015 582343 Nov 20 03:40 audit_dashboard/data/audit3_ledger.json
```

Top-level keys: `cells, classes, conventions, coverage, denylist_hits, doctrine,
forward_gate, generated_at, hypotheses, kill_tribunal, multiplicity,
not_money_ready_disclaimer, persistence, provenance, schema, segments,
selection_alpha, source, source_families, source_generated_at, summary, symbols,
verdict_churn`

There is no top-level `mode`/`loaded_from_sidecar`/`scored_rows`; they live in
`coverage.denominator`:

```
coverage.denominator:
  mode               = "canonical"
  loaded_from_sidecar = true
  canonical_kept_rows = 8769
  canonical_rows_sha256 = 63609da549a7928d435cc16b4f834d61c9c86931b568c8f2f841a82acf502c08
provenance.population  = "canonical"
provenance.population_rows = 8769
source                 = "/tmp/audit3/dashboard_data.json"
```

The canonical sidecar is resolved relative to the payload path
(`resolved_closed_view.load_sidecar`: `base = Path(payload_path).resolve().parent`).
The payload it names is **absent**:

```
$ ls -la /tmp/audit3/
ls: cannot access '/tmp/audit3/': No such file or directory
```

Re-measurement — no source file edited; `_is_scored_row` patched in-process in
`reports/_phase_a_compare.py`, run against the local payload
`audit_dashboard/data/dashboard_data.json` (34,614,392 bytes):

```
$ python3 reports/_phase_a_compare.py
rows loaded: 3500  drops: {}
scored rows — Phase A predicate: 3500   permissive/old-style: 3500
identical decisions: 3500/3500   disagreements: 0
wrote /tmp/phase_a_predicate_compare.json
```

A full `build_report()` two-run diff was **not** performed — the script compares
the predicate's per-row decisions, which is where Phase A's change lives
(`audit3_tribunal.py` line 598: `if not _is_scored_row(r): continue`).

## What this does and does not prove

**Does prove:**
- The ledger is `mode: canonical` + `loaded_from_sidecar: true` with 8769 rows.
  Because the canonical view is loaded from the sidecar and scored as-is, Phase A's
  change to the predicate is a no-op on the live surface by construction — the
  predicate cannot reject rows the sidecar already canonicalized.
- On 3500 local rows, the Phase A predicate and a permissive old-style filter
  agree on every row (0 disagreements).

**Does not prove:**
- That the predicate is *correct* — only that it is decision-neutral on the rows
  tested. A predicate can be wrong and still agree with an equally permissive filter.
- Anything about the **47,669-row live set** — DB access was denied
  (`Access denied ... 1045`) and was not retried further; that population was
  **not measured**.
- The 170-cell / zero-verdict-change claim as originally stated — **retracted**.

## What would be needed to fully reproduce

The original payload `/tmp/audit3/dashboard_data.json` (or a saved copy with its
matching sidecar), plus a full `build_report()` run on both sides of the predicate
swap, plus DB access for the live row count.
