# Doc 22 count clarification: 9 vs 13 vs 14 (2026-11-23)

## What the discrepancy was

[`docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md`](../docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md)
stated three different counts of "how many strategies/rows the audit covers" in two places:

- line 25 (Part 2 row-set note): "The programme's own counts are 9 (scoreboard) and 13 (doc 18)" against its own **14 rows**
- line 164 (Appendix A item 1): "Strategy count: 9 (scoreboard) vs 13 (doc 18) vs 14 (this document's fixed row set)"

Prior reviews recorded it as "pre-existing, not fixed". The line numbers in earlier reports (25 and 164)
still hold on `origin/main` at the time of this fix.

## What each number actually counts (with citations)

| Number | What it counts | Citation |
|---|---|---|
| **9** | Rows of doc 15's section-2 per-strategy table: 9 rows = 7 killed, 1 marginal survivor (funding carry), 1 blocked on data (commodity term-structure carry). Doc 15 itself says "Nine strategies were tested." This count predates commodity momentum and bond momentum (doc 15 lists them as "not yet run"). | `docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md:12-17`, table rows at lines 32-40 |
| **13** | The strategy count doc 18 carried in: "13 strategies tested, 12 KILL, 1 MARGINAL (funding carry), 0 cleared." No source ever enumerated its membership. | `docs/edge_research/18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md:12`; discussion at `docs/edge_research/19_HONEST_VERDICT_2026-11-22.md:143-148` (§8.1) |
| **14** | Doc 22's Part 2 row set (14 numbered rows). It equals doc 23's final-accounting table (14 rows) and the settled tally `0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)`. | `docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md:29-42`, `docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:180-193` |

Docs 18 and 19 no longer exist at `origin/main` (only docs 15, 22, 23, 24-27 remain in `docs/edge_research/`),
so their citations still resolve only in history; both are preserved at commit `69cd7943`. Line 167 of doc 22
also cites doc 18, so the dangling reference is pre-existing and not introduced here.

## Which outcome applied

**Outcome (b): three genuinely different quantities, conflated by unclear wording.**

- 14 is the count of verdict rows (11 not-investable + 3 unknown).
- 9 is an earlier snapshot (doc 15) taken before two momentum families were run.
- 13 is a carried-in count whose membership was never enumerated.

None of the three is a typo for another. Forcing all three to 14 would have deleted a correct distinction
("doc 15 predates the momentum families"), so no number was changed. Each original sentence was kept and a
dated bracketed clarification was appended, matching the existing `[corrected 2026-11-23: ...]` convention.

## The edit (additive only)

- **line 25** - appended `[clarified 2026-11-23: ...]` naming what 9, 13 and 14 each count, with SRC citations.
- **line 164** - appended a shorter `[clarified 2026-11-23: ...]` with the same mapping.

No text was deleted. Each edited line is the old line plus appended text only.

## Verification

- `python3 -m pytest tests/test_edge_research_tally_consistency.py -q` -> **22 passed** before, **22 passed** after.
- Tally line at doc 22:177 is byte-identical: `TALLY: 0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)`.
- Verdict-word counts in doc 22 unchanged (INVESTABLE 8, NOT_INVESTABLE 28, UNKNOWN 35, KILL 10, MARGINAL 1, BLOCKED_DATA 2 before and after).
- Diff: 181 lines before and after; only lines 25 and 164 differ; every other line byte-identical; each changed line starts with its old line (pure append).
