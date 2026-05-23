#!/usr/bin/env python3
"""
Strategy Correlation Guard
==========================
Computes pairwise correlation of daily returns between a candidate strategy
and all existing validated strategies. Flags candidates with correlation >= threshold.

Usage:
    python scripts/strategy_correlation_guard.py \
        --candidate baby_strategies/my_new_strategy.py \
        --threshold 0.30

Output:
    PASS  -> correlation < threshold with all validated strategies
    FAIL  -> correlation >= threshold with one or more strategies (prints which ones)
"""

import argparse
import importlib.util
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Auto-discover validated strategies from forward_signal_scanner.py
# Looks for entries with survivor_validated=True
# ---------------------------------------------------------------------------

def _load_validated_strategies():
    scanner_path = ROOT / "incubator" / "backtest_team" / "forward_signal_scanner.py"
    validated = []
    if not scanner_path.exists():
        # Fallback: use hardcoded list if scanner doesn't exist
        return [
            ("baby_strategies.volume_price_confirmation_reversal", "VolumePriceConfirmationReversalStrategy"),
            ("baby_strategies.keltner_mean_reversion", "KeltnerMeanReversionStrategy"),
            ("baby_strategies.bollinger_mean_reversion", "BollingerMeanReversionStrategy"),
        ]
    text = scanner_path.read_text()
    import re
    # Parse TIER1_STRATEGIES dict by tracking brace depth
    lines = text.splitlines()
    in_tier1 = False
    brace_depth = 0
    current_class = None
    current_body = []
    for line in lines:
        stripped = line.strip()
        if "TIER1_STRATEGIES = {" in stripped:
            in_tier1 = True
            brace_depth = stripped.count("{") - stripped.count("}")
            continue
        if not in_tier1:
            continue
        # Count braces
        brace_depth += stripped.count("{") - stripped.count("}")
        if brace_depth <= 0:
            break
        # Look for strategy class name key at depth 2 (direct child of TIER1_STRATEGIES)
        match = re.match(r'"(\w+Strategy)":\s*\{', stripped)
        if match and brace_depth == 2:
            current_class = match.group(1)
            current_body = []
        if current_class:
            current_body.append(stripped)
            if '"survivor_validated": True' in stripped or "'survivor_validated': True" in stripped:
                body_text = "\n".join(current_body)
                file_match = re.search(r'"file":\s*"([^"]+)"', body_text)
                if file_match:
                    file_path = file_match.group(1)
                    module_path = file_path.replace("/", ".").replace("\\", ".").replace(".py", "")
                    validated.append((module_path, current_class))
                current_class = None
                current_body = []
    return validated


VALIDATED_STRATEGIES = _load_validated_strategies()
TEST_SYMBOLS = ["BTC-USD", "ETH-USD", "AAPL", "MSFT", "EURUSD=X", "GC=F"]


def _load_strategy(module_path: str, class_name: str):
    """Dynamically import a strategy class. Returns None if file missing."""
    file_path = ROOT / (module_path.replace(".", "/") + ".py")
    if not file_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("mod", str(file_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, class_name)


def _normalize_yfinance_df(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten yfinance multi-index and lowercase columns."""
    df = df.copy().reset_index()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [" ".join(c).strip() if c[1] else c[0] for c in df.columns.values]
    rename = {}
    for c in df.columns:
        low = c.lower().replace(" ", "")
        for suffix in ["open", "high", "low", "close", "adjclose", "volume"]:
            if suffix in low:
                if suffix == "open" and "close" not in low:
                    rename[c] = "Open"
                elif suffix == "high":
                    rename[c] = "High"
                elif suffix == "low":
                    rename[c] = "Low"
                elif suffix == "close" or suffix == "adjclose":
                    rename[c] = "Close"
                elif suffix == "volume":
                    rename[c] = "Volume"
                break
    df = df.rename(columns=rename)
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in df.columns and col.lower() not in df.columns:
            df[col.lower()] = df[col]
    return df


def _fetch(symbol: str, period: str = "2y") -> pd.DataFrame:
    df = yf.download(symbol, period=period, progress=False, auto_adjust=True)
    if df.empty or len(df) < 50:
        return None
    return _normalize_yfinance_df(df)


def _signal_to_dict(sig):
    if hasattr(sig, "__dataclass_fields__"):
        return {
            "side": "LONG" if sig.direction in ("BUY", "LONG") else "SHORT",
            "entry_price": sig.entry_price,
            "tp": sig.take_profit,
            "sl": sig.stop_loss,
        }
    return sig


def _daily_returns(strategy_class, df: pd.DataFrame, symbol: str) -> pd.Series:
    """
    Rolling-window backtest returning a daily P&L series (0.0 when flat).
    """
    trades = []
    in_trade = False
    entry_price = entry_idx = direction = tp = sl = None
    cooldown = 0
    min_bars = 200
    pnl_series = pd.Series(0.0, index=df.index)

    for i in range(min_bars, len(df)):
        window = df.iloc[: i + 1].copy()

        if in_trade:
            high = float(df["High"].iloc[i])
            low = float(df["Low"].iloc[i])
            close = float(df["Close"].iloc[i])
            bars_held = i - entry_idx

            exit_price = None
            if direction in ("LONG", "BUY"):
                if low <= sl:
                    exit_price = sl
                elif high >= tp:
                    exit_price = tp
                elif bars_held >= 10:
                    exit_price = close
            else:
                if high >= sl:
                    exit_price = sl
                elif low <= tp:
                    exit_price = tp
                elif bars_held >= 10:
                    exit_price = close

            if exit_price is not None:
                cost = 0.002  # 0.2% round-trip
                if direction in ("LONG", "BUY"):
                    pnl = (exit_price - entry_price) / entry_price - cost
                else:
                    pnl = (entry_price - exit_price) / entry_price - cost
                # Attribute P&L to exit day
                pnl_series.iloc[i] = pnl
                in_trade = False
                cooldown = 1
            continue

        if cooldown > 0:
            cooldown -= 1
            continue

        try:
            strat = strategy_class()
            signals = strat.generate_signals(window, symbol)
        except Exception:
            continue

        if not signals:
            continue

        sig = _signal_to_dict(signals[0])
        direction = sig.get("side", sig.get("direction", "LONG"))
        tp = sig.get("take_profit", sig.get("tp"))
        sl = sig.get("stop_loss", sig.get("sl"))
        if tp is None or sl is None:
            continue

        if i + 1 >= len(df):
            break
        entry_price = float(df["Open"].iloc[i + 1])
        if entry_price <= 0:
            continue
        tp = float(tp)
        sl = float(sl)
        entry_idx = i + 1
        in_trade = True

    return pnl_series


def compute_correlation(candidate_class, validated_classes: list, symbols: list) -> dict:
    """Return max correlation and which strategy caused it."""
    candidate_returns = []
    validated_returns = {name: [] for _, name in validated_classes}

    for sym in symbols:
        df = _fetch(sym)
        if df is None:
            continue

        # Candidate
        try:
            cret = _daily_returns(candidate_class, df, sym)
            candidate_returns.append(cret)
        except Exception as e:
            print(f"  Warning: candidate failed on {sym}: {e}")
            continue

        # Validated
        for mod_path, class_name in validated_classes:
            try:
                StratClass = _load_strategy(mod_path, class_name)
                if StratClass is None:
                    continue  # File doesn't exist, skip silently
                vret = _daily_returns(StratClass, df, sym)
                validated_returns[class_name].append(vret)
            except Exception as e:
                print(f"  Warning: {class_name} failed on {sym}: {e}")
                continue

    if not candidate_returns:
        raise RuntimeError("Candidate produced no returns on any symbol.")

    # Align and concatenate across symbols
    c_series = pd.concat(candidate_returns).sort_index()
    results = {}
    for class_name, rets in validated_returns.items():
        if not rets:
            continue
        v_series = pd.concat(rets).sort_index()
        # Align dates
        aligned = pd.concat([c_series, v_series], axis=1).dropna()
        if len(aligned) < 30:
            continue
        corr = aligned.corr().iloc[0, 1]
        results[class_name] = corr

    return results


def main():
    parser = argparse.ArgumentParser(description="Strategy Correlation Guard")
    parser.add_argument("--candidate", required=True, help="Path to candidate .py file (e.g. baby_strategies/my_strat.py)")
    parser.add_argument("--class-name", default=None, help="Strategy class name (auto-detected if omitted)")
    parser.add_argument("--threshold", type=float, default=0.30, help="Max allowed correlation (default 0.30)")
    args = parser.parse_args()

    candidate_path = Path(args.candidate)
    if not candidate_path.exists():
        print(f"ERROR: File not found: {candidate_path}")
        sys.exit(1)

    # Auto-detect class name
    class_name = args.class_name
    if class_name is None:
        text = candidate_path.read_text()
        import re
        match = re.search(r"class\s+(\w+Strategy)\s*:", text)
        if not match:
            print("ERROR: Could not auto-detect strategy class name. Use --class-name.")
            sys.exit(1)
        class_name = match.group(1)

    spec = importlib.util.spec_from_file_location("candidate", candidate_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    CandidateClass = getattr(mod, class_name)

    print(f"Correlation Guard: {class_name} vs {len(VALIDATED_STRATEGIES)} validated strategies")
    print(f"Threshold: {args.threshold}")
    print(f"Symbols: {TEST_SYMBOLS}")
    print("-" * 60)

    correlations = compute_correlation(
        CandidateClass,
        VALIDATED_STRATEGIES,
        TEST_SYMBOLS,
    )

    max_corr = 0.0
    max_name = None
    for name, corr in correlations.items():
        if np.isnan(corr):
            continue
        status = "⚠️  HIGH" if abs(corr) >= args.threshold else "OK"
        print(f"  vs {name:40s}: {corr:+.3f}  {status}")
        if abs(corr) > max_corr:
            max_corr = abs(corr)
            max_name = name

    print("-" * 60)
    if max_corr >= args.threshold:
        print(f"FAIL — Max correlation {max_corr:.3f} with {max_name} exceeds {args.threshold}")
        sys.exit(1)
    else:
        print(f"PASS — Max correlation {max_corr:.3f} (with {max_name}) below {args.threshold}")
        sys.exit(0)


if __name__ == "__main__":
    main()
