#!/usr/bin/env python3
"""
Baby bundle what-if analyzer.

Default behavior:
- Low budget ($200 per pick)
- Scenario sweep across:
  - 1 random pick from each active bundle
  - 1 random pick from top 3 bundles
  - 5 picks from top bundle
  - 1 random pick from top strategy
  - Long-only picks from top 3 bundles
- Hourly (1h) and daily (24h) checks

Use `--mode count` first to see recent pick volume.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

BUDGET_LEVELS = {
    "low": 200.0,
    "medium": 500.0,
    "high": 1000.0,
    "very_high": 2000.0,
    "extreme": 5000.0,
}

DEFAULT_DASHBOARD_PATH = Path("battleground/data/baby_strats_dashboard.json")
GIC_ANNUAL_RATE = 0.05
MUTUAL_FUND_ANNUAL_RATE = 0.08


@dataclass(frozen=True)
class Trade:
    strategy: str
    bundle: str
    direction: str
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: Optional[float]
    exit_price: Optional[float]
    take_profit: Optional[float]
    stop_loss: Optional[float]
    pnl_pct: float
    exit_reason: str
    status: str
    source: str
    symbol: str = "N/A"


@dataclass(frozen=True)
class ScenarioResult:
    key: str
    label: str
    selected: List[Trade]
    pool: List[Trade]
    notes: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="What-if analysis for baby bundle picks using latest battleground data."
    )
    parser.add_argument(
        "--mode",
        choices=["count", "analyze"],
        default="analyze",
        help="count = show recent pick counts, analyze = run investment scenarios.",
    )
    parser.add_argument(
        "--dashboard-path",
        default=str(DEFAULT_DASHBOARD_PATH),
        help="Path to battleground dashboard JSON.",
    )
    parser.add_argument(
        "--level",
        choices=sorted(BUDGET_LEVELS.keys()),
        default="low",
        help="Investment level; amount means USD per pick.",
    )
    parser.add_argument(
        "--amount-per-pick",
        type=float,
        default=None,
        help="Override USD amount per pick. If omitted, uses level mapping.",
    )
    parser.add_argument(
        "--scenario",
        choices=[
            "all",
            "random_per_bundle",
            "top3_bundles",
            "five_from_top_bundle",
            "top_strategy",
            "long_only_top3_bundles",
        ],
        default="all",
        help="Scenario to run (or all).",
    )
    parser.add_argument(
        "--check-windows",
        default="1,24",
        help="Comma-separated windows (hours) for summary checks. Default: 1,24",
    )
    parser.add_argument(
        "--detail-window",
        type=int,
        default=24,
        help="Window (hours) used for detailed trade-by-trade breakdown.",
    )
    parser.add_argument(
        "--min-trades",
        type=int,
        default=3,
        help="Minimum trades to include in top-bundle/top-strategy ranking.",
    )
    parser.add_argument(
        "--simulations",
        type=int,
        default=1000,
        help="Monte Carlo runs for probability-of-profit estimate.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic picks.",
    )
    parser.add_argument(
        "--page",
        type=int,
        default=1,
        help="Detail page number (for long trade breakdowns).",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=18,
        help="Lines per detail page.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output (summary only).",
    )
    return parser.parse_args()


def as_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_float_zero(value: Any) -> float:
    parsed = as_float(value, 0.0)
    return 0.0 if parsed is None else parsed


def parse_iso(value: Any) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def norm_direction(value: Any) -> str:
    if not value:
        return "UNKNOWN"
    text = str(value).strip().upper()
    if text in {"BUY", "LONG"}:
        return "LONG"
    if text in {"SELL", "SHORT"}:
        return "SHORT"
    return text


def pct(value: float) -> str:
    return f"{value:+.2f}%"


def usd(value: float) -> str:
    return f"${value:,.2f}"


def chunked(seq: Sequence[str], size: int) -> List[List[str]]:
    if size <= 0:
        return [list(seq)]
    return [list(seq[i : i + size]) for i in range(0, len(seq), size)]


def load_dashboard(path: Path) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    strategies = {
        row.get("name"): row
        for row in payload.get("strategies", [])
        if isinstance(row, dict) and row.get("name")
    }

    bundles: List[Dict[str, Any]] = []
    for section in payload.get("sections", []):
        if not isinstance(section, dict):
            continue
        candidates = section.get("bundles")
        if not isinstance(candidates, list):
            continue
        for bundle in candidates:
            if not isinstance(bundle, dict):
                continue
            name = bundle.get("name")
            strat_names = [
                x for x in (bundle.get("strategies") or []) if isinstance(x, str) and x
            ]
            if name and strat_names:
                bundles.append(
                    {
                        "name": name,
                        "strategies": strat_names,
                        "classification": bundle.get("classification") or {},
                        "backtest": bundle.get("backtest") or {},
                        "forward": bundle.get("forward") or {},
                    }
                )
    return strategies, bundles


def collect_trades(
    strategies: Dict[str, Dict[str, Any]],
    bundles: List[Dict[str, Any]],
) -> Tuple[List[Trade], List[Trade], Dict[str, List[Trade]]]:
    strategy_to_bundles: Dict[str, List[str]] = {}
    for bundle in bundles:
        bname = bundle["name"]
        for strat in bundle["strategies"]:
            strategy_to_bundles.setdefault(strat, []).append(bname)

    bundle_closed: List[Trade] = []
    bundle_live: List[Trade] = []
    strategy_closed: Dict[str, List[Trade]] = {}

    for strategy_name, row in strategies.items():
        bundle_names = strategy_to_bundles.get(strategy_name, [])

        for raw in row.get("forward_trades") or []:
            if not isinstance(raw, dict):
                continue
            entry_time = parse_iso(raw.get("entry_time"))
            if entry_time is None:
                continue
            base = Trade(
                strategy=strategy_name,
                bundle="UNBUNDLED",
                direction=norm_direction(raw.get("direction") or raw.get("side")),
                entry_time=entry_time,
                exit_time=parse_iso(raw.get("exit_time")),
                entry_price=as_float(raw.get("entry_price")),
                exit_price=as_float(raw.get("exit_price")),
                take_profit=as_float(raw.get("take_profit")),
                stop_loss=as_float(raw.get("stop_loss")),
                pnl_pct=as_float_zero(raw.get("pnl_pct")),
                exit_reason=str(raw.get("exit_reason") or "UNKNOWN"),
                status="CLOSED",
                source="forward_trades",
                symbol=str(raw.get("symbol") or "N/A"),
            )
            strategy_closed.setdefault(strategy_name, []).append(base)
            for bname in bundle_names:
                bundle_closed.append(replace(base, bundle=bname))

        for raw in row.get("forward_live_picks") or []:
            if not isinstance(raw, dict):
                continue
            entry_time = parse_iso(raw.get("generated_at") or raw.get("entry_time"))
            if entry_time is None:
                continue
            base = Trade(
                strategy=strategy_name,
                bundle="UNBUNDLED",
                direction=norm_direction(raw.get("side") or raw.get("direction")),
                entry_time=entry_time,
                exit_time=None,
                entry_price=as_float(raw.get("entry_price")),
                exit_price=None,
                take_profit=as_float(raw.get("take_profit")),
                stop_loss=as_float(raw.get("stop_loss")),
                pnl_pct=as_float_zero(raw.get("pnl_pct")),
                exit_reason="OPEN",
                status="OPEN",
                source="forward_live_picks",
                symbol=str(raw.get("symbol") or "N/A"),
            )
            for bname in bundle_names:
                bundle_live.append(replace(base, bundle=bname))

    return bundle_closed, bundle_live, strategy_closed


def latest_timestamp(
    bundle_closed: Sequence[Trade],
    bundle_live: Sequence[Trade],
    strategy_closed: Dict[str, List[Trade]],
) -> datetime:
    all_times: List[datetime] = []
    all_times.extend(t.entry_time for t in bundle_closed)
    all_times.extend(t.entry_time for t in bundle_live)
    for trades in strategy_closed.values():
        all_times.extend(t.entry_time for t in trades)
    return max(all_times) if all_times else datetime.now(tz=timezone.utc)


def filter_window(
    trades: Iterable[Trade],
    anchor: datetime,
    hours: int,
) -> List[Trade]:
    start = anchor - timedelta(hours=hours)
    return [t for t in trades if start <= t.entry_time <= anchor]


def key_trade(trade: Trade) -> Tuple[str, str, str, float]:
    return (
        trade.strategy,
        trade.entry_time.isoformat(),
        trade.direction,
        round(trade.entry_price or 0.0, 8),
    )


def trade_stats(trades: Sequence[Trade]) -> Dict[str, float]:
    if not trades:
        return {
            "count": 0.0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "expectancy": 0.0,
            "sum_pnl_pct": 0.0,
            "avg_pnl_pct": 0.0,
        }
    pnls = [t.pnl_pct for t in trades]
    wins = [p for p in pnls if p > 0]
    losses_abs = [abs(p) for p in pnls if p < 0]
    wr = (len(wins) / len(trades)) * 100.0
    avg_win = mean(wins) if wins else 0.0
    avg_loss = mean(losses_abs) if losses_abs else 0.0
    expectancy = (wr / 100.0) * avg_win - (1.0 - wr / 100.0) * avg_loss
    return {
        "count": float(len(trades)),
        "win_rate": wr,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": expectancy,
        "sum_pnl_pct": sum(pnls),
        "avg_pnl_pct": mean(pnls),
    }


def monte_carlo_prob_profit(
    pool: Sequence[Trade],
    picks_count: int,
    simulations: int,
    seed: int,
) -> Optional[float]:
    if not pool or picks_count <= 0 or simulations <= 0:
        return None
    rng = random.Random(seed)
    pnls = [t.pnl_pct for t in pool]
    profitable = 0
    for _ in range(simulations):
        total = 0.0
        for _ in range(picks_count):
            total += rng.choice(pnls)
        if total > 0.0:
            profitable += 1
    return 100.0 * profitable / simulations


def select_random_from_pool(pool: Sequence[Trade], count: int, rng: random.Random) -> List[Trade]:
    if count <= 0 or not pool:
        return []
    if len(pool) >= count:
        return rng.sample(list(pool), count)
    return [rng.choice(list(pool)) for _ in range(count)]


def build_bundle_pools(trades: Sequence[Trade]) -> Dict[str, List[Trade]]:
    out: Dict[str, List[Trade]] = {}
    for trade in trades:
        out.setdefault(trade.bundle, []).append(trade)
    return out


def rank_bundles(
    bundle_pools: Dict[str, List[Trade]],
    min_trades: int,
) -> List[Tuple[str, Dict[str, float]]]:
    ranked: List[Tuple[str, Dict[str, float]]] = []
    for bundle, trades in bundle_pools.items():
        stats = trade_stats(trades)
        if int(stats["count"]) < max(1, min_trades):
            continue
        ranked.append((bundle, stats))
    ranked.sort(
        key=lambda x: (x[1]["expectancy"], x[1]["avg_pnl_pct"], x[1]["win_rate"]),
        reverse=True,
    )
    return ranked


def rank_strategies(
    strategy_trades: Dict[str, List[Trade]],
    anchor: datetime,
    window_hours: int,
    min_trades: int,
) -> List[Tuple[str, Dict[str, float], List[Trade]]]:
    ranked: List[Tuple[str, Dict[str, float], List[Trade]]] = []
    for strategy, trades in strategy_trades.items():
        recent = filter_window(trades, anchor=anchor, hours=window_hours)
        stats = trade_stats(recent)
        if int(stats["count"]) < max(1, min_trades):
            continue
        ranked.append((strategy, stats, recent))
    ranked.sort(
        key=lambda x: (x[1]["expectancy"], x[1]["avg_pnl_pct"], x[1]["win_rate"]),
        reverse=True,
    )
    return ranked


def scenario_random_per_bundle(
    bundle_pools: Dict[str, List[Trade]],
    seed: int,
) -> ScenarioResult:
    rng = random.Random(seed)
    selected: List[Trade] = []
    pool: List[Trade] = []
    for bundle in sorted(bundle_pools.keys()):
        trades = bundle_pools[bundle]
        if not trades:
            continue
        selected.append(rng.choice(trades))
        pool.extend(trades)
    note = f"{len(selected)} picks (1 random pick per active bundle)."
    return ScenarioResult(
        key="random_per_bundle",
        label="1 random pick from each active bundle",
        selected=selected,
        pool=pool,
        notes=note,
    )


def scenario_top3_bundles(
    bundle_pools: Dict[str, List[Trade]],
    min_trades: int,
    seed: int,
) -> ScenarioResult:
    ranked = rank_bundles(bundle_pools, min_trades=min_trades)
    top3 = ranked[:3]
    rng = random.Random(seed + 11)
    selected: List[Trade] = []
    pool: List[Trade] = []
    for bundle, _ in top3:
        trades = bundle_pools[bundle]
        selected.append(rng.choice(trades))
        pool.extend(trades)
    top_names = ", ".join(b for b, _ in top3) if top3 else "none"
    note = f"Top bundles: {top_names}."
    return ScenarioResult(
        key="top3_bundles",
        label="1 random pick from top 3 bundles",
        selected=selected,
        pool=pool,
        notes=note,
    )


def scenario_five_from_top_bundle(
    bundle_pools: Dict[str, List[Trade]],
    min_trades: int,
    seed: int,
) -> ScenarioResult:
    ranked = rank_bundles(bundle_pools, min_trades=min_trades)
    if not ranked:
        return ScenarioResult(
            key="five_from_top_bundle",
            label="5 picks from highest-performing bundle",
            selected=[],
            pool=[],
            notes="No bundle met minimum trade threshold.",
        )
    top_bundle = ranked[0][0]
    pool = bundle_pools[top_bundle]
    rng = random.Random(seed + 23)
    selected = select_random_from_pool(pool, count=5, rng=rng)
    note = f"Top bundle: {top_bundle}."
    return ScenarioResult(
        key="five_from_top_bundle",
        label="5 picks from highest-performing bundle",
        selected=selected,
        pool=pool,
        notes=note,
    )


def scenario_top_strategy(
    strategy_trades: Dict[str, List[Trade]],
    anchor: datetime,
    window_hours: int,
    min_trades: int,
    seed: int,
) -> ScenarioResult:
    ranked = rank_strategies(
        strategy_trades,
        anchor=anchor,
        window_hours=window_hours,
        min_trades=min_trades,
    )
    if not ranked:
        return ScenarioResult(
            key="top_strategy",
            label="All capital into top strategy pick",
            selected=[],
            pool=[],
            notes="No strategy met minimum trade threshold.",
        )
    strategy_name, _, recent_trades = ranked[0]
    rng = random.Random(seed + 31)
    pick = rng.choice(recent_trades)
    selected = [replace(pick, bundle="TOP_STRATEGY_ONLY")]
    note = f"Top strategy: {strategy_name}."
    return ScenarioResult(
        key="top_strategy",
        label="All capital into top strategy pick",
        selected=selected,
        pool=recent_trades,
        notes=note,
    )


def scenario_long_only_top3_bundles(
    bundle_pools: Dict[str, List[Trade]],
    min_trades: int,
    seed: int,
) -> ScenarioResult:
    long_pools = {
        bundle: [t for t in trades if t.direction == "LONG"]
        for bundle, trades in bundle_pools.items()
    }
    ranked = rank_bundles(long_pools, min_trades=min_trades)
    top3 = ranked[:3]
    rng = random.Random(seed + 47)
    selected: List[Trade] = []
    pool: List[Trade] = []
    for bundle, _ in top3:
        trades = long_pools[bundle]
        selected.append(rng.choice(trades))
        pool.extend(trades)
    top_names = ", ".join(b for b, _ in top3) if top3 else "none"
    note = f"Long-only top bundles: {top_names}."
    return ScenarioResult(
        key="long_only_top3_bundles",
        label="Long-only: 1 random pick from top 3 bundles",
        selected=selected,
        pool=pool,
        notes=note,
    )


def evaluate_scenario(
    scenario: ScenarioResult,
    amount_per_pick: float,
    simulations: int,
    seed: int,
) -> Dict[str, Any]:
    picks = scenario.selected
    invested = amount_per_pick * len(picks)
    returns = [amount_per_pick * (trade.pnl_pct / 100.0) for trade in picks]
    total_pnl = sum(returns)
    roi = (total_pnl / invested * 100.0) if invested > 0 else 0.0
    wins = sum(1 for trade in picks if trade.pnl_pct > 0.0)
    wr = (wins / len(picks) * 100.0) if picks else 0.0
    prob_profit = monte_carlo_prob_profit(
        pool=scenario.pool,
        picks_count=len(picks),
        simulations=simulations,
        seed=seed + len(picks),
    )
    return {
        "key": scenario.key,
        "label": scenario.label,
        "notes": scenario.notes,
        "pick_count": len(picks),
        "invested": invested,
        "total_pnl": total_pnl,
        "roi_pct": roi,
        "win_rate_pct": wr,
        "prob_profit_pct": prob_profit,
        "selected_trades": picks,
    }


def annualized_window_return(annual_rate: float, hours: int) -> float:
    return annual_rate * (hours / (24.0 * 365.0))


def run_count_mode(
    bundle_closed: Sequence[Trade],
    bundle_live: Sequence[Trade],
    strategy_closed: Dict[str, List[Trade]],
    anchor: datetime,
    windows: Sequence[int],
) -> None:
    print("Health Check - Pick Counts")
    print(f"Anchor time (UTC): {anchor.isoformat()}")
    print()

    all_strategy_trades = [trade for trades in strategy_closed.values() for trade in trades]
    for hours in windows:
        closed_window = filter_window(all_strategy_trades, anchor=anchor, hours=hours)
        unique_closed = {key_trade(t) for t in closed_window}
        bundle_closed_window = filter_window(bundle_closed, anchor=anchor, hours=hours)
        bundle_live_window = filter_window(bundle_live, anchor=anchor, hours=hours)
        bundle_pools = build_bundle_pools(bundle_closed_window)

        print(f"[Window: last {hours}h]")
        print(f"- Closed picks (unique strategy trades): {len(unique_closed)}")
        print(f"- Open picks (bundle-linked live picks): {len(bundle_live_window)}")
        print(f"- Active bundles with closed picks: {sum(1 for t in bundle_pools.values() if t)}")

        top_bundles = sorted(
            ((name, len(trades)) for name, trades in bundle_pools.items() if trades),
            key=lambda x: x[1],
            reverse=True,
        )[:10]
        if top_bundles:
            print("- Top bundles by recent pick count:")
            for name, count in top_bundles:
                print(f"  - {name}: {count}")
        else:
            print("- Top bundles by recent pick count: none")

        strat_counts: Dict[str, int] = {}
        for trade in closed_window:
            strat_counts[trade.strategy] = strat_counts.get(trade.strategy, 0) + 1
        top_strats = sorted(strat_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        if top_strats:
            print("- Top strategies by recent pick count:")
            for name, count in top_strats:
                print(f"  - {name}: {count}")
        else:
            print("- Top strategies by recent pick count: none")
        print()


def build_scenarios_for_window(
    bundle_closed: Sequence[Trade],
    strategy_closed: Dict[str, List[Trade]],
    anchor: datetime,
    window_hours: int,
    min_trades: int,
    seed: int,
) -> List[ScenarioResult]:
    window_bundle_trades = filter_window(bundle_closed, anchor=anchor, hours=window_hours)
    bundle_pools = build_bundle_pools(window_bundle_trades)

    return [
        scenario_random_per_bundle(bundle_pools=bundle_pools, seed=seed),
        scenario_top3_bundles(bundle_pools=bundle_pools, min_trades=min_trades, seed=seed),
        scenario_five_from_top_bundle(bundle_pools=bundle_pools, min_trades=min_trades, seed=seed),
        scenario_top_strategy(
            strategy_trades=strategy_closed,
            anchor=anchor,
            window_hours=window_hours,
            min_trades=min_trades,
            seed=seed,
        ),
        scenario_long_only_top3_bundles(
            bundle_pools=bundle_pools,
            min_trades=min_trades,
            seed=seed,
        ),
    ]


def line_for_trade(
    trade: Trade,
    amount_per_pick: float,
    scenario_key: str,
    idx: int,
) -> str:
    pnl_usd = amount_per_pick * (trade.pnl_pct / 100.0)
    entry = f"{trade.entry_time.strftime('%Y-%m-%d %H:%M')}Z"
    exit_time = trade.exit_time.strftime("%Y-%m-%d %H:%M") + "Z" if trade.exit_time else "OPEN"
    tp = f"{trade.take_profit:.4f}" if trade.take_profit is not None else "n/a"
    sl = f"{trade.stop_loss:.4f}" if trade.stop_loss is not None else "n/a"
    entry_px = f"{trade.entry_price:.4f}" if trade.entry_price is not None else "n/a"
    exit_px = f"{trade.exit_price:.4f}" if trade.exit_price is not None else "n/a"
    return (
        f"{idx:03d}) [{scenario_key}] bundle={trade.bundle} | strat={trade.strategy} | "
        f"side={trade.direction} | symbol={trade.symbol} | entry={entry}@{entry_px} | "
        f"exit={exit_time}@{exit_px} | TP={tp} | SL={sl} | "
        f"pnl={pct(trade.pnl_pct)} ({usd(pnl_usd)}) | reason={trade.exit_reason}"
    )


def run_analyze_mode(
    bundle_closed: Sequence[Trade],
    bundle_live: Sequence[Trade],
    strategy_closed: Dict[str, List[Trade]],
    anchor: datetime,
    args: argparse.Namespace,
) -> None:
    amount_per_pick = (
        args.amount_per_pick if args.amount_per_pick is not None else BUDGET_LEVELS[args.level]
    )
    windows = parse_windows(args.check_windows)
    if not windows:
        windows = [1, 24]

    all_summaries: Dict[int, List[Dict[str, Any]]] = {}
    scenario_key_filter = None if args.scenario == "all" else args.scenario

    for window in windows:
        scenarios = build_scenarios_for_window(
            bundle_closed=bundle_closed,
            strategy_closed=strategy_closed,
            anchor=anchor,
            window_hours=window,
            min_trades=args.min_trades,
            seed=args.seed + window,
        )
        if scenario_key_filter:
            scenarios = [s for s in scenarios if s.key == scenario_key_filter]
        evaluated = [
            evaluate_scenario(
                scenario=s,
                amount_per_pick=amount_per_pick,
                simulations=args.simulations,
                seed=args.seed + window,
            )
            for s in scenarios
        ]
        all_summaries[window] = evaluated

    if args.json:
        serializable: Dict[str, Any] = {
            "anchor_utc": anchor.isoformat(),
            "amount_per_pick": amount_per_pick,
            "level": args.level,
            "windows": {},
        }
        for window, summary in all_summaries.items():
            rows = []
            for item in summary:
                rows.append(
                    {
                        "key": item["key"],
                        "label": item["label"],
                        "notes": item["notes"],
                        "pick_count": item["pick_count"],
                        "invested": item["invested"],
                        "total_pnl": item["total_pnl"],
                        "roi_pct": item["roi_pct"],
                        "win_rate_pct": item["win_rate_pct"],
                        "prob_profit_pct": item["prob_profit_pct"],
                    }
                )
            serializable["windows"][str(window)] = rows
        print(json.dumps(serializable, indent=2))
        return

    print("Health Check - What-If Analysis")
    print(f"Anchor time (UTC): {anchor.isoformat()}")
    print(f"Budget level: {args.level} ({usd(amount_per_pick)} per pick)")
    print(
        "Scenarios: random_per_bundle | top3_bundles | five_from_top_bundle | top_strategy | long_only_top3_bundles"
    )
    print()

    for window in windows:
        baseline_gic_pct = annualized_window_return(GIC_ANNUAL_RATE, window) * 100.0
        baseline_mutual_pct = annualized_window_return(MUTUAL_FUND_ANNUAL_RATE, window) * 100.0
        print(f"[Window: last {window}h]")
        summary = all_summaries.get(window, [])
        if not summary:
            print("- No scenarios available.")
            print()
            continue

        best = max(summary, key=lambda x: x["total_pnl"], default=None)
        for item in summary:
            if item["pick_count"] <= 0:
                print(f"- {item['key']}: no qualifying picks. {item['notes']}")
                continue
            gic_usd = item["invested"] * (baseline_gic_pct / 100.0)
            mutual_usd = item["invested"] * (baseline_mutual_pct / 100.0)
            prob = (
                f"{item['prob_profit_pct']:.1f}%"
                if item["prob_profit_pct"] is not None
                else "n/a"
            )
            print(
                f"- {item['key']}: picks={item['pick_count']} | invested={usd(item['invested'])} | "
                f"pnl={usd(item['total_pnl'])} | roi={pct(item['roi_pct'])} | "
                f"win={item['win_rate_pct']:.1f}% | prob_profit={prob}"
            )
            print(
                f"  baseline: GIC={usd(gic_usd)} ({baseline_gic_pct:.4f}%), "
                f"mutual_fund={usd(mutual_usd)} ({baseline_mutual_pct:.4f}%) | {item['notes']}"
            )

        if best and best["pick_count"] > 0:
            print(
                f"- Optimization candidate: {best['key']} with {usd(best['total_pnl'])} "
                f"on {usd(best['invested'])} ({pct(best['roi_pct'])})."
            )
        print()

    detail_scenarios = build_scenarios_for_window(
        bundle_closed=bundle_closed,
        strategy_closed=strategy_closed,
        anchor=anchor,
        window_hours=args.detail_window,
        min_trades=args.min_trades,
        seed=args.seed + args.detail_window,
    )
    if scenario_key_filter:
        detail_scenarios = [s for s in detail_scenarios if s.key == scenario_key_filter]

    detail_lines: List[str] = []
    line_idx = 1
    for scenario in detail_scenarios:
        detail_lines.append(f"Scenario: {scenario.key} - {scenario.label}")
        if not scenario.selected:
            detail_lines.append("  (no trades selected)")
            continue
        for trade in scenario.selected:
            detail_lines.append(line_for_trade(trade, amount_per_pick, scenario.key, line_idx))
            line_idx += 1
        detail_lines.append("")

    open_in_window = filter_window(bundle_live, anchor=anchor, hours=args.detail_window)
    if open_in_window:
        detail_lines.append("Open picks in detail window (TP/SL from live pick feed):")
        for trade in open_in_window:
            detail_lines.append(line_for_trade(trade, amount_per_pick, "open_pick", line_idx))
            line_idx += 1

    print(f"Trade Breakdown (last {args.detail_window}h)")
    if not detail_lines:
        print("- No trade details available for this window.")
        return

    pages = chunked(detail_lines, max(1, args.page_size))
    page = max(1, min(args.page, len(pages)))
    for line in pages[page - 1]:
        print(line)
    print()
    print(
        f"Message {page}/{len(pages)}. Re-run with --page {min(page + 1, len(pages))} "
        f"for next page."
    )
    print(
        "Note: Most forward trade rows do not persist numeric TP/SL; they persist exit_reason "
        "(TP/SL/TIME). Live picks include explicit TP/SL."
    )


def parse_windows(raw: str) -> List[int]:
    values: List[int] = []
    for token in (raw or "").split(","):
        token = token.strip()
        if not token:
            continue
        try:
            hours = int(token)
        except ValueError:
            continue
        if hours > 0:
            values.append(hours)
    dedup_sorted = sorted(set(values))
    return dedup_sorted


def main() -> int:
    args = parse_args()
    dashboard_path = Path(args.dashboard_path)
    if not dashboard_path.exists():
        raise SystemExit(f"Dashboard file not found: {dashboard_path}")

    strategies, bundles = load_dashboard(dashboard_path)
    bundle_closed, bundle_live, strategy_closed = collect_trades(strategies, bundles)
    anchor = latest_timestamp(bundle_closed, bundle_live, strategy_closed)

    if args.mode == "count":
        run_count_mode(
            bundle_closed=bundle_closed,
            bundle_live=bundle_live,
            strategy_closed=strategy_closed,
            anchor=anchor,
            windows=parse_windows(args.check_windows) or [1, 24],
        )
        return 0

    run_analyze_mode(
        bundle_closed=bundle_closed,
        bundle_live=bundle_live,
        strategy_closed=strategy_closed,
        anchor=anchor,
        args=args,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
