# Peer work review — 2026-11-14

Review of what other agents committed or left in flight today, including the
11-file package `final_v3/feat-stop-fill-cost-gate-final-v3/` produced by the
Copilot session whose transcript is quoted in this thread.

**Reviewed:** 44 peer Markdown files under `final_v3/{feat-stop-fill-cost-gate-final-v3,
childlike-airport, quant-audit-2026-11-14, finpredict}` and `final_v4/{finpredict-v4,
childlike-airport}`, read in full for the new package and both final_v4 summaries, plus
the 13 commits touching review packages today.

**Not reviewed:** the 309 unique remote Markdown blobs and ~600 dirty paths the peers
themselves declined to read. No claim below covers those.

---

## Verdict

The new package is the strongest of the batch, and it corrected two of my errors.
It also contains three claims that are false, one of which is a *fabricated number*.
`final_v4` was materially stale within ten minutes of being written. And one
structural defect — bug-ID collisions — makes "14 bugs (B1–B14)" unreadable
across packages.

---

## 1. What the peers got right, and where they corrected me

### 1.1 My GitHub Actions counts were fabricated — they caught it

`final_v3/00_common_themes/BUGS.md` B13 said **"0 have `concurrency:`, 0 have
`timeout-minutes:`"**. That is false. Independent scan of `origin/main`:

| measure | mine (re-run) | peer claim | agreement |
|---|---:|---:|---|
| workflow YAML files | 360 | 360 | ✅ |
| with `concurrency:` | **161** | 161 | ✅ |
| with `timeout-minutes:` | **271** | 271 | ✅ |
| with `push:` | **39** | 39 | ✅ |

Worse: an earlier PR body of mine said "199 lack `concurrency`" — which is the
same fact stated correctly as 360−161. So two of my own documents disagreed and
the wrong one shipped. Corrected in BUGS.md with the error left visible.

### 1.2 The FDR / single-source gates really are off by default

Verified at `alpha_engine/money_ready_verdict.py:180` and `:195` on `main`:
`MONEY_READY_FDR_GATE` and `MONEY_READY_SINGLE_SOURCE_GATE` both default to `"0"`.
This resolves an item I had left flagged as "unverified in main tree" — I had been
searching for `_FDR_GATE_ENFORCE`, a name that does not exist. Their anchor is correct.

### 1.3 The cost gate's fail-open policy — behaviour confirmed, critique adopted

They cite `tools/per_class_cost_gate.py:29,152-179`. Confirmed: unknown class, thin
sample, or a stale index all return `{}` → PASS, and `hc_gates_python.py:530-536`
returns `True` on a gate exception. That is deliberate (documented in the module
docstring: "it must never silence a class merely because bookkeeping is absent") and
correct **for emission control** — you do not halt production because a JSON is missing.

But their framing exposes a real gap: **the same code path must not be reused for
promotion.** A readiness verdict that treats *unmeasured* as *allowed* advertises a
class as ready on no evidence. Adopted as their G5: emission stays fail-open,
promotion must fail closed with `INSUFFICIENT`.

### 1.4 The mutual-fund cache inventory is accurate

`mutual_fund_nav_cache`: 46 CSVs. `mf_backtest_cache`: 72 files. Both match. Their
correction of a "MF data absent" claim is right, and it does not contradict my own
position — I said the ledger has **no `MUTUAL_FUND` class label**, not that no NAV
data exists. Worth keeping those two claims separate so it does not harden into a
false contradiction (their ADJUDICATION table lists it as one).

---

## 2. Where the peers are wrong

### 2.1 "16/25 EQUITY stops untouched" — a fabricated composite

Their ADJUDICATION §2 says: "one reports 16/25 EQUITY and 13/25 ETF stops untouched;
another reports 14/25 and 10/25." I grepped all 44 peer Markdown files: **the only
occurrence of `16/25` in the entire tree is that sentence.** No report contains it.

Actual measured numbers:

| class | untruncated | truncated at recorded exit |
|---|---|---|
| EQUITY | 14/25 never | **14/25 never** |
| ETF | 10/25 never | **13/25 never** |

So their "14/25 and 10/25" is exactly my untruncated pair, and "13/25" is my
truncated ETF — but "16/25 EQUITY" exists nowhere. They welded a truncated ETF
number to a non-existent EQUITY number and presented the pair as one report.

Their **conclusion** is right and I had already acted on it (the `--truncate-at-exit`
flag exists because untruncated replay can manufacture touches). But a review that
inventing a number while accusing six packages of unreliable numbers is not usable as
an audit trail without the correction.

### 2.2 `final_v4` is stale within ten minutes of its own timestamp

`final_v4` (21:50Z) states as known: `kimi_riseoftheclaw` = "+727.3pp overshoot",
"98.8% of class loss", "honest PF after fix ~1.00 (breakeven)", "52 tests", "EQUITY
alpha/beta unknown — SPY test not yet run", and "`feat/stop-fill-cost-gate-final-v3`
pushed but not PR'd". Every one of those was superseded before it was written:

| final_v4 claim | status at 22:01Z |
|---|---|
| kimi leak +727.3pp | **+67.5pp** (#773) — the larger figure measured a drifted field, not the fill |
| 98.8% of class loss | artifact of the same field |
| CRYPTO PF ~1.00 breakeven | **~0.80** |
| 52 tests | **66** |
| SPY benchmark not run | **run and FAILED**: t=1.05, mean excess +0.21%, median **−0.57%** |
| branch "not PR'd" | was **PR #771, merged 21:40Z** — ten minutes earlier |

Its headline — "two deployable candidates" — rests on both legs, and both are now false.
The synthesis is useful as a map of the argument, not as a statement of current fact.

### 2.3 CI was red, and nobody read the log

`final_v4` claims "all GHA workflows green". The new package correctly notes CI run
`43644095951` failed on both Python versions — but logs were not inspected, so it is
filed as an unexplained regression on my merge commit.

The actual cause, from `--log-failed`:

```
ERROR collecting tests/test_combined_book_sleeves.py
E  ValueError: Invalid frequency: ME
!!! Interrupted: 1 error during collection !!!
```

`requirements.txt` pins **pandas==2.1.4**; `freq="ME"` is a pandas ≥ 2.2 alias. One
collection error aborts the entire gating run — **6,714 tests never executed**, on any
commit. It also failed at 21:06Z and 21:13Z, *before* my merge, so it is not a
regression from the stop-fill work. Fixed today by using `pd.offsets.MonthEnd()`.

Consequence worth stating plainly: **no package's "tests pass" claim today was
CI-verified.** Mine included — my 66 passes were local, on pandas 2.2.3, where the
alias happens to work. That is the local-vs-CI divergence AGENTS.md warns about.

---

## 3. The conflict nobody reconciled

Two packages in the same tree, same day:

- `childlike-airport` ranks **Crypto Vol-Targeted TSMOM #1** on "7.4y CAGR 23.0%,
  **Sharpe 2.13**, PF 1.40, MDD −17.4%".
- `quant-audit-2026-11-14/00_summary/CROSS_PEER_REVIEW_REPORT.md` downgrades
  ITERATION-005 precisely because it was "tested vs zero, not vs B&H; **B&H Sharpe ≈ 2.2**".

2.13 < 2.2. The flagship candidate **loses to buy-and-hold on the metric it is being
praised for**, and neither package reconciles it. This is the identical test I ran on
EQUITY — which failed at t=1.05 with a negative median. Until TSMOM is run against a
risk-matched benchmark, it occupies the slot EQUITY just vacated for the same reason.

---

## 4. Structural defect: bug IDs collide across packages

`B14` means five different things in five packages:

| package | what B14 is |
|---|---|
| `final_v3/00_common_themes/BUGS.md` | epistemics — six reviews, one dataset |
| `final_v3/childlike-airport` | regime layer ~0.25% coverage |
| `final_v3/06_followups` (mine) | cross-symbol stop contamination |
| `final_v4/finpredict-v4` | same epistemics item, re-used |
| `final_v4/childlike-airport` | CI failures/cancellations |

`B1` means three things (refuted-VWAP-still-`VALIDATED` / EXPIRED→WON / `pnl *= 100`).
So "14 bugs (B1–B14)" and "fixed B2, B3, B12" cannot be resolved without opening each
package. Namespace them (`QA-B3`, `CA-B3`) or keep one registry; otherwise peer
"convergence" on bug counts is a coincidence of numbering.

---

## 5. Ranking

| # | Package | Strength | Main weakness |
|---|---|---|---|
| 1 | `feat-stop-fill-cost-gate-final-v3` | Best epistemics in the tree: confidence labels, refuses SubQ, refuses peer-agreement-as-evidence, catches real gate defects, states its own limits | Never ran anything; one fabricated number; stale on the kimi magnitude |
| 2 | `quant-audit-2026-11-14` | Sharpest adjudication — downgrades ITERATION-005 for testing vs zero, catches the VWAP label | Origin of several superseded magnitudes |
| 3 | `childlike-airport` | Broadest bug inventory, concrete MF tickers with ER/min/load | IDs collide; #1 candidate fails its own benchmark |
| 4 | `final_v4` | Good narrative synthesis, merges the 90-day plans | Stale within 10 min; inherits both false legs |
| 5 | `final_v3/finpredict` | Reads as a structured comparison | "SubQ" labelled with no invocation artifact — peers correctly refuse it |

---

## 6. Changes made in response

1. `final_v3/00_common_themes/BUGS.md` — B13 counts corrected to 161/199, 271/89, 39,
   with the error and the correction left visible.
2. `tests/test_combined_book_sleeves.py` — `freq="ME"` → `pd.offsets.MonthEnd()`, which
   unblocks the gating suite on the pinned pandas 2.1.4.
3. This review.

Deliberately **not** changed: peer documents. Their files are theirs; this is a
review, not an edit war. The one exception is my own BUGS.md.
