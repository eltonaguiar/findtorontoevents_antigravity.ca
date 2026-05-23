"""
ETF Sector Rotation Emitter (production) — 2026-05-01
======================================================

Implements Faber Tactical Asset Allocation (10-month SMA filter + 3-month
sector momentum) across SPDR sector ETFs using the existing
`alpha_engine/etf_strategies::etf_sector_momentum` strategy.

Writes: alpha_engine/data/etf_sector_picks.json

Wire-Up Rule status: OPT-IN SIDECAR (registered in JSON_PICK_SOURCES).
  - Picks reach /audit on next dashboard rebuild after this emitter runs.
  - Wiring plan: JSON_PICK_SOURCES entry added in this PR → production.
  - Shadow-mode validation: operator should watch for 14 days before
    applying any gate promotion to etf_sector_rotation strategy.

Run:
    python tools/etf_sector_emitter.py [--dry-run]
    ETF_SECTOR_EMITTER_ENABLED=0 python tools/etf_sector_emitter.py  # skip
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "alpha_engine"))
sys.path.insert(0, str(ROOT))

OUT_PATH = ROOT / "alpha_engine" / "data" / "etf_sector_picks.json"
ENABLED_FLAG = "ETF_SECTOR_EMITTER_ENABLED"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_ohlcv(symbols: list[str], period: str = "1y") -> dict:
    """Download OHLCV data; return {symbol: DataFrame}. Fails gracefully."""
    try:
        import yfinance as yf
        import pandas as pd

        data = {}
        for sym in symbols:
            try:
                df = yf.download(sym, period=period, progress=False, auto_adjust=True)
                if df is not None and len(df) >= 50:
                    # yfinance >=0.2.x returns MultiIndex columns
                    # ([('Close','XLK'),...]); the strategies expect flat
                    # single-level OHLCV labels. Without this flatten,
                    # df["Close"] is a sub-DataFrame and etf_sector_momentum
                    # raises "truth value of a Series is ambiguous" — swallowed
                    # by the caller, producing 0 picks every run since 2026-05-01.
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    data[sym] = df
            except Exception as e:
                print(f"[etf_sector_emitter] yfinance fetch failed for {sym}: {e}", file=sys.stderr)
        return data
    except ImportError:
        print("[etf_sector_emitter] yfinance not available — returning empty dataset", file=sys.stderr)
        return {}


def _normalize_pick(raw: dict, source_system: str = "etf_all_strategies") -> dict:
    """Normalize etf_strategies output to the canonical pick schema."""
    symbol = raw.get("symbol", "UNKNOWN")
    entry = float(raw.get("entry_price", 0))
    tp = float(raw.get("take_profit", 0))
    sl = float(raw.get("stop_loss", 0))
    ts = raw.get("timestamp") or _now_iso()

    pick_id = f"{source_system}::{symbol}::{ts[:10]}"
    direction = "LONG" if raw.get("signal_type", "BUY") in ("BUY", "LONG") else "SHORT"

    return {
        "id": pick_id,
        "symbol": symbol,
        "strategy": raw.get("strategy", "etf_sector_momentum"),
        "source_system": source_system,
        "asset_class": "ETF",
        "signal_type": raw.get("signal_type", "BUY"),
        "direction": direction,
        "entry_price": round(entry, 4),
        "take_profit": round(tp, 4),
        "stop_loss": round(sl, 4),
        "confidence": float(raw.get("confidence", 0.6)),
        "risk_reward": float(raw.get("risk_reward", 0.0)),
        "reason": raw.get("reason", ""),
        "timeframe": "POSITION",
        "status": "OPEN",
        "timestamp": ts,
        "generated_at": _now_iso(),
        "extra": raw.get("extra", {}),
    }


def _check_vix_gate() -> tuple[bool, float | None]:
    """Return (gate_open, vix_value). gate_open=False means skip emission.

    Threshold: VIX<25 (ETF backtest: PF 3.22 / Sharpe 1.63 with VIX<25 vs
    PF 2.05 baseline per reports/etf_vix_regime_breakthrough_20260513.md).
    Fail-open: if VIX fetch fails, gate_open=True (permissive).
    Disable entirely with ETF_VIX_GATE_ENABLED=0.
    """
    if os.environ.get("ETF_VIX_GATE_ENABLED", "1").strip() == "0":
        return True, None
    threshold = float(os.environ.get("ETF_VIX_GATE_THRESHOLD", "25.0"))
    try:
        from audit_trail.vix_regime_gate import is_vix_above_threshold, get_cached_vix  # type: ignore
        vix = get_cached_vix()
        above = is_vix_above_threshold(threshold)
        return not above, vix
    except Exception as e:
        print(f"[etf_sector_emitter] VIX gate fetch failed (fail-open): {e}", file=sys.stderr)
        return True, None


def run(dry_run: bool = False) -> dict:
    """Run the ETF sector rotation emitter. Returns output dict."""
    enabled = os.environ.get(ENABLED_FLAG, "1").strip()
    if enabled == "0":
        print(f"[etf_sector_emitter] {ENABLED_FLAG}: OFF — skipping emission")
        return {"status": "disabled", "picks": []}

    gate_open, vix_val = _check_vix_gate()
    vix_str = f"{vix_val:.1f}" if vix_val is not None else "unknown"
    if not gate_open:
        threshold = float(os.environ.get("ETF_VIX_GATE_THRESHOLD", "25.0"))
        print(
            f"[etf_sector_emitter] VIX={vix_str} > {threshold} — "
            "high-vol regime gate engaged, skipping rotation picks"
        )
        return {"status": "vix_gate_engaged", "picks": [], "vix": vix_val, "threshold": threshold}
    print(f"[etf_sector_emitter] VIX={vix_str} — gate clear, proceeding with rotation")

    try:
        from etf_strategies import (  # type: ignore
            ETF_STRATEGIES,
            ETF_SYMBOLS,
        )
        from config import BOND_SYMBOLS  # type: ignore
    except ImportError as e:
        print(f"[etf_sector_emitter] Cannot import etf_strategies/config: {e}", file=sys.stderr)
        return {"status": "import_error", "picks": [], "error": str(e)}

    # Build combined symbol list: ETF_SYMBOLS + BOND_SYMBOLS needed by strategies.
    # etf_sector_momentum wants TLT + HYG (in BOND_SYMBOLS); etf_risk_parity_rotation
    # and etf_faber_tactical need TLT, IEF. Without fetching these, 2 of 7 wanted
    # symbols were silently missing and both strategies returned 0 picks.
    # etf_trend_following + etf_dual_momentum also benefit from the broader universe.
    combined_symbols: dict = {**ETF_SYMBOLS, **BOND_SYMBOLS}
    symbols = list(combined_symbols.keys())
    print(f"[etf_sector_emitter] Fetching OHLCV for {len(symbols)} symbols "
          f"(ETF={len(ETF_SYMBOLS)} + BOND={len(BOND_SYMBOLS)})...")
    ohlcv = _load_ohlcv(symbols, period="13mo")

    if not ohlcv:
        print("[etf_sector_emitter] No OHLCV data available — emitting empty picks")
        raw_picks = []
    else:
        raw_picks = []
        for strategy_name, strategy_fn in ETF_STRATEGIES.items():
            try:
                strategy_picks = strategy_fn(ohlcv)
                print(f"[etf_sector_emitter]   {strategy_name}: {len(strategy_picks)} picks")
                raw_picks.extend(strategy_picks)
            except Exception as e:
                print(
                    f"[etf_sector_emitter] Strategy {strategy_name} error: {e}",
                    file=sys.stderr,
                )
                traceback.print_exc()

    picks = [_normalize_pick(p) for p in raw_picks]
    print(f"[etf_sector_emitter] Generated {len(picks)} ETF picks across {len(ETF_STRATEGIES)} strategies")

    output = {
        "generated_at": _now_iso(),
        "source_system": "etf_all_strategies",
        "strategy": "multi_strategy_aggregate",
        "description": "All ETF strategies: Faber TAA / sector momentum / dual momentum / risk-parity / trend-following",
        "reference": "Faber 2007 TAA; Antonacci 2014 Dual Momentum; Kirby & Ostdiek 2012",
        "wire_up_rule": "opt-in sidecar — 14-day shadow validation before gate promotion",
        "strategies_run": list(ETF_STRATEGIES.keys()),
        "picks": picks,
    }

    if dry_run:
        print(f"[etf_sector_emitter] DRY-RUN — not writing to {OUT_PATH}")
        print(json.dumps(output, indent=2, default=str))
    else:
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUT_PATH.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
        print(f"[etf_sector_emitter] Wrote {len(picks)} picks to {OUT_PATH}")

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ETF Sector Rotation Emitter")
    parser.add_argument("--dry-run", action="store_true", help="Print output without writing")
    args = parser.parse_args()
    result = run(dry_run=args.dry_run)
    sys.exit(0 if result.get("status") != "import_error" else 1)
