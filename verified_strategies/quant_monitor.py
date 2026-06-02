#!/usr/bin/env python3
"""
Quant Ops Monitor — Real-Time Health Checks
=============================================
Monitors:
  1. Concentration (HHI) — source, symbol, class level
  2. Resolver dispute rate — EXPIRED mislabeling, UNKNOWN exits
  3. Per-class health — PF/WR/MDD vs thresholds
  4. Strategy lifecycle — emitter culling, promotion readiness

Run as: python3 -m verified_strategies.quant_monitor
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

DASHBOARD_PATH = Path("audit_dashboard/data/dashboard_data.json")

# ── Thresholds ──────────────────────────────────────────────────────

CONCENTRATION_THRESHOLDS = {
    'hhi_warning': 0.25,
    'hhi_block': 0.40,
    'max_source_pct': 0.40,
    'max_symbol_pct': 0.20,
}

RESOLVER_THRESHOLDS = {
    'expired_positive_rate_max': 0.10,  # EXPIRED picks with positive PnL
    'unknown_exit_rate_max': 0.05,      # UNKNOWN exit reason
    'disputed_rate_max': 0.02,           # Disputed cohorts
}

CLASS_HEALTH = {
    'CRYPTO':    {'min_pf': 0.8, 'min_wr': 0.40, 'max_dd': 0.25, 'min_n': 50},
    'EQUITY':    {'min_pf': 1.0, 'min_wr': 0.45, 'max_dd': 0.15, 'min_n': 30},
    'ETF':       {'min_pf': 1.0, 'min_wr': 0.45, 'max_dd': 0.15, 'min_n': 20},
    'FOREX':     {'min_pf': 0.8, 'min_wr': 0.40, 'max_dd': 0.20, 'min_n': 30},
    'COMMODITY': {'min_pf': 1.0, 'min_wr': 0.45, 'max_dd': 0.20, 'min_n': 15},
    'FUTURES':   {'min_pf': 1.0, 'min_wr': 0.45, 'max_dd': 0.20, 'min_n': 10},
    'BOND':      {'min_pf': 1.0, 'min_wr': 0.45, 'max_dd': 0.10, 'min_n': 10},
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
    status: str  # HEALTHY / DEGRADED / DEAD / INSUFFICIENT
    issues: List[str]


@dataclass
class MonitorReport:
    timestamp: str
    concentration: ConcentrationReport
    resolver: ResolverReport
    class_health: Dict[str, ClassHealthReport]
    strategy_culling: Dict[str, str]
    alerts: List[str]


def load_dashboard() -> Dict:
    if DASHBOARD_PATH.exists():
        with open(DASHBOARD_PATH) as f:
            return json.load(f)
    return {}


def compute_concentration(closed: List[Dict]) -> ConcentrationReport:
    """Compute HHI and max concentration by source and symbol."""
    source_counts = Counter()
    symbol_counts = Counter()

    for p in closed:
        src = p.get('source_system', p.get('strategy', 'unknown'))
        sym = p.get('symbol', 'unknown')
        source_counts[src] += 1
        symbol_counts[sym] += 1

    total = len(closed) or 1

    def hhi(counts: Counter) -> float:
        shares = [c / total for c in counts.values()]
        return sum(s ** 2 for s in shares)

    src_hhi = hhi(source_counts)
    sym_hhi = hhi(symbol_counts)

    max_src = source_counts.most_common(1)[0] if source_counts else ('none', 0)
    max_sym = symbol_counts.most_common(1)[0] if symbol_counts else ('none', 0)

    alerts = []
    if src_hhi > CONCENTRATION_THRESHOLDS['hhi_warning']:
        alerts.append(f"SOURCE_HHI={src_hhi:.3f} > {CONCENTRATION_THRESHOLDS['hhi_warning']}")
    if sym_hhi > CONCENTRATION_THRESHOLDS['hhi_warning']:
        alerts.append(f"SYMBOL_HHI={sym_hhi:.3f} > {CONCENTRATION_THRESHOLDS['hhi_warning']}")
    if max_src[1] / total > CONCENTRATION_THRESHOLDS['max_source_pct']:
        alerts.append(f"SOURCE_CONCENTRATION: {max_src[0]} = {max_src[1]/total:.1%}")
    if max_sym[1] / total > CONCENTRATION_THRESHOLDS['max_symbol_pct']:
        alerts.append(f"SYMBOL_CONCENTRATION: {max_sym[0]} = {max_sym[1]/total:.1%}")

    return ConcentrationReport(
        source_hhi=src_hhi, symbol_hhi=sym_hhi,
        max_source_pct=max_src[1] / total, max_source_name=max_src[0],
        max_symbol_pct=max_sym[1] / total, max_symbol_name=max_sym[0],
        alerts=alerts,
    )


def compute_resolver_health(closed: List[Dict]) -> ResolverReport:
    """Check resolver label quality."""
    total = len(closed) or 1

    expired = [p for p in closed if p.get('exit_reason') == 'EXPIRED']
    expired_positive = sum(1 for p in expired if (p.get('pnl_pct', 0) or 0) > 0)
    expired_pos_rate = expired_positive / len(expired) if expired else 0

    unknown = sum(1 for p in closed if p.get('exit_reason') == 'UNKNOWN')
    sl_hits = sum(1 for p in closed if p.get('exit_reason') == 'SL_HIT')
    tp_hits = sum(1 for p in closed if p.get('exit_reason') == 'TP_HIT')
    time_exits = sum(1 for p in closed if p.get('exit_reason') == 'TIME_EXIT')

    alerts = []
    if expired_pos_rate > RESOLVER_THRESHOLDS['expired_positive_rate_max']:
        alerts.append(f"EXPIRED_POSITIVE_RATE={expired_pos_rate:.1%} — possible mislabeling")
    if unknown / total > RESOLVER_THRESHOLDS['unknown_exit_rate_max']:
        alerts.append(f"UNKNOWN_EXIT_RATE={unknown/total:.1%}")

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
    """Per-class health check against thresholds."""
    class_trades = defaultdict(list)
    for p in closed:
        ac = p.get('asset_class', 'UNKNOWN')
        class_trades[ac].append(p)

    reports = {}
    for ac, trades in class_trades.items():
        pnls = [t.get('pnl_pct', 0) or 0 for t in trades]
        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p < 0)
        n = wins + losses
        wr = wins / n if n > 0 else 0
        # PF = gross profit / gross loss (sum of pnl), NOT win/loss counts — PR #464.
        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = -sum(p for p in pnls if p < 0)
        pf = gross_profit / gross_loss if gross_loss > 0 else (999 if gross_profit > 0 else 0)

        threshold = CLASS_HEALTH.get(ac, CLASS_HEALTH.get('EQUITY'))
        issues = []

        if n < threshold['min_n']:
            status = 'INSUFFICIENT'
            issues.append(f"n={n} < {threshold['min_n']}")
        elif pf < threshold['min_pf']:
            status = 'DEGRADED'
            issues.append(f"PF={pf:.2f} < {threshold['min_pf']}")
        elif wr < threshold['min_wr']:
            status = 'DEGRADED'
            issues.append(f"WR={wr:.1%} < {threshold['min_wr']:.0%}")
        else:
            status = 'HEALTHY'

        reports[ac] = ClassHealthReport(
            asset_class=ac, pf=pf, wr=wr, n=n,
            status=status, issues=issues,
        )

    return reports


def compute_strategy_culling(systems: List[Dict]) -> Dict[str, str]:
    """Identify strategies that should be culled or promoted."""
    culling = {}
    for sys in systems:
        name = sys.get('name', '?')
        n = sys.get('closed_picks', 0)
        wins = sys.get('wins', 0)
        losses = sys.get('losses', 0)
        wr = sys.get('win_rate', 0) or 0

        total = wins + losses
        if total == 0:
            culling[name] = 'NO_DATA'
            continue

        # Prefer the dashboard's authoritative gross-based profit_factor; fall
        # back to gross_win/gross_loss. Win/loss COUNT ratio is wrong (PR #464)
        # and is only a last resort when no pnl-magnitude data is present.
        pf = sys.get('profit_factor')
        if pf is None:
            gross_win = sys.get('gross_win')
            gross_loss = abs(sys.get('gross_loss') or 0)
            if gross_win is not None and gross_loss > 0:
                pf = gross_win / gross_loss
            elif gross_win and gross_loss == 0:
                pf = 999
            else:
                pf = wins / losses if losses > 0 else 999

        if n < 10:
            culling[name] = 'ACCUMULATING'
        elif pf >= 1.5 and wr >= 50:
            culling[name] = 'PROMOTE_CANDIDATE'
        elif pf >= 1.0:
            culling[name] = 'MONITOR'
        elif pf >= 0.7:
            culling[name] = 'MUTATE_CANDIDATE'
        else:
            culling[name] = 'CULL_CANDIDATE'

    return culling


def run_full_monitor() -> MonitorReport:
    """Run all monitoring checks."""
    import pandas as pd

    data = load_dashboard()
    closed = data.get('picks', {}).get('recent_closed', [])
    systems = data.get('systems', [])

    conc = compute_concentration(closed)
    resolver = compute_resolver_health(closed)
    class_health = compute_class_health(closed)
    culling = compute_strategy_culling(systems)

    all_alerts = conc.alerts + resolver.alerts
    for ac, report in class_health.items():
        if report.status == 'DEGRADED':
            all_alerts.append(f"CLASS_DEGRADED: {ac} — {', '.join(report.issues)}")

    return MonitorReport(
        timestamp=pd.Timestamp.now().isoformat(),
        concentration=conc,
        resolver=resolver,
        class_health=class_health,
        strategy_culling=culling,
        alerts=all_alerts,
    )


def print_report(report: MonitorReport):
    """Pretty-print the monitor report."""
    print(f"\n{'='*60}")
    print(f"QUANT OPS MONITOR — {report.timestamp}")
    print(f"{'='*60}")

    print(f"\n--- CONCENTRATION ---")
    print(f"  Source HHI:  {report.concentration.source_hhi:.3f}")
    print(f"  Symbol HHI:  {report.concentration.symbol_hhi:.3f}")
    print(f"  Top source:  {report.concentration.max_source_name} ({report.concentration.max_source_pct:.1%})")
    print(f"  Top symbol:  {report.concentration.max_symbol_name} ({report.concentration.max_symbol_pct:.1%})")

    print(f"\n--- RESOLVER HEALTH ---")
    print(f"  SL hit rate:       {report.resolver.sl_hit_rate:.1%}")
    print(f"  TP hit rate:       {report.resolver.tp_hit_rate:.1%}")
    print(f"  Time exit rate:    {report.resolver.time_exit_rate:.1%}")
    print(f"  EXPIRED positive:  {report.resolver.expired_positive_rate:.1%}")
    print(f"  UNKNOWN exits:     {report.resolver.unknown_exit_rate:.1%}")

    print(f"\n--- CLASS HEALTH ---")
    for ac, r in sorted(report.class_health.items()):
        print(f"  {ac:12s}  PF={r.pf:>7.2f}  WR={r.wr:>5.1%}  n={r.n:>5d}  {r.status}")

    print(f"\n--- STRATEGY CULLING ---")
    categories = defaultdict(list)
    for name, status in report.strategy_culling.items():
        categories[status].append(name)

    for cat in ['PROMOTE_CANDIDATE', 'MONITOR', 'MUTATE_CANDIDATE', 'CULL_CANDIDATE', 'ACCUMULATING', 'NO_DATA']:
        names = categories.get(cat, [])
        if names:
            print(f"  {cat}: {len(names)} strategies")

    if report.alerts:
        print(f"\n--- ALERTS ({len(report.alerts)}) ---")
        for a in report.alerts:
            print(f"  ⚠ {a}")
    else:
        print(f"\n--- NO ALERTS ---")


if __name__ == "__main__":
    report = run_full_monitor()
    print_report(report)

    output = Path("reports/quant_monitor_report.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'w') as f:
        json.dump({
            'timestamp': report.timestamp,
            'alerts': report.alerts,
            'concentration_hhi': report.concentration.source_hhi,
            'resolver_dispute_rate': report.resolver.expired_positive_rate,
        }, f, indent=2)
    print(f"\nReport saved to {output}")
