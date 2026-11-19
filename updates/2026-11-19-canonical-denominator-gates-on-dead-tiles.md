# One denominator, gates on, dead tiles out (2026-11-19)

Three items from the external review's P0 list, plus the review check itself.

## 1. `resolved_closed_picks_net` — the canonical view (A2)

**What was broken.** `/audit` and `/audit3` reported the same asset class two
different ways on the same day: ETF was n=52 / WR 1.9% / PF 0.02 on `/audit` and
n=584 / WR 43.1% / PF 0.98 on audit3. EQUITY differed 3× on n and 14pp on WR;
COMMODITY had opposite signs. Both pages were arithmetically correct on their own
inputs — the bug was that neither published which rows it counted, so no reader
could tell which number described the book.

**What changed.** `alpha_engine/resolved_closed_view.py` builds the resolved book
once: it takes the dashboard's *own* validity predicate (so there is still exactly
one copy of those rules), removes mirror duplicates under the dashboard's key,
attributes every excluded row to a reason instead of dropping it silently, applies
realised per-class cost from the payload's own `slippage_validation` figures, and
hashes the resulting rows.

`audit_trail/dashboard_generator.py` now emits
`resolved_closed_picks_net` in the payload (counts, per-class gross/net rollup,
cost model, exclusions-by-reason, sha256) and writes the rows to
`audit_dashboard/data/resolved_closed_picks_net.json`.

`alpha_engine/audit3_tribunal.py` loads that sidecar and scores **its** rows when
the hash matches; `payload_coverage` gains a `denominator` block that says
`mode=canonical` with the hash, or `mode=payload_slice` plus an explicit "this is
NOT the same denominator as /audit" note. The fallback is deliberately loud rather
than silent: audit3 still works when the sidecar is missing, but it can no longer
claim a denominator it did not use.

`.github/workflows/audit3-ledger.yml` fetches the sidecar from the live site
(`continue-on-error`, so a missing view degrades the run rather than failing it).

## 2. Promotion gates on by default

`alpha_engine/money_ready_verdict.py` shipped `MONEY_READY_FDR_GATE=0` and
`MONEY_READY_SINGLE_SOURCE_GATE=0`, i.e. a MONEY_READY verdict could be issued
with zero multiplicity control and with every profitable sleeve drawn from a
single feed — while the comments called them "shadow-first". Both now default to
`1`. This can only downgrade; nothing is promoted by the change, and the current
book is 0/10 MONEY_READY either way. `=0` restores shadow mode.

`tools/per_class_cost_gate.py` failed **open** on a missing index, a stale index,
or an unmeasured class — so the gate's off-switch was "the bookkeeping broke".
Strict is now the default: missing/stale/empty index → `gate_index_missing_strict`,
unmeasured class → `no_class_evidence_strict`, thin sample unchanged. The escape
hatch `PER_CLASS_COST_GATE_STRICT=0` exists for backfill runs and is reported in
the decision (`strict: false`) so a caller can never mistake an escape hatch for
the real gate.

## 3. Dead tiles removed (A5/A6/A6b)

* **`tier2_proven_strategies` panel retired.** Its three cards under the word
  PROVEN were a dead strategy (signal_validation: WR 4.9%, PF 0.08, MDD 127%,
  n=102), a Tier-3 paper floor (mega_mutation, which audit3 scores
  INSUFFICIENT_N at n=19) and an empty card (rl_agent, n=0) — under a header
  reading "0/3 clear strict Tier-2". The payload now carries `cards: []` and
  `retired: true` so downstream code sees the retirement, and the panel markup is
  gone.
* **"Renaissance" branding removed** from the T1 tier label and its three tooltips.
  `T1` still means PF>2 / WR>55 / MDD<10 / n≥200; it just no longer borrows an
  institution's name for a threshold nobody has cleared.
* **PF-lift tile removed from the kill-switch card.** It rendered
  `PF Lift: +-0.0220` beside a `POSITIVE` verdict, because the verdict keyed off
  the win-rate lift alone. Removing 42 "losers" is not an improvement if profit
  factor falls, so the tile is gone and the verdict now reads
  `NOT MEASURED (PF lift <= 0)` whenever the PF lift is not positive.

## Verification (what was actually run)

| Check | Result |
|---|---|
| `pytest tests/test_resolved_closed_view.py tests/test_per_class_cost_gate.py tests/test_money_ready_fdr_gate.py -q` | green |
| `pytest tests/test_audit3_{enforcement,expectancy_gates,coverage_alpha,tribunal,evidence,edge_hunt,selection_alpha}.py -q` | 84 passed |
| End-to-end: build view → write sidecar → embed block → run tribunal | `mode=canonical`, scored rows == `kept_rows`, `share=100.0` |
| Same run with the block's `rows_sha256` tampered | `mode=payload_slice`, note reads "NOT the same denominator as /audit" |
| Greps on `audit_dashboard/template.html` | `tier2-hero-cards-grid" style` 0, `ks-pf-lift` 0, `Renaissance` 0, `TIER-2 PROVEN` 0 |
| `py_compile` all changed Python + `yaml.safe_load` the workflow | ok |

Two defects this verification caught, both fixed before shipping:

1. The canonical row omitted `entry_price`/`id`, so audit3's own dedupe collapsed
   24 of 3,500 distinct trades — a new silent denominator drift inside the module
   built to remove one. Both fields are now carried through, with a regression test.
2. `denominator.mode` was inferred by comparing row counts, which cannot
   distinguish a 3,500-row slice from a 3,500-row canonical book. Mode is now
   recorded by `load_rows` at hash-verification time (`LAST_DENOMINATOR`) and
   reported with `loaded_from_sidecar` + `fallback_reason`.

## Found but NOT fixed (pre-existing)

`tests/test_money_ready_verdict.py` has **10 failures that predate this change** —
verified by running the file with `MONEY_READY_FDR_GATE=0
MONEY_READY_SINGLE_SOURCE_GATE=0`, i.e. under the old defaults: the same 10 fail.
The pattern is that synthetic fixtures (e.g. `_make_picks(47, 53)`) produce
`wr=0.4052` instead of `0.47`, which suggests the verdict is reading class stats
from somewhere other than the patched `_load_picks`. That is a separate bug in
`money_ready_verdict()` and is worth its own investigation; it is not caused by
the gate-default change and was not papered over here.

## Not done (deliberately)

audit3 keeps its own slippage constants for scoring rather than switching to the
canonical `pnl_net_pct`. Switching the cost basis at the same time as the
denominator would move every published verdict at once and make it impossible to
tell which change caused what. The denominator lands first; the cost basis follows
as its own measured step.
