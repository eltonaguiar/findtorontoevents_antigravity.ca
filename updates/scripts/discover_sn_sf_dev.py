#!/usr/bin/env python3
"""Discover + curate top ServiceNow / Salesforce developer roles for
Toronto/GTA + Canada (fully remote) from the live BESTIEJOB feed and
cross-check optional ATS tenants.

Pipeline: load feed -> tag filter -> dev-title filter -> geo filter ->
matcher classify -> dedupe agency reposts -> optional liveness check ->
rank -> emit verified_leads.json + markdown report.

Usage:
  python3 updates/scripts/discover_sn_sf_dev.py \
    --feed /tmp/bestiejob_feed.json \
    --out-dir docs \
    --report updates/2026-11-18-discovery-report.md \
    [--check-live] [--limit 60]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

PROTO = Path(__file__).resolve().parents[2] / "ideas" / "bestiejob" / "prototypes"
sys.path.insert(0, str(PROTO))
from job_signal_matcher import classify  # noqa: E402

FEED_URL = "https://eltonaguiar.github.io/BESTIEJOB/jobs.json"
DEV = re.compile(
    r"\bdeveloper|\bengineer|\barchitect|\bconsultant|\bimplementer|\bspecialist|"
    r"\btechnical\s+lead|\btech\s+lead|\bprogrammer|\btechnical\s+consultant|"
    r"\bplatform\s+(?:developer|engineer)",
    re.I,
)
ADMIN_ONLY = re.compile(r"^(?=.*\badmin(?:istrator)?\b)(?!.*\b(?:developer|engineer|architect|consultant|implementer)\b)", re.I)
GTA = re.compile(
    r"toronto|mississauga|brampton|vaughan|markham|scarborough|etobicoke|north york|"
    r"oakville|burlington|hamilton|richmond hill|oshawa|ajax|pickering|milton|\bgta\b|"
    r"greater toronto",
    re.I,
)
AGENCY_HINT = re.compile(
    r"infotek|staffing|consulting|solutions|technologies|services|resources|"
    r"systems|global|group|recruit|talent|partners|associates|inc\.?$|llc|corp",
    re.I,
)
DIRECT_EMPLOYER_HINT = re.compile(
    r"^(?:td|cibc|bmo|rbc|scotiabank|servicenow|salesforce|deloitte|pwc|kpmg|ey|"
    r"accenture|ibm|cognizant|infosys|tcs|capgemini|kinaxis|interac|docusign|benevity|"
    r"telus|bell|rogers|pointclickcare|brookfield|manulife|sunlife|canada life|"
    r"loblaw|celestica|equinix|state street|macquarie|danaher|docebo|docker|canadian tire|"
    r"cmhc|hydro one|ontario health|city of toronto|rcmp|gdit|dxc)",
    re.I,
)


def load_feed(path_or_url: str) -> dict:
    if path_or_url.startswith("http"):
        raw = urllib.request.urlopen(path_or_url, timeout=30).read()
        return json.loads(raw)
    return json.loads(Path(path_or_url).read_text(encoding="utf-8"))


def hay(j: dict) -> str:
    return f"{j.get('location','')} {j.get('workArrangement','')}".lower()


def is_canada_remote(j: dict) -> bool:
    loc = (j.get("location") or "").lower()
    h = hay(j)
    if re.search(r"remote\s*[-/]?\s*canada|canada\s*[-/]?\s*remote|remote\s*\(canada\)|anywhere in canada|canada remote", h):
        return True
    if "canada" in loc and ("remote" in h):
        return True
    if j.get("workArrangement") == "remote" and "canada" in h:
        return True
    return False


def in_scope_geo(j: dict) -> tuple[bool, str]:
    m = classify(j)
    elig = m["eligible"]
    bucket = m["geo_bucket"]
    if elig.get("toronto_gta_local"):
        return True, bucket
    if is_canada_remote(j) and not elig.get("exclude_signal"):
        return True, bucket
    # accept explicit Canada-wide remote buckets
    if bucket.startswith("Remote (Canada") and not elig.get("exclude_signal"):
        return True, bucket
    return False, bucket


def norm_title(t: str) -> str:
    t = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", t or "")
    t = re.sub(r"\b(?:jr|sr|senior|junior|lead|principal|staff|contract|remote|hybrid|onsite)\b", " ", t, flags=re.I)
    t = re.sub(r"[^a-z0-9 ]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def norm_company(c: str) -> str:
    c = re.sub(r"\b(?:inc|corp|ltd|limited|llc|gmbh|co|canada)\b\.?", " ", (c or ""), flags=re.I)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", c.lower())).strip()


_TRASH_COMPANY = re.compile(
    r"^(?:unknown|n/?a|company|confidential|canada|remote|jobs?\.?ca|workopolis.*|"
    r"linkedin|indeed|adzuna|trabajo.*|movojobs|movo\s*jobs|onjobcentre|simplyhired)$",
    re.I,
)
_LOC_IN_TITLE = re.compile(
    r"\s+(?:in|at|@)\s+[A-Z][\w .'\-]*?(?:,\s*(?:ON|Ontario|Canada|QC|BC|AB|MB|NS|NB|SK|NL|PE)\b.*)?$",
    re.I,
)
_BOARD_SUFFIX = re.compile(
    r"\s*[|·/]\s*(?:jobs?\.?ca|workopolis|remotive|movo\s*jobs|onjobcentre|remotejobs|"
    r"trabajo.*|simplyhired|linkedin|indeed|adzuna)\b.*$",
    re.I,
)


def clean_fields(j: dict) -> tuple[str, str]:
    """Return (title, company) cleaned from malformed feed rows where the
    company field leaked location/excerpt text, or the title carries the employer."""
    title = (j.get("title") or "").strip()
    company = (j.get("company") or "").strip()
    source = (j.get("source") or "").strip()

    # pull "at <Company>" / "@ <Company>" out of the title
    m = re.search(r"(?:\bat\b|@)\s+([A-Z][\w&.\-]+(?:\s+[A-Z][\w&.\-]+){0,4})\s*$", title)
    if m and (not company or _TRASH_COMPANY.match(company)):
        company = m.group(1).strip()
        title = title[: m.start()].strip(" -–|·")

    # pull trailing " - <Company>" (capitalised) out of the title
    m = re.search(r"\s[-–]\s([A-Z][\w&.'\-]+(?:\s+[A-Z][\w&.'\-]+){0,4})\s*$", title)
    if m and (not company or _TRASH_COMPANY.match(company)) and not re.search(
        r"\b(?:remote|toronto|canada|contract|developer|architect|consultant|engineer)\b", m.group(1), re.I
    ):
        company = m.group(1).strip()
        title = title[: m.start()].strip(" -–|·")

    # strip embedded "in Toronto, ON ..." / "| BMO" / " / Jobs.ca" fragments from the title
    title = _BOARD_SUFFIX.sub("", title)
    title = re.sub(r"\s+(?:in|at)\s+(?:Toronto|Mississauga|Brampton|Markham|Greater Toronto|Canada)\b.*$", "", title, flags=re.I)
    title = re.sub(r"\s*[🇨🇦].*$", "", title)
    title = re.sub(r"\s*/\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s*$", "", title)  # trailing person name
    # trailing "(Apex 2000 Inc)" -> company, and trailing "- Toronto, ON, Canada"
    m = re.search(r"\s*\(([^)]*(?:Inc|LLC|Ltd|Corp|Group|Consulting|Solutions|Technologies)[^)]*)\)\s*$", title, re.I)
    if m:
        if not company or _TRASH_COMPANY.match(company) or company == "Unknown":
            company = m.group(1).strip()
        title = title[: m.start()].strip(" -–|·")
    title = re.sub(
        r"\s*[-–]\s*[A-Z][\w .'\-]*?,\s*(?:ON|Ontario|QC|BC|AB|MB|NS|NB|SK|NL|PE|Canada)\b.*$",
        "", title, flags=re.I)
    title = re.sub(r"^Job\s*[-–]\s*", "", title)
    title = re.sub(r"\s+", " ", title).strip(" -–|·")

    # company contaminated with a location or job-board suffix
    mc = re.search(r"\(([^)]*(?:Inc|LLC|Ltd|Corp|Group|Consulting|Solutions|Technologies)[^)]*)\)", company, re.I)
    if mc:
        company = mc.group(1).strip()
    if company and re.search(r"\b(?:remote|toronto|canada|jobs?\.ca|workopolis|movojobs)\b|[,|/·]", company, re.I):
        if not re.search(r"\b(?:inc|corp|ltd|llc|group|bank|capital|consulting|solutions|technologies)\b", company, re.I):
            company = ""
    # fallback: derive a company-like token from the source when known employers use it
    if (not company or _TRASH_COMPANY.match(company)) and re.fullmatch(r"[a-z][a-z0-9\-]{1,20}", source):
        if source not in {"readme", "linkedin", "indeed", "adzuna", "ashby", "lever", "workday",
                          "greenhouse", "smartrecruiters", "builtin", "jobicy", "remotive",
                          "remoteok", "dice", "jobbank", "canadajobbank", "trabajo", "movojobs",
                          "onjobcentre", "simplyhired", "careerbeacon", "recruit", "talent"}:
            company = source.upper() if len(source) <= 4 else source.replace("-", " ").title()
    if not company or _TRASH_COMPANY.match(company):
        company = "Unknown"
    return title, company


def md_cell(s: str) -> str:
    return str(s or "").replace("|", "\\|").replace("\n", " ").strip()


try:  # optional dependency; falls back to the safe map below
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None

RIGHTS_CONFIG = PROTO.parents[2] / "updates" / "config" / "source-rights.yaml"

# Conservative fallback when the YAML config or PyYAML is unavailable.
DEFAULT_RIGHTS = {
    "readme": {"rights": "own_site_attributed", "redistribute": True},
    "adzuna": {"rights": "own_site_attributed", "redistribute": True, "require_linkback": True},
    "greenhouse": {"rights": "redistribution_approved", "redistribute": True},
    "lever": {"rights": "redistribution_approved", "redistribute": True},
    "ashby": {"rights": "redistribution_approved", "redistribute": True},
    "smartrecruiters": {"rights": "redistribution_approved", "redistribute": True},
    "linkedin": {"rights": "manual_discovery", "redistribute": False},
    "workday": {"rights": "permitted_api_private", "redistribute": False},
}


def load_rights(path: Path = RIGHTS_CONFIG) -> dict:
    """Load source rights config; return {source: entry}. Falls back safely."""
    try:
        if path.exists() and yaml is not None and path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            srcs = data.get("sources", {})
            if srcs:
                return {str(k).lower(): v for k, v in srcs.items()}
    except Exception:
        pass
    return DEFAULT_RIGHTS


def is_publishable(entry: dict) -> bool:
    """A source may be published publicly only when redistribution is allowed.

    Explicit `redistribute: false` always wins. Otherwise `redistribution_approved`
    and `own_site_attributed` are publishable; unknown sources default to False.
    """
    if not entry:
        return False
    if entry.get("redistribute") is False:
        return False
    if entry.get("redistribute") is True:
        return True
    return entry.get("rights") in {"redistribution_approved", "own_site_attributed"}


def is_live(url: str, timeout: int = 8) -> bool | None:
    if not url:
        return None
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "bestiejob-discovery/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 400
    except Exception:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "bestiejob-discovery/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return 200 <= r.status < 400
        except Exception:
            return False


def score(j: dict, m: dict, live: bool | None) -> int:
    s = 0
    title = j.get("title", "")
    strong = m.get("tracks", {}).get("ServiceNow", 0) + m.get("tracks", {}).get("Salesforce", 0)
    s += min(strong, 9)
    if m.get("certs"):
        s += 4
    if DIRECT_EMPLOYER_HINT.search(j.get("company", "") or ""):
        s += 3
    if AGENCY_HINT.search(j.get("company", "") or "") and not DIRECT_EMPLOYER_HINT.search(j.get("company", "") or ""):
        s -= 2
    if re.search(r"\bdeveloper|\bengineer|architect\b", title, re.I):
        s += 2
    if ADMIN_ONLY.search(title):
        s -= 2
    if j.get("workArrangement") == "remote":
        s += 1
    if live is True:
        s += 2
    elif live is False:
        s -= 5
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed", default=FEED_URL)
    ap.add_argument("--out-dir", default="docs/bestiejob")
    ap.add_argument("--report", default="updates/2026-11-18-discovery-report.md")
    ap.add_argument("--check-live", action="store_true")
    ap.add_argument("--limit", type=int, default=60)
    args = ap.parse_args()

    data = load_feed(args.feed)
    jobs = data.get("jobs", data if isinstance(data, list) else [])
    seen = set()
    cands = []
    for j in jobs:
        tags = j.get("tags", [])
        track_tag = "servicenow" if "servicenow" in tags else ("salesforce" if "salesforce" in tags else None)
        if not track_tag:
            continue
        title = j.get("title", "") or ""
        if not DEV.search(title):
            continue
        ok, bucket = in_scope_geo(j)
        if not ok:
            continue
        m = classify(j)
        # require a target track surviving intent/taxonomy guards
        if not (m["tracks"].get("ServiceNow") or m["tracks"].get("Salesforce")):
            continue
        title, company = clean_fields(j)
        j = {**j, "title": title, "company": company}
        key = (norm_title(title), norm_company(company))
        # also collapse cross-source copies that differ only by unknown company
        alt_key = (norm_title(title), "") if company == "Unknown" else key
        if key in seen or (company == "Unknown" and alt_key in seen):
            continue
        seen.add(key)
        seen.add(alt_key)
        cands.append({"job": j, "match": m, "bucket": bucket, "track": track_tag})

    # liveness: prelim-score then only probe a bounded shortlist
    for c in cands:
        c["score"] = score(c["job"], c["match"], None)
    if args.check_live:
        shortlist = sorted(cands, key=lambda c: c["score"], reverse=True)[: max(args.limit * 4, 120)]
        for c in shortlist:
            c["live"] = is_live(c["job"].get("url", ""))
        for c in cands:
            c.setdefault("live", None)
            c["score"] = score(c["job"], c["match"], c["live"])
    else:
        for c in cands:
            c["live"] = None

    cands.sort(key=lambda c: c["score"], reverse=True)
    top = cands[: args.limit]

    rights = load_rights()
    out = []
    for c in top:
        j, m = c["job"], c["match"]
        src = (j.get("source") or "").strip().lower()
        rentry = rights.get(src, {})
        out.append({
            "title": j.get("title"),
            "company": j.get("company"),
            "location": j.get("location"),
            "workArrangement": j.get("workArrangement"),
            "url": j.get("url"),
            "source": j.get("source"),
            "postedDate": j.get("postedDate"),
            "tags": j.get("tags", []),
            "track": c["track"],
            "tracks": m["tracks"],
            "certs": m["certs"],
            "geo_bucket": c["bucket"],
            "eligible": m["eligible"],
            "score": c["score"],
            "live": c["live"],
            "rights": rentry.get("rights", "unknown"),
            "redistribute": is_publishable(rentry),
            "require_linkback": bool(rentry.get("require_linkback")),
        })

    public = [o for o in out if o["redistribute"]]

    out_dir = Path(args.out_dir)
    (out_dir / "data").mkdir(parents=True, exist_ok=True)
    (out_dir / "data" / "verified_leads.json").write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")
    # Full (internal) set retained OUTSIDE the published docs/ tree for auditing.
    internal_path = Path(args.report).parent / "bestiejob-leads-internal.json"
    internal_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    blocked = len(out) - len(public)
    count = {"ServiceNow": sum(1 for o in public if o["track"] == "servicenow"),
             "Salesforce": sum(1 for o in public if o["track"] == "salesforce")}
    live_ok = sum(1 for o in public if o["live"] is True)
    md = [f"# Discovery Report — SN/SF Developer Roles (Toronto/GTA + Canada-remote)", "",
          f"- Feed: `{args.feed}`", f"- Candidates after filters: **{len(cands)}**",
          f"- Curated top: **{len(out)}**; publishable after rights gate: **{len(public)}** "
          f"(blocked {blocked}) (ServiceNow {count['ServiceNow']} / Salesforce {count['Salesforce']})",
          f"- Liveness checked: {'yes' if args.check_live else 'no'}"
          + (f" — reachable {live_ok}/{len(public)}" if args.check_live else ""), "",
          "_Publishable = redistribute allowed by `updates/config/source-rights.yaml`. "
          "LinkedIn/Workday rows are internal-only._", ""]
    for track in ("servicenow", "salesforce"):
        md.append(f"## {track.title()}")
        md.append("| # | Title | Company | Location | Arrangement | Score | Live | Source | Rights | Public |")
        md.append("|---|-------|---------|----------|-------------|-------|------|--------|--------|--------|")
        i = 0
        for o in out:
            if o["track"] != track:
                continue
            i += 1
            live = "?" if o["live"] is None else ("yes" if o["live"] else "NO")
            md.append(f"| {i} | {md_cell(o['title'])} | {md_cell(o['company'])} | {md_cell(o['location'])} | "
                      f"{md_cell(o['workArrangement'])} | {o['score']} | {live} | {md_cell(o['source'])} | "
                      f"{md_cell(o['rights'])} | {'yes' if o['redistribute'] else 'no'} |")
        md.append("")
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"candidates={len(cands)} curated={len(out)} public={len(public)} blocked={blocked} "
          f"SN={count['ServiceNow']} SF={count['Salesforce']} live_ok={live_ok}")
    print(f"wrote {out_dir/'data'/'verified_leads.json'} (+ {internal_path}) and {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
