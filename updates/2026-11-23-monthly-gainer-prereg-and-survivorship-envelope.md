# 2026-11-23 — Monthly top-gainer pre-registration (H-239/H-240) + survivorship envelope (H-241)

## What was broken / missing

1. The monthly top-gainer question had been deferred for the wrong reason: the ranking document said
   "~24 monthly rows available, 48 needed", which was true only of the 105-week weekly panel. The 6-year
   daily panel behind H-237/H-238 yields ~71 months. Nobody had written down which sample the monthly
   test is allowed to use, or what minimum would make it legitimate — so any future run could have chosen
   its own bar after seeing the answer.
2. H-201's universe carries `PARTIAL_NON_DELISTING_AWARE`: 44 names, every one still trading at the end
   of the window. That is the survivorship signature (additions present, removals absent). Attempts to
   procure delisted prices had never been recorded as *attempts*, only as an open ask.

## What changed

- **`plans/2026-11-23-prereg-H-239-H-240-monthly-top-gainer.md`** — pre-registes both monthly
  hypotheses with the observation requirement **written before any run**: **≥ 48 scored monthly periods**
  and **≥ 15 symbols of breadth per period**, derived in the document from the base rate (48 at
  p0=0.135, 69 at p0=0.10, one-sided α=.05, power .80). Below 48 periods the only permitted status is
  `UNTESTED / DATA_GAP`, never "no edge found". Features are frozen to the pairs the weekly holdout
  model already used; benchmark frozen to the universe mean.
- **`plans/2026-11-23-prereg-H-241-survivorship-envelope.md`** — pre-registers the envelope that
  replaces "remove the bias" with "bound the bias", including the acceptance corner (6%/yr hazard,
  −50% haircut) and the rule that the baseline cell must reproduce the published H-236 result or the run
  is INVALID.
- **`reports/hypothesis_registry.json`** — H-239, H-240, H-241 appended under
  `monthly_gainer_and_survivorship_2026_11_23`, all `UNTESTED`, each with a `banned_check` naming what
  it is *not* a re-test of. File re-validated as JSON after the write (114 `H-NNN` ids).
- **`tools/h241_survivorship_envelope.py`** + artifact — the envelope, run after the registration.
- **`reports/h241_survivorship_envelope_2026-11-23.md`** — the finding.

## What was measured (not assumed)

- **Delisted-price procurement failed, and now says so with evidence:** yfinance returned no data for
  **30 of 37** known dead tickers (the 7 that returned data are recycled live tickers); Stooq returned a
  JavaScript proof-of-work challenge body instead of CSV.
- **The envelope:** baseline reproduces published H-236 exactly (mean **9.407 bp/day**, CI-LB **−3.147**,
  n=1254, 44 names). At the pre-registered pessimistic corner (6%/yr, −50%) the mean falls **1.267 bp/day**
  to 8.140. At the worst corner (10%/yr, −70%) it falls **2.644 bp** to 6.763.
- **The finding that matters:** the baseline CI half-width is **12.673 bp** — ~10× the corner stress and
  ~4.8× the worst stress. So **delisting bias is not what blocks H-201; the 5-year sample is.** Buying a
  delisted-price source would tighten the interval by ~1.3 bp. Verdict label per the pre-registered rule
  is `NOT_SURVIVES` (every hazard>0 cell has CI-LB ≤ 0), but it fails for the same reason the baseline
  does, and the report states that rather than letting the label imply delisting was decisive.

## Verification

- `python3 tools/h241_survivorship_envelope.py` → reproduces published H-236 `books.PIT_44`
  (mean 9.407, CI-LB −3.147) to the last digit; writes 13-cell grid; exit 0.
- `python3 -c "import json;json.load(open('reports/hypothesis_registry.json'))"` → OK.
- Both tools compile (`py_compile`).
- No production code touched; no tests weakened; no verdict moved — **0 of 10 classes investable**
  before and after.
