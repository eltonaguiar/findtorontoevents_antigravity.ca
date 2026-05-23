# C-3 / H-017 — CRYPTO Funding-Settlement Liquidation-Cascade — 2026-05-18

_Generated 2026-05-18T08:52:01+00:00 by `tools/c3_funding_settlement_research.py`._

**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** No caller in `quality_gates.py`, `dashboard_generator.py`, or any pick-generation / scoring path. Reads free Binance market data, writes this report.

## Hypothesis (H-017, pre-registered per M-107)

Perpetual funding settles every 8h at fixed UTC clock times (00:00 / 08:00 / 16:00). Over-leveraged positions get squeezed; thin books at the settlement minute overshoot, then mean-revert. The signal is FORCED FLOW at a known clock time -- NOT a funding-rate directional bet. **FADE the displacement.**

## Method (signal defined BEFORE the run)

1. Universe: 10 liquid Binance USDT-M perps (BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, ADAUSDT, AVAXUSDT, LINKUSDT, DOGEUSDT, LTCUSDT).
2. Span: 7 months of free 1-min klines + `/fapi/v1/fundingRate` history (both paginated via startTime/endTime; API-failover mirror chain fapi/fapi1/fapi2 -> Bybit).
3. At each 8h settlement T: displacement = price(T) / prior-1h VWAP - 1; realized vol = stdev of prior-60-min 1-min log returns.
4. A pick FIRES when |displacement| > 1.5 x realized vol AND |funding| is in its per-symbol rolling top quartile (30-obs window, strictly-past).
5. Direction = FADE (entry opposite the displacement). Entry = close of the T+1min bar.
6. Exit = whichever first: VWAP reversion / 30-min time stop / +-20bps hard stop. Forward return signed by the fade direction.
7. Each settlement that fires -> one resolved-pick record (status WON/LOST from the signed gross return). The FULL signal-generated series is fed to the harness -- no cherry-picking.
8. `tools/edge_stability_harness.py` imported UNMODIFIED (EFF_MIN=0.3, MIN_WINDOW_N=80, MIN_STABLE_WINDOWS=3); `is_admissible()` called on the record series.
9. Post-cost gate: 30bps crypto round-trip; net edge must retain >=60% of gross.

## VERDICT: **REJECTED**

eff SIGN SPLITS (1+/2-) across strong windows -- sign-unstable, fails the same-sign requirement.

## Per-symbol data coverage

| symbol | picks fired | funding events | 1m bars | funding span |
|---|---|---|---|---|
| BTCUSDT | 111 | 630 | 120270 | 2025-10-20 -> 2026-05-18 |
| ETHUSDT | 114 | 630 | 120272 | 2025-10-20 -> 2026-05-18 |
| SOLUSDT | 133 | 630 | 120274 | 2025-10-20 -> 2026-05-18 |
| BNBUSDT | 52 | 630 | 120275 | 2025-10-20 -> 2026-05-18 |
| XRPUSDT | 114 | 630 | 120277 | 2025-10-20 -> 2026-05-18 |
| ADAUSDT | 164 | 630 | 120279 | 2025-10-20 -> 2026-05-18 |
| AVAXUSDT | 155 | 630 | 120281 | 2025-10-20 -> 2026-05-18 |
| LINKUSDT | 136 | 630 | 120283 | 2025-10-20 -> 2026-05-18 |
| DOGEUSDT | 114 | 630 | 120285 | 2025-10-20 -> 2026-05-18 |
| LTCUSDT | 112 | 630 | 120286 | 2025-10-20 -> 2026-05-18 |

## Harness verdict (THE gate -- 14-day walk-forward)

- **n picks (full signal series):** 1205
- **windows scored:** 8
- **windows strong (|eff|>=0.3):** 3  (+1 / -2)
- **per-window eff (new->old):** `-0.25 -0.03 +0.12 +0.08 -0.61 -0.13 -0.47 +0.49`
- **same-sign check:** FAIL -- 1+ vs 2- (signs split)
- **harness.is_admissible():** False
- **harness reason:** REJECTED — strong in 3 windows but signs split (1+/2-); needs 3 same-sign

## Win rate & edge

- **pooled gross WR:** 57.8%
- **pooled net WR (after 30bps):** 7.0%
- **gross edge:** 1.312 bps/trade
- **net edge:** -28.688 bps/trade
- **cost-survival:** -2186.25% of gross edge retained (gate: >=60%) -- FAIL

## Honest conclusion & next step

**H-017 was properly TESTED and REJECTED.** The harness scored 8 windows -- enough for a real verdict -- and the eff sign SPLITS (1+/2-) across the strong windows. The fade signal separates winners from losers in some 14-day windows but flips sign in others -- the identical regime-noise failure mode that killed `method_a_score` and the prior edge-hunt candidates. A sound mechanical prior (forced flow at a clock time) is not an edge until the harness says so, and it does not. **NOT admissible, NOT wired, NOT sized.**

_Per-window eff: `[-0.251, -0.033, 0.117, 0.078, -0.613, -0.134, -0.468, 0.486]`_

Reproducer: `python tools/c3_funding_settlement_research.py` (uses the committed cache; `--refresh-cache` to re-fetch).
