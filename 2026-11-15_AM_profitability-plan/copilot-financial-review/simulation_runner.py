"""Opt-in, offline historical portfolio research; never execution authority."""

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path


SYMBOLS = ("FZROX", "FXAIX", "VTSAX", "SPY", "VTI", "BND", "SGOV")
CAPITAL = 100000.0


@dataclass
class MarketData:
    dates: list[date]
    adjusted: dict[str, list[float]]
    raw: dict[str, list[float]]


@dataclass
class NavPoint:
    date: date
    nav: float
    cash: float
    cost: float
    turnover: float
    weights: dict[str, float]


def validate_market(market: MarketData) -> None:
    if len(market.dates) < 2 or market.dates != sorted(set(market.dates)):
        raise ValueError("Need at least two strictly increasing unique session dates")
    if not market.adjusted or set(market.adjusted) != set(market.raw):
        raise ValueError("Adjusted and raw price universes must be identical and nonempty")
    for kind, mapping in (("adjusted", market.adjusted), ("raw", market.raw)):
        for symbol, values in mapping.items():
            if len(values) != len(market.dates):
                raise ValueError(f"{kind} {symbol}: session/price length mismatch")
            for index, value in enumerate(values):
                if (isinstance(value, bool) or not isinstance(value, (int, float))
                        or not math.isfinite(value) or value <= 0):
                    raise ValueError(f"{kind} {symbol} {market.dates[index]}: invalid price")


def load_market(path: Path) -> MarketData:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        symbols = [field[:-4] for field in fields if field.endswith("_adj")]
        if not symbols or "date" not in fields:
            raise ValueError("CSV needs date and matching SYMBOL_adj/SYMBOL_close fields")
        if any(f"{symbol}_close" not in fields for symbol in symbols):
            raise ValueError("Raw-close reference columns are required")
        dates, adjusted, raw = [], {s: [] for s in symbols}, {s: [] for s in symbols}
        for row in reader:
            dates.append(date.fromisoformat(row["date"]))
            for symbol in symbols:
                adjusted[symbol].append(float(row[f"{symbol}_adj"]))
                raw[symbol].append(float(row[f"{symbol}_close"]))
    market = MarketData(dates, adjusted, raw)
    validate_market(market)
    return market


def prepare_market(cache: Path, output: Path) -> None:
    dates, adjusted, raw, sources = [], {}, {}, {}
    for symbol in SYMBOLS:
        path = cache / f"yahoo-{symbol}.json"
        data = path.read_bytes()
        chart = json.loads(data)["chart"]
        if chart.get("error") is not None or len(chart["result"]) != 1:
            raise ValueError(f"{symbol}: Yahoo response is not a single successful result")
        result = chart["result"][0]
        if result["meta"]["symbol"] != symbol:
            raise ValueError(f"{symbol}: instrument identity mismatch")
        observed = [
            datetime.fromtimestamp(t, timezone.utc).date() for t in result["timestamp"]
        ]
        if dates and observed != dates:
            raise ValueError(f"{symbol}: calendar differs; no silent intersection/forward fill")
        dates = observed
        adjusted[symbol] = result["indicators"]["adjclose"][0]["adjclose"]
        raw[symbol] = result["indicators"]["quote"][0]["close"]
        sources[symbol] = {
            "response_sha256": hashlib.sha256(data).hexdigest(),
            "public_feed": f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
        }
    market = MarketData(dates, adjusted, raw)
    validate_market(market)
    with output.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["date"] + [
            column for s in SYMBOLS for column in (f"{s}_adj", f"{s}_close")
        ])
        for index, day in enumerate(dates):
            writer.writerow([day.isoformat()] + [
                value for s in SYMBOLS for value in (adjusted[s][index], raw[s][index])
            ])
    manifest = {
        "source": "Retained public Yahoo daily responses, one vendor, not verified fills",
        "dates": [dates[0].isoformat(), dates[-1].isoformat()],
        "rows": len(dates), "symbols": sources,
        "derived_csv_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "exclusions": "None; missing/invalid prices or calendars fail rather than get filled",
    }
    output.with_suffix(".sources.json").write_text(json.dumps(manifest, indent=2) + "\n")


def month_ends(market: MarketData) -> list[int]:
    return [i for i in range(len(market.dates) - 1)
            if market.dates[i].month != market.dates[i + 1].month
            or market.dates[i].year != market.dates[i + 1].year]


def trend_targets(market: MarketData, lookback: int = 10) -> dict[int, dict[str, float]]:
    validate_market(market)
    if lookback < 2 or not {"SPY", "SGOV"}.issubset(market.adjusted):
        raise ValueError("Trend needs SPY/SGOV and at least two monthly observations")
    ends = month_ends(market)
    targets = {}
    for count in range(lookback - 1, len(ends)):
        signal = ends[count]
        history = [market.adjusted["SPY"][i]
                   for i in ends[count - lookback + 1:count + 1]]
        symbol = "SPY" if history[-1] > statistics.fmean(history) else "SGOV"
        targets[signal + 1] = {symbol: 1.0}
    if not targets:
        raise ValueError("Insufficient complete month ends; no invented initial target")
    return targets


def run_book(market: MarketData, targets: dict[int, dict[str, float]],
             rate: float) -> list[NavPoint]:
    validate_market(market)
    if not targets or not math.isfinite(rate) or not 0 <= rate < 0.1:
        raise ValueError("Need explicit targets and finite nonnegative transaction rate<10%")
    for index, weights in targets.items():
        if not 0 <= index < len(market.dates):
            raise ValueError("Target outside available calendar")
        if any(s not in market.adjusted for s in weights):
            raise ValueError("Target instrument missing from market data")
        if any(not math.isfinite(w) or w < 0 for w in weights.values()):
            raise ValueError("Weights must be finite and nonnegative")
        if math.fsum(weights.values()) > 1:
            raise ValueError("No leverage or overweight targets")
    start = min(targets)
    cash, positions, rows = CAPITAL, {}, []
    for index in range(start, len(market.dates)):
        if index > start:
            positions = {s: value * market.adjusted[s][index] / market.adjusted[s][index - 1]
                         for s, value in positions.items()}
        nav = cash + math.fsum(positions.values())
        cost, turnover = 0.0, 0.0
        target = {} if index == len(market.dates) - 1 else targets.get(index)
        if target is not None:
            universe = set(positions) | set(target)
            # Fees are funded from the account; solve against post-fee target notionals.
            for _ in range(40):
                traded = math.fsum(abs(target.get(s, 0.0) * (nav - cost)
                                       - positions.get(s, 0.0)) for s in universe)
                updated = rate * traded
                if math.isclose(updated, cost, rel_tol=1e-12, abs_tol=1e-9):
                    cost = updated
                    break
                cost = updated
            else:
                raise ValueError("Transaction-fee fixed point did not converge")
            turnover = traded / nav
            nav -= cost
            positions = {s: nav * w for s, w in target.items() if w > 0}
            cash = nav * (1 - math.fsum(target.values()))
        weights = {s: value / nav for s, value in positions.items()}
        rows.append(NavPoint(market.dates[index], nav, cash, cost, turnover, weights))
    return rows


def daily_returns(rows: list[NavPoint]) -> list[float]:
    previous, values = CAPITAL, []
    for row in rows:
        values.append(row.nav / previous - 1)
        previous = row.nav
    return values


def regular_returns(rows: list[NavPoint]) -> list[float]:
    if len(rows) < 2:
        raise ValueError("Boundary separation needs multiple account observations")
    previous, values = rows[0].nav, []
    for index in range(1, len(rows)):
        row = rows[index]
        gross = row.nav + row.cost if index == len(rows) - 1 else row.nav
        values.append(gross / previous - 1)
        previous = row.nav
    return values


def quantile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def metrics(rows: list[NavPoint], cash_returns: list[float]) -> dict:
    values = daily_returns(rows)
    if len(values) != len(cash_returns) or len(values) < 2:
        raise ValueError("Risk metrics need aligned cash returns and multiple observations")
    days = (rows[-1].date - rows[0].date).days
    if days <= 0:
        raise ValueError("Calendar CAGR needs positive elapsed days")
    excess = [r - c for r, c in zip(values, cash_returns)]
    sigma = statistics.stdev(excess)
    peak, drawdown, longest, underwater = CAPITAL, 0.0, 0, 0
    for row in rows:
        peak = max(peak, row.nav)
        drawdown = max(drawdown, 1 - row.nav / peak)
        underwater = underwater + 1 if row.nav < peak else 0
        longest = max(longest, underwater)
    tail_n = max(1, math.ceil(0.025 * len(values)))
    return {
        "start": rows[0].date.isoformat(), "end": rows[-1].date.isoformat(),
        "account_observations": len(values), "initial_usd": CAPITAL,
        "final_usd": rows[-1].nav,
        "total_return_pct": (rows[-1].nav / CAPITAL - 1) * 100,
        "cagr_pct": ((rows[-1].nav / CAPITAL) ** (365.25 / days) - 1) * 100,
        "volatility_pct": statistics.stdev(values) * math.sqrt(252) * 100,
        "excess_sharpe_vs_sgov": statistics.fmean(excess) / sigma * math.sqrt(252)
        if sigma else None,
        "mdd_loss_pct": drawdown * 100,
        "max_underwater_observed_sessions": longest,
        "daily_es97_5_loss_pct": -statistics.fmean(sorted(values)[:tail_n]) * 100,
        "es_tail_observations": tail_n, "cost_usd": math.fsum(r.cost for r in rows),
        "dollar_turnover_fraction_sum": math.fsum(r.turnover for r in rows),
    }


def joint_scenarios(values: list[float], spy: list[float], cash: list[float],
                    block: int, horizon: int, paths: int, seed: int, *,
                    entry_factors: tuple[float, ...] = (1., 1., 1.),
                    exit_factors: tuple[float, ...] = (1., 1., 1.)) -> dict:
    if (len(values) != len(spy) or len(values) != len(cash) or not values
            or min(block, horizon, paths) <= 0):
        raise ValueError("Scenarios require aligned nonempty series and positive dimensions")
    if any(not math.isfinite(r) or r <= -1 for seq in (values, spy, cash) for r in seq):
        raise ValueError("Invalid scenario return")
    if (len(entry_factors) != 3 or len(exit_factors) != 3
            or any(not math.isfinite(f) or not 0 < f <= 1
                   for f in entry_factors + exit_factors)):
        raise ValueError("Each account needs finite entry/exit cost factors in(0,1]")
    rng, profits, beats, beats_cash = random.Random(seed), 0, 0, 0
    wealths, losses, mean_excess = [], [], []
    for _ in range(paths):
        wealth, benchmark, ballast, peak, difference = 1., 1., 1., 1., 0.
        loss = 1 - entry_factors[0]
        elapsed = 0
        while elapsed < horizon:
            start = rng.randrange(len(values))
            for offset in range(min(block, horizon - elapsed)):
                index = (start + offset) % len(values)
                step = elapsed + offset
                vr, sr, cr = values[index], spy[index], cash[index]
                if step == 0:
                    vr = (1 + vr) * entry_factors[0] - 1
                    sr = (1 + sr) * entry_factors[1] - 1
                    cr = (1 + cr) * entry_factors[2] - 1
                if step == horizon - 1:
                    vr = (1 + vr) * exit_factors[0] - 1
                    sr = (1 + sr) * exit_factors[1] - 1
                    cr = (1 + cr) * exit_factors[2] - 1
                wealth *= 1 + vr
                benchmark *= 1 + sr
                ballast *= 1 + cr
                peak = max(peak, wealth)
                loss = max(loss, 1 - wealth / peak)
                difference += vr - sr
            elapsed += min(block, horizon - elapsed)
        profits += wealth > 1
        beats += wealth > benchmark + 1e-12
        beats_cash += wealth > ballast + 1e-12
        wealths.append(wealth)
        losses.append(loss)
        mean_excess.append(difference / horizon * 252 * 100)
    return {
        "block_sessions": block, "horizon_sessions": horizon, "paths": paths,
        "fraction_positive_wealth": profits / paths,
        "fraction_beating_spy": beats / paths, "fraction_beating_cash": beats_cash / paths,
        "wealth_multiple_5_50_95": [quantile(wealths, q) for q in (.05, .5, .95)],
        "mdd_loss_pct_50_95": [quantile(losses, q) * 100 for q in (.5, .95)],
        "excess_annualized_ci_95": [quantile(mean_excess, q) for q in (.025, .975)],
        "entry_cost_factors": entry_factors, "exit_cost_factors": exit_factors,
        "boundary_cost_method": "Remove historical boundary fees; apply once at each path endpoint",
        "scope": "Conditional historical block-resampling, NOT calibrated future probability",
    }


def execute(input_path: Path, output: Path) -> None:
    market = load_market(input_path)
    if set(market.adjusted) != set(SYMBOLS):
        raise ValueError("Frozen protocol requires exactly seven instruments")
    targets = trend_targets(market)
    start = min(targets)
    reports, curves = {}, {}
    for bps in (5, 20):
        rate = bps / 10000
        all_books = {f"full_{s}": run_book(market, {0: {s: 1.0}}, rate) for s in SYMBOLS}
        same = {f"matched_{s}": run_book(market, {start: {s: 1.0}}, rate)
                for s in ("SPY", "FXAIX", "SGOV")}
        same["trend"] = run_book(market, targets, rate)
        exposure = statistics.fmean(
            p.weights.get("SPY", 0.0) for p in same["trend"][:-1]
        )
        mix = {i: {"SPY": exposure, "SGOV": 1 - exposure}
               for i in targets}
        same["expost_exposure_control"] = run_book(market, mix, rate)
        full_cash, cash = daily_returns(all_books["full_SGOV"]), daily_returns(same["matched_SGOV"])
        report = {name: metrics(rows, full_cash) for name, rows in all_books.items()}
        report.update({name: metrics(rows, cash) for name, rows in same.items()})
        trend, spy = daily_returns(same["trend"]), daily_returns(same["matched_SPY"])
        differences = [a - b for a, b in zip(trend, spy)]
        sigma = statistics.stdev(differences)
        report["comparisons"] = {
            "spy_cagr_excess_pp": report["trend"]["cagr_pct"] - report["matched_SPY"]["cagr_pct"],
            "information_ratio_vs_spy": statistics.fmean(differences) / sigma * math.sqrt(252)
            if sigma else None,
            "mean_spy_exposure": exposure,
            "absolute_backtest_profit": report["trend"]["total_return_pct"] > 0,
            "raw_spy_outperformance": report["trend"]["cagr_pct"] > report["matched_SPY"]["cagr_pct"],
            "risk_diagnostic_improvement": (
                report["trend"]["mdd_loss_pct"] < report["expost_exposure_control"]["mdd_loss_pct"]
                and report["trend"]["excess_sharpe_vs_sgov"] is not None
                and report["expost_exposure_control"]["excess_sharpe_vs_sgov"] is not None
                and report["trend"]["excess_sharpe_vs_sgov"]
                > report["expost_exposure_control"]["excess_sharpe_vs_sgov"]
            ),
        }
        splits = {}
        for label, include in (("before_2025", lambda d: d < date(2025, 1, 1)),
                               ("from_2025", lambda d: d >= date(2025, 1, 1))):
            selected = [diff for row, diff in zip(same["trend"], differences) if include(row.date)]
            if len(selected) < 2:
                raise ValueError("Frozen chronological segment lacks observations")
            splits[label] = {"n": len(selected), "annualized_mean_spy_excess_pct":
                             statistics.fmean(selected) * 252 * 100}
        report["chronological_splits"] = splits
        regular_spy = regular_returns(same["matched_SPY"])
        regular_cash = regular_returns(same["matched_SGOV"])
        boundary_books = [same["trend"], same["matched_SPY"], same["matched_SGOV"]]
        entry_factors = tuple(rows[0].nav / CAPITAL for rows in boundary_books)
        exit_factors = tuple(rows[-1].nav / (rows[-1].nav + rows[-1].cost)
                             for rows in boundary_books)
        cis = [joint_scenarios(regular_returns(same["trend"]), regular_spy, regular_cash,
                              block, len(regular_spy), 1000, 20261115,
                              entry_factors=entry_factors, exit_factors=exit_factors)
               for block in (21, 60, 120)]
        report["paired_excess_diagnostics"] = cis
        report["allocation_screen"] = (
            report["trend"]["excess_sharpe_vs_sgov"] is not None
            and report["trend"]["excess_sharpe_vs_sgov"] >= .8
            and report["trend"]["mdd_loss_pct"] <= 20
            and all(r["annualized_mean_spy_excess_pct"] > 0 for r in splits.values())
            and all(r["excess_annualized_ci_95"][0] > 0 for r in cis)
        )
        if bps == 5:
            report["holding_scenarios"] = {
                name: [joint_scenarios(
                    regular_returns(rows), regular_spy, regular_cash, block, horizon,
                    1000, 20261115,
                    entry_factors=(rows[0].nav / CAPITAL,) + entry_factors[1:],
                    exit_factors=(rows[-1].nav / (rows[-1].nav + rows[-1].cost),)
                    + exit_factors[1:])
                       for block in (21, 60, 120) for horizon in (21, 63, 252, 756)]
                for name, rows in (("FXAIX", same["matched_FXAIX"]), ("trend", same["trend"]))
            }
        reports[f"{bps}bps_per_side"] = report
        curves.update({f"{bps}bps_{name}": rows for name, rows in {**all_books, **same}.items()})
    result = {
        "protocol": "08_SIMULATION_PLAN.md", "preregistration": "SIMULATION_PREREGISTRATION.json",
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "model": "Daily adjusted-total-return units, next-close lag, funded fractional book",
        "limits": "One vendor; historical exposed data; no verified real fills/PIT eligibility/tax/FX; no pristine OOS",
        "daily_return_scope": "Includes initial-cost-only observation and final liquidation costs",
        "research_only": True, "capital_eligible": False, "trade_admission": "UNTESTED",
        "joint_shocks_60_30_10_pct": [-24.0, -36.0], "cost_cases": reports,
    }
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    nav_path = output.with_name(output.stem + "_nav.csv")
    with nav_path.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["book", "date", "nav_usd", "cash_usd", "cost_usd",
                         "turnover", "weights_post_close"])
        for name, rows in curves.items():
            for row in rows:
                writer.writerow([name, row.date.isoformat(), row.nav, row.cash, row.cost,
                                 row.turnover, json.dumps(row.weights, sort_keys=True)])
    for bps, report in reports.items():
        print(bps, "trend CAGR", round(report["trend"]["cagr_pct"], 3),
              "SPY CAGR", round(report["matched_SPY"]["cagr_pct"], 3),
              "screen", report["allocation_screen"], "capital_eligible", False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Freeze retained public cache into audited CSV")
    prepare.add_argument("--cache-dir", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    run = commands.add_parser("run", help="Execute the frozen offline research protocol")
    run.add_argument("--input", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare_market(args.cache_dir, args.output)
    else:
        execute(args.input, args.output)


if __name__ == "__main__":
    main()
