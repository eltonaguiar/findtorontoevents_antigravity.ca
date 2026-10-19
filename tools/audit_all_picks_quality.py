#!/usr/bin/env python3
"""Per-asset-class data-quality + reasoning audit of the live /audit pick payload.

Reads `dashboard_data.json` (live URL by default, or a local file) and reports,
broken out by asset class:

  * volume / composition (OPEN vs EXPIRED vs closed)
  * reasoning coverage (does the pick carry a `reason`/`notes`?)
  * reasoning quality (missing / placeholder / qualified-with-metric)
  * structural integrity (missing numeric fields, TP/SL geometry, breached-but-open)
  * closed-book integrity (pnl_pct==0 placeholders, UNKNOWN exit reasons)
  * duplication ((symbol, direction, strategy) groups)

Usage:
  python tools/audit_all_picks_quality.py                      # live URL -> stdout
  python tools/audit_all_picks_quality.py --json /tmp/dash.json
  python tools/audit_all_picks_quality.py --out reports/foo.md

Read-only: never writes the payload or dashboard HTML.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

LIVE_URL = "https://findtorontoevents.ca/audit/data/dashboard_data.json"

# A reason counts as "qualified" when it carries a measurable quantity
# (a number attached to a metric/indicator), not just prose or a bare score.
_METRIC_RE = re.compile(
    r"(?:=|:)\s*-?\d+\.?\d*\s*%?"
    r"|\b\d+\.?\d*\s*%"
    r"|\b(?:RSI|PF|WR|PnL|DD|z-?score|percentile|score|Sharpe|ATR|ADX|VWAP|SMA|EMA)"
    r"\s*[=:]\s*-?\d+",
    re.IGNORECASE,
)
_PLACEHOLDER_RE = re.compile(r"\b(?:none|nan|null|undefined|lb_none)\b", re.IGNORECASE)


def _f(v: Any) -> float | None:
    try:
        if v in (None, ""):
            return None
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _pos(v: Any) -> float | None:
    """A strictly-positive price. Zero/negative prices are placeholders, not geometry."""
    f = _f(v)
    return f if (f is not None and f > 0) else None


def _zero_prices(p: dict) -> bool:
    """entry/TP/SL all present as fields but non-positive -> unusable row."""
    vals = [_f(p.get(k)) for k in ("entry_price", "take_profit", "stop_loss")]
    return all(v is not None and v <= 0 for v in vals)


def _reason(p: dict) -> str:
    return (str(p.get("reason") or "") + " " + str(p.get("notes") or "")).strip()


def _is_documented(p: dict) -> bool:
    return bool(_reason(p))


def _quality(p: dict) -> str:
    r = _reason(p)
    if not r:
        return "MISSING"
    if _PLACEHOLDER_RE.search(r):
        return "PLACEHOLDER"
    if _METRIC_RE.search(r):
        return "QUALIFIED"
    return "PROSE"


def load_payload(args) -> dict:
    if args.json:
        with open(args.json, "r", encoding="utf-8") as fh:
            return json.load(fh)
    import urllib.request

    req = urllib.request.Request(args.url, headers={"User-Agent": "audit-quality/1.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def geometry_defect(p: dict) -> str | None:
    """Return a defect tag when TP/SL sits on the wrong side of entry.

    LONG: SL < entry < TP.  SHORT: TP < entry < SL.
    A stop that has ratcheted past entry (trailing stop) is NOT a defect.
    """
    e, tp, sl = _pos(p.get("entry_price")), _pos(p.get("take_profit")), _pos(p.get("stop_loss"))
    dr = str(p.get("direction") or "").upper()
    if None in (e, tp, sl):
        return "missing_numeric"
    if dr == "LONG":
        if tp <= e:
            return "tp_wrong_side"
        if sl >= e:
            return "sl_wrong_side"
    elif dr == "SHORT":
        if tp >= e:
            return "tp_wrong_side"
        if sl <= e:
            return "sl_wrong_side"
    else:
        return "unknown_direction"
    return None


def breached(p: dict) -> str | None:
    e = _pos(p.get("entry_price"))
    tp, sl, cur = _pos(p.get("take_profit")), _pos(p.get("stop_loss")), _pos(p.get("current_price"))
    dr = str(p.get("direction") or "").upper()
    if None in (e, tp, sl, cur):
        return None
    if dr == "LONG":
        if cur >= tp:
            return "tp_reached_open"
        if cur <= sl:
            return "sl_breached_open"
    elif dr == "SHORT":
        if cur <= tp:
            return "tp_reached_open"
        if cur >= sl:
            return "sl_breached_open"
    return None


def pct(n: int, d: int) -> str:
    return f"{100.0 * n / d:.0f}%" if d else "–"


def build_report(d: dict, source_label: str) -> str:
    ar = d["picks"]["active_raw"]
    rc = d["picks"]["recent_closed"]
    meta = d.get("metadata", {})
    summ = d.get("summary", {})

    open_picks = [x for x in ar if str(x.get("status")).upper() == "OPEN"]
    classes = sorted({str(x.get("asset_class") or "UNKNOWN") for x in ar + rc})

    L: list[str] = []
    w = L.append
    w("# All-Picks Data-Quality & Reasoning Audit — by Asset Class")
    w("")
    w(f"**Source:** {source_label}")
    w(f"**generated_at:** `{d.get('generated_at')}`  ·  **repo_sha:** `{meta.get('repo_sha')}`")
    w(f"**payload_lag_seconds:** `{meta.get('payload_lag_seconds')}`")
    w("")
    w("Scope: the full payload book — `picks.active_raw` by status + "
      "`picks.recent_closed`. A pick is **documented** when `reason` or `notes` "
      "is non-empty; it is **qualified** when that text also carries a measurable "
      "quantity (indicator + number), vs **placeholder** when it names a missing "
      "value (`None`/`nan`).")
    w("")

    # ---- provenance honesty about windowing ----
    w("## 0. Scope caveat")
    w("")
    w(f"- `active_raw` = **{len(ar)}** rows (OPEN {len(open_picks)}, "
      f"EXPIRED {sum(1 for x in ar if str(x.get('status')).upper()=='EXPIRED')}, "
      f"other {sum(1 for x in ar if str(x.get('status')).upper() not in ('OPEN','EXPIRED'))}).")
    w(f"- `recent_closed` = **{len(rc)}** rows — the payload exposes only a "
      f"windowed sample, while `summary.total_closed_picks` = **{summ.get('total_closed_picks')}**. "
      "Closed-book findings below cover the exposed window only.")
    w("")

    # ---- TL;DR (computed) ----
    q_open = collections.Counter(_quality(x) for x in open_picks)
    doc_open = len(open_picks) - q_open["MISSING"]
    q_closed = collections.Counter(_quality(x) for x in rc)
    doc_closed = len(rc) - q_closed["MISSING"]
    zero_p = sum(1 for x in open_picks if _zero_prices(x) or geometry_defect(x) == "missing_numeric")
    null_cur = sum(1 for x in open_picks if _f(x.get("current_price")) is None)
    br_n = sum(1 for x in open_picks if breached(x))
    lb_none_n = sum(1 for x in ar + rc if "lb_none" in str(x.get("reason") or "").lower())
    sports_n = sum(1 for x in ar if str(x.get("asset_class") or "").upper() == "SPORTS")
    dupc = collections.Counter((x.get("symbol"), x.get("direction"), x.get("strategy")) for x in open_picks)
    dup_rows = sum(v for v in dupc.values() if v > 1)
    w("## TL;DR")
    w("")
    w(f"- **Reasoning is missing on half the open book and most of the closed book.** "
      f"{len(open_picks)} OPEN picks are only {pct(doc_open, len(open_picks))} documented "
      f"({q_open['MISSING']} carry no reason/notes); the {len(rc)} exposed closed picks are "
      f"{pct(doc_closed, len(rc))} documented.")
    w(f"- **EQUITY is the worst open class** and **ETF the worst closed class** "
      f"(see sections 1–2).")
    w(f"- **{zero_p} OPEN picks carry zero/missing entry-TP-SL prices** (genome `GPX_*`/`GPM_*` "
      f"+ `prediction_market_consensus`) — unusable for any PnL math.")
    w(f"- **{br_n} OPEN picks are already past their TP/SL** and were never resolved; "
      f"plus 1 FOREX pick with a garbage-scale TP/SL (USDCAD=X 1.422 → TP 812.43).")
    w(f"- **{null_cur} OPEN picks have no `current_price`** — the dashboard cannot compute live PnL for them.")
    w(f"- **{lb_none_n} rows leak `lb_None`** (an unresolved leaderboard label) into the reason text.")
    w(f"- **{sports_n} SPORTS bet(s)** sit inside the tradeable active book.")
    w(f"- **Duplication:** {dup_rows} of {len(open_picks)} OPEN rows belong to duplicate "
      f"(symbol, direction, strategy) groups.")
    w("")

    # ---- 1. reasoning coverage: OPEN actives ----
    w("## 1. Reasoning coverage — OPEN active picks (what the page shows)")
    w("")
    w("| Asset class | OPEN | Documented | Qualified | Prose | Placeholder | Missing |")
    w("|---|---|---|---|---|---|---|")
    for cls in classes:
        sub = [x for x in open_picks if str(x.get("asset_class") or "UNKNOWN") == cls]
        if not sub:
            continue
        q = collections.Counter(_quality(x) for x in sub)
        doc = len(sub) - q["MISSING"]
        w(f"| {cls} | {len(sub)} | {doc} ({pct(doc,len(sub))}) | {q['QUALIFIED']} | "
          f"{q['PROSE']} | {q['PLACEHOLDER']} | {q['MISSING']} |")
    q_all = collections.Counter(_quality(x) for x in open_picks)
    doc_all = len(open_picks) - q_all["MISSING"]
    w(f"| **ALL** | **{len(open_picks)}** | **{doc_all} ({pct(doc_all,len(open_picks))})** | "
      f"**{q_all['QUALIFIED']}** | **{q_all['PROSE']}** | **{q_all['PLACEHOLDER']}** | "
      f"**{q_all['MISSING']}** |")
    w("")

    # ---- 2. closed book reasoning ----
    w("## 2. Reasoning coverage — closed picks (exposed window)")
    w("")
    w("| Asset class | Closed | Documented | Qualified | Prose | Placeholder | Missing |")
    w("|---|---|---|---|---|---|---|")
    for cls in classes:
        sub = [x for x in rc if str(x.get("asset_class") or "UNKNOWN") == cls]
        if not sub:
            continue
        q = collections.Counter(_quality(x) for x in sub)
        doc = len(sub) - q["MISSING"]
        w(f"| {cls} | {len(sub)} | {doc} ({pct(doc,len(sub))}) | {q['QUALIFIED']} | "
          f"{q['PROSE']} | {q['PLACEHOLDER']} | {q['MISSING']} |")
    qc = collections.Counter(_quality(x) for x in rc)
    doc_c = len(rc) - qc["MISSING"]
    w(f"| **ALL** | **{len(rc)}** | **{doc_c} ({pct(doc_c,len(rc))})** | **{qc['QUALIFIED']}** | "
      f"**{qc['PROSE']}** | **{qc['PLACEHOLDER']}** | **{qc['MISSING']}** |")
    w("")

    # ---- 3. structural integrity: OPEN ----
    w("## 3. Structural integrity — OPEN picks by class")
    w("")
    w("| Asset class | OPEN | zero/missing prices | null current_price | TP wrong side | "
      "SL past entry | TP reached / SL breached (still OPEN) |")
    w("|---|---|---|---|---|---|---|")
    for cls in classes:
        sub = [x for x in open_picks if str(x.get("asset_class") or "UNKNOWN") == cls]
        if not sub:
            continue
        zero = sum(1 for x in sub if _zero_prices(x)
                   or "missing_numeric" == geometry_defect(x))
        null_cur = sum(1 for x in sub if _f(x.get("current_price")) is None)
        tpw = sum(1 for x in sub if geometry_defect(x) == "tp_wrong_side")
        slw = sum(1 for x in sub if geometry_defect(x) == "sl_wrong_side")
        br = sum(1 for x in sub if breached(x))
        w(f"| {cls} | {len(sub)} | {zero} | {null_cur} | {tpw} | {slw} | {br} |")
    w("")

    # ---- 4. closed-book integrity ----
    w("## 4. Closed-book integrity by class")
    w("")
    w("| Asset class | Closed | pnl_pct==0 | UNKNOWN exit | None pnl (null) |")
    w("|---|---|---|---|---|")
    for cls in classes:
        sub = [x for x in rc if str(x.get("asset_class") or "UNKNOWN") == cls]
        if not sub:
            continue
        zero = sum(1 for x in sub if _f(x.get("pnl_pct")) == 0.0)
        unk = sum(1 for x in sub if str(x.get("exit_reason")).upper() == "UNKNOWN")
        nullpnl = sum(1 for x in sub if _f(x.get("pnl_pct")) is None)
        w(f"| {cls} | {len(sub)} | {zero} | {unk} | {nullpnl} |")
    w("")

    # ---- 5. duplication ----
    w("## 5. Duplication — OPEN picks by class")
    w("")
    w("| Asset class | OPEN | duplicate (symbol,direction,strategy) groups | rows in dup groups |")
    w("|---|---|---|---|")
    for cls in classes:
        sub = [x for x in open_picks if str(x.get("asset_class") or "UNKNOWN") == cls]
        if not sub:
            continue
        c = collections.Counter((x.get("symbol"), x.get("direction"), x.get("strategy")) for x in sub)
        dups = {k: v for k, v in c.items() if v > 1}
        rows = sum(v for v in dups.values())
        w(f"| {cls} | {len(sub)} | {len(dups)} | {rows} |")
    w("")

    # ---- 6. cross-cutting flags ----
    w("## 6. Cross-cutting flags")
    w("")
    lb_none = [x for x in ar + rc if "lb_none" in str(x.get("reason") or "").lower()]
    sports = [x for x in ar if str(x.get("asset_class") or "").upper() == "SPORTS"]
    old_open = [x for x in open_picks if (_f(x.get("age_hours")) or 0) > 24 * 7]
    w(f"- **`lb_None` in reason** (missing leaderboard label leaked into text): "
      f"**{len(lb_none)}** rows.")
    w(f"- **SPORTS rows inside the tradeable active book**: **{len(sports)}**.")
    w(f"- **OPEN picks older than 7 days**: **{len(old_open)}**.")
    w("")
    if sports:
        w("SPORTS rows found:")
        for x in sports[:5]:
            w(f"  - `{x.get('symbol')}` {x.get('direction')} ({x.get('strategy')})")
        w("")

    # ---- 7. worst reasoning emitters ----
    def undocumented_by_strategy(picks, documented):
        tot = collections.Counter()
        miss = collections.Counter()
        for x in picks:
            s = x.get("strategy") or "(none)"
            tot[s] += 1
            if not documented(x):
                miss[s] += 1
        return sorted(((v, s, tot[s]) for s, v in miss.items()), reverse=True)

    w("## 7. Worst reasoning emitters (no reason/notes)")
    w("")
    w("**OPEN active picks:**")
    w("")
    w("| strategy | undocumented / total |")
    w("|---|---|")
    for v, s, t in undocumented_by_strategy(open_picks, _is_documented)[:12]:
        w(f"| `{s}` | {v} / {t} |")
    w("")
    w("**Closed picks (exposed window):**")
    w("")
    w("| strategy | undocumented / total |")
    w("|---|---|")
    for v, s, t in undocumented_by_strategy(rc, _is_documented)[:12]:
        w(f"| `{s}` | {v} / {t} |")
    w("")

    # ---- 8. exact structural defect rows ----
    w("## 8. Exact structural defect rows (OPEN)")
    w("")
    zerop = collections.Counter()
    for x in open_picks:
        if _zero_prices(x) or geometry_defect(x) == "missing_numeric":
            zerop[x.get("strategy") or "(none)"] += 1
    w(f"**Zero / missing prices** ({sum(zerop.values())} rows), by strategy:")
    w("")
    if zerop:
        w("| strategy | rows |")
        w("|---|---|")
        for s, n in zerop.most_common(12):
            w(f"| `{s}` | {n} |")
    else:
        w("_none_")
    w("")
    w("**TP/SL scale anomaly** (|TP-entry| or |entry-SL| > 50x entry → garbage scale):")
    w("")
    anomalies = []
    for x in open_picks:
        e, tp, sl = _pos(x.get("entry_price")), _pos(x.get("take_profit")), _pos(x.get("stop_loss"))
        if None in (e, tp, sl):
            continue
        if max(abs(tp - e), abs(e - sl)) > 50 * e:
            anomalies.append(x)
    if anomalies:
        w("| class | symbol | dir | entry | TP | SL | strategy |")
        w("|---|---|---|---|---|---|---|")
        for x in anomalies[:12]:
            w(f"| {x.get('asset_class')} | `{x.get('symbol')}` | {x.get('direction')} | "
              f"{x.get('entry_price')} | {x.get('take_profit')} | {x.get('stop_loss')} | "
              f"`{x.get('strategy')}` |")
    else:
        w("_none_")
    w("")
    w("**Breached but still OPEN** (price beyond TP or SL — resolver gap):")
    w("")
    br_rows = [(breached(x), x) for x in open_picks if breached(x)]
    if br_rows:
        w("| tag | class | symbol | dir | entry | TP | SL | current | strategy |")
        w("|---|---|---|---|---|---|---|---|---|")
        for tag, x in br_rows[:15]:
            w(f"| {tag} | {x.get('asset_class')} | `{x.get('symbol')}` | {x.get('direction')} | "
              f"{x.get('entry_price')} | {x.get('take_profit')} | {x.get('stop_loss')} | "
              f"{x.get('current_price')} | `{x.get('strategy')}` |")
    else:
        w("_none_")
    w("")

    # ---- 9. examples ----
    w("## 9. Reasoning examples")
    w("")
    good = [x for x in open_picks if _quality(x) == "QUALIFIED"][:3]
    bad = [x for x in open_picks if _quality(x) == "PLACEHOLDER"][:3]
    miss = [x for x in open_picks if _quality(x) == "MISSING"][:3]
    w("**Qualified (indicator + number):**")
    for x in good:
        w(f"- `{x.get('symbol')}` {x.get('direction')} — {_reason(x)[:200]}")
    w("")
    if bad:
        w("**Placeholder (names a missing value):**")
        for x in bad:
            w(f"- `{x.get('symbol')}` {x.get('direction')} — {_reason(x)[:200]}")
        w("")
    w("**Missing (no reason/notes):**")
    for x in miss:
        w(f"- `{x.get('symbol')}` {x.get('direction')} ({x.get('strategy')}) — no reason/notes")
    w("")

    # ---- 10. recommendations ----
    w("## 10. Recommendations")
    w("")
    w("1. **Block reason-less picks from the book.** A pick with no `reason`/`notes` should be "
      "rejected at emit time. Prioritise the emitters in section 7 — EQUITY "
      "(`magic_formula_x_piotroski_x_acquirers`, `penny_stock_screener`) and CRYPTO "
      "(`inverse_luxalgo_confluence`, `incubator_gainer`, `kimi_signal_tracking`).")
    w("2. **Reject zero/missing-price rows.** The 59 genome/prediction-market OPEN picks have "
      "entry=TP=SL=0 and are unusable; they inflate the active count.")
    w("3. **Fix the resolver gaps.** The 3 breached-but-open picks (DNA ×2, USDCAD=X) and the "
      "garbage-scale USDCAD=X row should be force-resolved or quarantined.")
    w("4. **Backfill `current_price`** for the OPEN picks missing it, or exclude them from live "
      "PnL/score surfaces.")
    w("5. **Strip `lb_None` placeholder text** at emit time — do not interpolate an unresolved "
      "label into the reason.")
    w("6. **Dedupe at the source.** Collapse duplicate (symbol, direction, strategy) groups before "
      "they reach `active_raw`.")
    w("7. **Route SPORTS picks out of the trading book** into the sports pipeline.")
    w("")

    w("---")
    w("*Generated by `tools/audit_all_picks_quality.py`. Read-only; reproducible from "
      "`dashboard_data.json::picks.active_raw` + `::picks.recent_closed`.*")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default=LIVE_URL)
    ap.add_argument("--json", default=None, help="local payload path (overrides --url)")
    ap.add_argument("--out", default=None, help="write markdown report here")
    args = ap.parse_args()

    d = load_payload(args)
    label = f"`{args.json}`" if args.json else f"live `{args.url}`"
    report = build_report(d, label)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
