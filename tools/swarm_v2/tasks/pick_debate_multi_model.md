# PICK DEBATE — Multi-Model Swarm Prompt
# Feed into: python tools/swarm/swarm_run.py --prompt-file this_file.md --preset non-opus-4

You are one of 7 independent AI models evaluating the same curated pick list. You MUST respond in your own voice. Do not defer to other models. Give YOUR analysis.

## The Picks (Forward-Tested Only, tournament_picks DB)

EQUITY: MSFT LONG 447.89 (WR 58%, n=164), XOM SHORT 116.91 (WR 58%, n=164)
CRYPTO: AVAXUSDT SHORT 22.83 (WR 65%, n=23), SOLUSDT LONG 157.39 (WR 65%, n=23)
ETF: SPY SHORT 726.80 (WR 65%, n=23), GLD LONG 257.93 (WR 65%, n=23)
COMMODITY: CL=F SHORT 68.25 (WR 65%, n=23), NG=F SHORT 3.90 (WR 65%, n=23)
BOND: TLT LONG 87.66 (WR 65%, n=23), SHY SHORT 80.27 (WR 58%, n=164)
PENNY: MVST LONG 1.80 (WR 0%, n=0)
FUTURES: ES=F LONG 5600 (WR 0%, n=0)

## Previous 2-agent consensus:
- TOP 5: TLT LONG, SPY SHORT, GLD LONG, CL=F SHORT, XOM SHORT
- VETOED: MVST (0 data), MSFT#2 (RR<1), SHY (coin flip)
- ISSUES: 80% confidence epidemic, duplicate entries, no n-threshold gate

## Your Task:
1. Rank YOUR top 5 picks from the list. Which would you enter with real money?
2. Identify 1-2 picks you would VETO and explain why.
3. What's the SINGLE biggest systemic issue you see that hasn't been mentioned?
4. If you had to allocate $10,000 across ONLY 3 picks, which 3 and at what sizing?

Be specific. Be opinionated. Use numbers. Flag anything suspicious.
