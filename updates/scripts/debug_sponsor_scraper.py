#!/usr/bin/env python3
"""Scrape conference sponsors from ServiceNow and Salesforce Toronto 2026 events."""
import urllib.request, re, json, sys, time
from html.parser import HTMLParser

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
TIMEOUT = 15

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None

def save_html(html, name):
    """Save HTML to /tmp for inspection."""
    with open(f"/tmp/{name}.html", "w") as f:
        f.write(html)
    print(f"  Saved {name}.html ({len(html)}b)", file=sys.stderr)

# ── 1. ServiceNow: find literal sponsor names ──
print("=== ServiceNow World Forum Toronto 2026 ===", file=sys.stderr)
html_sn = fetch("https://reg.servicenow.com/flow/servicenow/wftoronto26/sponsorshowcase/page/sponsors")
if html_sn:
    save_html(html_sn, "servicenow_sponsors")
    # Look for any <script> with JSON data or API responses embedded
    # Also look for displayName patterns in the full HTML (not just JSON)
    for m in re.finditer(r'"displayName"\s*:\s*"([^"]+)"', html_sn):
        n = re.sub(r'\s+', ' ', m.group(1)).strip()
        if n and len(n) > 3:
            print(f"  displayName: {n}")
    # Look for any literal "name" : "CompanyName" in the page
    for m in re.finditer(r'(?:company|org|organization|sponsor)Name["\']?\s*:\s*["\']([^"\']+)["\']', html_sn, re.I):
        n = re.sub(r'\s+', ' ', m.group(1)).strip()
        if n and len(n) > 3:
            print(f"  orgName: {n}")
    # Look for underscore-escaped unicode strings
    for m in re.finditer(r'(?:display|company|org)[Nn]ame["\']?\s*:\s*["\']([^"\']+)["\']', html_sn):
        n = re.sub(r'\s+', ' ', m.group(1)).strip()
        if n and len(n) > 3:
            print(f"  escName: {n}")
    # Search the raw page for any JSON object that looks like it has sponsors
    for m in re.finditer(r'\{"id":\s*"[^"]+","displayName":', html_sn):
        start = m.start()
        depth, i = 0, start
        while i < min(start + 3000, len(html_sn)):
            if html_sn[i] == '{': depth += 1
            elif html_sn[i] == '}': depth -= 1
            if depth == 0:
                try:
                    obj = json.loads(html_sn[start:i+1])
                    dn = obj.get("displayName", "")
                    if dn and len(dn) > 3:
                        print(f"  JSON-sponsor: {dn}")
                except: pass
                break
            i += 1
    # Also look for the __NEXT_DATA__ or similar
    for m in re.finditer(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html_sn, re.DOTALL):
        print(f"  Found __NEXT_DATA__ ({len(m.group(1))}b)")
else:
    print("  FAILED to fetch ServiceNow page", file=sys.stderr)

# ── 2. Salesforce: find literal sponsor names ──
print("\n=== Salesforce World Tour Toronto 2026 ===", file=sys.stderr)
html_sf = fetch("https://reg.salesforce.com/flow/plus/wttoronto26may/sponsors/page/sponsorcatalog")
if html_sf:
    save_html(html_sf, "salesforce_sponsors")
    # Same pattern search
    for m in re.finditer(r'"displayName"\s*:\s*"([^"]+)"', html_sf):
        n = re.sub(r'\s+', ' ', m.group(1)).strip()
        if n and len(n) > 3:
            print(f"  displayName: {n}")
    for m in re.finditer(r'(?:company|org|organization|sponsor)[Nn]ame["\']?\s*:\s*["\']([^"\']+)["\']', html_sf, re.I):
        n = re.sub(r'\s+', ' ', m.group(1)).strip()
        if n and len(n) > 3:
            print(f"  orgName: {n}")
    for m in re.finditer(r'\{"id":\s*"[^"]+","displayName":', html_sf):
        start = m.start()
        depth, i = 0, start
        while i < min(start + 3000, len(html_sf)):
            if html_sf[i] == '{': depth += 1
            elif html_sf[i] == '}': depth -= 1
            if depth == 0:
                try:
                    obj = json.loads(html_sf[start:i+1])
                    dn = obj.get("displayName", "")
                    if dn and len(dn) > 3:
                        print(f"  JSON-sponsor: {dn}")
                except: pass
                break
            i += 1
    # Also check the FAQ page
    html_sf_faq = fetch("https://www.salesforce.com/events/world-tour/toronto/faq/")
    if html_sf_faq:
        save_html(html_sf_faq, "salesforce_faq")
        for m in re.finditer(r'(?:partner|sponsor|exhibitor)[^<]*?<a[^>]*>([^<]+)</a>', html_sf_faq, re.I):
            n = re.sub(r'\s+', ' ', m.group(1)).strip()
            if n and len(n) > 3:
                print(f"  FAQ-link: {n}")
else:
    print("  FAILED to fetch Salesforce page", file=sys.stderr)

# ── 3. Also try the ServiceNow FAQ/sponsor list page ──
print("\n=== ServiceNow (also checking /faq and other pages) ===", file=sys.stderr)
for alt_url in [
    "https://www.servicenow.com/events/world-forum/toronto.html",
    "https://www.servicenow.com/events/world-forum/toronto/sponsors",
]:
    html_alt = fetch(alt_url)
    if html_alt:
        print(f"  Fetched {alt_url} ({len(html_alt)}b)", file=sys.stderr)
        for m in re.finditer(r'(?:partner|sponsor|exhibitor)[^<]*?<a[^>]*>([^<]+)</a>', html_alt, re.I):
            n = re.sub(r'\s+', ' ', m.group(1)).strip()
            if n and len(n) > 3:
                print(f"  Link-text: {n}")
        for m in re.finditer(r'alt="([^"]*)"', html_alt):
            alt = m.group(1).strip()
            if alt and len(alt) > 3:
                print(f"  Image-alt: {alt}")
    else:
        print(f"  FAILED: {alt_url}", file=sys.stderr)

print("\nDone. Check /tmp/*.html for full pages.", file=sys.stderr)