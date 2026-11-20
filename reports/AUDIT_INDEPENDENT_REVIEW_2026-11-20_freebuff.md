# Independent review of the 2026-11-20 audit claims

**Author:** freebuff-deepseek-v4-flash · **Date:** 2026-11-20
**Method:** every number below was measured in this run against a live endpoint
or a committed file. Claims I could not confirm are marked **unverified** rather
than repeated. Same standard I apply to my own claims.

Inputs reviewed:
- `reports/asset_class_edge_review_2026-11-20.json` + `tools/asset_class_edge_review.py` (`9c8f709cc78`)
- `plans/2026-11-20-audit-surface-consolidation-plan.md`
- `reports/AUDIT_CONSOLIDATION_PLAN_2026-11-20.md`

---

## 1. `/audit` vs `/audit3`: byte-identical, so "223 minutes behind" is closed

Fetched separately in this run:

| surface | bytes | sha256[0:12] | generated_at |
|---|---|---|---|
| `/audit/data/audit3_ledger.json` | 655585 | `cd6e3dc8110e` | `2026-11-20T12:35:03.741042+00:00` |
| `/audit3/audit3_ledger.json` | 655585 | `cd6e3dc8110e` | `2026-11-20T12:35:03.741042+00:00` |

Byte-identical: **yes**. **0 mismatching classes**,
**363 cells on each side with 0 differing verdicts**:

| class | /audit | /audit3 | |
|---|---|---|---|
| BOND | WEAK | WEAK | agree |
| COMMODITY | KILL | KILL | agree |
| CRYPTO | KILL | KILL | agree |
| EQUITY | WEAK | WEAK | agree |
| ETF | WEAK | WEAK | agree |
| FOREX | WEAK | WEAK | agree |
| FUTURES | INSUFFICIENT_N | INSUFFICIENT_N | agree |

The plan's P0 "223 minutes behind, patch has no owner" is stale: it is merged and
deployed (#985 publishes the fresh ledger to `/audit/data`; #994 removes
`audit3_ledger.json` from the `audit-dashboard` deploy glob, leaving one
publisher). Both URLs serve the same bytes from the same build, which is why
they can no longer drift. Verify parity with `cmp`, not with timestamps.

## 2. `policy_clean_*` is an alias — and the real clean view disagrees with it

Root cause pinned to a line:

```python
# alpha_engine/money_ready_verdict.py:1720  (origin/main)
_policy_n, _policy_wr, _policy_pf = n, wr, pf
# :1761-1764
"policy_clean_n":  _policy_n,
"policy_clean_wr": round(_policy_wr, 4),
"policy_clean_pf": round(_policy_pf, 4) if ...,
```

Published artifact (`generated_at=2026-11-20T12:59:03.895346+00:00`):

| class | pf | policy_clean_pf | n | policy_clean_n | verdict |
|---|---|---|---|---|---|
| BOND | - | - | 2 | 2 | INSUFFICIENT_DATA |
| CHEAP_STOCKS | 0.3899 | 0.3899 | 2 | 2 | INSUFFICIENT_DATA |
| COMMODITY | 0.2442 | 0.2442 | 30 | 30 | NOT_READY |
| CRYPTO | 0.2612 | 0.2612 | 21928 | 21928 | NOT_READY |
| EQUITY | 0.6085 | 0.6085 | 116 | 116 | NOT_READY |
| ETF | 1.8337 | 1.8337 | 30 | 30 | INSUFFICIENT_DATA |
| FOREX | 0.2222 | 0.2222 | 460 | 460 | NOT_READY |
| FUTURES | 1.2706 | 1.2706 | 17 | 17 | INSUFFICIENT_DATA |
| MEME | 0.0234 | 0.0234 | 10 | 10 | INSUFFICIENT_DATA |
| MUTUAL_FUND | 0.0 | 0.0 | 0 | 0 | INSUFFICIENT_DATA |
| PENNY_STOCK | 0.1779 | 0.1779 | 4 | 4 | INSUFFICIENT_DATA |

`pf == policy_clean_pf` in **10/11** classes; `n == policy_clean_n` in
**11/11**; clean counts larger than the parent: **none**.

**This is the correction that matters.** The registry *does* hold a genuine clean
view, and it is not what gets published:

| | registry `by_asset_class_policy_clean_net` | published `classes.CRYPTO` |
|---|---|---|
| n | 22633 | 21928 |
| pf | 0.257608 | 0.2612 |

`policy_excluded_count` in the registry: **111**.

Two conclusions:
1. The published `policy_clean_*` columns are the **raw** stats under a clean name —
   the readiness gate never reads the registry's clean view, so the filter cannot
   filter.
2. The "clean subset larger than its parent" objection **is structurally present**,
   just not at the numbers quoted: registry clean CRYPTO n=22633 exceeds
   published n=21928. The quoted 22,081 vs 3,726 does not match any
   current artifact, so those specific figures should be replaced with these.

Fix is one of: publish the registry view (and accept the reconciliation work its
larger denominator implies), or rename these columns `raw_*`. Do not keep the
current name and a smaller denominator.

## 3. The staleness risk is in the outcome layer, not just FX

`db_freshness.json` reports `overall: "RED"`. Stalest checks:

| check | table | minutes_stale | last_resolved |
|---|---|---|---|
| signal_outcomes | at_signal_outcomes | 115782.0 | 2026-03-04 08:47:58 |
| live_picks | trading_picks | 42.3 | 2026-05-23 17:47:39 |
| resolver_outputs | trading_picks | 36.8 | 2026-05-23 17:53:12 |

The FX claim is directionally right but conflates two layers.
`audit3_selection_alpha.py` maps `FOREX -> fx_prices`, and its own comments record
`fx_prices` last bar **2026-02-09** and `futures_daily_ohlcv` ending **2026-06-21**.
That makes FX **selection alpha** unmeasurable. It does not make the FX verdict
unmeasurable: the verdict comes from resolved pick outcomes, and FOREX carries
n=460 at pf=0.2222. "No edge" and
"attribution cannot be computed" are different statements; for FX the second is
the true one.

More important: `at_signal_outcomes` is ~80.4 days stale. And the
freshness file contradicts itself (one check reports `minutes_stale: 42.3` while
its `last_pick_at` reads `2026-05-23`). An artifact that cannot agree with itself
cannot be an SLA source, so L3 must be built on a consistent computation first —
otherwise it will propagate this doubt into every class label.

## 4. The edge review's falsification is arithmetically sound

Recomputed from the JSON, not the summary: `oos_hits/oos_n = -/- = -`,
matching published `oos_rate` -; `rate - base_rate_test = -`,
matching published lift -.

| class | event | OOS up-rate sel vs rest | OOS down-rate sel vs rest | mean fwd sel vs rest | best feature |
|---|---|---|---|---|---|


The conclusion holds in every class: the selected group has a lower up-rate, a
higher down-rate and a worse mean forward return. That is a variance artifact,
and the direction check is the right instrument. Two wording nits, no analytic
impact:

- The CRYPTO verdict string says "event rate up" while the OOS rate (-) is
  *below* its base rate (-) — the rate rose in train and flipped in OOS.
  The string should say which period it describes.
- Reporting FOREX/BOND as inconclusive instead of omitting them is the right call.

## 5. The 70-minute tolerance is unsatisfiable, but currently harmless

`tools/assert_surface_parity.py:73` sets `DEFAULT_TOLERANCE_MIN = 70`, commented
"the hourly cron runs at :10". Neither holds: `audit-dashboard.yml` is
`10 */3 * * *` and `audit3-ledger.yml` is `23 */6 * * *`. A 6-hourly producer can
only sit inside a 70-minute window right after a rebuild.

No false RED today, because both URLs are one build (section 1) and the measured
gap is zero. P0-8 (assert equal content hashes) is therefore free to adopt — the
hashes are already equal.

## 6. Unverified: "ETF tactical allocation 0/576 NOT REPRODUCED"

**I am not treating this as fact.** The registry holds 108 hypotheses, only
2 TAA-related (H-2026-11-19-03, H-2026-11-19-06), all `PRE_REGISTERED`.
No artifact on `main` contains 576 pre-registered cells, and `grep 576` across
`reports/` returns unrelated numbers (`elapsed_s: 576.04`, `sharpe: 0.3957`).

A "0/576" is a strong falsifying claim; it must be traceable to a file holding the
576 cells, including the window and the bar it was measured against. Until that
file is named, the status is *unverified*, and citing it would seed an
unverifiable number into a plan that later work builds on.

## 7. Ordering I would use

1. **Make the freshness artifact self-consistent** — everything downstream
   inherits its doubt (section 3).
2. **L2, exclusion bias bound** — one measurement that can invalidate every
   class headline at once, and it is currently untested.
3. **P0-8, hash equality** — free (section 5), removes a structural false-RED.
4. **`policy_clean_*` decision** — publish the registry view or rename to `raw_*`
   (section 2). Labelling, not measurement: today's numbers are honest.
5. **Source or drop the 0/576 claim** before it becomes a premise.
6. **L4, sabotage suite — earlier than proposed.** Both real defects today were
   "the gate received the wrong input" (sizing PF instead of published PF; gates
   fed raw stats labelled clean). A sabotage suite is the only item that tests
   power rather than firing, and it is the direct regression net for this class.

## 8. Limits of this review

- No external model consult was used; all numbers are from this repo or a live
  fetch during the run.
- I verified the edge review's stored outputs and arithmetic, not its data
  pipeline; I did not re-run the backtest.
- "41.2% unscored (8,605/14,632)" is **not verifiable from the artifact**: the
  readiness JSON publishes no coverage denominator. That absence is itself the
  finding, and an argument for L2 shipping a published denominator.
- Section 1 is a point-in-time measurement (`2026-11-20T12:35:03.741042+00:00`). Parity is
  guaranteed by the single-publisher design, not by a gate that could catch a
  future re-split.
