# Algorithm Specifications — Per Asset Class

**Package:** WIRED_IN/2026-11-15_0125/finpredict-v4
**Author:** finpredict-v4
**Date:** 2026-11-15

---

## Overview

The only deployable edge family that survived all audits and backtests is **long-term trend / momentum persistence** (Faber 200-day MA; dual momentum) combined with **low-cost beta allocation**. Intraday scalping/day-trading was eliminated across all classes (see `elimination_rationale`).

This document specifies the live algorithm per asset class that feeds the audit dashboard (`findtorontoevents.ca/audit`).

---

## 1. Mutual Funds / ETF Allocation Core

- **Algorithm:** 3-fund core (VTI 70% / BND 15% / SGOV 15%) + optional tactical override.
- **Signal:** Faber 200-day MA trend filter. When price < 200dMA, rotate weight toward the defensive sleeve (TLT/SGOV/BND).
- **Frequency:** monthly rebalance (21 trading days).
- **Data:** yfinance auto-adjusted closes.
- **Weights:** equal-weight among assets above 200dMA; defensive floor always on.
- **Exit:** none for core (hold); tactical sleeve exits when asset drops below 200dMA.
- **Backtest result:** Sharpe 1.01 vs 0.79 B&H; maxDD -18.8% vs -46.3%; final 7.39× vs 7.93× (2008–2026, cost-inclusive).

---

## 2. EQUITY (US)

- **Algorithm:** Faber 200-day MA trend + 6-month cross-sectional momentum (AQR/Clenow style, vol-targeted).
- **Stage:** research/pilot — NOT yet live-deployed (SPY gate failed in final audit → NO_ALPHA_BETA).
- **If deployed:** only above 200dMA; single-name picks filtered through the trend filter.
- **Elimination reason:** intraday RSI-2/scalping removed; only long-horizon trend retained.
- **Backtest:** trend filter proven; momentum documented (Clenow/AQR) but requires vol management.

---

## 3. CRYPTO (conditional pilot)

- **Algorithm:** swing momentum (POSITION horizon) on liquid pairs; short-biased where validated.
- **Stage:** shadow forward-test only (no live capital until n≥100, PF≥1.3, WR≥55%).
- **Guard:** route `kimi_riseoftheclaw` through intrabar resolver (fill at stop, gap-aware).
- **Elimination:** scalping / short-hold engines removed (fill bugs, cost drag).

---

## 4. FOREX

- **Algorithm:** low-frequency carry + trend (TSMOM 12m), swap-cost-accounted.
- **Stage:** HARD-DISABLED until data is clean (96.6% null PnL historically).
- **Elimination:** intraday session scalping removed; contrarian sentiment removed (anti-skill).

---

## 5. BOND

- **Algorithm:** duration rotation / 200-day trend on TLT; NAV-driven allocation (BND core).
- **Stage:** accumulating n (currently ~18-26 < 60 floor); FRED unblock needed.
- **Elimination:** intraday bond trading removed.

---

## 6. COMMODITY / FUTURES

- **Algorithm:** CTA trend (TSMOM, 200-day MA) on real futures; real feed required.
- **Stage:** blocked until real feed + 30-day paper track (COT gate failed 4/4, removed).
- **Elimination:** COT contrarian removed; crypto-proxy commodities removed.

---

## 7. ETF Tactical Sleeve

- **Algorithm:** monthly dual-momentum / Faber rotation on SPY/QQQ/IWM/TLT/GLD.
- **Stage:** enabled (this is the live emitter — see the pick justification for VTI/TLT/SGOV/BND).
- **Elimination:** intraday ETF strategies removed (WR 2.2% conclusive).

---

## 8. Prediction Markets (Kalshi/Polymarket)

- **Algorithm:** none — structurally not pursued (zero-sum + fees + adverse selection).
- **Elimination:** copy-trading removed (see elimination rationale).

---

## Live-emitted picks today (from the spec)

| Symbol | Class | Direction | Algorithm |
|--------|-------|-----------|-----------|
| VTI | ETF | STRONG_BUY | Above 200dMA, momentum |
| TLT | BOND | STRONG_BUY | Defensive flight-to-safety |
| SGOV | BOND | STRONG_BUY | T-bill floor |
| BND | BOND | STRONG_BUY | Bond core |
