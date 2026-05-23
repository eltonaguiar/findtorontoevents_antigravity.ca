#!/usr/bin/env python3
"""EQUITY source reconciliation — why do the repo's EQUITY numbers disagree?

Swarm + Mercury flagged a cross-table EQUITY contradiction. Investigation found
it is not 2 sources but **five+**, all in this repo, disagreeing on (n, WR, PF):

  asset_class_health.EQUITY   n=31   WR 35.5%  PF 0.72   (verdict-grade)
  hf_stats.EQUITY             n=271  WR 52.4%  PF 1.82
  by_asset_class.EQUITY       n=339  WR 54.4%  PF 2.06
  at_consensus_picks (MySQL)  n=738  WR  1.2%  PF 0.09
  closed_picks.json EQUITY    n~44   WR ~36%

`asset_class_health.EQUITY` is even internally inconsistent: headline WR 35.5%
(n=31) vs its own `circuit_breaker.realized_wr_30d` 60.8% (n=79).

This tool pulls every EQUITY record live and tabulates them so the root cause
is explicit: there is **no canonical EQUITY resolved-pick set** — each
subsystem applies its own window/filter/resolver and computes a different
number. Until one canonical source is chosen, no EQUITY edge claim — bullish
OR bearish — is trustworthy.

    python tools/equity_source_reconcile.py [--out report.md]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
CLOSED = ROOT / "alpha_engine" / "data" / "closed_picks.json"


def _g(d, *path):
    for p in path:
        if isinstance(d, dict):
            d = d.get(p)
        else:
            return None
    return d


def from_dashboard() -> list[dict]:
    rows = []
    if not DASH.exists():
        return [{"source": "dashboard_data.json", "note": "file absent"}]
    d = json.loads(DASH.read_text(encoding="utf-8"))
    ach = _g(d, "performance", "asset_class_health") or _g(d, "asset_class_health") or {}
    eq = ach.get("EQUITY") or ach.get("equity") or {}
    if eq:
        cb = eq.get("circuit_breaker", {})
        rows.append({"source": "asset_class_health.EQUITY", "n": eq.get("n"),
                     "wr": eq.get("win_rate"), "pf": eq.get("pf") or eq.get("profit_factor"),
                     "note": f"status={eq.get('status')}; realized_wr_30d="
                             f"{cb.get('realized_wr_30d')} (n={cb.get('realized_n_30d')})"})
    for key in ("hf_stats", "by_asset_class"):
        v = d.get(key) or _g(d, "performance", key) or {}
        e = v.get("EQUITY") if isinstance(v, dict) else None
        if e:
            n = e.get("n") or e.get("closed")
            wr = e.get("win_rate")
            if isinstance(wr, (int, float)) and wr <= 1.5:
                wr *= 100
            rows.append({"source": f"{key}.EQUITY", "n": n, "wr": wr,
                         "pf": e.get("profit_factor") or e.get("pf"),
                         "note": f"active={e.get('active')} closed={e.get('closed')}"})
    return rows


def from_closed_json() -> dict:
    if not CLOSED.exists():
        return {"source": "closed_picks.json EQUITY", "note": "absent"}
    d = json.loads(CLOSED.read_text(encoding="utf-8"))
    picks = d if isinstance(d, list) else d.get("picks", d.get("closed", []))
    eq = [p for p in picks if isinstance(p, dict)
          and str(p.get("asset_class") or "").upper() == "EQUITY"]
    if not eq:
        return {"source": "closed_picks.json EQUITY", "n": 0}
    wins = sum(1 for p in eq if p.get("pnl_pct") is not None and float(p["pnl_pct"]) > 0)
    gw = sum(float(p["pnl_pct"]) for p in eq
             if p.get("pnl_pct") is not None and float(p["pnl_pct"]) > 0)
    gl = abs(sum(float(p["pnl_pct"]) for p in eq
                 if p.get("pnl_pct") is not None and float(p["pnl_pct"]) < 0))
    return {"source": "closed_picks.json EQUITY", "n": len(eq),
            "wr": round(wins / len(eq) * 100, 1),
            "pf": round(gw / gl, 2) if gl > 1e-9 else 999.0, "note": "raw ledger"}


def from_mysql() -> dict:
    pw = os.environ.get("DB_PASS_STOCKS")
    if not pw:
        return {"source": "at_consensus_picks (MySQL)", "note": "DB_PASS_STOCKS not set — skipped"}
    try:
        import pymysql
        name = os.environ.get("DB_NAME_STOCKS") or "ejaguiar1_stocks"
        conn = pymysql.connect(host=os.environ.get("DB_HOST", "mysql.50webs.com"),
                               user=os.environ.get("DB_USER_STOCKS") or name,
                               password=pw, database=name, charset="utf8mb4",
                               cursorclass=pymysql.cursors.DictCursor, connect_timeout=20)
        with conn.cursor() as cur:
            cur.execute("SELECT status, pnl_pct FROM at_consensus_picks "
                        "WHERE UPPER(asset_class)='EQUITY' AND pnl_pct IS NOT NULL")
            rows = cur.fetchall()
        conn.close()
    except Exception as exc:  # noqa: BLE001
        return {"source": "at_consensus_picks (MySQL)", "note": f"fetch failed: {exc}"}
    if not rows:
        return {"source": "at_consensus_picks (MySQL)", "n": 0}
    pn = [float(r["pnl_pct"]) for r in rows]
    wins = sum(1 for x in pn if x > 0)
    gw = sum(x for x in pn if x > 0)
    gl = abs(sum(x for x in pn if x < 0))
    return {"source": "at_consensus_picks (MySQL)", "n": len(rows),
            "wr": round(wins / len(rows) * 100, 1),
            "pf": round(gw / gl, 2) if gl > 1e-9 else 999.0,
            "note": "resolved consensus picks"}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    rows = from_dashboard() + [from_closed_json(), from_mysql()]
    out = ["# EQUITY Source Reconciliation — 2026-05-18", "",
           "Every EQUITY (n, WR, PF) record found across the repo:", "",
           "| source | n | WR | PF | note |", "|---|---|---|---|---|"]
    wr_vals = []
    for r in rows:
        n = r.get("n", "—")
        wr = r.get("wr")
        if isinstance(wr, (int, float)):
            wr_vals.append(wr)
        wr_s = f"{wr:.1f}%" if isinstance(wr, (int, float)) else "—"
        pf = r.get("pf")
        pf_s = f"{pf:.2f}" if isinstance(pf, (int, float)) else "—"
        out.append(f"| `{r['source']}` | {n} | {wr_s} | {pf_s} | {r.get('note','')} |")
    spread = (max(wr_vals) - min(wr_vals)) if len(wr_vals) >= 2 else 0
    out += ["",
            f"## Root cause",
            "",
            f"WR ranges **{min(wr_vals):.1f}% – {max(wr_vals):.1f}%** "
            f"(spread {spread:.0f} points) across {len(wr_vals)} EQUITY records "
            f"in ONE repo. These are not the same data resolved differently — "
            f"they are **different pick populations**: each subsystem "
            f"(`asset_class_health`, `hf_stats`, `by_asset_class`, the consensus "
            f"DB, the JSON ledger) applies its own window, filter, and resolver "
            f"and reports its own n.",
            "",
            "**There is no canonical EQUITY resolved-pick set.** That is the bug "
            "— not corruption in any one table, but the absence of a single "
            "source of truth. The session's 'EQUITY = best candidate' (from "
            "`hf_stats`/`by_asset_class`, WR 52-54%) and 'EQUITY no-edge' (from "
            "`asset_class_health`, WR 35%) are both quoting real numbers from "
            "non-comparable populations.",
            "",
            "## Fix (upstream — peer-coordinated)",
            "",
            "1. Designate ONE canonical EQUITY resolved-pick source (recommend "
            "the consensus DB once the non-crypto resolver is fixed — it is the "
            "post-gate layer with the most rows).",
            "2. Make `asset_class_health`, `hf_stats`, `by_asset_class` all read "
            "that one source with an explicit, identical window.",
            "3. Re-run `tools/equity_mysql_edge_test.py` against the canonical "
            "set — only then is an EQUITY edge verdict trustworthy.",
            "",
            "Until then: **no EQUITY edge claim, bullish or bearish, is valid.** "
            "The data must agree with itself first."]
    report = "\n".join(out)
    if args.out:
        args.out.write_text(report, encoding="utf-8")
        print(f"# wrote {args.out}", file=sys.stderr)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
