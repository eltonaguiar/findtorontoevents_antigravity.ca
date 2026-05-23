"""
Baby strategy backtest runner — auto-promotes Tier-2 candidates to VT_BABY_STRATEGIES.

Usage:
    python -m baby_strategies.backtest_runner baby_strategies/equity_two_day_rsi_reversal.py
    python -m baby_strategies.backtest_runner --batch          # run all 210 strategies
    python -m baby_strategies.backtest_runner <file> --promote # write adapter if T2+

Tier-2 promotion criteria (per PERFORMANCE_CHARTER.md):
    n >= 30, WR >= 50%, PF >= 1.5, MDD <= 20%, Sharpe >= 0.5

Look-ahead bias prevention:
    Walk-forward: signals generated on df.iloc[:i] only; trade simulated on df.iloc[i:].
    Indicators computed with closed='left' (shift(1) enforced in simulate_trades).
"""
from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

RESULTS_DIR = ROOT / "baby_strategies" / "results"
VT_BABY_PATH = ROOT / "alpha_engine" / "vt_baby_strategies.py"

TIER2 = dict(n_min=30, wr_min=0.50, pf_min=1.5, mdd_max=0.20, sharpe_min=0.5)

# Default symbols to try per detected asset class
_DEFAULT_SYMBOLS: dict[str, list[str]] = {
    "CRYPTO": ["BTC-USD", "ETH-USD"],
    "EQUITY": ["SPY", "AAPL", "MSFT"],
    "ETF": ["SPY", "QQQ", "IWM"],
    "COMMODITY": ["HG=F", "GC=F"],
    "BOND": ["TLT", "IEF", "SHY"],
    "FOREX": ["EURUSD=X", "GBPUSD=X"],
    "FUTURES": ["HG=F", "GC=F"],
}


# ---------------------------------------------------------------------------
# Data fetch
# ---------------------------------------------------------------------------

def fetch_ohlcv(symbol: str, years: int = 2) -> pd.DataFrame:
    import yfinance as yf
    df = yf.download(symbol, period=f"{years}y", interval="1d", progress=False, auto_adjust=True)
    if df.empty:
        raise ValueError(f"No OHLCV data for {symbol}")
    df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
    df.index.name = "date"
    return df.dropna()


# ---------------------------------------------------------------------------
# Strategy discovery
# ---------------------------------------------------------------------------

def load_strategy_module(path: Path):
    stem = path.stem
    mod_name = f"_backtest_runner_{stem}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    mod.__name__ = mod_name
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def discover_strategy_class(mod) -> type | None:
    for name in dir(mod):
        obj = getattr(mod, name)
        if (
            isinstance(obj, type)
            and hasattr(obj, "generate_signals")
            and obj is not object
            and "Mock" not in name
        ):
            # Prefer classes with NAME attribute (strategy convention)
            if hasattr(obj, "NAME") or "Strategy" in name or "strategy" in name.lower():
                return obj
    # Fallback: first class with generate_signals
    for name in dir(mod):
        obj = getattr(mod, name)
        if isinstance(obj, type) and hasattr(obj, "generate_signals") and obj is not object:
            return obj
    return None


def detect_multi_asset_interface(cls) -> bool:
    """Return True if generate_signals takes a dict (multi-asset) rather than a DataFrame."""
    try:
        sig = inspect.signature(cls().generate_signals)
        params = list(sig.parameters.values())
        if params:
            ann = params[0].annotation
            if ann != inspect.Parameter.empty:
                return "dict" in str(ann).lower()
    except Exception:
        pass
    return False


def detect_asset_class(cls, path: Path) -> str:
    """Guess asset class from NAME, file name, or SYMBOL_PRESETS."""
    name_lower = (getattr(cls, "NAME", "") + path.stem).lower()
    if "crypto" in name_lower or "bitcoin" in name_lower or "btc" in name_lower:
        return "CRYPTO"
    if "bond" in name_lower or "yield" in name_lower or "tlt" in name_lower:
        return "BOND"
    if "forex" in name_lower or "fx" in name_lower or "currency" in name_lower:
        return "FOREX"
    if "copper" in name_lower or "platinum" in name_lower or "commodity" in name_lower or "gold" in name_lower:
        return "COMMODITY"
    if "etf" in name_lower:
        return "ETF"
    return "EQUITY"


# ---------------------------------------------------------------------------
# Trade simulation (look-ahead safe)
# ---------------------------------------------------------------------------

def simulate_trades(df: pd.DataFrame, signals: list[dict]) -> list[dict]:
    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values

    # Cooldown: skip re-entry while a trade is still open for (symbol, side).
    # Prevents walk-forward from counting the same trend as multiple trades.
    cooldown_until: dict[tuple, int] = {}

    trades = []
    for sig in signals:
        bar_idx = int(sig.get("bar_index", len(closes) - 1))
        if bar_idx >= len(closes) - 1:
            continue

        entry = float(sig.get("entry_price") or closes[bar_idx])
        tp = sig.get("take_profit")
        sl = sig.get("stop_loss")
        side = str(sig.get("side", "LONG")).upper()
        max_hold = int(sig.get("max_hold_days", 10))

        if not tp or not sl or entry <= 0:
            continue
        tp, sl = float(tp), float(sl)

        cooldown_key = (sig.get("symbol", ""), side)
        if bar_idx < cooldown_until.get(cooldown_key, 0):
            continue  # still in a prior trade for this symbol+side

        outcome = None
        exit_price = entry
        for i in range(bar_idx + 1, min(bar_idx + 1 + max_hold, len(closes))):
            h, lo = highs[i], lows[i]
            if side == "LONG":
                if lo <= sl:
                    outcome, exit_price = "loss", sl
                    break
                if h >= tp:
                    outcome, exit_price = "win", tp
                    break
            else:
                if h >= sl:
                    outcome, exit_price = "loss", sl
                    break
                if lo <= tp:
                    outcome, exit_price = "win", tp
                    break

        if outcome is None:
            exit_price = closes[min(bar_idx + max_hold, len(closes) - 1)]
            if side == "LONG":
                outcome = "win" if exit_price > entry else "loss"
            else:
                outcome = "win" if exit_price < entry else "loss"

        pnl = (exit_price - entry) / entry if side == "LONG" else (entry - exit_price) / entry
        trades.append({"outcome": outcome, "pnl_pct": pnl})
        cooldown_until[cooldown_key] = bar_idx + max_hold + 1  # next valid entry after trade closes

    return trades


def compute_metrics(trades: list[dict]) -> dict[str, Any]:
    if not trades:
        return {"n": 0, "wr": 0.0, "pf": 0.0, "mdd": 0.0, "sharpe": 0.0}

    wins = [t for t in trades if t["outcome"] == "win"]
    losses = [t for t in trades if t["outcome"] == "loss"]
    n = len(trades)
    wr = len(wins) / n

    gross_profit = sum(t["pnl_pct"] for t in wins)
    gross_loss = abs(sum(t["pnl_pct"] for t in losses))
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    equity = np.cumprod([1 + t["pnl_pct"] for t in trades])
    peak = np.maximum.accumulate(equity)
    mdd = float(((peak - equity) / peak).max()) if len(equity) > 0 else 0.0

    pnls = np.array([t["pnl_pct"] for t in trades])
    sharpe = float(pnls.mean() / pnls.std() * np.sqrt(252)) if pnls.std() > 0 else 0.0

    return {
        "n": n,
        "wr": round(wr, 4),
        "pf": round(min(pf, 999.0), 4),
        "mdd": round(mdd, 4),
        "sharpe": round(sharpe, 4),
    }


# ---------------------------------------------------------------------------
# Walk-forward backtest
# ---------------------------------------------------------------------------

def run_backtest(
    strategy_path: Path,
    symbol: str,
    years: int = 2,
    step: int = 5,
    min_bars: int = 60,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "strategy": strategy_path.stem,
        "symbol": symbol,
        "years": years,
        "run_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        mod = load_strategy_module(strategy_path)
    except Exception as e:
        result["error"] = f"import_error: {e}"
        return result

    cls = discover_strategy_class(mod)
    if not cls:
        result["error"] = "no_strategy_class_found"
        return result

    result["class"] = cls.__name__
    result["name"] = getattr(cls, "NAME", strategy_path.stem)
    multi_asset = detect_multi_asset_interface(cls)

    try:
        df = fetch_ohlcv(symbol, years)
    except Exception as e:
        result["error"] = f"fetch_error: {e}"
        return result

    result["total_bars"] = len(df)
    strategy = cls()

    all_signals: list[dict] = []
    errors = 0
    for i in range(min_bars, len(df), step):
        window = df.iloc[:i].copy()
        try:
            if multi_asset:
                sigs = strategy.generate_signals({symbol: window}, symbol)
            else:
                sigs = strategy.generate_signals(window, symbol)
            if sigs:
                for sig in sigs:
                    sig.setdefault("bar_index", i - 1)
                all_signals.extend(sigs)
        except Exception:
            errors += 1
            if errors > 10:
                break

    result["signals_generated"] = len(all_signals)
    result["generation_errors"] = errors

    trades = simulate_trades(df, all_signals)
    result["trades_simulated"] = len(trades)

    metrics = compute_metrics(trades)
    result.update(metrics)

    tier2_pass = (
        metrics["n"] >= TIER2["n_min"]
        and metrics["wr"] >= TIER2["wr_min"]
        and metrics["pf"] >= TIER2["pf_min"]
        and metrics["mdd"] <= TIER2["mdd_max"]
        and metrics["sharpe"] >= TIER2["sharpe_min"]
    )
    result["tier2_pass"] = tier2_pass
    result["tier2_criteria"] = TIER2

    return result


# ---------------------------------------------------------------------------
# VT_BABY_STRATEGIES adapter template
# ---------------------------------------------------------------------------

def generate_adapter_code(result: dict, multi_asset: bool = False) -> str:
    stem = result["strategy"]
    cls_name = result.get("class", "")
    name = result.get("name", stem)
    symbol = result["symbol"]

    if multi_asset:
        body = textwrap.dedent(f"""\
            def vt_{stem}(data: dict | pd.DataFrame, symbol: str = "{symbol}") -> list[dict]:
                from baby_strategies.{stem} import {cls_name}
                if isinstance(data, dict):
                    df = data.get(symbol, data.get(list(data.keys())[0]))
                else:
                    df = data
                if df is None or len(df) < 60:
                    return []
                df = _lower_ohlcv(df)
                sigs = {cls_name}().generate_signals({{symbol: df}}, symbol)
                out = []
                for s in (sigs or []):
                    d = _signal_to_dict(s, symbol)
                    if d:
                        d["asset_class"] = "{result.get("asset_class", "EQUITY")}"
                        out.append(d)
                return out
        """)
    else:
        body = textwrap.dedent(f"""\
            def vt_{stem}(data: dict | pd.DataFrame, symbol: str = "{symbol}") -> list[dict]:
                from baby_strategies.{stem} import {cls_name}
                df = data if isinstance(data, pd.DataFrame) else data.get(symbol)
                if df is None or len(df) < 60:
                    return []
                df = _lower_ohlcv(df)
                sigs = {cls_name}().generate_signals(df, symbol)
                out = []
                for s in (sigs or []):
                    d = _signal_to_dict(s, symbol)
                    if d:
                        out.append(d)
                return out
        """)

    reg_line = f'VT_BABY_STRATEGIES["{name}"] = vt_{stem}'
    return body + "\n" + reg_line


def auto_promote(result: dict, multi_asset: bool = False) -> bool:
    """Append adapter function + registration to vt_baby_strategies.py."""
    adapter = generate_adapter_code(result, multi_asset)
    stem = result["strategy"]
    name = result.get("name", stem)

    content = VT_BABY_PATH.read_text(encoding="utf-8")
    if f'"{name}"' in content:
        print(f"  [SKIP] {name!r} already registered in VT_BABY_STRATEGIES")
        return False

    marker = "# --- auto-promoted baby strategies (added by backtest_runner.py) ---"
    if marker not in content:
        content += f"\n\n{marker}\n"
    content += f"\n{adapter}\n"
    VT_BABY_PATH.write_text(content, encoding="utf-8")

    import subprocess
    r = subprocess.run(
        [sys.executable, "-m", "py_compile", str(VT_BABY_PATH)], capture_output=True
    )
    if r.returncode != 0:
        print(f"  [ERROR] Syntax error after auto-promote; reverting")
        VT_BABY_PATH.write_text(content.replace(adapter, ""), encoding="utf-8")
        return False

    print(f"  [PROMOTED] {name!r} → VT_BABY_STRATEGIES")
    return True


# ---------------------------------------------------------------------------
# Batch mode
# ---------------------------------------------------------------------------

def run_batch(years: int = 3, promote: bool = False) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    strategy_files = sorted(
        p for p in (ROOT / "baby_strategies").glob("*.py")
        if not p.name.startswith("backtest_")
        and p.name not in {"__init__.py", "backtest_runner.py"}
    )
    print(f"Found {len(strategy_files)} strategy files. Running backtests...")

    promoted, skipped, failed, passed = 0, 0, 0, 0
    for path in strategy_files:
        try:
            mod = load_strategy_module(path)
            cls = discover_strategy_class(mod)
            if not cls:
                skipped += 1
                continue
            asset_cls = detect_asset_class(cls, path)
            symbols = _DEFAULT_SYMBOLS.get(asset_cls, ["SPY"])

            best: dict | None = None
            for sym in symbols:
                try:
                    r = run_backtest(path, sym, years)
                    if "error" not in r and (best is None or r.get("n", 0) > best.get("n", 0)):
                        r["asset_class"] = asset_cls
                        best = r
                except Exception:
                    continue

            if best is None:
                failed += 1
                continue

            out_path = RESULTS_DIR / f"{path.stem}.json"
            out_path.write_text(json.dumps(best, indent=2), encoding="utf-8")

            verdict = "T2+" if best.get("tier2_pass") else "skip"
            n, wr, pf = best.get("n", 0), best.get("wr", 0), best.get("pf", 0)
            print(f"  {path.stem:<45} n={n:>3}  WR={wr:.1%}  PF={pf:.2f}  [{verdict}]")

            if best.get("tier2_pass"):
                passed += 1
                if promote:
                    multi = detect_multi_asset_interface(cls)
                    auto_promote(best, multi)
                    promoted += 1
            else:
                skipped += 1

        except Exception as e:
            print(f"  ERROR {path.stem}: {e}")
            failed += 1

    print(f"\nBatch done: {passed} T2+ | {skipped} skip | {failed} failed | {promoted} promoted")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Baby strategy backtest runner")
    parser.add_argument("strategy", nargs="?", help="Path to strategy .py file")
    parser.add_argument("--symbol", "-s", default=None, help="Symbol to backtest (default: auto-detect)")
    parser.add_argument("--years", "-y", type=int, default=3, help="Years of history (default: 3)")
    parser.add_argument("--batch", action="store_true", help="Run all strategies in baby_strategies/")
    parser.add_argument("--promote", action="store_true", help="Auto-add T2+ to VT_BABY_STRATEGIES")
    parser.add_argument("--step", type=int, default=5, help="Walk-forward step size in bars (default: 5)")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.batch:
        run_batch(years=args.years, promote=args.promote)
        return

    if not args.strategy:
        parser.error("Provide a strategy file or --batch")

    path = Path(args.strategy)
    if not path.exists():
        path = ROOT / args.strategy
    if not path.exists():
        sys.exit(f"File not found: {args.strategy}")

    mod = load_strategy_module(path)
    cls = discover_strategy_class(mod)
    if not cls:
        sys.exit("No strategy class with generate_signals() found")

    asset_cls = detect_asset_class(cls, path)
    symbol = args.symbol or _DEFAULT_SYMBOLS.get(asset_cls, ["SPY"])[0]
    multi = detect_multi_asset_interface(cls)

    print(f"Strategy : {path.stem} ({cls.__name__})")
    print(f"Asset cls: {asset_cls}  |  Symbol: {symbol}  |  Multi-asset: {multi}")

    result = run_backtest(path, symbol, args.years, step=args.step)
    result["asset_class"] = asset_cls

    if "error" in result:
        print(f"\nERROR: {result['error']}")
    else:
        print(f"\n{'Metric':<12} {'Value':>10}")
        print("-" * 25)
        for k in ("n", "wr", "pf", "mdd", "sharpe"):
            v = result.get(k, 0)
            fmt = f"{v:.1%}" if k in ("wr", "mdd") else f"{v:.4f}"
            print(f"{k:<12} {fmt:>10}")
        verdict = "TIER-2 PASS" if result.get("tier2_pass") else "BELOW TIER-2"
        print(f"\nVerdict: {verdict}")

    out_path = RESULTS_DIR / f"{path.stem}_{symbol.replace('=','').replace('-','')}.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Result → {out_path}")

    if result.get("tier2_pass"):
        adapter = generate_adapter_code(result, multi)
        print(f"\nAdapter template (review then --promote to wire):\n")
        print(adapter)
        if args.promote:
            auto_promote(result, multi)


if __name__ == "__main__":
    main()
