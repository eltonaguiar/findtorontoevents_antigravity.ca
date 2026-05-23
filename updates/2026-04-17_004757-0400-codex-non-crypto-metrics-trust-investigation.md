# Codex Investigation — Non-Crypto Metrics Trustworthiness

**Agent:** Codex  
**Created:** 2026-04-17 00:47:57 -0400  
**Scope:** Investigate whether the non-crypto asset-class stats feeding `findtorontoevents.ca/audit` are trustworthy.

## Executive verdict

I do **not** trust the non-crypto dashboard cards as a clean "raw historical truth" view.

They are a **policy-filtered health view**, not a pure all-history performance report:

1. The card `closed` count is taken from the raw asset-class bucket.
2. The card `win_rate` / `profit_factor` / `pnl` are computed from a **smaller validity-filtered subset**.
3. Large parts of equity / forex / ETF / futures history are excluded from metrics because they now match `historical_blocked_pick` or corruption rules.

That makes the cards useful as a **current forward-looking screened view**, but not trustworthy as a plain statement of "how this asset class has actually performed overall."

## What production is actually showing

I verified the live production payload at:

- `https://findtorontoevents.ca/audit/data/dashboard_data.json`

Exact production payload stamp:

- `generated_at`: `2026-04-17T04:24:31.521354+00:00`
- `repo_sha`: `64506fe56d421661aa9277b93a4e05d37261957d`
- `last_code_change_at`: `2026-04-17T03:37:27+00:00`

Important: production is **not** stamped to this workspace's current `HEAD` (`2940ba6c2c043c05fe77e3f16cffa8b69d84f608`). So "repo state" and live `/audit` state are already separated.

Current live asset-class card values are:

| Asset class | WR | PF | Closed |
|---|---:|---:|---:|
| EQUITY | 52.0% | 1.39 | 721 |
| FOREX | 45.1% | 0.26 | 1185 |
| COMMODITY | 40.2% | 1.14 | 420 |
| ETF | 48.4% | 0.86 | 74 |
| BOND | 50.0% | 1.60 | 17 |
| FUTURES | 0.0% | null | 19 |

These **do not match** the PF numbers quoted in the request (`1.47 / 1.11 / 1.18 / 0.86 / 1.60`). As of the payload generated on **2026-04-17 04:24:31 UTC**, the live values above are what production serves.

## Why the cards are hard to trust

### 1. Mixed denominators inside the same card

`audit_trail/dashboard_generator.py` builds `performance.by_asset_class` from `active + closed`, but:

- `closed` is incremented for every raw closed row in the bucket
- `wins`, `losses`, `win_rate`, `profit_factor`, `pnl` only use rows that pass `_is_valid_resolved_pick()`

That means the card mixes:

- a **raw closed count**
- with **filtered performance metrics**

So a user cannot reproduce the card metrics from the displayed closed count alone.

## Raw vs filtered reality

I recomputed the generator's own merged `closed` ledger using `collect_all_picks()` and the same `_is_valid_resolved_pick()` filter production uses.

| Asset | Raw closed | Valid for WR/PF | Raw WR | Raw PF | Valid WR | Valid PF |
|---|---:|---:|---:|---:|---:|---:|
| EQUITY | 721 | 350 | 41.96% | 0.94 | 52.03% | 1.39 |
| FOREX | 1185 | 928 | 45.92% | ~0.00 | 45.07% | 0.26 |
| COMMODITY | 420 | 418 | 40.00% | 1.07 | 40.20% | 1.14 |
| ETF | 74 | 63 | 43.84% | 0.71 | 48.39% | 0.86 |
| BOND | 17 | 17 | 50.00% | 1.60 | 50.00% | 1.60 |
| FUTURES | 19 | 0 | 5.26% | 0.06 | n/a | n/a |

This is the core trust issue:

- **Equity flips from loser to winner** once the validity filter is applied.
- **ETF improves materially** after filtering.
- **Futures disappears entirely** from valid metrics.
- **Forex is still bad even after filtering**, which is actually the most believable part of the current non-crypto book.

## Why rows are being excluded

### Equity

- Raw: `721`
- Valid: `350`
- Excluded: `371`

Exclusion reasons:

- `359` = `historical_blocked_pick`
- `12` = paper / auto-expired

Interpretation:

- The current positive equity card is **not** raw equity history.
- It is mostly a **"remove rows from now-blocked toxic equity strategies/symbols"** view.

That may be defensible for a forward-looking dashboard, but it is not the same thing as "equities historically have PF 1.39."

### Forex

- Raw: `1185`
- Valid: `928`
- Excluded: `257`

Exclusion reasons:

- `238` = `historical_blocked_pick`
- `11` = impossible non-crypto price moves
- `5` = corrupted `pnl_pct`
- `3` = paper / auto-expired

Even after those exclusions, forex still looks bad:

- Valid WR: `45.07%`
- Valid PF: `0.26`
- Valid sum PnL: `-982.00%`

Main valid-forex drag:

- `kimi_signal_tracking`: `153` valid rows, `-997.83%` sum PnL

Main valid-forex exit-label problem:

- `LOST`: `453` rows, `-1042.01%`
- `WON`: `303` rows, `+80.88%`

Interpretation:

- Forex is still economically weak after cleanup.
- It also depends heavily on binary `WON`/`LOST` style outcomes instead of transparent TP/SL attribution.
- That makes PF more fragile and less interpretable.

### Commodity

- Raw: `420`
- Valid: `418`
- Valid WR: `40.20%`
- Valid PF: `1.14`

But the book is highly concentrated:

- `multi_asset_copytrader`: `353 / 418` valid rows

Exit labels are mostly generic:

- `LOST`: `235`
- `WON`: `161`

Interpretation:

- Commodity is only barely positive on PF.
- It is too source-concentrated and too dependent on generic outcome labels to call it robust.

### ETF

- Raw: `74`
- Valid: `63`
- Excluded: `11`, all from `historical_blocked_pick`

Interpretation:

- ETF also benefits from current-policy filtering.
- The live `0.86` PF is a filtered number, not the raw all-history PF (`0.71`).

### Bond

- Raw = valid = `17`
- WR `50%`, PF `1.60`

Interpretation:

- Bond is the cleanest non-crypto card mechanically.
- But `n=17` is too small to trust as evidence of durable edge.

### Futures

- Raw: `19`
- Valid: `0`

Interpretation:

- The current futures card is effectively a null set dressed as a bucket.
- It should not be treated as evidence of anything.

## Source concentration matters

The current valid non-crypto metrics are not diversified:

- **Equity valid rows** are dominated by `kimi_riseoftheclaw` and `stocks_competition`
- **Forex valid rows** are dominated by `multi_asset_copytrader` and still heavily damaged by `kimi_signal_tracking`
- **Commodity valid rows** are overwhelmingly `multi_asset_copytrader`
- **Bond valid rows** split across only two sources

That means small upstream behavior changes in a couple of systems can move the asset-class cards a lot.

## Bottom line

If the question is:

- "Can I trust these cards as a raw all-history report card on stocks/forex/commodities/ETFs/bonds?"

My answer is:

- **No.**

If the question is:

- "Can I use these cards as a filtered, current-policy health dashboard after blocked rows and corrupt outcomes are screened out?"

My answer is:

- **Yes, but only with caveats.**

My practical trust ranking right now:

1. **Bond**: mechanically clean, but tiny sample
2. **Commodity**: modestly usable, but too concentrated to claim strong edge
3. **Equity**: current card is usable only as a filtered-health metric, not a raw-history claim
4. **ETF**: still negative after filtering
5. **Forex**: not trustworthy as an edge claim; still materially broken/weak after cleanup
6. **Futures**: effectively non-metric

## Files and functions checked

- `audit_trail/dashboard_generator.py`
  - `collect_all_picks()`
  - `_is_valid_resolved_pick()`
  - `_is_historical_blocked_pick()`
  - asset-class `ac_breakdown` construction
- `audit_trail/quality_gates.py`
  - `is_corrupted_outcome_row()`
- Live payload:
  - `https://findtorontoevents.ca/audit/data/dashboard_data.json`

## Verification performed

1. Pulled the live production payload header/body by HTTP range request.
2. Confirmed live `generated_at` / `repo_sha`.
3. Recomputed raw vs valid asset-class metrics from the generator's own merged closed ledger.
4. Counted exclusion reasons per asset class.
5. Checked top source-system contributors and exit-label composition for valid non-crypto rows.

## Change scope

Documentation only. No code changes were made in this investigation.
