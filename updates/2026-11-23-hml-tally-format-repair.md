# HML preregistration tally line: format repair so the discovery test can read it (2026-11-23)

**What was broken.** `tests/test_edge_research_tally_consistency.py` discovers every markdown
document under `docs/` that states a tally and asserts each one states the settled
`0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)`. It was failing on one document:

```
FAILED tests/test_edge_research_tally_consistency.py::test_every_document_that_states_a_tally_states_the_settled_one[docs/preregistration/HML_VALUE_TEST_2026-11-22.md]
E   AssertionError: docs/preregistration/HML_VALUE_TEST_2026-11-22.md states a tally but never the settled ('0', '11', '3'): []
```

**Root cause: the values were right, the format was not.** The document wrote the tally as
`` `0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN over 14 rows` `` with three defects:

1. no `TALLY:` prefix, so the canonical `TALLY_RE` never matched it (it requires the prefix);
2. the phrase *over 14 rows* instead of the canonical `(14 rows)`;
3. the figure was split across a hard line break between `0 INVESTABLE / 11` and
   `NOT_INVESTABLE / 3 UNKNOWN`, so even the loose discovery regex could not match a full
   triple on one line.

The loose discovery pattern still matched the second physical line (`11 NOT_INVESTABLE / 3
UNKNOWN` fragment does not match on its own either, but the earlier `0 INVESTABLE / 11`+`NOT_INVESTABLE` join across lines was what the report saw). Either way: the document was found by
discovery, and then could not satisfy the canonical check.

**What changed.** One line only, `docs/preregistration/HML_VALUE_TEST_2026-11-22.md` §7:

```diff
-- It does not change any tally row. The programme tally stays `0 INVESTABLE / 11
--  NOT_INVESTABLE / 3 UNKNOWN over 14 rows` — HML moved from UNKNOWN to
--  NOT_INVESTABLE on the run recorded in §8.
++- It does not change any tally row. The programme tally stays
++  `TALLY: 0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)` — HML moved from
++  UNKNOWN to NOT_INVESTABLE on the run recorded in §8.
```

No number changed. The claim in the sentence ("HML moved from UNKNOWN to NOT_INVESTABLE on
the run recorded in §8") is untouched.

**Verification.**

Before:
```
...............F...............                                          [100%]
1 failed, 30 passed in 0.46s
```
After:
```
...............................                                          [100%]
31 passed in 0.35s
```

Run as `python3 -m pytest -q tests/test_edge_research_tally_consistency.py tests/test_m1_cost_provenance.py`.

**Why this is the right fix and not a test change.** The test's contract is that the settled
figure is stated in one canonical form, so a reader or a script can grep it. Relaxing the
regex to accept "over 14 rows" would make a second format authoritative and reintroduce the
drift class the test exists to catch. Fixing the one prose line keeps a single canonical form.

**Related.** The same defect was reported by Zoo Code (`updates/2026-11-23-coms-status-update-and-proximity.md` §0) against `origin/main`, which is where the failing line was first observed. This repair lands it.
