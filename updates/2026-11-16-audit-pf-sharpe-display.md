# Audit display no longer prints infinite PF or explosive Sharpe

What was broken: the headline Profit Factor card rendered `∞` when a filtered book had wins and zero losses (`audit_dashboard/template.html` profitFactor ternary). The walk-forward table printed raw `oos_sharpe`, including BOND −65.632, which is a small-sample scale bug, not an edge.

What changed: zero-loss profit factor and win/loss ratio are null and display `n/a`. Walk-forward Sharpe with `|value| > 5`, non-finite value, or the existing tiny-fold flag displays `n/a`. Prediction-market sources and `copy_pm_` strategies no longer pass `_is_verified_alpha_pick` or `isVerifiedAlphaPick`. Other copy-trader rows are unchanged. No sizing and no database writes.

How verified: `python3 -m pytest tests/test_audit_truth_claims.py -q`.

Impact: display only. Unfiltered headline PF still comes from `s.profit_factor`. Deploy is the next `audit-dashboard.yml` cron, which does not block on this template edit. Live `/audit/` at review time still showed the pre-#843 copy because the 15:25Z scheduled run started before merge `9842be43e982`.
