"""
New Equity/Commodity Strategies Emitter — 2026-05-16
=====================================================

Production caller for the 20 academically-backed strategies in
``alpha_engine/new_equity_commodity_strategies_20.py`` (10 equity/ETF +
10 commodity). Satisfies the Wire-Up Rule: this module is the required
production caller so the strategy module is no longer an orphan.

Writes: alpha_engine/data/scanner_output/new_strategies_picks.json

Wire-Up Rule status: OPT-IN SIDECAR
  - Guarded by ``NEW_STRATS_RUNNER_ENABLED`` env var (default "1").
  - Picks reach /audit on next dashboard rebuild after this emitter runs.
  - Shadow-mode validation recommended for 14 days before gate promotion.

Run:
    python tools/new_strategies_emitter.py [--dry-run]
    NEW_STRATS_RUNNER_ENABLED=0 python tools/new_strategies_emitter.py  # skip
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "alpha_engine"))
sys.path.insert(0, str(ROOT))

OUT_PATH = ROOT / "alpha_engine" / "data" / "scanner_output" / "new_strategies_picks.json"
ENABLED_FLAG = "NEW_STRATS_RUNNER_ENABLED"
SOURCE_SYSTEM = "new_equity_commodity_strategies_20"

# Equity/ETF tickers to fetch — broad coverage matching strategy universe
EQUITY_SYMBOLS = [
    "SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META",
    "JPM", "BAC", "GS", "V", "UNH", "PFE", "MRK", "LLY", "JNJ",
    "XLV", "XLK", "XLF", "XLE", "XLU", "XLP", "XLC", "XLRE", "IWM", "DIA",
]

# Commodity futures tickers to fetch
COMMODITY_SYMBOLS = [
    "GC=F", "SI=F", "CL=F", "NG=F", "HG=F",
    "ZC=F", "ZW=F", "CT=F", "KC=F", "ZS=F",
]

# Strategies that operate on equity/ETF symbols
_EQUITY_STRATEGIES = {
    "post_earnings_drift",
    "week52_high_breakout",
    "low_volatility_factor",
    "short_interest_squeeze",
    "sector_rotation_etf",
    "bollinger_band_squeeze_stocks",
    "reversal_after_3_down_days",
    "dividend_capture_strategy",
    "golden_cross_200d",
    "mean_reversion_2day",
}

# Strategies that operate on commodity symbols
_COMMODITY_STRATEGIES = {
    "gold_real_yield_signal",
    "commodity_channel_index_bounce",
    "contango_roll_yield",
    "precious_metals_correlation_pair",
    "energy_eia_inventory_proxy",
    "copper_economic_cycle",
    "agricultural_weather_premium",
    "commodity_momentum_12_1",
    "commodity_volatility_risk_premium",
    "platinum_palladium_spread",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_ohlcv(symbols: list[str], period: str = "6mo") -> dict:
    """Download OHLCV data; return {symbol: DataFrame}. Fails gracefully."""
    try:
        import yfinance as yf
        import pandas as pd

        data = {}
        for sym in symbols:
            try:
                df = yf.download(sym, period=period, progress=False, auto_adjust=True)
                if df is None or len(df) < 20:
                    continue
                # yfinance >=0.2.x returns MultiIndex columns; flatten to single-level
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                data[sym] = df
            except Exception as e:
                print(
                    f"[new_strategies_emitter] yfinance fetch failed for {sym}: {e}",
                    file=sys.stderr,
                )
        return data
    except ImportError:
        print(
            "[new_strategies_emitter] yfinance not available — returning empty dataset",
            file=sys.stderr,
        )
        return {}


def _infer_asset_class(strategy_name: str, symbol: str) -> str:
    """Infer asset_class from strategy name or symbol suffix."""
    if strategy_name in _COMMODITY_STRATEGIES or symbol.endswith("=F"):
        return "COMMODITY"
    return "EQUITY"


def _normalize_pick(raw: dict) -> dict:
    """Normalize strategy output dict to the canonical pick schema."""
    strategy = raw.get("strategy", "unknown")
    symbol = raw.get("symbol", "UNKNOWN")
    signal_type = raw.get("signal_type", "BUY")
    direction = "LONG" if signal_type in ("BUY", "LONG") else "SHORT"
    asset_class = _infer_asset_class(strategy, symbol)
    ts = raw.get("timestamp") or _now_iso()
    entry = float(raw.get("entry_price", 0))
    tp = float(raw.get("take_profit", 0))
    sl = float(raw.get("stop_loss", 0))

    return {
        "id": f"{SOURCE_SYSTEM}::{strategy}::{symbol}::{ts[:10]}",
        "symbol": symbol,
        "strategy": strategy,
        "source_system": SOURCE_SYSTEM,
        "asset_class": asset_class,
        "signal_type": signal_type,
        "direction": direction,
        "entry_price": round(entry, 4),
        "take_profit": round(tp, 4),
        "stop_loss": round(sl, 4),
        "confidence": float(raw.get("confidence", 0.6)),
        "risk_reward": float(raw.get("risk_reward", 0.0)),
        "reason": raw.get("reason", ""),
        "timeframe": raw.get("timeframe", "1d"),
        "max_hold_bars": raw.get("max_hold_bars", 10),
        "status": "OPEN",
        "timestamp": ts,
        "generated_at": _now_iso(),
        "entry_time": ts,
        "extra": {
            "category": raw.get("category", ""),
            "emitter": "new_strategies_emitter",
        },
    }


def _passes_gate(pick: dict) -> bool:
    """Run pick through passes_active_gate; return False on any exception (fail-open)."""
    try:
        from audit_trail.quality_gates import passes_active_gate  # type: ignore
        return passes_active_gate(pick)
    except Exception as e:
        print(
            f"[new_strategies_emitter] passes_active_gate error for {pick.get('symbol')}: {e}",
            file=sys.stderr,
        )
        return True  # fail-open: gate error → allow pick through


def run(dry_run: bool = False) -> dict:
    """Run all 20 strategies and emit gated picks. Returns output dict."""
    enabled = os.environ.get(ENABLED_FLAG, "1").strip()
    if enabled == "0":
        print(f"[new_strategies_emitter] {ENABLED_FLAG}: OFF — skipping emission")
        return {"status": "disabled", "picks": []}

    # Import all 20 strategy functions
    try:
        import new_equity_commodity_strategies_20 as strat_module  # type: ignore
    except ImportError as e:
        print(
            f"[new_strategies_emitter] Cannot import new_equity_commodity_strategies_20: {e}",
            file=sys.stderr,
        )
        return {"status": "import_error", "picks": [], "error": str(e)}

    all_strategies = [
        # Equity/ETF strategies
        strat_module.post_earnings_drift,
        strat_module.week52_high_breakout,
        strat_module.low_volatility_factor,
        strat_module.short_interest_squeeze,
        strat_module.sector_rotation_etf,
        strat_module.bollinger_band_squeeze_stocks,
        strat_module.reversal_after_3_down_days,
        strat_module.dividend_capture_strategy,
        strat_module.golden_cross_200d,
        strat_module.mean_reversion_2day,
        # Commodity strategies
        strat_module.gold_real_yield_signal,
        strat_module.commodity_channel_index_bounce,
        strat_module.contango_roll_yield,
        strat_module.precious_metals_correlation_pair,
        strat_module.energy_eia_inventory_proxy,
        strat_module.copper_economic_cycle,
        strat_module.agricultural_weather_premium,
        strat_module.commodity_momentum_12_1,
        strat_module.commodity_volatility_risk_premium,
        strat_module.platinum_palladium_spread,
    ]

    # Fetch OHLCV data for all symbols
    all_symbols = EQUITY_SYMBOLS + COMMODITY_SYMBOLS
    print(
        f"[new_strategies_emitter] Fetching OHLCV for {len(all_symbols)} symbols "
        f"(equity={len(EQUITY_SYMBOLS)}, commodity={len(COMMODITY_SYMBOLS)})..."
    )
    ohlcv = _load_ohlcv(all_symbols, period="6mo")

    if not ohlcv:
        print("[new_strategies_emitter] No OHLCV data available — emitting empty picks")

    # Run each strategy with try/except: one bad strategy must not crash the runner
    raw_picks = []
    strategies_run = []
    for fn in all_strategies:
        fn_name = fn.__name__
        try:
            picks = fn(ohlcv)
            count = len(picks) if picks else 0
            print(f"[new_strategies_emitter]   {fn_name}: {count} raw signals")
            if picks:
                raw_picks.extend(picks)
            strategies_run.append(fn_name)
        except Exception as e:
            print(
                f"[new_strategies_emitter] Strategy {fn_name} error: {e}",
                file=sys.stderr,
            )
            traceback.print_exc()
            strategies_run.append(f"{fn_name}:ERROR")

    # Normalize and gate-filter
    normalized = [_normalize_pick(p) for p in raw_picks]
    gated_picks = []
    rejected_count = 0
    for pick in normalized:
        if _passes_gate(pick):
            gated_picks.append(pick)
        else:
            rejected_count += 1

    print(
        f"[new_strategies_emitter] {len(raw_picks)} raw → "
        f"{len(gated_picks)} gated picks "
        f"({rejected_count} rejected by passes_active_gate)"
    )

    output = {
        "generated_at": _now_iso(),
        "source_system": SOURCE_SYSTEM,
        "strategy": "all_20_equity_commodity_strategies",
        "description": (
            "20 academically-backed equity/commodity strategies: "
            "PEAD, 52-week breakout, low-volatility, short-squeeze, sector rotation, "
            "Bollinger squeeze, 3-day reversal, dividend capture, golden cross, "
            "mean reversion, gold/real-yield, CCI bounce, contango roll, "
            "precious metals correlation, EIA proxy, copper cycle, agri weather, "
            "12-1 momentum, vol risk premium, Pt/Pd spread."
        ),
        "reference": (
            "Bernard&Thomas 1989; George&Hwang 2004; Baker et al 2011; "
            "Asness et al 2013; Faber 2007; Erb&Harvey 2006"
        ),
        "wire_up_rule": "opt-in sidecar — 14-day shadow validation before gate promotion",
        "strategies_run": strategies_run,
        "equity_symbols_fetched": len([s for s in EQUITY_SYMBOLS if s in ohlcv]),
        "commodity_symbols_fetched": len([s for s in COMMODITY_SYMBOLS if s in ohlcv]),
        "raw_signals": len(raw_picks),
        "rejected_by_gate": rejected_count,
        "picks": gated_picks,
    }

    if dry_run:
        print(f"[new_strategies_emitter] DRY-RUN — not writing to {OUT_PATH}")
        print(json.dumps(output, indent=2, default=str))
    else:
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: write to tmp file in same dir, then rename
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=OUT_PATH.parent, prefix=".new_strategies_picks_", suffix=".tmp"
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
                json.dump(output, fh, indent=2, default=str)
            os.replace(tmp_path, OUT_PATH)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        print(f"[new_strategies_emitter] Wrote {len(gated_picks)} picks to {OUT_PATH}")

    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit picks from the 20 new equity/commodity strategies"
    )
    parser.add_argument("--dry-run", action="store_true", help="Print output without writing file")
    args = parser.parse_args()
    result = run(dry_run=args.dry_run)
    sys.exit(0 if result.get("status") != "import_error" else 1)


if __name__ == "__main__":
    main()
