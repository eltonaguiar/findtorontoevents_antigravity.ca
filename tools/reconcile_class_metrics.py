#!/usr/bin/env python3
"""
Reconcile per-class metrics across /audit, /audit2 and /audit3.

Two independent jobs, no judgement:

  B2  INTERNAL CONSISTENCY of the frozen /audit3 ledger (pure arithmetic, no DB).
      Re-derives each published class figure from the other published fields and
      reports any invariant that does not hold. A mismatch is a FINDING, never
      something to edit away.

  B3  GROSS -> NET BRIDGE from the live `trading_picks` table.
      Computes gross PF (no cost), then net PF under the ledger's own
      `slippage_pct_by_class`, then net PF under /audit's `SLIPPAGE_BPS`, and
      reports the residual against the ledger's published net PF.

Population is matched to the scrutiny engine
(tools/per_class_scrutiny_engine.py:78-81) on purpose:
    closed_at IS NOT NULL AND pnl_pct IS NOT NULL
    AND status NOT IN ('OPEN','ABANDONED','FLAT','FORCE_CLOSED_TOXIC')
    AND closed_at > '2026-01-01'
    AND DATE(closed_at) != '2026-06-04'      # 5,960-row resolver backfill

That population is NOT the ledger's population (the ledger scores 8,827 of
14,914 closed picks via dashboard_data.resolved_closed_picks_net). The residual
column is therefore expected to be non-zero, and the point of the bridge is to
say HOW MUCH of it is cost versus cohort.

Usage:
    python3 tools/reconcile_class_metrics.py                    # ledger only (no DB)
    python3 tools/reconcile_class_metrics.py --db               # ledger + bridge
    python3 tools/reconcile_class_metrics.py --db --json-only
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Running as `python3 tools/reconcile_class_metrics.py` puts tools/ (not the repo
# root) on sys.path, so `from tools.db_env import ...` would fail. Insert ROOT.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_LEDGER = ROOT / "docs" / "audit_review_2026-11-22" / "_raw" / "audit3_audit3_ledger.json"
OUT_DIR = ROOT / "reports"

# /audit's own cost constants, from alpha_engine/money_ready_verdict.py SLIPPAGE_BPS
# (basis points). Read here as a literal so the script does not import the
# MySQL-heavy verdict module. Keep in sync if that dict changes.
AUDIT_SLIPPAGE_BPS = {
    "CRYPTO": 15.0, "EQUITY": 10.0, "COMMODITY": 12.0, "ETF": 8.0,
    "FOREX": 5.0, "BOND": 8.0, "MUTUAL_FUND": 8.0, "FUTURES": 10.0,
}
AUDIT_DEFAULT_BPS = 10.0

# trading_picks.category -> canonical class. Only unambiguous mappings.
CATEGORY_TO_CLASS = {
    "crypto": "CRYPTO", "equity": "EQUITY", "commodity": "COMMODITY",
    "etf": "ETF", "forex": "FOREX", "bond": "BOND", "futures": "FUTURES",
    "meme": "MEME", "memecoin": "MEME", "penny_stock": "PENNY_STOCK",
    "mutual_fund": "MUTUAL_FUND", "index": "INDEX",
}


# ── helpers ──────────────────────────────────────────────────────────────────

def _f(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _pf(gw: float, gl: float):
    return round(gw / gl, 4) if gl and gl > 0 else None


# ── B2: internal consistency of the frozen ledger ────────────────────────────

def check_ledger(ledger: dict) -> tuple[list[dict], list[dict]]:
    """Return (per-class rows, findings). Pure arithmetic over published fields."""
    rows: list[dict] = []
    findings: list[dict] = []

    def add(sev, cls, check, detail):
        findings.append({"severity": sev, "class": cls, "check": check, "detail": detail})

    for c in ledger.get("classes", []) or []:
        cls = c.get("asset_class") or "?"
        n = _f(c.get("n"))
        wins = _f(c.get("wins"))
        wr = _f(c.get("wr"))
        pf = _f(c.get("pf"))
        cost = _f(c.get("mean_cost_pct"))
        pf_cost = _f(c.get("pf_cost_pct"))
        gross_e = _f(c.get("gross_expectancy_pct"))
        net_e = _f(c.get("net_expectancy_pct"))
        ci = c.get("net_ci_pct") or [None, None]
        ci2 = c.get("net_ci_pct_2x") or [None, None]
        alpha_n = _f(c.get("alpha_n"))
        alpha = _f(c.get("alpha_pct"))

        row = {"class": cls, "n": n, "wr": wr, "pf": pf, "mean_cost_pct": cost,
               "gross_expectancy_pct": gross_e, "net_expectancy_pct": net_e,
               "alpha_pct": alpha, "alpha_n": alpha_n, "verdict": c.get("verdict")}
        rows.append(row)

        # 1. wr must equal wins/n
        if n and wins is not None and wr is not None:
            want = wins / n
            if abs(want - wr) > 0.002:
                add("HIGH", cls, "wr == wins/n", f"published wr {wr} vs wins/n {round(want,4)}")

        # 2. wr must sit inside its own CI
        wci = c.get("wr_ci") or []
        if wr is not None and len(wci) == 2 and all(_f(x) is not None for x in wci):
            if not (_f(wci[0]) <= wr <= _f(wci[1])):
                add("HIGH", cls, "wr within wr_ci", f"wr {wr} outside [{wci[0]}, {wci[1]}]")

        # 3. net expectancy must equal gross minus cost
        if gross_e is not None and net_e is not None and cost is not None:
            diff = abs((gross_e - cost) - net_e)
            if diff > 0.01:
                add("HIGH", cls, "net_exp == gross_exp - cost",
                    f"gross {gross_e} - cost {cost} = {round(gross_e-cost,4)} vs net {net_e}")

        # 4. the two cost fields must agree
        if cost is not None and pf_cost is not None and abs(cost - pf_cost) > 0.001:
            add("MED", cls, "mean_cost_pct == pf_cost_pct", f"{cost} vs {pf_cost}")

        # 5. net expectancy must sit inside net_ci
        if net_e is not None and len(ci) == 2 and all(_f(x) is not None for x in ci):
            if not (_f(ci[0]) <= net_e <= _f(ci[1])):
                add("HIGH", cls, "net_exp within net_ci", f"net {net_e} outside [{ci[0]}, {ci[1]}]")

        # 6. 2x-cost CI must be at least as wide and shifted down
        if len(ci) == 2 and len(ci2) == 2 and all(_f(x) is not None for x in [*ci, *ci2]):
            lo, hi, lo2, hi2 = _f(ci[0]), _f(ci[1]), _f(ci2[0]), _f(ci2[1])
            if not (lo2 <= lo + 1e-9 and hi2 <= hi + 1e-9):
                add("MED", cls, "2x CI shifted down", f"1x [{lo},{hi}] 2x [{lo2},{hi2}]")

        # 7. PF must be arithmetically compatible with gross expectancy:
        #    pf = gw/gl and gross_exp*n = gw-gl  =>  gl = gross_exp*n/(pf-1) must be > 0
        if pf is not None and gross_e is not None and n:
            if abs(pf - 1.0) > 1e-6:
                gl = gross_e * n / (pf - 1.0)
                if gl <= 0:
                    add("HIGH", cls, "pf consistent with gross expectancy",
                        f"implied gross losses {round(gl,2)} <= 0 (pf {pf}, gross_exp {gross_e}, n {n})")
            else:
                add("MED", cls, "pf consistent with gross expectancy", "pf == 1 with non-zero expectancy")

        # 8. selection alpha coverage: alpha_n vs n
        if alpha_n is not None and n:
            cov = alpha_n / n
            if cov < 0.9:
                add("HIGH", cls, "alpha covers the class sample",
                    f"alpha_n {int(alpha_n)} of n {int(n)} = {round(cov*100,1)}% "
                    f"(alpha {alpha}) is measured on a subset, not the class")

        # 9. alpha must equal pick_net - hold_net
        hold = _f(c.get("hold_net_pct"))
        if alpha is not None and hold is not None and net_e is not None and alpha_n and n and abs(alpha_n - n) < 1:
            if abs((net_e - hold) - alpha) > 0.01:
                add("MED", cls, "alpha == pick_net - hold_net",
                    f"{net_e} - {hold} = {round(net_e-hold,4)} vs alpha {alpha}")

        # 10. DSR must not be >0 when the gate says unproven
        ag = c.get("alpha_gate") or {}
        if ag.get("status") == "unproven" and ag.get("passed"):
            add("HIGH", cls, "alpha_gate unproven => not passed", f"{ag}")

    # 11. class totals vs summary n_rows
    summ = ledger.get("summary") or {}
    n_rows = _f(summ.get("n_rows"))
    tot = sum(_f(r["n"], 0) or 0 for r in rows)
    if n_rows and tot and abs(tot - n_rows) > 1:
        add("HIGH", "-", "sum(classes.n) == summary.n_rows",
            f"classes sum {int(tot)} vs summary n_rows {int(n_rows)}")

    # 12. verdict counters vs the actual class verdicts
    for key, field in (("n_kill_classes", "KILL"), ("n_proven_classes", "PROVEN_T2")):
        want = _f(summ.get(key))
        got = sum(1 for r in rows if r["verdict"] == field)
        if want is not None and int(want) != got:
            add("MED", "-", f"summary.{key} matches class verdicts",
                f"summary says {int(want)}, classes[] has {got} {field}")

    return rows, findings


# ── B3: gross -> net bridge from the live DB ─────────────────────────────────

def bridge(ledger: dict) -> tuple[list[dict], list[dict]]:
    """Per-class gross/net PF from trading_picks, using each surface's own costs."""
    findings: list[dict] = []
    rows: list[dict] = []
    try:
        import pymysql
        from tools.db_env import get_stocks_creds
    except Exception as e:  # pragma: no cover - environment dependent
        return rows, [{"severity": "BLOCKED", "class": "-", "check": "db",
                       "detail": f"{type(e).__name__}: {e}"}]

    slip = (ledger.get("conventions") or {}).get("slippage_pct_by_class") or {}
    led = {c.get("asset_class"): c for c in (ledger.get("classes") or [])}
    creds = get_stocks_creds()
    creds["connect_timeout"] = 10
    creds["read_timeout"] = 60

    base_where = (
        "closed_at IS NOT NULL AND pnl_pct IS NOT NULL "
        "AND status NOT IN ('OPEN','ABANDONED','FLAT','FORCE_CLOSED_TOXIC') "
        "AND closed_at > '2026-01-01' AND DATE(closed_at) != '2026-06-04'"
    )
    sql = f"""
        SELECT COUNT(*) n,
               SUM(IF(pnl_pct>0,1,0)) wins,
               SUM(IF(pnl_pct>0,pnl_pct,0)) gw,
               ABS(SUM(IF(pnl_pct<0,pnl_pct,0))) gl,
               SUM(IF(pnl_pct-%s>0,pnl_pct-%s,0)) ngw,
               ABS(SUM(IF(pnl_pct-%s<0,pnl_pct-%s,0))) ngl
        FROM trading_picks
        WHERE {base_where} AND LOWER(TRIM(category))=%s
    """

    try:
        conn = pymysql.connect(**creds)
    except Exception as e:  # pragma: no cover
        return rows, [{"severity": "BLOCKED", "class": "-", "check": "db connect",
                       "detail": f"{type(e).__name__}: {str(e)[:200]}"}]

    try:
        cur = conn.cursor()
        cur.execute(f"SELECT LOWER(TRIM(category)) c, COUNT(*) n FROM trading_picks "
                    f"WHERE {base_where} GROUP BY c ORDER BY n DESC")
        cats = [(r[0], int(r[1])) for r in cur.fetchall()]
        for cat in cats:
            raw_cat, cat_n = cat
            cls = CATEGORY_TO_CLASS.get(raw_cat or "", (raw_cat or "").upper() or "UNCATEGORIZED")
            cost = slip.get(cls)
            if cls == "MEME":
                cost = slip.get("MEME")
            audit_cost = AUDIT_SLIPPAGE_BPS.get(cls)
            audit_cost = (audit_cost / 100.0) if audit_cost is not None else AUDIT_DEFAULT_BPS / 100.0
            if cost is None:
                cur.execute(sql, (0, 0, 0, 0, raw_cat))
                r = cur.fetchone()
                rows.append({"class": cls, "category": raw_cat, "db_n": int(r[0]), "cost": None,
                             "gross_pf": _pf(_f(r[2], 0), _f(r[3], 0)), "net_pf": None,
                             "audit_net_pf": None, "ledger_net_pf": (led.get(cls) or {}).get("pf"),
                             "note": "UNMEASURED: class absent from slippage_pct_by_class"})
                continue
            cur.execute(sql, (cost, cost, cost, cost, raw_cat))
            r = cur.fetchone()
            n = int(r[0] or 0)
            if n == 0:
                continue
            gross_pf = _pf(_f(r[2], 0), _f(r[3], 0))
            net_pf = _pf(_f(r[4], 0), _f(r[5], 0))
            # /audit cost applied to the same rows
            cur.execute(sql, (audit_cost, audit_cost, audit_cost, audit_cost, raw_cat))
            ra = cur.fetchone()
            audit_net_pf = _pf(_f(ra[4], 0), _f(ra[5], 0))
            lrow = led.get(cls) or {}
            rows.append({
                "class": cls, "category": raw_cat, "db_n": n,
                "cost": cost, "audit_cost": audit_cost,
                "wr": round(int(r[1] or 0) / n, 4),
                "gross_pf": gross_pf, "net_pf": net_pf, "audit_net_pf": audit_net_pf,
                "ledger_n": lrow.get("n"), "ledger_net_pf": lrow.get("pf"),
                "residual_net_vs_ledger": (round(net_pf - _f(lrow.get("pf")), 4)
                                           if net_pf and _f(lrow.get("pf")) is not None else None),
                "note": "",
            })
        conn.close()
    except Exception as e:  # pragma: no cover
        try:
            conn.close()
        except Exception:
            pass
        findings.append({"severity": "BLOCKED", "class": "-", "check": "db query",
                         "detail": f"{type(e).__name__}: {str(e)[:200]}"})
    return rows, findings


# ── output ──────────────────────────────────────────────────────────────────

def render_md(rows, findings, bridge_rows, bridge_findings, ledger_path, stamp) -> str:
    L = []
    L.append(f"# Per-class metric reconciliation — {stamp}")
    L.append("")
    L.append(f"Ledger: `{ledger_path.relative_to(ROOT) if str(ledger_path).startswith(str(ROOT)) else ledger_path}`")
    L.append("")
    L.append("No number here is edited from a source. A mismatch is reported, not patched.")
    L.append("")
    L.append("## 1 Ledger internal consistency (B2)")
    L.append("")
    L.append("| class | n | WR | net PF | alpha | alpha_n | verdict |")
    L.append("|---|---|---|---|---|---|---|")
    for r in rows:
        L.append(f"| {r['class']} | {r['n']} | {r['wr']} | {r['pf']} | {r['alpha_pct']} | "
                 f"{r['alpha_n']} | {r['verdict']} |")
    L.append("")
    if findings:
        L.append(f"### Findings ({len(findings)})")
        L.append("")
        L.append("| sev | class | check | detail |")
        L.append("|---|---|---|---|")
        for f_ in findings:
            L.append(f"| {f_['severity']} | {f_['class']} | {f_['check']} | {f_['detail']} |")
    else:
        L.append("No invariant violations found.")
    L.append("")
    L.append("## 2 Gross to net bridge (B3)")
    L.append("")
    if not bridge_rows:
        L.append("Not run (no `--db`), or the database was unreachable.")
    else:
        L.append("`gross_pf` has no cost. `net_pf` uses the ledger's `slippage_pct_by_class`. "
                 "`audit_net_pf` uses /audit's `SLIPPAGE_BPS` on the same rows. "
                 "`ledger_net_pf` is what /audit3 publishes.")
        L.append("")
        L.append("| class | db n | WR | gross PF | net PF (audit3 cost) | net PF (audit cost) | ledger n | ledger net PF | residual |")
        L.append("|---|---|---|---|---|---|---|---|---|")
        for r in bridge_rows:
            L.append(f"| {r['class']} | {r['db_n']} | {r.get('wr','-')} | {r['gross_pf']} | "
                     f"{r['net_pf']} | {r['audit_net_pf']} | {r.get('ledger_n','-')} | "
                     f"{r.get('ledger_net_pf','-')} | {r.get('residual_net_vs_ledger','-')} |")
        L.append("")
        L.append("Cohort caveat: the DB population here matches the scrutiny engine, not the "
                 "ledger. The ledger scores a different cohort (dashboard_data.resolved_closed_picks_net), "
                 "so a non-zero residual is expected and is the measure of cohort difference, not of error.")
    if bridge_findings:
        L.append("### Bridge findings")
        L.append("")
        for f_ in bridge_findings:
            L.append(f"- **{f_['severity']}** {f_['check']}: {f_['detail']}")
    L.append("")
    L.append("## Provenance")
    L.append("")
    L.append("- cost constants: ledger `conventions.slippage_pct_by_class`; /audit `SLIPPAGE_BPS` in `alpha_engine/money_ready_verdict.py`")
    L.append("- DB population filter: `tools/per_class_scrutiny_engine.py:74-81`")
    L.append(f"- generated: {datetime.now(timezone.utc).isoformat()}")
    L.append("")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    ap.add_argument("--db", action="store_true", help="also run the gross->net bridge against MySQL")
    ap.add_argument("--json-only", action="store_true")
    args = ap.parse_args(argv)

    ledger_path = Path(args.ledger)
    if not ledger_path.exists():
        print(f"ERROR: ledger not found: {ledger_path}", file=sys.stderr)
        return 2
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

    rows, findings = check_ledger(ledger)
    bridge_rows, bridge_findings = ([], [])
    if args.db:
        bridge_rows, bridge_findings = bridge(ledger)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(),
               "ledger": str(ledger_path),
               "ledger_classes": rows, "ledger_findings": findings,
               "bridge": bridge_rows, "bridge_findings": bridge_findings}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jpath = OUT_DIR / f"class_metric_reconciliation_{stamp}.json"
    jpath.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    if not args.json_only:
        md = render_md(rows, findings, bridge_rows, bridge_findings, ledger_path, stamp)
        mpath = OUT_DIR / f"class_metric_reconciliation_{stamp}.md"
        mpath.write_text(md, encoding="utf-8")
        print(md)
        print(f"[written] {mpath}", file=sys.stderr)
    print(f"[written] {jpath}", file=sys.stderr)

    high = sum(1 for f_ in findings if f_["severity"] == "HIGH")
    return 0 if high == 0 else 0  # never fail the caller; findings are the output


if __name__ == "__main__":
    raise SystemExit(main())
