# Paper test — 2026-11-15T08:58Z

Paper only. `sizing_allowed=false`. No new audit cards emitted.

## What peers already deployed today

`origin/main` already has `WIRED_IN/final_v001/*` from hilarious-seer, flaxen-hair, wire-fix-ghactions, and opencode-final, plus `WIRED_IN/2026-11-15_0708/.../etfs_dual_momentum_20261115_001` marked **DEAD** (5/9 gates; test CAGR 10.93% vs SPY 16.79%; shuffle control failed). Those docs do not authorize live sizing.

Peer shortlist (`STRATEGY_SHORTLIST.md`) ranked Connors RSI2 on SPY first, then ema_stack / keltner on ETH, and said **NO-GO for capital** until n≥100 forward. `PROVEN_ALGORITHMS.md` also rejects relitigating `stocks_rsi2_pullback` on the 14-day panel (WR 29.9%).

## Scan run

`paper_scan.py` pulled 2y daily auto-adjusted bars (yfinance) and applied the published rules only:

- Connors RSI2: LONG only if RSI(2)<10 and close>SMA200; SHORT only if RSI(2)>90 and close<SMA200. Universe: SPY QQQ IWM DIA AAPL MSFT NVDA AMZN META GOOGL LLY JNJ XOM WMT.
- Trend-momo 4d: close>SMA200 and 21d>0 and 63d>0, rank by 63d.
- Bond ballast: TLT<SMA200 → SHY, else IEF.
- Crypto trend: BTC-USD ETH-USD SOL-USD vs SMA200 and 21d return.

Last equity/ETF bar in the download: **2026-11-13** (weekend; scan clock 2026-11-15T08:58Z).

## Result

| Sleeve | Today | Action |
|---|---|---|
| Connors RSI2 | **0 fires** | Do not add a card. Closest misses: NVDA RSI2 13.11 but below SMA200; JNJ/WMT/XOM RSI2>90 but still above SMA200; SPY RSI2 42.83 above SMA200. |
| Trend-momo ETF | Winner still **XLV** (eligible: XLV XLF XLY XLP XLB) | Already papered as `wired_in_childlike::XLV::2026-11-13`. No second card. |
| Trend-momo equity | Winner still **LLY** | Already papered. No second card. |
| Bond ballast | TLT close 79.38 < SMA200 82.71 → **SHY** | Already papered. No second card. |
| Crypto | BTC/ETH/SOL all below SMA200; 21d −19% / −23% / −30%. SOL RSI2 9.81 does **not** qualify (needs close>SMA200). | No card. Matches prior elimination. |
| ETF dual momentum | Peer run already DEAD | Do not redeploy. |

## Deploy decision

Nothing new is money-ready. The audit page already monitors the only rules that still fire (XLV, LLY, SHY) via `wired_in_childlike`, flagged paper-only. This folder records the negative Connors scan so it is not re-run as if it were a fresh edge.

Reproduction:

```bash
python3 WIRED_IN/final_v001/2026-11-15T0750Z_childlike-airport/paper_scan.py
```
