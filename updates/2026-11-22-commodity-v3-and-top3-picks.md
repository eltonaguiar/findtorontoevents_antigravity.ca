# 2026-11-22 — V3 commodity settlement + frozen top-3-per-class register

## What was broken

Two things, both about claims being asserted rather than measured.

1. **Commodity trend** was being cited as "the strongest class result in the project"
   (CAGR +3.59 %, Sharpe 0.431) by one desk while another desk's CI-LB gate rejected the
   same class. Nobody had run the *first* desk's own construction, so the disagreement was
   being argued with two different universes instead of resolved.
2. **"Top 3 per asset class"** was being asked for while six of ten classes had no usable
   measurement. Answering that question with three confident tickers per class would have
   been the single most misleading thing this desk could produce.

## What was changed

- `tools/commodity_tsmom_check.py` — reproduces the peer construction exactly (11 ETFs,
  monthly bars, SMA(10), T-bill cash leg, 20 bp on |Δweight|, lagged signal) and adds four
  things the original lacked: a **zero-cash-rate variant** to price the T-bill contribution,
  **both halves**, **1×/2× cost**, and a **bootstrap CI lower bound** on mean monthly excess
  return. Deterministic, offline-capable via a local cache, `NO_DATA`/`INSUFFICIENT_N` when
  the panel is short — never a number from thin air.
- `reports/2026-11-22-commodity-tsmom-v3-settlement.md` — the settlement write-up.
- `reports/top3_picks_2026-11-22.json` + `reports/2026-11-22-top3-per-asset-class.md` —
  the pre-registered register, with tier, thesis, evidence and a falsifier per pick.
- `tools/top3_pick_tracker.py` — marks the frozen picks to market and appends to
  `data/top3_picks_history.jsonl`. It can add prices and returns; it cannot re-rank, re-tier
  or rewrite a thesis.

## How it was verified

- `pytest tests/test_commodity_tsmom_check.py tests/test_top3_pick_tracker.py` → **13 passed**.
  The commodity tests include a look-ahead test (changing the final month's price must not
  change earlier exposure decisions) and a cost test (20 bp must reduce a compounding series).
  The tracker tests cover `NO_PRICE` and `NO_DATA` — the two ways a tracker lies by omission.
- The V3 run itself: 181 months, 11 members, BH anchor reproduces the peer's buy-and-hold to
  **2 bp of CAGR** — which is what localises the 575 bp TREND disagreement to the signal
  rather than the data.

## What this does not do

Does not refute the peer's number. It is recorded as `NOT_REPRODUCED`, the invested-share
mismatch (86 % vs 43 %) is published as the likely cause, and the ask for his weight function
went out over COMS. Nothing promoted, no class moved to CANDIDATE, zero capital sanctioned.
