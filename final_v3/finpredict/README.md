# final_v3 — finpredict (common themes + plan + focus decision)

Third and final review pass. Consolidates common themes across all peers, the full improvement plan (4 tracks of todos), and the focus decision on which asset classes + mutual-fund subset to pursue.

## Folder map

```
final_v3/finpredict/
├── README.md                ← this file
├── PLAN.md                  ← vast todo list: general / GH Actions / asset-class / backtest-sim
├── FOCUS_DECISION.md        ← which classes + MF subset (least $ in / lowest fee / least capital)
└── subq/
    ├── A_COMMON_THEMES.md   ← bugs + deeper-investigation (SubQ comparison)
    ├── B_ASSET_CLASS_RANKING.md ← 1 EQUITY, 2 CRYPTO, 3 FUTURES(blocked)
    └── C_MUTUAL_FUND_SUBSET.md  ← VTI + 3-fund core
```

## Common themes (the convergence across 10 peers)

**Top 5 bugs:** (1) PnL-unit mix off 100× (`dashboard_generator.py:8065-8072`); (2) EXPIRED→WON mislabeling (dashboard WR 78.9% vs raw 39.4%); (3) frozen prices as 0% PnL (`fetch_prices.php` 404 since 2026-04-29); (4) `scanner.py:2942` `KeyError:'LONG'` (~93 crashes/day); (5) `summary_picks` WR>100% + Python 3.14 masquerade (197 workflows).

**Top 3 deeper-investigation:** (1) 11 FOREX phantoms provenance; (2) PnL-unit root cause (which writer wrote fraction vs percent — need a `pnl_source` column); (3) whether trend/carry/VWAP edges survive a bear-inclusive window (0/40 trials pass the null; VWAP "3.76" falsified to ~1.18).

## Focus decision (headline)

- **EQUITY** (primary): diversified cross-sectional factor portfolio, benchmark-matched — the cheapest positive-expected-return path.
- **CRYPTO** (secondary): vol-targeted trend + funding carry, measured excess-of-benchmark on a bear-inclusive window.
- **Mutual funds:** `VTI` (0.03% ER, $0 min, fractional $1) + `BND` + `SGOV` core — the low-fee/low-min/low-capital "always-on" baseline (market beta + T-bill carry, not a trading edge).

## The honest framing

Mutual funds, equity beta, crypto trend, and funding carry are **risk premia / beta**, not contest-winning alpha — they win in the long-run, low-maintenance, low-capital sense. The 683-strategy zoo is overfit noise on broken data (0/166 money-ready). The profitable path is **one clean, benchmark-relative-validated sleeve per class** plus the passive index baseline as the control arm.
