# Algorithm Specification — PREDICTION MARKETS (binary contracts)

**Agent:** buffy (Codebuff) · **Date:** 2026-11-15 (rev. 2)
**Status:** `INSTRUMENTED — NOT MEASURED` (settlement and calibration code exists and is tested;
no obtainable price history to score against — see §5)

**Module:** [`tools/pm_binary.py`](../../../tools/pm_binary.py) · **Artifact:** [`artifacts/pm_calibration.json`](artifacts/pm_calibration.json)

---

## 1. Why this class needs its own module

A prediction contract is **not a price series**. It costs `p ∈ [0,1]`, pays exactly `1` or `0` at
settlement, and cannot be marked to market after the close. `tools/sim_path_forward.py` models
returns on continuous instruments; forcing a binary through it invents fills that never existed and
produces the pathology already visible in the ledger — closed rows with `exit_price == entry_price`,
flat closes that carry no information.

So the class gets a settlement-native resolver and its own trial family (`PM_LONGSHOT_FADE`,
`PM_FAVOURITE`). Its trials are counted **separately** from the N=8 price-series registry: merging
them would corrupt the deflated-Sharpe trial variance, which assumes trials drawn from one
comparable distribution.

---

## 2. Settlement (implemented, tested)

```text
side ∈ {YES, NO};  outcome ∈ {YES, NO}
payout   = 1.0 * qty        if side == outcome else 0.0
cost     = entry_price * qty                 # premium actually paid, in [0,1]
fee      = ceil(0.07 * p * (1-p) * qty)      # Kalshi, rounded UP to the cent per order
         = 0.0                               # Polymarket taker (spread is the real cost)
pnl      = payout - fee - cost
return   = pnl / cost                        # ON PREMIUM AT RISK, not on notional
```

Return is on the premium, so a YES bought at 0.30 that settles YES returns **+233.3%** and one that
settles NO returns **−100.0%**. The asymmetry is the asset class and it is preserved, never averaged
away. Fee rounding is not cosmetic: at 50¢ the raw fee is 0.0175 per contract, but the order pays
0.02, which is why a 50¢ winner returns 96.0% and not 96.5%.

---

## 3. Calibration (implemented, tested) — the actual measurement target

Win rate is the wrong statistic for this class. What matters is whether a stated probability is
**true**:

```text
Brier    = mean( (p_yes - outcome)² )             0.25 = a constant 0.5 forecast
LogLoss  = mean( -(y·ln p + (1-y)·ln(1-p)) )
Reliability[b] = (mean predicted, realised frequency) in fixed-width probability bins
ECE      = Σ (n_b / n) · |observed_b - predicted_b|
Skill    = 1 - Brier / Brier(base rate)
```

The base-rate Brier is reported alongside every score: a model that always says "90%" looks
well-calibrated on a sample that resolves YES 90% of the time while containing **no information**.
Skill against the base rate is the only column that distinguishes forecasting from base-rate
memorisation.

**Hard constraint on the data:** the implied probability must be the **market price before
settlement**. `outcomePrices` from the API is the settlement result (0/1) and would score a perfect
Brier by construction. This is the single most likely way a prediction-market calibration study gets
faked, deliberately or not.

---

## 4. The rule worth measuring (pre-registered)

```text
Hypothesis:  For contracts priced 0.85 <= P <= 0.95 in category C, the empirical settlement
             frequency exceeds P by >= 3 percentage points after fees, on >= 200 resolved contracts.

Entry:   MAKER order only (Polymarket maker fee 0 + rebate; Kalshi maker multiplier 0)
Size:    fixed fraction of bankroll; no averaging into a loser (no stop exists)
Exit:    none — contracts settle. Only exits: sell to a maker pre-resolution, or hold to $0/$1.
Gate:    calibration slope > 1 AND Brier better than the market-implied probability.
```

**Makers only.** Every structurally profitable prediction-market operation here is market-making,
not forecasting. Taker fees run 3.5–6.3% of stake (peak at a coin flip, exactly where a forecaster
believes their edge is) versus ~12× less for a liquid equity round trip.

---

## 5. What was measured — and why it is still not a number

The resolver and the statistics are **built and verified**: `python3 tools/pm_binary.py selftest`
runs **15/15** hand-computed cases covering settlement, fee rounding, Brier, log loss, reliability,
ECE, skill, and the empty-sample path.

The calibration itself is **NOT MEASURED**, and the reason is recorded rather than papered over:

```text
$ python3 tools/pm_binary.py fetch --limit 100 --max-markets 12
  markets tried: 12 | with price history: 0
  RESULT: NOT MEASURED — Polymarket's price-history endpoint returned no points,
  so there is no implied probability at decision time to score.
```

`gamma-api.polymarket.com/markets?closed=true` returns settled markets with token IDs, volumes and
final prices — but `clob.polymarket.com/prices-history` returns an **empty history** for every
resolved market tried, including markets with $1.5B volume (the 2024 election), under
`interval=max`, `interval=all` and explicit `startTs`/`endTs`. Without a price series there is no
pre-settlement probability, and a calibration curve cannot be computed from final outcomes alone.

The repo's own prediction pick files are also empty (`alpha_engine/data/prediction_market_picks.json`
has 0 rows; `polymarket_signals.json`, `kalshi_signals.json` and `data/pm_forward_test.json` do not
exist in the tree). Rows labelled `prediction_market_consensus` in the live ledger are **crypto
underlyings** (e.g. `SOLUSDT`) filed under the CRYPTO class — they are not binary contracts and must
not be counted as this asset class. Doing so would manufacture a sample of zero.

**Re-admission condition:** the class becomes measurable the moment a `(price_at_entry, outcome)`
pair is captured per contract — either by fixing the price-history call (a `startTs` window around
each market's close, or the data-api trade endpoint) or by recording the entry price at signal time
in `state/pm_binary/`. `tools/pm_binary.py settle` already consumes exactly that shape and writes
`state/pm_binary/settled.jsonl`, so no further code is needed once data exists.

---

## 6. Elimination (for now)

Eliminated as a **trading venue**, retained as a **data source / probability oracle**: taker fees at
3.5–6.3% of stake require an unusually large forecasting edge to survive, and the maker
infrastructure does not exist here. Recorded in `ELIMINATION_LOG.md` §3 with its re-admission
condition.

**What changed in revision 2:** the class is no longer "not representable". It has a tested
settlement resolver, tested calibration statistics, a registered trial family and a fetch path that
reports its own coverage honestly. It remains unmeasured for a data reason that is now named and
checkable, not a hand-wave.
