#!/usr/bin/env python3
"""
Update forward-paper matches from real market data.

Evaluates paper-trading strategies on post-start real BTC bars and writes
closed-trade forward metrics back to each strategy .meta.json.
"""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from incubator.backtest_team.real_data_sweep_runner import RealDataSweepRunner, Trade
from incubator.backtest_team.generate_baby_strats_dashboard import _verification_payload

AGENTS_ROOT = ROOT / "incubator" / "agents"
REPORTS_ROOT = ROOT / "incubator" / "backtest_results"


def _parse_dt(text: Any) -> Optional[pd.Timestamp]:
    if not text:
        return None
    try:
        ts = pd.to_datetime(str(text), utc=True, errors="coerce")
        if pd.isna(ts):
            return None
        return ts
    except Exception:
        return None


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _discover_meta_files(agents_root: Path) -> List[Path]:
    return sorted(agents_root.rglob("*.py.meta.json"))


def _load_strategy_class(py_file: Path) -> Tuple[Optional[type], Optional[str]]:
    try:
        module_name = f"fwd_{py_file.stem}_{int(datetime.now().timestamp() * 1_000_000) % 1_000_000}"
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec is None or spec.loader is None:
            return None, "Import spec loader not available"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[attr-defined]
    except Exception as exc:
        return None, f"Import error: {exc}"

    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, type) and attr_name.endswith("Strategy") and attr_name != "Strategy":
            return attr, None
    return None, "No class ending with 'Strategy' found"


def _slice_df_to_ts(df: pd.DataFrame, ts: pd.Timestamp) -> pd.DataFrame:
    return df[df["timestamp"] <= ts].copy()


def _slice_series_to_ts(series: pd.Series, ts: pd.Timestamp) -> pd.Series:
    return series[series.index <= ts].copy()


def _pair_to_ticker(pair: str) -> str:
    """Convert 'ETH/USDT' -> 'ETHUSDT'."""
    return pair.replace("/", "")


def _resolve_pair(meta: Dict[str, Any], strategy_class: Optional[type] = None) -> str:
    """Determine the target trading pair for a strategy.

    Priority: meta.json 'pair' field > strategy class TARGET_PAIR > default BTC/USDT.
    """
    pair = meta.get("pair")
    if pair:
        return str(pair)
    if strategy_class is not None:
        cls_pair = getattr(strategy_class, "TARGET_PAIR", None)
        if cls_pair:
            return str(cls_pair)
    return "BTC/USDT"


def _build_kwargs(runner: RealDataSweepRunner, param_names: List[str], ts: pd.Timestamp, equity: float, symbol: str = "BTCUSDT") -> Dict[str, Any]:
    ctx = runner._ctx
    kwargs: Dict[str, Any] = {}
    for p in param_names:
        if p == "symbol":
            kwargs[p] = symbol
        elif p in ("data", "btc_data", "data_1h"):
            kwargs[p] = _slice_df_to_ts(ctx["btc"], ts)
        elif p == "data_4h":
            kwargs[p] = _slice_df_to_ts(ctx["btc_4h"], ts)
        elif p == "data_5m":
            kwargs[p] = _slice_df_to_ts(ctx["btc_5m"], ts)
        elif p == "data_15m":
            kwargs[p] = _slice_df_to_ts(ctx["btc_15m"], ts)
        elif p == "spx_data":
            kwargs[p] = _slice_df_to_ts(ctx["spx"], ts)
        elif p == "dxy_data":
            kwargs[p] = _slice_df_to_ts(ctx["dxy"], ts)
        elif p == "vix_data":
            kwargs[p] = _slice_df_to_ts(ctx["vix"], ts)
        elif p == "flow_data":
            kwargs[p] = _slice_series_to_ts(ctx["flow"], ts)
        elif p == "whale_inflow":
            kwargs[p] = _slice_series_to_ts(ctx["whale_inflow"], ts)
        elif p == "funding_rate":
            f_slice = _slice_series_to_ts(ctx["funding"], ts)
            kwargs[p] = float(f_slice.iloc[-1]) if len(f_slice) else 0.0
        elif p == "gov_data":
            kwargs[p] = _slice_series_to_ts(ctx["gov"], ts)
        elif p == "social_data":
            kwargs[p] = _slice_series_to_ts(ctx["social"], ts)
        elif p == "liquidation_data":
            kwargs[p] = _slice_df_to_ts(ctx["liquidation"], ts)
        elif p == "account_balance":
            kwargs[p] = float(equity)
        else:
            kwargs[p] = None
    return kwargs


def _trade_exit_ts(trade: Trade) -> Optional[pd.Timestamp]:
    return _parse_dt(trade.exit_time)


def _daily_from_trades(trades: List[Trade]) -> List[Dict[str, Any]]:
    buckets: Dict[str, Dict[str, Any]] = {}
    # Use US/Eastern so trades exiting at e.g. 11PM EST Mar 15
    # are correctly bucketed under Mar 15 (not Mar 16 UTC).
    import zoneinfo
    est = zoneinfo.ZoneInfo("America/New_York")
    for t in trades:
        exit_ts = _trade_exit_ts(t)
        if exit_ts is None:
            continue
        day = exit_ts.astimezone(est).strftime("%Y-%m-%d")
        b = buckets.setdefault(day, {"date": day, "pnl": 0.0, "pnl_pct": 0.0, "trades": 0, "wins": 0, "losses": 0})
        b["pnl"] += float(t.pnl)
        b["pnl_pct"] += float(t.pnl_pct) * 100.0
        b["trades"] += 1
        if float(t.pnl_pct) > 0:
            b["wins"] += 1
        else:
            b["losses"] += 1
    out = [buckets[k] for k in sorted(buckets.keys())]
    for row in out:
        row["pnl"] = round(float(row["pnl"]), 6)
        row["pnl_pct"] = round(float(row["pnl_pct"]), 4)
    return out


def _compute_forward_metrics(trades: List[Trade]) -> Dict[str, Any]:
    n = len(trades)
    if n <= 0:
        return {"win_rate": None, "sharpe": None, "max_drawdown": None, "total_trades": 0}

    pnl_pct = np.array([float(t.pnl_pct) for t in trades], dtype=float)
    wins = int((pnl_pct > 0).sum())
    win_rate = float(wins / n)

    sharpe = None
    if len(pnl_pct) > 1 and np.std(pnl_pct) > 0.001:
        sharpe = float(np.mean(pnl_pct) / np.std(pnl_pct) * np.sqrt(252))
        sharpe = max(-99.99, min(99.99, sharpe))  # Cap to prevent near-zero std overflow

    equity = [1.0]
    for r in pnl_pct:
        equity.append(equity[-1] * (1.0 + r))
    peak = equity[0]
    max_dd = 0.0
    for eq in equity:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    return {
        "win_rate": round(win_rate, 6),
        "sharpe": round(sharpe, 6) if sharpe is not None else None,
        "max_drawdown": round(float(max_dd), 6),
        "total_trades": int(n),
    }


def _evaluate_strategy_forward(
    runner: RealDataSweepRunner,
    py_file: Path,
    meta: Dict[str, Any],
    min_bars: int,
    strategy_timeout_sec: int,
    symbol: str = "BTCUSDT",
) -> Dict[str, Any]:
    started_at = _parse_dt(((meta.get("paper_trading") or {}).get("started_at")))
    if started_at is None:
        started_at = _parse_dt(meta.get("created_at"))
    if started_at is None:
        return {"status": "skipped", "reason": "missing_started_at"}

    strategy_class, err = _load_strategy_class(py_file)
    if strategy_class is None:
        return {"status": "error", "reason": err or "load_failed"}

    try:
        strategy = strategy_class()
        generate_fn = getattr(strategy, "generate_signals")
        param_names = list(inspect.signature(generate_fn).parameters.keys())
    except Exception as exc:
        return {"status": "error", "reason": f"init_error: {exc}"}

    btc = runner._ctx["btc"]
    eligible_idx = [i for i in range(min_bars, len(btc)) if pd.to_datetime(btc.iloc[i]["timestamp"], utc=True) >= started_at]
    if not eligible_idx:
        return {"status": "ok", "trades": [], "started_at": started_at.isoformat(), "live_picks": []}

    trades: List[Trade] = []
    live_picks: List[Dict[str, Any]] = []
    equity = 10_000.0
    started_clock = datetime.now(timezone.utc).timestamp()
    errors_seen = 0

    for end_idx in eligible_idx:
        if datetime.now(timezone.utc).timestamp() - started_clock > strategy_timeout_sec:
            return {"status": "timeout", "trades": trades, "errors_seen": errors_seen, "started_at": started_at.isoformat()}

        ts = pd.to_datetime(btc.iloc[end_idx]["timestamp"], utc=True)
        try:
            kwargs = _build_kwargs(runner, param_names, ts, equity, symbol=symbol)
            raw = generate_fn(**kwargs)
            signals = runner._normalize_signals(raw)
        except Exception:
            errors_seen += 1
            continue

        # Latest-bar signal snapshot gives immediate forward-facing "FW picks"
        # even before any trade has closed for WR/Sharpe accounting.
        if end_idx == eligible_idx[-1]:
            for sig in signals:
                direction = str(getattr(sig, "direction", "") or "").upper()
                side = "BUY" if "BUY" in direction or "LONG" in direction else "SELL" if "SELL" in direction or "SHORT" in direction else None
                if side is None:
                    continue
                try:
                    entry_price = float(getattr(sig, "entry_price"))
                    take_profit = float(getattr(sig, "take_profit"))
                    stop_loss = float(getattr(sig, "stop_loss"))
                except Exception:
                    continue
                live_picks.append(
                    {
                        "side": side,
                        "symbol": str(getattr(sig, "symbol", "BTCUSDT") or "BTCUSDT"),
                        "entry_price": round(entry_price, 8),
                        "take_profit": round(take_profit, 8),
                        "stop_loss": round(stop_loss, 8),
                        "generated_at": ts.isoformat(),
                    }
                )

        for sig in signals:
            try:
                trade = runner._simulate_trade(sig, end_idx)
            except Exception:
                errors_seen += 1
                continue
            if trade is None:
                continue
            exit_ts = _trade_exit_ts(trade)
            if exit_ts is None:
                continue
            if exit_ts < started_at:
                continue
            trades.append(trade)
            equity += float(trade.pnl)

    return {
        "status": "ok",
        "trades": trades,
        "errors_seen": errors_seen,
        "started_at": started_at.isoformat(),
        "live_picks": live_picks,
    }


def _update_meta_forward(
    meta_path: Path,
    meta: Dict[str, Any],
    trades: List[Trade],
    now_utc: datetime,
    live_picks: Optional[List[Dict[str, Any]]] = None,
    symbol: str = "BTCUSDT",
) -> None:
    paper = meta.setdefault("paper_trading", {})
    started_at = _parse_dt(paper.get("started_at")) or _parse_dt(meta.get("created_at")) or pd.Timestamp(now_utc)
    days_elapsed = max(0, (pd.Timestamp(now_utc) - started_at).days)
    days_remaining = max(0, 30 - days_elapsed)
    progress_pct = min(100.0, max(0.0, (days_elapsed / 30.0) * 100.0))

    daily = _daily_from_trades(trades)
    metrics = _compute_forward_metrics(trades)
    current_pnl_pct = round(sum(float(x["pnl_pct"]) for x in daily), 4)

    paper["days_elapsed"] = int(days_elapsed)
    paper["days_remaining"] = int(days_remaining)
    paper["progress_pct"] = float(round(progress_pct, 2))
    paper["trades_count"] = int(metrics["total_trades"])
    paper["current_pnl"] = float(current_pnl_pct)
    paper["daily_pnl"] = daily
    paper["last_updated"] = now_utc.isoformat()

    meta["forward_metrics"] = metrics
    meta["forward_daily_pnl"] = daily
    meta["forward_live_picks"] = live_picks or []
    meta["forward_live_pick_count"] = int(len(live_picks or []))
    meta["forward_last_updated"] = now_utc.isoformat()
    meta["forward_data_source"] = "real_market_data_crypto_db"

    # Individual trade records for audit trail
    meta["forward_trades"] = [
        {
            "symbol": symbol,
            "entry_time": str(t.entry_time),
            "exit_time": str(t.exit_time),
            "direction": str(t.direction),
            "entry_price": round(float(t.entry_price), 2),
            "exit_price": round(float(t.exit_price), 2),
            "pnl_pct": round(float(t.pnl_pct) * 100.0, 4),
            "exit_reason": str(t.exit_reason),
            "bars_held": int(t.bars_held),
        }
        for t in trades
    ]

    _save_json(meta_path, meta)


def _get_runner(
    runners: Dict[str, RealDataSweepRunner],
    pair: str,
    args: argparse.Namespace,
) -> Optional[RealDataSweepRunner]:
    """Get or create a RealDataSweepRunner for the given pair (lazy cache)."""
    if pair in runners:
        return runners[pair]
    try:
        runner = RealDataSweepRunner(
            db_path=args.db_path,
            pair=pair,
            bars=args.bars,
            initial_capital=10_000.0,
            commission=args.commission,
            max_hold_bars=args.max_hold_bars,
            min_bars=args.min_bars,
            bar_step=args.bar_step,
            strategy_timeout_sec=args.strategy_timeout_sec,
        )
        runners[pair] = runner
        print(f"[FORWARD] Loaded runner for {pair}")
        return runner
    except Exception as exc:
        print(f"[FORWARD] Could not create runner for {pair}: {exc}")
        runners[pair] = None  # type: ignore[assignment]
        return None


def run(args: argparse.Namespace) -> int:
    runners: Dict[str, RealDataSweepRunner] = {}

    # Pre-load the default BTC/USDT runner
    _get_runner(runners, args.pair, args)

    meta_files = _discover_meta_files(AGENTS_ROOT)
    now_utc = datetime.now(timezone.utc)
    processed = 0
    updated = 0
    skipped_nonreal = 0
    skipped_no_data = 0
    with_matches = 0
    rows: List[Dict[str, Any]] = []

    for meta_path in meta_files:
        meta = _load_json(meta_path)
        status = str(meta.get("status", "")).lower()
        if status not in {"paper_trading", "graduated", "live"}:
            continue

        py_file = meta_path.with_suffix("")
        if py_file.suffix == ".meta":
            py_file = py_file.with_suffix("")
        if py_file.suffix != ".py":
            continue
        if not py_file.exists():
            continue

        if args.real_only:
            verification = _verification_payload(py_file, meta)
            if verification.get("real_data_verified") is not True:
                skipped_nonreal += 1
                continue

        # Resolve target pair — check meta, then strategy class, then default
        strategy_class, _ = _load_strategy_class(py_file)
        pair = _resolve_pair(meta, strategy_class)
        ticker = _pair_to_ticker(pair)

        runner = _get_runner(runners, pair, args)
        if runner is None:
            skipped_no_data += 1
            continue

        processed += 1
        eval_result = _evaluate_strategy_forward(
            runner=runner,
            py_file=py_file,
            meta=meta,
            min_bars=args.min_bars,
            strategy_timeout_sec=args.strategy_timeout_sec,
            symbol=ticker,
        )

        trades = eval_result.get("trades", []) if isinstance(eval_result.get("trades"), list) else []
        live_picks = eval_result.get("live_picks", []) if isinstance(eval_result.get("live_picks"), list) else []
        _update_meta_forward(meta_path, meta, trades, now_utc, live_picks, symbol=ticker)
        updated += 1
        if len(trades) > 0:
            with_matches += 1

        rows.append(
            {
                "agent_id": meta.get("agent_id", py_file.parent.name),
                "strategy_name": meta.get("strategy_name", py_file.stem),
                "pair": pair,
                "status": eval_result.get("status"),
                "trade_matches": len(trades),
                "errors_seen": int(eval_result.get("errors_seen") or 0),
                "started_at": eval_result.get("started_at"),
                "meta_file": str(meta_path.relative_to(ROOT)),
            }
        )

    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = now_utc.strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_ROOT / f"forward_matches_{stamp}.json"
    report_payload = {
        "generated_at": now_utc.isoformat(),
        "db_path": args.db_path,
        "default_pair": args.pair,
        "pairs_loaded": list(runners.keys()),
        "processed": processed,
        "updated": updated,
        "real_only": bool(args.real_only),
        "skipped_non_real": skipped_nonreal,
        "skipped_no_data": skipped_no_data,
        "with_matches": with_matches,
        "rows": rows,
    }
    _save_json(report_path, report_payload)

    print(f"[FORWARD] Pairs loaded: {list(runners.keys())}")
    print(f"[FORWARD] Processed: {processed}, Updated: {updated}, With matches: {with_matches}, Skipped non-real: {skipped_nonreal}, No data: {skipped_no_data}")
    print(f"[FORWARD] Report: {report_path}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update forward-paper matches from real market data.")
    parser.add_argument("--db-path", default=str(ROOT / "crypto_data.db"))
    parser.add_argument("--pair", default="BTC/USDT")
    parser.add_argument("--bars", type=int, default=2500)
    parser.add_argument("--commission", type=float, default=0.001)
    parser.add_argument("--max-hold-bars", type=int, default=20)
    parser.add_argument("--min-bars", type=int, default=80)
    parser.add_argument("--bar-step", type=int, default=2)
    parser.add_argument("--strategy-timeout-sec", type=int, default=20)
    parser.add_argument("--real-only", action="store_true", default=True, help="Only update real-data-verified strategies.")
    parser.add_argument("--allow-mixed", action="store_true", help="Include mixed/proxy strategies.")
    args = parser.parse_args()
    if args.allow_mixed:
        args.real_only = False
    return args


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
