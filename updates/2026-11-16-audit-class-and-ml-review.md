# Audit class, prediction, ML, and risk review

Date: 2026-11-16. Live page https://findtorontoevents.ca/audit/ and `/audit/data/money_ready_verdict.json`, `intrabar_truth_by_class.json`, `dashboard_data.json`, `db_health.json`.

## Verdict

No asset class is money-ready. Book n=7805, WR 40.9%, PF 0.91, expectancy -0.16, compounded PnL -77.7%, Sharpe -0.109. Ghost rows 22,947, tier red.

| Class | n | WR | PF | Note |
|---|---:|---:|---:|---|
| CRYPTO | 3716 | 35.8% | 0.92 | DSR 0. PBO 0.0 is not a real pass. |
| FOREX | 618 | 32.0% | 0.65 | Losing. |
| EQUITY | 250 | 59.2% | 0.94 | High WR, still losing. |
| COMMODITY | 231 | 40.3% | 1.03 | Only PF>1 class with n>=100. DSR 0. WATCH, not ready. |
| FUTURES | 53 | 41.5% | 1.07 | n too small. DSR 0.58. |
| ETF | 45 | 2.2% | 0.02 | Intrabar book. Do not use the daily PF 1.79 tile. |
| BOND | 26 | 7.7% | 0.39 | Insufficient. |
| MEMECOIN | 102 intrabar / 10 class | 29.4% | 0.66 | Regime-concentrated. |
| PENNY / CHEAP | 4 / 1 | — | — | Insufficient. |

Prediction markets are not a book. Polymarket/Kalshi system rows have closed_picks=0. The verified-alpha realized slice is losing (n=896, WR 42.4%, PnL -193%). Prior PBO 0.603 stays shadow.

## What the stack actually does

ML gatekeeper filters and re-ranks. It does not prove profit. `ml_score >= 0.0` counts as validated. Consensus is a hand formula, not a trained model. Position sizing (Kelly, regime, heat) is not tied to DSR, PBO, WFE, live Sharpe, and n>=100 together.

The class verdict can still say MONEY_READY through an SPA OR, with PBO allowed up to 0.55 and no WFE or live-Sharpe check. The page filter was worse: a hardcoded historical list (COT cotton, two ML sleeves at n=31 and n=34) could show MONEY READY, and a missing verdict passed.

## Change in this PR

`audit_dashboard/money_ready_filter.js` now fails closed. A pick is hidden unless the sleeve has all five gates and the class verdict is MONEY_READY. The historical list does not pass. This does not change the scanner, the sizer, or the database.

Not in this PR: `audit_trail/stamp_pick_quality.py` still writes PROVEN at n>=10 and WR>=55%. That relabels stored picks and needs its own review.

## COMS

No peer reply on `inbox/gx10-c9b9/auditpage/grok-4-7` before this note. Other seats were idle or watching their own PRs. None objected to the earlier honesty merge.
