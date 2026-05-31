"""Phase 6 — Meta-effectiveness analyzer for AI-model hedge-fund portfolios.

Answers: *whose decision rules actually compound capital?* using risk-adjusted
return (Sharpe, Sortino, CAGR/MaxDD) — NOT raw WR.

Pure analysis: read-only, NO DB writes, NO live API calls. Defaults to
``--dry-run`` which reads from the dashboard JSON exports
(``audit_dashboard/data/pf_portfolios.json`` + ``pf_portfolio_*.json``); pass
``--apply`` to read from live MySQL instead (env vars per ``init_db.py``).

Outputs:
  reports/portfolio_meta_<asof>.md   — human report
  audit_dashboard/data/pf_meta.json  — machine schema (see DESIGN §9)

Design ref: docs/DESIGN_AI_MODEL_HEDGE_FUND_PORTFOLIOS_2026-05-29.md §9.

CLI:
    python3 tools/portfolios/meta_effectiveness.py            # dry-run, today UTC
    python3 tools/portfolios/meta_effectiveness.py --asof 2026-05-30
    python3 tools/portfolios/meta_effectiveness.py --apply    # live DB
    python3 tools/portfolios/meta_effectiveness.py --out path.md --json path.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "audit_dashboard" / "data"
REPORTS_DIR = REPO_ROOT / "reports"

TRADING_DAYS = 252  # standard annualization factor


# ---------------------------------------------------------------------------
# Math helpers (pure, deterministic, well-tested).
# ---------------------------------------------------------------------------
def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _stdev(xs: list[float]) -> float:
    """Population stdev (n divisor). Returns 0.0 if <2 points."""
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    var = sum((x - m) ** 2 for x in xs) / len(xs)
    return math.sqrt(var)


def daily_returns_from_nav(navs: list[float]) -> list[float]:
    """r_t = (nav_t - nav_{t-1}) / nav_{t-1}. Skips non-positive priors."""
    out: list[float] = []
    for i in range(1, len(navs)):
        prev = navs[i - 1]
        if prev and prev > 0:
            out.append((navs[i] - prev) / prev)
    return out


def sharpe(returns: list[float], periods_per_year: int = TRADING_DAYS) -> float:
    """Annualized Sharpe (rf=0). Returns 0.0 if <2 points or zero vol.

    Note: we allow Sharpe to compute on as few as 2 daily returns — the report
    flags low-n portfolios but doesn't require n=252. With <2 points we have
    no variance estimate and return 0.0 by convention.
    """
    if len(returns) < 2:
        return 0.0
    sd = _stdev(returns)
    if sd == 0.0:
        return 0.0
    return (_mean(returns) / sd) * math.sqrt(periods_per_year)


def sortino(returns: list[float], periods_per_year: int = TRADING_DAYS) -> float:
    """Annualized Sortino (downside-only stdev, MAR=0)."""
    if len(returns) < 2:
        return 0.0
    downs = [r for r in returns if r < 0]
    if not downs:
        # No losing days — return Sharpe-like proxy using full stdev as floor.
        sd = _stdev(returns)
        if sd == 0.0:
            return 0.0
        return (_mean(returns) / sd) * math.sqrt(periods_per_year)
    # Downside deviation uses sqrt(mean(r^2)) of below-MAR returns.
    dd = math.sqrt(sum(r * r for r in downs) / len(downs))
    if dd == 0.0:
        return 0.0
    return (_mean(returns) / dd) * math.sqrt(periods_per_year)


def max_drawdown(navs: list[float]) -> float:
    """Return max drawdown as a NEGATIVE percentage (e.g. -0.18 = -18%).

    Returns 0.0 for empty / single-point series.
    """
    if len(navs) < 2:
        return 0.0
    peak = navs[0]
    worst = 0.0
    for v in navs:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (v - peak) / peak
            if dd < worst:
                worst = dd
    return worst


def cagr(navs: list[float], n_days: int) -> float:
    """Compound Annual Growth Rate.

    n_days = days from first to last NAV. Uses 365.25 calendar-day basis.
    Returns 0.0 if start NAV <=0 or n_days<=0.
    """
    if len(navs) < 2 or n_days <= 0:
        return 0.0
    start, end = navs[0], navs[-1]
    if start <= 0:
        return 0.0
    ratio = end / start
    if ratio <= 0:
        return -1.0  # wiped out
    years = n_days / 365.25
    if years <= 0:
        return 0.0
    return ratio ** (1.0 / years) - 1.0


def calmar(cagr_v: float, mdd: float) -> float:
    if mdd == 0.0:
        return 0.0
    return cagr_v / abs(mdd)


# ---------------------------------------------------------------------------
# Data loading (dry-run reads JSON; --apply reads DB).
# ---------------------------------------------------------------------------
def load_from_json(data_dir: Path = DATA_DIR) -> tuple[list[dict], dict[str, dict]]:
    """Return (roster, details_by_key). Raises FileNotFoundError if no roster."""
    roster_path = data_dir / "pf_portfolios.json"
    if not roster_path.exists():
        raise FileNotFoundError(str(roster_path))
    roster_payload = json.loads(roster_path.read_text())
    roster = roster_payload.get("portfolios", [])
    details: dict[str, dict] = {}
    for entry in roster:
        key = entry.get("portfolio_key")
        if not key:
            continue
        # File naming convention from export_json._safe_key.
        import re

        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", key)
        fp = data_dir / f"pf_portfolio_{safe}.json"
        if fp.exists():
            details[key] = json.loads(fp.read_text())
    return roster, details


def load_from_db() -> tuple[list[dict], dict[str, dict]]:
    """Read PF_* tables. Reuses export_json.build_payloads + connect pattern."""
    from tools.portfolios import export_json  # type: ignore

    conn = export_json._connect()
    try:
        roster_payload, details = export_json.build_payloads(conn)
    finally:
        conn.close()
    return roster_payload.get("portfolios", []), details


# ---------------------------------------------------------------------------
# Core analysis.
# ---------------------------------------------------------------------------
def _nav_series(detail: dict) -> tuple[list[float], list[str]]:
    """Return (nav_values, asof_dates) sorted ascending by asof_date."""
    curve = detail.get("nav_curve") or []
    rows = []
    for r in curve:
        try:
            v = float(r["nav_usd"])
        except (TypeError, KeyError, ValueError):
            continue
        d = str(r.get("asof_date") or "")
        rows.append((d, v))
    rows.sort(key=lambda x: x[0])
    return [v for _, v in rows], [d for d, _ in rows]


def _portfolio_metrics(detail: dict, starting_nav: float) -> dict:
    navs, dates = _nav_series(detail)
    rets = daily_returns_from_nav(navs)
    n_days = 0
    if len(dates) >= 2:
        try:
            d0 = date.fromisoformat(dates[0][:10])
            d1 = date.fromisoformat(dates[-1][:10])
            n_days = max(0, (d1 - d0).days)
        except Exception:  # noqa: BLE001
            n_days = max(0, len(navs) - 1)
    sh = sharpe(rets)
    so = sortino(rets)
    mdd = max_drawdown(navs)
    cg = cagr(navs, n_days) if n_days > 0 else 0.0
    cal = calmar(cg, mdd)
    total_ret = 0.0
    if navs and starting_nav > 0:
        total_ret = (navs[-1] - starting_nav) / starting_nav
    # Turnover (per-month) — sum of |notional_change| / avg_nav, scaled.
    positions = detail.get("positions") or []
    closed = [p for p in positions if (p.get("status") == "closed")]
    avg_nav = _mean(navs) if navs else starting_nav
    if avg_nav <= 0:
        avg_nav = starting_nav or 1.0
    rotated = 0.0
    for p in closed:
        try:
            qty = float(p.get("qty") or 0)
            entry = float(p.get("entry_price") or 0)
            rotated += abs(qty * entry)
        except (TypeError, ValueError):
            pass
    months = max(1.0, n_days / 30.0) if n_days else 1.0
    turnover = (rotated / avg_nav) / months if avg_nav else 0.0
    return {
        "n_nav_points": len(navs),
        "n_daily_returns": len(rets),
        "n_days": n_days,
        "total_return_pct": total_ret,
        "cagr": cg,
        "sharpe": sh,
        "sortino": so,
        "max_dd": mdd,
        "calmar": cal,
        "turnover": turnover,
    }


def _per_class_skill(roster: list[dict], details: dict[str, dict]) -> list[dict]:
    """For each (model_id, asset_class) aggregate closed-position Sharpe-like
    score (mean pnl% / stdev pnl%). Pick best model per class.

    Returns rows: {asset_class, best_model_id, best_sharpe, n_models, n_trades}.
    """
    # buckets[asset_class][model_id] -> list of realized_pnl_pct
    buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for entry in roster:
        key = entry.get("portfolio_key")
        model_id = entry.get("model_id") or "<unknown>"
        det = details.get(key)
        if not det:
            continue
        for p in det.get("positions") or []:
            if p.get("status") != "closed":
                continue
            ac = p.get("asset_class") or "UNKNOWN"
            try:
                pnl = float(p.get("realized_pnl_pct") or 0.0)
            except (TypeError, ValueError):
                continue
            buckets[ac][model_id].append(pnl)

    out: list[dict] = []
    for ac, models in buckets.items():
        n_trades_total = 0
        best_model = None
        best_score = float("-inf")
        for model_id, pnls in models.items():
            n_trades_total += len(pnls)
            if len(pnls) < 2:
                score = _mean(pnls) if pnls else 0.0
            else:
                sd = _stdev(pnls)
                score = (_mean(pnls) / sd) if sd else 0.0
            if score > best_score:
                best_score = score
                best_model = model_id
        out.append({
            "asset_class": ac,
            "best_model_id": best_model,
            "best_sharpe": best_score if best_score != float("-inf") else 0.0,
            "n_models": len(models),
            "n_trades": n_trades_total,
        })
    out.sort(key=lambda r: -r["best_sharpe"])
    return out


def _attribution(detail: dict, port_metric: dict) -> dict:
    """Decompose return into selection / sizing / timing contributions.

    selection_contrib = mean(realized_pnl_pct of accepted picks)
                       - mean(realized_pnl_pct of ALL closed picks for this
                              model — proxy for "available picks")
       (In dry-run we don't have an external pick universe; fall back to 0.0
        and document that selection_contrib==0 means "single-source" / no
        counterfactual universe available.)

    sizing_contrib = portfolio_total_return - equal_weight_return
       where equal_weight_return = mean(pnl_pct) across closed positions.

    timing_contrib = mean( entry_vs_prior_5d_avg ) — simple heuristic.
       For each closed position: (entry_price - prior_5d_avg) / prior_5d_avg
       (positive = entered above recent avg = worse for longs; we sign-flip
        for shorts). We only have entry_price, not historical bars, so we use
        the NAV-mark-on-entry-date vs prior 5-NAV average as a proxy.
    """
    positions = detail.get("positions") or []
    closed = [p for p in positions if p.get("status") == "closed"]
    if not closed:
        return {"selection_contrib": 0.0, "sizing_contrib": 0.0, "timing_contrib": 0.0}

    pnls: list[float] = []
    for p in closed:
        try:
            pnls.append(float(p.get("realized_pnl_pct") or 0.0))
        except (TypeError, ValueError):
            pass
    equal_weight_return = _mean(pnls) if pnls else 0.0
    sizing_contrib = port_metric.get("total_return_pct", 0.0) - equal_weight_return

    # Selection: no external universe in dry-run → 0.0 (documented).
    selection_contrib = 0.0

    # Timing: NAV-mark on entry vs prior_5d avg NAV.
    navs, dates = _nav_series(detail)
    date_to_idx = {d[:10]: i for i, d in enumerate(dates)}
    timing_vals: list[float] = []
    for p in closed:
        ed = str(p.get("entry_date") or "")[:10]
        idx = date_to_idx.get(ed)
        if idx is None or idx < 1:
            continue
        prior = navs[max(0, idx - 5):idx]
        if not prior:
            continue
        avg5 = _mean(prior)
        if avg5 <= 0:
            continue
        sign = -1.0 if (p.get("direction") == "short") else 1.0
        # entering when NAV-mark is BELOW prior avg = favorable timing for longs.
        timing_vals.append(-sign * (navs[idx] - avg5) / avg5)
    timing_contrib = _mean(timing_vals) if timing_vals else 0.0

    return {
        "selection_contrib": selection_contrib,
        "sizing_contrib": sizing_contrib,
        "timing_contrib": timing_contrib,
    }


def _best_of_class_blend(
    roster: list[dict],
    details: dict[str, dict],
    per_class: list[dict],
    rank_rows: list[dict],
) -> dict:
    """Synthetic NAV curve = equal-weight across asset classes of each class's
    best-model portfolio. Compare Sharpe vs every single-model book.
    """
    # Map model_id -> portfolio_key (first matching).
    model_to_key: dict[str, str] = {}
    for e in roster:
        mid = e.get("model_id")
        if mid and mid not in model_to_key:
            model_to_key[mid] = e.get("portfolio_key")

    selected_keys: list[str] = []
    for row in per_class:
        mid = row.get("best_model_id")
        k = model_to_key.get(mid)
        if k and k not in selected_keys:
            selected_keys.append(k)

    if not selected_keys:
        return {"sharpe": 0.0, "cagr": 0.0, "max_dd": 0.0, "beat_all_single_models": False}

    # Align NAV curves by date — for each date, average normalized NAV
    # (NAV / starting_nav) across the selected books that have data on that day.
    aligned: dict[str, list[float]] = defaultdict(list)
    for k in selected_keys:
        det = details.get(k)
        if not det:
            continue
        starting = float((det.get("portfolio") or {}).get("starting_nav") or 100000.0)
        if starting <= 0:
            continue
        navs, dates = _nav_series(det)
        for d, v in zip(dates, navs):
            aligned[d[:10]].append(v / starting)

    if not aligned:
        return {"sharpe": 0.0, "cagr": 0.0, "max_dd": 0.0, "beat_all_single_models": False}

    sorted_dates = sorted(aligned.keys())
    blend_curve = [_mean(aligned[d]) for d in sorted_dates]
    rets = daily_returns_from_nav(blend_curve)
    sh = sharpe(rets)
    n_days = 0
    try:
        n_days = (date.fromisoformat(sorted_dates[-1]) - date.fromisoformat(sorted_dates[0])).days
    except Exception:  # noqa: BLE001
        pass
    cg = cagr(blend_curve, n_days) if n_days > 0 else 0.0
    mdd = max_drawdown(blend_curve)

    beat_all = True
    for row in rank_rows:
        if row.get("sharpe", 0.0) >= sh:
            beat_all = False
            break
    if not rank_rows:
        beat_all = False
    return {
        "sharpe": sh,
        "cagr": cg,
        "max_dd": mdd,
        "beat_all_single_models": beat_all,
    }


def analyze(roster: list[dict], details: dict[str, dict], asof_date: str) -> dict:
    """Pure function: roster + details -> pf_meta.json payload."""
    rank_rows: list[dict] = []
    for entry in roster:
        key = entry.get("portfolio_key")
        det = details.get(key)
        if not det:
            continue
        try:
            starting = float((det.get("portfolio") or {}).get("starting_nav")
                             or entry.get("starting_nav") or 100000.0)
        except (TypeError, ValueError):
            starting = 100000.0
        m = _portfolio_metrics(det, starting)
        attr = _attribution(det, m)
        rank_rows.append({
            "portfolio_key": key,
            "model_id": entry.get("model_id"),
            "appetite": entry.get("risk_appetite"),
            "sharpe": m["sharpe"],
            "cagr": m["cagr"],
            "max_dd": m["max_dd"],
            "calmar": m["calmar"],
            "total_return_pct": m["total_return_pct"],
            "sortino": m["sortino"],
            "turnover": m["turnover"],
            "n_nav_points": m["n_nav_points"],
            "selection_contrib": attr["selection_contrib"],
            "sizing_contrib": attr["sizing_contrib"],
            "timing_contrib": attr["timing_contrib"],
        })
    rank_rows.sort(key=lambda r: -r["sharpe"])
    per_class = _per_class_skill(roster, details)
    blend = _best_of_class_blend(roster, details, per_class, rank_rows)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "asof_date": asof_date,
        "rank_by_sharpe": rank_rows,
        "per_class_skill": per_class,
        "best_of_class_blend": blend,
    }


# ---------------------------------------------------------------------------
# Markdown rendering.
# ---------------------------------------------------------------------------
def render_markdown(payload: dict) -> str:
    rank = payload.get("rank_by_sharpe") or []
    per_class = payload.get("per_class_skill") or []
    blend = payload.get("best_of_class_blend") or {}
    asof = payload.get("asof_date", "")
    lines: list[str] = []
    lines.append(f"# Portfolio Meta-Effectiveness — asof {asof}")
    lines.append("")
    lines.append(f"_Generated: {payload.get('generated_at','')}_")
    lines.append("")
    lines.append("Ranks each AI-model paper portfolio by **risk-adjusted return**"
                 " (Sharpe), with selection/sizing/timing attribution and a"
                 " best-of-class blend baseline. Source: DESIGN §9.")
    lines.append("")

    lines.append("## Top 10 portfolios by Sharpe")
    lines.append("")
    if not rank:
        lines.append("_No portfolios with NAV history yet._")
    else:
        lines.append("| # | portfolio_key | model | appetite | Sharpe | CAGR | MaxDD | Calmar | selection | sizing | timing |")
        lines.append("|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|")
        for i, r in enumerate(rank[:10], 1):
            lines.append(
                f"| {i} | `{r['portfolio_key']}` | {r.get('model_id') or ''} | "
                f"{r.get('appetite') or ''} | {r['sharpe']:.2f} | "
                f"{r['cagr']*100:.2f}% | {r['max_dd']*100:.2f}% | "
                f"{r['calmar']:.2f} | {r['selection_contrib']*100:.2f}% | "
                f"{r['sizing_contrib']*100:.2f}% | {r['timing_contrib']*100:.2f}% |"
            )
    lines.append("")

    lines.append("## Per-class skill matrix (best model by Sharpe-like score on closed trades)")
    lines.append("")
    if not per_class:
        lines.append("_No closed positions yet._")
    else:
        lines.append("| asset_class | best_model | score | n_models | n_trades |")
        lines.append("|---|---|---:|---:|---:|")
        for row in per_class:
            lines.append(
                f"| {row['asset_class']} | {row.get('best_model_id') or ''} | "
                f"{row['best_sharpe']:.3f} | {row['n_models']} | {row['n_trades']} |"
            )
    lines.append("")

    lines.append("## Best-of-class blend (fund of funds)")
    lines.append("")
    if blend:
        lines.append(f"- Sharpe: **{blend.get('sharpe',0.0):.2f}**")
        lines.append(f"- CAGR: **{blend.get('cagr',0.0)*100:.2f}%**")
        lines.append(f"- MaxDD: **{blend.get('max_dd',0.0)*100:.2f}%**")
        verdict = "YES — beats every single-model book" if blend.get("beat_all_single_models") \
            else "no — at least one single-model book matches/exceeds blend Sharpe"
        lines.append(f"- Beat all single-model books: **{verdict}**")
    lines.append("")

    lines.append("## Strongest finding")
    lines.append("")
    if rank:
        top = rank[0]
        lines.append(
            f"Top portfolio is `{top['portfolio_key']}` (model "
            f"`{top.get('model_id')}`, appetite `{top.get('appetite')}`) with "
            f"Sharpe **{top['sharpe']:.2f}**, CAGR **{top['cagr']*100:.2f}%**, "
            f"MaxDD **{top['max_dd']*100:.2f}%**. Sizing contribution "
            f"**{top['sizing_contrib']*100:.2f}%** vs equal-weight; timing "
            f"**{top['timing_contrib']*100:.2f}%**."
        )
    else:
        lines.append("_Not enough data to declare a leader._")
    lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    ap.add_argument("--asof", default=None,
                    help="YYYY-MM-DD anchor (default: today UTC)")
    ap.add_argument("--apply", action="store_true",
                    help="read live MySQL PF_* tables (default: read dashboard JSON)")
    ap.add_argument("--dry-run", action="store_true",
                    help="explicit dry-run (default mode, ignored if --apply set)")
    ap.add_argument("--out", default=None,
                    help="markdown report path (default: reports/portfolio_meta_<asof>.md)")
    ap.add_argument("--json", dest="json_out", default=None,
                    help="JSON output path (default: audit_dashboard/data/pf_meta.json)")
    args = ap.parse_args(argv)

    asof = args.asof or datetime.now(timezone.utc).date().isoformat()
    out_md = Path(args.out) if args.out else REPORTS_DIR / f"portfolio_meta_{asof}.md"
    out_json = Path(args.json_out) if args.json_out else DATA_DIR / "pf_meta.json"

    use_db = args.apply and not args.dry_run

    try:
        if use_db:
            roster, details = load_from_db()
        else:
            roster, details = load_from_json()
    except FileNotFoundError as exc:
        print(f"[meta_effectiveness] no data yet — {exc} not found. "
              "Cron run has not produced JSON yet; exiting cleanly.")
        # Write empty payload so downstream consumers can detect "no data".
        empty = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "asof_date": asof,
            "rank_by_sharpe": [],
            "per_class_skill": [],
            "best_of_class_blend": {
                "sharpe": 0.0, "cagr": 0.0, "max_dd": 0.0,
                "beat_all_single_models": False,
            },
        }
        try:
            out_json.parent.mkdir(parents=True, exist_ok=True)
            out_json.write_text(json.dumps(empty, indent=2))
            print(f"[meta_effectiveness] wrote empty {out_json}")
        except Exception as e:  # noqa: BLE001
            print(f"[meta_effectiveness] (could not write empty JSON: {e})")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"::error title=meta_effectiveness::load failed: {exc}", file=sys.stderr)
        return 1

    payload = analyze(roster, details, asof)
    md = render_markdown(payload)

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(md)
    out_json.write_text(json.dumps(payload, indent=2))

    print(f"[meta_effectiveness] mode={'DB' if use_db else 'JSON'} asof={asof}")
    print(f"[meta_effectiveness] {len(payload['rank_by_sharpe'])} portfolio(s) ranked; "
          f"{len(payload['per_class_skill'])} asset class(es); "
          f"blend Sharpe {payload['best_of_class_blend'].get('sharpe',0.0):.2f}")
    print(f"[meta_effectiveness] wrote {out_md}")
    print(f"[meta_effectiveness] wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
