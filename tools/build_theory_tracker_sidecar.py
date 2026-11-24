#!/usr/bin/env python3
"""Build audit_dashboard/data/theory_tracker.json — theory/hypothesis tracker sidecar.

Minimal honest data path for the two theory-tracker emitters whose outputs
nothing read (feed-trace audit 2026-11-16):

  * alpha_engine/portfolio_theories.py  -> alpha_engine/data/theory_portfolios.json
  * WIRED_IN/**/build_tracker.py etc.   -> reports/h0XX_*.json (hypothesis harness runs)

Aggregates both into ONE strict-JSON sidecar consumed by:
  * the "🧪 Theory / Hypothesis Tracker" block in audit_dashboard/template.html
  * the freshness tile wired in audit_dashboard/dashboard_freshness.js sources[]

Output schema (strict JSON — never NaN/Infinity):
    {
      "generated_at": "<UTC ISO>",
      "theories": [
        {"name": ..., "hypothesis": ..., "status": ..., "n": ...,
         "verdict": ..., "last_updated": ...},
        ...
      ]
    }

Row mapping:
  * theory_portfolios.json portfolio rows — name = portfolio key (e.g.
    "B_news_sentiment"), hypothesis/status/verdict are not emitted by that
    source so they stay empty; n = stats.total_trades (fallback: closed
    position count); last_updated = file-level last_updated.
  * reports/h0XX_*.json rows — one row per experiment stem (newest run wins
    per stem, so the weekly h004_* reruns collapse to their latest run while
    distinct experiments under the same H-id stay separate); hypothesis =
    "H-004" etc.; n = first available count field; verdict / status / run
    timestamp taken from the report body, with the filename date as fallback.

Missing or unreadable inputs are tolerated: the sidecar is still emitted as
empty-but-valid strict JSON. Non-finite numbers (NaN/Infinity) in inputs are
dropped (never re-emitted) and serialization uses allow_nan=False as a hard
backstop.

USAGE
  python3 tools/build_theory_tracker_sidecar.py
  python3 tools/build_theory_tracker_sidecar.py --out /tmp/theory_tracker.json
"""
from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PORTFOLIOS = REPO_ROOT / "alpha_engine" / "data" / "theory_portfolios.json"
DEFAULT_REPORTS_DIR = REPO_ROOT / "reports"
DEFAULT_OUT = REPO_ROOT / "audit_dashboard" / "data" / "theory_tracker.json"

# reports/h0XX_<slug>_YYYYMMDD.json or reports/h0XX_<slug>.json
_H0_FILE_RE = re.compile(r"^h(\d{3})_(.+?)(?:_(\d{8}))?$")

# First-available count field for h0XX report rows, in preference order.
_REPORT_N_FIELDS = (
    "n_trades",
    "n_picks_with_cot",
    "n_picks_with_signal",
    "n_picks_with_fg",
    "n_enriched_picks",
    "n_equity_picks",
    "n_etf_picks_total",
)


def _finite(value: Any) -> float | None:
    """Return value as float when it is a real (finite) number, else None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    f = float(value)
    return f if math.isfinite(f) else None


def _clean_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return str(value).strip()


def _iso_or_empty(value: Any) -> str:
    text = _clean_str(value)
    return text if text else ""


def _load_json(path: Path) -> Any:
    try:
        if not path.is_file():
            return None
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _report_n(report: dict) -> int | None:
    for key in _REPORT_N_FIELDS:
        n = _finite(report.get(key))
        if n is not None:
            return int(n)
    windows = report.get("windows")
    if isinstance(windows, list):
        total = 0
        seen = False
        for win in windows:
            if isinstance(win, dict):
                n = _finite(win.get("n_total"))
                if n is not None:
                    total += int(n)
                    seen = True
        if seen:
            return total
    return None


def _portfolio_rows(data: Any, source_path: Path) -> list[dict]:
    rows: list[dict] = []
    if not isinstance(data, dict):
        return rows
    portfolios = data.get("portfolios")
    if not isinstance(portfolios, dict):
        return rows
    file_updated = _iso_or_empty(data.get("last_updated"))
    for key in sorted(portfolios):
        pf = portfolios[key]
        if not isinstance(pf, dict):
            pf = {}
        stats = pf.get("stats") if isinstance(pf.get("stats"), dict) else {}
        closed = pf.get("closed_positions")
        closed_n = len(closed) if isinstance(closed, list) else 0
        n = _finite(stats.get("total_trades"))
        active = pf.get("active_positions")
        has_open = isinstance(active, list) and len(active) > 0
        rows.append({
            "name": _clean_str(key),
            "hypothesis": "",
            "status": "active" if has_open else "idle",
            "n": int(n) if n is not None else closed_n,
            "verdict": "",
            "last_updated": file_updated,
        })
    return rows


def _report_rows(reports_dir: Path) -> list[dict]:
    """One row per h0XX experiment stem — newest run per stem wins."""
    newest: dict[str, tuple[str, Path]] = {}
    if not reports_dir.is_dir():
        return []
    for path in sorted(reports_dir.glob("h0*.json")):
        m = _H0_FILE_RE.match(path.stem)
        if not m:
            continue
        h_num, slug, file_date = m.group(1), m.group(2), m.group(3) or ""
        stem = f"h{h_num}_{slug}"
        sort_key = f"{file_date}|{path.stat().st_mtime:.6f}|{path.name}"
        if stem not in newest or sort_key > newest[stem][0]:
            newest[stem] = (sort_key, path)
    rows: list[dict] = []
    for stem in sorted(newest):
        path = newest[stem][1]
        m = _H0_FILE_RE.match(path.stem)
        h_num, file_date = (m.group(1), m.group(3) or "") if m else ("", "")
        report = _load_json(path)
        if not isinstance(report, dict):
            report = {}
        hypothesis = _clean_str(
            report.get("hypothesis_id") or report.get("hypothesis")
        ) or f"H-{h_num}"
        last_updated = _iso_or_empty(
            report.get("run_ts") or report.get("run_date")
        )
        if not last_updated and file_date:
            last_updated = f"{file_date[:4]}-{file_date[4:6]}-{file_date[6:8]}"
        rows.append({
            "name": stem,
            "hypothesis": hypothesis,
            "status": _clean_str(report.get("run_mode")) or "reported",
            "n": _report_n(report),
            "verdict": _clean_str(report.get("verdict")),
            "last_updated": last_updated,
        })
    return rows


def build_sidecar(
    portfolios_path: Path | None = None,
    reports_dir: Path | None = None,
) -> dict:
    """Aggregate theory_portfolios.json + newest reports/h0XX_*.json."""
    portfolios_path = portfolios_path or DEFAULT_PORTFOLIOS
    reports_dir = reports_dir or DEFAULT_REPORTS_DIR
    rows = _portfolio_rows(_load_json(portfolios_path), portfolios_path)
    rows.extend(_report_rows(reports_dir))
    rows.sort(key=lambda r: r["name"].lower())
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "theories": rows,
    }


def write_sidecar(payload: dict, out_path: Path) -> Path:
    """Serialize strictly (allow_nan=False rejects any NaN/Infinity)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, allow_nan=False)
        fh.write("\n")
    return out_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--portfolios", type=Path, default=DEFAULT_PORTFOLIOS)
    ap.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    payload = build_sidecar(args.portfolios, args.reports_dir)
    write_sidecar(payload, args.out)
    print(f"Wrote {len(payload['theories'])} theory rows -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
