#!/usr/bin/env python3
"""
Quant Ops Monitor — Real-Time Health Checks (EAGLE2 synthesis)
==============================================================
  1. Concentration (HHI) — source, symbol
  2. Resolver dispute rate — EXPIRED mislabeling
  3. Per-class health — PF/WR vs thresholds
  4. Strategy lifecycle — cull / mutate / promote candidates
  5. freeze_promotions — block scaling when dispute/HHI red (blackboxai §4.2)
"""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

DASHBOARD_PATH = Path("audit_dashboard/data/dashboard_data.json")

CONCENTRATION_THRESHOLDS = {
    "hhi_warning": 0.25,
    "hhi_block": 0.40,
    "max_source_pct": 0.40,
    "max_symbol_pct": 0.20,
}

RESOLVER_THRESHOLDS = {
    "expired_positive_rate_max": 0.10,
    "unknown_exit_rate_max": 0.05,
    "disputed_rate_max": 0.02,
}

CLASS_HEALTH = {
    "CRYPTO": {"min_pf": 0.8, "min_wr": 0.40, "min_n": 50},
    "EQUITY": {"min_pf": 1.0, "min_wr": 0.45, "min_n": 30},
    "ETF": {"min_pf": 1.0, "min_wr": 0.45, "min_n": 20},
    "FOREX": {"min_pf": 0.8, "min_wr": 0.40, "min_n": 30},
    "COMMODITY": {"min_pf": 1.0, "min_wr": 0.45, "min_n": 15},
    "FUTURES": {"min_pf": 1.0, "min_wr": 0.45, "min_n": 10},
    "BOND": {"min_pf": 1.0, "min_wr": 0.45, "min_n": 10},
}


@dataclass
class ConcentrationReport:
    source_hhi: float
    symbol_hhi: float
    max_source_pct: float
    max_source_name: str
    max_symbol_pct: float
    max_symbol_name: str
    alerts: List[str]


@dataclass
class ResolverReport:
    total: int
    expired_positive_rate: float
    unknown_exit_rate: float
    sl_hit_rate: float
    tp_hit_rate: float
    time_exit_rate: float
    alerts: List[str]


@dataclass
class ClassHealthReport:
    asset_class: str
    pf: float
    wr: float
    n: int
    status: str
    issues: List[str]


@dataclass
class MonitorReport:
    timestamp: str
    concentration: ConcentrationReport
    resolver: ResolverReport
    class_health: Dict[str, ClassHealthReport]
    strategy_culling: Dict[str, str]
    alerts: List[str]
    freeze_promotions: bool = False


def load_dashboard() -> Dict:
    if DASHBOARD_PATH.exists():
        with open(DASHBOARD_PATH) as f:
            return json.load(f)
    return {}


def compute_concentration(closed: List[Dict]) -> ConcentrationReport:
    source_counts: Counter = Counter()
    symbol_counts: Counter = Counter()
    for p in closed:
        source_counts[p.get("source_system", p.get("strategy", "unknown"))] += 1
        symbol_counts[p.get("symbol", "unknown")] += 1

    total = len(closed) or 1

    def hhi(counts: Counter) -> float:
        shares = [c / total for c in counts.values()]
        return sum(s ** 2 for s in shares)

    src_hhi = hhi(source_counts)
    sym_hhi = hhi(symbol_counts)
    max_src = source_counts.most_common(1)[0] if source_counts else ("none", 0)
    max_sym = symbol_counts.most_common(1)[0] if symbol_counts else ("none", 0)

    alerts: List[str] = []
    if src_hhi > CONCENTRATION_THRESHOLDS["hhi_warning"]:
        alerts.append(f"SOURCE_HHI={src_hhi:.3f}")
    if max_src[1] / total > CONCENTRATION_THRESHOLDS["max_source_pct"]:
        alerts.append(f"SOURCE_CONCENTRATION: {max_src[0]} = {max_src[1]/total:.1%}")

    return ConcentrationReport(
        source_hhi=src_hhi,
        symbol_hhi=sym_hhi,
        max_source_pct=max_src[1] / total,
        max_source_name=max_src[0],
        max_symbol_pct=max_sym[1] / total,
        max_symbol_name=max_sym[0],
        alerts=alerts,
    )


def compute_resolver_health(closed: List[Dict]) -> ResolverReport:
    total = len(closed) or 1
    expired = [p for p in closed if p.get("exit_reason") == "EXPIRED"]
    expired_positive = sum(1 for p in expired if (p.get("pnl_pct", 0) or 0) > 0)
    expired_pos_rate = expired_positive / len(expired) if expired else 0.0

    unknown = sum(1 for p in closed if p.get("exit_reason") == "UNKNOWN")
    sl_hits = sum(1 for p in closed if p.get("exit_reason") == "SL_HIT")
    tp_hits = sum(1 for p in closed if p.get("exit_reason") == "TP_HIT")
    time_exits = sum(1 for p in closed if p.get("exit_reason") == "TIME_EXIT")

    alerts: List[str] = []
    if expired_pos_rate > RESOLVER_THRESHOLDS["expired_positive_rate_max"]:
        alerts.append(f"EXPIRED_POSITIVE_RATE={expired_pos_rate:.1%}")

    return ResolverReport(
        total=total,
        expired_positive_rate=expired_pos_rate,
        unknown_exit_rate=unknown / total,
        sl_hit_rate=sl_hits / total,
        tp_hit_rate=tp_hits / total,
        time_exit_rate=time_exits / total,
        alerts=alerts,
    )


def compute_class_health(closed: List[Dict]) -> Dict[str, ClassHealthReport]:
    class_trades: Dict[str, List] = defaultdict(list)
    for p in closed:
        class_trades[p.get("asset_class", "UNKNOWN")].append(p)

    reports = {}
    for ac, trades in class_trades.items():
        pnls = [t.get("pnl_pct", 0) or 0 for t in trades]
        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p < 0)
        n = wins + losses
        wr = wins / n if n > 0 else 0.0
        pf = wins / losses if losses > 0 else (999.0 if wins > 0 else 0.0)

        threshold = CLASS_HEALTH.get(ac, CLASS_HEALTH["EQUITY"])
        issues: List[str] = []
        if n < threshold["min_n"]:
            status = "INSUFFICIENT"
            issues.append(f"n={n}<{threshold['min_n']}")
        elif pf < threshold["min_pf"] or wr < threshold["min_wr"]:
            status = "DEGRADED"
            issues.append(f"PF={pf:.2f} WR={wr:.1%}")
        else:
            status = "HEALTHY"

        reports[ac] = ClassHealthReport(ac, pf, wr, n, status, issues)
    return reports


def compute_strategy_culling(systems: List[Dict]) -> Dict[str, str]:
    culling = {}
    for sys in systems:
        name = sys.get("name", "?")
        wins = sys.get("wins", 0)
        losses = sys.get("losses", 0)
        n = sys.get("closed_picks", 0)
        wr = sys.get("win_rate", 0) or 0
        total = wins + losses
        if total == 0:
            culling[name] = "NO_DATA"
        elif n < 10:
            culling[name] = "ACCUMULATING"
        elif (wins / losses if losses else 999) >= 1.5 and wr >= 50:
            culling[name] = "PROMOTE_CANDIDATE"
        elif (wins / losses if losses else 0) >= 1.0:
            culling[name] = "MONITOR"
        elif (wins / losses if losses else 0) >= 0.7:
            culling[name] = "MUTATE_CANDIDATE"
        else:
            culling[name] = "CULL_CANDIDATE"
    return culling


def run_full_monitor() -> MonitorReport:
    import pandas as pd

    data = load_dashboard()
    closed = data.get("picks", {}).get("recent_closed", [])
    systems = data.get("systems", [])

    conc = compute_concentration(closed)
    resolver = compute_resolver_health(closed)
    class_health = compute_class_health(closed)
    culling = compute_strategy_culling(systems)

    all_alerts = conc.alerts + resolver.alerts
    for ac, rep in class_health.items():
        if rep.status == "DEGRADED":
            all_alerts.append(f"CLASS_DEGRADED: {ac}")

    freeze = (
        conc.source_hhi >= CONCENTRATION_THRESHOLDS["hhi_block"]
        or resolver.expired_positive_rate > RESOLVER_THRESHOLDS["expired_positive_rate_max"]
        or conc.max_source_pct > CONCENTRATION_THRESHOLDS["max_source_pct"]
    )
    if freeze:
        all_alerts.append("FREEZE_PROMOTIONS")

    return MonitorReport(
        timestamp=pd.Timestamp.now().isoformat(),
        concentration=conc,
        resolver=resolver,
        class_health=class_health,
        strategy_culling=culling,
        alerts=all_alerts,
        freeze_promotions=freeze,
    )


if __name__ == "__main__":
    report = run_full_monitor()
    print(f"QUANT MONITOR {report.timestamp} freeze={report.freeze_promotions}")
    for a in report.alerts:
        print(f"  ! {a}")

    out = Path("reports/quant_monitor_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(
            {
                "timestamp": report.timestamp,
                "alerts": report.alerts,
                "freeze_promotions": report.freeze_promotions,
                "concentration_hhi": report.concentration.source_hhi,
                "resolver_dispute_rate": report.resolver.expired_positive_rate,
            },
            f,
            indent=2,
        )
    print(f"Wrote {out}")
