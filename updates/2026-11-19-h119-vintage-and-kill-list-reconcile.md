# H-119 two vintages reconciled, and the two kill lists made accountable (2026-11-19)

Two items from external review v3 that were still open on `main`.

## 1. H-119 showed two vintages on one card

The forward-shadow card carried a June snapshot — net PF 1.36, CI-LB 0.95, n 108,
RENDERUSDT 5.6% — directly above a live sidecar overlay that said net PF 1.12, CI-LB
0.92, n 431, JUPUSDT 5.1%. Nothing labelled which was which, so the reviewer was right
that a reader could not tell the current state from the fallback.

Worse was the instruction on the card: *"Re-evaluated at the n>=150 gate (~2026-06-25)."*
n is 431. The gate was cleared long ago, the date passed, and no promotion happened —
so the sentence described a future that had already come and gone, and it was being
emitted fresh on every hourly run.

**Changed**

* `tools/crypto_rsi5070_forward_tracker.py` — `gate_eta: "~2026-06-25"` is retired. A
  calendar date is not a gate. The sidecar now emits `n_gate_met` (bool) and the verdict
  says whether the n gate is met instead of naming a date. The failing-gate list is
  unchanged and still the operative statement: `net_ci_lb_gt_1.15`.
* `audit_dashboard/data/crypto_rsi5070_us_forward_status.json` — same two fields hand-
  corrected so the page is honest before the next tracker run (which regenerates it).
* `audit_dashboard/template.html` — static fallback moves to the 2026-11-19 values and
  is labelled "figures: 2026-11-19 snapshot (sidecar overlay pending)". A new
  `#rsi5070-vintage` element is set by the overlay script to `live · sidecar <ts>`, or
  to "sidecar unreachable, values may be stale" when the fetch fails. The dead
  `d.n + (d.n_gate ? '' : '')` expression now actually displays the gate.

The card still says **NOT a live signal, NOT sized**, and still cannot promote on its
own: only `net_ci_lb_gt_1.15` separates it from the bar, and it is 0.92.

## 2. The two kill lists share exactly one name

Confirmed: 10 audit3 KILL cells vs 64 legacy names, overlap `futures_momentum` — one.

They are two instruments, and merging them would damage both:

| | legacy `strategy_kill_list.json` | audit3 ledger |
|---|---|---|
| granularity | strategy name | strategy × direction cell (+ class, symbol) |
| direction aware | no | yes |
| basis | 2026-05-28 manual quant review + honest kill switch | realized ledger expectancy after measured costs, BH harm q ≤ 0.10 |
| carries | name | n, net %/trade, harm q, direction, class |
| read by | `strategy_suppression.load_kill_list`, `production_scanner.py` S1 loader | `audit3_denylist.denied_reason` |

`luxalgo_confluence` is the case that settles it: audit3 kills it LONG and holds it as a
CANDIDATE SHORT. A name-only list cannot express that, and importing the legacy names
into audit3's doctrine would promote decisions made on different data into a different
statistical contract.

So the reconciliation is **published, not merged**: `tools/kill_list_reconcile.py`
prints the union with provenance per name, the readers for each list, and the semantics
table above. The only genuinely unguarded case — a name in neither list — becomes a
visible set instead of an implicit one.

## Verification

* `python3 -m py_compile tools/crypto_rsi5070_forward_tracker.py tools/kill_list_reconcile.py`
* `python3 tools/kill_list_reconcile.py` — reports 10 cells / 64 names / 1 overlap
* `pytest tests/test_kill_list_reconcile.py` — union arithmetic, overlap membership,
  direction awareness
* `pytest tests/test_audit3_enforcement.py` — denylist behaviour unchanged
* grep: no `~2026-06-25` left in the template, the tracker or the sidecar

Not verified: the tracker itself was not executed (it needs the MySQL cohort); it is
compile-checked and its output contract is exercised by `rsi5070-forward-snapshot.yml`
on the next run.
