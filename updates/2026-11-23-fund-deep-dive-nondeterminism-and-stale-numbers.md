# Fund deep-dive: relative `SRC`, a transcribed table, and a peer review that caught stale numbers

**Date:** 2026-11-23 · **Branch:** `feat/fund-deep-dive-fixes-2026-11-23`

> **ERRATUM.** An earlier version of this file claimed the generator produced
> non-deterministic headline CAGRs "because a `set` is iterated before the
> arithmetic". **That diagnosis was wrong and is withdrawn.** See
> §"Withdrawn claim" below for the measurements that refute it and for what
> actually happened.

## What was broken

Two real defects in the measurement layer, both of which let the published
"corrected" report quote numbers the tool did not actually produce.

### 0. Withdrawn claim — "headline CAGRs flipped between runs"

I reported two "value sets" and blamed interpreter hash randomisation. It is
tempting to leave this because the *symptom* I saw was real, but the *cause*
was not, and the fix I shipped (pinning `PYTHONHASHSEED`) addressed nothing.

**What actually happened:** I was reading two different JSON fields in
different sessions and treating them as one.

| fund | `cagr_pct` (gross) | `net_cagr_pct` (net) | MER |
|---|---:|---:|---:|
| FZROX | 10.74% | 10.74% | 0.000% |
| FXAIX | 11.67% | 11.66% | 0.015% |
| VTSAX | 10.52% | 10.48% | 0.040% |
| SPY | 11.59% | 11.48% | 0.0945% |
| VTI | 10.53% | 10.49% | 0.030% |
| BND | −0.29% | −0.32% | 0.030% |
| SGOV | 3.90% | 3.81% | 0.090% |

The gap between the two columns is **exactly each fund's expense ratio**, and
**FZROX has a 0.00% MER and is identical in both** — which is the tell. The
"two value sets" were gross and net, not two runs.

**Proof the generator is reproducible:** five consecutive runs produce an
identical content hash once `generated_at` is dropped —
`b72059a1ab55e7ee` on all five. And a diff across eight `PYTHONHASHSEED`
values (0–7) shows no numeric difference whatsoever. The only run-to-run
variation is the `generated_at` timestamp, which is expected.

**What the misdiagnosis cost:** a commit message and this file both asserted a
bug that does not exist, and the shipped "mitigation" was a no-op that would
have quietly masked a future *real* determinism regression. The seed pin has
been removed; the run-twice guard test is kept, with an honest docstring, as a
forward-looking check.

**What is worth keeping from this:** `cagr_pct` and `net_cagr_pct` sit
adjacent in the payload and differ by roughly the MER, which makes them easy to
confuse when reading output by eye. There is now a test,
`test_net_cagr_is_exactly_gross_minus_the_fee`, that pins the A6 compounded
relation `net = (1+gross)(1−mer)−1` for every fund.

### 1. `SRC` was a relative path

`SRC` was `"2026-11-15_AM.../market_prices.csv"`, resolved against the CWD. That
made the tool impossible to sandbox: a test could not `chdir` into a temp dir
without breaking input resolution, so at least one test wrote its fixture
numbers over the **tracked** `reports/fund_deep_dive.json`. That is how stale
figures reached the document.

**Fix:** `SRC` is now absolute, derived from `REPO_ROOT`. CWD is used only for
output. Tests isolate freely.

### 2. The document was transcribed, not generated

The "corrected" report's measured table had been copied by hand. It disagreed
with the CI table further down the same file, and a peer review noticed the
inconsistency before I did.

**Fix:** `tools/gen_corrected_table.py` regenerates the table directly from the
JSON. Human copy step removed.

## The peer review

Run locally against `Qwen3.6-35B-A3B-NVFP4` on vLLM (`tools/fund_peer_review.py`;
Ollama 32B models OOM while vLLM holds the GPU). Asked for the single strongest
remaining objection, adversarial.

The reviewer's reasoning focused on an apparent mismatch between the measured
table (FXAIX 11.66 / SPY 11.48 → 0.18pp apart) and the paired difference
(net +0.131pp). It talked itself out of it as rounding. **It was right to
flag it and wrong about the cause** — the real cause was defect #3 above, plus
defect #1 meaning the two tables had been produced by different runs.

That is the useful outcome: a local 35B model, given no access to the code,
located the one internal inconsistency in a document I had just written.

## Verification

- `tests/test_fund_metrics.py` — **34 passed**
- Guard tests added: `test_generator_is_byte_stable_across_runs`,
  `test_L1_adjusted_closes_reinvest_dividends`,
  `test_corrected_doc_numbers_match_the_json`
- `reports/fund_deep_dive.json` regenerated from the corrected code
- CSV unchanged (`75c4f0ca7f29ea571d23be505456d6c0`) — the fix changed the tool, not the data

## L1 — the assumption that could have invalidated everything

Whether the adjusted closes reinvest dividends had never been checked. Settled
with **SGOV as a control**: a 0-3 month T-bill ETF whose NAV is pinned near $100
and which distributes its full yield monthly. Price-only ⇒ ~0%/yr.
Total-return ⇒ tracks the T-bill rate.

Observed **83.12 → 100.56 = +3.90%/yr**. A price-only series cannot do that, so
the CAGRs are total-return. BND corroborates: NAV fell ~3%/yr yet the series
returns −0.32%/yr, i.e. ~3pp/yr of distributions are in there.

## Still open

- Futures remain out of scope (adjusted closes cannot express roll yield).
- Jurisdiction-dependent tax conclusions (E3–E6) need operator input.
