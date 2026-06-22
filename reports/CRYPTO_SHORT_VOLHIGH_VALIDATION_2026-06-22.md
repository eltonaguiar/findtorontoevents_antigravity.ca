# crypto_short_volhigh — extended validation (2026-06-22, swarm-owed falsifications)

Follow-up to `reports/CRYPTO_SHORT_VOLHIGH_ROBUST_CANDIDATE_2026-06-22.md`. The methodology swarm
flagged two remaining checks (single IS/OOS insufficient → walk-forward; prove vol-conditioning adds
value beyond crash-catching → synthetic control). Both now run; both PASS.

## Re-mine on grown cohort (1251 → 1274)
`crypto_short_volhigh` HELD: n 54→56, netPF 1.86→1.83, bootstrap CI-LB 1.41→**1.385**, still the only
cell passing the full robust gate. No new robust candidate appeared. Slight softening = normal noise.

## 1) Walk-forward — 3 sequential folds (replaces single IS/OOS)
| fold | window | n | WR | netPF |
|------|--------|---|----|----|
| 1 | 2026-02-24 .. 05-30 | 18 | 72.2% | **3.51** |
| 2 | 2026-06-01 .. 06-05 | 18 | 55.6% | **1.33** |
| 3 | 2026-06-06 .. 06-21 | 20 | 60.0% | **1.72** |

**All 3 folds net-positive.** The edge persists across sequential time windows, not just one split.
(Caveat: folds 2–3 are short recent windows — the cohort is recency-weighted, a known data-snapshot
pattern; broader-time confirmation still accrues with forward-n.)

## 2) Synthetic-control — does the HIGH-vol tercile add value?
| cell | n | WR | netPF |
|------|---|----|----|
| CRYPTO SHORT **VOLHIGH** | 56 | 62.5% | **1.83** |
| CRYPTO SHORT VOLLOW | 31 | 48.4% | **0.52** (loser) |
| CRYPTO SHORT all-vol | 87 | 57.5% | 1.27 |

**Decisive:** high-vol shorts win (1.83), low-vol shorts lose (0.52), and VOLHIGH beats shorting
indiscriminately (1.27). The volatility conditioning IS the edge — not generic "short crypto."

## Cumulative falsification scorecard (all PASS)
bootstrap CI-LB 1.385 · regime (wins both, incl up-month) · concentration 47% / 16-of-19 symbols ·
session (US/ASIA strong) · time-split IS/OOS both 63% · **walk-forward 3/3 folds positive** ·
**synthetic-control (vol adds value)** · swarm-endorsed (plausible vol-mean-reversion).

## Honest status (unchanged gates)
Best honest lead of the hunt; the most thoroughly falsified candidate we have. STILL not sizable:
n=56 < 80 forward gate; downside-skewed crash-fade; recency-weighted; a SHORT (needs perps/borrow).
Next: forward-accrue to n>=80 holding bootstrap CI-LB>1.0, then a tiny paper-pilot as a downside-hedge
sleeve. The robust-edge-miner cron keeps re-confirming it; a fresh n>=80 falsification re-run before any pilot.
