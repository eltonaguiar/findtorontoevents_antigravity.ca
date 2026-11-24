# 2026-11-23 — provenance-gap annotation, stale pilot line, registry count

Base: `origin/main` at `5e403d5f97cd3a8ab65e74a7c69c54430ced249d`.
Worktree used for verification: `/tmp/b35` (detached), never the shared working tree,
which sits on the local-only `push/phase2-round-2026-11-22` branch.

## Fix 1 — AGENTS.md registry count was wrong (56 said, 59 true)

**What was broken.** The "Audit status 2026-11-23" note under the Path Registry
claimed `all 56 paths in the table above were re-checked`. The table grew when the
peer-claim entries were added (commit `eccdd04`), so the number was stale.

**Counted, both ways, on main:**

- `grep -c '^| `' AGENTS.md` → **59** (whole file)
- rows inside the registry table alone (header `| Path | What it is |` to the first
  blank line) → **59**

Both agree because the registry is the only backticked-row table in the file, so
the note should state **59**. Every one of the 59 paths was then checked to exist
on main with `git cat-file -e origin/main:<path>` (dirs for `**` rows): 0 missing.

**What changed.** Only the numeral, 56 → 59, in that note. Corrected sentence:

> **Audit status 2026-11-23:** all 59 paths in the table above were re-checked with `git ls-tree origin/main` and exist on main.

**Verified by.** The two counts above and the 0-missing existence loop.

## Fix 2a — B11 provenance gap in the frozen HML pre-registration

**What was broken.** `docs/preregistration/HML_VALUE_TEST_2026-11-22.md` cites
`[SRC: tools/capacity_model.py:49]` for the 4.32% policy rate, but
`tools/capacity_model.py` does not exist on `origin/main`:

```
$ git ls-tree origin/main -- tools/capacity_model.py       # (no output)
$ git ls-tree origin/main -- tests/test_capacity_model.py  # (no output)
$ git ls-tree -r origin/main --name-only | grep -i capacity_model  # (no output)
```

The `[SRC:]` citations are at lines 117, 122, 133, 149, 200, 258, 277, 291, 297,
307, 313 and 314. The 4.32% hurdle is therefore not reproducible from the repo.

**What changed.** Nothing in the existing text. The pre-registration is frozen, so
no cited line, no figure, no kill rule and no verdict was touched. An additive
blockquote was inserted after §5's closing paragraph (after "Passing the kill rule
is **not** a promotion…"), before §6:

> **Provenance gap (recorded 2026-11-23).** This document cites `tools/capacity_model.py:49` for the 4.32% policy rate, but that file is absent from `origin/main` (verified with `git ls-tree origin/main -- tools/capacity_model.py`, which returns nothing; `tests/test_capacity_model.py` is absent too). The 4.32% hurdle is therefore not reproducible from the repository as of that date. This changes neither the binding test (at most 4.32% at the gross-signal level) nor the KILL verdict, which is driven by the gross signal, not by the cost model. See `docs/edge_research/29_NEXT_STEPS_2026-11-23.md` item 2 and `updates/2026-11-23-peer-claim-verification.md` (B11).

**Tally-test safety.** `tests/test_edge_research_tally_consistency.py` discovers
every `docs/**/*.md` containing a `CLAIM_RE` triple
(`N INVESTABLE / N NOT_INVESTABLE / N UNKNOWN`) and requires the settled
`0/11/3` plus no stale triple outside an exempted line. The HML doc has exactly
one triple (line 240, `0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN`, the settled
one) and no `TALLY-HISTORICAL-OK` marker. The appended block introduces no triple
at all, and it is a blockquote (`>`) anyway, which `_is_historical` exempts. The
existing line 240 is untouched.

**Verified by.** `python3 -m pytest tests/test_edge_research_tally_consistency.py -q` → see
the run log below.

## Fix 2b — doc 25's stale "pilot 0 closed" line

**What was broken.** `docs/edge_research/25_DRAFT_RANKED_LIST_2026-11-23.md` says
the CRYPTO paper pilot has 0 closes (table row 7, §2.3 line "3 rows, all OPEN,
0 CLOSED", and the summary table). The log on main has moved.

**Counted, from main (not the working tree).** The pilot log is
`verified_strategies/paper_pilot/crypto_intraday_sim_paper_log.jsonl`:

- 12 rows total: **5 CLOSE**, 7 OPEN
- CLOSE close-dates: **2026-11-20 → 2026-11-22**
- CLOSE entry timestamps: **2026-11-19T16:00:00+00:00 → 2026-11-20T20:00:00+00:00**
- slots closed: `vwap_reversion` (H-2026-11-19-01, 3), `bollinger_mr` (H-2026-11-19-02, 2)

**What changed.** No existing sentence was deleted or rewritten. An additive
blockquote was inserted directly after the "**n:** **3 rows, all OPEN, 0 CLOSED.**"
bullet in §2.3:

> **Update 2026-11-23:** the pilot log now shows 5 CLOSE rows (close dates 2026-11-20 to 2026-11-22; entry timestamps 2026-11-19T16:00Z to 2026-11-20T20:00Z). The "0 closed" figure was accurate when written; see `verified_strategies/paper_pilot/crypto_intraday_sim_paper_log.jsonl` on `origin/main` (12 rows: 5 CLOSE, 7 OPEN). The verdict below is unchanged: 5 closes is far below the n >= 100 gate, so the class remains `PENDING_N`.

The surrounding reasoning (Net PF CI-LB `UNMEASURED`, kill triggers not
evaluable, `PENDING_N` verdict) is left as written; only its input moved.

**Verified by.** The row count and timestamp extraction above.

## Not changed

- `docs/edge_research/29_NEXT_STEPS_2026-11-23.md` (the defect list this fixes)
- Any figure, kill rule or verdict in the HML pre-registration
- `verified_strategies/paper_pilot/*` logs themselves
