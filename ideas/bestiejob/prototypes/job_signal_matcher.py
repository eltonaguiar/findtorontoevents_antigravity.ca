#!/usr/bin/env python3
"""Prototype: body/cert-aware track + geo matching for BESTIEJOB candidates.

Starter work to address gaps in scan_boards.py/AGENT-RUNBOOK review:
- two-tier signals (title/body keywords) for ServiceNow, Salesforce, Other (ITSM/CMDB/ITAM)
- cert tokens (CSA, CAD, CIS, CTA, etc.) captured as evidence
- Toronto/GTA + Canada-remote / Ontario-eligible geo bucketing heuristics

Input: JSON array or JSONL of job dicts (flexible keys: title, description/body/text,
location/location_summary, remote/workplaceType/mode, url/posting_url, company/publisher).
Output: JSONL with added `match` object (tracks, certs, geo_bucket, eligible, reasons).

No deps, no network. Extend patterns/weights and integrate into scan->normalize->verify pipeline.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def _c(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.I)


TRACKS = {
    "ServiceNow": {
        "strong": [
            _c(r"\bservice\s*now\b"), _c(r"\bgliderecord\b"), _c(r"\bglideajax\b"), _c(r"\bglidesystem\b"),
            _c(r"\bscript include"), _c(r"\bintegrationhub\b"), _c(r"\bflow designer\b"), _c(r"\bitsm\b"),
            _c(r"\bitom\b"), _c(r"\bitam\b"), _c(r"\bcmdb\b"), _c(r"\bcsdm\b"), _c(r"\bcsm\b"), _c(r"\bfsm\b"),
            _c(r"\bhrsd\b"), _c(r"\bsecops\b"), _c(r"\bgrc\b"), _c(r"\bservicenow developer\b"),
            _c(r"\bservicenow administrator\b"), _c(r"\bservicenow architect\b"), _c(r"\bnow platform\b"),
        ],
        "medium": [
            _c(r"\bscoped app"), _c(r"\bbusiness rule"), _c(r"\bclient script"), _c(r"\bui policy"),
            _c(r"\bupdate set"), _c(r"\bmid server"), _c(r"\bimport set"), _c(r"\btransform map"),
            _c(r"\bd[ée]veloppeur(?:se)?\s+servicenow\b"), _c(r"\bconsultant(?:e)?\s+servicenow\b"),
        ],
    },
    "Salesforce": {
        "strong": [
            _c(r"\bsalesforce\b"), _c(r"\bapex\b"), _c(r"\blwc\b"), _c(r"\blightning web component"),
            _c(r"\bsoql\b"), _c(r"\bsosl\b"), _c(r"\bvisualforce\b"), _c(r"\bsales\s*cloud\b"),
            _c(r"\bservice\s*cloud\b"), _c(r"\bexperience\s*cloud\b"), _c(r"\bmarketing\s*cloud\b"),
            _c(r"\bcpq\b"), _c(r"\bmulesoft\b"), _c(r"\bforce\.com\b"), _c(r"\bsalesforce developer\b"),
            _c(r"\bsalesforce administrator\b"), _c(r"\bsalesforce architect\b"),
        ],
        "medium": [
            _c(r"\bflow builder\b"), _c(r"\bomnistudio\b"), _c(r"\bdata cloud\b"), _c(r"\bagentforce\b"),
            _c(r"\bplatform developer\b"),
            _c(r"\bd[ée]veloppeur(?:se)?\s+salesforce\b"), _c(r"\bconsultant(?:e)?\s+salesforce\b"),
        ],
    },
    "Other": {
        "strong": [
            _c(r"\bitsm\b"), _c(r"\bcmdb\b"), _c(r"\bitam\b"), _c(r"\bitom\b"), _c(r"\basset management\b"),
            _c(r"\bconfiguration management\b"), _c(r"\bchange management\b"), _c(r"\bincident management\b"),
            _c(r"\bproblem management\b"), _c(r"\bintegration (?:engineer|developer|specialist)\b"),
            _c(r"\bworkflow automation\b"), _c(r"\bpower platform\b"), _c(r"\bpower bi\b"),
            _c(r"\binformatica\b"), _c(r"\bmdm\b"), _c(r"\bmaster data management\b"),
        ],
        "medium": [
            _c(r"\betl\b"), _c(r"\bdata engineer\b"), _c(r"\bplatform engineer\b"), _c(r"\bbusiness applications\b"),
        ],
    },
}

CERTS = [
    ("CSA", _c(r"\bCSA\b|\bCertified System Administrator\b")),
    ("CAD", _c(r"\bCAD\b|\bCertified Application Developer\b")),
    # CIS family (ITSM/CSM/HAM/HRSD/ITOM/Discovery etc.) - common in SN postings
    ("CIS", _c(r"\bCIS(?:-[A-Z0-9]+)?\b|\bCertified Implementation Specialist\b")),
    ("CTA", _c(r"\bCTA\b|\bCertified Technical Architect\b")),
    ("PD1", _c(r"\bPD\s*1\b|\bPlatform Developer I\b")),
    ("PD2", _c(r"\bPD\s*2\b|\bPlatform Developer II\b")),
    ("ITIL", _c(r"\bITIL(?:\s*v?\d)?\b")),
    ("SN_AdminCert", _c(r"\bCertified System Administrator\b|\bServiceNow Certified\b|\bAdministrateur(?:rice)?\s+ServiceNow\b")),
    ("SF_AdminCert", _c(r"\bSalesforce Certified Administrator\b|\bAdministrateur(?:rice)?\s+Salesforce\b")),
]

TORONTO_CORE = _c(r"\btoronto\b|\bscarborough\b|\betobicoke\b|\bnorth york\b|\beast york\b")
GTA_CITIES = _c(
    r"\bmississauga\b|\bmarkham\b|\bbrampton\b|\bvaughan\b|\brichmond hill\b|"
    r"\boakville\b|\bburlington\b|\bpickering\b|\bajax\b|\bwhitby\b|\boshawa\b|"
    r"\bmilton\b|\bnewmarket\b|\baurora\b"
)
ONTARIO = _c(r"\bontario\b|\b,\s*on\b|\bon,\s*canada\b|\b ON \b")
CANADA = _c(r"\bcanada\b|\bcanadian\b|\b,\s*ca\b")
REMOTE = _c(
    r"\bremote\b|\bwork from home\b|\bwfh\b|\bdistributed\b|\banywhere in\b|"
    r"\bfully remote\b|\btelework\b|\bt[ée]l[ée]travail\b|\bà distance\b|\ba distance\b"
)
HYBRID_ONSITE = _c(r"\bhybrid\b|\bon[- ]?site\b|\binsite\b|\boffice\b|\bin person\b|\bhybride\b")
GLOBAL = _c(r"\bglobal\b|\bworldwide\b|\binternational\b|\banywhere\b")
US_ONLY = _c(r"\bunited states\b|\busa\b|\bu\.s\.\b|\bus only\b|\bmust be in us\b")


def _text(job: dict) -> tuple[str, str, str]:
    title = str(job.get("title") or job.get("role") or "")
    body = " ".join(
        str(job.get(k) or "")
        for k in ("description", "body", "text", "snippet", "duties", "developer_evidence")
    )
    loc = " ".join(
        str(job.get(k) or "")
        for k in ("location", "location_summary", "geo_evidence", "city", "region", "country", "workplaceType", "mode")
    )
    return title, body, loc


def _is_negated(text: str, start: int, window: int = 50) -> bool:
    """Heuristic: nearby preceding negation cue (e.g. 'no Apex', 'without scripting').
    Conservative window to reduce false negatives; not a full NLP parse."""
    pre = text[max(0, start - window):start].lower()
    return bool(re.search(
        r"\b(?:no|not|without|never|don't|do not|does not|did not|cannot|can't|non[- ]|"
        r"rather than|instead of)\b[^.?!\n]{0,35}$",
        pre,
    ))


_NON_BUILD_TITLE = _c(
    r"\b(?:end[ -]?user\s+trainer|trainer|training\s+specialist|support\s+analyst|"
    r"help\s*desk|service\s*desk\s+(?:analyst|agent|technician)|reporting\s+analyst|"
    r"account\s+executive|sales\s+(?:representative|associate|executive))\b"
)
_NON_BUILD_EXPLICIT = _c(
    r"\bno\s+(?:scripting|development|developer|dev\b|admin(?:istrator)?\s+(?:configuration|changes|change)|"
    r"configuration\s+changes|coding|integrations?|apex|lwc|lightning\s+web\s+components?|custom\s+code)\b"
    r"|\b(?:no|without)\s+(?:any\s+)?(?:custom\s+)?(?:development|coding|scripting|apex|lwc|integrations?)\b"
    r"|\bend[ -]?user\s+(?:training|support)\b|\bsubmit\s+tickets\b|\breset\s+passwords?\b"
    r"|\bmanage\s+(?:pipeline|forecasts?)\b|\bno\s+development\s+duties\b"
    r"|\bdeclarative(?:-only)?\b[^\n.]{0,40}\b(?:admin|flows?|configuration)\b"
)
# Platform build/implementation artifacts/verbs (negation-aware). Generic "build reports/dashboards"
# and "configure users/permissions" are handled separately to avoid penalizing true non-build roles.
_BUILD_EVIDENCE = _c(
    r"\b(?:script\s+include|gliderecord|glideajax|business\s+rule|client\s+script|ui\s+policy|ui\s+action|"
    r"scoped\s+app|update\s+set|flow\s+designer|integrationhub|transform\s+map|mid\s+server|"
    r"apex|lwc|lightning\s+web\s+component|visualforce|soql|sosl|omnistudio|mulesoft|"
    r"implement(?:ation)?|develop(?:ment|er)?|engineer(?:ing)?|architect(?:ure)?|customiz(?:e|ation)|"
    r"integrat(?:e|ion|ions)|automation|discovery|service\s+mapping|cmdb\s+(?:integration|health|data\s+quality)|"
    r"scripted\s+rest|rest\s+api\s+integration)\b"
)
_BUILD_EVIDENCE_GENERIC = _c(
    r"\b(?:build|configure|create)\s+(?:applications?|apps?|modules?|workflows?|integrations?|scripts?|automations?|"
    r"scoped\s+apps?|business\s+rules?|client\s+scripts?|catalog\s+items?|flows?|pages?|components?)\b"
)


def _has_positive_match(pat: re.Pattern[str], text: str, window: int = 50) -> bool:
    for m in pat.finditer(text):
        if not _is_negated(text, m.start(), window=window):
            return True
    return False


def classify(job: dict) -> dict:
    title, body, loc = _text(job)
    tb = f"{title}\n{body}"
    reasons: list[str] = []
    tracks: dict[str, int] = {}
    for name, pats in TRACKS.items():
        score = 0
        hits: list[str] = []
        for p in pats["strong"]:
            m = p.search(title)
            if m and not _is_negated(title, m.start(), window=30):
                score += 3
                hits.append(f"title:{p.pattern}")
            else:
                m = p.search(body)
                if m and not _is_negated(body, m.start()):
                    score += 2
                    hits.append(f"body:{p.pattern}")
        for p in pats["medium"]:
            m = p.search(tb)
            if m and not _is_negated(tb, m.start()):
                score += 1
                hits.append(f"ctx:{p.pattern}")
        if score:
            tracks[name] = score
            reasons.extend(hits[:4])
    certs = [name for name, p in CERTS if p.search(tb)]
    if certs:
        reasons.append(f"certs:{','.join(certs)}")

    # Intent heuristic: downweight clear non-build/usage/support/training signals when
    # strong build evidence is absent. Conservative (keeps cert/build-backed cases).
    non_build_title = bool(_NON_BUILD_TITLE.search(title))
    non_build_explicit = bool(_NON_BUILD_EXPLICIT.search(tb))
    build_evidence = _has_positive_match(_BUILD_EVIDENCE, tb) or _has_positive_match(_BUILD_EVIDENCE_GENERIC, tb)
    if tracks and (non_build_title or non_build_explicit) and not build_evidence:
        if non_build_explicit:
            tracks.clear()
            reasons.append("intent:tracks_cleared_non_build_explicit")
        else:
            penalty = 2
            for k in list(tracks.keys()):
                tracks[k] = max(0, tracks[k] - penalty)
                if tracks[k] == 0:
                    del tracks[k]
            reasons.append(f"intent:non_build_penalty={penalty}")
            if not tracks:
                reasons.append("intent:tracks_cleared_non_build")

    # Taxonomy guard: Dynamics 365/Dataverse/CRM-only admin roles are not target SN/SF/ITSM-CMDB-ITAM
    # when there is no ServiceNow/Salesforce/platform-build/ITSM-ITAM-CMDB evidence.
    if tracks.get("Other") and re.search(r"\bdynamics\s*365\b|\bdataverse\b", tb, re.I):
        has_target_other = bool(re.search(r"\bitsm\b|\bitam\b|\bcmdb\b|\bitom\b|\bcsm\b|\bhrsd\b|\bsecops\b|\bgrc\b|\bham\b|\bsam\s*pro\b|\bconfiguration management\b|\bchange management\b|\bincident management\b|\bproblem management\b", tb, re.I))
        has_sn_sf = bool(tracks.get("ServiceNow") or tracks.get("Salesforce"))
        if not has_target_other and not has_sn_sf and not certs:
            # remove generic power-platform-only contribution
            if tracks.get("Other", 0) <= 4:
                del tracks["Other"]
                reasons.append("intent:dynamics_powerplatform_only_other_removed")
            else:
                tracks["Other"] = max(0, tracks["Other"] - 3)
                reasons.append("intent:dynamics_powerplatform_penalty=3")

    hay = f"{loc}\n{title}\n{body}"
    remote = bool(REMOTE.search(hay))
    toronto = bool(TORONTO_CORE.search(hay))
    gta = bool(GTA_CITIES.search(hay))
    ont = bool(ONTARIO.search(hay)) or toronto or gta
    canada = bool(CANADA.search(hay)) or ont
    hybrid = bool(HYBRID_ONSITE.search(hay))
    global_remote = bool(GLOBAL.search(hay)) and remote
    us_only = bool(US_ONLY.search(hay))

    # Explicit exclusion of Ontario for remote/Canada roles (target-scope ineligible, not US-only exclusion).
    ontario_excluded = bool(
        remote and canada and not toronto and not gta and re.search(
            r"\b(?:excluding|except|other than|outside(?: of)?|not\s+(?:available|eligible|open)(?:\s+to)?)\b[^.\n;]{0,60}\bontario\b"
            r"|\bontario\b[^.\n;]{0,30}\b(?:excluded|ineligible)\b",
            hay, re.I,
        )
    )
    # Positive Ontario-eligibility signals (distinct from "Ontario" appearing in an exclusion clause).
    ontario_positive = bool(
        toronto or gta
        or re.search(r"\bontario\s+residents?\s+only\b|\b(?:open|eligible|available)\s+to\s+[^.\n;]{0,40}\bontario\b|\bin\s+ontario\b|\bontario\b\s*(?:,|\b(?:accepted|eligible|preferred|required|based|remote)\b)", hay, re.I)
        or re.search(r"\b,\s*on\b|\bon,\s*canada\b|\b ON \b", hay)
    )
    ont_effective = (ontario_positive or ont) and not ontario_excluded

    # Treat French/explicit remote+Canada as Canada-remote signal even if province omitted.
    # Explicit Ontario exclusion makes it out-of-scope for Ontario-targeted remote matching.
    canada_remote_target = remote and canada and not us_only and not ontario_excluded
    canada_remote = canada_remote_target

    if toronto:
        geo_bucket = "Toronto"
    elif gta:
        geo_bucket = "GTA (non-Toronto core)"
    elif ontario_excluded and remote and canada and not us_only and not toronto and not gta:
        geo_bucket = "Remote (Canada, Ontario excluded)"
    elif canada_remote and ont_effective:
        geo_bucket = "Remote (Ontario/Canada-eligible signal)"
    elif canada_remote:
        geo_bucket = "Remote (Canada signal)"
    elif global_remote and not canada:
        geo_bucket = "Global remote — confirm Ontario eligibility"
    elif canada or ont:
        geo_bucket = "Canada/Ontario (unspecified locality)"
    else:
        geo_bucket = "Other/unknown"

    eligible = {
        "toronto_gta_local": toronto or gta,
        "canada_remote_signal": canada_remote,
        # Canada-remote roles are potentially Ontario-eligible unless explicitly constrained.
        "ontario_eligible_signal": ont_effective and not ontario_excluded,
        "needs_confirm": (global_remote and not canada) or (canada_remote and not ont_effective),
        "exclude_signal": us_only and not canada,
        "hybrid_or_onsite": hybrid,
    }
    if ontario_excluded and remote and canada and not toronto and not gta:
        reasons.append("geo:ontario_excluded_text")
    return {
        "tracks": tracks,
        "certs": certs,
        "geo_bucket": geo_bucket,
        "eligible": eligible,
        "reasons": reasons[:12],
    }


def iter_jobs(path: Path):
    data = path.read_text(encoding="utf-8")
    try:
        obj = json.loads(data)
        if isinstance(obj, list):
            yield from obj
            return
    except json.JSONDecodeError:
        pass
    for line in data.splitlines():
        line = line.strip()
        if line:
            yield json.loads(line)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", nargs="?", help="JSON/JSONL file of jobs (omit for demo)")
    ap.add_argument("--demo", action="store_true", help="run built-in demo samples")
    args = ap.parse_args()
    if args.demo or not args.input:
        jobs = [
            {
                "title": "ServiceNow Developer (ITSM/CMDB)",
                "location": "Toronto, ON (Hybrid)",
                "description": "Build Script Includes, GlideRecord integrations, Flow Designer. CSA/CAD preferred.",
            },
            {
                "title": "Salesforce Platform Engineer",
                "location": "Remote - Canada",
                "description": "Apex, LWC, SOQL, Sales Cloud. PD1 nice to have.",
            },
            {
                "title": "Integration Specialist",
                "location": "Mississauga, ON",
                "description": "ITAM/CMDB data integrations, Informatica, workflow automation.",
            },
            {
                "title": "Software Engineer",
                "location": "United States (Remote)",
                "description": "General backend role.",
            },
        ]
    else:
        jobs = list(iter_jobs(Path(args.input)))
    for job in jobs:
        out = dict(job)
        out["match"] = classify(job)
        print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
