# AA-4 60/40 trend+pattern blend backtest — multi_asset_cot + multi_asset_copytrader

**Date:** 2026-05-13
**Source:** `alpha_engine/data/closed_picks.json` terminal rows
**Hypothesis:** 60% multi_asset_cot (trend, COMMODITY) + 40% multi_asset_copytrader (cross-class) improves Sharpe via diversification.

## TL;DR — Hypothesis FALSIFIED

Blend dilutes the COT winner without lifting copytrader. **multi_asset_cot solo dominates every weighting tested.**

| Strategy | n | WR% | PF | mean% | std% | Sharpe~ | Total% | MDD% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **multi_asset_cot solo** | 102 | 94.1 | **21.86** | 0.042 | 0.021 | 32.56 | 4.38 | 0.18 |
| multi_asset_copytrader solo | 943 | 21.6 | 0.71 | -0.002 | 0.021 | -1.83 | -2.25 | 2.48 |
| copytrader_no_FOREX | 281 | 37.7 | 1.00 | 0.000 | 0.038 | 0.00 | 0.00 | 1.44 |
| blend 60/40 (paired) | 102 | 94.1 | 16.26 | 0.025 | 0.019 | 21.27 | 2.58 | 0.15 |
| blend 50/50 | 102 | 94.1 | 14.42 | 0.021 | 0.020 | 16.62 | 2.13 | 0.14 |
| blend 40/60 | 102 | 78.4 | 11.01 | 0.016 | 0.021 | 12.16 | 1.69 | 0.13 |
| blend 60/40 (no-forex copytrader) | 102 | 94.1 | 15.27 | 0.028 | 0.022 | 20.05 | 2.90 | 0.17 |

## Findings

**Finding 1 — Blend never beats COT solo on any metric.** Every blend tested has lower Sharpe, lower total return, and roughly the same MDD as solo cot. The blend's only "improvement" is sample size (which is illusory — the pairing repeats copytrader rows in `itertools.cycle`).

**Finding 2 — FOREX exclusion doesn't rescue copytrader.** Even after stripping FOREX (which from AA-7 we know is the JPY-cross drag), copytrader_no_forex sits at PF 1.00 / Sharpe 0.00 — exact break-even. The COMMODITY+EQUITY rump isn't a positive-edge subset.

**Finding 3 — Heavy fabrication risk on COT side.** PF 21.86 on n=102 with WR 94.1% is suspicious. Same red flag as `multi_asset_cot` system-PF 19.19 in master plan. **NS-A DB-verify still pending** before any real-money sign-off on cot.

**Finding 4 — MDD compression is the only blend "win".** 0.18% solo → 0.13-0.17% blend. But absolute MDD is so small (<0.2%) on the cot side that the compression is noise.

## Interpretation

The blend hypothesis assumed copytrader carries a real signal that would diversify cot's COMMODITY exposure. AA-7 already showed copytrader's FOREX side is broken; this analysis shows the rest of copytrader is break-even. Blending a winner with break-even noise just dilutes the winner.

**Real conclusion:** If multi_asset_cot's edge is real (NS-A verification gate), trade it solo, sized for the 0.18% MDD profile. Blending is wrong unless we find an *uncorrelated positive-edge* counterparty — copytrader is not it.

## Recommendations

**R1 — Do not deploy 60/40 blend.** Solo cot dominates.

**R2 — Block on NS-A.** Cannot endorse cot solo until DB-verify confirms PF 21.86 / WR 94.1%. The PF reversal pattern (`kimi_signal_tracking` 0.28 → 8.38 from same resolver-denominator quirk) means dashboard payload alone is insufficient.

**R3 — Find a real diversifier for cot.** Backtested candidates from this session:
- ETF sector rotation: PF 2.05 / Sharpe 0.97 (TIER-1 PF) — already covered separate class
- EQUITY top-5 momentum: PF 2.82 / Sharpe 1.34 — separate class
- BOND HYG/LQD 6m momentum: PF 1.62 / Sharpe 0.57 — different duration profile, **potential diversifier**

Pair cot with BOND momentum overlay → low-correlation classes. Backtest queued.

**R4 — Mark copytrader for surgical class-and-symbol pruning.** AA-7 already addresses FOREX side. Run same per-symbol analysis on COMMODITY + EQUITY subsets of copytrader before any further blend attempt.

## Reproducer

```python
import json, statistics, math, itertools
rows = json.load(open('alpha_engine/data/closed_picks.json', encoding='utf-8'))
def stream(src):
    return [float(r['pnl_pct']) for r in rows
            if r.get('source_system')==src and r.get('pnl_pct') is not None]
cot = stream('multi_asset_cot')
cop = stream('multi_asset_copytrader')
def metrics(pnls):
    w = sum(1 for p in pnls if p>0); l = sum(1 for p in pnls if p<0)
    wr = w/(w+l)*100 if (w+l) else 0
    pf = sum(p for p in pnls if p>0)/sum(-p for p in pnls if p<0) if any(p<0 for p in pnls) else 999
    return wr, pf
print('cot:', metrics(cot), 'cop:', metrics(cop))
blend = [0.6*cot[i] + 0.4*cop[j] for i,j in zip(range(len(cot)), itertools.cycle(range(len(cop))))]
print('blend 60/40:', metrics(blend))
```

NFA. Reversible (no production change).
