#!/usr/bin/env python3
"""Fetch raw GitHub Actions job logs through the WEBSITE, via chrome-devtools-mcp.

No GitHub REST API is used. The flow is the same one a human performs:

  1. Open  https://github.com/<owner>/<repo>/actions/runs/<run_id>  in the browser
     (the CLI attaches to the user's already-authenticated Chrome via --autoConnect).
  2. Read the job ids and commit sha out of the rendered DOM.
  3. Visit the "View raw logs" link for each job:
        https://github.com/<owner>/<repo>/commit/<sha>/checks/<job_id>/logs
     GitHub 302s that to a short-lived signed Azure Blob URL
     (productionresultssaN.blob.core.windows.net/.../job-logs.txt) holding plain text.
  4. Read the resolved blob URL from location.href and pull it.

The blob URL is pre-authorised by its SAS signature, so the download needs no
cookies - but it is time limited (typically ~10-30 min), so fetch promptly.

Usage:
  python tools/gha_fetch_logs_via_browser.py 45721890415
  python tools/gha_fetch_logs_via_browser.py 45721890415 45724028919
  python tools/gha_fetch_logs_via_browser.py --job 45721890415/139582011591
  python tools/gha_fetch_logs_via_browser.py 45721890415 --out tmp/gha/logs
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = "eltonaguiar/findtorontoevents_antigravity.ca"
DEFAULT_OUT = Path("tmp/gha/logs")


# ---------------------------------------------------------------- CLI plumbing
def _cdt_argv() -> list[str]:
    """Resolve how to invoke the chrome-devtools CLI.

    On Windows npm installs a `.cmd` shim, which forces the call through cmd.exe.
    cmd.exe REWRITES the argument string, which silently chops a multi-line JS
    payload such that `--pageId` never arrives - the CLI then answers
    "specify either a pageId or a serviceWorkerId". So on Windows we run the
    package's real JS entry point with node, where argv survives byte-for-byte.
    """
    if os.name != "nt":
        return [shutil.which("chrome-devtools") or "chrome-devtools"]

    roots = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        roots.append(Path(appdata) / "npm" / "node_modules" / "chrome-devtools-mcp")
    roots.append(Path.home() / "AppData" / "Roaming" / "npm" / "node_modules" / "chrome-devtools-mcp")
    for root in roots:
        pkg = root / "package.json"
        if not pkg.is_file():
            continue
        try:
            meta = json.loads(pkg.read_text(encoding="utf-8"))
            b = meta.get("bin")
            rel = b if isinstance(b, str) else (b or {}).get("chrome-devtools")
            if rel:
                js = (root / rel).resolve()
                if js.is_file():
                    return ["node", str(js)]
        except Exception:  # noqa: BLE001 - fall through to the shim
            continue
    return ["cmd", "/c", shutil.which("chrome-devtools") or "chrome-devtools"]


def cdt(*args: str, timeout: int = 60) -> str:
    """Run the chrome-devtools CLI and return combined output.

    Navigating to a signed blob URL can leave the tab's load event pending, which
    wedges subsequent commands. A short per-call timeout turns that into a
    skip-and-continue instead of a hang.
    """
    try:
        p = subprocess.run(
            [*_cdt_argv(), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout,
        )
        return (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        print(f"  (cli timeout after {timeout}s: {' '.join(args[:2])})")
        return ""


def parse_tool_output(raw: str):
    """Unwrap a chrome-devtools result.

    Two shapes occur:
      - plain JSON  {"pages": [...]}                     (list_pages / new_page)
      - enveloped   {"message": "...```json\n<value>\n```"}
    """
    raw = raw.strip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            return None
        obj = json.loads(m.group(0))
    if isinstance(obj, dict) and "message" in obj and len(obj) <= 3:
        msg = str(obj["message"])
        m = re.search(r"```json\s*(.*?)\s*```", msg, re.S)
        if m:
            return json.loads(m.group(1))
        return msg
    return obj


def list_pages() -> list[dict]:
    d = parse_tool_output(cdt("list_pages", "--output-format=json"))
    return (d or {}).get("pages", []) if isinstance(d, dict) else []


def page_id_for(url_fragment: str) -> int | None:
    for p in list_pages():
        if url_fragment in (p.get("url") or ""):
            return p.get("id")
    return None


def evaluate(page_id: int, js: str):
    return parse_tool_output(
        cdt("evaluate_script", js, "--pageId", str(page_id), "--output-format=json")
    )


# ------------------------------------------------------------------- the work
DISCOVER_JS = r"""() => {
  const jobLinks = [...document.querySelectorAll('a[href*="/job/"]')];
  const jobs = [];
  const seen = new Set();
  for (const a of jobLinks) {
    const m = (a.getAttribute('href') || '').match(/\/job\/(\d+)/);
    if (!m) continue;
    const id = m[1];
    const name = (a.textContent || '').trim().replace(/\s+/g, ' ');
    if (!seen.has(id)) { seen.add(id); jobs.push({id, name}); }
    else if (name) { const j = jobs.find(x => x.id === id); if (j && !j.name) j.name = name; }
  }
  const shas = [...new Set([...document.querySelectorAll('a[href*="/commit/"]')]
    .map(a => ((a.getAttribute('href') || '').match(/\/commit\/([0-9a-f]{7,40})/) || [])[1])
    .filter(Boolean))];
  return {jobs, sha: shas[0] || null, title: document.title};
}"""


def wait_for_discovery(page_id: int, tries: int = 10, delay: float = 1.0) -> dict:
    """Poll until the run page has rendered its job links.

    `new_page` can return before navigation settles, which yields an empty DOM
    (no jobs, blank title) if we scrape immediately.
    """
    last: dict = {}
    for _ in range(tries):
        info = evaluate(page_id, DISCOVER_JS)
        if isinstance(info, dict):
            last = info
            if info.get("jobs") and info.get("sha"):
                return info
        time.sleep(delay)
    return last


def discover(run_id: str) -> tuple[int, list[dict], str | None, str]:
    run_url = f"https://github.com/{REPO}/actions/runs/{run_id}"
    print(f"[run {run_id}] opening {run_url}")
    before = {p.get("id") for p in list_pages()}
    cdt("new_page", run_url, "--output-format=json")
    after = list_pages()
    fresh = [p.get("id") for p in after if p.get("id") not in before]

    # Prefer the tab we just opened; fall back to any tab already on this run.
    pid = next((p["id"] for p in after
                if p.get("id") in fresh and f"actions/runs/{run_id}" in (p.get("url") or "")), None)
    if pid is None and fresh:
        pid = fresh[-1]
    if pid is None:
        pid = page_id_for(f"actions/runs/{run_id}")
    if pid is None:
        raise RuntimeError(f"could not find the run page for {run_id} after opening it")

    info = wait_for_discovery(pid)
    jobs = info.get("jobs") or []
    sha = info.get("sha")
    title = info.get("title") or ""
    print(f"[run {run_id}] page={pid} title={title!r} jobs={len(jobs)} sha={sha}")
    return pid, jobs, sha, title


def fetch_job_log(page_id: int, sha: str, job_id: str, job_name: str, out_dir: Path) -> Path | None:
    """Fetch one job's raw log.

    Each job gets its OWN tab which is closed afterwards. Navigating a shared tab
    to the signed blob URL can leave its load event pending forever and wedge the
    whole CDP attach (observed 2026-11-25: every later command timed out and only
    closing the tab / restarting Chrome recovered it). A throwaway tab limits the
    blast radius to one job.
    """
    raw_url = f"https://github.com/{REPO}/commit/{sha}/checks/{job_id}/logs"
    before = {p.get("id") for p in list_pages()}
    cdt("new_page", raw_url)
    after = list_pages()
    fresh = [p for p in after if p.get("id") not in before]
    job_page = next((p["id"] for p in fresh if "blob.core.windows.net" in (p.get("url") or "")), None)
    if job_page is None and fresh:
        job_page = fresh[-1]["id"]
    if job_page is None:
        job_page = page_id_for("/logs")
    print(f"  [job {job_id}] opened page {job_page}")
    resolved = evaluate(job_page, "() => location.href") if job_page is not None else None
    if job_page is not None:
        cdt("close_page", str(job_page), timeout=30)
    if not isinstance(resolved, str) or not resolved.startswith("http"):
        print(f"  [job {job_id}] no resolved URL (still on GitHub? auth or missing logs)")
        return None
    if "github.com" in resolved and "/checks/" in resolved:
        print(f"  [job {job_id}] stayed on GitHub -> logs not accessible for this job")
        return None

    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", job_name or "job").strip("_")[:60]
    dest = out_dir / f"{job_id}__{slug}.log"
    try:
        req = urllib.request.Request(resolved, headers={"User-Agent": "gha-log-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        # Azure answers an expired SAS with 403 + an XML AuthenticationFailed body.
        body = e.read().decode("utf-8", "replace")
        if "Signature not valid in the specified time frame" in body:
            print(f"  [job {job_id}] SAS EXPIRED before download - re-resolve the link and retry")
            print("            (signed links are valid ~10 minutes from the st/se window)")
        else:
            print(f"  [job {job_id}] download failed: HTTP {e.code}")
        return None
    except Exception as e:  # noqa: BLE001 - report, do not abort the whole run
        print(f"  [job {job_id}] download failed: {e}")
        return None
    text = data.decode("utf-8", "replace").lstrip("\ufeff")
    # Never persist an error page as if it were a log.
    if text.lstrip().startswith("<?xml") or "AuthenticationFailed" in text[:500]:
        print(f"  [job {job_id}] response was an Azure error document, not a log - discarded")
        return None
    dest.write_text(text, encoding="utf-8")
    print(f"  [job {job_id}] {slug:<40} {len(text):>8} chars -> {dest}")
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_ids", nargs="*", help="workflow run ids")
    ap.add_argument("--job", action="append", default=[],
                    help="run_id/job_id to fetch a single job (repeatable)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.run_ids and not args.job:
        ap.error("give at least one run id or --job run_id/job_id")

    args.out.mkdir(parents=True, exist_ok=True)
    fetched: list[Path] = []

    for spec in args.job:
        run_id, _, job_id = spec.partition("/")
        if not job_id:
            print(f"bad --job spec {spec!r}; expected run_id/job_id", file=sys.stderr)
            continue
        pid, jobs, sha, _ = discover(run_id)
        name = next((j["name"] for j in jobs if j["id"] == job_id), "job")
        if not sha:
            print(f"[run {run_id}] no commit sha found; cannot build raw-log URL", file=sys.stderr)
            continue
        got = fetch_job_log(pid, sha, job_id, name, args.out)
        if got:
            fetched.append(got)

    for run_id in args.run_ids:
        pid, jobs, sha, _ = discover(run_id)
        if not sha:
            print(f"[run {run_id}] no commit sha found; skipping", file=sys.stderr)
            continue
        for j in jobs:
            got = fetch_job_log(pid, sha, j["id"], j.get("name", ""), args.out)
            if got:
                fetched.append(got)

    print(f"\nfetched {len(fetched)} log file(s) into {args.out}")
    return 0 if fetched else 1


if __name__ == "__main__":
    raise SystemExit(main())
