# MUTUAL FUNDS — Honest Assessment

**Asset Class:** MUTUAL FUNDS
**Status:** NOT_BUILT (Consensus: do not build)
**Date:** 2026-11-14
**Sources:** finpredict-v3, scratch-hippodraco, finpredict-v2

---

## Verdict: Do NOT Build a Live MF Pick Class

**Unanimous consensus across all peers:**

| Peer | Position |
|------|----------|
| finpredict-v3 | "De-advertise (NOT_BUILT) and do not build a live pick class." |
| scratch-hippodraco | "No intraday edge is possible (monthly NAV, no mark-to-market)." |
| finpredict-v2 | "If ever built: only a monthly tactical-rotation backtest vs a risk-matched benchmark." |
| hilarious-seer | Agrees with consensus. |

---

## Why Mutual Funds Cannot Be a Live Pick Class

1. **Monthly NAV only** — Mutual funds price once per day after market close. There is no intraday mark-to-market.
2. **No real-time PnL** — A "pick" on a mutual fund cannot show live PnL because the price is unknown until 4 PM ET.
3. **No TP/SL intraday** — Stop-losses and take-profits cannot be executed intraday; they execute at the next NAV.
4. **Stale data** — The current dashboard shows MF picks but they are all stale placeholders.
5. **Regulatory restrictions** — Many mutual funds have frequent-trading restrictions (e.g., 30-day hold periods).

---

## What CAN Be Done With Mutual Funds

### Monthly Tactical Rotation (Research Only)
- **Frequency:** Monthly rebalancing
- **Signal:** Momentum, value, or risk-parity across fund categories (large-cap, small-cap, international, bonds)
- **Data:** Morningstar or fund company NAV history
- **Output:** Asset allocation recommendation (not live picks)

### Honest Label
Keep the class labeled `NOT_BUILT` on the dashboard. Do not show MF picks as "active" or "money-ready." If research is conducted, label it clearly as "monthly allocation research, not live trading."

---

## If User Insists on MF Coverage

Requirements:
1. Monthly NAV data feed (Morningstar API or fund company CSV)
2. 10+ year history for backtesting
3. Monthly rebalancing only (no intraday claims)
4. Cost model including fund expense ratios + any load fees
5. Benchmark: appropriate fund category average, not absolute return
6. Walk-forward with monthly folds
7. Label as "allocation research" — never as "live picks"

Effort: Large (3–6 months)
Expected Sharpe: 0.2–0.5 (lower than all other classes)
Priority: Lowest

---

## Bottom Line

**Mutual funds have no place in an intraday pick-trading system.** The entire architecture (live PnL, TP/SL, intraday resolution) is incompatible with monthly NAV pricing. Keep `NOT_BUILT` and focus resources on CRYPTO, ETF, and EQUITY where real edge is possible.
