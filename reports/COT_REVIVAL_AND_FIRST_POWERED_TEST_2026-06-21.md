# COT alt-data revival + first properly-powered new-data test (2026-06-20/21)
**Author:** claude-opus · operator-chosen "alt-data collector revival" · all SQL-verified

## Delivered (autonomous, committed to main)
- **Insider feed revived:** `tools/refresh_insider_trades.py` (broadened to 153-ticker universe, idempotent upsert) + weekly workflow + table backed up. 400d landing run executed. CAVEAT: open-market buys (code P) are sparse on US large-caps → the insider anomaly is **forward-accrual-gated**.
- **COT feed revived + LANDED:** `tools/refresh_cftc_cot.py` → `cftc_cot_weekly` (5yr, 11 commodities, 2,618 rows) + weekly workflow.
- **NEW price feed created:** `futures_daily_ohlcv` (5yr daily, 11 commodity futures via yfinance, 13,833 rows) — the price side that makes COT (and other commodity signals) backtestable.

## First properly-powered new-data backtest — COT commercial-hedger (H-134/H-135)
The first new-data avenue this session with BOTH signal + price at 5yr depth → **not n-starved** (H-134 n_eff=207). Pre-registered (Briese commercial-hedger = "smart money"; |z|>1 on trailing-52wk comm_net_pct_of_oi → directional; net@3bp).

| Hypothesis | horizon | n | net PF | CI-LB | n_eff | IS/OOS | verdict |
|---|---|---|---|---|---|---|---|
| H-134 | 5-day | 1006 | 1.072 | 0.886 | 207 | 1.11/1.04 | **sub-bar** |
| H-135 | 20-day | 255 | 1.252 | 0.925 | 48 | **1.60/1.00** | **sub-bar + OOS-decayed** |

**Verdict: COT commercial-hedger is real-but-weak, NOT promotable** — doesn't clear the 1.15 CI-LB bar net of cost at either horizon; the 20-day's higher point PF is front-loaded (OOS collapses to breakeven). Family closed (no horizon-fishing). This is a *clean, honest, properly-powered* refutation — the first new source tested without an n-starvation excuse.

## What this UNLOCKS (next, data-feasible NOW)
`futures_daily_ohlcv` (5yr daily, 11 commodities) is a real price feed I just created. It makes several classic commodity signals **immediately backtestable** for the first time:
1. **Commodity time-series momentum (TSMOM)** — Moskowitz-Ooi-Pedersen 2012; the canonical CTA/managed-futures edge. 12-month trend, vol-scaled, monthly hold. Strong academic prior + 5yr × 11 = adequate n. **Highest-value next test.**
2. Cross-sectional commodity momentum / carry (roll-yield) — needs back-month contracts (only front available) so carry is gated; momentum is feasible.
3. Commodity seasonality (sanctioned source) — grains (ZC/ZS/ZW) have documented seasonal patterns.

## Net
The collector-revival direction delivered 2 maintained feeds + a new price feed + the first properly-powered new-data verdict. COT itself is sub-bar, but the infrastructure now enables the commodity TSMOM test (next), which has the strongest academic prior of any remaining data-feasible avenue.
