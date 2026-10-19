#!/usr/bin/env python3
"""
job_search.py — find live job postings with links via the local Ollama stack.

Answers requests like:
  "find the latest ServiceNow developer jobs in Toronto"
  "fully-remote Canadian ServiceNow jobs"
  "Salesforce jobs, including Toronto on-site"

Pipeline:
  1. expand the request into several web-search queries
  2. run them through the LOCAL Ollama web-search API (no API key, $0)
  3. dedupe by URL, drop obviously non-matching locations
  4. optionally have a local model rank/summarise (--no-llm to skip)

Usage
-----
  python3 tools/job_search.py --role "ServiceNow Developer" --location "Toronto, ON"
  python3 tools/job_search.py --role "ServiceNow Developer" --remote-ca
  python3 tools/job_search.py --role "Salesforce Developer" --location "Toronto, ON" --include-remote
  python3 tools/job_search.py --role "ServiceNow" --role "Salesforce" --remote-ca --json

Notes
-----
* Search backend: POST http://localhost:11434/api/experimental/web_search
  (the endpoint is /api/experimental/, NOT /api/web_search which 404s)
* Job boards are noisy: results are returned verbatim with their URLs so the
  human can verify. NEVER invent a posting or a link.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict

OLLAMA = "http://localhost:11434"
SEARCH_ENDPOINT = "/api/experimental/web_search"
DEFAULT_MODEL = "qwen3.5:35b-a3b"

# Boards that produce real, linkable postings. Used only for ranking, never filtering.
GOOD_BOARDS = (
    "workdayjobs", "myworkdayjobs", "ashbyhq.com", "greenhouse.io", "lever.co",
    "smartrecruiters", "bamboohr", "icims", "linkedin.com/jobs", "indeed.",
    "emploive", "jobsca", "jobbank.gc.ca", "jobs.ashbyhq", "wellfound",
)
# Signals an item is plausibly in scope.
CA_SIGNALS = ("toronto", "ontario", "canada", "canadian", "remote", "on, can", "on-site", "hybrid")
# Ad / redirect URLs -> always dropped, they are never the posting.
AD_URL_MARKERS = ("bing.com/aclick", "googleadservices", "doubleclick.net", "adclick")
# Aggregator SEARCH/LISTING pages: useful to a human, but not an individual posting.
# Generic search backends (DuckDuckGo) surface these far more often than the Ollama
# web search, so they get down-ranked rather than dropped.
AGGREGATOR_HINTS = ("ziprecruiter.com/jobs/", "simplyhired.ca/search", "workopolis.com/search",
                    "indeed.com/q-", "jobbank.gc.ca/jobsearch/jobsearch")
# Clearly outside Canada -> dropped when the request is Canadian.
NON_CA = ("usa", "united states", "u.s.", "texas", "boston", "austin", "new york",
          "seattle", "chicago", "san francisco", "california", "atlanta", "denver",
          "united kingdom", "london, uk", "india", "bangalore", "singapore",
          "dublin", "berlin", "paris", "sydney", "tokyo")
# Canadian, but not the requested city -> kept, ranked lower.
OTHER_CA_CITIES = ("montreal", "ottawa", "vancouver", "calgary", "edmonton", "winnipeg",
                   "halifax", "quebec", "waterloo", "mississauga", "markham", "vaughan",
                   "brampton", "kitchener", "victoria", "saskatoon", "regina")


@dataclass
class Posting:
    title: str
    url: str
    company: str = ""
    location: str = ""
    posted: str = ""
    snippet: str = ""
    queries: list[str] = field(default_factory=list)
    score: int = 0

    def key(self) -> str:
        u = (self.url or "").split("?")[0].rstrip("/").lower()
        return re.sub(r"/(application|apply)$", "", u)


# --------------------------------------------------------------------------
def _post(path: str, payload: dict, timeout: int = 90) -> dict:
    req = urllib.request.Request(
        OLLAMA + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _search_ollama(query: str, max_results: int, retries: int = 3) -> list[dict] | None:
    """Primary backend: the local Ollama daemon's web search. None = unavailable."""
    for attempt in range(retries):
        try:
            d = _post(SEARCH_ENDPOINT, {"query": query, "max_results": max_results}, timeout=90)
            return d.get("results", []) or []
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries - 1:
                wait = 15 * (attempt + 1)
                print(f"  ! ollama 429 on {query!r}; retrying in {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            print(f"  ! ollama backend failed for {query!r}: HTTP {exc.code}", file=sys.stderr)
            return None
        except Exception as exc:  # noqa: BLE001
            print(f"  ! ollama backend failed for {query!r}: {str(exc)[:100]}", file=sys.stderr)
            return None
    return None


def _search_ddgs(query: str, max_results: int) -> list[dict] | None:
    """Fallback backend: DuckDuckGo via the keyless `ddgs` library.

    Install with:  .venv/bin/python -m pip install ddgs
    """
    try:
        from ddgs import DDGS  # type: ignore
    except Exception:
        try:
            from duckduckgo_search import DDGS  # type: ignore
        except Exception:
            return None
    try:
        out: list[dict] = []
        for r in DDGS().text(query, max_results=max_results):
            url = r.get("href") or r.get("url") or ""
            if not url:
                continue
            out.append({
                "title": r.get("title", ""),
                "url": url,
                "content": r.get("body") or r.get("snippet") or "",
            })
        return out
    except Exception as exc:  # noqa: BLE001
        print(f"  ! ddgs failed for {query!r}: {str(exc)[:100]}", file=sys.stderr)
        return None


BACKENDS = ("ollama", "ddgs")


def web_search(query: str, max_results: int = 10, backend: str = "auto") -> list[dict]:
    """Search with automatic failover: ollama -> ddgs.

    A single backend is a single point of failure (the Ollama web-search API
    rate-limits under load), so `auto` tries each in order and returns the
    first non-empty result set.
    """
    order = BACKENDS if backend == "auto" else (backend,)
    for name in order:
        res = _search_ollama(query, max_results) if name == "ollama" else _search_ddgs(query, max_results)
        if res:
            return res
        if res is None and name == "ddgs":
            print("  ! ddgs unavailable — install it: .venv/bin/python -m pip install ddgs",
                  file=sys.stderr)
    return []


def build_queries(roles: list[str], location: str | None, remote_ca: bool,
                  include_remote: bool, extra: list[str]) -> list[str]:
    qs: list[str] = []
    for role in roles:
        if location:
            qs.append(f"{role} jobs {location} hiring")
            qs.append(f"{role} jobs {location} site:workdayjobs.com OR site:ashbyhq.com")
        if remote_ca:
            qs.append(f"remote {role} jobs Canada hiring")
            qs.append(f"fully remote {role} job Canada work from home")
        if include_remote and location:
            qs.append(f"remote {role} jobs Canada")
        if not location and not remote_ca:
            qs.append(f"{role} jobs Toronto Ontario Canada hiring")
    qs.extend(extra)
    seen, out = set(), []
    for q in qs:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out


def _first(patterns: list[str], text: str) -> str:
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return m.group(1).strip(" *#|\n\t")
    return ""


def parse_posting(raw: dict, query: str, require_ca: bool) -> Posting | None:
    """Turn a raw search hit into a Posting, or None if clearly out of scope."""
    title = (raw.get("title") or "").strip()
    url = (raw.get("url") or "").strip()
    content = str(raw.get("content") or "")
    if not url:
        return None
    if any(m in url.lower() for m in AD_URL_MARKERS):
        return None

    blob = f"{title}\n{content}".lower()
    if require_ca and not any(s in blob for s in CA_SIGNALS):
        # location unknown AND no Canadian signal -> keep, but flag low
        pass

    company = _first([r"\bat\s+([A-Z][\w&.\-']+(?:\s+[A-Z][\w&.\-']+){0,3})"], title)
    if not company:
        company = _first([r"\*\*Company:\*\*\s*([^\n|]+)", r"\bCompany:\s*([^\n|]+)"], content)
    location = _first(
        [r"\*\*Location:\*\*\s*([^\n|]+)", r"\bLocation:\s*([^\n|]+)",
         r"\b(Toronto,\s*ON[^\n|,]*)", r"\b(Remote[^\n|,]{0,20})"],
        content,
    )
    posted = _first([r"\*\*Published:\*\*\s*([0-9]{4}-[0-9]{2}-[0-9]{2})",
                     r"\b(20[0-9]{2}-[0-9]{2}-[0-9]{2})\b"], content)

    p = Posting(title=title, url=url, company=company, location=location,
                posted=posted, snippet=re.sub(r"\s+", " ", content)[:240], queries=[query])

    score = 0
    if any(b in url.lower() for b in GOOD_BOARDS):
        score += 3            # real ATS/board link
    if location and ("toronto" in location.lower() or "ontario" in location.lower()):
        score += 4
    if "canada" in blob:
        score += 2
    if "remote" in blob:
        score += 1
    if posted:
        score += 2
    if re.search(r"\b(servicenow|salesforce)\b", blob):
        score += 3
    if "toronto" in blob:
        score += 3
    # de-rank other Canadian cities unless the role is remote
    if any(c in blob for c in OTHER_CA_CITIES) and "remote" not in blob:
        score -= 5
    # listing/search pages are not individual postings -> rank below them
    if is_search_page(url):
        score -= 4
    p.score = score
    return p


def is_search_page(url: str) -> bool:
    """True for aggregator SEARCH pages rather than an individual posting."""
    low = url.lower()
    if "/search" in low or "?q=" in low or "&q=" in low:
        return True
    if any(h in low for h in AGGREGATOR_HINTS):
        return True
    return re.search(r"/jobs/[a-z0-9-]+-jobs-", low) is not None


# Words that describe a level/shape of job rather than a product family.
GENERIC_ROLE_WORDS = {
    "developer", "engineer", "consultant", "senior", "junior", "lead", "analyst",
    "specialist", "manager", "architect", "administrator", "admin", "dev", "sr", "jr",
    "remote", "jobs", "job", "full", "time", "part", "and", "the", "for",
}


def required_terms(roles: list[str]) -> set[str]:
    """Distinctive product/family tokens, e.g. {"servicenow"} from "ServiceNow Developer"."""
    terms: set[str] = set()
    for role in roles:
        for tok in re.findall(r"[a-z0-9]+", role.lower()):
            if len(tok) > 2 and tok not in GENERIC_ROLE_WORDS:
                terms.add(tok)
    return terms


def missing_role(p: Posting, terms: set[str]) -> bool:
    """True when the posting never mentions the requested role family at all."""
    if not terms:
        return False
    hay = f"{p.title} {p.snippet} {p.url}".lower().replace(" ", "")
    return not any(t in hay for t in terms)


def out_of_scope(p: Posting, requested_location: str | None) -> bool:
    """True when the posting is clearly outside the requested country."""
    if not requested_location:
        return False
    wants_ca = any(t in requested_location.lower()
                   for t in ("toronto", "ontario", "canada", "quebec", "british columbia"))
    if not wants_ca:
        return False
    hay = f"{p.location} {p.title} {p.snippet}".lower()
    if any(t in hay for t in NON_CA) and not any(t in hay for t in ("canada", "canadian")):
        return True
    return False


# --------------------------------------------------------------------------
# Link validation — actually fetch each URL. A posting is only "verified" if
# the page loads AND its text matches the title/company we were given.
# --------------------------------------------------------------------------
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def validate(p: Posting, timeout: int = 20) -> tuple[str, str]:
    """Return (verdict, detail). Verdicts: VERIFIED / REACHABLE / BLOCKED / DEAD / ERROR."""
    req = urllib.request.Request(p.url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-CA,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(500_000).decode("utf-8", "replace")
            status = resp.getcode()
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 429, 999):
            return "BLOCKED", f"HTTP {exc.code} bot-protection — cannot verify programmatically"
        if exc.code in (404, 410):
            return "DEAD", f"HTTP {exc.code} — posting removed"
        return "ERROR", f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return "ERROR", str(exc)[:80]

    low = body.lower()
    toks = [t for t in re.findall(r"[a-z]{4,}", p.title.lower())][:8]
    hits = sum(1 for t in toks if t in low)
    comp_ok = bool(p.company) and p.company.split()[0].lower() in low
    if comp_ok or hits >= 3:
        return "VERIFIED", f"HTTP {status}; title-tokens {hits}/{len(toks)}; company-match={comp_ok}"
    return "REACHABLE", f"HTTP {status}; no title match (JS-rendered or generic page)"


def print_validation(postings: list[Posting]) -> None:
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=6) as pool:
        verdicts = list(pool.map(validate, postings))
    print("\n### Link validation (each URL fetched live)\n")
    print("| Verdict | HTTP/Detail | Job | URL |")
    print("|---|---|---|---|")
    counts: dict[str, int] = {}
    for p, (verdict, detail) in zip(postings, verdicts):
        counts[verdict] = counts.get(verdict, 0) + 1
        print(f"| {verdict} | {detail} | {p.title[:55]} | {p.url} |")
    print(f"\n**Summary:** " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))


def print_raw_urls(postings: list[Posting]) -> None:
    print("\n### Raw URLs (copy/paste to check yourself)\n```")
    for p in postings:
        print(p.url)
    print("```")


def synthesise(postings: list[Posting], roles: list[str], scope: str, model: str) -> str:
    """Ask a local model to present the verified list. Falls back to plain markdown."""
    listing = "\n".join(
        f"- {p.title} | {p.company or '?'} | {p.location or '?'} | {p.posted or '?'} | {p.url}"
        for p in postings[:25]
    )
    prompt = (
        f"Below are job postings found by web search for: {', '.join(roles)} / {scope}.\n"
        "Produce a markdown table with columns: Job Title | Company | Location | Posted | URL.\n"
        "RULES: use ONLY the rows given; NEVER invent a job or URL; keep URLs exact; "
        "if a field is unknown write '?'. Order with most recent first, then by relevance.\n\n"
        f"{listing}"
    )
    try:
        out = _post("/api/chat", {
            "model": model, "stream": False,
            "messages": [{"role": "user", "content": prompt}],
            "options": {"num_predict": 1200, "temperature": 0.2},
        }, timeout=600)
        return out["message"]["content"]
    except Exception as exc:  # noqa: BLE001
        print(f"  ! model synthesis failed ({str(exc)[:90]}); emitting raw table", file=sys.stderr)
        return ""


def render_table(postings: list[Posting]) -> str:
    rows = ["| Job Title | Company | Location | Posted | URL |", "|---|---|---|---|---|"]
    for p in postings:
        rows.append(f"| {p.title[:70]} | {p.company or '?'} | {p.location or '?'} | "
                    f"{p.posted or '?'} | {p.url} |")
    return "\n".join(rows)


# --------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Find live job postings with links (local Ollama stack).")
    ap.add_argument("--role", "-r", action="append", required=True,
                    help="role keyword, repeatable (e.g. -r 'ServiceNow Developer' -r 'Salesforce Developer')")
    ap.add_argument("--location", "-l", default="Toronto, ON",
                    help="location string (default 'Toronto, ON'); use '' for none")
    ap.add_argument("--remote-ca", action="store_true", help="also search fully-remote Canadian roles")
    ap.add_argument("--include-remote", action="store_true", help="include remote alongside a location")
    ap.add_argument("--extra-query", action="append", default=[], help="extra search query")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model (default {DEFAULT_MODEL})")
    ap.add_argument("--max-results", type=int, default=10, help="results per query")
    ap.add_argument("--limit", type=int, default=25, help="max postings to report")
    ap.add_argument("--no-role-filter", action="store_true",
                    help="keep postings that never mention the role family (e.g. ServiceNow)")
    ap.add_argument("--search-backend", choices=("auto",) + BACKENDS, default="auto",
                    help="auto (default) tries ollama then ddgs; or force one explicitly")
    ap.add_argument("--no-llm", action="store_true", help="skip model synthesis, print raw table")
    ap.add_argument("--validate", action="store_true",
                    help="fetch every URL and report VERIFIED/REACHABLE/BLOCKED/DEAD")
    ap.add_argument("--raw-urls", action="store_true", help="append a plain URL list")
    ap.add_argument("--out", help="also write the markdown report to this file")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    args = ap.parse_args(argv)

    location = args.location or None
    scope_bits = []
    if location:
        scope_bits.append(location)
    if args.remote_ca:
        scope_bits.append("fully-remote Canada")
    scope = " + ".join(scope_bits) or "Canada"

    queries = build_queries(args.role, location, args.remote_ca, args.include_remote, args.extra_query)
    print(f"[job_search] roles={args.role} scope={scope}", file=sys.stderr)
    print(f"[job_search] running {len(queries)} queries...", file=sys.stderr)

    by_key: dict[str, Posting] = {}
    for q in queries:
        for raw in web_search(q, args.max_results, backend=args.search_backend):
            p = parse_posting(raw, q, require_ca=bool(location or args.remote_ca))
            if not p:
                continue
            if p.key() in by_key:
                by_key[p.key()].queries.extend(p.queries)
            else:
                by_key[p.key()] = p

    postings = [p for p in by_key.values() if not out_of_scope(p, location)]
    if not args.no_role_filter:
        terms = required_terms(args.role)
        kept = [p for p in postings if not missing_role(p, terms)]
        dropped = len(postings) - len(kept)
        if dropped:
            print(f"[job_search] dropped {dropped} posting(s) that never mention {sorted(terms)}",
                  file=sys.stderr)
        postings = kept
    postings = sorted(postings, key=lambda p: (p.score, p.posted or ""), reverse=True)[: args.limit]

    if not postings:
        print("[job_search] no postings found — check that Ollama is running and the "
              "web-search endpoint works.", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"roles": args.role, "scope": scope,
                          "postings": [asdict(p) for p in postings]}, indent=2))
        return 0

    header = (f"## {', '.join(args.role)} — {scope}\n\n"
              f"_Found {len(postings)} postings via local web search on "
              f"{__import__('datetime').date.today().isoformat()}._\n")
    if args.no_llm:
        report = header + "\n" + render_table(postings)
    else:
        body = synthesise(postings, args.role, scope, args.model)
        report = header + "\n" + (body if body and "|" in body else render_table(postings))

    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print(report)
        if args.validate:
            print_validation(postings)
        if args.raw_urls:
            print_raw_urls(postings)
        print("\n<!-- verify every URL before relying on it; postings expire quickly -->")
    out = buf.getvalue()
    print(out)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out)
        print(f"[job_search] wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
