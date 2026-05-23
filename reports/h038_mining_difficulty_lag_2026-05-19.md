# H-038 CRYPTO mining-difficulty-lag — 2026-05-19

_Generated 2026-05-19T20:22:37+00:00 by `tools/h038_mining_difficulty_lag.py`._

**Status: OPT-IN RESEARCH SIDECAR.** No caller in `quality_gates.py`, `dashboard_generator.py`, or any pick / scoring path at test time. Fetches free data, runs the pre-registered signal through `edge_stability_harness` (imported unmodified), writes this report.

## Pre-registered hypothesis (registry `mining_difficulty_lag_2026_05_19` / H-038)

BTC hash-rate vs the ~2-week difficulty-retarget lag. Difficulty re-targets every 2016 blocks (~14 days); between retargets the difficulty number is frozen while hash-rate drifts. The gap `hashrate_gap = hashrate_today / hashrate_at_last_retarget - 1` is a miner-economics signal: a large positive gap precedes an upward difficulty adjustment (a miner cost shock) -> SHORT BTC; a large negative gap precedes a downward adjustment -> LONG. The gap is z-scored against a strictly-past 180-day baseline; |gap_z| is the harness conviction field.

**No-look-ahead:** the gap uses the retarget strictly before day D; the 180-day z-score baseline uses gap values strictly before D; the trade enters at close(D) and resolves at close(D+5).

**Distinct from killed H-014:** H-014 used unique-address / transaction COUNTS (Metcalfe adoption proxy). H-038 uses NO address or transaction data — it is a pure miner-supply / cost-shock timing signal from the hash-rate-vs-difficulty retarget lag.

## Data (all free, no API key)

- BTC daily hash-rate: mempool.space `/api/v1/mining/hashrate/3y`.
- Difficulty-retarget history: mempool.space `/api/v1/mining/difficulty-adjustments/3y`.
- Daily close for the resolution-asset book: api-failover chain (Binance api/api1/api2/api3 -> CryptoCompare).
- Resolution symbols (BTC signal resolved market-wide): BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT, ADAUSDT, DOGEUSDT, LTCUSDT.
- Continuous-position multi-asset resolved records: **7192**.

## Harness verdict (THE gate — harness imported UNMODIFIED)

- per-window eff (new->old): `-0.38 +0.05 -0.22 +0.17 -0.53 -0.42 +0.91 -0.69 -0.29 +0.37 +0.27 +0.53 -0.72 -0.23 +0.07 +0.26 +0.97 -0.01 -0.52 -0.07 -0.45 -0.07 +0.46 +0.60 +0.17 -0.08 -0.32 +0.48 +0.17 +0.24 -0.06 -0.25 -0.35 +0.39 -0.55 +0.28 -0.27 +0.82 -0.34 -0.50 +0.12 +0.59 -0.61 -0.10 -0.13 +0.61 -0.30 +0.20 -0.13 +0.65 +0.39 -0.38 +0.20 +0.43 -0.16 +0.79 -0.10 -0.69 -0.49 -0.08 +0.31 +0.43 -0.11 +0.43`
- windows scored: 64  (strong: 35, +18/-17)
- sign: `mixed`
- harness `is_admissible()`: False
- harness reason: REJECTED — strong in 35 windows but signs split (18+/17-); needs 3 same-sign

## Edge & cost survival

- pooled WR: 47.19%
- gross mean per-trade return: -0.006633
- net mean per-trade return (after 30bps): -0.009633
- cost-survival (|gross| > 30bps): 96.2%  (gate >= 60%: PASS)

## VERDICT: **REJECTED**

Clean kill. The mining-difficulty-lag signal does not separate winners from losers with a stable sign across enough 14-day windows (or fails the 30bps cost gate). Do NOT wire or size — wiring a non-admissible emitter pollutes /audit. Archive as a tested failure.
