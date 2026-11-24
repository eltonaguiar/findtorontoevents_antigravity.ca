#!/usr/bin/env python3
"""Scrape two conference sponsor directories using Playwright for SPA rendering.

Conferences:
  1. ServiceNow World Forum Toronto 2026 (RainFocus on reg.servicenow.com)
  2. Salesforce World Tour Toronto 2026   (RainFocus on reg.salesforce.com)

Output: CSV to stdout with columns:
  sponsor_name,conference,website,careers_url,ats_type,classification
"""

import csv
import re
import sys
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

TIMEOUT = 30000  # 30 s page-level timeout

# ── Known ATS detection patterns ─────────────────────────────────────────

ATS_PATTERNS = {
    "Workday": [
        re.compile(r"\.myworkdayjobs\.com", re.I),
        re.compile(r"workday\.com.*career", re.I),
        re.compile(r"myworkdayjobs", re.I),
        re.compile(r"wd5\.myworkdayjobs", re.I),
    ],
    "Greenhouse": [
        re.compile(r"greenhouse\.io", re.I),
        re.compile(r"boards\.greenhouse\.io", re.I),
        re.compile(r"app\.greenhouse\.io", re.I),
    ],
    "Lever": [
        re.compile(r"lever\.co", re.I),
        re.compile(r"jobs\.lever\.co", re.I),
    ],
    "Ashby": [
        re.compile(r"ashbyhq\.com", re.I),
        re.compile(r"jobs\.ashbyhq\.com", re.I),
    ],
    "SmartRecruiters": [
        re.compile(r"smartrecruiters\.com", re.I),
    ],
    "BambooHR": [
        re.compile(r"bamboohr\.com", re.I),
        re.compile(r"bamboohr\.com/jobs", re.I),
    ],
    "ICIMS": [
        re.compile(r"icims\.com", re.I),
    ],
    "JazzHR": [
        re.compile(r"jazzhr\.com", re.I),
    ],
}

# ── Classification patterns ──────────────────────────────────────────────

SI_KEYWORDS = re.compile(
    r"\b(consulting|consultants|accenture|deloitte|infosys|tcs?|tata consult|"
    r"wipro|capgemini|cognizant|ibm|hcl|tech[-\s]?mahindra|"
    r"at\s?os|atos|doxa|dls\s?technology|systems\s?integrator|"
    r"avendata|fusion\s?consulting|resultant|bilot|"
    r"cloud\s?reach|crest\s?data|fpt\s?software|"
    r"glen\s?systems|hyland|kainos|keyrus|"
    r"leaven\s?digital|lumen\s?technologies|mavim|"
    r"metri\s?tech|neoris|nortal|pwc|"
    r"r stahl|rws|sauron|sirius|sirion|"
    r"sogeti|softserve|spinnaker|squirro|"
    r"sungard|syntax|tcs|think|thomson\s?reuters|"
    r"tietoevry|trianz|tx\s?systems|ust|"
    r"valorem\s?reply|veritis|virtusa|wolters\s?kluwer)\b",
    re.I,
)

ISV_KEYWORDS = re.compile(
    r"\b(software|solutions|platform|saas|cloud|"
    r"servicenow|salesforce|microsoft|google|amazon|aws|"
    r"oracle|sap|adobe|splunk|datadog|new\s?relic|"
    r"elastic|mongo|snowflake|databricks|"
    r"celonis|ui\s?path|automation\s?anywhere|"
    r"docusign|box|dropbox|slack|jira|"
    r"mulesoft|tableau|power\s?bi|talend)\b",
    re.I,
)

ENDUSER_KEYWORDS = re.compile(
    r"\b(bank|insurance|hospital|healthcare|retail|manufacturing|"
    r"university|college|school|government|ministry|"
    r"energy|telecom|utility|airline|transport|"
    r"toronto|canada|ontario|city|region|municipal)\b",
    re.I,
)


# ── Playwright helpers ───────────────────────────────────────────────────


def new_page(pw):
    """Create a configured Playwright page."""
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent=USER_AGENT,
        viewport={"width": 1280, "height": 900},
        locale="en-US",
        timezone_id="America/Toronto",
    )
    page = context.new_page()
    page.set_default_timeout(TIMEOUT)
    return browser, page


SPONSOR_SELECTORS = [
    # RainFocus / common grid patterns
    "div[class*='sponsor']",
    "div[class*='exhibitor']",
    "div[class*='company']",
    "div[class*='grid'] a",
    "div[class*='card']",
    "li[class*='sponsor']",
    "li[class*='exhibitor']",
    "li[class*='partner']",
    "section[class*='sponsor']",
    "section[class*='exhibitor']",
    # Generic tile / booth
    "a[class*='sponsor']",
    "a[class*='booth']",
    "img[class*='sponsor']",
    "img[class*='logo']",
    "span[class*='sponsor']",
    "span[class*='exhibitor']",
]

TEXT_SELECTORS = [
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p",
    "li",
    "a",
    "span",
    "div",
]


def extract_sponsors_from_page(page, url: str) -> set:
    """Load a URL with Playwright, wait for render, and extract sponsor names."""
    sponsors = set()
    try:
        page.goto(url, wait_until="networkidle", timeout=TIMEOUT)
    except PWTimeout:
        pass  # Continue even if timeout — some RainFocus pages are slow

    # 1. Try specific sponsor containers first
    for sel in SPONSOR_SELECTORS:
        try:
            elements = page.query_selector_all(sel)
            for el in elements:
                text = el.inner_text().strip()
                if text and len(text) > 2:
                    sponsors.update(_split_names(text))
        except Exception:
            continue

    # 2. Try selecting sponsor-related heading/text containers
    sponsors.update(_text_search(page, "sponsor"))
    sponsors.update(_text_search(page, "exhibitor"))

    # 3. Text-content search for "sponsors" section (fallback)
    body_text = page.evaluate("document.body.innerText")
    for line in body_text.split("\n"):
        line = line.strip()
        if re.search(r"(sponsor|exhibitor|partner)", line, re.I):
            sponsors.update(_split_names(line))

    # 4. Alt-text from images
    try:
        imgs = page.query_selector_all("img[alt]")
        for img in imgs:
            alt = (img.get_attribute("alt") or "").strip()
            if alt and len(alt) > 2 and re.search(r"(sponsor|exhibitor|partner|logo)", alt, re.I):
                sponsors.add(normalize_sponsor_name(alt))
    except Exception:
        pass

    return sponsors


def _text_search(page, keyword: str) -> set:
    """Search rendered DOM for elements whose class/id/text contains keyword."""
    results = set()
    for sel in TEXT_SELECTORS:
        try:
            elements = page.query_selector_all(sel)
            for el in elements:
                outer = (el.get_attribute("class") or "") + " " + (el.get_attribute("id") or "")
                if not re.search(keyword, outer, re.I):
                    continue
                text = el.inner_text().strip()
                if text and len(text) > 2:
                    results.update(_split_names(text))
        except Exception:
            continue
    return results


def _split_names(text: str) -> list:
    """Split multi-line/pipe-separated text into individual company names."""
    names = []
    for line in text.split("\n"):
        for part in re.split(r"[•·–—\-|,*]{2,}", line):
            name = normalize_sponsor_name(part)
            if name and len(name) > 2 and not _is_noise(name):
                names.append(name)
    return names


NOISE_WORDS = {
    "sponsors", "sponsor", "exhibitors", "exhibitor", "partners", "partner",
    "gold", "silver", "bronze", "platinum", "media", "community",
    "showcase", "booth", "learn more", "register", "agenda", "speakers",
    "faq", "contact", "title", "presenting", "sponsor catalog",
    "home", "about", "login", "sign in", "sign up", "logout",
    "search", "filter", "sort by", "all", "view all",
}


def _is_noise(name: str) -> bool:
    lower = name.lower().strip(".,;:!?'\"")
    return lower in NOISE_WORDS or re.match(r"^[-–—=]+$", lower)


def normalize_sponsor_name(name: str) -> str:
    """Clean up sponsor names."""
    name = re.sub(r"\s+", " ", name).strip()
    name = re.sub(r"^[•·–—\-|,*\s]+", "", name)
    name = re.sub(r"[•·–—\-|,*\s]+$", "", name)
    name = name.strip(".,;:!?'\"")
    return name.strip()


# ── HTTP helpers (for careers/website probes) ────────────────────────────


def fetch(url: str) -> str | None:
    """Fetch a URL and return its text content, or None on error."""
    import urllib.request
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, OSError, ConnectionError, UnicodeError):
        return None


def idna_safe(domain: str) -> str:
    """Encode a domain for IDNA, returning fallback on failure."""
    try:
        return domain.encode("idna").decode("ascii")
    except (UnicodeError, UnicodeEncodeError):
        # Strip non-ASCII characters and retry
        ascii_only = re.sub(r"[^\x00-\x7f]", "", domain)
        if ascii_only:
            try:
                return ascii_only.encode("idna").decode("ascii")
            except (UnicodeError, UnicodeEncodeError):
                pass
        return domain  # best-effort


def guess_website(sponsor: str) -> str | None:
    """Guess a company website from its name using a simple heuristic."""
    clean = re.sub(r"[^a-zA-Z0-9 ]+", "", sponsor).strip().lower()
    domain = clean.replace(" ", "").replace("-", "")
    if not domain:
        return None
    domain = idna_safe(domain)
    url = f"https://www.{domain}.com"
    if fetch(url):
        return url
    domain_h = idna_safe(clean.replace(" ", "-"))
    url_h = f"https://www.{domain_h}.com"
    if url_h != url and fetch(url_h):
        return url_h
    return f"https://www.{domain}.com"


def check_careers_url(url: str) -> str | None:
    if not url:
        return None
    if fetch(url):
        return url
    return None


def guess_careers_urls(website: str | None, sponsor: str) -> list[str]:
    candidates = []
    if website:
        domain = urlparse(website).netloc
        for path in ("/careers", "/jobs", "/careers/jobs", "/join-us", "/about-us/careers"):
            candidates.append(f"https://{domain}{path}")
        candidates.append(f"https://careers.{domain}")
        candidates.append(f"https://jobs.{domain}")
    return candidates


def detect_ats(urls: list[str]) -> tuple[str | None, str | None]:
    for url in urls:
        html = fetch(url)
        if html is None:
            continue
        for ats, patterns in ATS_PATTERNS.items():
            if any(p.search(html) for p in patterns):
                return url, ats
        if re.search(r"career|job|position|open.?ing|apply|hiring", html, re.I):
            return url, "Unknown"
    return (None, None)


def classify(sponsor: str, website: str | None) -> str:
    combined = f"{sponsor} {website or ''}"
    if SI_KEYWORDS.search(combined):
        return "SI"
    if ISV_KEYWORDS.search(combined):
        return "ISV"
    if ENDUSER_KEYWORDS.search(combined):
        return "EndUser"
    return "Unknown"


# ── Scraper per conference ───────────────────────────────────────────────


def scrape_servicenow(pw) -> list[dict]:
    results = []
    sponsors = set()

    url = (
        "https://reg.servicenow.com/flow/servicenow/wftoronto26/"
        "sponsorshowcase/page/sponsors"
    )
    browser, page = new_page(pw)
    try:
        sponsors = extract_sponsors_from_page(page, url)
        # Also try the event main page
        try:
            page2 = page.context.new_page()
            s2 = extract_sponsors_from_page(
                page2,
                "https://www.servicenow.com/events/world-forum/toronto.html",
            )
            sponsors.update(s2)
            page2.close()
        except Exception:
            pass
    finally:
        browser.close()

    for s in sorted(sponsors):
        website = guess_website(s)
        careers_candidates = guess_careers_urls(website, s)
        careers_url, ats_type = detect_ats(careers_candidates)
        classification = classify(s, website)
        results.append({
            "sponsor_name": s,
            "conference": "ServiceNow World Forum Toronto 2026",
            "website": website or "",
            "careers_url": careers_url or "",
            "ats_type": ats_type or "",
            "classification": classification,
        })
    return results


def scrape_salesforce(pw) -> list[dict]:
    results = []
    sponsors = set()

    url = (
        "https://reg.salesforce.com/flow/plus/wttoronto26may/"
        "sponsors/page/sponsorcatalog"
    )
    browser, page = new_page(pw)
    try:
        sponsors = extract_sponsors_from_page(page, url)
        # Also try the event FAQ page
        try:
            page2 = page.context.new_page()
            s2 = extract_sponsors_from_page(
                page2,
                "https://www.salesforce.com/events/world-tour/toronto/faq/",
            )
            sponsors.update(s2)
            page2.close()
        except Exception:
            pass
    finally:
        browser.close()

    for s in sorted(sponsors):
        website = guess_website(s)
        careers_candidates = guess_careers_urls(website, s)
        careers_url, ats_type = detect_ats(careers_candidates)
        classification = classify(s, website)
        results.append({
            "sponsor_name": s,
            "conference": "Salesforce World Tour Toronto 2026",
            "website": website or "",
            "careers_url": careers_url or "",
            "ats_type": ats_type or "",
            "classification": classification,
        })
    return results


# ── Main ─────────────────────────────────────────────────────────────────


def main():
    all_sponsors = []

    with sync_playwright() as pw:
        all_sponsors.extend(scrape_servicenow(pw))
        all_sponsors.extend(scrape_salesforce(pw))

    if not all_sponsors:
        print("# No sponsors found — URLs may require authentication", file=sys.stderr)
        return

    writer = csv.DictWriter(
        sys.stdout,
        fieldnames=[
            "sponsor_name",
            "conference",
            "website",
            "careers_url",
            "ats_type",
            "classification",
        ],
    )
    writer.writeheader()
    writer.writerows(all_sponsors)


if __name__ == "__main__":
    main()