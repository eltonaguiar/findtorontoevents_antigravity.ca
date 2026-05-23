# Strategy Regeneration After Walk-Forward Gate Failure

You are a quantitative researcher with Lopez de Prado level expertise.

## Context
A trading system has:
- 14 hypotheses killed by a walk-forward eff-stability harness (sign-flip pattern)
- The gate requires: efficiency score >= 0.30 in the same direction across 3+ of 5 14-day windows
- EQUITY is the strongest class: PF~1.55, WR~51%, n=426 (post-resolver recent)
- No hypothesis has passed the gate — all show sign-flip (strategy appears profitable in some windows, unprofitable in others)

## Task
Answer: What are the 3 most likely structural reasons that ALL 14 hypotheses fail a walk-forward eff-stability gate with a sign-flip pattern?

For each reason:
1. Name the root cause
2. Explain the mechanism (why does it produce sign-flip?)
3. What is the ONE actionable fix?

Then: Given that 0/14 hypotheses pass, what is the single highest-probability action for finding real edge? Choose from:
(a) better data / intraday resolution
(b) different test statistic (e.g., replace efficiency ratio with directional accuracy)
(c) longer windows (28-day instead of 14-day)
(d) ensemble of weak signals (combine multiple sub-threshold signals)
(e) something else — specify what

Justify your choice with a statistical argument, not intuition.
