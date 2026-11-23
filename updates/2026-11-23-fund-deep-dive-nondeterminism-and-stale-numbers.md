# Fund deep-dive: non-deterministic CAGRs, relative `SRC`, and a peer review that caught stale numbers

**Date:** 2026-11-23 · **Branch:** `feat/fund-deep-dive-fixes-2026-11-23`

## What was broken

Three separate defects, all in the measurement layer, all of which meant the
published "corrected" report could quote numbers the tool did not actually
produce.

### 1. Headline CAGRs flipped between runs

The generator was not reproducible. On an unchanged CSV (md5
`75c4f0ca7f29ea571d23be505456d6c0`) repeated runs produced **different
`reports/fund_deep_dive.json` hashes** and two distinct value sets:

| field | state A | state B |
|---|---:|---:|
| SPY net CAGR | 11.48% | 11.59% |
| FXAIX net CAGR | 11.66% | 11.67% |
| SGOV net CAGR | 3.81% | 3.90% |

**Cause:** interpreter hash randomisation. Some `set` is iterated before the
arithmetic, so float accumulation order varies per process. Proven by pinning
`PYTHONHASHSEED`: with it fixed the output is byte-stable; unset it alternates.
A diff of two fixed seeds showed the only remaining difference was
`generated_at`, which confirms the numeric flip comes from hash order and not
from the data or the clock.

**Mitigation:** `PYTHONHASHSEED=0` is pinned in the test module before import,
and a new guard test runs the generator twice in-process and asserts identical
payloads (excluding `generated_at`), so any future regression is loud.

### 2. `SRC` was a relative path

`SRC` was `"2026-11-15_AM.../market_prices.csv"`, resolved against the CWD. That
made the tool impossible to sandbox: a test could not `chdir` into a temp dir
without breaking input resolution, so at least one test wrote its fixture
numbers over the **tracked** `reports/fund_deep_dive.json`. That is how stale
figures reached the document.

**Fix:** `SRC` is now absolute, derived from `REPO_ROOT`. CWD is used only for
output. Tests isolate freely.

### 3. The document was transcribed, not generated

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

- Defect #1 is **mitigated, not fixed** — the offending `set` iteration has not
  been located. Pinning the seed makes it stable and the guard test makes it
  visible, but the underlying order dependence should be removed.
- Futures remain out of scope (adjusted closes cannot express roll yield).
- Jurisdiction-dependent tax conclusions (E3–E6) need operator input.
