#!/usr/bin/env python3
"""§1 Regime-segmented performance stub (Mercury / HEDGE_FUND plan).

Labels each closed pick's **UTC calendar day** with a coarse **BTC regime** derived from
**Binance spot** daily close-to-close return (public ``/api/v3/klines``, no key):

  * **CRISIS** — R ≤ −3%
  * **BEAR**   — −3% < R ≤ −0.5%
  * **SIDEWAYS** — −0.5% < R < +0.5%
  * **BULL**   — R ≥ +0.5%

Then computes **per-regime** metrics on ``pnl_pct`` (trade-level, same scaling spirit as
other audit stubs):

  * **sharpe_like** = mean / std × √n  (if std > 0)
  * **sortino_like** = mean / downside_dev × √n  (target 0; semi-deviation of losses)
  * **calmar_like** = sum(pnl) / |max_drawdown_on_cum_path|  (if drawdown ≠ 0)

Only regimes with ≥ ``--min-trades`` closes are reported.

Output: ``tools/data/regime_performance_btc_report.json``

Usage:
  python tools/regime_performance_btc_stub.py
  python tools/regime_performance_btc_stub.py --min-trades 20 --redis-alert
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import numpy as np

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO / "tools" / "data" / "regime_performance_btc_report.json"

KLINES_URL = (
    "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=%d"
)
UA = "findtorontoevents-regime-perf/1.0 (+https://findtorontoevents.ca)"


def parse_ts(ts_str: Any) -> Optional[datetime]:
    if not ts_str:
        return None
    s = str(ts_str).replace("+00:00", "Z").rstrip("Z")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def fetch_btc_daily_closes(limit: int = 120) -> List[Tuple[datetime.date, float]]:
    """Return list of (date_utc, close_price) sorted by date."""
    url = KLINES_URL % limit
    req = Request(url, headers={"User-Agent": UA})
    try:
        with urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
    except (HTTPError, URLError, OSError, ValueError) as e:
        raise RuntimeError("binance_klines_failed: %s" % e) from e
    rows = json.loads(raw)
    out: List[Tuple[datetime.date, float]] = []
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) < 5:
            continue
        t_ms = int(row[0])
        close = float(row[4])
        d = datetime.fromtimestamp(t_ms / 1000.0, tz=timezone.utc).date()
        out.append((d, close))
    out.sort(key=lambda x: x[0])
    return out


def build_date_regime(closes: List[Tuple[datetime.date, float]]) -> Dict[datetime.date, str]:
    """Map candle date -> regime label using close-to-close return ending that day."""
    reg: Dict[datetime.date, str] = {}
    for i in range(1, len(closes)):
        d, c = closes[i]
        _, c0 = closes[i - 1]
        if c0 <= 0:
            continue
        r = (c / c0) - 1.0
        if r <= -0.03:
            lab = "CRISIS"
        elif r <= -0.005:
            lab = "BEAR"
        elif r >= 0.005:
            lab = "BULL"
        else:
            lab = "SIDEWAYS"
        reg[d] = lab
    return reg


def sharpe_like(a: np.ndarray) -> float:
    if len(a) < 2:
        return 0.0
    m = float(a.mean())
    s = float(a.std(ddof=1))
    if s < 1e-12:
        return 0.0
    return (m / s) * math.sqrt(float(len(a)))


def sortino_like(a: np.ndarray, target: float = 0.0) -> float:
    if len(a) < 2:
        return 0.0
    mu = float(a.mean())
    downside = a[a < target] - target
    if len(downside) == 0:
        return 0.0 if mu <= target else float("inf")
    dd = float(np.sqrt(np.mean(downside.astype(np.float64) ** 2)))
    if dd < 1e-12:
        return 0.0
    return ((mu - target) / dd) * math.sqrt(float(len(a)))


def calmar_like(a: np.ndarray) -> Optional[float]:
    if len(a) == 0:
        return None
    cum = np.cumsum(a.astype(np.float64))
    peak = np.maximum.accumulate(cum)
    mdd = float((cum - peak).min())
    total = float(cum[-1])
    if mdd >= -1e-9:
        return None
    return total / abs(mdd)


def metrics_for_regime(pnls: List[float], min_trades: int) -> Optional[Dict[str, Any]]:
    if len(pnls) < min_trades:
        return None
    a = np.array(pnls, dtype=np.float64)
    sl = sortino_like(a)
    cm = calmar_like(a)
    return {
        "n_trades": len(pnls),
        "mean_pnl_pct": round(float(a.mean()), 6),
        "win_rate_pct": round(float(np.mean(a > 0)) * 100.0, 2),
        "sharpe_like": round(sharpe_like(a), 6),
        "sortino_like": round(sl, 6) if sl != float("inf") else None,
        "calmar_like": round(cm, 6) if cm is not None else None,
        "sum_pnl_pct": round(float(a.sum()), 6),
    }


def redis_broadcast(msg: str) -> None:
    bus = Path(r"C:\Users\zerou\redis-bus\agent_bus.py")
    if not bus.is_file():
        return
    try:
        subprocess.run(
            [sys.executable, str(bus), "broadcast", "cursor-composer", msg],
            check=False,
            timeout=20,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dashboard", type=str, default=str(DEFAULT_DASHBOARD))
    ap.add_argument("--out", type=str, default=str(OUT_JSON))
    ap.add_argument("--min-trades", type=int, default=15)
    ap.add_argument("--klines-limit", type=int, default=120)
    ap.add_argument("--crypto-only", action="store_true")
    ap.add_argument("--redis-alert", action="store_true")
    args = ap.parse_args()

    path = Path(args.dashboard)
    if not path.is_file():
        print("ERROR: dashboard not found: %s" % path, file=sys.stderr)
        return 1

    try:
        closes = fetch_btc_daily_closes(args.klines_limit)
    except RuntimeError as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 1

    date_regime = build_date_regime(closes)
    by_reg: Dict[str, List[float]] = defaultdict(list)
    unknown = 0

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    picks = (data.get("picks") or {}).get("recent_closed") or []
    for p in picks:
        if not isinstance(p, dict):
            continue
        if args.crypto_only and str(p.get("asset_class") or "").upper() != "CRYPTO":
            continue
        ts = parse_ts(p.get("closed_at"))
        if ts is None:
            continue
        d = ts.date()
        lab = date_regime.get(d)
        if lab is None:
            unknown += 1
            continue
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue
        try:
            by_reg[lab].append(float(pnl))
        except (TypeError, ValueError):
            continue

    per: Dict[str, Any] = {}
    for lab in ("BULL", "SIDEWAYS", "BEAR", "CRISIS"):
        m = metrics_for_regime(by_reg.get(lab, []), args.min_trades)
        if m:
            per[lab] = m

    report: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_dashboard": str(path).replace("\\", "/"),
        "btc_data": {
            "source": "api.binance.com /api/v3/klines BTCUSDT 1d",
            "candles_used": len(closes),
            "regime_thresholds": {
                "crisis_r_leq": -0.03,
                "bear_r_leq": -0.005,
                "bull_r_geq": 0.005,
                "otherwise": "SIDEWAYS",
            },
        },
        "config": {
            "min_trades": args.min_trades,
            "crypto_only": args.crypto_only,
        },
        "summary": {
            "closed_picks_assigned": sum(len(v) for v in by_reg.values()),
            "closed_picks_unknown_regime_day": unknown,
            "regimes_reported": list(per.keys()),
        },
        "per_regime": per,
        "note": "BTC daily close-to-close labels are a coarse macro proxy, not strategy-native HMM. Sharpe/Sortino/Calmar are trade-PnL heuristics.",
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(
        "assigned=%s regimes=%s -> %s"
        % (report["summary"]["closed_picks_assigned"], list(per.keys()), out_path)
    )

    if args.redis_alert:
        redis_broadcast(
            "HEDGE_PLAN §1 regime-perf-BTC-stub: assigned=%s regimes=%s | %s"
            % (
                report["summary"]["closed_picks_assigned"],
                list(per.keys()),
                str(out_path).replace("\\", "/"),
            )
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
