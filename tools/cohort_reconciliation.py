# tools/cohort_reconciliation.py
"""Pure cohort reconciliation for /audit published JSONs (measurement only).

Reads only published files; never touches the live DB.
No trade triggers. Output contains no READY/ENTER wording.
"""
import sys
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA_VERSION = "1.1.0"
LOW_N_MIN = 20  # same low-n floor as for win rate; skip PF below this


def utcnow_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_ts(ts):
    """Parse an ISO timestamp; tolerate trailing 'Z', microseconds, and tz abbreviations."""
    if ts is None:
        raise ValueError("parse_ts(None)")
    s = str(ts).strip()
    if s.endswith("Z") or s.endswith("z"):
        s = s[:-1] + "+00:00"
    for abbrev, offset in (("EST", "-05:00"), ("EDT", "-04:00"),
                           ("CST", "-06:00"), ("CDT", "-05:00"),
                           ("MST", "-07:00"), ("MDT", "-06:00"),
                           ("PST", "-08:00"), ("PDT", "-07:00"),
                           ("UTC", "+00:00"), ("GMT", "+00:00")):
        if s.endswith(" " + abbrev):
            s = s[: -(len(abbrev) + 1)] + offset
            break
    return datetime.fromisoformat(s)


def load_json(path):
    """Load JSON. Return None if missing; raise ValueError if malformed."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"malformed JSON in {path}: {e}")


def _pf(rows):
    rows = [r for r in rows if r.get("pnl_pct") is not None]
    if not rows:
        return None
    pos = sum(r["pnl_pct"] for r in rows if r["pnl_pct"] > 0)
    neg = abs(sum(r["pnl_pct"] for r in rows if r["pnl_pct"] < 0))
    if neg == 0:
        return "inf" if pos > 0 else 0.0
    return pos / neg


def metric_block(rows):
    rows = [r for r in rows if r.get("pnl_pct") is not None]
    n = len(rows)
    wins = sum(1 for r in rows if r["pnl_pct"] > 0)
    losses = sum(1 for r in rows if r["pnl_pct"] < 0)
    hidden = n < 20
    return {
        "n": n,
        "wins": wins,
        "losses": losses,
        "win_rate": None if hidden else (wins / n if n else None),
        "win_rate_hidden": hidden,
        "pf": _pf(rows),
    }


def _coverage(records, window_hours, generated_dt):
    ats = [parse_ts(r["closed_at"]) for r in records if r.get("closed_at")]
    window_start = generated_dt - timedelta(hours=window_hours)
    if not ats:
        return {"status": "incomplete_coverage", "oldest_closed_at": None,
                "window_start_utc": window_start.isoformat(), "covers_window": False}
    oldest = min(ats)
    return {"oldest_closed_at": oldest.isoformat(),
            "window_start_utc": window_start.isoformat(),
            "covers_window": oldest <= window_start,
            "status": "complete" if oldest <= window_start else "incomplete_coverage"}


def _group_metrics(records):
    by_class = {}
    by_strategy = {}
    for r in records:
        cls = r.get("asset_class") or "UNKNOWN"
        strat = r.get("strategy") or "UNKNOWN"
        by_class.setdefault(cls, []).append(r)
        by_strategy.setdefault(strat, []).append(r)
    return ({"class": k, "metrics": metric_block(v)} for k, v in by_class.items()), \
           ({"strategy": k, "metrics": metric_block(v)} for k, v in by_strategy.items())


def _window_filter(records, window_hours, generated_dt):
    cutoff = generated_dt - timedelta(hours=window_hours)
    out = []
    for r in records:
        try:
            ts = parse_ts(r.get("closed_at"))
        except Exception:
            continue
        if ts >= cutoff:
            out.append(r)
    return out


def recompute_rolling_metrics(records, window_hours, generated_at):
    generated_dt = parse_ts(generated_at)
    cov = _coverage(records, window_hours, generated_dt)
    filtered = _window_filter(records, window_hours, generated_dt)
    by_class = {it["class"]: it["metrics"] for it in _group_metrics(filtered)[0]}
    by_strategy = {it["strategy"]: it["metrics"] for it in _group_metrics(filtered)[1]}
    return {"window_hours": window_hours, "coverage": cov,
            "by_class": by_class, "by_strategy": by_strategy}


def _block_dates_map(block_dates):
    if not block_dates:
        return {}
    return {str(k).strip().casefold(): parse_ts(v) for k, v in block_dates.items()}


def flag_blocklist_bypass(records, block_dates=None):
    from alpha_engine.strategy_blocklist import is_blocked_strategy, block_reason
    dates = _block_dates_map(block_dates)
    issues = []
    for r in records:
        strat = r.get("strategy")
        if not strat:
            continue
        ac = r.get("asset_class") or ""
        if not is_blocked_strategy(strat, ac):
            continue
        reason = block_reason(strat, ac) or "blocked"
        entry = r.get("entry_time")
        known = False
        bypass = "blocked_now_issue_time_unknown"
        if strat.strip().casefold() in dates and entry:
            try:
                entry_dt = parse_ts(entry)
                if entry_dt >= dates[strat.strip().casefold()]:
                    known, bypass = True, "blocked_at_issue_time"
                else:
                    continue  # not blocked at issue time -> no flag
            except Exception:
                pass
        issues.append({
            "pick_id": r.get("id"),
            "symbol": r.get("symbol"),
            "direction": r.get("direction"),
            "strategy": strat,
            "asset_class": ac or "UNKNOWN",
            "reason": reason,
            "issue_time_known": known,
            "bypass": bypass,
        })
    return {"flagged": bool(issues), "count": len(issues), "issues": issues}


from collections import defaultdict


def flag_batch_artefact(records, min_cluster=5):
    # group by (closed_at, strategy): each strategy gets its own cluster so a
    # single timestamp closing several strategies never collapses into one
    # random strategy
    by_key = defaultdict(list)
    for r in records:
        ts = r.get("closed_at")
        strat = r.get("strategy")
        if ts and strat:
            by_key[(ts, strat)].append(r)
    clusters = []
    for (ts, strat), rows in sorted(by_key.items(), key=lambda kv: kv[0][0]):
        if len(rows) < min_cluster:
            continue
        sources = {r.get("source_system") for r in rows}
        # base metrics for the strategy cohort (all records of that strategy)
        strat_all = [r for r in records if r.get("strategy") == strat]
        # excl metrics: drop rows that share this batch timestamp AND this strategy
        strat_excl = [r for r in strat_all
                      if not (r.get("closed_at") == ts and r.get("strategy") == strat)]
        excl_metrics = metric_block(strat_excl)
        clusters.append({
            "closed_at": ts,
            "count": len(rows),
            "strategy": strat,
            "source_system": next(iter(sources), None),
            "metrics": metric_block(strat_all),
            "metrics_excl_batch": excl_metrics,
        })
    return {"flagged": bool(clusters), "clusters": clusters}


def _pf_delta(a, b):
    if a == b:
        return 0.0
    if a == "inf":
        return 10.0  # treat infinite vs finite as large delta
    if b == "inf":
        return 10.0
    return abs((a or 0.0) - (b or 0.0))


def flag_published_disagreement(dashboard_by_window, summary_stats,
                               tol_pf=0.1, tol_n_pct=0.2,
                               stale_hours=48, dashboard_generated_at=None):
    checks = []
    for path, summary in summary_stats.items():
        if summary is None:
            checks.append({"file": path, "source": "missing"})
            continue
        wh = summary.get("window_hours")
        dash = dashboard_by_window.get(wh)
        if dash is None:
            checks.append({"file": path, "source": "no_matching_window"})
            continue
        cov_status = dash["coverage"]["status"]
        if cov_status != "complete":
            checks.append({"file": path, "cohort": f"{wh}h",
                           "coverage_status": cov_status, "disagree": False})
            continue
        # stale check (flags with age in days per user requirement)
        stale_source = False
        try:
            gen = parse_ts(summary["generated_at"])
            if dashboard_generated_at:
                dash_gen = parse_ts(dashboard_generated_at)
                if (dash_gen - gen).total_seconds() > stale_hours * 3600:
                    stale_days = round((dash_gen - gen).total_seconds() / 86400)
                    checks.append({"file": path, "source": "stale",
                                   "stale_days": stale_days,
                                   "stale_hours": round((dash_gen - gen).total_seconds() / 3600, 1)})
                    stale_source = True
        except Exception:
            pass
        if stale_source:
            # a stale summary reflects a different-time cohort; per-class
            # disagreement against the current dashboard would be spurious.
            # BUT a stale source is itself a top-level problem (dead summary
            # job) and must set flagged=True so it is never hidden.
            continue
        for cls, sm in summary.get("by_class", {}).items():
            dm = dash["by_class"].get(cls)
            if dm is None:
                continue
            summary_n = sm.get("n_closed", 0)
            dash_n = dm.get("n", 0)
            # recent_closed is a capped/filtered sample, not the full cohort.
            # When the published summary's n is more than 2x the dashboard's
            # in-window n for a class, that is an input limitation, not a
            # disagreement -> record status and skip disagree for the class.
            if summary_n > 2 * dash_n:
                checks.append({
                    "file": path, "cohort": f"{wh}h/{cls}",
                    "status": "sample_not_full_cohort",
                    "dashboard_n": dash_n, "summary_n": summary_n,
                    "disagree": False,
                })
                continue
            # Low-n rule (same as for win rate): with fewer than 20 trades on
            # either side, one losing trade can swing the profit factor wildly,
            # so skip the PF comparison. Record status, skip disagree.
            if summary_n < LOW_N_MIN or dash_n < LOW_N_MIN:
                checks.append({
                    "file": path, "cohort": f"{wh}h/{cls}",
                    "status": "low_n",
                    "dashboard_n": dash_n, "summary_n": summary_n,
                    "dashboard_pf": dm.get("pf"), "summary_pf": sm.get("pf"),
                    "disagree": False,
                })
                continue
            pf_delta = _pf_delta(dm.get("pf"), sm.get("pf"))
            n_delta_frac = abs(dash_n - summary_n) / max(dash_n, summary_n, 1)
            disagree = pf_delta > tol_pf or n_delta_frac > tol_n_pct
            checks.append({
                "file": path, "cohort": f"{wh}h/{cls}",
                "coverage_status": "complete",
                "dashboard_n": dash_n, "dashboard_pf": dm.get("pf"),
                "summary_n": summary_n, "summary_pf": sm.get("pf"),
                "disagree": disagree,
            })
    stale_flagged = any(c.get("source") == "stale" for c in checks)
    disagreement_flagged = any(c.get("disagree") for c in checks)
    return {"flagged": stale_flagged or disagreement_flagged, "checks": checks,
            "stale_sources_flagged": stale_flagged}


import argparse


def assemble_output(parts):
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": utcnow_iso(),
        "comparison_scope": "published-file-vs-published-file",
        "inputs": parts.get("inputs", {}),
        "rolling_metrics_by_window": parts.get("rolling_metrics_by_window", {}),
        "blocklist_bypass": parts.get("blocklist_bypass", {"flagged": False, "count": 0, "issues": []}),
        "batch_artefact": parts.get("batch_artefact", {"flagged": False, "clusters": []}),
        "published_disagreement": parts.get("published_disagreement",
                                           {"flagged": False, "checks": [],
                                            "stale_sources_flagged": False}),
        "notes": parts.get("notes", []),
    }


def _read_inputs(dash_path, s14_path, s48_path):
    dash = load_json(dash_path)
    s14 = load_json(s14_path)
    s48 = load_json(s48_path)
    recs = []
    if dash and dash.get("picks", {}).get("recent_closed"):
        recs = dash["picks"]["recent_closed"]
    inputs = {
        "dashboard_data": {"path": dash_path, "present": dash is not None,
                           "generated_utc": (dash or {}).get("generated_at"),
                           "records": len(recs)},
        "summary_stats_14d": {"path": s14_path, "present": s14 is not None,
                              "generated_utc": (s14 or {}).get("generated_at")},
        "summary_stats_48h": {"path": s48_path, "present": s48 is not None,
                              "generated_utc": (s48 or {}).get("generated_at")},
    }
    return dash, recs, s14, s48, inputs


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cohort_reconciliation")
    ap.add_argument("--dashboard", default="audit_dashboard/data/dashboard_data.json")
    ap.add_argument("--summary14d", default="audit_dashboard/data/pick_summary_stats_14d.json")
    ap.add_argument("--summary48h", default="audit_dashboard/data/pick_summary_stats_48h.json")
    ap.add_argument("--block-dates", default=None, help="optional JSON: strategy -> block ISO date")
    ap.add_argument("--out", default="audit_dashboard/data/cohort_reconciliation.json")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)

    dash, recs, s14, s48, inputs = _read_inputs(args.dashboard, args.summary14d, args.summary48h)
    if args.strict and dash is None:
        raise FileNotFoundError(args.dashboard)

    generated_at = dash.get("generated_at") if dash else utcnow_iso()
    w14 = recompute_rolling_metrics(recs, 336, generated_at) if dash else {}
    w48 = recompute_rolling_metrics(recs, 48, generated_at) if dash else {}
    rolling = {}
    if w14:
        rolling["14d"] = w14
    if w48:
        rolling["48h"] = w48

    block_dates = None
    if args.block_dates:
        with open(args.block_dates, encoding="utf-8") as f:
            block_dates = json.load(f)
    bypass = flag_blocklist_bypass(recs, block_dates) if dash else {"flagged": False, "count": 0, "issues": []}
    batch = flag_batch_artefact(recs) if dash else {"flagged": False, "clusters": []}

    summary_map = {"14d": s14, "48h": s48}
    dash_by_window = {336: w14, 48: w48}
    disagreement = flag_published_disagreement(dash_by_window, summary_map,
                                              dashboard_generated_at=generated_at) if dash else {"flagged": False, "checks": [], "stale_sources_flagged": False}

    notes = ["comparison_scope=published-file-vs-published-file; no live DB read performed"]
    if s14 and s14.get("generated_at"):
        notes.append(f"summary_stats_14d generated_at={s14.get('generated_at')}")
    if s48 and s48.get("generated_at"):
        notes.append(f"summary_stats_48h generated_at={s48.get('generated_at')}")

    out = assemble_output({"inputs": inputs, "rolling_metrics_by_window": rolling,
                           "blocklist_bypass": bypass, "batch_artefact": batch,
                           "published_disagreement": disagreement, "notes": notes})
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
