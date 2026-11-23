# Why 0/69 picks clear G3 (DSR ≥ 0.95 at N=658), and the criteria a future strategy must meet

**Date:** 2026-11-23 · **Worktree:** vanilla-handsaw · **Author:** Kilo
**Paper only. Zero capital. Not investment advice.**

## 1. What G3 actually requires

The tribunal's deflated Sharpe (Bailey/López de Prado) is

```
sr0 = K(N) / sqrt(n)                       # K(658) = 3.134
DSR = Φ( (sr − sr0) · sqrt(n−1) / sqrt(1 − skew·sr + (kurt−1)/4·sr²) )
```

so the hurdle **falls as 1/√n**: more trades, lower bar. (This is the per-strategy DSR. It is
*not* the same as the SR* in `reports/sr_star_table.json`, which uses cross-cell dispersion
σ=0.649 to estimate the expected max **across** strategies — do not mix the two.)

## 2. The measured frontier at N=658

| n | required per-trade Sharpe for DSR ≥ 0.95 |
|---:|---:|
| 30 | 0.939 |
| 50 | 0.706 |
| 80 | 0.549 |
| **100** | **0.488** |
| 150 | 0.396 |
| 219 | 0.326 |
| 400 | 0.240 |
| 1000 | 0.151 |

Equivalent view — minimum n for a given Sharpe: SR 0.5 → n=96 · SR 0.724 → n=48 · SR 0.8 → n=40 · SR 1.0 → n=27.

## 3. Why every one of the 69 fails

It is a **sample-size problem on modest Sharpe**, not an impossible bar:
- **AUDJPY** is the best pick: SR 0.724, n=34 → DSR **0.830**. It needs just **n=48** (14 more
  closed trades) to clear 0.95. It is the closest thing the programme has.
- **CVX** (2nd best SR 0.449, n=35) needs n=118.
- The high-n picks fail on Sharpe: NEAR n=219 SR 0.13, ETH n=155 SR 0.13, WIF n=146 SR 0.14 —
  they need SR ≥ 0.33, i.e. ~2.5× more edge.
- Everything else has n<50 **and** SR<0.2, which is far below both axes.

Root cause: picks are short samples (median n≈35) of weak per-trade edge (median SR near 0).
The deflation penalty is not what kills them — **insufficient n and low SR** are.

## 4. Concrete criteria a future strategy must meet to clear G3 ≥ 0.95 at N=658

**Hard floor (all required):**
1. **n ≥ 100 closed forward trades** — at n=100 the SR bar is 0.488; below n=100 the required SR
   climbs steeply (0.94 at n=30) and becomes impractical.
2. **per-trade Sharpe ≥ 0.50 at n=100**, or **≥ 0.40 at n=150**, or **≥ 0.33 at n=219**.
3. **Target SR ≥ 0.60 with n ≥ 100** for margin (gives DSR ≈ 0.97+, robust to skew/kurtosis).
4. Report the **trial count N** and use the **effective** N (correlation-adjusted, ~25 per the
   fleet's freebuff note), not cells×symbols, when claiming the number.
5. DSR is necessary, not sufficient — the pick must **also** clear G1 (gross > 2× class cost),
   G2 (hold ≥ 1 day), G4 (net annualised > 4.32% T-bill) and G5 (pre-registered before outcome).

**What this rules out, plainly:** a strategy with per-trade SR ≈ 0.2 that "looks fine" on a
positive mean will need **n ≈ 600–1,000** to clear G3. Betting on more of the same signal is the
wrong fix; the remedy is **more independent observations** (per-trade sampling over many symbols)
or **a genuinely larger effect**, not another 100 rows of the same weak edge.

## 5. Recommendation

Do not chase N down to make the bar look passable; make **n up and SR up**. The single most
valuable action is to let **AUDJPY-class** candidates accrue the 14+ trades they need (it is one
short step from DSR 0.95), and to pre-register one high-Sharpe, high-n hypothesis rather than
adding trials. Everything else stays paper-only.

*Files:* `reports/g3_bar_analysis_corrected.json`, `reports/eval_rerun_per_class_costs.json`.
