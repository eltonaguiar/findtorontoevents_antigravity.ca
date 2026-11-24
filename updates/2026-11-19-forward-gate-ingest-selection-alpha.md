# PROVEN_T2 gated on forward evidence; the ledger is filled; selection alpha measured (2026-11-19)

Three follow-ups to #908, in the order they had to happen: gate the verdict, fill the
ledger, then use it.

## 1. PROVEN_T2 now needs forward rows, not just a re-scored history

**Broken:** #908 defined forward evidence but nothing consumed it. A pre-registered pod
could reach `PROVEN_T2` purely from the same closed picks the tribunal had just
re-scored — the evidence that *motivated* the pod, not evidence *about* it.

**Changed:** `_promote(cell, forward)` in `alpha_engine/audit3_tribunal.py` demotes
`PROVEN_T2` -> `CANDIDATE` unless that cell's own pod passes the promotion rule, and
the reason is written into `cell["reasons"]`. `forward_gate_block()` builds the gate
data: per pre-registered pod, only rows closed on/after `registered_at` count (a pod
judged on earlier rows is a backtest with extra steps), plus a read-only
`hypotheses` view so an accruing lead like H-119 is visible without being promotable.
The CLI always supplies the block; `build_report(forward=None)` keeps pre-gate
behaviour for library callers and is pinned by a test.

**Today it changes nothing, and that is checked, not assumed:** on the live payload
the verdict list is identical with and without the gate
(41 tested / 3 candidate / 1 kill / 0 proven), and the single pre-registered pod
(`POD-EQUITY-BREAKOUT`, since 2026-11-19) has 0 forward rows.

## 2. The ledger is filled from the honest intrabar cohort

`alpha_engine/forward_observations_ingest.py` (read-only; `--apply` to write, dry run
by default):

| Step | Result |
|---|---|
| honest cohort (deduped, non-ambiguous intrabar) | 3,756 rows |
| H-119 condition (CRYPTO, RSI 50-70, US session) | **430 rows** |
| outside every registered condition | 3,326 (skipped, not rejected) |
| rejected | 0 |
| re-run | `added 0, duplicates 430` (idempotent) |

H-119 has **no strategy label** in the cohort (`LIKE '%rsi5070%'` returns zero rows),
so attribution runs through the project's own stampers, exactly as the tracker does —
anything else would measure a different population than the gate it feeds.

**Cross-check:** ledger net PF **1.1147** (CI-LB **0.9213**, mean +0.1348%/trade) vs the
tracker's **1.1191** (CI-LB **0.9158**). Two independent paths, 0.4% apart.

Promotion verdict is unchanged and now measured: **not eligible** — net CI-LB 0.9213
<= 1.0, IR 0.043 < 0.5, benchmark coverage 79.8% < 90%. Clock:
`H-119: 430/100 forward rows, 1.467/day, N_GATE_MET`, no invented ETA.

### Bugs found while wiring it (each cost a run)

* `_ms()` parsed only strings; the cohort returns `datetime`, so every bar window
  collapsed to `(0,0)` at the epoch and all 3,756 rows reported `no_bars`.
* `fetch_bars()` returns a **flat** `{symbol: bars}` map, not the nested one I assumed.
* `fetch_cohort()` deliberately omits `exit_price` / `intrabar_resolved_at`; both are
  now hydrated by primary key rather than by re-implementing its dedupe.
* The bar window stopped at entry, so the benchmark leg could not be measured over
  entry..exit — benchmark coverage 64% -> 80%.
* **My own first rule was wrong.** Rejecting rows whose prices disagree with the
  resolved return kept 180 of ~430 rows and moved net PF from 1.12 to **0.65** — a
  biased subset. The resolved return is authoritative; `exit_px` is derived from it
  and the disagreement is preserved as `resolver_exit_px` / `gross_mismatch_pp`.
  The 0.65 would have been reported as evidence against H-119.

## 3. Selection alpha vs matched exposure, per class

`alpha_engine/audit3_selection_alpha.py` against live prices (2,475 of 3,500 closed
picks covered; the rest have no bar at entry/exit or no timestamp):

| Class | n | pick | hold | alpha/pick | 95% CI | verdict |
|---|---|---|---|---|---|---|
| CRYPTO | 1,969 | +0.340% | +0.502% | **-0.162%** | [-0.739, +0.405] | no skill shown |
| EQUITY | 240 | +0.908% | +0.794% | **+0.114%** | [-0.407, +0.593] | no skill shown |
| ETF | 266 | -0.014% | +0.105% | **-0.119%** | [-0.417, +0.209] | no skill shown |
| CRYPTO/LONG | 1,195 | | | -0.525% | [-1.334, +0.215] | negative point estimate |
| CRYPTO/SHORT | 774 | | | +0.398% | [-0.191, +1.301] | no skill shown |

Overall: pick +0.357% vs hold +0.488% -> **alpha -0.131%** [-0.600, +0.318], alpha
win-rate 45.2%.

**Answer: no asset class shows selection skill after costs.** Every interval includes
zero. The one positive point estimate (EQUITY +0.114%/pick) is well inside noise, and
CRYPTO's loss is concentrated in LONG (-0.525%) while SHORT is positive — a sign
pattern consistent with beta, not selection. FOREX/BOND/COMMODITY/FUTURES have no
price coverage, so they are reported as absent rather than as zero.

Separately fixed: `_conn()` in the alpha module read raw `DB_PASS_STOCKS`, which
`tools/db_env.py` documents as stale after the 2026-05-12 rotation; it now resolves
through `get_stocks_creds()` (canonical `.env.dbpw`).

## Verification

* `pytest tests/test_forward_observations_ingest.py tests/test_audit3_forward_gate.py` — 21 passed
* `pytest tests/test_audit3_tribunal.py tests/test_audit3_enforcement.py
  tests/test_audit3_coverage_alpha.py tests/test_audit3_selection_alpha.py
  tests/test_audit3_expectancy_gates.py tests/test_forward_observations.py` — 78 passed
* `forward_observations --verify` -> 430 rows, ok=True, 0 violations, 0 duplicates
* gate on the live payload -> `enforced: true`, verdict list identical to ungated
* ingestion re-run -> 0 added / 430 duplicates

## Limitations

* Ingestion covers the honest intrabar cohort only. Pick-level ledger rows from other
  sources still have no forward writer, so `PROVEN_T2` remains out of reach for them.
* `regime_ok` is `True` for every ingested row because the stampers returned a complete
  pre-entry feature vector; this cohort carries no regime label, and the field is
  recorded but never gated.
* The benchmark leg is a 1h-close buy-and-hold with a 6h staleness tolerance, not a
  cost-adjusted index leg; it is a descriptor, and the 90% coverage gate is the only
  thing it decides.
