#!/usr/bin/env python3
"""
Deterministic backtest/simulation harness for 2026-11-15_AM_profitability-plan.
Uses only stdlib. No external data, no network. Results are MODEL-BASED
(assumption-driven) simulations, not proof of live profitability.
"""
import csv
import json
import math
import random
import statistics
from datetime import datetime, timezone

random.seed(20261115)

TRADING_DAYS = 252
YEARS = 10
N_PATHS = 2000
RF = 0.03  # cash/T-bill hurdle (annual)


def annualize_mean(daily_returns):
    return (1 + statistics.mean(daily_returns)) ** TRADING_DAYS - 1


def annualize_vol(daily_returns):
    if len(daily_returns) < 2:
        return 0.0
    return statistics.pstdev(daily_returns) * math.sqrt(TRADING_DAYS)


def sharpe(daily_returns, rf=RF):
    vol = annualize_vol(daily_returns)
    if vol == 0:
        return 0.0
    return (annualize_mean(daily_returns) - rf) / vol


def max_drawdown(equity_curve):
    peak = equity_curve[0]
    mdd = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        dd = (v / peak) - 1.0
        if dd < mdd:
            mdd = dd
    return mdd


def cagr(equity_curve, years=YEARS):
    if equity_curve[0] <= 0:
        return 0.0
    return (equity_curve[-1] / equity_curve[0]) ** (1 / years) - 1


def simulate_gbm_paths(mu_ann, sigma_ann, years, n_paths, cost_ann=0.0):
    days = years * TRADING_DAYS
    dt = 1 / TRADING_DAYS
    mu = mu_ann - cost_ann
    paths = []
    all_daily = []
    for _ in range(n_paths):
        eq = [1.0]
        dailies = []
        for _ in range(days):
            z = random.gauss(0, 1)
            ret = (mu - 0.5 * sigma_ann ** 2) * dt + sigma_ann * math.sqrt(dt) * z
            eq.append(eq[-1] * (1 + ret))
            dailies.append(ret)
        paths.append(eq)
        all_daily.append(dailies)
    return paths, all_daily


def simulate_6040(reb_days=21, eq_mu=0.09, eq_sigma=0.15, bd_mu=0.04, bd_sigma=0.05,
                  corr=0.1, years=YEARS, n_paths=N_PATHS, cost_ann=0.0005):
    days = years * TRADING_DAYS
    dt = 1 / TRADING_DAYS
    paths = []
    all_daily = []
    for _ in range(n_paths):
        eq = [1.0]
        w_eq, w_bd = 0.6, 0.4
        port_eq = 0.6
        port_bd = 0.4
        dailies = []
        for i in range(days):
            z1 = random.gauss(0, 1)
            z2 = corr * z1 + math.sqrt(max(1 - corr ** 2, 0)) * random.gauss(0, 1)
            r_eq = (eq_mu - 0.5 * eq_sigma ** 2) * dt + eq_sigma * math.sqrt(dt) * z1
            r_bd = (bd_mu - 0.5 * bd_sigma ** 2) * dt + bd_sigma * math.sqrt(dt) * z2
            port_eq *= (1 + r_eq)
            port_bd *= (1 + r_bd)
            total = port_eq + port_bd
            # daily cost drag
            total *= (1 - cost_ann / TRADING_DAYS)
            ret = total / eq[-1] - 1
            eq.append(total)
            dailies.append(ret)
            if (i + 1) % reb_days == 0:
                port_eq = total * w_eq
                port_bd = total * w_bd
        paths.append(eq)
        all_daily.append(dailies)
    return paths, all_daily


def summarize(paths, all_daily, name):
    cagrs = [cagr(p) for p in paths]
    mdds = [max_drawdown(p) for p in paths]
    sharpes = [sharpe(d) for d in all_daily]
    end_pos = sum(1 for p in paths if p[-1] > p[0]) / len(paths)
    beat_cash = sum(1 for p in paths if cagr(p) > RF) / len(paths)
    return {
        "strategy": name,
        "paths": len(paths),
        "horizon_years": YEARS,
        "median_cagr": statistics.median(cagrs),
        "p10_cagr": statistics.quantiles(cagrs, n=10)[0],
        "p90_cagr": statistics.quantiles(cagrs, n=10)[-1],
        "median_sharpe": statistics.median(sharpes),
        "median_mdd": statistics.median(mdds),
        "p90_mdd_worst": statistics.quantiles(mdds, n=10)[0],  # most negative
        "prob_positive": end_pos,
        "prob_beat_cash_3pct": beat_cash,
    }


def simulate_dual_momentum_toy(years=20, n_paths=1000):
    """
    Monthly toy: risky asset alternates bull/bear regimes; defensive asset stable.
    Absolute momentum: hold risky if 12m return > 0 else defensive; else cash-like.
    Demonstrates drawdown reduction in trend/crash regimes (model-based).
    """
    months = years * 12
    paths_bh = []
    paths_dm = []
    for _ in range(n_paths):
        # regime-switching risky returns
        risky = [100.0]
        defensive = [100.0]
        bh = [1.0]
        dm = [1.0]
        state = 1  # bull
        risky_rets = []
        def_rets = []
        for m in range(months):
            # regime persistence
            if state == 1 and random.random() < 0.04:
                state = -1
            elif state == -1 and random.random() < 0.20:
                state = 1
            if state == 1:
                r_risky = random.gauss(0.012, 0.045)
            else:
                r_risky = random.gauss(-0.018, 0.055)
            r_def = random.gauss(0.003, 0.012)
            risky_rets.append(r_risky)
            def_rets.append(r_def)
            risky.append(risky[-1] * (1 + r_risky))
            defensive.append(defensive[-1] * (1 + r_def))
            # buy & hold risky
            bh.append(bh[-1] * (1 + r_risky - 0.0001))
            # dual/absolute momentum (12m lookback)
            if m >= 12:
                mom12 = risky[-1] / risky[-13] - 1
            else:
                mom12 = risky[-1] / risky[0] - 1
            if mom12 > 0:
                dm_ret = r_risky
            else:
                dm_ret = r_def  # absolute momentum to defensive
            dm.append(dm[-1] * (1 + dm_ret - 0.0002))  # slightly higher turnover cost
        paths_bh.append(bh)
        paths_dm.append(dm)
    def mdd_curve(c):
        peak=c[0]; m=0.0
        for v in c:
            peak=max(peak,v); m=min(m,v/peak-1)
        return m
    def cagr_m(c, yrs):
        return (c[-1]/c[0])**(1/yrs)-1
    bh_c = [cagr_m(p, years) for p in paths_bh]
    dm_c = [cagr_m(p, years) for p in paths_dm]
    bh_m = [mdd_curve(p) for p in paths_bh]
    dm_m = [mdd_curve(p) for p in paths_dm]
    return {
        "toy": "regime-switching risky + defensive, monthly, 12m absolute momentum",
        "paths": n_paths, "years": years,
        "buy_hold_risky_median_cagr": statistics.median(bh_c),
        "buy_hold_risky_median_mdd": statistics.median(bh_m),
        "dual_momentum_median_cagr": statistics.median(dm_c),
        "dual_momentum_median_mdd": statistics.median(dm_m),
        "dm_mdd_improved_share": sum(1 for a,b in zip(dm_m,bh_m) if a>b)/n_paths,
        "dm_positive_share": sum(1 for c in dm_c if c>0)/n_paths,
    }


def net_of_cost_sensitivity():
    """Show gross edge vs round-trip cost per trade impact on expectancy/PF-like ratio."""
    # assume trade distribution: win +1R, loss -1R before costs, R=1%
    R = 0.01
    scenarios = []
    for gross_wr in [0.45, 0.50, 0.52, 0.55]:
        for gross_pf in [0.9, 1.1, 1.3, 1.5]:
            # derive avg win/loss ratio from pf and wr: pf = (wr*W)/((1-wr)*L)
            L = R
            W = gross_pf * (1-gross_wr) * L / gross_wr if gross_wr>0 else 0
            for rt_cost_bps in [5, 10, 20, 30, 50]:
                cost = rt_cost_bps / 10000.0
                exp_gross = gross_wr * W - (1-gross_wr) * L
                exp_net = gross_wr * (W - cost) - (1-gross_wr) * (L + cost)
                gross_win_sum = gross_wr * W
                gross_loss_sum = (1-gross_wr) * L
                net_win_sum = gross_wr * max(W - cost, 0)
                net_loss_sum = (1-gross_wr) * (L + cost)
                pf_net = (net_win_sum / net_loss_sum) if net_loss_sum>0 else 0
                scenarios.append({
                    "gross_wr": gross_wr, "gross_pf": round(gross_pf,2), "rt_cost_bps": rt_cost_bps,
                    "expectancy_gross_R": round(exp_gross/R,4),
                    "expectancy_net_R": round(exp_net/R,4),
                    "pf_net": round(pf_net,4),
                    "net_positive": exp_net > 0
                })
    # summarize key rows
    return scenarios


def main():
    out_dir = "/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/childlike-airport/2026-11-15_AM_profitability-plan/childlike-airport/09_backtest_simulations"
    results = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "assumptions": {
        "paths": N_PATHS, "horizon_years": YEARS, "rf_cash": RF,
        "equity_gbm": {"mu": 0.09, "sigma": 0.15, "cost": 0.0005},
        "bonds_gbm_proxy": {"mu": 0.04, "sigma": 0.05},
        "blend_60_40": {"rebalance_days": 21, "corr_eq_bd": 0.1, "annual_cost": 0.0005},
        "taa_toy": "regime-switching risky/defensive, monthly, 12m absolute momentum",
        "note": "MODEL-BASED simulations (GBM/toy). Not live proof; no guarantee future regimes match."
    }}

    # 1) Equity buy & hold (SPY-like proxy)
    eq_paths, eq_d = simulate_gbm_paths(0.09, 0.15, YEARS, N_PATHS, cost_ann=0.0005)
    results["equity_buy_hold_proxy"] = summarize(eq_paths, eq_d, "Equity B&H proxy (mu 9%, vol 15%, 5bps cost)")
    # 2) 60/40
    b_paths, b_d = simulate_6040()
    results["balanced_60_40"] = summarize(b_paths, b_d, "60/40 equity/bonds rebalance monthly (5bps cost)")
    # 3) Bonds/cash-like defensive
    bd_paths, bd_d = simulate_gbm_paths(0.04, 0.05, YEARS, N_PATHS, cost_ann=0.0003)
    results["bonds_defensive_proxy"] = summarize(bd_paths, bd_d, "Bonds defensive proxy (mu 4%, vol 5%)")
    # 4) Dual momentum toy
    results["dual_momentum_toy"] = simulate_dual_momentum_toy()
    # 5) Cost sensitivity
    sens = net_of_cost_sensitivity()
    results["cost_sensitivity_rows"] = len(sens)
    # save key sensitivity subset
    key = [r for r in sens if r["gross_wr"] in (0.45,0.50,0.55) and r["gross_pf"] in (1.0,1.1,1.3,1.5) and r["rt_cost_bps"] in (5,10,20,30)]
    results["cost_sensitivity_key"] = key
    # aggregates
    kills = [r for r in sens if r["gross_pf"]<=1.1 and r["rt_cost_bps"]>=10 and not r["net_positive"]]
    results["cost_sensitivity_summary"] = {
        "total_scenarios": len(sens),
        "scenarios_net_negative": sum(1 for r in sens if not r["net_positive"]),
        "example_marginal_edge_killed_by_costs": len(kills),
        "finding": "Marginal gross edges (PF<=1.1 or WR<=50%) frequently turn net-negative at 10-30bps RT costs."
    }

    # relative comparisons
    eq_m = results["equity_buy_hold_proxy"]["median_cagr"]
    b_m = results["balanced_60_40"]["median_cagr"]
    results["comparisons"] = {
        "balanced_vs_equity_median_cagr_diff": b_m - eq_m,
        "balanced_vs_equity_median_mdd_improvement": results["balanced_60_40"]["median_mdd"] - results["equity_buy_hold_proxy"]["median_mdd"],
        "note": "Balanced typically trades some CAGR for materially lower drawdown (risk-adjusted suitability depends on objective)."
    }

    with open(out_dir + "/simulation_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # CSV summary
    rows = [results["equity_buy_hold_proxy"], results["balanced_60_40"], results["bonds_defensive_proxy"]]
    with open(out_dir + "/simulation_summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    # cost sensitivity csv
    with open(out_dir + "/cost_sensitivity.csv", "w", newline="") as f:
        if key:
            w = csv.DictWriter(f, fieldnames=list(key[0].keys()))
            w.writeheader(); w.writerows(key)

    # markdown report
    def pct(x): return f"{x*100:.2f}%"
    md = []
    md.append("# 09 — Backtest/Simulation Plan, Execution, and Results\n")
    md.append(f"**Generated (UTC):** {results['generated_at_utc']}  ")
    md.append("**Type:** model-based simulations (GBM + regime-switching toy), deterministic seed `20261115`.  ")
    md.append("**Claim level:** demonstrates *plausible* backtest/simulation behavior under stated assumptions; **not** proof of live profitability or future performance.\n")
    md.append("## 1. Plan (created & executed)\n")
    md.append("| # | Simulation | Purpose | Output |")
    md.append("|---|---|---|---|")
    md.append("| 1 | Equity buy-and-hold proxy (SPY-like) | Benchmark / beta path | CAGR, Sharpe, MDD, P(positive), P(beat cash) |")
    md.append("| 2 | 60/40 balanced (monthly rebalance, low cost) | Risk-managed core allocation path | same metrics + vs equity |")
    md.append("| 3 | Bonds defensive proxy | Ballast behavior | same metrics |")
    md.append("| 4 | Dual-momentum toy (regime-switching) | Show drawdown control logic vs B&H in trend/crash regimes | median CAGR/MDD, MDD-improved share |")
    md.append("| 5 | Net-of-cost sensitivity grid | Prove marginal gross edges die after realistic costs | expectancy/PF_net by WR/PF/cost bps |")
    md.append("\n**Execution:** `python3 09_backtest_simulations/run_simulations.py` (stdlib only). Artifacts: `simulation_results.json`, `simulation_summary.csv`, `cost_sensitivity.csv`.\n")
    md.append("## 2. Core results ({} paths, {}y horizon, RF={}%)\n".format(N_PATHS, YEARS, int(RF*100)))
    md.append("| Strategy | Median CAGR | P10/P90 CAGR | Median Sharpe | Median MDD | Worst-decile MDD | P(>0) | P(beat cash 3%) |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        md.append(f"| {r['strategy']} | {pct(r['median_cagr'])} | {pct(r['p10_cagr'])} / {pct(r['p90_cagr'])} | {r['median_sharpe']:.2f} | {pct(r['median_mdd'])} | {pct(r['p90_mdd_worst'])} | {pct(r['prob_positive'])} | {pct(r['prob_beat_cash_3pct'])} |")
    dm = results['dual_momentum_toy']
    md.append("\n### 2b. Dual-momentum toy (model regime test)\n")
    md.append(f"- Buy&Hold risky median CAGR {pct(dm['buy_hold_risky_median_cagr'])}, median MDD {pct(dm['buy_hold_risky_median_mdd'])}")
    md.append(f"- Dual-momentum median CAGR {pct(dm['dual_momentum_median_cagr'])}, median MDD {pct(dm['dual_momentum_median_mdd'])}")
    md.append(f"- MDD improved vs B&H in {pct(dm['dm_mdd_improved_share'])} of paths; positive-CAGR share {pct(dm['dm_positive_share'])}")
    md.append("\n## 3. Net-of-cost sensitivity (active strategies)\n")
    cs = results['cost_sensitivity_summary']
    md.append(f"- Scenarios tested: {cs['total_scenarios']}; net-negative: {cs['scenarios_net_negative']}. {cs['finding']}")
    md.append("- Example (gross PF 1.10, WR 50%, 20bps RT): expectancy turns negative / PF_net < 1 in grid — **costs erase marginal edges**.\n")
    md.append("| Gross WR | Gross PF | RT cost (bps) | Exp gross (R) | Exp net (R) | PF_net | Net>0 |")
    md.append("|---:|---:|---:|---:|---:|---:|:---:|")
    for r in key[:24]:
        md.append(f"| {r['gross_wr']:.2f} | {r['gross_pf']:.2f} | {r['rt_cost_bps']} | {r['expectancy_gross_R']:.3f} | {r['expectancy_net_R']:.3f} | {r['pf_net']:.3f} | {'Y' if r['net_positive'] else 'N'} |")
    md.append("\n## 4. Interpretation (honest)\n")
    md.append("- **Core path supported in simulation:** low-cost diversified 60/40 shows high P(>0) and P(beat cash) with substantially smaller median/worst-decile MDD than equity-only — consistent with a **risk-managed beta/ballast** approach (not prediction alpha).")
    md.append("- **TAA/absolute-momentum logic** can reduce drawdowns in trend/crash-like regimes in-model; real-world benefit depends on costs, whipsaw, and regime behavior (must be forward-validated vs buy-and-hold benchmark).")
    md.append("- **Active sleeves**: without verified gross edge and strict cost control, net expectancy is fragile. This reinforces: fix measurement/fills/costs, then demand net benchmark-relative proof.\n")
    md.append("## 5. What this does NOT prove\n")
    md.append("- No guarantee of live profitability, no validated alpha for repo strategies, no bypass of OOS/DSR/PBO/forward gates. Assumptions (mu/sigma/correlations/costs/regimes) may not match future markets. Outperforming SPY/buy-and-hold in reality remains an empirical question requiring forward, net, benchmark-relative evidence.\n")
    md.append("## 6. Next steps\n")
    md.append("- Run on **trusted, reconciled historical data** (canonical cohort) once measurement/QA is fixed; compare vs SPY total return net of costs.")
    md.append("- Apply forward-test tracking protocol (`10_forward_test_protocol/FORWARD_TEST_TRACKING_PROTOCOL.md`) with kill/hold rules.")
    with open(out_dir + "/SIMULATION_PLAN_AND_RESULTS.md", "w") as f:
        f.write("\n".join(md) + "\n")

    print("OK", out_dir)
    print(json.dumps({k: results[k] for k in ["equity_buy_hold_proxy","balanced_60_40","bonds_defensive_proxy","dual_momentum_toy","cost_sensitivity_summary"]}, indent=2))

if __name__ == "__main__":
    main()
