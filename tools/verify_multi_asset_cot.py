#!/usr/bin/env python3
"""Forensic verifier for `multi_asset_cot` headline PF.

READ-ONLY. Resolves PF=19.19 swarm question:
  - dashboard `systems.multi_asset_cot` headline numbers
  - DB cross-check (bt_backtest_trades / raw_picks via audit_trail.mysql_client)
  - JSON fallback (alpha_engine/data/closed_picks.json) when DB unreachable
  - per-symbol PF, top-5 trade PnL contribution, bootstrap 95% CI for PF
  - verdict: REAL / OUTLIER_DRIVEN / RESOLVER_INFLATED / DATA_GAP

Emits `reports/multi_asset_cot_db_verify_<YYYY_MM_DD>.md`.
Exits 0 always.
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_JSON = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
CLOSED_PICKS_JSON = REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json"
REPORTS_DIR = REPO_ROOT / "reports"
SOURCE_NAME = "multi_asset_cot"
BOOTSTRAP_N = 10000
OUTLIER_CONTRIB_THRESHOLD = 0.30  # any single trade > 30% of total PnL flags inflation


def _safe_float(v: Any) -> Optional[float]:
    try:
        f = float(v)
        if f != f:
            return None
        return f
    except (TypeError, ValueError):
        return None


def extract_dashboard_headline(path: Path) -> Dict[str, Any]:
    """Pull headline PF/WR/n from `systems.multi_asset_cot` if present."""
    out = {"found": False, "pf": None, "wr": None, "n": None, "raw": None}
    if not path.exists():
        out["error"] = f"missing {path}"
        return out
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        out["error"] = f"json parse error: {e}"
        return out
    systems = data.get("systems") or {}
    entry = None
    if isinstance(systems, dict):
        entry = systems.get(SOURCE_NAME)
        if entry is None:
            for k, v in systems.items():
                if isinstance(v, dict) and SOURCE_NAME in str(k).lower():
                    entry = v
                    break
    elif isinstance(systems, list):
        for row in systems:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or row.get("strategy") or row.get("source_system") or "").lower()
            if SOURCE_NAME in name:
                entry = row
                break
    if not isinstance(entry, dict):
        out["error"] = f"systems.{SOURCE_NAME} not present"
        return out
    out["found"] = True
    out["pf"] = _safe_float(entry.get("pf") or entry.get("profit_factor"))
    out["wr"] = _safe_float(entry.get("wr") or entry.get("win_rate") or entry.get("wr_pct"))
    out["n"] = entry.get("n") or entry.get("count") or entry.get("trades")
    out["raw"] = {k: entry.get(k) for k in ("pf", "wr", "n", "count", "win_rate", "trades")}
    return out


def fetch_trades_db() -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """Try DB. Returns (trades, error). trades=None if unavailable."""
    try:
        from audit_trail import mysql_client  # type: ignore
    except Exception as e:
        return None, f"mysql_client import failed: {e}"
    try:
        conn = mysql_client._create_connection()
    except Exception as e:
        return None, f"db connect failed: {e}"
    rows: List[Dict[str, Any]] = []
    try:
        cur = conn.cursor()
        # bt_backtest_trades — primary backtest fact table
        try:
            cur.execute(
                "SELECT symbol, pnl_pct, entry_time, exit_time, status "
                "FROM bt_backtest_trades WHERE strategy=%s OR source_table=%s",
                (SOURCE_NAME, SOURCE_NAME),
            )
            for r in cur.fetchall():
                rows.append({"symbol": r[0], "pnl_pct": _safe_float(r[1]),
                             "entry_time": r[2], "exit_time": r[3],
                             "status": r[4], "src": "bt_backtest_trades"})
        except Exception as e:
            rows.append({"_warn": f"bt_backtest_trades query failed: {e}"})
        # raw_picks — closed historical picks
        try:
            cur.execute(
                "SELECT symbol, pnl_pct, signal_timestamp, status FROM raw_picks "
                "WHERE source_system=%s",
                (SOURCE_NAME,),
            )
            for r in cur.fetchall():
                rows.append({"symbol": r[0], "pnl_pct": _safe_float(r[1]),
                             "entry_time": r[2], "exit_time": None,
                             "status": r[3], "src": "raw_picks"})
        except Exception as e:
            rows.append({"_warn": f"raw_picks query failed: {e}"})
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return rows, None


def fetch_trades_json(path: Path) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    if not path.exists():
        return [], f"missing {path}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return [], f"json parse error: {e}"
    picks = data if isinstance(data, list) else data.get("picks", []) or data.get("closed", [])
    out: List[Dict[str, Any]] = []
    for p in picks:
        if not isinstance(p, dict):
            continue
        src = p.get("source_system") or p.get("source") or ""
        srcs = p.get("source_systems") or []
        if SOURCE_NAME not in str(src).lower() and SOURCE_NAME not in str(srcs).lower():
            continue
        out.append({"symbol": p.get("symbol"),
                    "pnl_pct": _safe_float(p.get("pnl_pct") or p.get("realized_pnl_pct")),
                    "entry_time": p.get("entry_time"),
                    "exit_time": p.get("exit_time"),
                    "status": p.get("status"),
                    "src": "closed_picks.json"})
    return out, None


def compute_pf(pnls: Iterable[float]) -> Optional[float]:
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses == 0:
        return None if wins == 0 else math.inf
    return wins / losses


def compute_wr(pnls: List[float]) -> Optional[float]:
    if not pnls:
        return None
    return 100.0 * sum(1 for p in pnls if p > 0) / len(pnls)


def top_n_contribution(pnls: List[float], n: int = 5) -> List[Tuple[float, float]]:
    """Return list of (pnl, pct_of_abs_total) for top-n by absolute magnitude."""
    if not pnls:
        return []
    total_abs = sum(abs(p) for p in pnls) or 1.0
    ranked = sorted(pnls, key=lambda p: abs(p), reverse=True)[:n]
    return [(p, abs(p) / total_abs) for p in ranked]


def bootstrap_pf_ci(pnls: List[float], n_iter: int = BOOTSTRAP_N,
                    seed: int = 42) -> Tuple[Optional[float], Optional[float]]:
    if len(pnls) < 5:
        return None, None
    rng = random.Random(seed)
    pfs: List[float] = []
    k = len(pnls)
    for _ in range(n_iter):
        sample = [pnls[rng.randrange(k)] for _ in range(k)]
        pf = compute_pf(sample)
        if pf is None or pf == math.inf:
            continue
        pfs.append(pf)
    if not pfs:
        return None, None
    pfs.sort()
    lo = pfs[int(0.025 * len(pfs))]
    hi = pfs[min(len(pfs) - 1, int(0.975 * len(pfs)))]
    return lo, hi


def per_symbol_breakdown(rows: List[Dict[str, Any]]) -> List[Tuple[str, int, Optional[float], Optional[float]]]:
    by_sym: Dict[str, List[float]] = {}
    for r in rows:
        p = r.get("pnl_pct")
        if p is None:
            continue
        by_sym.setdefault(r.get("symbol") or "UNKNOWN", []).append(p)
    out = []
    for sym, pnls in sorted(by_sym.items(), key=lambda kv: -len(kv[1])):
        out.append((sym, len(pnls), compute_pf(pnls), compute_wr(pnls)))
    return out


def decide_verdict(headline_pf: Optional[float], computed_pf: Optional[float],
                   top_contribs: List[Tuple[float, float]], n_trades: int,
                   data_source: str) -> str:
    if n_trades == 0:
        return "DATA_GAP"
    top1_pct = top_contribs[0][1] if top_contribs else 0.0
    if computed_pf is not None and computed_pf > 15 and top1_pct > 0.50:
        return "OUTLIER_DRIVEN"
    if computed_pf is not None and top1_pct > OUTLIER_CONTRIB_THRESHOLD:
        return "OUTLIER_DRIVEN"
    if (headline_pf is not None and computed_pf is not None
            and headline_pf > 0 and computed_pf > 0
            and abs(headline_pf - computed_pf) / max(headline_pf, computed_pf) > 0.40):
        return "RESOLVER_INFLATED"
    if n_trades < 30:
        return "DATA_GAP"
    return "REAL"


def build_report(headline: Dict[str, Any], rows: List[Dict[str, Any]],
                 data_source: str, notes: List[str]) -> str:
    pnls = [r["pnl_pct"] for r in rows if r.get("pnl_pct") is not None]
    n = len(pnls)
    pf = compute_pf(pnls)
    wr = compute_wr(pnls)
    top5 = top_n_contribution(pnls, 5)
    ci_lo, ci_hi = bootstrap_pf_ci(pnls)
    verdict = decide_verdict(headline.get("pf"), pf, top5, n, data_source)

    lines = []
    lines.append(f"# multi_asset_cot DB Verify — {datetime.now(timezone.utc).date()}")
    lines.append("")
    lines.append(f"**Verdict: {verdict}**")
    lines.append("")
    lines.append("## Headline (dashboard `systems.multi_asset_cot`)")
    if headline.get("found"):
        lines.append(f"- PF: {headline.get('pf')}")
        lines.append(f"- WR: {headline.get('wr')}")
        lines.append(f"- n: {headline.get('n')}")
    else:
        lines.append(f"- NOT FOUND: {headline.get('error')}")
    lines.append("")
    lines.append(f"## Computed (source: {data_source}, n={n})")
    lines.append(f"- PF: {pf}")
    lines.append(f"- WR: {wr}")
    if ci_lo is not None:
        lines.append(f"- PF 95% bootstrap CI: [{ci_lo:.3f}, {ci_hi:.3f}] (n_iter={BOOTSTRAP_N})")
    else:
        lines.append("- PF 95% bootstrap CI: insufficient data")
    lines.append("")
    lines.append("## Top-5 trades by |PnL| contribution")
    if top5:
        lines.append("| rank | pnl_pct | % of |abs total| |")
        lines.append("|---|---|---|")
        for i, (p, frac) in enumerate(top5, 1):
            lines.append(f"| {i} | {p:.4f} | {frac*100:.2f}% |")
    else:
        lines.append("(no trades)")
    lines.append("")
    lines.append("## Per-symbol breakdown")
    syms = per_symbol_breakdown(rows)
    if syms:
        lines.append("| symbol | n | PF | WR% |")
        lines.append("|---|---|---|---|")
        for sym, c, spf, swr in syms[:25]:
            lines.append(f"| {sym} | {c} | {spf} | {swr} |")
    else:
        lines.append("(no per-symbol data)")
    lines.append("")
    lines.append("## Notes")
    for nt in notes:
        lines.append(f"- {nt}")
    lines.append("")
    lines.append("## Verdict legend")
    lines.append("- **REAL** — headline matches computed; no single-trade outlier dominance.")
    lines.append("- **OUTLIER_DRIVEN** — single trade > 30% of |total PnL|, or PF>15 with top-1 > 50%.")
    lines.append("- **RESOLVER_INFLATED** — headline PF deviates from recomputed PF by > 40%.")
    lines.append("- **DATA_GAP** — n<30 or no trades reachable.")
    return "\n".join(lines) + "\n"


def main(argv: List[str]) -> int:
    notes: List[str] = []
    headline = extract_dashboard_headline(DASHBOARD_JSON)
    if not headline.get("found"):
        notes.append(f"dashboard headline missing: {headline.get('error')}")
    rows: List[Dict[str, Any]] = []
    data_source = "none"
    db_rows, db_err = fetch_trades_db()
    if db_rows is None:
        notes.append(f"DB unavailable — {db_err}")
    else:
        warns = [r for r in db_rows if "_warn" in r]
        clean = [r for r in db_rows if "_warn" not in r]
        for w in warns:
            notes.append(w["_warn"])
        if clean:
            rows = clean
            data_source = "mysql (bt_backtest_trades + raw_picks)"
        else:
            notes.append("DB reachable but returned 0 rows for multi_asset_cot")
    if not rows:
        json_rows, json_err = fetch_trades_json(CLOSED_PICKS_JSON)
        if json_err:
            notes.append(f"JSON fallback note: {json_err}")
        if json_rows:
            rows = json_rows
            data_source = f"json fallback ({CLOSED_PICKS_JSON.name})"
        else:
            notes.append("no JSON fallback rows for multi_asset_cot")
    report = build_report(headline, rows, data_source, notes)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y_%m_%d")
    out_path = REPORTS_DIR / f"multi_asset_cot_db_verify_{date_tag}.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
