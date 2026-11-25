#!/usr/bin/env python3
"""
Read-only phishing scan of every GitHub Pages site on an account.

Written for the 2026-11-25 incident, where a reCAPTCHA-gate phishing kit was found on the
50webs and GoDaddy shared-hosting docroots. This tool answers the follow-up question:
"did the kit reach GitHub Pages?" The 2026-11-25 run answered **no** (34 sites, 204 kit-path
probes, zero hits). Re-run it after any credential rotation or Pages change.

What it does, per site
  1. Fetches the site root, records status/final-URL/size/title.
  2. Greps the body for the kit IoCs (attacker domain, reCAPTCHA site keys, taunt marker, kit dirs).
  3. Greps for generic phishing/obfuscation smells (password input, external <form action>,
     meta-refresh, eval(atob(...)), seed-phrase / IBAN lures, wallet-connect).
  4. Probes the six kit paths (/de/, /de/index.php, /easyapp/index.php, /appeasy/index.php,
     /de/visit.txt, /de-de) - all must be 404 on Pages.
  5. Collects every host the page references, excluding github.io/github.com, so a reviewer can
     eyeball the egress list.

Requirements: `gh` authenticated as the account owner (or set OWNER to any account).
Usage:
    python3 tools/security/pages_phishing_scan.py                # all eltonaguiar Pages sites
    python3 tools/security/pages_phishing_scan.py --owner someone --json out.json
    python3 tools/security/pages_phishing_scan.py --urls urls.txt
Exit code: 0 = clean, 1 = at least one IoC hit or a non-404 kit path.

This script only reads. It never writes to GitHub and never uploads anything.
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (compatible; fte-pages-security-audit/1.0)"
CTX = ssl.create_default_context()

# IoCs from the 2026-11-25 kit (see updates/2026-11-25-phishing-kit-compromise.md)
IOC = [
    "oldyhub.com",
    "Off to the Mouse they go",
    "6LcPqy8uAAAAAH2Q1xna1sW7ZMUovgXxfwVTjl2D",
    "6LfVpC8uAAAAAEx69ILoPfTCng-Nb1hP9Gwfk4Cu",
    "appeasy",
    "easyapp",
]

KIT_PATHS = ("de/", "de/index.php", "easyapp/index.php", "appeasy/index.php",
             "de/visit.txt", "de-de")

GENERIC = {
    "eval_atob": r"eval\s*\(\s*(atob|unescape|decodeURIComponent)\s*\(",
    "fromcharcode": r"String\.fromCharCode\s*\(",
    "doc_write_unescape": r"document\.write\s*\(\s*unescape",
    "meta_refresh": r"<meta[^>]+http-equiv\s*=\s*['\"]?refresh",
    "pw_input": r"<input[^>]+type\s*=\s*['\"]?password",
    "iban_bic": r"\b(IBAN|BIC|TAN|Kartennummer|Kreditkarte|Sozialversicherung)\b",
    "crypto_seed": r"\b(seed phrase|recovery phrase|private key|12 words|seedphrase)\b",
    "wallet_connect": r"(walletconnect|connect ?wallet|metamask)",
    "external_form": r"<form[^>]+action\s*=\s*['\"]https?://",
}

# Hosts that are fine to see in the egress list (reviewers: extend deliberately, not blindly)
BENIGN_SUFFIX = ("github.io", "github.com", "githubusercontent.com")


def fetch(url: str, timeout: int = 25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.status, r.geturl(), r.read(400_000).decode("utf-8", "replace")


def gh_json(path: str):
    p = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        return None
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return None


def pages_urls(owner: str) -> list[str]:
    """Every Pages URL on the account, newest repos first."""
    repos, page = [], 1
    while True:
        batch = gh_json(f"user/repos?per_page=100&page={page}&affiliation=owner")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    urls = []
    for r in repos:
        if not r.get("has_pages"):
            continue
        info = gh_json(f"repos/{owner}/{r['name']}/pages") or {}
        if info.get("html_url"):
            urls.append(info["html_url"] if info["html_url"].endswith("/")
                        else info["html_url"] + "/")
    return sorted(set(urls))


def check(site: str) -> dict:
    rec = {"site": site, "status": None, "final": None, "size": 0, "title": "",
           "ioc": [], "gen": [], "ext_hosts": [], "kit_paths": {}, "err": None}
    try:
        st, final, body = fetch(site)
        rec.update(status=st, final=final, size=len(body))
        m = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
        if m:
            rec["title"] = re.sub(r"\s+", " ", m.group(1)).strip()[:90]
        low = body.lower()
        rec["ioc"] = [t for t in IOC if t.lower() in low]
        rec["gen"] = [n for n, pat in GENERIC.items() if re.search(pat, body, re.I)]
        hosts = set(re.findall(r"https?://([A-Za-z0-9._-]+)", body))
        rec["ext_hosts"] = sorted(h for h in hosts if not h.endswith(BENIGN_SUFFIX))[:12]
    except urllib.error.HTTPError as e:
        rec.update(status=e.code, err=f"HTTP {e.code}")
    except Exception as e:  # noqa: BLE001 - report, never raise
        rec.update(err=f"{type(e).__name__}: {str(e)[:60]}")

    for p in KIT_PATHS:
        try:
            st, _f, body = fetch(site.rstrip("/") + "/" + p, timeout=15)
            rec["kit_paths"][p] = f"{st}:{len(body)}"
            low = body.lower()
            for t in IOC:
                if t.lower() in low and t not in rec["ioc"]:
                    rec["ioc"].append(t)
        except urllib.error.HTTPError as e:
            rec["kit_paths"][p] = str(e.code)
        except Exception:  # noqa: BLE001
            rec["kit_paths"][p] = "ERR"
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only GitHub Pages phishing scan")
    ap.add_argument("--owner", default="eltonaguiar")
    ap.add_argument("--urls", help="file with one Pages URL per line (skips discovery)")
    ap.add_argument("--json", help="write full results here")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    sites = ([l.strip() for l in open(args.urls) if l.strip()]
             if args.urls else pages_urls(args.owner))
    if not sites:
        print("no Pages sites found", file=sys.stderr)
        return 1
    print(f"scanning {len(sites)} Pages site(s)\n")

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for r in ex.map(check, sites):
            results.append(r)
            bad = r["ioc"] or any(not v.startswith("404") for v in r["kit_paths"].values())
            print(f"{'!!!' if bad else '   '} {str(r['status']):>4} {r['size']:>7}B "
                  f"{r['site'][:60]:<60} ioc={r['ioc']} gen={r['gen']}")
            if r["err"]:
                print(f"      err: {r['err']}")

    hits = [r for r in results
            if r["ioc"] or any(not v.startswith("404") for v in r["kit_paths"].values())]
    print(f"\n=== {len(results)} sites, {len(hits)} with kit indicators ===")
    for r in hits:
        live = {k: v for k, v in r["kit_paths"].items() if not v.startswith("404")}
        print(f"  {r['site']}  ioc={r['ioc']} kit_paths={live}")

    if args.json:
        json.dump(results, open(args.json, "w"), indent=1)
        print(f"full results -> {args.json}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
