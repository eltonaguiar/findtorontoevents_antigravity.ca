#!/usr/bin/env python3
"""Aggregate non-LLM feature signals into pick-shaped dicts.

Emitters (no LLM):
  - funding_rate_extreme (Binance perp funding)
  - vix_regime_overlay (VIX level → defensive/offensive bias pick)
  - commodity_momentum (CL=F / NG=F short-horizon trend)

Writes: audit_dashboard/data/feature_signals_latest.json
Wired: alpha_engine/production_scanner.py when FEATURE_SIGNALS_ENABLED=1 (default ON).

Usage:
    python3 -m tools.feature_signals.orchestrator
    python3 -m tools.feature_signals.orchestrator --no-funding
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

OUT_PATH = REPO / "audit_dashboard" / "data" / "feature_signals_latest.json"


def _stamp(pick: dict[str, Any], sleeve: str) -> dict[str, Any]:
    pick = dict(pick)
    pick.setdefault("source_system", "feature_signals")
    pick.setdefault("strategy", sleeve)
    pick["asset_class"] = str(
        pick.get("asset_class") or pick.get("category") or "UNKNOWN"
    ).upper()
    if pick["asset_class"] == "CRYPTO" or str(pick.get("category", "")).lower() == "crypto":
        pick["asset_class"] = "CRYPTO"
        pick["category"] = "crypto"
    pick["_feature_signal_sleeve"] = sleeve
    pick["forward_validated"] = False
    return pick


def emit_funding_picks(max_picks: int = 8) -> list[dict[str, Any]]:
    """Reuse alpha_engine funding_rate_arb scanner."""
    try:
        from alpha_engine.funding_rate_arb import scan_funding_rate_arb
        raw = scan_funding_rate_arb(verbose=False) or []
    except Exception as exc:
        return [{"_error": f"funding_rate_arb: {exc}"}]
    out = []
    for p in raw[:max_picks]:
        if not isinstance(p, dict) or not p.get("symbol"):
            continue
        p = _stamp(p, "funding_rate_extreme")
        p["asset_class"] = "CRYPTO"
        out.append(p)
    return out


def emit_vix_regime_picks() -> list[dict[str, Any]]:
    """Single regime advisory pick for ETF overlay (not full rotator backtest)."""
    try:
        from audit_trail.vix_regime_gate import get_cached_vix
    except Exception as exc:
        return [{"_error": f"vix_regime_gate: {exc}"}]

    vix = get_cached_vix()
    if vix is None:
        return []

    if vix >= 28:
        direction, symbol, thesis = "SHORT", "SPY", f"VIX elevated {vix:.1f} — defensive"
        asset = "ETF"
    elif vix <= 16:
        direction, symbol, thesis = "LONG", "QQQ", f"VIX calm {vix:.1f} — risk-on"
        asset = "ETF"
    else:
        return []

    now = datetime.now(timezone.utc).isoformat()
    return [_stamp({
        "id": f"feature_vix_regime::{symbol}::{now[:10]}",
        "symbol": symbol,
        "direction": direction,
        "entry_price": 0.0,
        "status": "OPEN",
        "confidence": 0.62,
        "reason": thesis,
        "category": "etf",
        "asset_class": asset,
    }, "vix_regime_overlay")]


def emit_commodity_momentum_picks() -> list[dict[str, Any]]:
    """Simple 20d momentum on front-month energy futures via yfinance."""
    try:
        import yfinance as yf
    except ImportError as exc:
        return [{"_error": f"yfinance: {exc}"}]

    specs = [
        ("CL=F", "COMMODITY", "WTI crude"),
        ("NG=F", "COMMODITY", "Natural gas"),
    ]
    out: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()
    for sym, ac, label in specs:
        try:
            hist = yf.Ticker(sym).history(period="30d", interval="1d", auto_adjust=True)
            if hist is None or len(hist) < 22:
                continue
            close = hist["Close"]
            ret = float(close.iloc[-1] / close.iloc[-21] - 1.0)
            if abs(ret) < 0.03:
                continue
            direction = "LONG" if ret > 0 else "SHORT"
            entry = float(close.iloc[-1])
            out.append(_stamp({
                "id": f"feature_commodity_mom::{sym}::{now[:10]}",
                "symbol": sym,
                "direction": direction,
                "entry_price": round(entry, 4),
                "take_profit": round(entry * (1.02 if direction == "LONG" else 0.98), 4),
                "stop_loss": round(entry * (0.99 if direction == "LONG" else 1.01), 4),
                "status": "OPEN",
                "confidence": min(0.75, 0.55 + abs(ret) * 2),
                "reason": f"{label} 20d mom {ret*100:+.1f}%",
                "category": "commodity",
                "asset_class": ac,
            }, "commodity_momentum"))
        except Exception:
            continue
    return out


def emit_all(*, include_funding: bool = True) -> dict[str, Any]:
    sleeves: dict[str, list] = {}
    if include_funding:
        sleeves["funding_rate_extreme"] = emit_funding_picks()
    sleeves["vix_regime_overlay"] = emit_vix_regime_picks()
    sleeves["commodity_momentum"] = emit_commodity_momentum_picks()

    picks: list[dict[str, Any]] = []
    for name, rows in sleeves.items():
        for r in rows:
            if "_error" not in r and r.get("symbol"):
                picks.append(r)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "enabled": os.environ.get("FEATURE_SIGNALS_ENABLED", "1"),
        "sleeve_counts": {k: len([x for x in v if "_error" not in x]) for k, v in sleeves.items()},
        "errors": {k: v for k, v in sleeves.items() if v and "_error" in v[0]},
        "picks": picks,
    }


def merge_feature_signals(active: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Append feature-signal picks to the active list (dedupe by symbol+strategy)."""
    if os.environ.get("FEATURE_SIGNALS_ENABLED", "1") not in ("1", "true", "TRUE", "yes"):
        return active

    path = OUT_PATH
    if os.environ.get("FEATURE_SIGNALS_REFRESH", "0") in ("1", "true", "yes"):
        payload = emit_all()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    elif path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = emit_all()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    keys = {
        (str(p.get("symbol", "")).upper(), str(p.get("strategy", "")).lower())
        for p in active
    }
    merged = list(active)
    added = 0
    for p in payload.get("picks") or []:
        key = (str(p.get("symbol", "")).upper(), str(p.get("strategy", "")).lower())
        if key in keys or not p.get("symbol"):
            continue
        keys.add(key)
        merged.append(p)
        added += 1
    if added:
        print(f"  [FEATURE SIGNALS] merged {added} non-LLM picks from {path.name}")
    return merged


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-funding", action="store_true")
    args = ap.parse_args(argv)
    payload = emit_all(include_funding=not args.no_funding)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH} picks={len(payload.get('picks', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())