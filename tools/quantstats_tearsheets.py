"""Per-asset-class QuantStats HTML tear-sheets.

OPT-IN SIDECAR — does not modify production pick-generation, scoring, or
active-gate paths. Run on demand to produce HTML reports under
``reports/tearsheets/<asset_class>_<timestamp>.html`` from the closed-pick
ledger in ``audit_dashboard/data/dashboard_data.json``.

Why
---
``reports/hedge_fund_performance_review_*.md`` is hand-rolled per cycle.
QuantStats auto-generates: cumulative returns, MaxDD, Calmar, rolling
Sharpe, distribution, monthly heatmap, drawdown periods, etc. — the
exact diagnostics we use to decide which asset class to size up. This
gives reviewers the same view the hedge-fund-performance-review doc
ships, without anyone hand-typing percentages.

The 2026-04-28 review explicitly flagged CRYPTO MDD 178% as a "lethal"
finding that should have been caught earlier. A standing tear-sheet
would have surfaced it the moment MDD crossed any reasonable threshold.

Wiring (per CLAUDE.md Wire-Up Rule)
-----------------------------------
This module is an **opt-in sidecar**. It is invoked manually
(``python tools/quantstats_tearsheets.py``) or by a future scheduled
workflow. No production pick-generation or scoring path imports it.
Production wiring is deferred — see PR description ``## Wiring Plan``.

Design choices
--------------
- Reads from ``audit_dashboard/data/dashboard_data.json`` (canonical
  pick ledger; ``picks.recent_closed`` has 3,500+ rows with ``pnl_pct``,
  ``asset_class``, ``closed_at``).
- One HTML file per asset class (EQUITY, CRYPTO, FOREX, COMMODITY,
  ETF, BOND), plus an aggregate "ALL" file.
- Treats each closed pick as a single-period return; aggregates by
  ``closed_at`` calendar day so the QuantStats date-indexed plots work.
- ``pnl_pct`` is decimal already in the existing ledger (e.g., 0.034 =
  3.4%). The module asserts this on first read and bails if it sees
  values >5 (which would imply integer-percent units — the cycle10
  unit-mismatch bug from feedback memory).
- No yfinance benchmark fetching by default (we run offline-friendly).
  Callers may pass ``benchmark="SPY"`` to opt in.

Usage
-----
    # Default: write all asset-class tear-sheets to reports/tearsheets/
    python tools/quantstats_tearsheets.py

    # Single class
    python tools/quantstats_tearsheets.py --asset-class EQUITY

    # Custom data file
    python tools/quantstats_tearsheets.py --data audit_trail/data/dashboard_payload.json

License notice
--------------
QuantStats is Apache-2.0 (compatible with this project's MIT-style use).
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)

# QuantStats has matplotlib at import time. We import lazily so unit tests
# that don't actually render can stub it out.
_QS = None


def _load_quantstats():  # pragma: no cover - just an import shim
    global _QS
    if _QS is None:
        try:
            import quantstats as qs  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "quantstats is not installed. Install with "
                "`pip install -r requirements-hedge-fund.txt` or "
                "`pip install quantstats`."
            ) from exc
        _QS = qs
    return _QS


# Asset classes we expect to see in the closed-pick ledger. Anything else
# is bucketed as "OTHER" so we don't drop rows silently.
KNOWN_ASSET_CLASSES = {"EQUITY", "CRYPTO", "FOREX", "COMMODITY", "ETF", "BOND"}


def _parse_iso(ts: Any) -> datetime | None:
    """Best-effort ISO8601 parse. Returns None on failure (we drop the row)."""
    if not ts:
        return None
    if isinstance(ts, datetime):
        return ts.astimezone(timezone.utc) if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _f(v: Any) -> float | None:
    """Tolerant float coerce."""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _bucket(pick: dict[str, Any]) -> str:
    ac = (pick.get("asset_class") or "").strip().upper()
    if ac in KNOWN_ASSET_CLASSES:
        return ac
    return "OTHER"


def load_closed_picks(data_path: str | Path) -> list[dict[str, Any]]:
    """Read closed picks from a dashboard JSON file.

    Tries the canonical containers in order:
      1. ``picks.recent_closed`` (audit_dashboard/data/dashboard_data.json)
      2. ``picks`` (audit_trail/data/dashboard_payload.json — list)
      3. top-level list (universal_resolved_picks.json)
    """
    p = Path(data_path)
    if not p.exists():
        raise FileNotFoundError(f"closed-picks data file not found: {p}")
    with p.open("r", encoding="utf-8") as fh:
        d = json.load(fh)
    if isinstance(d, list):
        return [r for r in d if isinstance(r, dict)]
    if isinstance(d, dict):
        picks = d.get("picks")
        if isinstance(picks, dict):
            recent = picks.get("recent_closed") or []
            return [r for r in recent if isinstance(r, dict)]
        if isinstance(picks, list):
            return [r for r in picks if isinstance(r, dict)]
        # Fall back to top-level
        for key in ("recent_closed", "all_picks", "closed"):
            v = d.get(key)
            if isinstance(v, list):
                return [r for r in v if isinstance(r, dict)]
    raise ValueError(f"could not locate a closed-picks list inside {p}")


def detect_pnl_unit(picks: Iterable[dict[str, Any]]) -> str:
    """Heuristically detect whether ``pnl_pct`` is decimal or integer-percent.

    The existing ledger is mixed: EQUITY / ETF / CRYPTO / BOND tend to
    store integer-percent (e.g. ``pnl_pct=3.45`` means +3.45%), whereas
    FOREX / COMMODITY / FUTURES / UNKNOWN tend to store decimal
    (``pnl_pct=0.0034`` means +0.34%). This is the classic cycle10
    unit-mismatch (feedback_cycle10_unit_mismatch_bug).

    Heuristic: median absolute pnl. If median > 0.5, the source is
    almost certainly integer-percent (anything else would be an
    implausible 50% per trade). If median < 0.5, it's decimal.

    Returns ``"percent"`` (integer-percent) or ``"decimal"``. On empty
    or all-None input returns ``"decimal"`` (the doc-spec default).
    """
    abs_vals: list[float] = []
    for p in picks:
        v = _f(p.get("pnl_pct"))
        if v is None:
            continue
        abs_vals.append(abs(v))
    if not abs_vals:
        return "decimal"
    abs_vals.sort()
    median = abs_vals[len(abs_vals) // 2]
    return "percent" if median > 0.5 else "decimal"


def picks_to_daily_returns(
    picks: Iterable[dict[str, Any]],
    *,
    asset_class: str | None = None,
    pnl_unit: str | None = None,
    pnl_unit_check: bool = True,
):
    """Aggregate per-pick pnl_pct into a daily-return pandas Series.

    Parameters
    ----------
    picks : iterable of dict
    asset_class : str or None
        If set, only picks with matching ``_bucket(pick)`` are kept.
    pnl_unit : {"decimal", "percent", None}
        - ``"decimal"`` — input is already decimal (0.034 == 3.4%).
        - ``"percent"`` — input is integer-percent (3.4 == 3.4%); we
          divide by 100 before aggregating.
        - ``None`` — auto-detect via :func:`detect_pnl_unit` (filtered
          to the requested ``asset_class`` first). This is the default
          and is what handles the cross-class mixed-units bug in the
          existing ledger.
    pnl_unit_check : bool
        Only relevant when ``pnl_unit="decimal"`` is forced. If True and
        >1% of picks have ``|pnl_pct|>5``, raise — guards against a
        caller mis-declaring units.

    Returns
    -------
    pandas.Series
        Daily aggregated DECIMAL returns indexed by UTC date. Each day's
        return is the *sum* of per-pick returns closing that day (paper
        equal-weight $1-per-pick). Empty days are dropped.
    """
    import pandas as pd  # imported here to keep the module import-light for unit tests

    # Filter once so detect_pnl_unit only sees the right asset class
    if asset_class is not None:
        picks = [p for p in picks if _bucket(p) == asset_class.upper()]

    if pnl_unit is None:
        pnl_unit = detect_pnl_unit(picks)
    pnl_unit = pnl_unit.lower()
    if pnl_unit not in ("decimal", "percent"):
        raise ValueError(f"pnl_unit must be 'decimal' or 'percent', got {pnl_unit!r}")
    scale = 0.01 if pnl_unit == "percent" else 1.0

    by_day: dict[Any, float] = defaultdict(float)
    n_kept = 0
    n_outlier = 0
    for p in picks:
        ts = _parse_iso(p.get("closed_at") or p.get("resolved_at") or p.get("timestamp"))
        if ts is None:
            continue
        ret = _f(p.get("pnl_pct"))
        if ret is None:
            continue
        scaled = ret * scale
        if abs(scaled) > 5:
            n_outlier += 1
        by_day[ts.date()] += scaled
        n_kept += 1

    if (
        pnl_unit_check
        and pnl_unit == "decimal"
        and n_kept > 0
        and (n_outlier / n_kept) > 0.01
    ):
        raise ValueError(
            f"pnl_pct unit mismatch suspected: {n_outlier}/{n_kept} picks "
            f"have |scaled_pnl|>5 with pnl_unit='decimal'. "
            f"If your source uses integer-percent units, pass "
            f"pnl_unit='percent' (or None for auto-detect). "
            f"See feedback_cycle10_unit_mismatch_bug."
        )

    if not by_day:
        return pd.Series(dtype=float, name="returns")
    items = sorted(by_day.items())
    idx = pd.to_datetime([k for k, _ in items])
    vals = [v for _, v in items]
    return pd.Series(vals, index=idx, name="returns")


def write_tearsheet(
    returns,
    output_path: str | Path,
    *,
    title: str,
    benchmark=None,
) -> Path:
    """Render an HTML tear-sheet to ``output_path``.

    ``returns`` is a pandas Series of decimal daily returns.
    ``benchmark`` may be a pandas Series, a ticker string (yfinance
    fetched), or None (offline; no benchmark column).
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if returns.empty:
        # Degenerate: write a minimal placeholder rather than letting QuantStats raise.
        out.write_text(
            f"<html><body><h1>{title}</h1>"
            f"<p>No returns data available for this asset class.</p>"
            f"</body></html>",
            encoding="utf-8",
        )
        return out
    qs = _load_quantstats()
    qs.reports.html(returns, benchmark=benchmark, title=title, output=str(out))
    return out


def write_all_tearsheets(
    data_path: str | Path,
    output_dir: str | Path,
    *,
    only: list[str] | None = None,
    benchmark=None,
) -> dict[str, Path]:
    """Write per-asset-class tear-sheets + an aggregate ALL.

    Returns a dict ``{class_label: html_path}``.
    """
    picks = load_closed_picks(data_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    written: dict[str, Path] = {}

    classes = sorted({_bucket(p) for p in picks})
    if only:
        wanted = {c.upper() for c in only}
        classes = [c for c in classes if c in wanted]

    for cls in classes:
        ret = picks_to_daily_returns(picks, asset_class=cls)
        out_path = out_dir / f"{cls.lower()}_{ts_tag}.html"
        try:
            write_tearsheet(ret, out_path, title=f"{cls} — {ts_tag}", benchmark=benchmark)
        except Exception as exc:  # pragma: no cover - render-time failure
            logger.warning("tearsheet render failed for %s: %s", cls, exc)
            continue
        written[cls] = out_path

    if not only or "ALL" in {c.upper() for c in only}:
        agg = picks_to_daily_returns(picks)
        out_path = out_dir / f"all_{ts_tag}.html"
        try:
            write_tearsheet(agg, out_path, title=f"ALL ASSET CLASSES — {ts_tag}", benchmark=benchmark)
            written["ALL"] = out_path
        except Exception as exc:  # pragma: no cover
            logger.warning("aggregate tearsheet render failed: %s", exc)

    return written


def _cli() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "--data",
        default="audit_dashboard/data/dashboard_data.json",
        help="path to a dashboard JSON containing picks.recent_closed",
    )
    ap.add_argument(
        "--out",
        default="reports/tearsheets",
        help="output directory for HTML tear-sheets",
    )
    ap.add_argument(
        "--asset-class",
        action="append",
        help="restrict to one or more asset classes (repeatable; e.g. EQUITY CRYPTO)",
    )
    ap.add_argument(
        "--benchmark",
        default=None,
        help="yfinance benchmark ticker (e.g. SPY). Default: no benchmark (offline).",
    )
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    written = write_all_tearsheets(
        args.data, args.out, only=args.asset_class, benchmark=args.benchmark
    )
    if not written:
        print("No tear-sheets written.", file=sys.stderr)
        return 1
    for cls, path in sorted(written.items()):
        print(f"{cls}\t{path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_cli())
