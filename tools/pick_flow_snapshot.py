#!/usr/bin/env python3
"""pick_flow_snapshot.py — one-shot DB query → committed JSON snapshot.

Runs inside CI (which has DB access). Queries at_raw_picks, at_filter_log,
at_consensus_picks for the last 24h, applies passes_hedge_fund_gate() to CRYPTO
picks, and writes a per-asset-class funnel JSON to reports/pick_flow_snapshot.json.

The snapshot is committed alongside the dashboard payload so it's readable
from the repo after every CI cycle.

Usage:
    python tools/pick_flow_snapshot.py                # last 24h
    python tools/pick_flow_snapshot.py --days 7       # custom window

Credentials: env AUDIT_DB_HOST / AUDIT_DB_USER / AUDIT_DB_PASS
(falls back to DB_STOCKS_HOST / DB_STOCKS_USER / DB_PASS_STOCKS).
"""
import argparse
import datetime as dt
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Ensure repo root is on sys.path so alpha_engine imports work in CI
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    sys.exit("pip install pymysql")


def _db_connect():
    """Connect using the env vars the CI already sets."""
    host = os.getenv("AUDIT_DB_HOST") or os.getenv("DB_STOCKS_HOST", "mysql.50webs.com")
    user = os.getenv("AUDIT_DB_USER") or os.getenv("DB_STOCKS_USER", "ejaguiar1_stocks")
    pw = os.getenv("AUDIT_DB_PASS") or os.getenv("DB_PASS_STOCKS") or os.getenv("DB_STOCKS_PASSWORD", "")
    db = os.getenv("AUDIT_DB_NAME") or os.getenv("DB_STOCKS_NAME", "ejaguiar1_stocks")

    return pymysql.connect(
        host=host, user=user, password=pw, database=db,
        connect_timeout=30, cursorclass=DictCursor,
    )


# ---------------------------------------------------------------------------
#  DB queries (same logic as pick_flow_funnel.py live mode)
# ---------------------------------------------------------------------------

def _query_raw_emitted(cur, since: str, until: str) -> dict[str, int]:
    cur.execute(
        "SELECT COALESCE(NULLIF(asset_class,''),'UNKNOWN') ac, COUNT(*) n "
        "FROM at_raw_picks WHERE DATE(recorded_at) BETWEEN %s AND %s GROUP BY ac",
        (since, until),
    )
    return {r["ac"]: r["n"] for r in cur.fetchall()}


def _query_gate_rejections(cur, since: str, until: str) -> dict[str, dict]:
    """Return {asset_class: {count: n, top_reason: str}}."""
    cur.execute(
        "SELECT COALESCE(NULLIF(asset_class,''),'UNKNOWN') ac, COUNT(*) n, "
        "SUBSTRING_INDEX(GROUP_CONCAT(filter_reason ORDER BY 1),',',1) tr "
        "FROM at_filter_log WHERE DATE(created_at) BETWEEN %s AND %s GROUP BY ac",
        (since, until),
    )
    out = {}
    for r in cur.fetchall():
        out[r["ac"]] = {"count": r["n"], "top_reason": r["tr"]}
    return out


def _query_consensus_survivors(cur, since: str, until: str) -> dict[str, int]:
    cur.execute(
        "SELECT COALESCE(NULLIF(asset_class,''),'UNKNOWN') ac, COUNT(*) n "
        "FROM at_consensus_picks WHERE DATE(generated_at) BETWEEN %s AND %s GROUP BY ac",
        (since, until),
    )
    return {r["ac"]: r["n"] for r in cur.fetchall()}


def _query_closed_with_pnl(cur, since: str, until: str) -> dict[str, dict]:
    """Return {asset_class: {closed: int, wins: int, gross_win: float, gross_loss: float}}."""
    cur.execute(
        "SELECT COALESCE(NULLIF(asset_class,''),'UNKNOWN') ac, COUNT(*) n, "
        "SUM(pnl_pct>0) wins, "
        "SUM(CASE WHEN pnl_pct>0 THEN pnl_pct ELSE 0 END) gw, "
        "ABS(SUM(CASE WHEN pnl_pct<=0 THEN pnl_pct ELSE 0 END)) gl "
        "FROM at_raw_picks WHERE DATE(closed_at) BETWEEN %s AND %s "
        "AND pnl_pct IS NOT NULL GROUP BY ac",
        (since, until),
    )
    out = {}
    for r in cur.fetchall():
        out[r["ac"]] = {
            "closed": r["n"],
            "wins": r["wins"],
            "gross_win": float(r["gw"] or 0),
            "gross_loss": float(r["gl"] or 0),
        }
    return out


def _query_active_by_source(cur, asset_class: str) -> list[dict]:
    """Fetch active OPEN picks for HF-gate simulation (up to 5000).
    Only selects columns the gate actually inspects: symbol, source_system,
    strategy, asset_class, direction, confidence (plus id for traceability)."""
    cur.execute(
        "SELECT id, symbol, source_system, strategy, asset_class, direction, confidence "
        "FROM at_raw_picks WHERE asset_class=%s AND status='OPEN' "
        "ORDER BY recorded_at DESC LIMIT 5000",
        (asset_class,),
    )
    return cur.fetchall()


def _query_equity_sources_30d(cur) -> list[dict]:
    """Return all EQUITY source_system values + raw pick counts from last 30 days.
    Used to cross-reference the EQUITY_BANNED_SOURCES frozenset against actual
    emitters — names may differ from what the forward-test audit identified."""
    cur.execute(
        "SELECT source_system, COUNT(*) n "
        "FROM at_raw_picks WHERE asset_class='EQUITY' "
        "AND DATE(recorded_at) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) "
        "GROUP BY source_system ORDER BY n DESC"
    )
    return cur.fetchall()


# ---------------------------------------------------------------------------
#  HF gate simulation (import only if available)
# ---------------------------------------------------------------------------

def _safe_confidence(pick: dict) -> float:
    """Extract confidence as float, returning 0.0 on missing/invalid."""
    try:
        c = pick.get("confidence")
        return float(c) if c is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _apply_hf_gate_to_picks(picks: list[dict], min_confidence: float = 0.0) -> dict:
    """Apply passes_hedge_fund_gate() + optional confidence floor.

    Returns {
        total, hf_passed, hf_rejected, hf_errors,
        conf_passed (subset of hf_passed with confidence >= min_confidence),
        reject_reasons: [{reason, count}]
    }.
    """
    result = {
        "total": 0,
        "hf_passed": 0,
        "hf_rejected": 0,
        "hf_errors": 0,
        "conf_passed": 0,
        "reject_reasons": Counter(),
        "min_confidence": min_confidence,
    }
    try:
        from alpha_engine.hedge_fund_quality_gate import passes_hedge_fund_gate
    except ImportError:
        result["error"] = "hedge_fund_quality_gate not importable"
        return result

    for p in picks:
        result["total"] += 1
        try:
            ok, reason = passes_hedge_fund_gate(p)
        except Exception:
            result["hf_errors"] += 1
            ok, reason = True, ""  # fail-open (gate bug → let pick through)

        if ok:
            result["hf_passed"] += 1
            # Apply confidence floor on top of HF gate
            if _safe_confidence(p) >= min_confidence:
                result["conf_passed"] += 1
        else:
            result["hf_rejected"] += 1
            result["reject_reasons"][reason] += 1

    # Convert Counter to sorted list of {reason, count}
    result["reject_reasons"] = [
        {"reason": r, "count": c}
        for r, c in result["reject_reasons"].most_common(30)
    ]
    return result


# ---------------------------------------------------------------------------
#  Build snapshot
# ---------------------------------------------------------------------------

def build_snapshot(since: str, until: str) -> dict:
    conn = _db_connect()
    cur = conn.cursor()

    raw = _query_raw_emitted(cur, since, until)
    rej = _query_gate_rejections(cur, since, until)
    cons = _query_consensus_survivors(cur, since, until)
    closed = _query_closed_with_pnl(cur, since, until)

    # HF gate simulation for CRYPTO (most picks, most impact).
    crypto_hf = {}
    try:
        crypto_picks = _query_active_by_source(cur, "CRYPTO")
        crypto_hf = _apply_hf_gate_to_picks(crypto_picks, min_confidence=0.70)
    except Exception:
        crypto_hf = {"error": "CRYPTO HF-gate query failed", "total": 0}

    # HF gate simulation for EQUITY — verifies EQUITY_BANNED_SOURCES
    # (stocks_competition, fast_stocks_competition, etc.) are blocking the
    # 316 negative-PnL sources identified in the 2026-05-24 forward-test audit.
    equity_hf = {}
    try:
        equity_picks = _query_active_by_source(cur, "EQUITY")
        # Build source breakdown in one pass, while applying the gate
        src_counts = Counter()
        for p in equity_picks:
            src = str(p.get("source_system") or "").strip()
            if src:
                src_counts[src] += 1
        equity_hf = _apply_hf_gate_to_picks(equity_picks, min_confidence=0.0)
        equity_hf["source_breakdown"] = dict(src_counts.most_common(30))
        # Parse reject_reasons for banned source hits (format: "HF_GATE: EQUITY banned source_system X (...)")
        banned_src_hits = {}
        for item in equity_hf.get("reject_reasons", []):
            reason = item.get("reason", "")
            if "banned source_system" in reason:
                # Extract source name between "source_system " and " ("
                try:
                    src = reason.split("banned source_system ")[1].split(" (")[0].strip()
                    banned_src_hits[src] = item.get("count", 0)
                except IndexError:
                    pass
        equity_hf["banned_source_hits"] = banned_src_hits
        # Report what the gate actually uses (import its frozenset, not raw env var)
        try:
            from alpha_engine.hedge_fund_quality_gate import EQUITY_BANNED_SOURCES as _eq_bs
            equity_hf["banned_sources_configured"] = sorted(_eq_bs)
            # Cross-reference: list ALL EQUITY sources from last 30 days with banned markers
            try:
                eq_sources_30d = _query_equity_sources_30d(cur)
                equity_hf["all_equity_sources_30d"] = [
                    {
                        "source_system": r["source_system"],
                        "raw_count": r["n"],
                        "banned": r["source_system"] in _eq_bs,
                    }
                    for r in eq_sources_30d
                ]
            except Exception:
                equity_hf["all_equity_sources_30d"] = []
        except ImportError:
            equity_hf["banned_sources_configured"] = []
            equity_hf["all_equity_sources_30d"] = []
    except Exception:
        equity_hf = {"error": "EQUITY HF-gate query failed", "total": 0}

    conn.close()

    # Assemble per-class rows
    all_classes = sorted(set(list(raw) + list(rej) + list(cons) + list(closed)))
    rows = []
    for ac in all_classes:
        r = raw.get(ac, 0)
        rj = rej.get(ac, {})
        cs = cons.get(ac, 0)
        cl = closed.get(ac, {})
        cl_n = cl.get("closed", 0)
        cl_wins = cl.get("wins", 0)
        gw = cl.get("gross_win", 0)
        gl = cl.get("gross_loss", 0)

        wr = round(100 * cl_wins / cl_n, 1) if cl_n else None
        pf = round(gw / gl, 2) if gl > 0 else (None if gw == 0 else float("inf"))

        rows.append({
            "asset_class": ac,
            "raw_emitted": r,
            "gate_rejected": rj.get("count", 0),
            "top_reject_reason": rj.get("top_reason", ""),
            "consensus_survivors": cs,
            "closed": cl_n,
            "win_rate_pct": wr,
            "profit_factor": pf,
        })

    return {
        "_meta": {
            "generated_at": dt.datetime.utcnow().isoformat() + "Z",
            "window_since": since,
            "window_until": until,
            "script": "tools/pick_flow_snapshot.py",
        },
        "per_class": sorted(rows, key=lambda x: -x["raw_emitted"]),
        "crypto_hf_gate": crypto_hf,
        "equity_hf_gate": equity_hf,
        "note": (
            "crypto_hf_gate runs on active OPEN CRYPTO picks (separate population "
            "from the per_class raw_emitted counts, which cover all statuses). "
            "hf_passed = survived HF gate (banned sources/symbols/drawdown). "
            "conf_passed = hf_passed ∩ confidence ≥ crypto_hf_gate.min_confidence. "
            "Closed WR/PF use closed_at-dated rows; picks whose status is "
            "terminal but closed_at is NULL are not counted."
        ),
    }


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--out", default="reports/pick_flow_snapshot.json")
    args = ap.parse_args()

    until = args.until or dt.date.today().isoformat()
    since = args.since or (dt.date.today() - dt.timedelta(days=args.days)).isoformat()

    print(f"pick_flow_snapshot: {since} .. {until}")
    snapshot = build_snapshot(since, until)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snapshot, indent=2, default=str))

    # Quick summary to stdout
    for row in snapshot["per_class"]:
        print(
            f"  {row['asset_class']:12} emit={row['raw_emitted']:>6}  "
            f"rej={row['gate_rejected']:>6}  cons={row['consensus_survivors']:>4}  "
            f"closed={row['closed']:>5}  WR={row['win_rate_pct'] or '-':>5}  "
            f"PF={row['profit_factor'] or '-'}"
        )
    hf = snapshot["crypto_hf_gate"]
    if hf and "hf_passed" in hf:
        total = hf.get("total", 0)
        passed = hf["hf_passed"]
        rejected = hf["hf_rejected"]
        errors = hf.get("hf_errors", 0)
        conf = hf.get("conf_passed", 0)
        min_conf = hf.get("min_confidence", 0.70)
        print(
            f"\n  CRYPTO HF Gate: {total} active sampled → "
            f"{passed} passed, {rejected} rejected, {errors} errors"
        )
        print(
            f"  CRYPTO HF + conf≥{min_conf}: {conf} forward-test candidates"
        )

    eq = snapshot.get("equity_hf_gate", {})
    if eq and "hf_passed" in eq:
        total = eq.get("total", 0)
        passed = eq["hf_passed"]
        rejected = eq["hf_rejected"]
        errors = eq.get("hf_errors", 0)
        print(
            f"\n  EQUITY HF Gate: {total} active sampled → "
            f"{passed} passed, {rejected} rejected, {errors} errors"
        )
        banned_hits = eq.get("banned_source_hits", {})
        if banned_hits:
            print("  EQUITY banned source hits:")
            for src, count in sorted(banned_hits.items(), key=lambda x: -x[1]):
                print(f"    {src}: {count}")
        # Print all EQUITY sources from last 30 days with banned markers
        all_srcs = eq.get("all_equity_sources_30d", [])
        if all_srcs:
            print("\n  EQUITY source_system values (30d), banned=✗:")
            for s in all_srcs:
                marker = "✗" if s["banned"] else " "
                print(f"    [{marker}] {s['source_system']:40} n={s['raw_count']:>5}")

    print(f"\n  → {out_path}")


if __name__ == "__main__":
    main()
