# Focus decision (final_v4)

## Where to spend the next 90 days

**EQUITY (slot 1)** — the only class with a measured positive margin (clears 3.23× its cost structure, mean +0.323%/trade, stops respected at 0.91×, best exit bucket TIME_EXIT n=220 WR 61.4% PF 1.988). Needs a **benchmark-vs-SPY** test (not vs zero): 24 months, n≥500, OOS Sharpe ≥ SPY **and** PF ≥1.15. Caveat: t=1.52 (p=0.12), second-half PF fell 1.34→0.98 — likely beta, and peers already falsified 3 RSI(2) variants vs buy-and-hold.

**CRYPTO (slot 2, conditional)** — the only class with a *diagnosed, fixable* defect hiding a possible edge: late stop-fills were 1.54× planned risk = 98.8% of class loss, 94% from one system (**fixed today**). The condition: the fill fix must produce forward evidence that PF 0.768 → ~1.00. Then a vol-targeted trend sleeve + funding carry, benchmark-relative, on a bear-inclusive window.

**Everything else is blocked by arithmetic, not effort:** ETF 267% cost/PnL, COMMODITY 422%, FOREX −16.2pp breakeven gap, BOND n=35 + broken exit labels.

## Mutual funds / index — the "always-on" baseline (not a prediction edge)

Mutual funds **do not count** as a prediction edge — they are the equity risk premium, and cannot be measured intraday (monthly NAV). The user's real ask ("least money in, less maintenance, less capital") is answered by **index ETFs**:

- **Best default: `VTI`** — Vanguard Total Stock Market ETF, **0.03% ER, $0 minimum, fractional shares from ~$1** (least money, least maintenance, broker-portable). `FZROX` (0.00%/$0) only wins if locked to Fidelity.
- **3-fund core (~70/15/15):** `VTI` + `BND` (0.03%) + `SGOV`/`VGSH` (0.04–0.09%) — rebalance annually.
- **Expected:** ~7–9% nominal equity beta + ~4–5% current T-bill carry. This is the **market baseline** every repo "edge" failed to beat net of costs and selection bias — use it as the **control arm** (`BENCHMARK_SLEEVE` in `portfolio_defs.py` + a monthly `benchmark_snapshot.py`), never a pick emitter.

## Why not the others (one line each)

- **ETF** — cost exceeds edge (267% of PnL); index exposure is already covered by the VTI sleeve cheaper.
- **FOREX** — contaminated + a −16.2pp breakeven gap; carry is real but below the cost floor at keyless retail spreads.
- **BOND** — n=35, exit labels broken; the "edge" is duration beta, already in BND.
- **COMMODITY** — 422% cost ratio; the COT contrarian gate failed 4/4 today.
- **FUTURES** — highest ceiling (CTA trend) but data-blocked (no continuous contracts); revisit only with a real feed.

## The honest framing

EQUITY beta + crypto trend + funding carry + the VTI index sleeve are **risk premia / beta**, not contest-winning alpha — they win in the long-run, low-maintenance, low-capital sense. TradingView's +5,220% winner (from 59,187 entrants) and the 43%-profitable Commodities winner prove contests are survivorship + variance, not method. The profitable path is **one clean, benchmark-relative-validated sleeve per class** (EQUITY → CRYPTO) + the index control arm.
