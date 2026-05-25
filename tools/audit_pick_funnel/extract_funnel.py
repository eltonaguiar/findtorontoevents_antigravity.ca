"""
extract_funnel.py — Full pick-funnel visibility for /audit dashboard.

Pulls TODAY + 90-day picks from ejaguiar1_stocks.trading_picks and
at_signal_outcomes. For each pick captures the gates it passed/failed
(PROVEN / Smart / Verified-Alpha / High-Conviction per-class floors).

Also walks the scanned universe (equity + crypto + penny seeds) to find
symbols that did NOT produce a pick and emits the rejection reason.

Outputs:
  audit_dashboard/data/pick_funnel_today.json
  audit_dashboard/data/pick_funnel_90d.json
  audit_dashboard/data/pick_funnel_rejected_universe.json

Read-only on production tables. Paged queries with LIMIT/OFFSET; no SELECT *
without WHERE+LIMIT.

Usage:
  python3 tools/audit_pick_funnel/extract_funnel.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.audit_pick_funnel._db import connect_stocks  # noqa: E402

OUT_DIR = ROOT / "audit_dashboard" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Per-class score floors mirror audit_trail/quality_gates.py (FROZEN 2026-05-20)
SMART_FLOOR_BY_CLASS = {
    "CRYPTO": 60, "FOREX": 40, "COMMODITY": 30, "FUTURES": 45,
    "BOND": 60, "ETF": 55, "EQUITY": 60, "PENNY": 60, "INDEX": 55, "MEME": 60,
}
PROVEN_MIN_CONF = 0.60
HC_MIN_SCORE = 80      # High-conviction floor (mirrors hc_filter.js)
HC_MIN_CONF = 0.75
VERIFIED_ALPHA_MIN_SCORE = 70
BLOCKED_TRUST_TIERS = {"BANNED", "AVOID", "UNTRUSTED"}

PAGE = 5000
MAX_ROWS = 100_000


def _utc_iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_class(cat: Optional[str]) -> str:
    if not cat:
        return "UNKNOWN"
    c = cat.upper()
    aliases = {
        "STOCK": "EQUITY", "STOCKS": "EQUITY",
        "PENNYSTOCK": "PENNY", "PENNYSTOCKS": "PENNY",
    }
    return aliases.get(c, c)


def _classify_status(status: Optional[str]) -> str:
    if not status:
        return "UNKNOWN"
    s = status.upper()
    if s in {"ACTIVE", "OPEN", "SIGNAL"}:
        return "ACTIVE"
    if s in {"WON", "WIN", "TP_HIT", "CLOSED_TP"}:
        return "WIN"
    if s in {"LOST", "LOSS", "SL_HIT", "CLOSED_SL"}:
        return "LOSS"
    if s in {"CLOSED", "FLAT", "TIME_EXIT", "EXPIRED", "STALE"}:
        return "CLOSED_FLAT"
    return s


def evaluate_gates(pick: Dict[str, Any]) -> Dict[str, Any]:
    """Mirror the production gate decisions. Returns dict of gate→bool + reason."""
    asset_class = _normalize_class(pick.get("category"))
    score = pick.get("elite_score") or 0
    trust = pick.get("trust_score") or 0
    conf = float(pick.get("confidence") or 0.0)

    smart_floor = SMART_FLOOR_BY_CLASS.get(asset_class, 60)

    passed_smart_score = score >= smart_floor
    passed_smart_conf = conf >= PROVEN_MIN_CONF
    passed_smart = passed_smart_score and passed_smart_conf

    passed_va = score >= VERIFIED_ALPHA_MIN_SCORE
    passed_hc = (score >= HC_MIN_SCORE) and (conf >= HC_MIN_CONF) and (trust >= 60)
    passed_proven = (score >= 70) and (conf >= 0.70) and (trust >= 70)

    # Reason for first failure (drill-down for rejected-universe view)
    fail_reason = None
    if not passed_smart_score:
        fail_reason = f"SCORE<{smart_floor} (got {score})"
    elif not passed_smart_conf:
        fail_reason = f"CONF<{PROVEN_MIN_CONF} (got {conf:.2f})"
    elif not passed_va:
        fail_reason = "below VERIFIED_ALPHA floor"
    elif not passed_hc:
        fail_reason = "below HIGH_CONVICTION floor"
    elif not passed_proven:
        fail_reason = "below PROVEN floor"

    return {
        "asset_class": asset_class,
        "smart_floor": smart_floor,
        "passed_smart": passed_smart,
        "passed_verified_alpha": passed_va,
        "passed_high_conviction": passed_hc,
        "passed_proven": passed_proven,
        "first_fail_reason": fail_reason,
    }


def fetch_picks(conn, days: int) -> List[Dict[str, Any]]:
    """Paged read of trading_picks for the last N days."""
    rows: List[Dict[str, Any]] = []
    offset = 0
    where = "WHERE created_at >= NOW() - INTERVAL %s DAY"
    cols = (
        "id, symbol, direction, strategy, entry_price, take_profit, stop_loss, "
        "confidence, elite_score, trust_score, category, source_system, status, "
        "pnl_pct, exit_price, created_at, closed_at, exit_reason"
    )
    while len(rows) < MAX_ROWS:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {cols} FROM trading_picks {where} "
                f"ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (days, PAGE, offset),
            )
            batch = cur.fetchall()
        if not batch:
            break
        rows.extend(batch)
        offset += PAGE
        if len(batch) < PAGE:
            break
    return rows


def fetch_outcomes(conn, days: int) -> List[Dict[str, Any]]:
    """Resolved at_signal_outcomes — joined client-side by symbol+strategy."""
    rows: List[Dict[str, Any]] = []
    offset = 0
    while len(rows) < MAX_ROWS:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, symbol, direction, strategy, asset_class, outcome, "
                "pnl_pct, source_system, opened_at, closed_at "
                "FROM at_signal_outcomes "
                "WHERE COALESCE(closed_at, opened_at) >= NOW() - INTERVAL %s DAY "
                "ORDER BY closed_at DESC LIMIT %s OFFSET %s",
                (days, PAGE, offset),
            )
            batch = cur.fetchall()
        if not batch:
            break
        rows.extend(batch)
        offset += PAGE
        if len(batch) < PAGE:
            break
    return rows


def build_funnel(picks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate per-class funnel counts."""
    funnel: Dict[str, Dict[str, int]] = {}
    for p in picks:
        g = evaluate_gates(p)
        ac = g["asset_class"]
        bucket = funnel.setdefault(ac, {
            "scanned": 0, "passed_smart": 0, "passed_verified_alpha": 0,
            "passed_high_conviction": 0, "passed_proven": 0,
            "opened": 0, "closed": 0, "win": 0, "loss": 0,
        })
        bucket["scanned"] += 1
        if g["passed_smart"]:
            bucket["passed_smart"] += 1
        if g["passed_verified_alpha"]:
            bucket["passed_verified_alpha"] += 1
        if g["passed_high_conviction"]:
            bucket["passed_high_conviction"] += 1
        if g["passed_proven"]:
            bucket["passed_proven"] += 1
        st = _classify_status(p.get("status"))
        if st == "ACTIVE":
            bucket["opened"] += 1
        elif st in {"WIN", "LOSS", "CLOSED_FLAT"}:
            bucket["closed"] += 1
            if st == "WIN":
                bucket["win"] += 1
            elif st == "LOSS":
                bucket["loss"] += 1
    # Add derived stats — WR uses only decisive (WIN+LOSS), excluding flat/expired
    for ac, b in funnel.items():
        decisive = b["win"] + b["loss"]
        b["decisive"] = decisive
        b["wr_pct"] = round(100.0 * b["win"] / decisive, 2) if decisive else None
    return funnel


def serialize_pick(p: Dict[str, Any]) -> Dict[str, Any]:
    g = evaluate_gates(p)
    return {
        "pick_id": p.get("id"),
        "symbol": p.get("symbol"),
        "direction": p.get("direction"),
        "strategy": p.get("strategy"),
        "source_system": p.get("source_system"),
        "asset_class": g["asset_class"],
        "entry": float(p["entry_price"]) if p.get("entry_price") is not None else None,
        "tp": float(p["take_profit"]) if p.get("take_profit") is not None else None,
        "sl": float(p["stop_loss"]) if p.get("stop_loss") is not None else None,
        "confidence": float(p["confidence"]) if p.get("confidence") is not None else None,
        "elite_score": p.get("elite_score"),
        "trust_score": p.get("trust_score"),
        "status": p.get("status"),
        "status_class": _classify_status(p.get("status")),
        "pnl_pct": float(p["pnl_pct"]) if p.get("pnl_pct") is not None else None,
        "exit_price": float(p["exit_price"]) if p.get("exit_price") is not None else None,
        "exit_reason": p.get("exit_reason"),
        "created_at": _utc_iso(p.get("created_at")),
        "closed_at": _utc_iso(p.get("closed_at")),
        "gates": {
            "smart": g["passed_smart"],
            "verified_alpha": g["passed_verified_alpha"],
            "high_conviction": g["passed_high_conviction"],
            "proven": g["passed_proven"],
            "first_fail_reason": g["first_fail_reason"],
            "smart_floor": g["smart_floor"],
        },
    }


def load_universe() -> Dict[str, List[str]]:
    """Load scanned universes for rejection-walk. Soft-fail per source."""
    universe: Dict[str, List[str]] = {}
    eq = ROOT / "config" / "equity_universe.csv"
    if eq.exists():
        try:
            with eq.open() as f:
                rdr = csv.reader(f)
                syms = [row[0].strip().upper() for row in rdr if row and row[0].strip() and not row[0].startswith("#")]
            universe["EQUITY"] = sorted(set(syms))
        except Exception:
            pass
    penny = ROOT / "data" / "penny_universe_seed.json"
    if penny.exists():
        try:
            data = json.loads(penny.read_text())
            if isinstance(data, list):
                universe["PENNY"] = sorted({str(x).upper() for x in data})
            elif isinstance(data, dict):
                syms = data.get("symbols") or data.get("universe") or list(data.keys())
                universe["PENNY"] = sorted({str(x).upper() for x in syms})
        except Exception:
            pass
    return universe


def build_rejected_universe(
    universe: Dict[str, List[str]],
    picks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """For each class, list symbols in the universe that produced NO pick today,
    plus picks that DID produce but failed the smart gate (gate-rejected)."""
    today_syms_by_class: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for p in picks:
        g = evaluate_gates(p)
        ac = g["asset_class"]
        sym = (p.get("symbol") or "").upper()
        if not sym:
            continue
        existing = today_syms_by_class.setdefault(ac, {}).get(sym)
        # Keep the best-scored row per symbol (best chance of passing)
        if (existing is None) or ((p.get("elite_score") or 0) > (existing.get("elite_score") or 0)):
            today_syms_by_class[ac][sym] = {
                "elite_score": p.get("elite_score"),
                "confidence": float(p.get("confidence") or 0),
                "first_fail_reason": g["first_fail_reason"],
                "passed_smart": g["passed_smart"],
            }

    out: Dict[str, Any] = {}
    for ac, syms in universe.items():
        seen = today_syms_by_class.get(ac, {})
        not_scanned = [s for s in syms if s not in seen]
        gate_rejected = [
            {"symbol": s, **v} for s, v in seen.items() if not v["passed_smart"]
        ]
        out[ac] = {
            "universe_size": len(syms),
            "scanned_today": len(seen),
            "not_scanned_count": len(not_scanned),
            "not_scanned_sample": not_scanned[:50],
            "gate_rejected_count": len(gate_rejected),
            "gate_rejected_sample": sorted(
                gate_rejected, key=lambda r: -(r.get("elite_score") or 0)
            )[:50],
        }
    return out


def main() -> int:
    conn = connect_stocks()
    try:
        print("[funnel] fetching last 90 days picks...", flush=True)
        picks_90 = fetch_picks(conn, 90)
        print(f"[funnel]  -> {len(picks_90)} rows", flush=True)

        print("[funnel] fetching last 24h picks...", flush=True)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        picks_today = [
            p for p in picks_90
            if p.get("created_at") and (
                (p["created_at"].replace(tzinfo=timezone.utc) if p["created_at"].tzinfo is None else p["created_at"]) >= cutoff
            )
        ]
        print(f"[funnel]  -> {len(picks_today)} rows", flush=True)

        print("[funnel] fetching at_signal_outcomes (context)...", flush=True)
        outcomes_90 = fetch_outcomes(conn, 90)
        print(f"[funnel]  -> {len(outcomes_90)} outcomes", flush=True)
    finally:
        conn.close()

    today_payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_hours": 24,
        "n_picks": len(picks_today),
        "funnel_by_class": build_funnel(picks_today),
        "picks": [serialize_pick(p) for p in picks_today],
    }
    out_today = OUT_DIR / "pick_funnel_today.json"
    out_today.write_text(json.dumps(today_payload, indent=2, default=str))
    print(f"[funnel] wrote {out_today}")

    funnel_90 = build_funnel(picks_90)
    payload_90 = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": 90,
        "n_picks": len(picks_90),
        "n_outcomes": len(outcomes_90),
        "funnel_by_class": funnel_90,
        # Sample only — JSON would be huge otherwise (45k+ picks)
        "picks_sample": [serialize_pick(p) for p in picks_90[:1000]],
    }
    out_90 = OUT_DIR / "pick_funnel_90d.json"
    out_90.write_text(json.dumps(payload_90, indent=2, default=str))
    print(f"[funnel] wrote {out_90}")

    universe = load_universe()
    rej_payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "universe_sources": {
            "EQUITY": "config/equity_universe.csv",
            "PENNY": "data/penny_universe_seed.json",
        },
        "by_class": build_rejected_universe(universe, picks_today),
        "notes": "Crypto/forex/commodity/bond universes are dynamic — see "
                 "alpha_engine/universe_expander.py. Listed classes use static seeds.",
    }
    out_rej = OUT_DIR / "pick_funnel_rejected_universe.json"
    out_rej.write_text(json.dumps(rej_payload, indent=2, default=str))
    print(f"[funnel] wrote {out_rej}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
