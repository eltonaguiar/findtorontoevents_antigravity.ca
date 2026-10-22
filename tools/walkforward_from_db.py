"""Run the walk-forward strategy eval harness on live DB picks."""
import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pymysql
import importlib.util
spec = importlib.util.spec_from_file_location("wse", os.path.join("tools", "walkforward_strategy_eval.py"))
wse = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wse)

DB_HOST = os.getenv("AUDIT_DB_HOST", "mysql.50webs.com")
DB_PORT = int(os.getenv("AUDIT_DB_PORT", "3306"))
DB_USER = os.getenv("AUDIT_DB_USER", "ejaguiar1_stocks")
DB_PASS = os.getenv("AUDIT_DB_PASS", "stocks1234560")
DB_NAME = os.getenv("AUDIT_DB_NAME", "ejaguiar1_stocks")


def _dt(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    try:
        return datetime.fromisoformat(str(v).replace("Z", ""))
    except Exception:
        return None


def fetch_rows():
    conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS,
                           database=DB_NAME, connect_timeout=15)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, source_system, strategy, symbol, asset_class, direction, status,
               pnl_pct, entry_price, exit_price, take_profit, stop_loss, confidence,
               recorded_at, closed_at, dedup_hash, was_stale, was_banned, was_demoted,
               was_wr_suppressed
        FROM at_raw_picks
        WHERE status IN ('WON','LOST') AND pnl_pct IS NOT NULL
    """)
    cols = [d[0] for d in cur.description]
    raw = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    out = []
    for r in raw:
        ts = _dt(r["recorded_at"])
        if ts is None:
            continue
        closed = _dt(r["closed_at"]) or ts
        out.append({
            "id": r["id"],
            "source_system": r["source_system"],
            "strategy": r["strategy"],
            "symbol": r["symbol"],
            "asset_class": r["asset_class"],
            "direction": r["direction"],
            "status": r["status"],
            "pnl_pct": float(r["pnl_pct"]),
            "entry_price": float(r["entry_price"]) if r["entry_price"] is not None else None,
            "exit_price": float(r["exit_price"]) if r["exit_price"] is not None else None,
            "take_profit": float(r["take_profit"]) if r["take_profit"] is not None else None,
            "stop_loss": float(r["stop_loss"]) if r["stop_loss"] is not None else None,
            "confidence": float(r["confidence"]) if r["confidence"] is not None else None,
            "timestamp": ts.isoformat() + "Z",
            "entry_time": ts.isoformat() + "Z",
            "closed_at": closed.isoformat() + "Z",
            "dedup_hash": r["dedup_hash"],
            "was_stale": bool(r["was_stale"]),
            "was_banned": bool(r["was_banned"]),
            "was_demoted": bool(r["was_demoted"]),
            "was_wr_suppressed": bool(r["was_wr_suppressed"]),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-n", type=int, default=10)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    raw = fetch_rows()
    cleaned, dropped = wse.clean_picks(raw)
    res = wse.evaluate_all(cleaned, min_n=args.min_n)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(res, f, indent=2, default=str)
    print(f"raw={len(raw)} clean={len(cleaned)} dropped={dropped}")
    print(f"train={res['n_train']} test={res['n_test']} artifact_cells={len(res['artifact_cells'])} winners={len(res['winners'])}")
    for w in res["winners"][:25]:
        print(f"  {w['asset_class']}|{w['symbol']}|{w['strategy']}|{w['direction']}: "
              f"tr_n={w['train']['n']} tr_PF={w['train']['pf']} | te_n={w['test']['n']} te_WR={w['test']['wr']} te_PF={w['test']['pf']} stable={w['stable_pf']}")
    print("\nClass-level (test):")
    for cls, m in sorted(res["classes"].items()):
        print(f"  {cls}: n={m['n']} WR={m['wr']} PF={m['pf']}")


if __name__ == "__main__":
    main()
