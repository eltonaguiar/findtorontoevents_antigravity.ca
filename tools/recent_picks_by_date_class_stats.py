#!/usr/bin/env python3
"""Recent picks — stats by OPEN DATE x ASSET CLASS.

WHY: the /audit payload exposes per-asset-class aggregates
(`performance.by_asset_class`, `performance.asset_class_health`) but there is
NO table that breaks recent picks down by the date they were opened. This tool
builds exactly that, straight from the live payload, so it can never disagree
with what /audit serves.

WHAT IS COMPUTED (per open-date x asset-class cohort, and per asset class):
  - n picks, closed vs still-open
  - wins / losses / flat and win-rate
  - current P/L  = sum of `pnl_pct` (realized for closed rows, unrealized for
                   open rows) in percentage points, equal-weight, 1 unit/pick
  - profit factor = gross win / gross loss (percentage-point terms)
  - max drawdown  = max peak-to-trough of the cumulative P/L series
                    (percentage points, equal-weight, chronological order)
  - avg P/L per pick

DATA SOURCE (default = live): https://findtorontoevents.ca/audit/data/dashboard_data.json
Overridable with --json <local path>.

BOOKS:
  - picks.recent_closed    -> realized rows (status WON/LOST/CLOSED/...)
  - picks.active_raw       -> only status == OPEN rows (unrealized "current" P/L)

OPEN-DATE RESOLUTION (honest, no guessing):
  - `entry_time` when present (a genuine entry timestamp)
  - else `timestamp` when it differs from `closed_at` (i.e. it is an entry stamp)
  - else UNKNOWN -> the row is excluded from the by-date table but still counted
    in the per-asset-class summary. Coverage is reported explicitly.

Read-only: performs no writes except the files you ask it to emit.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

LIVE_URL = "https://findtorontoevents.ca/audit/data/dashboard_data.json"

CLASS_ORDER = [
    "CRYPTO", "EQUITY", "FOREX", "COMMODITY", "ETF", "FUTURES", "BOND",
    "MEME", "PENNY_STOCK", "SPORTS",
]


def _f(v):
    """Best-effort float; None on failure."""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load(url=None, path=None):
    if path:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    req = urllib.request.Request(
        url or LIVE_URL, headers={"User-Agent": "recent-picks-stats/1.0"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


def _entry_date(row):
    """Return YYYY-MM-DD of the pick's OPEN date, or None when unknown."""
    et = (row.get("entry_time") or "").strip()
    if et:
        return et[:10]
    ts = (row.get("timestamp") or "").strip()
    ca = (row.get("closed_at") or "").strip()
    if ts and (not ca or ts[:10] != ca[:10]):
        return ts[:10]
    # active rows: timestamp/signal_time are entry stamps
    st = (row.get("signal_time") or "").strip()
    if st:
        return st[:10]
    return None


def _sort_key(row):
    """Chronological key for the cumulative-P/L series."""
    for k in ("entry_time", "timestamp", "signal_time", "closed_at"):
        v = (row.get(k) or "").strip()
        if v:
            return v
    return ""


def _realization_key(row):
    """Ordering key for the cumulative P/L curve.

    A pick's P/L is *realized* when it closes, not when it opened, so closed
    rows are ordered by `closed_at`. Still-open rows have no exit yet, so they
    are appended after every realized row (ordered by entry). This is what
    makes the drawdown a genuine realized-then-unrealized equity curve rather
    than an entry-date-ordered approximation.
    """
    if row.get("_open"):
        return (1, _sort_key(row))
    ca = (row.get("closed_at") or "").strip()
    return (0, ca or _sort_key(row))


def max_drawdown(rows):
    """Max peak-to-trough of the cumulative sum of pnl_pct, in pp (>=0).

    Ordered by realization time (closed_at), then still-open rows last — see
    `_realization_key`. The value is order-sensitive by construction; this
    ordering is the economically meaningful one (a realized P/L curve).
    """
    ordered = sorted(rows, key=_realization_key)
    cum = 0.0
    peak = 0.0
    mdd = 0.0
    for r in ordered:
        pnl = _f(r.get("pnl_pct"))
        if pnl is None:
            continue
        cum += pnl
        peak = max(peak, cum)
        mdd = max(mdd, peak - cum)
    return mdd


def _metrics(rows):
    """Aggregate one cohort of rows."""
    pnls = [p for p in (_f(r.get("pnl_pct")) for r in rows) if p is not None]
    n = len(rows)
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p < 0)
    flat = len(pnls) - wins - losses
    gross_win = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    decided = wins + losses
    pf = (gross_win / gross_loss) if gross_loss > 0 else None
    return {
        "n": n,
        "n_priced": len(pnls),
        "closed": sum(1 for r in rows if not r.get("_open")),
        "open": sum(1 for r in rows if r.get("_open")),
        "wins": wins,
        "losses": losses,
        "flat": flat,
        "decided": decided,
        "wr": (100.0 * wins / decided) if decided else None,
        "pl_pct": sum(pnls),
        "avg_pl_pct": (sum(pnls) / len(pnls)) if pnls else None,
        "pf": pf,
        "gross_win": gross_win,
        "gross_loss": gross_loss,
        "max_dd_pct": max_drawdown(rows),
    }


def build(payload, days=14):
    picks = payload.get("picks", {}) or {}
    closed = list(picks.get("recent_closed", []) or [])
    active_open = [r for r in (picks.get("active_raw", []) or [])
                   if r.get("status") == "OPEN"]
    for r in closed:
        r["_open"] = False
    for r in active_open:
        r["_open"] = True
    allrows = closed + active_open

    # ---- by open date x asset class (only rows with a known open date) ----
    dated = [r for r in allrows if _entry_date(r)]
    all_dates = sorted({_entry_date(r) for r in dated})
    window = set(all_dates[-days:]) if all_dates else set()

    cohorts = defaultdict(list)
    for r in dated:
        d = _entry_date(r)
        if d in window:
            cohorts[(d, r.get("asset_class") or "UNKNOWN")].append(r)

    by_date = []
    for (d, cls), rows in sorted(cohorts.items()):
        m = _metrics(rows)
        m["date"] = d
        m["asset_class"] = cls
        by_date.append(m)

    # ---- per asset class (whole book window, no date requirement) ----
    by_class = []
    groups = defaultdict(list)
    for r in allrows:
        groups[r.get("asset_class") or "UNKNOWN"].append(r)
    for cls, rows in groups.items():
        m = _metrics(rows)
        m["asset_class"] = cls
        # realized vs unrealized split
        realized = [r for r in rows if not r.get("_open")]
        unrealized = [r for r in rows if r.get("_open")]
        m["realized_pl_pct"] = sum(
            p for p in (_f(r.get("pnl_pct")) for r in realized) if p is not None)
        m["unrealized_pl_pct"] = sum(
            p for p in (_f(r.get("pnl_pct")) for r in unrealized) if p is not None)
        by_class.append(m)

    def _cls_key(m):
        c = m["asset_class"]
        return (CLASS_ORDER.index(c) if c in CLASS_ORDER else 99, c)

    by_class.sort(key=_cls_key)
    by_date.sort(key=lambda m: (m["date"], _cls_key(m)), reverse=False)

    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "payload_generated_at": payload.get("generated_at"),
        "payload_repo_sha": (payload.get("metadata") or {}).get("repo_sha"),
        "books": {
            "recent_closed": len(closed),
            "active_open": len(active_open),
        },
        "open_date_coverage": {
            "closed_with_open_date": sum(1 for r in closed if _entry_date(r)),
            "closed_total": len(closed),
            "active_with_open_date": sum(1 for r in active_open if _entry_date(r)),
            "active_total": len(active_open),
        },
        "window_days": days,
        "window": [min(window), max(window)] if window else None,
        "date_method": (
            "open date = entry_time when present; else timestamp when it "
            "differs from closed_at; else unknown (excluded from by-date table)"
        ),
        "wr_basis": "WR = wins / (wins + losses); flat (pnl_pct == 0) rows are not in the denominator",
        "dd_basis": (
            "cumulative P/L curve ordered by realization time (closed_at for "
            "closed rows; still-open rows appended last)"
        ),
    }
    return {"meta": meta, "by_date": by_date, "by_class": by_class}


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def _thin(m):
    """A cohort whose WR/expectancy rests on too few decided picks to trust."""
    return m["decided"] < 30


def _pf(m):
    return "n/a" if m["pf"] is None else f"{m['pf']:.2f}"


def _pct(v, dp=2):
    return "n/a" if v is None else f"{v:+.{dp}f}"


def render_md(res):
    m = res["meta"]
    L = []
    L.append("# Recent picks — stats by open date × asset class")
    L.append("")
    L.append(f"- Payload generated: `{m['payload_generated_at']}`")
    L.append(f"- Payload repo_sha: `{m['payload_repo_sha']}`")
    L.append(f"- Books used: `recent_closed`={m['books']['recent_closed']} (realized) + "
             f"`active_raw[status=OPEN]`={m['books']['active_open']} (unrealized)")
    L.append(f"- Window: last **{m['window_days']} days** "
             f"({m['window'][0] if m['window'] else 'n/a'} → {m['window'][1] if m['window'] else 'n/a'})")
    cov = m["open_date_coverage"]
    L.append(f"- Open-date coverage: closed {cov['closed_with_open_date']}/{cov['closed_total']}; "
             f"active {cov['active_with_open_date']}/{cov['active_total']}")
    L.append("")
    L.append("**Units.** `Σ P/L` — sum of per-pick `pnl_pct` in percentage points, "
             "equal-weight (1 unit per pick); realized for closed picks, current "
             "(unrealized) for still-open picks. `PF` — gross win ÷ gross loss in "
             "the same pp terms. `DD` — max peak-to-trough of the cumulative Σ P/L "
             "series, pp.")
    L.append("")
    L.append(f"**Open-date method.** {m['date_method']}.")
    L.append(f"**Win-rate basis.** {m['wr_basis']}.")
    L.append(f"**Drawdown basis.** {m['dd_basis']}.")
    L.append("")
    L.append("## By open date × asset class")
    L.append("")
    L.append("| Open date | Asset class | N | Closed | Open | W/L/F | Decided | WR% | Σ P/L% | PF | DD% | Avg%/pick |")
    L.append("|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|")
    for r in res["by_date"]:
        wr = "" if r["wr"] is None else f"{r['wr']:.1f}"
        thin = " †" if _thin(r) else ""
        L.append(
            f"| {r['date']} | {r['asset_class']}{thin} | {r['n']} | {r['closed']} | {r['open']} | "
            f"{r['wins']}/{r['losses']}/{r['flat']} | {r['decided']} | {wr} | "
            f"{_pct(r['pl_pct'])} | {_pf(r)} | {r['max_dd_pct']:.2f} | {_pct(r['avg_pl_pct'])} |"
        )
    L.append("")
    L.append("## By asset class (full book window)")
    L.append("")
    L.append("| Asset class | N | Closed | Open | W/L/F | Decided | WR% | Realized Σ P/L% | Unrealized Σ P/L% | Current Σ P/L% | PF | MaxDD% | Avg%/pick |")
    L.append("|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in res["by_class"]:
        wr = "" if r["wr"] is None else f"{r['wr']:.1f}"
        thin = " †" if _thin(r) else ""
        L.append(
            f"| {r['asset_class']}{thin} | {r['n']} | {r['closed']} | {r['open']} | "
            f"{r['wins']}/{r['losses']}/{r['flat']} | {r['decided']} | {wr} | {_pct(r['realized_pl_pct'])} | "
            f"{_pct(r['unrealized_pl_pct'])} | {_pct(r['pl_pct'])} | {_pf(r)} | "
            f"{r['max_dd_pct']:.2f} | {_pct(r['avg_pl_pct'])} |"
        )
    L.append("")
    L.append("`W/L/F` = wins / losses / flat (pnl_pct exactly 0). `Decided` = W+L; "
             "**WR% is wins ÷ decided**, so flat rows are excluded from the denominator "
             "(N is not the denominator). `†` = thin sample (fewer than 30 decided picks).")
    L.append("")
    return "\n".join(L)


def _tone(v):
    if v is None:
        return "#94a3b8"
    return "#4ade80" if v > 0 else ("#f87171" if v < 0 else "#94a3b8")


def _td(v, dp=2):
    return f'<span style="color:{_tone(v)}">{_pct(v, dp)}</span>'


def render_html(res):
    """A self-contained dark-theme fragment matching the updates page."""
    m = res["meta"]
    cov = m["open_date_coverage"]
    ts = m["payload_generated_at"] or ""
    win = m["window"] or ["n/a", "n/a"]

    rows = []
    for r in res["by_date"]:
        wr = "—" if r["wr"] is None else f"{r['wr']:.1f}"
        thin = (' <span style="color:#f59e0b" title="thin sample: '
                'fewer than 30 decided picks">&dagger;</span>') if _thin(r) else ""
        rows.append(
            "<tr>"
            f'<td>{r["date"]}</td><td><strong>{r["asset_class"]}</strong>{thin}</td>'
            f'<td style="text-align:right">{r["n"]}</td>'
            f'<td style="text-align:right">{r["closed"]}</td>'
            f'<td style="text-align:right">{r["open"]}</td>'
            f'<td style="text-align:right">{r["wins"]}/{r["losses"]}/{r["flat"]}</td>'
            f'<td style="text-align:right">{r["decided"]}</td>'
            f'<td style="text-align:right">{wr}</td>'
            f'<td style="text-align:right">{_td(r["pl_pct"])}</td>'
            f'<td style="text-align:right">{_pf(r)}</td>'
            f'<td style="text-align:right">{r["max_dd_pct"]:.2f}</td>'
            f'<td style="text-align:right">{_td(r["avg_pl_pct"])}</td>'
            "</tr>"
        )

    crows = []
    for r in res["by_class"]:
        wr = "—" if r["wr"] is None else f"{r['wr']:.1f}"
        thin = (' <span style="color:#f59e0b" title="thin sample: '
                'fewer than 30 decided picks">&dagger;</span>') if _thin(r) else ""
        crows.append(
            "<tr>"
            f'<td><strong>{r["asset_class"]}</strong>{thin}</td>'
            f'<td style="text-align:right">{r["n"]}</td>'
            f'<td style="text-align:right">{r["closed"]}</td>'
            f'<td style="text-align:right">{r["open"]}</td>'
            f'<td style="text-align:right">{r["wins"]}/{r["losses"]}/{r["flat"]}</td>'
            f'<td style="text-align:right">{r["decided"]}</td>'
            f'<td style="text-align:right">{wr}</td>'
            f'<td style="text-align:right">{_td(r["realized_pl_pct"])}</td>'
            f'<td style="text-align:right">{_td(r["unrealized_pl_pct"])}</td>'
            f'<td style="text-align:right">{_td(r["pl_pct"])}</td>'
            f'<td style="text-align:right">{_pf(r)}</td>'
            f'<td style="text-align:right">{r["max_dd_pct"]:.2f}</td>'
            f'<td style="text-align:right">{_td(r["avg_pl_pct"])}</td>'
            "</tr>"
        )

    th = ('style="text-align:left;padding:4px;border-bottom:1px solid #2a2a3e"')
    thr = ('style="text-align:right;padding:4px;border-bottom:1px solid #2a2a3e"')
    td = 'style="padding:4px;border-bottom:1px solid #1c1c2a"'

    return f'''<div class="update-entry" style="--dot-color: #38bdf8;" data-tags="picks,stats,by-date,by-asset-class,profit-factor,drawdown,current-pnl" data-category="trading" data-types="analysis">
      <div class="update-date" style="line-height:1.5">Oct 06, 2026 &mdash; <strong style="color:#38bdf8;">Recent picks: stats by open date &times; asset class &mdash; current P/L, profit factor and drawdown</strong></div>
      <div class="update-content">
        <p><strong>What this is:</strong> a read-only breakdown of the picks on <a href="/audit/">/audit</a> by the <strong>date they were opened</strong> and by <strong>asset class</strong>, with the numbers a trader actually asks for &mdash; current P/L, profit factor and max drawdown. It is computed straight from the live audit payload, so it can never disagree with the tables on /audit.</p>
        <p style="font-size:0.86em;color:#cbd5e1"><strong>Win rate, honestly defined:</strong> <code>WR%</code> is <strong>wins &divide; decided</strong> (wins + losses). Flat picks (<code>pnl_pct</code> exactly 0 &mdash; mostly still-open rows the pricer has not moved yet) sit <em>outside</em> the denominator, so <code>N</code> is <strong>not</strong> the win-rate base. The <code>W/L/F</code> and <code>Decided</code> columns show the real base; classes resting on fewer than 30 decided picks are marked <span style="color:#f59e0b">&dagger;</span>.</p>

        <p><strong>Source &amp; books.</strong> Payload generated <code>{ts}</code> (repo_sha <code>{(m['payload_repo_sha'] or '')[:12]}</code>). Realized rows come from <code>recent_closed</code> ({m['books']['recent_closed']}); unrealized rows are <code>active_raw</code> rows still <code>status=OPEN</code> ({m['books']['active_open']}). Window: last <strong>{m['window_days']} days</strong> ({win[0]} &rarr; {win[1]}).</p>

        <p><strong>Units.</strong> <code>&Sigma; P/L</code> is the sum of per-pick <code>pnl_pct</code> in percentage points, equal-weight (1 unit per pick) &mdash; realized for closed picks, <em>current/unrealized</em> for still-open picks. <code>PF</code> is gross win &divide; gross loss in the same pp terms. <code>DD</code> is the max peak-to-trough of the cumulative &Sigma; P/L series.</p>

        <h3 style="color:#a78bfa;margin:14px 0 6px">By open date &times; asset class</h3>
        <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:0.86em">
          <tr>
            <th {th}>Open date</th><th {th}>Class</th><th {thr}>N</th><th {thr}>Closed</th>
            <th {thr}>Open</th><th {thr}>W/L/F</th><th {thr}>Decided</th><th {thr}>WR%</th>
            <th {thr}>&Sigma; P/L%</th><th {thr}>PF</th><th {thr}>DD%</th><th {thr}>Avg%/pick</th>
          </tr>
          {''.join(rows)}
        </table>
        </div>

        <h3 style="color:#a78bfa;margin:16px 0 6px">By asset class (full book &mdash; all rows, no date filter)</h3>
        <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:0.86em">
          <tr>
            <th {th}>Class</th><th {thr}>N</th><th {thr}>Closed</th><th {thr}>Open</th>
            <th {thr}>W/L/F</th><th {thr}>Decided</th><th {thr}>WR%</th>
            <th {thr}>Realized &Sigma; P/L%</th>
            <th {thr}>Unrealized &Sigma; P/L%</th><th {thr}>Current &Sigma; P/L%</th>
            <th {thr}>PF</th><th {thr}>MaxDD%</th><th {thr}>Avg%/pick</th>
          </tr>
          {''.join(crows)}
        </table>
        </div>

        <p style="font-size:0.85em;color:#94a3b8"><strong>Honest limitations.</strong> Open-date coverage &mdash; closed {cov['closed_with_open_date']}/{cov['closed_total']}, active {cov['active_with_open_date']}/{cov['active_total']}; closed rows with no genuine entry timestamp are excluded from the by-date table (but counted in the by-class table). Rows with a missing <code>pnl_pct</code> are excluded from P/L and PF. <code>DD</code> is computed on the cumulative P/L curve ordered by <em>realization time</em> (<code>closed_at</code> for closed rows, still-open rows appended last) &mdash; it is an order-sensitive path metric, not a per-pick average. P/L is an equal-weight sum of per-pick percentage returns, not a compounded portfolio return. Not financial advice &mdash; research/educational.</p>
        <p style="font-size:0.78em;color:#64748b">Generated by <code>tools/recent_picks_by_date_class_stats.py</code> from the live payload. Re-run any time; no writes to the pipeline.</p>
      </div>
    </div>
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=LIVE_URL)
    ap.add_argument("--json", dest="json_path", default=None,
                    help="read a local dashboard_data.json instead of the live URL")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--out-md", default=None)
    ap.add_argument("--out-html", default=None)
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()

    payload = load(url=args.url, path=args.json_path)
    res = build(payload, days=args.days)

    md = render_md(res)
    if args.out_md:
        with open(args.out_md, "w", encoding="utf-8") as f:
            f.write(md)
    if args.out_html:
        with open(args.out_html, "w", encoding="utf-8") as f:
            f.write(render_html(res))
    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1)

    m = res["meta"]
    print(f"books: closed={m['books']['recent_closed']} open={m['books']['active_open']} "
          f"| window={m['window']} | by_date_rows={len(res['by_date'])} "
          f"| by_class_rows={len(res['by_class'])}")
    for r in res["by_class"]:
        wr = "n/a" if r["wr"] is None else f"{r['wr']:.1f}%"
        print(f"  {r['asset_class']:<12} n={r['n']:<5} W/L/F={r['wins']}/{r['losses']}/{r['flat']:<5} "
              f"WR={wr:<7} curPL={_pct(r['pl_pct'])}% PF={_pf(r)} maxDD={r['max_dd_pct']:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
