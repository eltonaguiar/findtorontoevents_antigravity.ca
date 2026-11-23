# COMS wake for vanilla-handsaw/kilo — end-goal chain

**Date:** 2026-11-23T00:30Z
**From:** kilo (vanilla-handsaw)
**To:** self / mentions/all

**Status:** parity items 2–5 complete (P0-1/2/3/P1-4/P1-5 verifier shipped). P1-6/P1-6b/P1-6c complete (EQUITY cost 5.13 bps Questrade net, PIT 17 names 768 trades, borrow=long_only_0_bps, POD-EQUITY-BREAKOUT retired).

**Next wave (background task running):**
- P2-9: assert_surface_parity.py + /audit2 LEDGER_SERVED_FROM
- END-GOAL A: per-asset-class ranked pick list (reports/asset_class_rankings.json)
- END-GOAL B: overall cross-class ranking for real-money human
- END-GOAL C/D: backtest + quant metrics (Sharpe, Sortino, MaxDD, PF, DSR, PBO, net-of-cost)

**Wake condition:** any of the above files appear or are updated, or the next hourly audit3-ledger cron lands a fresh ledger.

**Goal reminder:** produce a ranked list of picks per asset class + overall best real-money option(s) for a human, then backtest the examples under identical entry criteria and report quant metrics.

Do not start new scanners until N7 freeze gate (E11/E13/E14) is green. Zero real money until forward n>=100, PF CI-LB>1.0, 100% intrabar honesty.

See updates/2026-11-23-P1-5-benchmark-blocker-verifier.md and reports/pit_universe_EQUITY.json.
