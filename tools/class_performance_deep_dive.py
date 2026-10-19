#!/usr/bin/env python3
"""Per-asset-class pick-performance VERDICT, with earlier-picks fallback.

Question it answers:
  "Do we have strong performance per asset class — and where the recent window
   is too thin to tell, what do EARLIER (now-resolved) picks say?"

Primary basis  : the /audit pick book (picks.recent_closed = realised,
                 picks.active_raw[status=OPEN] = unrealised), equal-weight
                 per-pick `pnl_pct` in percentage points.
Fallback basis : the full 7.5-month book ("ALL" window) and the broader
                 `performance.asset_class_health` all-time ledger view.
Also flags    : asset classes with NO recent picks, and why.

Read-only. Live payload by default; --json <path> for offline.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import urllib.request
from datetime import datetime, timedelta, timezone

LIVE = "https://findtorontoevents.ca/audit/data/dashboard_data.json"
CLASS_ORDER = ["CRYPTO", "EQUITY", "FOREX", "COMMODITY", "ETF",
               "FUTURES", "BOND", "MEME", "PENNY_STOCK", "SPORTS"]
Z = 1.96


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load(path=None, url=LIVE):
    if path:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    req = urllib.request.Request(url, headers={"User-Agent": "class-verdict/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def d10(row, *keys):
    for k in keys:
        v = (row.get(k) or "").strip()
        if v:
            return v[:10]
    return None


def closed_date(r):
    return d10(r, "closed_at", "exit_time")


def entry_date(r):
    return d10(r, "entry_time", "timestamp", "signal_time")


def wilson_lb(wins, n):
    if n == 0:
        return None
    p = wins / n
    d = 1 + Z * Z / n
    c = p + Z * Z / (2 * n)
    m = Z * math.sqrt((p * (1 - p) + Z * Z / (4 * n)) / n)
    return (c - m) / d


def metrics(vals):
    n = len(vals)
    if n == 0:
        return None
    wins = sum(1 for v in vals if v > 0)
    losses = sum(1 for v in vals if v < 0)
    flat = n - wins - losses
    decided = wins + losses
    mean = sum(vals) / n
    sd = statistics.pstdev(vals) if n > 1 else 0.0
    se = sd / math.sqrt(n)
    t = mean / se if se > 0 else None
    gw = sum(v for v in vals if v > 0)
    gl = abs(sum(v for v in vals if v < 0))
    return {
        "n": n, "wins": wins, "losses": losses, "flat": flat, "decided": decided,
        "wr": (100 * wins / decided) if decided else None,
        "wr_lb": (100 * wilson_lb(wins, decided)) if decided else None,
        "mean": mean, "sd": sd, "t": t, "sum": sum(vals),
        "pf": (gw / gl) if gl > 0 else None, "gw": gw, "gl": gl,
    }


def verdict(mm):
    """Classify by statistical credibility, not by sign alone."""
    if not mm or mm["decided"] < 30:
        return "TOO EARLY"
    pf = mm["pf"] or 0.0
    wrlb = mm["wr_lb"] or 0.0
    t = mm["t"] or 0.0
    if pf >= 1.2 and wrlb >= 45 and t >= 2:
        return "STRONG"
    if mm["mean"] > 0 and pf >= 1.05 and t > 0:
        return "MODEST"
    if mm["mean"] < 0 or pf < 1.0:
        return "WEAK"
    return "INCONCLUSIVE"


WINDOWS = [("7d", 7), ("14d", 14), ("30d", 30), ("90d", 90), ("ALL", None)]


def build(payload):
    picks = payload.get("picks") or {}
    closed = list(picks.get("recent_closed") or [])
    active = [r for r in (picks.get("active_raw") or []) if r.get("status") == "OPEN"]

    cds = sorted(d for d in (closed_date(r) for r in closed) if d)
    latest = cds[-1]
    y, m, dd = map(int, latest.split("-"))
    base = datetime(y, m, dd, tzinfo=timezone.utc)

    out = {}
    for cls in CLASS_ORDER:
        rows = [r for r in closed if (r.get("asset_class") or "UNKNOWN") == cls]
        wins_per = {}
        for label, days in WINDOWS:
            if days is None:
                sub = rows
            else:
                lo = (base - timedelta(days=days)).strftime("%Y-%m-%d")
                sub = [r for r in rows if (closed_date(r) or "") >= lo]
            vals = [v for v in (_f(r.get("pnl_pct")) for r in sub) if v is not None]
            wins_per[label] = metrics(vals)
        out[cls] = {
            "recent": wins_per,
            "open_rows": [r for r in active if (r.get("asset_class") or "") == cls],
        }
    return out, {"closed_at_span": (cds[0], cds[-1]),
                 "recent_closed": len(closed), "active_open": len(active),
                 "generated_at": payload.get("generated_at"),
                 "repo_sha": (payload.get("metadata") or {}).get("repo_sha")}


def fmt(mm):
    if not mm:
        return "—"
    return (f"{mm['n']} | {mm['wins']}/{mm['losses']}/{mm['flat']} | {mm['decided']} | "
            f"{(mm['wr'] or 0):.1f} | {(mm['wr_lb'] or 0):.1f} | "
            f"{(mm['pf'] if mm['pf'] is not None else 0):.2f} | {mm['mean']:+.3f} | "
            f"{(mm['t'] if mm['t'] is not None else 0):+.2f} | {mm['sum']:+.1f} | "
            f"{verdict(mm)}")


NO_RECENT_PICKS_NOTE = {
    "MEME": "zero rows in BOTH books (0 closed, 0 open).",
    "PENNY_STOCK": "zero rows in BOTH books (0 closed, 0 open).",
}

ROOT_CAUSE = """
**Why MEME and PENNY_STOCK emit nothing.** The MEME/PENNY enhanced-v2 strategies
*are* declared (`alpha_engine/june2026_research_candidates.py`:
`ENHANCED_V2_BY_CLASS["MEME"]`, `["PENNY_STOCK"]`), but `_build_generators()`
gates each one on its flagship generator:

```python
entry = FLAGSHIP_BY_CLASS.get(ac)
if not entry:
    continue          # <-- skipped entirely, no generator registered
```

`FLAGSHIP_BY_CLASS` (`alpha_engine/eight_class_flagship_strategies.py`) has keys
`CRYPTO, EQUITY, ETF, FOREX, COMMODITY, FUTURES, BOND, PREDICTION_MARKETS,
CHEAP_STOCKS, IPO` — **there is no `MEME` key and no `PENNY_STOCK` key**, so both
classes fall through the `continue` and never produce a forward-observation pick.
Compounding causes: the academic emitter wires only 1 of 3 MEME strategies
(`academic_strategies_emitter.py`: "MEME 1/3 wired (prototype)"), and MEME's
position cap was halved (`per_class_position_caps.py`: `"MEME": 0.01  # CUT 50%
2026-06-12`). Even the broad all-time ledger is tiny for these: MEME n=10
(PF 0.02), PENNY_STOCK n=1 — so there is no "earlier picks" evidence to fall back
on either.
"""

THIN_NOTE = """
**Classes that are genuinely too early (no meaningful closed history).**

- **FUTURES** — 0 closed rows; `performance.resolution_coverage.FUTURES` shows
  `resolved: 0, meets_gate: false`. Nothing to grade yet.
- **SPORTS** — 0 closed rows; `resolution_coverage.SPORTS` `resolved: 0,
  meets_gate: false`. 2 open picks only.
- **COMMODITY** — only 3 closed rows ever; `resolution_coverage.COMMODITY`
  `resolved: 3 / 13 = 23%`, `meets_gate: false`, despite 63 picks still open.
  The resolver is not clearing this class, so "performance" is unknowable today.
- **BOND** — 29 closed rows in the pick book, but `asset_class_health.BOND` is
  `insufficient_data` with `n: 0`: the broader registry/ledger view has no BOND
  entry at all (the local `pf_registry.json` is stale 2026-06-23 and
  `source_files_canonical: false`). A source-coverage gap, not just a small sample.
"""


def render_md(per_class, meta, health):
    L = []
    A = L.append
    A("# Asset-class pick-performance verdict — 2026-10-06")
    A("")
    A(f"- Payload generated: `{meta['generated_at']}` (repo_sha `{(meta['repo_sha'] or '')[:12]}`)")
    A(f"- Book: `recent_closed`={meta['recent_closed']} realised + "
      f"`active_raw[OPEN]`={meta['active_open']} unrealised")
    A(f"- Closed-at span: {meta['closed_at_span'][0]} → {meta['closed_at_span'][1]}")
    A("")
    A("**Basis.** Equal-weight sum of per-pick `pnl_pct` (percentage points), realised "
      "for closed picks. `WR%` = wins ÷ decided; `WRlb95` = Wilson 95% lower bound; "
      "`PF` = gross win ÷ gross loss; `t` = mean/SE (|t| ≥ 2 ≈ 95% confidence the mean "
      "≠ 0); `Σ` = net pp. Windows bucket closed rows by `closed_at`.")
    A("")
    A("**Verdict rule.** TOO EARLY if decided < 30. Else STRONG if PF ≥ 1.20 and "
      "WRlb95 ≥ 45 and t ≥ 2; MODEST if mean > 0 and PF ≥ 1.05 and t > 0; WEAK if "
      "mean < 0 or PF < 1.0; else INCONCLUSIVE.")
    A("")
    A("## Headline")
    A("")
    strong = [c for c in CLASS_ORDER if c in per_class
              and verdict(per_class[c]["recent"].get("ALL") or {}) == "STRONG"]
    early = []
    for c in CLASS_ORDER:
        if c not in per_class:
            continue
        mm = per_class[c]["recent"].get("ALL")
        v = verdict(mm or {})
        if v == "TOO EARLY":
            early.append(c)
        if mm is None:
            early.append(c)
    A(f"- **STRONG**: {', '.join(strong) if strong else 'none'}")
    A(f"- **TOO EARLY (incl. no closed history)**: {', '.join(sorted(set(early)))}")
    A("")
    A("## Per-class detail (window | N | W/L/F | decided | WR% | WRlb95 | PF | mean% | t | Σ% | verdict)")
    A("")
    for cls in CLASS_ORDER:
        if cls not in per_class:
            continue
        A(f"### {cls}")
        A("")
        A("| Window | N | W/L/F | decided | WR% | WRlb95 | PF | mean% | t | Σ% | verdict |")
        A("|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|")
        for lbl, _ in WINDOWS:
            mm = per_class[cls]["recent"].get(lbl)
            if not mm:
                A(f"| {lbl} | 0 | — | — | — | — | — | — | — | — | {verdict(mm)} |")
                continue
            A(f"| {lbl} | {mm['n']} | {mm['wins']}/{mm['losses']}/{mm['flat']} | "
              f"{mm['decided']} | {(mm['wr'] or 0):.1f} | {(mm['wr_lb'] or 0):.1f} | "
              f"{(mm['pf'] if mm['pf'] is not None else 0):.2f} | {mm['mean']:+.3f} | "
              f"{(mm['t'] if mm['t'] is not None else 0):+.2f} | {mm['sum']:+.1f} | "
              f"{verdict(mm)} |")
        A("")

    A("## Classes with NO recent picks — investigation")
    A("")
    A("| Class | recent closed | recent open | status |")
    A("|---|---:|---:|---|")
    for cls in CLASS_ORDER:
        if cls not in per_class:
            A(f"| {cls} | 0 | 0 | no rows at all |")
            continue
        mm = per_class[cls]["recent"].get("ALL")
        nrows = mm["n"] if mm else 0
        opens = len(per_class[cls]["open_rows"])
        note = NO_RECENT_PICKS_NOTE.get(cls, "")
        A(f"| {cls} | {nrows} | {opens} | {note or ('resolvable' if nrows else 'no closed history')} |")
    A("")
    A(ROOT_CAUSE)
    A(THIN_NOTE)

    A("## Cross-check: pick book (recent) vs asset_class_health (broader all-time)")
    A("")
    A("`performance.asset_class_health` is a *different, broader* basis (all-time "
      "ledger; n up to ~8× the recent book). Where the two disagree, treat the "
      "recent book as the apples-to-apples read and the health view as a flag.")
    A("")
    A("| Class | recent ALL: N | recent PF | recent Σ% | health N | health PF | health Σ% | status |")
    A("|---|---:|---:|---:|---:|---:|---:|---|")
    for cls in CLASS_ORDER:
        rec = per_class.get(cls, {}).get("recent", {}).get("ALL")
        h = health.get(cls) or {}
        rn = rec["n"] if rec else 0
        rpf = f"{rec['pf']:.2f}" if rec and rec["pf"] is not None else "—"
        rs = f"{rec['sum']:+.1f}" if rec else "—"
        hpf = h.get("pf")
        A(f"| {cls} | {rn} | {rpf} | {rs} | {h.get('n', '—')} | "
          f"{('%.3f' % hpf) if hpf is not None else '—'} | "
          f"{(h.get('pnl_pct') if h.get('pnl_pct') is not None else '—')} | {h.get('status', '—')} |")
    A("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    ap.add_argument("--url", default=LIVE)
    ap.add_argument("--out-md", default=None)
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()
    payload = load(args.json, args.url)
    per_class, meta = build(payload)
    health = (payload.get("performance") or {}).get("asset_class_health") or {}
    md = render_md(per_class, meta, health)
    if args.out_md:
        open(args.out_md, "w", encoding="utf-8").write(md)
    if args.out_json:
        json.dump({"meta": meta, "per_class": per_class, "health": health},
                  open(args.out_json, "w", encoding="utf-8"), indent=1, default=str)
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
