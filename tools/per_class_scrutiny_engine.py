#!/usr/bin/env python3
"""
Per-Class Scrutiny Engine — automated 5-axis hedge-fund filter

Runs all (source_system, category) pairs with n>=MIN_N through:
  Axis 1: Concentration (max symbol share < 30%)
  Axis 2: Fat-tail (top-3 wins < 30% of gross wins)
  Axis 3: OOS stability (first-half PF > 1.0 AND second-half PF > 1.0)
  Axis 4: Batch artifact (no single date > 35% of total closes)
  Axis 5: Binomial significance (p < 0.05 vs 50% null)

Output: reports/per_class_scrutiny_YYYYMMDD.json + console summary

Usage:
    python3 tools/per_class_scrutiny_engine.py [--min-n 30] [--output reports/]
"""
import sys
import json
import argparse
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _f(x):
    """Coerce Decimal (from pymysql SUM/AVG/ABS) to float for safe arithmetic."""
    if x is None:
        return 0.0
    if isinstance(x, Decimal):
        return float(x)
    return x

try:
    import pymysql
    import pymysql.cursors
except ImportError:
    print("ERROR: pymysql not installed. Run: pip install pymysql")
    sys.exit(1)

try:
    from scipy.stats import binomtest
except ImportError:
    print("ERROR: scipy not installed. Run: pip install scipy")
    sys.exit(1)

# ── DB connection ─────────────────────────────────────────────────────────────

def get_conn():
    from tools.db_env import get_stocks_creds
    return pymysql.connect(
        **get_stocks_creds(),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


# ── 5-axis scrutiny ───────────────────────────────────────────────────────────

CONC_THRESHOLD = 0.30     # max single-symbol share
FAT_TAIL_THRESHOLD = 0.30 # top-3 wins as fraction of gross wins
OOS_MIN_PF = 1.0          # both halves must beat this
BATCH_THRESHOLD = 0.35    # max single-date share
BINOM_ALPHA = 0.05        # significance level


def scrutinize_source(cur, source_system: str, category: str) -> dict:
    """Run 5-axis scrutiny on one (source, category) pair. Returns verdict dict."""
    base = """
        FROM trading_picks
        WHERE source_system=%s AND LOWER(TRIM(category))=%s
          AND closed_at IS NOT NULL AND pnl_pct IS NOT NULL
          AND status NOT IN ('OPEN','ABANDONED','FLAT','FORCE_CLOSED_TOXIC')
          AND closed_at > '2026-01-01'
    """
    cls = category.lower().strip()

    # Overall stats
    cur.execute(f"SELECT COUNT(*) as n, "
                f"SUM(CASE WHEN pnl_pct>0 THEN 1.0 ELSE 0 END) as wins, "
                f"SUM(CASE WHEN pnl_pct>0 THEN pnl_pct ELSE 0 END) as gross_wins, "
                f"ABS(SUM(CASE WHEN pnl_pct<0 THEN pnl_pct ELSE 0 END)) as gross_losses, "
                f"MIN(closed_at) as first_close, MAX(closed_at) as last_close "
                f"{base}", (source_system, cls))
    row = cur.fetchone()
    n, wins = int(row["n"] or 0), int(row["wins"] or 0)
    if n == 0:
        return {"source_system": source_system, "category": cls, "n": 0, "verdict": "INSUFFICIENT_N"}

    gw = float(row["gross_wins"] or 0)
    gl = float(row["gross_losses"] or 0)
    wr = wins / n
    pf = round(gw / gl, 2) if gl > 0 else None
    avg_pnl = round(gw / n * 100, 3)  # basis points

    axes = {}

    # Axis 1: Concentration
    cur.execute(f"SELECT symbol, COUNT(*) as cnt {base} GROUP BY symbol ORDER BY cnt DESC LIMIT 1",
                (source_system, cls))
    top_sym = cur.fetchone()
    max_share = top_sym["cnt"] / n if top_sym else 0
    axes["concentration"] = {"pass": max_share < CONC_THRESHOLD,
                              "max_share": round(max_share, 3),
                              "symbol": top_sym["symbol"] if top_sym else None}

    # Axis 2: Fat-tail
    cur.execute(f"SELECT pnl_pct {base} AND pnl_pct>0 ORDER BY pnl_pct DESC LIMIT 3",
                (source_system, cls))
    top3_wins = sum(_f(r["pnl_pct"]) for r in cur.fetchall())
    fat_ratio = top3_wins / gw if gw > 0 else 1.0
    axes["fat_tail"] = {"pass": fat_ratio < FAT_TAIL_THRESHOLD,
                         "top3_share": round(fat_ratio, 3)}

    # Axis 3: OOS split
    cur.execute(f"SELECT MIN(closed_at) as mn, MAX(closed_at) as mx {base}", (source_system, cls))
    bounds = cur.fetchone()
    if bounds and bounds["mn"] and bounds["mx"]:
        from datetime import timedelta
        mn = bounds["mn"] if isinstance(bounds["mn"], date) else bounds["mn"].date()
        mx = bounds["mx"] if isinstance(bounds["mx"], date) else bounds["mx"].date()
        mid = mn + (mx - mn) / 2
        mid_str = str(mid)
        cur.execute(f"SELECT "
                    f"SUM(CASE WHEN closed_at<=%s THEN (pnl_pct>0) ELSE 0 END) as h1w, "
                    f"SUM(CASE WHEN closed_at<=%s THEN 1 ELSE 0 END) as h1n, "
                    f"SUM(CASE WHEN pnl_pct>0 AND closed_at<=%s THEN pnl_pct ELSE 0 END) as h1gw, "
                    f"ABS(SUM(CASE WHEN pnl_pct<0 AND closed_at<=%s THEN pnl_pct ELSE 0 END)) as h1gl, "
                    f"SUM(CASE WHEN closed_at>%s THEN (pnl_pct>0) ELSE 0 END) as h2w, "
                    f"SUM(CASE WHEN closed_at>%s THEN 1 ELSE 0 END) as h2n, "
                    f"SUM(CASE WHEN pnl_pct>0 AND closed_at>%s THEN pnl_pct ELSE 0 END) as h2gw, "
                    f"ABS(SUM(CASE WHEN pnl_pct<0 AND closed_at>%s THEN pnl_pct ELSE 0 END)) as h2gl "
                    f"{base}",
                    (mid_str, mid_str, mid_str, mid_str, mid_str, mid_str, mid_str, mid_str,
                     source_system, cls))
        oos = cur.fetchone()
        h1gw_f, h1gl_f = _f(oos["h1gw"]), _f(oos["h1gl"])
        h2gw_f, h2gl_f = _f(oos["h2gw"]), _f(oos["h2gl"])
        h1_pf = (h1gw_f / h1gl_f) if h1gl_f and h1gl_f > 0 else None
        h2_pf = (h2gw_f / h2gl_f) if h2gl_f and h2gl_f > 0 else None
        oos_pass = (h1_pf is None or h1_pf >= OOS_MIN_PF) and (h2_pf is None or h2_pf >= OOS_MIN_PF)
        if _f(oos["h1n"]) == 0:
            oos_pass = True  # no H1 data — can't fail
        axes["oos_stability"] = {"pass": oos_pass,
                                  "h1_pf": round(h1_pf, 2) if h1_pf else None,
                                  "h2_pf": round(h2_pf, 2) if h2_pf else None,
                                  "h1_n": int(_f(oos["h1n"])), "h2_n": int(_f(oos["h2n"]))}
    else:
        axes["oos_stability"] = {"pass": False, "error": "no date bounds"}

    # Axis 4: Batch artifact
    cur.execute(f"SELECT DATE(closed_at) as d, COUNT(*) as cnt {base} GROUP BY d ORDER BY cnt DESC LIMIT 1",
                (source_system, cls))
    top_date = cur.fetchone()
    max_date_share = top_date["cnt"] / n if top_date else 0
    axes["batch_artifact"] = {"pass": max_date_share < BATCH_THRESHOLD,
                               "max_date_share": round(max_date_share, 3),
                               "peak_date": str(top_date["d"]) if top_date else None,
                               "peak_n": top_date["cnt"] if top_date else 0}

    # Axis 5: Binomial
    p_val = binomtest(wins, n, 0.5, alternative="greater").pvalue
    axes["binomial"] = {"pass": p_val < BINOM_ALPHA, "p_value": round(p_val, 6), "n": n, "wins": wins}

    passing = sum(1 for v in axes.values() if v.get("pass"))
    failing_axes = [k for k, v in axes.items() if not v.get("pass")]

    if passing == 5:
        verdict = "PASS_ALL_AXES"
    elif passing >= 4:
        verdict = "WATCHLIST"
    elif passing >= 3:
        verdict = "BORDERLINE"
    else:
        verdict = "FAIL"

    return {
        "source_system": source_system,
        "category": cls,
        "n": n,
        "wr": round(wr * 100, 1),
        "pf": pf,
        "avg_pnl_bp": avg_pnl,
        "axes_passing": passing,
        "failing_axes": failing_axes,
        "verdict": verdict,
        "axes": axes,
        "first_close": str(bounds["mn"]) if bounds else None,
        "last_close": str(bounds["mx"]) if bounds else None,
    }


def run_scrutiny(min_n: int = 30, output_dir: str = "reports") -> list:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT source_system, LOWER(TRIM(category)) as cls, COUNT(*) as n
        FROM trading_picks
        WHERE closed_at IS NOT NULL AND pnl_pct IS NOT NULL
          AND status NOT IN ('OPEN','ABANDONED','FLAT','FORCE_CLOSED_TOXIC')
          AND closed_at > '2026-01-01'
        GROUP BY source_system, cls
        HAVING n >= %s
        ORDER BY n DESC
    """, (min_n,))
    candidates = cur.fetchall()
    print(f"Found {len(candidates)} (source, class) pairs with n>={min_n}")

    results = []
    for c in candidates:
        r = scrutinize_source(cur, c["source_system"], c["cls"])
        results.append(r)

    conn.close()

    # Sort: PASS_ALL first, then WATCHLIST, then by PF desc
    order = {"PASS_ALL_AXES": 0, "WATCHLIST": 1, "BORDERLINE": 2, "FAIL": 3, "INSUFFICIENT_N": 4}
    results.sort(key=lambda x: (order.get(x["verdict"], 5), -(x.get("pf") or 0)))

    # Write JSON output
    today = datetime.utcnow().strftime("%Y%m%d")
    out_path = Path(output_dir) / f"per_class_scrutiny_{today}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"generated_utc": datetime.utcnow().isoformat() + "Z",
                   "min_n": min_n, "results": results}, f, indent=2, default=str)
    print(f"\nReport saved to: {out_path}")

    # Console summary
    print(f"\n{'Source':<45} {'Class':<12} {'n':>5} {'WR':>6} {'PF':>6} {'Axes':>5}  Verdict")
    print("-" * 100)
    for r in results:
        flags = ""
        if r.get("verdict") == "PASS_ALL_AXES":
            flags = "✅"
        elif r.get("verdict") == "WATCHLIST":
            flags = "⚠️"
        elif r.get("verdict") == "FAIL":
            fail_short = ",".join(a[:3] for a in r.get("failing_axes", []))
            flags = f"❌ [{fail_short}]"
        print(f"  {r['source_system']:<45} {r['category']:<12} {r['n']:>5} "
              f"{str(r.get('wr','?')):>6}% {str(r.get('pf','?')):>6} "
              f"{r.get('axes_passing','?'):>4}/5  {flags}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-n", type=int, default=30, help="Minimum n for inclusion")
    parser.add_argument("--output", default="reports", help="Output directory")
    args = parser.parse_args()
    run_scrutiny(min_n=args.min_n, output_dir=args.output)
