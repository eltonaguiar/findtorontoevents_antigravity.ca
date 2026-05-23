# On-Chain Crypto Signal Research — STRAND B — H-014 — 2026-05-18

_Generated 2026-05-18T04:06:04+00:00 by `tools/onchain_crypto_research.py`._

**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** This module has no caller in `quality_gates.py`, `dashboard_generator.py`, or any pick-generation / scoring path. It reads REAL on-chain data and writes this report — nothing else. Per the repo Wire-Up Rule it is explicitly an opt-in research sidecar.

## Mandate

`reports/EDGE_HUNT_CONCLUSION_2026-05-18.md` recorded 7 straight harness kills — every signal the system already draws from (price/volume technicals, COT, funding rate, futures term structure, earnings surprise) is exhausted. STRAND B of the strategic fork (`reports/STRATEGIC_FORK_SYNTHESIS_2026-05-18.md`, Option 1) is a **NEW input class** — information the pick emitters have never seen. H-014 tests **on-chain blockchain network activity**, pre-registered in `reports/hypothesis_registry.json` (separate commit, before any backtest logic, per M-107).

This is **not** a banned re-build: it is not funding-rate, not fear&greed/RSI, not yield-curve, not COT. It is also **not a price/volume proxy** — the signals are counts of on-chain addresses and transactions and on-chain stablecoin token supply. Price is used ONLY to measure the forward return that resolves a pick WON/LOST.

## The three on-chain signals (all REAL, all free, no synthetic data)

| id | signal | on-chain source |
|----|--------|-----------------|
| S1 | active-address momentum | blockchain.com /charts/n-unique-addresses (REAL on-chain count of distinct addresses per day) |
| S2 | transaction-count momentum | blockchain.com /charts/n-transactions (REAL on-chain confirmed transactions per day) |
| S3 | stablecoin-supply change | CoinGecko market_chart USDT+USDC market cap (REAL aggregate on-chain stablecoin token supply) |

## Method — identical leakage controls for all three (auditable)

1. **Real data only.** On-chain series fetched live from blockchain.com charts API and CoinGecko market_chart. No simulated, self-generated, or random-walk data anywhere. The fetched cache is committed alongside this module so the verdict is independently re-runnable.
2. **Strictly-past z-score.** Rolling 30-day z-score of the daily fractional change in the on-chain metric — uses only observations BEFORE the signal date.
3. **No look-ahead entry.** The pick enters on the first price bar STRICTLY AFTER the on-chain signal date; forward return over a fixed 5-day hold.
4. **Continuous-position book — FULL series, not a subset.** One resolved-pick record per on-chain day per resolution asset (direction = sign(z)). There is NO `|z|` threshold — the harness sees every signal-generated record, not a self-selected subset the signal happened to like. This is the H3 honesty requirement.
4b. **Multi-asset resolution (density construction).** The BTC on-chain network signal is a *market-wide* input. A single-BTC book yields ~1 record/day — far below the harness's >= 80-records-with->=15-winners-and->=15-losers per-14-day-window bar (this is exactly why Fork-2 H-006/H-008 came back UNTESTED). So the signal is resolved against the forward returns of a universe of liquid crypto majors (BTC/ETH/SOL/BNB/XRP/ADA/LTC/DOGE), the SAME density construction the H-008 BOND redesign used (a multi-instrument ladder). **Honest caveat:** the crypto majors are highly correlated (crypto beta ~ 1), so the *effective* independent sample is well below the nominal record count — the harness still renders a verdict on sign-stability, but the per-window winners/losers are not 8 independent observations.
5. **Purged + embargoed walk-forward** (5-day embargo, 14-day blocks).
6. **Verdict gate — the UNMODIFIED harness.** Records fed through `tools/edge_stability_harness.is_admissible()` / `.evaluate()`, imported verbatim — not wrapped, not reimplemented, not loosened. ADMISSIBLE iff `|eff| >= 0.3`, same sign, in >= 3 of the scored 14-day windows.
7. **Post-cost gate.** Realistic crypto round-trip cost = 2 x (taker 10bps + slippage 5bps) = 30bps. The net edge must keep >= 60% of gross. **BOTH** the harness AND the cost gate must pass — a harness pass alone is not enough (funding-arb passed the harness and died on cost).

**A gaudy in-sample win rate is NOT a pass.** Only the harness verdict + the cost gate count. After 7 prior kills the base rate is poor; this is reported honestly either way.

## Exact harness construction (auditable per H3)

The harness runs on the FULL continuous-position record list — one record for *every* on-chain day x resolution-asset with a computable z and a forward return, NOT a subset filtered by signal strength. Each record carries `status` (WON/LOST from the direction-signed forward return) and `signal_z` (the `|z|` conviction magnitude — the score field the harness evaluates). `harness._load` is temporarily pointed at this list; `harness.evaluate()` / `is_admissible()` then run their own unchanged `_windows` / `_window_eff` logic (the harness module is imported verbatim, EFF_MIN/MIN_WINDOW_N/MIN_STABLE_WINDOWS untouched). If a real edge exists, winners carry higher `|z|` than losers with a stable sign across >= 3 walk-forward windows. If not, the sign splits — the exact failure mode that killed the prior 7 candidates.

## S1 — active-address momentum — [REJECTED]

- **Hypothesis:** H-014 (CRYPTO)
- **On-chain source:** blockchain.com /charts/n-unique-addresses (REAL on-chain count of distinct addresses per day)
- **Resolution:** multi-asset (8 crypto majors: ADAUSDT, BNBUSDT, BTCUSDT, DOGEUSDT, ETHUSDT, LTCUSDT, SOLUSDT, XRPUSDT)
- **On-chain history:** 2912 days (2018-05-20 .. 2026-05-16)
- **Continuous-position records:** 7944

### Purged + embargoed walk-forward
- OOS sample: n=7944, pooled WR=49.5%
- embargo: 5 days
- gross edge (mean signed return/trade): -0.001088

| block start | n | WR |
|---|---|---|
| 2023-08-23 | 128 | 47.7% |
| 2023-09-06 | 112 | 59.8% |
| 2023-09-20 | 112 | 44.6% |
| 2023-10-04 | 112 | 61.6% |
| 2023-10-18 | 112 | 56.2% |
| 2023-11-01 | 112 | 38.4% |
| 2023-11-15 | 112 | 38.4% |
| 2023-11-29 | 112 | 40.2% |
| ... | ... | (72 blocks total) |

### Harness verdict (THE gate — unmodified)
- per-window eff (new->old): `+0.05 +0.12 -0.56 +0.07 -0.14 -0.23 +0.42 +0.49 +0.27 -0.20 +1.26 +0.16 -0.48 +0.47 -0.19 +0.56 +0.54 +0.09 -0.71 +0.16 -0.35 -0.08 +0.24 -0.11 ...`
- windows strong: 24/71 (+13/-11)
- classification: **TESTED — harness rendered an eff-stability verdict**
- **is_admissible(): False** — REJECTED — strong in 24 windows but signs split (13+/11-); needs 3 same-sign

### Post-cost gate (H4)
- round-trip cost: 30.0 bps (0.003)
- gross edge: -0.001088  ->  net edge: -0.004088
- cost survival: 0.0% of gross (floor 60%)
- **cost gate passes: False**

### Verdict: REJECTED

## S2 — transaction-count momentum — [REJECTED]

- **Hypothesis:** H-014 (CRYPTO)
- **On-chain source:** blockchain.com /charts/n-transactions (REAL on-chain confirmed transactions per day)
- **Resolution:** multi-asset (8 crypto majors: ADAUSDT, BNBUSDT, BTCUSDT, DOGEUSDT, ETHUSDT, LTCUSDT, SOLUSDT, XRPUSDT)
- **On-chain history:** 2916 days (2018-05-20 .. 2026-05-16)
- **Continuous-position records:** 7952

### Purged + embargoed walk-forward
- OOS sample: n=7952, pooled WR=48.8%
- embargo: 5 days
- gross edge (mean signed return/trade): -0.002411

| block start | n | WR |
|---|---|---|
| 2023-08-23 | 128 | 46.1% |
| 2023-09-06 | 112 | 40.2% |
| 2023-09-20 | 112 | 57.1% |
| 2023-10-04 | 112 | 61.6% |
| 2023-10-18 | 112 | 56.2% |
| 2023-11-01 | 112 | 45.5% |
| 2023-11-15 | 112 | 34.8% |
| 2023-11-29 | 112 | 47.3% |
| ... | ... | (72 blocks total) |

### Harness verdict (THE gate — unmodified)
- per-window eff (new->old): `+0.02 -0.52 +0.40 -0.10 -0.10 +0.80 +0.15 +0.01 -0.74 -0.04 -0.24 +0.64 -0.02 -0.26 -0.18 +0.11 +0.61 -0.10 -0.10 -0.14 +0.74 +0.62 -0.22 -0.15 ...`
- windows strong: 26/71 (+14/-12)
- classification: **TESTED — harness rendered an eff-stability verdict**
- **is_admissible(): False** — REJECTED — strong in 26 windows but signs split (14+/12-); needs 3 same-sign

### Post-cost gate (H4)
- round-trip cost: 30.0 bps (0.003)
- gross edge: -0.002411  ->  net edge: -0.005411
- cost survival: 0.0% of gross (floor 60%)
- **cost gate passes: False**

### Verdict: REJECTED

## S3 — stablecoin-supply change — [REJECTED]

- **Hypothesis:** H-014 (CRYPTO)
- **On-chain source:** CoinGecko market_chart USDT+USDC market cap (REAL aggregate on-chain stablecoin token supply)
- **Resolution:** multi-asset (8 crypto majors: ADAUSDT, BNBUSDT, BTCUSDT, DOGEUSDT, ETHUSDT, LTCUSDT, SOLUSDT, XRPUSDT)
- **On-chain history:** 365 days (2025-05-19 .. 2026-05-18)
- **Continuous-position records:** 2632

### Purged + embargoed walk-forward
- OOS sample: n=2632, pooled WR=50.9%
- embargo: 5 days
- gross edge (mean signed return/trade): 0.001869

| block start | n | WR |
|---|---|---|
| 2025-06-19 | 112 | 43.8% |
| 2025-07-03 | 112 | 56.2% |
| 2025-07-17 | 112 | 50.9% |
| 2025-07-31 | 112 | 40.2% |
| 2025-08-14 | 112 | 49.1% |
| 2025-08-28 | 112 | 43.8% |
| 2025-09-11 | 112 | 58.0% |
| 2025-09-25 | 112 | 45.5% |
| ... | ... | (24 blocks total) |

### Harness verdict (THE gate — unmodified)
- per-window eff (new->old): `-0.01 -0.30 +0.65 +0.32 +0.74 -0.35 -0.20 +0.17 -0.58 +0.66 +0.55 -0.08 -0.06 -0.60 +0.10 -0.52 -0.86 -0.70 -0.12 -0.14 +0.03 +0.37 -0.04`
- windows strong: 13/23 (+6/-7)
- classification: **TESTED — harness rendered an eff-stability verdict**
- **is_admissible(): False** — REJECTED — strong in 13 windows but signs split (6+/7-); needs 3 same-sign

### Post-cost gate (H4)
- round-trip cost: 30.0 bps (0.003)
- gross edge: 0.001869  ->  net edge: -0.001131
- cost survival: -60.5% of gross (floor 60%)
- **cost gate passes: False**

### Verdict: REJECTED

## Honest conclusion

**0 of 3 on-chain signals cleared the gate.** None may rank, gate, or size a pick. Honest breakdown:

- **Tested and REJECTED (3):** S1 (active-address momentum), S2 (transaction-count momentum), S3 (stablecoin-supply change). The unmodified harness rendered a real eff-stability verdict and the signal failed it — a measured result, not a data gap.
- **UNTESTED — data-insufficient (0):** none. The harness needs >= 80 records with >= 15 winners and >= 15 losers per 14-day window across >= 3 windows. Where free on-chain history (e.g. CoinGecko's 365-day market_chart cap for stablecoin supply) cannot supply that, the honest verdict is **UNTESTED — explicitly NOT a pass**. The harness thresholds were NOT lowered and the windows were NOT shrunk to manufacture a verdict.

On-chain network activity is a genuinely new input class — but a new input class is not an edge until the harness says so, and today it does not. This is consistent with the EDGE_VERDICT base rate. No signal is wired, none is sized; paper-only posture stands.
