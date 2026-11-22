# Final verification sweep and tally-drift fix (2026-11-22)

Read-only research record. Not investment advice. The settled tally for this
programme is **`TALLY: 0 INVESTABLE / 10 NOT_INVESTABLE / 4 UNKNOWN (14 rows)`**.

## Answer

**Yes** - `0/10/4` now holds across every document in the repo that states a tally.

Before this sweep it did not. [`docs/EDGE_CANDIDATES_2026-11-22.md`](../docs/EDGE_CANDIDATES_2026-11-22.md)
carried the stale pre-reconciliation `0 INVESTABLE / 8 NOT_INVESTABLE / 6 UNKNOWN`.

## Test results, verbatim

Before any change (`tests/test_edge_research_tally_consistency.py` +
`tests/test_m1_cost_provenance.py`):

```
.................                                                        [100%]
17 passed in 0.16s
```

That green run was the defect: it passed while a fourth document was wrong.

After the fix:

```
...........................                                              [100%]
27 passed in 0.33s
```

The 27 = 17 original + 10 new (4 discovered-document checks, 1 coverage guard,
5 classifier cases).

Fail-before demonstration of the new discovery logic - a scratch file
`docs/_scratch_stale_tally_demo.md` containing a correct line *and* a stale
`0/9/5` line was created, the test run, then the file deleted:

```
E       AssertionError: docs/_scratch_stale_tally_demo.md carries a stale tally outside a historical context: [(5, 'The tally is 0 INVESTABLE / 9 NOT_INVESTABLE / 5 UNKNOWN.')]
FAILED tests/test_edge_research_tally_consistency.py::test_every_document_that_states_a_tally_states_the_settled_one[docs/_scratch_stale_tally_demo.md]
1 failed, 18 passed in 0.30s
=== SCRATCH REMOVED ===
scratch file gone
..................                                                       [100%]
18 passed in 0.29s
```

## Drift diagnosis (one sentence)

The consistency test discovered nothing - it checked a **hardcoded dict of three
paths** (`DOCS = {"15": ..., "22": ..., "23": ...}`), so any document outside that
list could carry any tally and no assertion would ever read it.

## Document corrected

[`docs/EDGE_CANDIDATES_2026-11-22.md`](../docs/EDGE_CANDIDATES_2026-11-22.md) line 10,
now in canonical form:

```
TALLY: 0 INVESTABLE / 10 NOT_INVESTABLE / 4 UNKNOWN (14 rows)
```

**Conclusions unchanged.** VALUE stocks and PEAD are still `UNKNOWN` with every
metric unmeasured rather than quoting unrun code - that honesty is the point of
the document and it survives verbatim. Two things changed beside the count:

- One clause was added noting the UNKNOWN table below predates the count and
  still enumerates six rows, two of which doc 23 now classes NOT_INVESTABLE. The
  table itself was left alone rather than rewritten.
- Its `## The 6 UNKNOWN rows` heading and table are unchanged - they are the
  historical six-row view, not a claim about the settled count.

## Structural hole closed

[`tests/test_edge_research_tally_consistency.py`](../tests/test_edge_research_tally_consistency.py)
now **discovers** documents: `_tally_documents()` globs `docs/**/*.md` and keeps any
file whose text contains a tally-like claim
(`<a> INVESTABLE / <b> NOT_INVESTABLE / <c> UNKNOWN`). For each discovered file,
`test_every_document_that_states_a_tally_states_the_settled_one` asserts:

1. the document states the settled `0/10/4` at least once, and
2. no line states a different tally unless that line is classified historical.

The claim pattern for discovery is deliberately looser than the canonical one -
no `(N rows)` suffix required - so a stale figure is caught even when it is not
written in canonical form.

## Historical-tally opt-out convention adopted

A line quoting an OLD tally as history is exempt when **any** of these holds:

| Rule | Used for |
|---|---|
| It carries the explicit marker `TALLY-HISTORICAL-OK` | The convention going forward |
| It is a blockquote (`> ...`) | Correction notices are conventionally quoted - covers doc 22's and doc 23's |
| It contains a history cue (`unchanged`, `supersedes`, `previously`, `earlier`, `first version`, `recompute[sd]?`, `corrected`) **and** lives in a document that also states the settled tally | Covers doc 15's inline "supersedes an earlier" line, doc 22's M1/M3 notes, and the `updates/` records |

Why these three rather than one: the explicit marker is the durable convention,
but the correction notes in docs 15/22/23 were already written and are legitimate
history - requiring them to be edited would mean touching the three settled
documents, which this sweep is explicitly not for. The cue rule is deliberately
gated on the document already being correct: a document whose *only* figure is
stale can never be excused by a word like "unchanged". That gate is pinned by
`test_historical_classifier`, which asserts the same "unchanged" line is exempt
in a correct document and **fails** in an otherwise-stale one.

## Settled documents untouched

`docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md`,
`22_FINAL_SYNTHESIS_2026-11-22.md` and `23_DEFINITIVE_ANSWER_2026-11-22.md` are
byte-identical before and after (sha256 32732c68..., 570b4d7a..., 079c7b7f...).
They were dirty in the working tree from earlier work; this sweep neither edited
nor committed them.

## Scope notes

- No push, no `origin/main`, no destructive git.
- `tools/momentum_core.py` untouched.
- `check_active_picks.py` and `alpha_engine/smart_picks_engine.py` never run.
- Foreign dirty entries in the tree (paper-trading sim data, audit-review docs,
  the three edge-research documents, protocol acks) were excluded from the commit.
