# MUTUAL FUNDS

**Closed-ledger measurement: n = 0.** Mutual funds are not a tradable class in this system — the
dashboard has no MUTUAL_FUND rows, so there is nothing to measure.

**Scan footprint:** the class appears only in research documents, e.g.
`reports/2026-10-22-mutual-fund-multi-asset-audit.md` and
`reports/FRM_CFA_CONCEPTS_AUDIT_2026-06-20.md`.

**Verdict: INSTRUMENTED — NOT MEASURED (no trades).** Not "failed"; never attempted.

**Why it is a poor fit for this pipeline:** mutual funds price once daily at NAV, cannot be
shorted, and settle T+1 with no intraday fills. The entire advantage of this repo's machinery
(daily close resolution, same-day TP/SL) is meaningless here, and a fund-of-funds rotation would
be a monthly strategy with NAV-only marks.

**If it is to be attempted at all**, the honest form is a monthly rotation across a fixed list of
index funds, benchmarked against the same list held equally weighted, with expense ratios in the
cost model. That is a 12-observation-per-year test: it needs 3+ years before n ≥ 36.
