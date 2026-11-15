#!/usr/bin/env python3
"""Consult SubQ Snap (Decisions API, POST /v1/systemone) on the profitability questions.

This API key permits only the Decisions API (chat/responses need subq-savant-1.4, not
permitted here). Snap returns typed answers: noul (P(yes)), choice (per-option
probabilities + confidence), score (probability-weighted level + legend + confidence).

Usage: python ask_subq.py [query_name ...]     # default: all queries
Key read from %TEMP%/subq_key.txt (never printed, never committed).
Output: subq_responses.json next to this script (merged additively on re-run).
"""
import io
import json
import os
import sys
import time
import urllib.request

BASE = "https://api.subq.ai/v1/systemone"
MODEL = "subq-snap-1.2"
KEYFILE = os.path.join(os.environ.get("TEMP", "/tmp"), "subq_key.txt")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subq_responses.json")

STYLE_OPTS = {
    "day": "intraday, flat before close",
    "swing": "hours to a few days",
    "position": "days to ~2 weeks",
    "longterm": "weeks to months, monthly cadence",
}
OBSTACLE_OPTS = {
    "costs": "round-trip costs (spread/fees/slippage) exceed the edge",
    "data": "data quality/fills make measurement untrustworthy",
    "competition": "crowded/efficient market, no residual edge",
    "infrastructure": "missing infrastructure (feeds, execution, coverage)",
}
PROB_SCORE = ["<10%", "10-25%", "25-40%", "40-55%", "55-70%", ">70%"]
EVIDENCE_SCORE = ["No credible evidence", "Retail folklore only", "Mixed/weak",
                  "Replicated academically", "Academic + real money", "Strong, durable, capacity-tested"]
SHARPE_SCORE = ["<0.5", "0.5-0.7", "0.7-1.0", "1.0-1.5", "1.5-2.0", ">2.0"]

CLASSES = ["CRYPTO", "EQUITY_US", "COMMODITY_FUTURES", "ETF", "BOND", "FOREX", "MUTUAL_FUNDS"]

QUERIES = {
    "q1_asset_class_ranking": {
        "state": (
            "A small-team retail algo-trading system has failed for years to show profit in ANY asset class "
            "(crypto, US equities, futures/commodities, ETFs, bonds, forex; no mutual-fund coverage). "
            "Measurement is currently being fixed: PnL recomputed vs market data, stop-fill slippage modeled. "
            "Constraints per class: round-trip cost per trade, data quality/reliability, competition intensity. "
            "Ranking target: probability of reaching REAL risk-adjusted profitability within 2 years."
        ),
        "questions": dict(
            [("prob_" + c.lower(), {"type": "score",
              "instructions": "Probability that %s reaches real risk-adjusted profitability within 2 years for this small team." % c,
              "criteria": PROB_SCORE}) for c in CLASSES] +
            [("style_" + c.lower(), {"type": "choice",
              "instructions": "Holding-period style structurally required for %s (the one that can even work there)." % c,
              "criteria": STYLE_OPTS}) for c in CLASSES] +
            [("obstacle_" + c.lower(), {"type": "choice",
              "instructions": "Single biggest structural obstacle for %s." % c,
              "criteria": OBSTACLE_OPTS}) for c in CLASSES]
        ),
    },
    "q2_benchmark_relative": {
        "state": (
            "A strategy must outperform (i) buy-and-hold SPY and (ii) a 60/40 portfolio on a risk-adjusted basis "
            "(Sharpe, Sortino, max drawdown) over 24+ months of forward data before capital is allocated. "
            "Context: most retail backtests that 'beat SPY' fail after realistic costs and multiple-testing "
            "correction; the team has a history of testing many hypotheses (multiple comparisons)."
        ),
        "questions": {
            "min_forward_months": {"type": "score",
                "instructions": "Minimum months of forward, cost-adjusted, out-of-sample data to credibly claim 'beats buy-and-hold'.",
                "criteria": ["<12", "12-18", "18-24", "24-30", "30-36", ">36"]},
            "excess_sharpe_worth": {"type": "score",
                "instructions": "Defensible excess Sharpe (strategy Sharpe minus SPY Sharpe) that is actually worth pursuing and likely real.",
                "criteria": SHARPE_SCORE},
            "primary_gate": {"type": "choice",
                "instructions": "Which single test should be the primary gate for a 'beats buy-and-hold' claim?",
                "criteria": {
                    "benchmark_ttest": "paired test of strategy vs SPY returns (t/DSR on the difference)",
                    "walkforward": "walk-forward windows all positive across regimes",
                    "deflated_sharpe": "Sharpe deflated for number of trials tried",
                    "forward_paper": "live forward paper-trading at stated costs",
                    "all_prereg": "pre-registered combo of the above with kill criteria"}},
            "costs_before_costs": {"type": "noul",
                "instructions": "Does a backtest that beats SPY before costs but not after count as NO evidence of edge?",
                "criteria": {"true": "costs are part of the edge, not an implementation detail",
                             "false": "pre-cost edge can still be real if execution improves"}},
        },
    },
    "q3_copytrading_prediction_markets": {
        "state": (
            "Traders have tried copy-trading winners on prediction markets (Kalshi, Polymarket) and copy-trading "
            "signal providers in crypto, yet still lose. Candidate structural reasons: (1) adverse selection of "
            "who publishes trades (hot-streak selection), (2) latency/slippage between their fill and your copy, "
            "(3) fee/spread arithmetic (1-2 cents on a 50-cent contract = 4% of notional round trip), "
            "(4) quote-vs-resolution mismatch (different payoff function), (5) small-n resolution randomness "
            "(60% hit rate over 30 trades has roughly +/-17pp 95% CI), (6) winner non-stationarity "
            "(winners stop/scale/get banned), (7) self-defeating volume (copying moves the price)."
        ),
        "questions": dict(
            [("reason_%d_class" % i, {"type": "choice",
              "instructions": "Reason %d: what kind of claim is it?" % i,
              "criteria": {
                  "arithmetic": "provable arithmetic (follows from definitions, no probability needed)",
                  "quantifiable": "probabilistic but directly quantifiable from data",
                  "game_theory": "game-theoretic/self-defeating equilibrium argument",
                  "empirical": "empirical regularity that could fail"}})
             for i in range(1, 8)] +
            [("latency_beats", {"type": "noul",
              "instructions": "Would sub-second API mirroring with costs in the loop remove most of the copy-trading failure modes?",
              "criteria": {"true": "execution and costs are the dominant failure",
                           "false": "selection and non-stationarity dominate regardless of speed"}}),
             ("n_ge_100_leader", {"type": "noul",
              "instructions": "Is requiring the copied leader to have n>=100 trades with a Wilson CI above 50% a reasonable minimum bar?",
              "criteria": {"true": "small-n streaks are indistinguishable from luck",
                           "false": "even n=100 overfits in prediction markets"}})]
        ),
    },
    "q4_mutual_funds_path": {
        "state": (
            "Mutual funds: NAV priced once daily, long-only, 30-day frequent-trading limits, expense ratios "
            "0.03-1%. The team believes mutual funds would be winners 'given enough time'. Questions: under what "
            "conditions could a mutual-fund selection or rotation system reliably beat a low-cost index fund? "
            "Consider style/sector rotation lag, survivorship bias in fund databases, after-cost drag, and "
            "whether the honest answer is 'hold low-cost index funds' vs 'active selection'."
        ),
        "questions": {
            "active_beats_after_costs": {"type": "noul",
                "instructions": "Can mutual-fund ACTIVE selection reliably beat its low-cost index benchmark AFTER all costs over a full cycle?",
                "criteria": {"true": "selection skill exists and survives fees",
                             "false": "fees + survivorship + lag make the honest default passive"}},
            "rotation_beats_cash": {"type": "noul",
                "instructions": "Is a simple monthly momentum-rotation sleeve over low-cost broad funds more likely to beat cash+fees than to lose?",
                "criteria": {"true": "documented risk premia + low costs make this likely",
                             "false": "rotation timing can also destroy beta"}},
            "prob_rotation_positive": {"type": "score",
                "instructions": "Probability a pre-registered low-cost fund rotation sleeve has positive net return over 10 years.",
                "criteria": PROB_SCORE},
            "minimal_infra": {"type": "choice",
                "instructions": "Single most important infrastructure to build FIRST to test any mutual-fund strategy properly.",
                "criteria": {
                    "nav_cache": "daily NAV cache + fund metadata (ER, AUM, inception)",
                    "pit_universe": "point-in-time universe (no survivorship)",
                    "shareclass_dedup": "share-class deduplication (same portfolio, many classes)",
                    "cost_model": "after-cost drag model (12b-1 fees, redemption fees, spreads)"}},
            "prob_active_positive": {"type": "score",
                "instructions": "Probability that ACTIVE fund selection (not rotation) beats its index after costs over a full cycle.",
                "criteria": PROB_SCORE},
        },
    },
    "q5_proven_algorithms": {
        "state": (
            "Which algorithm families have the strongest historical evidence (academic replication + real-money "
            "track records): trend following/Donchian, momentum factor, value factor, mean reversion RSI(2), "
            "carry, volatility risk premium, pairs/stat-arb, market making, and retail-popular methods "
            "(ICT/FVG 'smart money', most TradingView indicators)? For each, judge evidence quality and "
            "decay status into the 2010s-2020s."
        ),
        "questions": dict(
            [("evidence_" + k, {"type": "score",
              "instructions": "Evidence quality for %s (replication + real-money durability, net of the decay seen in 2010s-2020s)." % name,
              "criteria": EVIDENCE_SCORE})
             for k, name in [
                 ("trend", "Donchian/turtle-style trend following"),
                 ("momentum", "cross-sectional momentum factor"),
                 ("value", "value factor"),
                 ("rsi2", "RSI(2) short mean reversion"),
                 ("carry", "carry trades"),
                 ("volrisk", "volatility risk premium selling"),
                 ("pairs", "pairs/statistical arbitrage"),
                 ("mkmaking", "market making"),
                 ("ict", "ICT concepts (fair value gaps, smart money)"),
                 ("tv_indicators", "typical TradingView indicator strategies"),
             ]] +
            [("retail_no_evidence", {"type": "noul",
              "instructions": "Do ICT/FVG 'smart money' concepts have peer-reviewed or documented real-money evidence?",
              "criteria": {"true": "there is credible published evidence",
                           "false": "the evidence is anecdotal or absent"}})]
        ),
    },
    "q6_key_metrics_bar": {
        "state": (
            "Key metrics and thresholds that must be satisfied before trusting a trading system with real money, "
            "from four perspectives: (1) quant hedge fund risk committee, (2) mutual fund manager "
            "(UCITS/retail constraints), (3) a bank's top proprietary trader, (4) a retail trader paper-trading. "
            "Metrics on the table: Sharpe, Sortino, max drawdown, Calmar, profit factor, hit rate with Wilson CI, "
            "capacity/slippage, turnover, benchmark-relative excess return."
        ),
        "questions": dict(
            [("most_matters_p%d" % i, {"type": "choice",
              "instructions": name + ": which single metric matters MOST when deciding to trust the system with real money?",
              "criteria": {
                  "sharpe": "Sharpe ratio (risk-adjusted return per unit vol)",
                  "maxdd": "max drawdown / permanent loss risk",
                  "excess": "excess return vs the benchmark actually used",
                  "pf": "profit factor / expectancy consistency",
                  "hitrate_ci": "hit rate with Wilson confidence interval",
                  "capacity": "capacity and slippage at intended size",
                  "calmar": "Calmar (return per unit drawdown)",
                  "var_tail": "tail risk (VaR/ES, stress tests)"}})
             for i, name in [(1, "Quant hedge fund risk committee"),
                             (2, "Mutual fund manager (UCITS/retail)"),
                             (3, "Bank top proprietary trader"),
                             (4, "Retail trader paper-trading")]] +
            [("min_sharpe_p%d" % i, {"type": "score",
              "instructions": name + ": minimum Sharpe (net, vs own benchmark) that would clear the bar.",
              "criteria": SHARPE_SCORE})
             for i, name in [(1, "Quant hedge fund risk committee"),
                             (2, "Mutual fund manager (UCITS/retail)"),
                             (3, "Bank top proprietary trader"),
                             (4, "Retail trader paper-trading")]]
        ),
    },
}


def ask(name, spec):
    body = json.dumps({"model": MODEL, "state": spec["state"],
                       "questions": spec["questions"]}).encode()
    with io.open(KEYFILE) as kf:
        key = kf.read().strip()
    req = urllib.request.Request(BASE, data=body, method="POST", headers={
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
    })
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read().decode())
    if "error" in data:
        return {"error": data["error"], "elapsed_s": round(time.time() - t0, 1)}
    return {"model": MODEL, "elapsed_s": round(time.time() - t0, 1), "answers": data.get("answers", data)}


def main():
    results = {}
    only = sys.argv[1:] or list(QUERIES)
    for name in only:
        if name not in QUERIES:
            continue
        print("asking", name, flush=True)
        try:
            results[name] = ask(name, QUERIES[name])
        except Exception as e:
            results[name] = {"error": str(e)}
        print("  ->", "error" if "error" in results[name] else "ok %ss" % results[name].get("elapsed_s"), flush=True)
    prior = {}
    if os.path.exists(OUT):
        try:
            prior = json.load(io.open(OUT, encoding="utf-8"))
        except Exception:
            prior = {}
    prior.update(results)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(prior, f, indent=2, ensure_ascii=False)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
