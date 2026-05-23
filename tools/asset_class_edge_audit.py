#!/usr/bin/env python3
"""Read-only asset-class edge audit for the /audit payload.

This helper is intentionally stdlib-only and does not touch live ledgers.
It summarizes:
  - closed-pick performance by asset class
  - recent windows (30 / 100 / 250)
  - strongest strategy + direction pockets inside each class
  - which score fields actually separate winners from losers
  - the current UEPS / PEAD live-book gap

Usage:
    python tools/asset_class_edge_audit.py
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parent.parent
PAYLOAD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
ACTIVE_PICKS = REPO / "alpha_engine" / "data" / "active_picks.json"
UEPS_PICKS = REPO / "audit_dashboard" / "data" / "ueps_picks.json"

WINDOWS = (30, 100, 250)
SIGNAL_FIELDS = ("trust_score", "strat_fwd_wr", "strat_fwd_pf", "confidence")

# Without this filter, closed-pocket aggregates over-credit symbols that the
# live gate now blocks (PR #535 sub-class kill, etc.) — yielding "edge" that is
# not reachable going forward. Mirror the in-tree blacklists rather than
# re-importing, to keep this tool stdlib-only.
COMMODITY_BLACKLIST = frozenset({
    "CL=F", "BZ=F", "HO=F", "RB=F", "NG=F",
    "ZC=F", "ZS=F", "ZW=F", "LE=F", "HE=F", "KC=F", "CT=F",
    "SI=F", "GC=F",
})


def _is_blacklisted(row: dict[str, Any]) -> bool:
    cls = str(row.get("asset_class") or row.get("category") or "").upper()
    sym = str(row.get("symbol") or "").upper()
    if cls == "COMMODITY" and sym in COMMODITY_BLACKLIST:
        return True
    return False


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_rows(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return [row for row in obj if isinstance(row, dict)]
    if isinstance(obj, dict):
        for key in ("picks", "active_picks", "active", "rows", "signals"):
            val = obj.get(key)
            if isinstance(val, list):
                return [row for row in val if isinstance(row, dict)]
    return []


def _num(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _pnl(row: dict[str, Any]) -> float | None:
    for key in ("pnl_pct", "realized_pnl_pct", "unrealized_pnl_pct"):
        val = _num(row.get(key))
        if val is not None:
            return val
    return None


def _wr(rows: list[dict[str, Any]]) -> float | None:
    pnls = [_pnl(row) for row in rows]
    pnls = [p for p in pnls if p is not None]
    if not pnls:
        return None
    return sum(1 for p in pnls if p > 0) / len(pnls)


def _pf(rows: list[dict[str, Any]]) -> float | None:
    gross_profit = sum((_pnl(row) or 0.0) for row in rows if (_pnl(row) or 0.0) > 0)
    gross_loss = -sum((_pnl(row) or 0.0) for row in rows if (_pnl(row) or 0.0) < 0)
    if gross_loss == 0:
        return None if gross_profit == 0 else math.inf
    return gross_profit / gross_loss


def _sum_pnl(rows: list[dict[str, Any]]) -> float:
    return sum(_pnl(row) or 0.0 for row in rows)


def _pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def _pf_str(value: float | None) -> str:
    if value is None:
        return "n/a"
    if math.isinf(value):
        return "inf"
    return f"{value:.3f}"


def _bucket_by_rank(rows: list[dict[str, Any]], field: str, buckets: int = 3) -> list[tuple[str, list[dict[str, Any]]]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        val = _num(row.get(field))
        if val is not None:
            scored.append((val, row))
    if len(scored) < buckets:
        return []
    scored.sort(key=lambda item: item[0])
    n = len(scored)
    labels = ("low", "mid", "high") if buckets == 3 else tuple(f"bucket_{i+1}" for i in range(buckets))
    out: list[tuple[str, list[dict[str, Any]]]] = []
    for idx in range(buckets):
        start = (idx * n) // buckets
        end = ((idx + 1) * n) // buckets
        out.append((labels[idx], [row for _, row in scored[start:end]]))
    return out


def _asset_class(row: dict[str, Any]) -> str:
    return str(row.get("asset_class") or row.get("category") or "UNKNOWN").upper()


def _print_table(title: str, lines: list[str]) -> None:
    print(f"\n## {title}")
    for line in lines:
        print(line)


def main() -> int:
    payload = _load_json(PAYLOAD)
    picks = payload.get("picks", {}) if isinstance(payload, dict) else {}
    recent_closed_all = _to_rows(picks.get("recent_closed"))
    active_raw = _to_rows(picks.get("active_raw"))

    n_pre = len(recent_closed_all)
    recent_closed = [r for r in recent_closed_all if not _is_blacklisted(r)]
    n_filtered = n_pre - len(recent_closed)

    _print_table(
        "Inputs",
        [
            f"- payload: {PAYLOAD}",
            f"- recent_closed rows (raw): {n_pre}",
            f"- recent_closed rows after blacklist filter: {len(recent_closed)} (dropped {n_filtered})",
            f"- active_raw rows: {len(active_raw)}",
            "- blacklist filter: drops COMMODITY rows whose symbol is in COMMODITY_BLACKLIST",
            "  (PR #535 sub-class kill — those rows can no longer be replicated by the live gate)",
        ],
    )

    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in recent_closed:
        by_class[_asset_class(row)].append(row)

    summary_lines = [
        "| Asset Class | n | WR | PF | Sum PnL% |",
        "|---|---:|---:|---:|---:|",
    ]
    for asset_class, rows in sorted(by_class.items(), key=lambda item: (-len(item[1]), item[0])):
        summary_lines.append(
            f"| {asset_class} | {len(rows)} | {_pct(_wr(rows))} | {_pf_str(_pf(rows))} | {_sum_pnl(rows):.3f} |"
        )
    _print_table("Closed Performance By Asset Class", summary_lines)

    window_lines = ["| Asset Class | Window | n | WR | PF | Sum PnL% |", "|---|---:|---:|---:|---:|---:|"]
    for asset_class in sorted(by_class):
        rows = by_class[asset_class]
        for window in WINDOWS:
            sample = rows[-window:] if len(rows) >= window else rows
            window_lines.append(
                f"| {asset_class} | {window} | {len(sample)} | {_pct(_wr(sample))} | {_pf_str(_pf(sample))} | {_sum_pnl(sample):.3f} |"
            )
    _print_table("Recent Windows", window_lines)

    top_strategy_lines = ["| Asset Class | Strategy | Direction | n | WR | PF | Sum PnL% |", "|---|---|---|---:|---:|---:|---:|"]
    for asset_class in sorted(by_class):
        strat_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in by_class[asset_class]:
            key = (str(row.get("strategy") or "?"), str(row.get("direction") or "?"))
            strat_groups[key].append(row)
        ranked: list[tuple[float, float, float, int, str, str]] = []
        for (strategy, direction), rows in strat_groups.items():
            if len(rows) < 12:
                continue
            pf = _pf(rows)
            pnl_sum = _sum_pnl(rows)
            if pf is None or math.isinf(pf) or pnl_sum <= 0:
                continue
            ranked.append((pf, pnl_sum, _wr(rows) or 0.0, len(rows), strategy, direction))
        ranked.sort(reverse=True)
        for pf, pnl_sum, wr, n, strategy, direction in ranked[:5]:
            top_strategy_lines.append(
                f"| {asset_class} | {strategy} | {direction} | {n} | {_pct(wr)} | {_pf_str(pf)} | {pnl_sum:.3f} |"
            )
    _print_table("Top Strategy Pockets (min n=12, positive aggregate PnL)", top_strategy_lines)

    field_lines = ["| Asset Class | Field | Bucket | n | WR | PF | Sum PnL% |", "|---|---|---|---:|---:|---:|---:|"]
    for asset_class in ("EQUITY", "ETF", "FOREX", "COMMODITY", "CRYPTO"):
        rows = by_class.get(asset_class, [])
        for field in SIGNAL_FIELDS:
            for label, bucket in _bucket_by_rank(rows, field):
                field_lines.append(
                    f"| {asset_class} | {field} | {label} | {len(bucket)} | {_pct(_wr(bucket))} | {_pf_str(_pf(bucket))} | {_sum_pnl(bucket):.3f} |"
                )
    _print_table("Field Separation (rank-tertiles)", field_lines)

    active_lines = ["| Asset Class | Active Raw | Top Strategies |", "|---|---:|---|"]
    active_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in active_raw:
        active_by_class[_asset_class(row)].append(row)
    for asset_class, rows in sorted(active_by_class.items(), key=lambda item: (-len(item[1]), item[0])):
        counts = Counter(str(row.get("strategy") or "?") for row in rows)
        top = ", ".join(f"{name} ({count})" for name, count in counts.most_common(5))
        active_lines.append(f"| {asset_class} | {len(rows)} | {top} |")
    _print_table("Active Raw Mix", active_lines)

    active_payload = _load_json(ACTIVE_PICKS)
    active_rows = _to_rows(active_payload)
    ltv_rows = [row for row in active_rows if str(row.get("pick_type") or "").lower() == "long_term_value"]
    pead_active = [
        row
        for row in active_rows
        if "pead" in str(row.get("strategy") or "").lower()
        or "earnings" in str(row.get("strategy") or "").lower()
    ]
    pead_closed = [
        row
        for row in recent_closed
        if "pead" in str(row.get("strategy") or "").lower()
        or "earnings" in str(row.get("strategy") or "").lower()
    ]
    ueps_payload = _load_json(UEPS_PICKS)
    ueps_summary = ueps_payload.get("summary", {}) if isinstance(ueps_payload, dict) else {}
    _print_table(
        "UEPS / PEAD Status",
        [
            f"- ueps_picks.generated_at: {ueps_payload.get('generated_at')}",
            f"- ueps summary: {ueps_summary}",
            f"- active_picks rows: {len(active_rows)}",
            f"- active long_term_value rows: {len(ltv_rows)}",
            f"- active PEAD-like rows: {len(pead_active)}",
            f"- recent_closed PEAD-like rows: {len(pead_closed)}",
            f"- PEAD-like closed strategies: {sorted({str(row.get('strategy')) for row in pead_closed})}",
        ],
    )

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
