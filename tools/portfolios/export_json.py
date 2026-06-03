"""Export PF_* tables -> dashboard JSON (Phase 4).

Reads the live MySQL PF_* tables and writes:

  audit_dashboard/data/pf_portfolios.json
      Roster: one entry per portfolio with latest NAV + latest metrics.

  audit_dashboard/data/pf_portfolio_<portfolio_key>.json
      Per-portfolio detail: open + closed positions and the full NAV curve.

``generated_at`` is ISO-UTC (machine field; the dashboard renders EST itself).

SAFETY: defaults to --dry-run, which prints a sample of what WOULD be written
and writes NO files. Pass --write to actually emit the JSON files.

Usage:
    python tools/portfolios/export_json.py            # dry-run (prints sample)
    python tools/portfolios/export_json.py --write    # write JSON files

Env (same convention as tools/portfolios/init_db.py):
    DB_HOST_STOCKS / DB_USER_STOCKS / DB_PASS_STOCKS / DB_NAME_STOCKS
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# 2026-06-03 P0 fix (v2): inject repo root into sys.path so absolute imports
# resolve when this file is run as `python tools/portfolios/export_json.py`
# (the daily GHA workflow). v1 tried relative imports (`from .engine`) but
# those require `python -m tools.portfolios.export_json`; under direct script
# invocation the module has no parent package and raises
# `ImportError: attempted relative import with no known parent package`.
# This made the export step crash at module-load time, the FTP step then
# uploaded the previous (stale) JSON, and pf.html drill columns
# (Weight %, TP, Current $, Unrealized %) stayed blank on the live site.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.portfolios.engine import mark_position  # noqa: E402
from tools.portfolios.prices import get_close  # noqa: E402
DATA_DIR = REPO_ROOT / "audit_dashboard" / "data"


def _connect():
    import pymysql

    return pymysql.connect(
        host=os.environ.get("DB_HOST_STOCKS", "mysql.50webs.com"),
        user=os.environ.get("DB_USER_STOCKS", "ejaguiar1_stocks"),
        password=os.environ.get("DB_PASS_STOCKS", "stocks1234560"),
        database=os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"),
        port=3306, connect_timeout=20, cursorclass=pymysql.cursors.DictCursor,
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_key(key: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", key or "unknown")


def _jsonable(v):
    """Coerce DB types (Decimal, date/datetime, bytes) into JSON-safe values."""
    from datetime import date as _date

    if isinstance(v, (datetime, _date)):
        return v.isoformat()
    if isinstance(v, bytes):
        try:
            return v.decode()
        except Exception:  # noqa: BLE001
            return None
    try:
        import decimal

        if isinstance(v, decimal.Decimal):
            return float(v)
    except Exception:  # noqa: BLE001
        pass
    return v


def _row(d: dict) -> dict:
    return {k: _jsonable(v) for k, v in d.items()}


def _maybe_json(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:  # noqa: BLE001
            return v
    return v


def build_payloads(conn) -> tuple[dict, dict]:
    """Return (roster_payload, {portfolio_key: detail_payload})."""
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM PF_PORTFOLIO ORDER BY model_id, risk_appetite")
        portfolios = cur.fetchall()

    roster = []
    details: dict[str, dict] = {}

    for pf in portfolios:
        pid = pf["id"]
        key = pf["portfolio_key"]

        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM PF_NAV_SNAPSHOT WHERE portfolio_id=%s "
                "ORDER BY asof_date ASC", (pid,))
            navs = cur.fetchall()
            cur.execute(
                "SELECT * FROM PF_DAILY_METRICS WHERE portfolio_id=%s "
                "ORDER BY asof_date DESC LIMIT 1", (pid,))
            metrics_row = cur.fetchone()
            cur.execute(
                "SELECT * FROM PF_POSITION WHERE portfolio_id=%s "
                "ORDER BY status, entry_date DESC", (pid,))
            positions = cur.fetchall()

        # ── Mark-to-market open positions with live prices ──
        from tools.portfolios.engine import mark_position
        from tools.portfolios.prices import get_close

        for p in positions:
            entry = _jsonable(p.get("entry_price")) or 0.0
            p["entry_price"] = entry
            p["tp_price"] = _jsonable(p.get("tp_price"))
            p["sl_price"] = _jsonable(p.get("sl_price"))
            p["weight_pct"] = _jsonable(p.get("weight_at_entry"))  # pf.html reads weight_pct

            if p.get("status") != "open":
                continue

            sym = p.get("symbol", "")
            ac = p.get("asset_class", "CRYPTO")
            current = get_close(sym, ac)
            if current is None or current <= 0:
                continue

            qty = float(p.get("qty") or 0.0)
            if qty <= 0:
                continue

            marked = mark_position(p, current)
            p["current_price"] = current
            p["unrealized_pnl_pct"] = marked.get("unrealized_pnl_pct", 0.0)
            p["unrealized_pnl_usd"] = marked.get("unrealized_pnl_usd", 0.0)
            p["market_value_usd"] = marked.get("market_value_usd", 0.0)

        latest_nav = navs[-1] if navs else None
        metrics = _row(metrics_row) if metrics_row else {}
        if "exposure_by_class" in metrics:
            metrics["exposure_by_class"] = _maybe_json(metrics["exposure_by_class"])

        roster.append({
            "portfolio_key": key,
            "model_id": pf.get("model_id"),
            "risk_appetite": pf.get("risk_appetite"),
            "kind": pf.get("kind"),
            "status": pf.get("status"),
            "starting_nav": _jsonable(pf.get("starting_nav")),
            "latest_nav": _jsonable(latest_nav["nav_usd"]) if latest_nav else None,
            "latest_asof": _jsonable(latest_nav["asof_date"]) if latest_nav else None,
            "n_open": _jsonable(latest_nav["n_open"]) if latest_nav else 0,
            "gross_exposure_pct": _jsonable(latest_nav["gross_exposure_pct"]) if latest_nav else None,
            "total_return_pct": (
                (float(latest_nav["nav_usd"]) - float(pf["starting_nav"]))
                / float(pf["starting_nav"]) * 100.0
                if latest_nav and pf.get("starting_nav") else None),
            "sharpe_30d": metrics.get("sharpe_30d"),
            "max_dd": metrics.get("max_dd"),
            "pf_to_date": metrics.get("pf_to_date"),
            "wr_to_date": metrics.get("wr_to_date"),
        })

        details[key] = {
            "schema_version": 1,
            "generated_at": _now_iso(),
            "portfolio": _row(pf | {"config_snapshot": _maybe_json(pf.get("config_snapshot"))}),
            "nav_curve": [_row(n) for n in navs],
            "positions": [_row(p) for p in positions],
            "metrics_latest": metrics,
        }

    roster_payload = {
        "schema_version": 1,
        "generated_at": _now_iso(),
        "n_portfolios": len(roster),
        "portfolios": roster,
    }
    return roster_payload, details


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Export PF_* tables to dashboard JSON")
    ap.add_argument("--write", action="store_true",
                    help="write JSON files (default is dry-run: print sample only)")
    ap.add_argument("--dry-run", action="store_true", help="explicit dry-run")
    args = ap.parse_args(argv)
    write = args.write and not args.dry_run

    try:
        conn = _connect()
    except Exception as exc:  # noqa: BLE001
        print(f"::error title=export_json::DB connect failed: {exc}", file=sys.stderr)
        return 1

    try:
        roster, details = build_payloads(conn)
    finally:
        conn.close()

    print(f"[export_json] {roster['n_portfolios']} portfolio(s); "
          f"mode={'WRITE' if write else 'DRY-RUN'}")

    if not write:
        sample = dict(roster)
        sample["portfolios"] = roster["portfolios"][:3]
        print(json.dumps(sample, indent=2)[:2000])
        print(f"[export_json] DRY-RUN: would write pf_portfolios.json + "
              f"{len(details)} per-portfolio file(s). No files written.")
        return 0

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "pf_portfolios.json").write_text(json.dumps(roster, indent=2))
    print(f"[export_json] wrote {DATA_DIR / 'pf_portfolios.json'}")
    for key, payload in details.items():
        fname = DATA_DIR / f"pf_portfolio_{_safe_key(key)}.json"
        fname.write_text(json.dumps(payload, indent=2))
    print(f"[export_json] wrote {len(details)} per-portfolio file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
