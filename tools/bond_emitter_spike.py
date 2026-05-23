"""
Bond Emitter Spike (proof-of-concept) — 2026-04-22
===================================================

Goal: prove the wire-up path for BOND pick emission using the existing
FRED data pipe (alpha_engine/bond_data_fred.py).

Reads:
    - alpha_engine/bond_strategies.py  :: BOND_STRATEGIES
    - alpha_engine/bond_data_fred.py   :: fetch_bond_bundle (if available)
    - alpha_engine/config.py           :: BOND_SYMBOLS (fallback)

Writes (DRAFT — NOT ingested by dashboard):
    - alpha_engine/data/active_picks_bond_draft.json

Not production:
    * No TP/SL risk policy application
    * No quality-gate integration
    * Empty-array output is acceptable if FRED offline / no API key

Run:
    .venv/Scripts/python.exe tools/bond_emitter_spike.py
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALPHA = ROOT / "alpha_engine"
OUT = ALPHA / "data" / "active_picks_bond_draft.json"

sys.path.insert(0, str(ALPHA))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_strategies():
    try:
        from bond_strategies import BOND_STRATEGIES  # type: ignore
        return BOND_STRATEGIES
    except Exception as e:
        print(f"[bond_spike] could not import BOND_STRATEGIES: {e}", file=sys.stderr)
        return {}


def _load_symbols():
    try:
        from config import BOND_SYMBOLS  # type: ignore
        return BOND_SYMBOLS
    except Exception as e:
        print(f"[bond_spike] could not import BOND_SYMBOLS: {e}", file=sys.stderr)
        return {}


def _try_fetch_fred():
    """Use the existing FRED pipeline if available."""
    try:
        from bond_data_fred import fetch_bond_bundle  # type: ignore
        bundle = fetch_bond_bundle()
        if bundle:
            print(f"[bond_spike] FRED bundle keys={list(bundle.keys())[:8]}", file=sys.stderr)
            return bundle
    except Exception as e:
        print(f"[bond_spike] FRED fetch unavailable: {e}", file=sys.stderr)
    return {}


def _try_fetch_yf(symbols):
    """Fallback: yfinance for bond ETFs (TLT/HYG/etc.)."""
    try:
        import yfinance as yf  # type: ignore
    except Exception:
        return {}
    out = {}
    for sym in list(symbols)[:12]:
        try:
            df = yf.download(sym, period="1y", interval="1d", progress=False, auto_adjust=False)
            if df is not None and len(df) > 80:
                df = df.rename(columns=str.lower)
                out[sym] = df
        except Exception:
            continue
    return out


def run() -> dict:
    strategies = _load_strategies()
    symbols = _load_symbols()
    print(f"[bond_spike] strategies={len(strategies)} symbols={len(symbols)}", file=sys.stderr)

    # 2026-05-12: FRED is currently timing out on every series (10 min wasted
    # per run, all empty arrays). The previous detection `if not data` was
    # truthy for the post-timeout dict {DGS2:[], DGS10:[], ...} so the
    # yfinance fallback never fired and the 3 ETF-aware strategies received
    # empty data → emitted 0 picks. Two-part fix:
    #
    # 1. SKIP_FRED env var lets the workflow bypass the 10-min FRED retry
    #    loop entirely. Set in alpha-engine-bond.yml to recover the daily
    #    cron from its dead state until FRED reachability is restored.
    # 2. Empty-values detection treats {key: []} dicts as no-data so the
    #    yfinance fallback fires anyway when FRED returns no rows.
    skip_fred = os.environ.get("SKIP_FRED", "").strip().lower() in ("1", "true", "yes")
    if skip_fred:
        print("[bond_spike] SKIP_FRED set; jumping directly to yfinance fallback", file=sys.stderr)
        data = {}
    else:
        data = _try_fetch_fred()

    # Empty-values detection: FRED bundle can be a dict with all-empty lists
    # when every backend timed out. Treat that as no-data so yfinance fires.
    if isinstance(data, dict) and data and not any(data.values()):
        print(f"[bond_spike] FRED returned {len(data)} keys but all empty — "
              f"treating as no-data and falling back to yfinance", file=sys.stderr)
        data = {}

    if not data and symbols:
        data = _try_fetch_yf(symbols)
    if not data:
        print("[bond_spike] no data — draft will be empty (acceptable for spike)", file=sys.stderr)

    picks: list[dict] = []
    for name, strat_fn in strategies.items():
        try:
            raw = strat_fn(data) if callable(strat_fn) else []
            if not raw:
                continue
            for sig in raw:
                if isinstance(sig, dict):
                    sig.setdefault("asset_class", "BOND")
                    sig.setdefault("strategy", name)
                    sig.setdefault("source_system", "bond_emitter_spike")
                    sig.setdefault("emitted_at", _now_iso())
                    picks.append(sig)
        except Exception as e:
            print(f"[bond_spike] strategy {name} failed: {e}", file=sys.stderr)
            traceback.print_exc(limit=2)

    payload = {
        "generated_at": _now_iso(),
        "spike_version": "bond_emitter_spike_v1",
        "is_draft": True,
        "ingested_by_dashboard": False,
        "pick_count": len(picks),
        "picks": picks,
        "notes": [
            "Proof-of-concept for BOND emitter wire-up via FRED + yfinance fallback.",
            "NOT ingested by dashboard generator.",
            "Follow-up: schedule via .github/workflows/alpha-engine-bond.yml (daily cadence).",
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"[bond_spike] wrote {OUT} — picks={len(picks)}")
    return payload


if __name__ == "__main__":
    run()
