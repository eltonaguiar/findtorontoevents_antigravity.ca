"""
ETF Emitter Spike (proof-of-concept) — 2026-04-22
==================================================

Goal: prove the wire-up path for ETF pick emission.

Reads:
    - alpha_engine/etf_strategies.py :: ETF_STRATEGIES
    - alpha_engine/config.py         :: ETF_SYMBOLS

Writes (DRAFT — NOT ingested by dashboard):
    - alpha_engine/data/active_picks_etf_draft.json

This is explicitly NOT a production emitter:
    * No TP/SL risk policy application
    * No quality-gate integration
    * No HC-gate / feed-hygiene filtering
    * Empty-array output is acceptable if data source unavailable

Run:
    .venv/Scripts/python.exe tools/etf_emitter_spike.py
"""
from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALPHA = ROOT / "alpha_engine"
OUT = ALPHA / "data" / "active_picks_etf_draft.json"

# Make alpha_engine importable (mirrors how scanner.py is run)
sys.path.insert(0, str(ALPHA))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_strategies():
    try:
        from etf_strategies import ETF_STRATEGIES  # type: ignore
        return ETF_STRATEGIES
    except Exception as e:
        print(f"[etf_spike] could not import ETF_STRATEGIES: {e}", file=sys.stderr)
        return {}


def _load_symbols():
    try:
        from config import ETF_SYMBOLS  # type: ignore
        return ETF_SYMBOLS
    except Exception as e:
        print(f"[etf_spike] could not import ETF_SYMBOLS: {e}", file=sys.stderr)
        return {}


def _try_fetch_ohlc(symbols):
    """Best-effort yfinance fetch. Returns dict[sym] -> DataFrame or {}."""
    try:
        import yfinance as yf  # type: ignore
        import pandas as pd  # noqa: F401
    except Exception:
        print("[etf_spike] yfinance/pandas unavailable — emitting empty set", file=sys.stderr)
        return {}

    out = {}
    for sym in list(symbols)[:25]:  # cap to keep spike lightweight
        try:
            # 2y window: ETF strategies guard len(df) < 255 (dual_momentum
            # needs close.iloc[-252]) / < 210 (Faber 200d SMA). A 6mo fetch
            # (~126 bars) silently fails every strategy → picks=0.
            df = yf.download(sym, period="2y", interval="1d", progress=False, auto_adjust=False)
            if df is not None and len(df) > 60:
                # yfinance >=0.2.x returns MultiIndex columns — flatten to the
                # OHLCV level (capitalised: Close/High/Low/Volume). The ETF
                # strategies in etf_strategies.py index df["Close"] etc., so
                # keep the capitalised names — do NOT lower-case them.
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                out[sym] = df
        except Exception:
            continue
    return out


def run() -> dict:
    strategies = _load_strategies()
    symbols = _load_symbols()
    print(f"[etf_spike] strategies={len(strategies)} symbols={len(symbols)}", file=sys.stderr)

    picks: list[dict] = []

    data = _try_fetch_ohlc(symbols) if symbols else {}
    if not data:
        print("[etf_spike] no OHLC data — draft will be empty (acceptable for spike)", file=sys.stderr)

    for name, strat_fn in strategies.items():
        try:
            # Strategies in etf_strategies.py take dict[str, DataFrame] per convention
            raw = strat_fn(data) if callable(strat_fn) else []
            if not raw:
                continue
            for sig in raw:
                if isinstance(sig, dict):
                    sig.setdefault("asset_class", "ETF")
                    sig.setdefault("strategy", name)
                    sig.setdefault("source_system", "etf_emitter_spike")
                    sig.setdefault("emitted_at", _now_iso())
                    picks.append(sig)
        except Exception as e:
            print(f"[etf_spike] strategy {name} failed: {e}", file=sys.stderr)
            traceback.print_exc(limit=2)

    payload = {
        "generated_at": _now_iso(),
        "spike_version": "etf_emitter_spike_v1",
        "is_draft": True,
        "ingested_by_dashboard": False,
        "pick_count": len(picks),
        "picks": picks,
        "notes": [
            "Proof-of-concept for ETF emitter wire-up.",
            "NOT ingested by dashboard generator.",
            "Follow-up: schedule via .github/workflows/alpha-engine-etf.yml",
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"[etf_spike] wrote {OUT} — picks={len(picks)}")
    return payload


if __name__ == "__main__":
    run()
