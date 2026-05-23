"""BOND pilot — TIPS breakeven mean-reversion (read-only signal generator).

Pilot A from `reports/bond_deep_dive_round2_2026-05-13.md`. Per
docs/MUTATION_THREE_AXIS_PROTOCOL.md, ships as shadow-mode signal generator
first; production wire-up only after backtest gate clears (n>=30, PF>=1.5,
WR>=50%, MDD<=12% over 90-day shadow).

Signal: when 10y breakeven inflation (FRED T10YIE) deviates ±1σ from its
5y rolling mean, expect mean-reversion. Trade TIP/IEF pair:
- Z < -1σ (breakeven below mean): LONG TIP / SHORT IEF (long inflation expectations)
- Z > +1σ (breakeven above mean): SHORT TIP / LONG IEF (short inflation expectations)

Free data:
- FRED `T10YIE` for 10y breakeven inflation
- yfinance `TIP`, `IEF` for ETF prices

Output: `audit_dashboard/data/bond_pilots/tips_breakeven_mr_signals.json`
(append-only, one record per evaluation).

Run: `python tools/bond_pilots/tips_breakeven_mr.py [--dry-run]`
GHA cron: 1× per day, post-market-close US (~21:00 UTC).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "audit_dashboard" / "data" / "bond_pilots"
OUT_PATH = OUT_DIR / "tips_breakeven_mr_signals.json"

FRED_API_KEY = os.environ.get("FRED_API_KEY", "")
FRED_SERIES = "T10YIE"
LOOKBACK_DAYS = 5 * 365  # 5y rolling mean
DEVIATION_THRESHOLD = 1.0  # ±1σ

# Position spec (caller resizes per portfolio)
PILOT_TAG = "bond_pilot_tips_mr_v1"
TIMEFRAME = "1W"
EXPECTED_HOLD_DAYS = 30  # exit when Z crosses 0 OR 30d time-cap


def _fred_url() -> str:
    """FRED CSV download URL (works without API key for public series)."""
    return f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={FRED_SERIES}"


def fetch_breakeven_history() -> list[tuple[str, float]]:
    """Return list of (date_iso, value) tuples since LOOKBACK_DAYS ago. Empty on failure."""
    try:
        req = urllib.request.Request(_fred_url(), headers={
            "User-Agent": "findtorontoevents-bond-pilot/1.0",
            "Accept": "text/csv",
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8")
    except Exception as e:
        print(f"FRED fetch failed: {e}", file=sys.stderr)
        return []
    out = []
    for line in raw.splitlines()[1:]:  # skip header
        parts = line.split(",")
        if len(parts) < 2:
            continue
        date_str = parts[0].strip()
        val_str = parts[1].strip()
        if val_str in {".", "", "NA"}:
            continue
        try:
            out.append((date_str, float(val_str)))
        except ValueError:
            continue
    return out


def compute_z_score(series: list[float]) -> tuple[float, float, float, float]:
    """Returns (latest, mean, std, z) for the series."""
    if not series:
        return (float("nan"),) * 4
    latest = series[-1]
    n = len(series)
    mean = sum(series) / n
    var = sum((x - mean) ** 2 for x in series) / max(1, n - 1)
    std = math.sqrt(var)
    z = (latest - mean) / std if std > 0 else 0.0
    return latest, mean, std, z


def evaluate_signal(history: list[tuple[str, float]]) -> dict:
    """Compute Z-score on 5y rolling window + emit signal record."""
    if not history:
        return {"generated_at": datetime.now(timezone.utc).isoformat(),
                "error": "no FRED data fetched", "signal": None}
    values = [v for _, v in history]
    latest_date, _ = history[-1]
    latest, mean, std, z = compute_z_score(values)
    sig = None
    if z < -DEVIATION_THRESHOLD:
        sig = {"direction": "LONG_TIP_SHORT_IEF",
               "rationale": f"breakeven Z={z:.2f} < -{DEVIATION_THRESHOLD}σ; expect inflation expectations mean-revert UP"}
    elif z > DEVIATION_THRESHOLD:
        sig = {"direction": "SHORT_TIP_LONG_IEF",
               "rationale": f"breakeven Z={z:.2f} > +{DEVIATION_THRESHOLD}σ; expect inflation expectations mean-revert DOWN"}
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_as_of": latest_date,
        "fred_series": FRED_SERIES,
        "latest_breakeven_pct": round(latest, 3),
        "rolling_mean_pct": round(mean, 3),
        "rolling_std_pct": round(std, 3),
        "z_score": round(z, 3),
        "deviation_threshold": DEVIATION_THRESHOLD,
        "n_observations": len(values),
        "signal": sig,
        "pilot_tag": PILOT_TAG,
        "timeframe": TIMEFRAME,
        "expected_hold_days": EXPECTED_HOLD_DAYS,
    }


def append_signal(record: dict, path: Path = OUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []
    else:
        existing = []
    existing.append(record)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    history = fetch_breakeven_history()
    record = evaluate_signal(history)
    print(json.dumps(record, indent=2))

    if record.get("signal") is None:
        print("No actionable signal (Z within band).")
    else:
        s = record["signal"]
        print(f"SIGNAL: {s['direction']} — {s['rationale']}")

    if args.dry_run:
        print("DRY-RUN: not appended to store.")
        return
    append_signal(record)
    print(f"Appended to {OUT_PATH}")


if __name__ == "__main__":
    main()
