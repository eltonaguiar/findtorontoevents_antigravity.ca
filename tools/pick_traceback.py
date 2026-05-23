#!/usr/bin/env python3
"""Pick trace-back + edge-attribution analyzer.

Answers, from the picks the system ACTUALLY made (no new DB schema needed —
the attribution already lives per-pick in closed_picks.json / active_picks.json):

  1. Why was each pick picked? — its stored `reason`, scores, grades, strategy.
  2. Does any score actually SEPARATE winners from losers? — the discrimination
     test: mean(score | WON) vs mean(score | LOST). If they are equal, that
     score carries no edge. This is the core "do we have an edge" question.
  3. Per-tier / per-source blueprint — WR / PF grouped by grade + source.

Pure stdlib. Window defaults to the last 14 days of resolved picks.

    python tools/pick_traceback.py [--days 14] [--out reports/pick_traceback.md]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOSED = ROOT / "alpha_engine" / "data" / "closed_picks.json"
ACTIVE = ROOT / "alpha_engine" / "data" / "active_picks.json"

# Score fields the pipeline attaches to a pick — the candidate "edge signals".
SCORE_FIELDS = ("confidence", "elite_score", "ml_score", "ml_composite_score",
                "method_a_score", "forward_wr", "risk_reward")


def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    d = json.loads(path.read_text(encoding="utf-8"))
    picks = d if isinstance(d, list) else d.get("picks", d.get("closed", d.get("active", [])))
    return [p for p in picks if isinstance(p, dict)]


def _resolved_date(p: dict) -> str:
    return str(p.get("resolved_at") or p.get("exit_date") or p.get("timestamp") or "")


def _is_won(p: dict) -> bool | None:
    s = str(p.get("status") or "").upper()
    if s == "WON":
        return True
    if s == "LOST":
        return False
    v = p.get("pnl_pct")
    if v is None:
        return None
    return float(v) > 0


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def agg(picks: list[dict]) -> dict:
    n = len(picks)
    if not n:
        return {"n": 0, "wr": 0.0, "pf": 0.0}
    wins = sum(1 for p in picks if _is_won(p) is True)
    gw = sum(float(p["pnl_pct"]) for p in picks
             if p.get("pnl_pct") is not None and float(p["pnl_pct"]) > 0)
    gl = abs(sum(float(p["pnl_pct"]) for p in picks
                 if p.get("pnl_pct") is not None and float(p["pnl_pct"]) < 0))
    pf = gw / gl if gl > 1e-9 else (999.0 if gw > 0 else 0.0)
    return {"n": n, "wr": wins / n, "pf": pf}


def discrimination(picks: list[dict]) -> list[dict]:
    """For each score field: mean over WON vs over LOST picks.

    A score with edge separates the two. gap≈0 means the score is noise.
    """
    won = [p for p in picks if _is_won(p) is True]
    lost = [p for p in picks if _is_won(p) is False]
    rows = []
    for f in SCORE_FIELDS:
        wv = [x for x in (_num(p.get(f)) for p in won) if x is not None]
        lv = [x for x in (_num(p.get(f)) for p in lost) if x is not None]
        if len(wv) < 5 or len(lv) < 5:
            rows.append({"field": f, "n_won": len(wv), "n_lost": len(lv),
                         "mean_won": None, "mean_lost": None, "gap": None,
                         "verdict": "insufficient"})
            continue
        mw, ml = statistics.mean(wv), statistics.mean(lv)
        sd = statistics.pstdev(wv + lv) or 1e-9
        # standardised gap (Cohen's-d-ish): |Δmean| / pooled sd
        eff = abs(mw - ml) / sd
        verdict = ("EDGE" if eff >= 0.30 else
                   "weak" if eff >= 0.10 else "NOISE")
        rows.append({"field": f, "n_won": len(wv), "n_lost": len(lv),
                     "mean_won": round(mw, 4), "mean_lost": round(ml, 4),
                     "gap": round(mw - ml, 4), "eff": round(eff, 3),
                     "verdict": verdict})
    return rows


def build_report(closed: list[dict], active: list[dict], days: int) -> str:
    overall = agg(closed)
    out = [
        "# Pick Trace-Back & Edge-Attribution — last %d days" % days,
        "",
        f"Window: resolved picks in the last {days} days. "
        f"Closed n={overall['n']} · WR {overall['wr']*100:.1f}% · "
        f"PF {overall['pf']:.2f}. Active picks tracked: {len(active)}.",
        "",
        "## 1. Discrimination test — does any score separate winners from losers?",
        "",
        "For each score the pipeline attaches to a pick: its mean over WON picks "
        "vs over LOST picks. A real edge signal separates the two "
        "(standardised gap `eff` ≥ 0.30). `eff` ≈ 0 = the score is noise — it "
        "does not predict outcome.",
        "",
        "| Score field | mean(WON) | mean(LOST) | gap | eff | verdict |",
        "|---|---|---|---|---|---|",
    ]
    disc = discrimination(closed)
    for r in disc:
        if r["verdict"] == "insufficient":
            out.append(f"| `{r['field']}` | — | — | — | — | insufficient n |")
        else:
            out.append(f"| `{r['field']}` | {r['mean_won']} | {r['mean_lost']} | "
                       f"{r['gap']:+} | {r['eff']} | {r['verdict']} |")
    edges = [r for r in disc if r.get("verdict") == "EDGE"]
    out += ["",
            f"**{len(edges)} of {len(SCORE_FIELDS)} scores show real separation "
            f"(eff≥0.30).** " +
            ("The remaining scores do not predict outcome — picks ranked by them "
             "are no better than random. This is the structural reason the book "
             "has no proven edge: the ranking signals do not discriminate."
             if len(edges) <= 1 else
             "Scores flagged EDGE are the ones worth keeping in the gate.")]

    # 2. per source_strategy_type
    out += ["", "## 2. Blueprint by source-strategy type", "",
            "| source_strategy_type | n | WR | PF |", "|---|---|---|---|"]
    by_src = defaultdict(list)
    for p in closed:
        by_src[str(p.get("source_strategy_type") or "?")].append(p)
    for k in sorted(by_src, key=lambda x: -agg(by_src[x])["n"]):
        a = agg(by_src[k])
        out.append(f"| {k} | {a['n']} | {a['wr']*100:.1f}% | {a['pf']:.2f} |")

    # 3. per grade bucket
    out += ["", "## 3. Blueprint by elite grade", "",
            "Does a better grade mean a better outcome? (if WR is flat across "
            "grades, the grade is not an edge)",
            "", "| elite_grade | n | WR | PF |", "|---|---|---|---|"]
    by_g = defaultdict(list)
    for p in closed:
        by_g[str(p.get("elite_grade") or "?")].append(p)
    for k in sorted(by_g):
        a = agg(by_g[k])
        out.append(f"| {k} | {a['n']} | {a['wr']*100:.1f}% | {a['pf']:.2f} |")

    # 4. top strategies
    out += ["", "## 4. Blueprint by strategy (n≥10)", "",
            "| strategy | n | WR | PF |", "|---|---|---|---|"]
    by_st = defaultdict(list)
    for p in closed:
        by_st[str(p.get("strategy") or p.get("source_system") or "?")].append(p)
    rows = [(k, agg(v)) for k, v in by_st.items() if len(v) >= 10]
    rows.sort(key=lambda x: -x[1]["pf"])
    for k, a in rows:
        out.append(f"| {k} | {a['n']} | {a['wr']*100:.1f}% | {a['pf']:.2f} |")

    # 5. why-picked sample
    out += ["", "## 5. Why-picked trace — sample (5 WON, 5 LOST)", ""]
    won = [p for p in closed if _is_won(p) is True][:5]
    lost = [p for p in closed if _is_won(p) is False][:5]
    for label, grp in (("WON", won), ("LOST", lost)):
        for p in grp:
            out.append(f"- **[{label}]** `{p.get('symbol')}` {p.get('direction') or p.get('signal_type')} "
                        f"· {p.get('strategy')} · conf={p.get('confidence')} "
                        f"elite={p.get('elite_score')} grade={p.get('elite_grade')} "
                        f"· pnl={p.get('pnl_pct')}")
            rsn = str(p.get("reason") or "").strip()
            if rsn:
                out.append(f"  - reason: {rsn[:200]}")
    return "\n".join(out)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()[:10]
    closed = [p for p in _load(CLOSED) if _resolved_date(p)[:10] >= cutoff]
    active = _load(ACTIVE)
    report = build_report(closed, active, args.days)
    if args.out:
        args.out.write_text(report, encoding="utf-8")
        print(f"# wrote {args.out}", file=sys.stderr)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
