# 2026-11-14 — CI could not run any tests (pandas alias), and B13's counts were false

Two fixes from reviewing the day's peer packages. One unblocks the whole gating
suite; the other corrects a fabricated number in my own bug report.

## 1. What was broken — the gating suite aborted on collection

`tests/test_combined_book_sleeves.py:17` built a date range with `freq="ME"`.
That alias was introduced in pandas 2.2. `requirements.txt` pins **pandas==2.1.4**,
so CI raised:

```
ERROR collecting tests/test_combined_book_sleeves.py
E  ValueError: Invalid frequency: ME
!!! Interrupted: 1 error during collection !!!
================= 10 skipped, 87 deselected, 1 error in 21.15s =================
```

One collection error aborts the run, so **6,714 tests never executed** — on every
commit. It had been failing at 21:06Z, 21:13Z, 21:40Z and 22:00Z on `main`, i.e.
before and after my stop-fill merges, so it was not a regression from that work.

Local runs passed because this machine has pandas 2.2.3, where `"ME"` is valid. That
local-vs-CI divergence is exactly why AGENTS.md says to smoke-test the production
invocation rather than the import.

## 2. What changed

`tests/test_combined_book_sleeves.py`:

```python
- _MONTH_ENDS = pd.date_range("2025-01-31", periods=13, freq="ME")
+ _MONTH_ENDS = pd.date_range("2025-01-31", periods=13, freq=pd.offsets.MonthEnd())
```

`MonthEnd()` is the underlying offset object and is valid on 2.1 and 2.2+, so this does
not need a version guard.

## 3. Second fix — B13's GitHub Actions counts were invented

`final_v3/00_common_themes/BUGS.md` B13 read: "360 workflow files; **0** have
`concurrency:`, **0** have `timeout-minutes:`". Both false. Independent scan of
`origin/main`:

| measure | value |
|---|---:|
| workflow YAML files | 360 |
| with `concurrency:` | 161 (199 without) |
| with `timeout-minutes:` | 271 (89 without) |
| with `push:` | 39 |

A peer package (`final_v3/feat-stop-fill-cost-gate-final-v3/02-improvement-plan/GITHUB_ACTIONS_FIXES.md`)
caught it and its numbers match mine exactly. An earlier PR body of mine stated the
same fact correctly ("199 lack `concurrency`"), so two of my documents disagreed and the
wrong one shipped. The paragraph is corrected *in place*, with the error and the
correction left visible — a bug report containing a fabricated count is the exact
failure class it is documenting.

The conclusion does not change: 199 workflows that can race on overlapping outputs is
still the defect, and `push:` still exists on 39 of them.

## 4. Verification

- `python3 -m pytest tests/test_combined_book_sleeves.py -q` — passes locally; the
  assertion no longer depends on a version-specific alias.
- The 66 stop-fill/cost-gate/COT tests still pass.
- CI confirmation requires the post-merge run, since this machine has pandas 2.2.3 and
  cannot reproduce 2.1.4 behaviour directly. Stated as a limitation, not a pass.

## 5. Peer review record

The full review — including three false claims in the peer package, five colliding
`B14` definitions, and `final_v4` being stale within ten minutes of its own
timestamp — is in `final_v3/07_peer_review/PEER_WORK_REVIEW_2026-11-14.md`.
