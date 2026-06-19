# Robust edge gauntlet — 2026-06-13 (loop iteration 5)

**Conclusive result: 0 of all non-crypto strategies survive a 5-filter robustness gauntlet. There is no robust net-positive edge in the current book — the bottleneck is structural (pick amplitude + resolver batch-artifacts), not a hidden winner.**

## The gauntlet (n≥50, all must hold)
1. **Net PF ≥ 1.2** after per-class round-trip cost (FOREX majors 3bp/JPY 6bp; EQUITY/ETF/INDEX 4bp; BOND 3bp).
2. **≥ 3 distinct `closed_at` dates** — rejects single-batch / single-snapshot resolution artifacts.
3. **IS-half net PF ≥ 1.1** (time-split).
4. **OOS-half net PF ≥ 1.1** (time-split).
5. **Survives dropping the single largest winner** (net PF ≥ 1.1) — rejects one-trade-carried edges.

Method: deduped per (source, strategy, symbol, day); 5bp win threshold.

## Result — only 3 are even net-positive, each killed by a different filter

| Class | Strategy | n | closed-dates | net PF | Killed by |
|---|---|---|---|---|---|
| EQUITY | `stocks_ema_golden_cross` | 56 | 4 | 1.98 | **OOS 0.79** (overfit) |
| EQUITY | `smart_money_accumulation` | 76 | 10 | 1.37 | **IS 0.27** (unstable; all edge in 2nd half) |
| ETF | `leveraged_etf_decay` | 69 | **1** | 1.24 | **BATCH (1 date)** + drop-top 1.05 (one-trade) |

**Survive all 5 filters: 0.** Every candidate that looks net-positive fails for a textbook reason (overfit, instability, or single-batch/single-trade artifact).

## What this means (the pivot)
We have now exhaustively hunted the existing non-crypto book with cost + dedup + time-split + anti-batch + drop-largest discipline and found **no robust net-positive edge**. Continuing to mine the current book for a hidden winner is not the path. The two structural root causes are:

1. **Pick amplitude is too low.** Winners average ~0.2–0.3% (FOREX) — below the cost floor. Edges with gross PF > 2 die net. *Fix at the emission source: target larger moves, or add a cost-aware emission gate rejecting picks whose expected move < k×(round-trip cost).*
2. **Resolver batch-artifacts manufacture false edges.** The few high-PF cohorts (e.g. leveraged_etf_decay) are single-`closed_at`-date snapshots, not live first-touch trading. *Fix: require ≥3 distinct closed dates + TP/SL diversity before trusting any cohort; re-resolve intrabar (`verified_strategies/intrabar_replay_noncrypto.py`).*

## Recommendation
- **Stop sizing-hunts on the current book.** No class is money-ready; do not pilot any current candidate with real capital.
- **Invest in the two structural fixes** (amplitude-aware emission gate; intrabar re-resolution + anti-batch cohort hygiene). These are the only path to a net-positive, robust edge.
- Re-run this gauntlet in ~4–6 weeks once forward, non-batch, higher-amplitude picks have accrued.

Reproduce: refined hunt in this session; cost model = `tools/forex_long_pilot_tracker.py`.
