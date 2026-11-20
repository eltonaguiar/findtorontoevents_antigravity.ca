# Class divergence — why /audit and /audit3 disagree (2026-11-19)

Same book, same day, two surfaces: `money_ready_verdict.json` generated 18:47Z (the /audit
"money ready" verdict) and `audit3_ledger.json` generated 18:32Z (the /audit3 kill tribunal).
The class-level numbers do not agree, by up to 3.2x. This report says **which number to trust
for what**, and which of the discrepancies are methodology and which are bugs.

## Headline

Four distinct causes, only one of which is a genuine defect in the verdict file. The largest
apparent disagreement (CRYPTO) is **not** a 3.2x gap in skill — it is two different row
populations. I also have to retract part of my own framing: the "up to 3.2x" figure I put in the
peer review was computed as a **mean of per-cell profit factors**, which is not a valid
aggregate (PF is a ratio of sums, not a sum of ratios). Corrected comparison below.

| Class | verdict n | verdict PF (gross) | verdict net expectancy | audit3 n | audit3 PF (net) | Ratio (verdict/audit3) | Cause |
|---|---|---|---|---|---|---|---|
| CRYPTO | 3,726 | 0.263 | −5.66% | 6,675 | 0.838 | **0.31** | different row set |
| ETF | 52 | 1.823 | **−2.26%** | 575 | 1.005 | 1.81 | gross vs net |
| EQUITY | 256 | 0.644 | **+0.75%** | 931 | 1.089 | 0.59 | gross vs net + row set |
| FOREX | 628 | 0.166 | −2.01% | 256 | 0.920 | 0.18 | different row set (inverted) |
| COMMODITY | 232 | 0.469 | −1.03% | 50 | 0.096 | 4.9 | different row set |
| FUTURES | 60 | 1.271 | +0.59% | 4 | 1.872 | 0.68 | n too small both sides |
| BOND | 0 | — | — | 32 | 0.654 | n/a | verdict resolves nothing |
| MEME | 10 | 0.023 | — | — | — | n/a | below any floor |

## Cause 1 — Different row populations (the big one)

audit3's own coverage block is explicit: `total_closed_picks 14,637`, `valid_closed_picks
8,200`, `scored_rows 8,613`, with four documented exclusion cohorts (`invalid_row` 5,823,
`mirror_duplicate` 91, `non_performance_exit` 43, `resolver_breakeven_fallback` 67) plus
`integrity_excluded` 5,933 and `auto_expired` 9,257.

The verdict resolves a **smaller, different** slice: 3,726 CRYPTO rows vs audit3's 6,675, but
628 FOREX rows vs audit3's 256. So it is not a subset in either direction — the two pipelines
disagree about *which picks count as resolved*. Until the resolver population is defined once and
shared, every cross-surface comparison is measuring two different books.

**Trust:** audit3 for anything about which strategies fail (it publishes its denominator and its
exclusions). The verdict for a live UI roll-up only.

## Cause 2 — Gross PF vs net expectancy in the same record

`money_ready_verdict.py:1273` computes expectancy **post-cost**:

```python
expectancy = wr * (avg_win - slippage) - (1 - wr) * (avg_loss + slippage)
```

while the class `pf` field beside it is gross. Two classes therefore carry contradiction noise:

- **ETF: PF 1.82 (looks like the one good class) but net expectancy −2.26%.** Gross-only, ETF is
  the strongest class on /audit; net of the file's own 5bp ETF slippage it is negative. Copilot's
  plan cites "ETF PF 1.82" as evidence ETF is the strong sleeve — it is citing the gross number.
- **EQUITY: PF 0.64 (looks dead) but net expectancy +0.75%.** Reverse direction, same cause.

**Fix:** publish `pf_gross` and `pf_net` as separate keys, never a bare `pf`, and put the sign of
the net figure next to the verdict. A reader cannot reconcile a PF<1 with a positive expectancy
from the current field names.

## Cause 3 — `policy_clean_*` is not a filter (real bug)

`policy_clean_pf == pf` **exactly** for all 11 classes, while `policy_clean_n` differs from
`n_resolved` every time. For CRYPTO it is worse than cosmetically wrong:

```
n_resolved       = 3,726
policy_clean_n   = 22,081     # a "clean subset" six times larger than the whole
policy_clean_pf  = 0.263      # identical to the unfiltered pf
```

A clean subset cannot exceed its parent, and a filter that changes n by 5.9x cannot leave the
profit factor bit-identical. Either the count and the ratio are computed over different frames,
or the clean-filter result is never assigned and the headline is copied.

**Fix:** assert `policy_clean_n <= n_resolved` and `abs(policy_clean_pf - pf) > 0` when the counts
differ, in the generator's own test suite. This is the kind of invariant that should fail CI
rather than ship to a page.

## Cause 4 — Coverage arithmetic (`scored_share_of_valid_pct = 105.04`)

`scored_rows 8,613` divided by `valid_closed_picks 8,200` = 105.04%. A scored share cannot exceed
100%: the scored population includes rows the validity filter excludes. Already on the ledger
(T-item), noted here because it is the same class of denominator bug as Cause 1.

## What this changes in my peer review

- The "up to 3.2x" headline in §? of the peer review is **withdrawn as stated**; the real gaps are
  row-population differences (Cause 1) and gross-vs-net field confusion (Cause 2), and neither is
  3.2x of *skill*.
- Item that stands, strengthened: the plan's "ETF is the proven class" rests on a gross PF of
  1.82 whose own net expectancy is negative. That is now a second, independent reason the $2k
  recommendation needs the net number before it is actioned.

## Verification

Every figure above is reproducible from the two committed artifacts:

```
python3 - <<'PY'
import json
v=json.load(open("audit_dashboard/data/money_ready_verdict.json"))
a=json.load(open("audit_dashboard/data/audit3_ledger.json"))
for k,c in v["classes"].items():
    print(k, c["n_resolved"], c.get("pf"), c.get("expectancy"),
          c.get("policy_clean_n"), c.get("policy_clean_pf"))
print(a["coverage"]["total_closed_picks"], a["coverage"]["valid_closed_picks"],
      a["coverage"]["scored_rows"], a["coverage"]["scored_share_of_valid_pct"])
PY
```

The 10-minute progress loop (`tools/buffy_progress_loop.py`) re-runs the ratio table on every tick
and records it in `reports/progress_loop/<date>.jsonl`, so a future rebuild that changes the
picture shows up as a diff rather than a surprise.
