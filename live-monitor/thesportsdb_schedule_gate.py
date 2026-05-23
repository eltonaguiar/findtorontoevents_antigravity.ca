#!/usr/bin/env python3
"""
TheSportsDB Schedule-Coverage Gate
==================================
No-key sanity check: cross-references our pipeline events (sports_picks.php?
action=today) against TheSportsDB free schedule API. This is a SCHEDULE GATE,
not a row-injector — the script never POSTs to sports_odds.php.

For each configured sport it pulls TheSportsDB's `eventsnextleague.php?id=<id>`
and the live pipeline `value_bets[]`, then matches on
(home_team, away_team, commence_time +- 1h tolerance). It emits a JSON report
to data/sports_schedule_gate_<UTC>.json with:
  matched / pipeline_only / sportsdb_only counts per sport
and prints a stdout summary table. Exit code is 0 when every probed sport
shows >=70% match coverage, else 1 (so the workflow step can either
continue-on-error or fail loudly per its policy).

API:
  Base   https://www.thesportsdb.com/api/v1/json/123/
  Key    123 (free, public, baked into URL — NO secret needed)
  Quota  Cloudflare 429 rate-limit at ~30 req/min; we sleep 1.5s between calls.

League IDs (verified via lookupleague.php on 2026-05-03):
  NBA   4387   NHL   4380   NFL   4391   MLB   4424
  MLS   4346   EPL   4328   NCAAB 4607   NCAAF 4479   UFC   4443

Usage:
    python live-monitor/thesportsdb_schedule_gate.py --dry-run
    python live-monitor/thesportsdb_schedule_gate.py --sports nba,nhl
    python live-monitor/thesportsdb_schedule_gate.py --report-only --output gate.json

Stdlib-only — no pip install required on GitHub runners.
"""

import argparse
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TSDB_BASE = "https://www.thesportsdb.com/api/v1/json/123"
PIPELINE_URL = "https://findtorontoevents.ca/live-monitor/api/sports_picks.php?action=today"
HTTP_TIMEOUT = 20
USER_AGENT = "FindTorontoEvents-ScheduleGate/1.0"
TSDB_INTER_REQUEST_SLEEP = 1.5
MATCH_TOLERANCE_SECONDS = 3600
COVERAGE_FLOOR = 0.70

# Sport short -> TheSportsDB league id. IDs verified 2026-05-03 via lookupleague.php.
SPORT_LEAGUE_IDS = {
    "nba":   4387,
    "nhl":   4380,
    "nfl":   4391,
    "mlb":   4424,
    "mls":   4346,
    "epl":   4328,
    "ncaab": 4607,
    "ncaaf": 4479,
    "ufc":   4443,
}

# Pipeline `sport_short` field uses uppercase. Map both ways for matching.
PIPELINE_SPORT_SHORT = {k: k.upper() for k in SPORT_LEAGUE_IDS}


def _http_get_json(url, retries=2):
    last_err = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url)
        req.add_header("User-Agent", USER_AGENT)
        req.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                body = resp.read().decode()
                if not body or not body.lstrip().startswith(("{", "[")):
                    last_err = f"non-json body: {body[:80]!r}"
                    time.sleep(2.0 * (attempt + 1))
                    continue
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            last_err = f"HTTP {exc.code}"
            if exc.code == 429:
                time.sleep(3.0 * (attempt + 1))
                continue
            break
        except Exception as exc:
            last_err = str(exc)
            time.sleep(1.5 * (attempt + 1))
    print(f"  fetch fail {url[:90]}... :: {last_err}", file=sys.stderr)
    return None


def _norm_team(name):
    if not name:
        return ""
    n = re.sub(r"[^a-z0-9]+", "", str(name).lower())
    # Common alias trims so "Los Angeles Lakers" matches "LA Lakers".
    for prefix in ("losangeles", "newyork", "neworleans", "sanantonio",
                   "sanfrancisco", "sandiego", "saintlouis", "stlouis"):
        if n.startswith(prefix):
            n = n[len(prefix):]
            break
    return n


def _parse_dt_to_utc(value):
    if not value:
        return None
    s = str(value).strip().replace("Z", "+00:00")
    # Pipeline emits "YYYY-MM-DD HH:MM:SS" (assume UTC); TSDB strTimestamp is ISO.
    candidates = [s, s.replace(" ", "T"), s.replace(" ", "T") + "+00:00"]
    for cand in candidates:
        try:
            dt = datetime.datetime.fromisoformat(cand)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt.astimezone(datetime.timezone.utc)
        except ValueError:
            continue
    return None


def fetch_tsdb_schedule(sport_short):
    league_id = SPORT_LEAGUE_IDS.get(sport_short)
    if not league_id:
        return []
    url = f"{TSDB_BASE}/eventsnextleague.php?id={league_id}"
    payload = _http_get_json(url)
    if not isinstance(payload, dict):
        return []
    events = payload.get("events") or []
    out = []
    for ev in events:
        ts = ev.get("strTimestamp") or ev.get("strTimestampUtc")
        if not ts and ev.get("dateEvent"):
            t = (ev.get("strTime") or "00:00:00").split("+")[0]
            ts = f"{ev['dateEvent']}T{t}"
        out.append({
            "event_id": str(ev.get("idEvent") or ""),
            "home_team": ev.get("strHomeTeam") or "",
            "away_team": ev.get("strAwayTeam") or "",
            "commence_time": ts or "",
            "commence_dt": _parse_dt_to_utc(ts),
        })
    return out


def fetch_pipeline_events(sport_short):
    payload = _http_get_json(PIPELINE_URL)
    if not isinstance(payload, dict):
        return []
    target = PIPELINE_SPORT_SHORT.get(sport_short, sport_short.upper())
    seen = {}
    for vb in (payload.get("value_bets") or []):
        if (vb.get("sport_short") or "").upper() != target:
            continue
        key = (vb.get("home_team", ""), vb.get("away_team", ""), vb.get("commence_time", ""))
        if key in seen:
            continue
        seen[key] = {
            "event_id": str(vb.get("event_id") or ""),
            "home_team": vb.get("home_team") or "",
            "away_team": vb.get("away_team") or "",
            "commence_time": vb.get("commence_time") or "",
            "commence_dt": _parse_dt_to_utc(vb.get("commence_time")),
        }
    return list(seen.values())


def diff_schedules(pipeline_evs, tsdb_evs):
    matched, pipeline_only = [], []
    tsdb_consumed = set()
    for pe in pipeline_evs:
        ph, pa, pdt = _norm_team(pe["home_team"]), _norm_team(pe["away_team"]), pe["commence_dt"]
        hit = None
        for idx, te in enumerate(tsdb_evs):
            if idx in tsdb_consumed:
                continue
            th, ta = _norm_team(te["home_team"]), _norm_team(te["away_team"])
            teams_match = (ph and pa and ((ph == th and pa == ta) or (ph == ta and pa == th)))
            if not teams_match:
                continue
            if pdt and te["commence_dt"]:
                if abs((pdt - te["commence_dt"]).total_seconds()) > MATCH_TOLERANCE_SECONDS:
                    continue
            hit = idx
            break
        if hit is None:
            pipeline_only.append(pe)
        else:
            tsdb_consumed.add(hit)
            matched.append({"pipeline": pe, "tsdb": tsdb_evs[hit]})
    sportsdb_only = [te for i, te in enumerate(tsdb_evs) if i not in tsdb_consumed]
    return matched, pipeline_only, sportsdb_only


def _strip_dt(rec):
    """drop non-serializable datetime field for JSON output."""
    return {k: v for k, v in rec.items() if k != "commence_dt"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sports", default=",".join(SPORT_LEAGUE_IDS.keys()))
    ap.add_argument("--dry-run", action="store_true",
                    help="Do not write report file (still prints summary).")
    ap.add_argument("--report-only", action="store_true",
                    help="Always exit 0 regardless of coverage; report drift only.")
    ap.add_argument("--output", default="",
                    help="Override report path. Default: data/sports_schedule_gate_<UTC>.json")
    args = ap.parse_args(argv)

    targets = [s.strip().lower() for s in args.sports.split(",") if s.strip()]
    started = datetime.datetime.now(datetime.timezone.utc)
    started_iso = started.isoformat().replace("+00:00", "Z")

    summary = {
        "ok": True,
        "started_at": started_iso,
        "tolerance_seconds": MATCH_TOLERANCE_SECONDS,
        "coverage_floor": COVERAGE_FLOOR,
        "league_ids": {s: SPORT_LEAGUE_IDS.get(s) for s in targets},
        "sports": {},
        "totals": {"matched": 0, "pipeline_only": 0, "sportsdb_only": 0},
        "below_floor": [],
    }

    for short in targets:
        if short not in SPORT_LEAGUE_IDS:
            summary["sports"][short] = {"error": f"unknown sport: {short}"}
            continue
        pipeline_evs = fetch_pipeline_events(short)
        tsdb_evs = fetch_tsdb_schedule(short)
        time.sleep(TSDB_INTER_REQUEST_SLEEP)
        matched, pipe_only, sdb_only = diff_schedules(pipeline_evs, tsdb_evs)
        denom = max(len(pipeline_evs), 1)
        cov = len(matched) / denom if pipeline_evs else 1.0
        # Skip floor check when TSDB returned zero events (rate-limit / off-day)
        # so we don't fail the gate on upstream availability, only on real drift.
        tsdb_unavailable = len(tsdb_evs) == 0
        sport_rec = {
            "league_id": SPORT_LEAGUE_IDS[short],
            "pipeline_n": len(pipeline_evs),
            "tsdb_n": len(tsdb_evs),
            "tsdb_unavailable": tsdb_unavailable,
            "matched": len(matched),
            "pipeline_only": len(pipe_only),
            "sportsdb_only": len(sdb_only),
            "coverage": round(cov, 4),
            "pipeline_only_samples": [_strip_dt(e) for e in pipe_only[:5]],
            "sportsdb_only_samples": [_strip_dt(e) for e in sdb_only[:5]],
        }
        summary["sports"][short] = sport_rec
        summary["totals"]["matched"] += len(matched)
        summary["totals"]["pipeline_only"] += len(pipe_only)
        summary["totals"]["sportsdb_only"] += len(sdb_only)
        if pipeline_evs and not tsdb_unavailable and cov < COVERAGE_FLOOR:
            summary["below_floor"].append(short)

    # stdout summary table
    print(f"\nTheSportsDB Schedule Gate  ({started_iso})")
    print(f"{'sport':<7} {'leagueId':<9} {'pipe':>5} {'tsdb':>5} {'match':>6} {'pOnly':>6} {'sOnly':>6} {'cov':>6}")
    print("-" * 60)
    for short in targets:
        rec = summary["sports"].get(short, {})
        if "error" in rec:
            print(f"{short:<7} ERROR: {rec['error']}")
            continue
        marker = " (tsdb-unavail)" if rec.get("tsdb_unavailable") else ""
        print(f"{short:<7} {rec['league_id']:<9} {rec['pipeline_n']:>5} {rec['tsdb_n']:>5} "
              f"{rec['matched']:>6} {rec['pipeline_only']:>6} {rec['sportsdb_only']:>6} "
              f"{rec['coverage']:>6.0%}{marker}")
    if summary["below_floor"]:
        print(f"BELOW {int(COVERAGE_FLOOR * 100)}% FLOOR: {summary['below_floor']}")

    # write report
    if not args.dry_run:
        out_path = args.output or os.path.join(
            "data", f"sports_schedule_gate_{started.strftime('%Y%m%dT%H%M%SZ')}.json")
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)
        print(f"report -> {out_path}")

    if args.report_only or not summary["below_floor"]:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
