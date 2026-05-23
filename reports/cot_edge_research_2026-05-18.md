# COT Edge Research — real CFTC commercial positioning

Signal: 52-week commercial-net z-score, |z| >= 1.5, trade WITH commercials. Forward return measured 4 weeks after the post-publish entry bar. No look-ahead.

## Pooled — n=717 signals
- hit-rate (forward return agrees with signal): **53.8%**
- mean signed forward return: **+0.27%** per signal
- a real edge needs hit-rate > 55% AND mean signed > 0 AND year-stable.

## Per contract

| contract | n | hit-rate | mean signed |
|---|---|---|---|
| GC | 175 | 51.4% | +0.27% |
| SI | 172 | 62.8% | +1.27% |
| HG | 172 | 42.4% | -1.52% |
| NQ | 89 | 51.7% | +0.63% |
| YM | 109 | 63.3% | +1.25% |

## By year — stability check

| year | n | hit-rate | mean signed |
|---|---|---|---|
| 2014 | 32 | 78.1% | +1.17% |
| 2015 | 38 | 78.9% | +3.17% |
| 2016 | 61 | 47.5% | -1.06% |
| 2017 | 29 | 58.6% | +1.09% |
| 2018 | 63 | 50.8% | +0.35% |
| 2019 | 62 | 54.8% | -0.07% |
| 2020 | 63 | 47.6% | -0.57% |
| 2021 | 48 | 64.6% | +1.55% |
| 2022 | 83 | 50.6% | -0.77% |
| 2023 | 61 | 59.0% | +0.70% |
| 2024 | 83 | 30.1% | -1.70% |
| 2025 | 73 | 57.5% | +1.93% |
| 2026 | 21 | 61.9% | +1.69% |

**Year stability: 8 positive / 5 non-positive.** NOT year-stable / sub-threshold — COT z-score is not a usable edge at these parameters.
---

## VERDICT — COT-z is NOT a money-ready edge

Per-contract by-year drill on the two "promising" contracts (SI 62.8%, YM 63.3%
pooled):

- **SI (silver):** strong 2014-15 (100% / 83%), then decays — 2022 47%, 2023
  43%, 2024 47%. The pooled 62.8% is carried by 2014-15 + a thin 2025 (n=10).
- **YM (Dow):** flips hard — 2020 82%, 2023 74%, 2025 74% **but** 2021 25%,
  2024 27%. No stability.

Both 2024 collapsed (SI 47%, YM 27%). The COT commercial-positioning z-score is
**regime-dependent, not a durable edge** — it is not a parameter-tuning problem,
it is fundamental year-to-year instability.

This directly answers the swarm's "the one thing that means we're wasting our
time": real CFTC COT data, properly lagged, walk-forward tested over 13 years —
**fails.** The historical `cot_positioning` "edge" was never real: the CT=F
gaudy numbers were COT-row-duplication leakage, and the clean signal tested
here is ~coin-flip (53.8% pooled).

**COT is removed from the edge-candidate queue.** Tested with rigor, killed with
data — not hand-waving. The `cot_edge_research.py` harness remains: re-runnable
if a new COT parameterisation (positioning *changes* vs levels, different
horizon) is ever proposed, but the burden of proof is now high.

Remaining candidate queue: regime-conditioned scores, qlib factors (#1178).
