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
CANON_PATH = REPO / "alpha_engine" / "data" / "feature_signals.json"


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


# ── MySQL persistent storage ──────────────────────────────────────────────
# MASTERPLAN Phase 2: write feature signals to MySQL for dashboard integration
# and historical tracking. Gated by FEATURE_SIGNALS_MYSQL_ENABLED env var.

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS feature_signals (
    signal_id       VARCHAR(150) PRIMARY KEY,
    symbol          VARCHAR(20),
    direction       VARCHAR(10),
    strategy        VARCHAR(100),
    sleeve          VARCHAR(50),
    asset_class     VARCHAR(20),
    entry_price     DECIMAL(20,8),
    take_profit     DECIMAL(20,8),
    stop_loss       DECIMAL(20,8),
    confidence      DECIMAL(5,4),
    reason          TEXT,
    status          VARCHAR(20) DEFAULT 'OPEN',
    source_system   VARCHAR(50) DEFAULT 'feature_signals',
    feature_type    VARCHAR(50),
    generated_at    DATETIME,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_fs_symbol    (symbol),
    INDEX idx_fs_sleeve    (sleeve),
    INDEX idx_fs_generated (generated_at),
    INDEX idx_fs_status    (status),
    INDEX idx_fs_asset     (asset_class)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

UPSERT_SQL = """
INSERT INTO feature_signals
    (signal_id, symbol, direction, strategy, sleeve, asset_class,
     entry_price, take_profit, stop_loss, confidence, reason,
     status, source_system, feature_type, generated_at)
VALUES
    (%(signal_id)s, %(symbol)s, %(direction)s, %(strategy)s, %(sleeve)s,
     %(asset_class)s, %(entry_price)s, %(take_profit)s, %(stop_loss)s,
     %(confidence)s, %(reason)s, %(status)s, %(source_system)s,
     %(feature_type)s, %(generated_at)s)
ON DUPLICATE KEY UPDATE
    direction     = VALUES(direction),
    entry_price   = VALUES(entry_price),
    take_profit   = VALUES(take_profit),
    stop_loss     = VALUES(stop_loss),
    confidence    = VALUES(confidence),
    reason        = VALUES(reason),
    status        = VALUES(status),
    generated_at  = VALUES(generated_at)
"""


def _get_mysql_password() -> str:
    """Resolve MySQL password from env vars (same pattern as mysql_trading_sync)."""
    for key in ("DB_PASS", "DB_PASS_STOCKS", "AUDIT_DB_PASS", "MYSQL_PASSWORD"):
        v = os.environ.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return "stocks"


def _write_to_mysql(payload: dict[str, Any]) -> int:
    """Upsert feature signals into ejaguiar1_stocks.feature_signals.

    Gated by FEATURE_SIGNALS_MYSQL_ENABLED env var (default "1").
    Returns number of rows written/updated.
    """
    if os.environ.get("FEATURE_SIGNALS_MYSQL_ENABLED", "1").lower() not in (
        "1", "true", "yes", "on"
    ):
        print("  [MYSQL] FEATURE_SIGNALS_MYSQL_ENABLED is off — skipping")
        return 0

    try:
        import pymysql
    except ImportError:
        print("  [MYSQL] pymysql not installed — skipping")
        return 0

    host = os.environ.get("DB_HOST", "mysql.50webs.com")
    port = int(os.environ.get("DB_PORT", "3306"))
    user = os.environ.get("DB_USER", "ejaguiar1_stocks")
    password = _get_mysql_password()
    database = os.environ.get("DB_NAME", "ejaguiar1_stocks")

    picks = payload.get("picks", [])
    if not picks:
        return 0

    generated_at = payload.get("generated_at", "")
    # Normalize generated_at to MySQL DATETIME format
    gen_dt = None
    if generated_at:
        try:
            gen_dt = generated_at.replace("T", " ").replace("Z", "")[:19]
        except Exception:
            pass

    written = 0
    try:
        conn = pymysql.connect(
            host=host, port=port, user=user, password=password,
            database=database, charset="utf8mb4", autocommit=True,
            connect_timeout=15, read_timeout=30, write_timeout=30,
        )
        with conn.cursor() as cur:
            # Ensure table exists
            cur.execute(CREATE_TABLE_SQL)

            for pick in picks:
                try:
                    signal_id = str(pick.get("id", ""))[:150]
                    if not signal_id:
                        continue
                    params = {
                        "signal_id": signal_id,
                        "symbol": str(pick.get("symbol", ""))[:20],
                        "direction": str(pick.get("direction", ""))[:10],
                        "strategy": str(pick.get("strategy", ""))[:100],
                        "sleeve": str(pick.get("_feature_signal_sleeve", ""))[:50],
                        "asset_class": str(pick.get("asset_class", "UNKNOWN"))[:20],
                        "entry_price": _safe_float(pick.get("entry_price")),
                        "take_profit": _safe_float(pick.get("take_profit")),
                        "stop_loss": _safe_float(pick.get("stop_loss")),
                        "confidence": _safe_float(pick.get("confidence")),
                        "reason": str(pick.get("reason", ""))[:500],
                        "status": str(pick.get("status", "OPEN"))[:20],
                        "source_system": str(pick.get("source_system", "feature_signals"))[:50],
                        "feature_type": str(pick.get("feature_type", ""))[:50],
                        "generated_at": gen_dt,
                    }
                    cur.execute(UPSERT_SQL, params)
                    written += 1
                except Exception as e:
                    print(f"  [MYSQL] upsert failed for {pick.get('symbol', '?')}: {e}")

        conn.close()
    except Exception as e:
        print(f"  [MYSQL] connection error: {e}")
        return 0

    return written


def _safe_float(val) -> float | None:
    """Convert to finite float or None for MySQL-safe inserts."""
    import math
    if val is None or val == "":
        return None
    try:
        f = float(val)
    except (ValueError, TypeError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-funding", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                     help="Emit signals but do not write to JSON or MySQL")
    args = ap.parse_args(argv)
    payload = emit_all(include_funding=not args.no_funding)

    picks = payload.get("picks", [])
    sleeve_counts = payload.get("sleeve_counts", {})
    errors = payload.get("errors", {})

    print(f"Feature Signals Orchestrator — {payload['generated_at']}")
    print(f"  Sleeves: {sleeve_counts}")
    if errors:
        print(f"  Errors:  {list(errors.keys())}")
    print(f"  Total picks: {len(picks)}")

    for p in picks:
        arrow = "^" if p.get("direction") == "LONG" else "v"
        print(f"    {arrow} {p.get('symbol','?'):<14} {p.get('direction','?'):<6} "
              f"conf={p.get('confidence',0):.0%}  {p.get('strategy','?')}")

    if args.dry_run:
        print(f"  [DRY RUN] Would write {len(picks)} picks to JSON + MySQL")
        return 0

    # Write JSON outputs (both dashboard and production scanner paths)
    for out_path in (OUT_PATH, CANON_PATH):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"  Written to: {OUT_PATH}")
    print(f"  Written to: {CANON_PATH}")

    # Write to MySQL
    mysql_written = _write_to_mysql(payload)
    if mysql_written:
        print(f"  [MYSQL] Upserted {mysql_written} signals to feature_signals table")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())