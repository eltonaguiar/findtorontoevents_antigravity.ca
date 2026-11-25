#!/usr/bin/env python3
"""Census GitHub Actions from the public web pages instead of the REST API.

Why: the shared GitHub API quota (5,000/h for the whole account) runs dry while
several agents poll it, and a census costs ~110 calls. GitHub server-renders the
Actions pages with an embedded JSON payload
(<script type="application/json" data-target="react-app.embeddedData">), which
carries the same run objects the UI shows. Fetching those pages costs no API quota.

Usage
  python3 tools/gha_web_census.py                      # recent-runs census
  python3 tools/gha_web_census.py --pages 20           # window of N*25 runs
  python3 tools/gha_web_census.py --dormant            # + per-workflow last run
  python3 tools/gha_web_census.py --watch qa-market-validation deploy-riseoftheclaw
  python3 tools/gha_web_census.py --json reports/x.json

Exit codes: 0 = report produced, 1 = could not read the pages at all.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
EMBEDDED = re.compile(
    r'data-target="react-app\.embeddedData">(.*?)</script>', re.S)
# NOTE: lowercase. norm() strips WORKFLOW_RUN_CONCLUSION_ and lowercases, so an
# uppercase set here matched nothing and every census reported "0 failures with no
# later success" while the MIX line showed failures. Keep in sync with norm().
FAIL_C = {"failure", "timed_out", "startup_failure", "action_required"}


# github.com throttles bursts of HTML too (observed 2026-11-25: ~1000 pages at 12
# workers, then /actions came back with 1 page instead of 14 and the tree page
# returned nothing, so the census silently reported a 25-run window and "0 dormant").
# There is no rate-limit header on HTML, so pace requests here and treat a short
# read as a failure instead of a fact.
MIN_INTERVAL = 0.5           # seconds between requests, globally
_THROTTLE = threading.Lock()
_LAST = [0.0]
STATS = collections.Counter()


def _throttle() -> None:
    with _THROTTLE:
        wait = MIN_INTERVAL - (time.monotonic() - _LAST[0])
        if wait > 0:
            time.sleep(wait)
        _LAST[0] = time.monotonic()


def fetch(url: str, tries: int = 4) -> str | None:
    for i in range(tries):
        _throttle()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                STATS["ok"] += 1
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            STATS[f"http_{e.code}"] += 1
            if e.code in (429, 403, 500, 502, 503, 504) and i < tries - 1:
                ra = (e.headers or {}).get("Retry-After")
                # GitHub sends Retry-After: 300 on burst abuse. Honour it, but cap
                # it: one 300 s nap per request stalls the whole scan, and the cap
                # is what keeps a 258-page dormancy pass finishable.
                delay = min(float(ra) if str(ra).isdigit() else 5 * (i + 1), 20)
                print(f"  ~ throttled ({e.code}) {url}; sleeping {delay:.0f}s", file=sys.stderr)
                time.sleep(delay)
                continue
            print(f"  ! {url}: HTTP {e.code}", file=sys.stderr)
            return None
        except (urllib.error.URLError, TimeoutError) as e:
            STATS["transport_error"] += 1
            if i == tries - 1:
                print(f"  ! {url}: {e}", file=sys.stderr)
                return None
            time.sleep(2 * (i + 1))
    return None


def embedded(html: str) -> dict | None:
    m = EMBEDDED.search(html or "")
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        import html as _h
        try:
            return json.loads(_h.unescape(m.group(1)))
        except json.JSONDecodeError:
            return None


def find_runs(obj, out=None):
    """Locate the run list anywhere in a payload (page shapes differ)."""
    out = [] if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "workflowRuns" and isinstance(v, list):
                out.extend(v)
            else:
                find_runs(v, out)
    elif isinstance(obj, list):
        for v in obj:
            find_runs(v, out)
    return out


def norm(r: dict) -> dict:
    st = r.get("state") or {}
    return {
        "name": r.get("workflowName") or r.get("name") or "?",
        "path": r.get("workflowFilePath") or "?",
        "id": r.get("id"),
        "status": (st.get("status") or "").replace("WORKFLOW_RUN_STATUS_", "").lower(),
        "conclusion": (st.get("conclusion") or "").replace(
            "WORKFLOW_RUN_CONCLUSION_", "").lower(),
        "ts": ((r.get("createdAt") or {}).get("timestamp") or ""),
    }


def hours_ago(ts: str, now: dt.datetime) -> float | None:
    if not ts:
        return None
    try:
        t = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (now - t).total_seconds() / 3600


def collect_runs(repo: str, pages: int) -> list[dict]:
    runs, seen = [], set()
    fetched = 0
    for p in range(1, pages + 1):
        url = f"https://github.com/{repo}/actions?page={p}"
        d = embedded(fetch(url) or "")
        if not d:
            print(f"::warning::stopped reading runs at page {p}/{pages} — reporting a "
                  f"PARTIAL window of {len(runs)} runs", file=sys.stderr)
            break
        fetched += 1
        page_runs = [norm(x) for x in find_runs(d.get("payload") or {})]
        if not page_runs:
            break
        new = [r for r in page_runs if r["id"] not in seen]
        for r in new:
            seen.add(r["id"])
        runs.extend(new)
        if len(new) < len(page_runs) or len(page_runs) < 25:
            break
    if pages > 1 and fetched < pages:
        print(f"::warning::read {fetched} of {pages} requested run pages (GitHub HTML "
              f"throttling) — treat this census as partial", file=sys.stderr)
    return runs


def all_workflows(repo: str) -> list[dict]:
    """Every workflow, read from the /actions layout payload.

    NOTE: /actions/workflows does NOT embed the JSON payload (it is a redirect to
    the same layout), so harvesting there silently returned zero workflows and the
    dormancy report came back empty. The list lives in
    payload.workflowsLayoutRoute.workflows on /actions?page=N instead.
    """
    out, seen = [], set()
    for p in range(1, 9):
        d = embedded(fetch(f"https://github.com/{repo}/actions?page={p}") or "")
        if not d:
            break
        wf = (((d.get("payload") or {}).get("workflowsLayoutRoute") or {})
              .get("workflows") or [])
        new = [w for w in wf if w.get("path") and w["path"] not in seen]
        for w in new:
            seen.add(w["path"])
        out.extend(new)
        if not new:
            break
        time.sleep(0.4)
    return out


def all_workflow_files(repo: str, branch: str = "main") -> list[dict]:
    """Every file in .github/workflows, from the code-tree page payload.

    The Actions sidebar only exposes 50 workflows, and /actions/workflows embeds no
    payload at all, so neither can answer "what hasn't run lately?" for a repo with
    382 workflow files. The tree page does: payload.codeViewTreeRoute.tree.items.
    """
    url = f"https://github.com/{repo}/tree/{branch}/.github/workflows"
    d = embedded(fetch(url) or "")
    if not d:
        print("::error::could not read the .github/workflows tree page; dormancy scan "
              "is unavailable (refusing to report a partial file list as complete)",
              file=sys.stderr)
        return []
    route = (d.get("payload") or {}).get("codeViewTreeRoute") or {}
    items = ((route.get("tree") or {}).get("items")) or []
    return [{"name": i.get("name"), "path": f".github/workflows/{i.get('name')}"}
            for i in items if str(i.get("name", "")).endswith((".yml", ".yaml"))]


def workflow_last_runs(repo: str, paths: list[str], workers: int = 3) -> dict:
    """path -> runs list, or None when the page could not be read.

    None vs [] matters: [] means the workflow page loaded and has no runs (never
    registered), None means a 429/timeout. The first draft collapsed both into
    'never registered' and reported 145 such workflows during a throttled scan.
    """
    def one(path: str):
        slug = path.split("/")[-1]
        d = embedded(fetch(f"https://github.com/{repo}/actions/workflows/{slug}?page=1") or "")
        if d is None:
            return path, None
        runs = [norm(x) for x in find_runs(d.get("payload") or {})]
        return path, runs

    res = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for path, runs in ex.map(one, paths):
            if runs is None:      # 429/timeout: keep None so callers can say "unreadable"
                res[path] = None
                continue
            runs.sort(key=lambda r: r["ts"], reverse=True)
            res[path] = runs
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="eltonaguiar/findtorontoevents_antigravity.ca")
    ap.add_argument("--pages", type=int, default=12, help="25 runs per page")
    ap.add_argument("--dormant", action="store_true", help="scan every workflow's last run")
    ap.add_argument("--watch", nargs="*", default=[], help="workflow file slugs to detail")
    ap.add_argument("--health", action="store_true",
                    help="per-workflow success rate, failure streak and flakiness")
    ap.add_argument("--json", default="reports/gha_web_census_latest.json")
    a = ap.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    runs = collect_runs(a.repo, a.pages)
    if not runs:
        print("could not read any run from the web pages", file=sys.stderr)
        return 1
    runs.sort(key=lambda r: r["ts"])
    rep = {"generated_at": now.isoformat(timespec="seconds"), "repo": a.repo,
           "source": "github.com HTML embeddedData (no REST API)",
           "window": {"runs": len(runs), "oldest": runs[0]["ts"], "newest": runs[-1]["ts"]}}

    mix = collections.Counter(r["conclusion"] or r["status"] for r in runs)
    print(f"WINDOW {len(runs)} runs  {runs[0]['ts']} -> {runs[-1]['ts']}")
    print(f"MIX   {dict(mix)}")
    rep["mix"] = dict(mix)

    by = collections.defaultdict(list)
    for r in runs:
        by[r["path"]].append(r)

    unrecovered = []
    for path, rs in by.items():
        fails = [r for r in rs if r["conclusion"] in FAIL_C]
        if not fails:
            continue
        lf = max(fails, key=lambda r: r["ts"])
        succ = [r["ts"] for r in rs if r["conclusion"] == "success"]
        ls = max(succ) if succ else None
        if ls is None or ls < lf["ts"]:
            unrecovered.append({"path": path, "name": lf["name"], "last_failure": lf["ts"],
                                "run_id": lf["id"], "last_success": ls,
                                "failures": len(fails), "runs": len(rs)})
    unrecovered.sort(key=lambda x: x["last_failure"], reverse=True)
    print(f"\n== FAILURES WITH NO LATER SUCCESS: {len(unrecovered)} ==")
    for u in unrecovered:
        print(f"  {u['name'][:44]:44} fail={u['last_failure'][:16]} "
              f"({hours_ago(u['last_failure'], now):.1f}h) run={u['run_id']} "
              f"fails={u['failures']}/{u['runs']} last_success={(u['last_success'] or 'NONE')[:16]}")
    rep["unrecovered"] = unrecovered

    all_fails = [r for r in runs if r["conclusion"] in FAIL_C]
    print(f"\n== FAILURE RUNS IN WINDOW: {len(all_fails)} ==")
    for r in sorted(all_fails, key=lambda x: x["ts"], reverse=True)[:20]:
        print(f"  {r['ts'][:16]}  {r['name'][:42]:42} run={r['id']}")
    rep["failure_runs"] = [{"ts": r["ts"], "name": r["name"], "id": r["id"]}
                           for r in all_fails]

    if a.dormant:
        files = all_workflow_files(a.repo)
        if not files:
            print("dormancy scan skipped: the workflow file list could not be read "
                  "(no dormancy numbers will be reported)", file=sys.stderr)
            files = [{"path": p} for p in by]
            rep["dormancy_unavailable"] = True
            a.dormant = False
        inactive = [w for w in files if str(w.get("path", "")).endswith((".disabled", ".retired"))]
        active = [w for w in files if w not in inactive]
        # Anything already seen in the run window ran inside it; no need to fetch it.
        need = [w["path"] for w in active
                if not by.get(w["path"]) and w["path"] not in (".github/workflows/" + str(w.get("name")))
                or by.get(w["path"]) is None]
        need = [p for p in need if not by.get(p)]
        print(f"\n== DORMANT (no run in >24h) ==")
        print(f"   {len(files)} workflow files (.yml/.yaml), {len(active) - len(need)} active in this "
              f"window, fetching {len(need)} workflow pages (0 REST calls)")
        last = workflow_last_runs(a.repo, need)
        dorm = []
        never = 0
        unreadable = 0
        for w in active:
            got = last.get(w["path"], "not-fetched")
            if got is None:
                unreadable += 1          # throttled: says nothing about dormancy
                continue
            if got == "not-fetched":
                got = by.get(w["path"]) or []
            rs = got
            if not rs:
                never += 1               # page loaded, no runs ever
                continue
            rs = sorted(rs, key=lambda r: r["ts"], reverse=True)
            age = hours_ago(rs[0]["ts"], now) if rs else None
            if age is None or age > 24:
                dorm.append({"path": w["path"], "name": w.get("name"), "age_h": age,
                             "last": rs[0]["ts"] if rs else None,
                             "conclusion": rs[0]["conclusion"] if rs else None})
        dorm.sort(key=lambda x: (x["age_h"] is None, -(x["age_h"] or 0)))
        for d in dorm:
            tag = "NEVER" if d["age_h"] is None else f"{d['age_h']:.0f}h"
            print(f"  {str(d['name'])[:44]:44} last={tag:>6} concl={d['conclusion'] or '-':9} {d['path']}")
        print(f"  dormant={len(dorm)} of {len(active)} workflow files; "
              f"never_run={never}; unreadable(429/timeout)={unreadable}")
        if unreadable:
            print(f"::warning::{unreadable} workflow pages could not be read, so dormancy "
                  f"is a LOWER BOUND", file=sys.stderr)
        rep["dormant"] = dorm
        rep["never_run"] = never
        rep["unreadable"] = unreadable
        rep["workflow_files"] = len(files)

    if a.watch:
        print(f"\n== WATCHED WORKFLOWS ==")
        watched = {}
        for slug in (s for raw in a.watch for s in str(raw).split(",") if s.strip()):
            slug = slug.strip()
            if slug.endswith((".yml", ".yaml")):
                slug = slug.rsplit(".", 1)[0]
            path = f".github/workflows/{slug}.yml"
            rs = workflow_last_runs(a.repo, [path]).get(path) or []
            watched[slug] = rs[:8]
            print(f"  {slug}")
            for r in rs[:6]:
                print(f"    {r['ts'][:16]}  {(r['conclusion'] or r['status']):10} run={r['id']}")
        rep["watched"] = watched

    if a.health:
        print("\n== HEALTH QUALITY (per workflow, from the run window) ==")
        rows = []
        for path, rs in by.items():
            done = [r for r in rs if r["conclusion"] not in ("in_progress", "queued", "pending", "")]
            if not done:
                continue
            ok = sum(1 for r in done if r["conclusion"] == "success")
            bad = sum(1 for r in done if r["conclusion"] in FAIL_C)
            seq = list(reversed(done))  # newest first
            streak = 0
            for r in seq:
                if r["conclusion"] in FAIL_C:
                    streak += 1
                else:
                    break
            flips = sum(1 for i in range(1, len(seq))
                        if (seq[i]["conclusion"] in FAIL_C) != (seq[i - 1]["conclusion"] in FAIL_C))
            rows.append({
                "path": path, "name": done[0]["name"], "runs": len(done),
                "success_rate": round(100.0 * ok / len(done), 1),
                "failures": bad, "fail_streak": streak, "flips": flips,
                "last": seq[0]["ts"], "last_conclusion": seq[0]["conclusion"],
            })
        noisy = [r for r in rows if r["failures"]]
        noisy.sort(key=lambda r: (-r["fail_streak"], r["success_rate"]))
        for r in noisy[:15]:
            print(f"  {r['name'][:36]:36} runs={r['runs']:2} ok={r['success_rate']:5.1f}% "
                  f"fails={r['failures']:2} streak={r['fail_streak']:2} flips={r['flips']:2} "
                  f"last={r['last_conclusion']}")
        clean = len(rows) - len(noisy)
        print(f"  {clean} workflows had no failure in the window; {len(noisy)} had at least one")
        rep["health"] = rows

    print(f"\nHTTP: {dict(STATS)}")
    if a.json:
        import os
        os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
        with open(a.json, "w") as f:
            json.dump(rep, f, indent=1)
        print(f"\nwritten: {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
