# P0 — The forward clock is structurally blocked, not merely starved

**Date:** 2026-11-22
**Scope:** `tools/paper_portfolio.py --load-from-gate` run against real repo state, and the
`alpha_engine.audit3_tribunal.forward_gate_block` gate it delegates to.
**Verdict:** the structural claim is **CONFIRMED in code**. The numbers in the original
framing are **worse than stated**, not better.

---

## 1. The refusal output, verbatim

```
  POD-EQUITY-BREAKOUT              n=0    eligible=False no forward rows — nothing can promote
  POD-LUXALGO-SHORT                n=0    eligible=False pod status 'post_hoc' cannot confer confirmatory
  POD-CRYPTO-ENSEMBLE-GRADE        n=0    eligible=False pod status 'declined' cannot confer confirmatory
  POD-CRYPTO-VWAP-REVERSION        n=0    eligible=False pod is observe - registered for observation only
  POD-CRYPTO-BOLLINGER-MR          n=0    eligible=False pod is observe - registered for observation only
  POD-FABER-TAA                   n=0    eligible=False pod is observe - registered for observation only
  POD-FOREX-USDJPY-MOMENTUM        n=0    eligible=False pod is observe - registered for observation only
  POD-COMMODITY-ROLL-YIELD         n=0    eligible=False pod is observe - registered for observation only
  POD-CRYPTO-POSITION             n=0    eligible=False pod is observe - registered for observation only
  POD-ETF-DUAL-MOMENTUM            n=0    eligible=False pod is observe - registered for observation only
  POD-CRYPTO-BTC4H-RSIMACD         n=0    eligible=False pod is observe - registered for observation only
```

(The `post_hoc` / `declined` lines are produced by `tools/paper_portfolio.py:505-510`, which
labels pods the gate hides; the `observe` lines come from the gate itself.)

## 2. The verified status → promotability logic

There is no separate status table to find: the mapping is a hard branch in the gate.

**`alpha_engine/audit3_tribunal.py:1630-1645`** (inside `forward_gate_block`):

```python
status = str(pod.get("status") or "").strip().lower()
# `observe` pods are shown so their forward clock is visible on /audit3,
# but only pre_registered pods may promote a cell: an observe pod's rows
# are informational by construction. Declined/post-hoc/retired are hidden.
if status not in {"pre_registered", "observe"}:
    continue
...
res = dict(FO.promotion(subset))
if status != "pre_registered":
    res["eligible"] = False
    res["reasons"] = [f"pod is {status} - registered for observation only"]
    res["promotion_blocked_by_status"] = status
```

The decisive line is `if status != "pre_registered": res["eligible"] = False`. It runs
*after* `FO.promotion(subset)` and **overwrites** the row-based verdict. However good the
forward rows are, a non-`pre_registered` pod is forced ineligible.

**`alpha_engine/forward_observations.py:379-429`** (`promotion`) is the row-based rule that
gets overwritten: it requires `n >= min_n`, `pf_ci_lb > PROMOTION_PF_CI_LB` or
`ir >= PROMOTION_IR`, 100% honest intrabar first-touch, and benchmark coverage
`>= BENCHMARK_COVERAGE_MIN`. The thresholds are constants at
[`alpha_engine/forward_observations.py:68-72`](alpha_engine/forward_observations.py:68):
`PROMOTION_MIN_N = 100`, `PROMOTION_PF_CI_LB = 1.0`, `PROMOTION_IR = 0.5`,
`BENCHMARK_COVERAGE_MIN = 0.90`, `CLOCK_WINDOW_DAYS = 30`.

**`tests/test_audit3_forward_gate.py:146-157`** locks the behaviour in a test:

```python
def test_observe_pod_is_shown_but_cannot_promote(tmp_path):
    ...
    assert pod["eligible"] is False
    assert pod["n_forward"] >= 100
    assert any("observe" in r for r in pod["reasons"])
```

That test supplies **120 perfect forward rows** to an `observe` pod and asserts it still
cannot promote. So `observe` is not a display label.

### Is it permanent, or just configuration?

It is **enforced by code but driven by a manifest field**. `observe` is a status in
[`reports/audit3_confirmatory.json`](reports/audit3_confirmatory.json) whose own vocabulary
string says it "cannot confer confirmatory **until it is promoted to pre_registered**". So an
`observe` pod can *never* promote as configured, but the bar is a deliberate re-registration
decision, not a code change. That is the correct reading: the block is by design, and the
design says how to leave it.

## 3. Full pod status census

### 3a. Primary manifest [`reports/audit3_confirmatory.json`](reports/audit3_confirmatory.json) (11 pods)

| status | count |
|---|---|
| `observe` | **8** |
| `pre_registered` | 1 (`POD-EQUITY-BREAKOUT`) |
| `post_hoc` | 1 (`POD-LUXALGO-SHORT`) |
| `declined` | 1 (`POD-CRYPTO-ENSEMBLE-GRADE`) |

### 3b. Second manifest [`audit_dashboard/data/audit2_pods.json`](audit_dashboard/data/audit2_pods.json) (7 pods)

`observe` 6 (five shared with audit3 plus `POD-MEGA-MUTATION-CANDIDATE`), `pre_registered` 1.

### 3c. Union across both manifests (12 unique pods)

| status | count |
|---|---|
| `observe` | **9** |
| `pre_registered` | 1 |
| `post_hoc` | 1 |
| `declined` | 1 |

**Correction to the framing:** the brief said "6 of 11 pods are `observe`" and "7 of 11
structurally incapable". The verified count is **8 of 11 `observe`**, so **10 of 11**
pods in the primary manifest cannot confer confirmatory status by construction. Only
`POD-EQUITY-BREAKOUT` is structurally capable, and it is blocked for a different reason:
no rows.

### 3d. Forward ledger census (read-only parse of [`reports/forward_observations.jsonl`](reports/forward_observations.jsonl), untouched)

- 432 rows total.
- **430** on `H-119` — which has **no pod**; it is marked `"promotable": false` in
  [`reports/hypothesis_registry.json`](reports/hypothesis_registry.json) (the N3 orphan resolution).
- 2 rows on `H-2026-11-22-EQUITY-TREND10M` / `H-2026-11-22-COMMODITY-TREND10M` — no pods either.
- **Zero rows on any pod's hypothesis.** Every pod is at `n_forward = 0`.

## 4. Blunt statement

**Can the fleet produce a PROVEN_T2 verdict by construction today? No.**

Exactly one pod (`POD-EQUITY-BREAKOUT`, `pre_registered`) is allowed to try, and it has zero
forward rows. The other ten are forced ineligible by `status != "pre_registered"` regardless
of row count. And the whole ledger's 432 rows accrue to hypotheses that are not pods at all,
so they cannot promote anything.

**The single change that would unblock it:**

- For the one eligible pod: accrue and honestly close `POD-EQUITY-BREAKOUT`'s own forward
  rows (`H-BABY-EQUITY-VT-PATTERN-SWEEP-001`, closed on/after 2026-11-19) with
  `intrabar_first_touch: true` and benchmark legs, until the `promotion` rule in
  [`alpha_engine/forward_observations.py:379`](alpha_engine/forward_observations.py:379) passes.
  No status change needed.
- For the eight `observe` pods: change `pods[].status` from `observe` to `pre_registered` in
  [`reports/audit3_confirmatory.json`](reports/audit3_confirmatory.json) after a fresh
  registration decision. That is a manifest edit, not a code edit.

## 5. What this means

The programme's outcome so far is that every mechanism tested was KILLED and no rule beat
holding SPY. This finding closes the loop: the machinery that would certify a survivor is
itself unable to certify. Ten of eleven pods are barred by status, the eleventh has no rows,
and every row that exists belongs to hypotheses with no pod. The fleet is not waiting for
the clock to run; for ten pods the clock is not wired to anything that can ring.

Honest bottom line: **there is no current path from any pod to a confirmatory verdict.**
The gate is not broken - it is doing exactly what it was told - but what it was told leaves
nothing promotable. Until a pod is pre-registered *and* accrues honest forward rows, every
"PROVEN" claim in this programme would have to come from somewhere other than this gate,
and there is no evidence that it does.
