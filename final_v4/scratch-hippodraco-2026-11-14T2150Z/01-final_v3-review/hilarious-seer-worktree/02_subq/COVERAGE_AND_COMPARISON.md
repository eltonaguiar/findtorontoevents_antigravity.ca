# SubQ — availability, and what was used instead

**Status: NOT AVAILABLE. Not substituted silently — recorded.**

## What I checked (2026-11-14)

| Check | Method | Result |
|---|---|---|
| `subq` / `SubQ` on PATH | `which subq SubQ subq-cli` | no binary |
| Repo references | case-insensitive search over `.md/.py/.json/.yaml` | **false positives only** — every hit is the SQL word `subquery` in `tools/db_health_check.py`, `tools/mysql_dedup_fix.py`, and old worktree copies |
| Gravity Index (developer-service catalog) | `search` for a research/coverage/comparison service named SubQ | **no recommendation, no options.** Catalog has no such product; the closest entries were news/social data and proxy APIs, which are not this |

So "leverage SubQ" could not be executed. I did not invent a comparison to fill the gap, and I did
not relabel my own analysis as SubQ output.

## What I used instead — and why it is a real substitute, not a downgrade

The function SubQ was meant to serve is *coverage* (did we look everywhere?) and *comparison*
(do independent methods agree?). I ran that function with three independent instruments:

| Instrument | Covers | Blind to |
|---|---|---|
| **Re-execution** from the raw ledger (`final_v3/05_evidence/`) | every number I claim; reproduces from 3,500 rows | anything absent from the payload |
| **Repo's own benchmark artifact** `audit_dashboard/data/benchmark_ledger_proof.json` | 170 ledgers, paired bootstrap vs benchmark, random-entry MC | strategies not in that artifact |
| **Peer reconciliation** — 6 packages: `finpredict-v2`, `hilarious-seer`, `fix-p0-safe-fixes`, `quant-audit`, `finpredict-v3`, `flaxen-hair` | independent conclusions, including disagreements | shared upstream data errors propagate to all of them |

Their disagreements are the useful part. Where all three agree (the system is not money-ready; crypto
stop fills are the dominant loss; the 170-ledger bootstrap result is negative), confidence is high.
Where they conflict — VWAP "VALIDATED" vs refuted — the conflict itself localised a stale-artifact bug
that re-execution then confirmed (see `../00_common_themes/BUGS.md` §B1).

## What SubQ would add if it exists

Three things this substitution cannot do:

1. **Trial-count coverage.** It cannot tell us how many hypotheses were tested outside the repo. My
   multiple-testing correction uses only in-repo counts (170 ledgers, 658 trials), which is a lower
   bound. Any external tool that counts trials across sessions would materially sharpen §B8.
2. **Cost-model coverage.** `tools/data/transaction_costs.json` is a hand-maintained estimate. A
   coverage service could compare it to observed fills once the stop-fill replay has enough samples.
3. **Benchmark coverage.** All 170 ledgers are compared to a benchmark in one artifact; a second,
   independent benchmark construction would test whether the 4/170 result is an artifact of that
   construction.

## How to plug it in

`tools/stop_fill_replay.py` and `tools/cot_contrarian_backtest.py` both emit `--json` artifacts with a
stable summary block. Any comparison service should consume those files rather than re-deriving
numbers, so its output is checkable against `05_evidence/`. That is the integration contract.

**What would change my conclusions:** a SubQ-style report contradicting §B3 (crypto fill leak) would
need to produce a row-level reconciliation of `exit_price` vs `stop_loss` that differs from
`05_evidence/stop_fill_audit.txt`. Disagreement without row-level data is not evidence.
