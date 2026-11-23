#!/usr/bin/env python3
"""mechanism_audit.py — the operator's required per-pick fields, applied honestly per class.

For each asset class's best candidate, states:
  MECHANISM (which friction/risk premium), COUNTERPARTY (who loses), WHY THIS SYMBOL,
  WHY NOW, WHAT KILLS IT, and a verdict on whether the mechanism is real vs beta vs unproven.
The point is to refuse the "my scan ranked it" answer: if we cannot name the loser, we are the loser.
"""
import json

AUDIT = {
 "FOREX": {"pick":"AUDJPY long","n":34,"dsr":0.815,
   "mechanism":"G10 carry: AUD pays a higher rate than JPY (JPY is the funding currency). Long AUDJPY earns the rate differential while the carry trade is stable.",
   "counterparty":"JPY-funded carry traders who are forced to unwind in a risk-off shock (they buy JPY, sell AUD). The loser is the highly-levered carry position caught in the squeeze.",
   "why_this_symbol":"AUD is the highest-yield liquid commodity currency; JPY is the lowest-yield funding currency. AUDJPY is the purest expression of the G10 carry premium.",
   "why_now":"Cannot honestly state a live 'now' - the FX price feed ends 2026-02-09 and the pick pipeline has 5 open / 0 closed. Mechanism is structural, not event-driven.",
   "what_kills_it":"A risk-off/yen-squeeze regime (VIX spike, equity selloff) unwinds carry; and it must still clear DSR>=0.95 at honest N - it is 0.815, ~14 trades short.",
   "verdict":"REAL MECHANISM, NEAREST MISS - the only class where a documented risk premium and the best DSR coincide."},
 "STOCKS": {"pick":"CVX long","n":35,"dsr":0.318,
   "mechanism":"Energy/commodity momentum + value tilt: oil majors track crude, and value/energy outperforms in inflationary regimes.",
   "counterparty":"Index and ESG rebalancers who structurally underweight energy, plus panic sellers of cyclical equity.",
   "why_this_symbol":"Concentrated energy beta vs SPY's diluted exposure - but that is a SECTOR BET, so the 'edge' is a factor tilt, not alpha.",
   "why_now":"No dated trade series exists (0 realized EQUITY rows locally); cannot state a live now.",
   "what_kills_it":"Oil-momentum reversal; DSR 0.318 << 0.95; survivorship-biased universe.",
   "verdict":"BETA/TILT, UNPROVEN - the mechanism is a factor, not a demonstrated edge."},
 "ETF": {"pick":"SOXX long","n":37,"dsr":0.004,
   "mechanism":"Semiconductor cycle / tech capex beta.",
   "counterparty":"Late-cycle sellers and rebalancers; but a long-only ETF's counterparty is really just the market.",
   "why_this_symbol":"Concentrated sector beta vs broad SPY - a tilt, and highly correlated with XLK/QQQ (one bet, Finding 5).",
   "why_now":"No live price for sectors; cannot state a now.","what_kills_it":"DSR 0.004; sector drawdown; it is beta not alpha.",
   "verdict":"BETA, NOT ALPHA"},
 "CRYPTO": {"pick":"ETH long","n":155,"dsr":0.064,
   "mechanism":"BTC/ETH beta and reflexive momentum; possible staking yield, but no measured carry here.",
   "counterparty":"Leveraged late longs and liquidation cascades - the loser is the over-levered momentum chaser.",
   "why_this_symbol":"ETH has the best large-n crypto sample (n=155) and clears cost only at the major band; still noise.",
   "why_now":"Price data 8 months stale; no live now.","what_kills_it":"DSR 0.064; 20-52bp cost; net<=0 for most crypto.",
   "verdict":"WEAK/UNPROVEN - momentum, no measured edge."},
 "BOND": {"pick":"SGOV (T-bill) as cash hurdle","n":31,"dsr":0.0001,
   "mechanism":"T-bill carry - the risk-free rate (~3.9-4.3%/yr measured).",
   "counterparty":"Short-term cash borrowers (the T-bill market). This is the risk-free rate, so there is no 'loser' to exploit.",
   "why_this_symbol":"It IS the cash hurdle every strategy must beat.","why_now":"Always available.",
   "what_kills_it":"Nothing - it is the benchmark, not a pick.","verdict":"THE BAR, NOT A PICK (operator endorsed this framing)."},
 "MUTUAL_FUND": {"pick":"VTSAX (index)","n":0,"dsr":None,
   "mechanism":"Total-US-market equity risk premium (beta).",
   "counterparty":"Liquidity sellers / risk-averse rebalancers.","why_this_symbol":"0.995 correlated with SPY - same beta, cheapest access.",
   "why_now":"Always available.","what_kills_it":"Only the fee (MER) - the risk premium is the return you are buying.",
   "verdict":"BETA - fees decide, not edge."},
 "COMMODITY": {"pick":"none","n":85,"dsr":0.0,
   "mechanism":"No credible mechanism identified; class shows negative expectancy after a 20bp ASSUMED cost.",
   "counterparty":"Cannot name a consistent loser.","why_this_symbol":"N/A","why_now":"N/A",
   "what_kills_it":"Negative expectancy; cost is assumed not measured.","verdict":"NO MECHANISM - dead."},
 "OPTIONS": {"pick":"none","n":0,"mechanism":"No options data layer.","counterparty":"N/A","why_this_symbol":"N/A","why_now":"N/A","what_kills_it":"No data.","verdict":"UNRANKABLE"},
 "FUTURES": {"pick":"none","n":0,"mechanism":"No dated futures price.","counterparty":"N/A","why_this_symbol":"N/A","why_now":"N/A","what_kills_it":"No data.","verdict":"UNRANKABLE"},
 "PREDICTION_MARKETS": {"pick":"none","n":0,"mechanism":"Maker-only evidence; no measured OOS edge.","counterparty":"Takers crossing a wide spread.","why_this_symbol":"N/A","why_now":"N/A","what_kills_it":"No measured edge.","verdict":"UNRANKABLE"},
}

def main():
    out={"generated_at":__import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
         "rule":"refuse 'my scan ranked it'; if you cannot name the loser, you are the loser",
         "classes":AUDIT,
         "synthesis":"Only FX carry (AUDJPY) pairs a DOCUMENTED risk premium with the best DSR (0.815, ~14 trades from 0.95). "
                     "Everything else is beta (ETF/FUND/BOND), an unproven factor tilt (STOCKS), unproven momentum (CRYPTO), or no mechanism at all (COMMODITY). "
                     "This makes the FX data feed the highest-value procurement: it is the one place a real mechanism and a near-passing statistic coincide."}
    open("reports/mechanism_audit.json","w").write(json.dumps(out,indent=2)+"\n")
    for c,v in AUDIT.items():
        print(f"{c:20s} {v['verdict']}")

if __name__=="__main__":
    main()
