You are reviewing a PRE-REGISTERED hypothesis before any data is touched. Answer from the text only; do not run tools, do not read files, and do not ask for more data. Be specific and terse.

Hypothesis H-146 (EQUITY, registered 2026-11-21):
- Universe: US common stocks, market cap $2B-$10B at formation, monthly snapshot (no index list).
- Signal: gross profitability GP/A = (revenue - cost of revenue) / total assets, from the most recent quarterly statement filed STRICTLY before the rebalance date.
- Portfolio: month-end rank on GP/A, long top quintile equal-weight.
- Holding: enter next session open, exit at first month-end >= 20 calendar days and <= 60 calendar days.
- Benchmark: pre-declared MKT/SMB/HML/RMW factors.
- Acceptance: walk-forward eff >= 0.30 on >= 3 admissible windows, same sign, >= 60% of gross edge surviving 2x measured slippage plus funding, forward n >= 100, net information ratio >= 0.50, falsified within 90 days.
- Context: the EQUITY aggregate over 955 closed picks is net +0.098% per trade with 95% CI [-0.516, +0.720] -- indistinguishable from zero.

Separately: the Deflated Sharpe gate for CRYPTO ran with a 14-trial baseline (legacy) and scored 0.9978 (would pass). Raised to 629 measured strategy cells, it scores 0.9284 (fails). The gate's threshold is 0.95. Breakpoint: 345 trials. DSR is monotone decreasing in trial count, so raising a baseline can only turn a pass into a fail; no class already failing can be rescued by a larger count.

Answer these four questions, numbered, no preamble:
1. Name the single biggest leak or overfit risk in H-146 as written, and the one sentence that would close it.
2. Does the 20-60 day exit band create a look-ahead or survivorship path? Answer yes/no, then why in one sentence.
3. Is the acceptance rule (eff >= 0.30 AND IR >= 0.50 AND n >= 100) too strict, about right, or too loose, given a base rate of zero measured edge? One sentence.
4. Should CRYPTO stay open as a search space given that its DSR now fails at 629 trials but its net CI excludes zero only on the negative side? One sentence.
