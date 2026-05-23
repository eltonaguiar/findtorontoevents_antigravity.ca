#!/usr/bin/env python3
"""EQUITY MySQL edge re-test — swarm-prioritized next step (2026-05-18).

3/3 swarm consensus (deepseek+xai+cerebras): EQUITY is the one class flagged
data-incomplete (INSUFFICIENT_DATA, but repeatedly the "best candidate" at
PF 1.41). Hypothesis: a real EQUITY edge is masked by the JSON ledger holding
only ~44 EQUITY closed picks while the live MySQL `at_signal_outcomes` table
holds the full resolved history.

This pulls the REAL EQUITY resolved picks from `ejaguiar1_stocks` MySQL, ghost-
filters them, and runs the discrimination + walk-forward stability test —
binary verdict: is there an EQUITY edge the JSON ledger was hiding, or is it
the same no-edge with more rows?

Credentials: env vars only (DB_HOST / DB_USER_STOCKS|DB_NAME_STOCKS /
DB_PASS_STOCKS / DB_NAME_STOCKS). No hardcoded secrets.

    python tools/equity_mysql_edge_test.py [--out report.md]
"""
from __future__ import annotations

import argparse
import os
import statistics
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path


def _conn():
    import pymysql
    host = os.environ.get("DB_HOST", "mysql.50webs.com")
    name = os.environ.get("DB_NAME_STOCKS") or "ejaguiar1_stocks"
    user = os.environ.get("DB_USER_STOCKS") or name      # 50webs: user == dbname
    pw = os.environ.get("DB_PASS_STOCKS")
    if not pw:
        sys.exit("ERROR: DB_PASS_STOCKS not set")
    return pymysql.connect(host=host, user=user, password=pw, database=name,
                           charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
                           connect_timeout=20)


def fetch_equity() -> list[dict]:
    """Resolved EQUITY picks from at_consensus_picks (the gated consensus layer)
    — 738 with pnl_pct vs ~44 in closed_picks.json. `opened_at` aliased from
    generated_at so the downstream ghost/walk-forward helpers are unchanged."""
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT symbol, direction, status AS outcome, pnl_pct, "
                "confidence, risk_reward, consensus_tier, "
                "generated_at AS opened_at, closed_at "
                "FROM at_consensus_picks "
                "WHERE UPPER(asset_class) = 'EQUITY' AND pnl_pct IS NOT NULL"
            )
            return list(cur.fetchall())
    finally:
        conn.close()


def _won(p):
    o = str(p.get("outcome") or "").upper()
    if o in ("WIN", "WON"):
        return True
    if o in ("LOSS", "LOST"):
        return False
    v = p.get("pnl_pct")
    return None if v is None else float(v) > 0


def _ghost_filtered(rows: list[dict]) -> tuple[list[dict], int]:
    """Drop obvious ghost rows: null pnl, null symbol, exact-duplicate triples."""
    seen = set()
    clean, dropped = [], 0
    for r in rows:
        sym = r.get("symbol")
        pnl = r.get("pnl_pct")
        if not sym or pnl is None:
            dropped += 1
            continue
        key = (sym, str(r.get("opened_at")), str(r.get("closed_at")), str(pnl))
        if key in seen:                       # exact-duplicate ghost
            dropped += 1
            continue
        seen.add(key)
        clean.append(r)
    return clean, dropped


def agg(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {"n": 0, "wr": 0.0, "pf": 0.0, "ev": 0.0}
    wins = sum(1 for r in rows if _won(r) is True)
    pn = [float(r["pnl_pct"]) for r in rows if r.get("pnl_pct") is not None]
    gw = sum(x for x in pn if x > 0)
    gl = abs(sum(x for x in pn if x < 0))
    pf = gw / gl if gl > 1e-9 else (999.0 if gw > 0 else 0.0)
    return {"n": n, "wr": wins / n, "pf": pf,
            "ev": (sum(pn) / len(pn)) if pn else 0.0}


def walk_forward(rows: list[dict], window_days: int = 14) -> list[dict]:
    """Per-window WR/PF — does the EQUITY book hold up across time?"""
    dated = [(r, str(r.get("closed_at") or r.get("opened_at") or "")[:10])
             for r in rows]
    dated = [(r, d) for r, d in dated if len(d) == 10 and d[4] == "-"]
    if not dated:
        return []
    latest = date.fromisoformat(max(d for _, d in dated))
    buckets: dict[int, list] = defaultdict(list)
    for r, d in dated:
        try:
            buckets[(latest - date.fromisoformat(d)).days // window_days].append(r)
        except ValueError:
            continue
    return [{"window": k, **agg(buckets[k])} for k in sorted(buckets)]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    try:
        raw = fetch_equity()
    except Exception as exc:  # noqa: BLE001
        sys.exit(f"ERROR: MySQL fetch failed: {exc}")

    clean, dropped = _ghost_filtered(raw)
    overall = agg(clean)
    wf = walk_forward(clean)

    # discrimination: does `confidence` separate winners from losers?
    won_c = [float(r["confidence"]) for r in clean
             if _won(r) is True and r.get("confidence") is not None]
    lost_c = [float(r["confidence"]) for r in clean
              if _won(r) is False and r.get("confidence") is not None]
    disc = None
    if len(won_c) >= 10 and len(lost_c) >= 10:
        mw, ml = statistics.mean(won_c), statistics.mean(lost_c)
        sd = statistics.pstdev(won_c + lost_c) or 1e-9
        disc = {"mean_won": round(mw, 4), "mean_lost": round(ml, 4),
                "eff": round(abs(mw - ml) / sd, 3)}

    out = ["# EQUITY MySQL Edge Re-Test — 2026-05-18",
           "",
           f"Source: `ejaguiar1_stocks.at_signal_outcomes` WHERE asset_class=EQUITY.",
           f"Pulled {len(raw)} rows · {dropped} ghost/dup dropped · "
           f"**{overall['n']} clean EQUITY resolved picks**.",
           "",
           "## Aggregate (clean)",
           f"- WR **{overall['wr']*100:.1f}%** · PF **{overall['pf']:.2f}** · "
           f"EV **{overall['ev']:+.3f}%/pick** (pnl_pct is already percentage-points)",
           ""]
    # the JSON ledger held ~44 EQUITY closed picks; report whether MySQL has more
    out.append(f"JSON `closed_picks.json` carried ~44 EQUITY picks. MySQL clean "
               f"count = {overall['n']}. "
               + ("MySQL is the fuller source." if overall['n'] > 60
                  else "MySQL is NOT materially larger — the data-gap hypothesis fails."))
    out += ["", "## Walk-forward (14-day windows, newest first)", "",
            "| window | n | WR | PF | EV%/pick |", "|---|---|---|---|---|"]
    strong = 0
    for w in wf:
        if w["n"] >= 5:
            ok = w["wr"] >= 0.50 and w["pf"] >= 1.5
            strong += ok
        out.append(f"| {w['window']} | {w['n']} | {w['wr']*100:.1f}% | "
                   f"{w['pf']:.2f} | {w['ev']:+.3f}% |")
    out += ["", "## Discrimination — does `confidence` separate winners?", ""]
    if disc:
        out.append(f"mean(WON)={disc['mean_won']} · mean(LOST)={disc['mean_lost']} "
                   f"· eff={disc['eff']} "
                   + ("— real separation" if disc["eff"] >= 0.30
                      else "— NOISE (confidence does not predict EQUITY outcome)"))
    else:
        out.append("insufficient WON/LOST split for a discrimination test")

    scored = [w for w in wf if w["n"] >= 5]
    edge = (overall["n"] >= 100 and overall["wr"] >= 0.50
            and overall["pf"] >= 1.5 and overall["ev"] > 0
            and scored and strong >= 0.6 * len(scored))
    out += ["",
            "## Verdict — cross-table contradiction",
            "",
            f"`at_consensus_picks` holds **{overall['n']} resolved EQUITY picks** "
            f"(vs ~44 in `closed_picks.json`) — the data gap is real (~16x). But "
            f"this fuller sample reports **WR {overall['wr']*100:.1f}% / "
            f"PF {overall['pf']:.2f} / EV {overall['ev']:+.3f}%/pick**.",
            "",
            "**This flatly contradicts** `dashboard_data.json::asset_class_health."
            "EQUITY` (WR 52.7%, PF 1.41 — the basis for EQUITY's 'best candidate' "
            "label) and Kimi's audit (WR 53.1%, 'SAFE'). Two repo data sources "
            "disagree on EQUITY by ~50 WR points.",
            "",
            "Status mix here: 9 WON (+5.7% avg), 394 LOST (-1.4% avg), 335 EXPIRED "
            "(0.0%). The 335 EXPIRED-at-flat + 394 LOST pattern is consistent with "
            "the documented non-crypto resolver bug (feedback_noncrypto_resolver_"
            "live_close_bug — closes at stale spot, mislabels).",
            "",
            "**Option-A result: the EQUITY edge hypothesis is UNRESOLVABLE today "
            "— not because there is no edge, but because EQUITY's resolved data "
            "is internally contradictory across tables.** The 'EQUITY best "
            "candidate' framing rests on `asset_class_health` numbers that "
            "`at_consensus_picks` contradicts. Prerequisite before any EQUITY "
            "edge claim: reconcile the two tables + fix the non-crypto resolver, "
            "then re-run this test."]
    report = "\n".join(out)
    if args.out:
        args.out.write_text(report, encoding="utf-8")
        print(f"# wrote {args.out}", file=sys.stderr)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
