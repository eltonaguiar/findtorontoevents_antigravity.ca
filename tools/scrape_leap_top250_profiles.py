"""Serial TradingView profile scraper for Leap Crypto May 2026 top-250.

NOT a swarm. Rate-limited one-at-a-time per user directive (2026-05-13):
"we cant use swarms for tradingview the traffic would be blocked, do it 1 by 1".

Pipeline:
  1. Read reports/data/leap_top250_leaderboard_2026-05-13.json
  2. For each trader, fetch profile + ideas + scripts pages via scrapling
     StealthyFetcher (camoufox stealth + Cloudflare solver).
  3. Persist raw HTML + parsed JSON to reports/data/leap_profiles_*.
  4. Random 5-15s delay between profiles.
  5. Skip on resume if parsed JSON exists and --force not passed.

Optional env:
  HTTP_PROXY / HTTPS_PROXY  proxy URL forwarded to scrapling
  LEAP_START_RANK / LEAP_END_RANK  filter to slice (e.g., 16-100)
  LEAP_SCRAPE_HEADFUL=1  show browser (debug)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Optional

try:
    from scrapling import StealthyFetcher, Selector
except ImportError as e:
    print(f"FATAL: scrapling not installed: {e}", file=sys.stderr)
    sys.exit(2)


FREE_PROXY_SOURCES = [
    # ProxyScrape public free-list (HTTP, anonymous, 10s timeout filter)
    "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&format=text&timeout=10000&anonymity=anonymous,elite",
    # Backup: monosans daily-updated GitHub raw
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    # Backup: TheSpeedX/SOCKS-list
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
]


class FreeProxyPool:
    """Rotates through free HTTP proxies, drops dead ones, refreshes when exhausted."""

    def __init__(self, max_size: int = 200):
        self.max_size = max_size
        self.proxies: list[str] = []
        self.dead: set[str] = set()
        self.idx = 0

    def fetch(self) -> int:
        proxies: list[str] = []
        for src in FREE_PROXY_SOURCES:
            try:
                req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as r:
                    body = r.read().decode("utf-8", errors="ignore")
                for line in body.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Accept "host:port" or "http://host:port"
                    if line.startswith("http://") or line.startswith("https://"):
                        proxies.append(line)
                    elif ":" in line and not line.startswith("//"):
                        proxies.append("http://" + line)
                if len(proxies) >= self.max_size:
                    break
            except Exception as e:
                print(f"[proxy] source fail {src!r}: {e}", file=sys.stderr)
                continue
        random.shuffle(proxies)
        self.proxies = [p for p in proxies if p not in self.dead][: self.max_size]
        self.idx = 0
        return len(self.proxies)

    def next(self) -> Optional[str]:
        if not self.proxies:
            return None
        for _ in range(len(self.proxies)):
            if self.idx >= len(self.proxies):
                self.idx = 0
            p = self.proxies[self.idx]
            self.idx += 1
            if p not in self.dead:
                return p
        return None

    def mark_dead(self, proxy: str) -> None:
        self.dead.add(proxy)
        if proxy in self.proxies:
            try:
                self.proxies.remove(proxy)
            except ValueError:
                pass

    def healthy_count(self) -> int:
        return len(self.proxies)


_PROXY_POOL: Optional[FreeProxyPool] = None


def get_pool() -> Optional[FreeProxyPool]:
    return _PROXY_POOL


def init_pool(enable: bool) -> Optional[FreeProxyPool]:
    global _PROXY_POOL
    if not enable:
        _PROXY_POOL = None
        return None
    p = FreeProxyPool()
    n = p.fetch()
    print(f"[proxy] loaded {n} free proxies")
    _PROXY_POOL = p
    return p

REPO_ROOT = Path(__file__).resolve().parents[1]
LEADERBOARD = REPO_ROOT / "reports/data/leap_top250_leaderboard_2026-05-13.json"
HTML_DIR = REPO_ROOT / "reports/data/leap_profiles_html"
PARSED_DIR = REPO_ROOT / "reports/data/leap_profiles_parsed"
HTML_DIR.mkdir(parents=True, exist_ok=True)
PARSED_DIR.mkdir(parents=True, exist_ok=True)

PROFILE_URL = "https://www.tradingview.com/u/{user}/"
IDEAS_URL = "https://www.tradingview.com/u/{user}/#published-ideas"
SCRIPTS_URL = "https://www.tradingview.com/u/{user}/#published-scripts"


def env_proxy() -> Optional[str]:
    return os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")


def _try_fetch(url: str, proxy: Optional[str], timeout_ms: int) -> tuple[int, Optional[str]]:
    kwargs: dict[str, Any] = {
        "headless": os.environ.get("LEAP_SCRAPE_HEADFUL", "0") != "1",
        "network_idle": True,
        "timeout": timeout_ms,
        "wait": 3000,
        "solve_cloudflare": True,
        "google_search": True,
        "humanize": True,
        "block_webrtc": True,
    }
    if proxy:
        kwargs["proxy"] = proxy
    try:
        resp = StealthyFetcher.fetch(url, **kwargs)
    except TypeError:
        for k in ("humanize", "solve_cloudflare", "block_webrtc"):
            kwargs.pop(k, None)
        try:
            resp = StealthyFetcher.fetch(url, **kwargs)
        except Exception as e:
            return -1, None
    except Exception as e:
        return -1, None
    if resp is None:
        return -1, None
    status = getattr(resp, "status", 0) or 0
    body = getattr(resp, "body", None) or getattr(resp, "html_content", None) or ""
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="ignore")
    return status, body


def _to_text(x) -> str:
    if isinstance(x, bytes):
        return x.decode("utf-8", errors="ignore")
    return x or ""


def fetch_one(url: str, *, timeout_ms: int = 45000, max_retries: int = 6) -> Optional[str]:
    pool = get_pool()
    env_p = env_proxy()
    # Attempt 1: env proxy or direct
    tried: list[str] = []
    if env_p:
        st, body = _try_fetch(url, env_p, timeout_ms)
        tried.append(f"env={env_p}->{st}")
        if 200 <= st < 300 and body:
            return body
    elif pool is None:
        st, body = _try_fetch(url, None, timeout_ms)
        tried.append(f"direct->{st}")
        if 200 <= st < 300 and body:
            return body

    if pool is None:
        return None

    # Rotate free proxies
    for i in range(max_retries):
        if pool.healthy_count() == 0:
            n = pool.fetch()
            print(f"[proxy] pool exhausted, refetched {n}", file=sys.stderr)
            if n == 0:
                break
        proxy = pool.next()
        if not proxy:
            break
        st, body = _try_fetch(url, proxy, timeout_ms)
        tried.append(f"{proxy}->{st}")
        if 200 <= st < 300 and body:
            return body
        # Mark dead on connection error or 403/407/timeouts
        if st < 0 or st in (403, 407, 502, 503, 504):
            pool.mark_dead(proxy)
    print(f"[fetch] giving up on {url} after {len(tried)} attempts: {tried[-3:]}", file=sys.stderr)
    return None


def parse_profile(html: str) -> dict[str, Any]:
    sel = Selector(content=html)
    bio = sel.css_first("div.tv-user-profile__bio")
    bio_text = bio.text.strip() if bio else ""
    name_el = sel.css_first("div.tv-user-profile__name") or sel.css_first("h1.tv-profile-page__title")
    name = name_el.text.strip() if name_el else ""
    socials = []
    for a in sel.css("div.tv-user-profile__social a"):
        href = a.attrib.get("href") if hasattr(a, "attrib") else None
        if href:
            socials.append(href)
    stats: dict[str, Any] = {}
    for stat in sel.css("div.tv-user-profile__stat"):
        try:
            label = stat.css_first(".tv-user-profile__stat-label")
            value = stat.css_first(".tv-user-profile__stat-value")
            if label and value:
                stats[label.text.strip().lower()] = value.text.strip()
        except Exception:
            pass
    return {"name": name, "bio": bio_text, "socials": socials, "stats": stats}


def parse_ideas(html: str) -> list[dict[str, Any]]:
    sel = Selector(content=html)
    out: list[dict[str, Any]] = []
    for card in sel.css("div.tv-feed__item, article.tv-widget-idea") or []:
        try:
            title_el = card.css_first(".tv-widget-idea__title a, a.tv-card-content__title")
            sym_el = card.css_first("a.tv-widget-idea__symbol")
            side_el = card.css_first(".tv-widget-idea__label")
            desc_el = card.css_first(".tv-widget-idea__description, .tv-card-content__description")
            time_el = card.css_first("time")
            out.append({
                "title": title_el.text.strip() if title_el else "",
                "url": title_el.attrib.get("href") if title_el and hasattr(title_el, "attrib") else "",
                "symbol": sym_el.text.strip() if sym_el else "",
                "side": side_el.text.strip() if side_el else "",
                "desc": (desc_el.text or "").strip()[:500] if desc_el else "",
                "ts": time_el.attrib.get("datetime") if time_el and hasattr(time_el, "attrib") else "",
            })
        except Exception:
            continue
    return out


def parse_scripts(html: str) -> list[dict[str, Any]]:
    sel = Selector(content=html)
    out: list[dict[str, Any]] = []
    for card in sel.css("div.tv-feed__item, article.tv-widget-script") or []:
        try:
            title_el = card.css_first(".tv-widget-script__title a, a.tv-card-content__title")
            desc_el = card.css_first(".tv-widget-script__description, .tv-card-content__description")
            out.append({
                "title": title_el.text.strip() if title_el else "",
                "url": title_el.attrib.get("href") if title_el and hasattr(title_el, "attrib") else "",
                "desc": (desc_el.text or "").strip()[:600] if desc_el else "",
            })
        except Exception:
            continue
    return out


def scrape_one(user: str, *, force: bool = False) -> dict[str, Any]:
    parsed_path = PARSED_DIR / f"{user}.json"
    if parsed_path.exists() and not force:
        return {"user": user, "status": "skipped_cached", "parsed_path": str(parsed_path)}

    user_html_dir = HTML_DIR / user
    user_html_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {"user": user, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    # 1) profile page
    profile_html = fetch_one(PROFILE_URL.format(user=user))
    if profile_html:
        (user_html_dir / "profile.html").write_text(_to_text(profile_html), encoding="utf-8", errors="ignore")
        result["profile"] = parse_profile(profile_html)
        result["profile_status"] = "ok"
    else:
        result["profile_status"] = "fail"

    time.sleep(random.uniform(2.0, 5.0))

    # 2) ideas (same URL, anchor; the page is SPA but anchor sometimes triggers fetch)
    ideas_html = fetch_one(IDEAS_URL.format(user=user))
    if ideas_html:
        ideas_html = _to_text(ideas_html)
        (user_html_dir / "ideas.html").write_text(ideas_html, encoding="utf-8", errors="ignore")
        result["ideas"] = parse_ideas(ideas_html)[:50]
        result["ideas_count"] = len(result["ideas"])
    else:
        result["ideas"] = []
        result["ideas_count"] = 0

    time.sleep(random.uniform(2.0, 5.0))

    # 3) scripts (pine)
    scripts_html = fetch_one(SCRIPTS_URL.format(user=user))
    if scripts_html:
        scripts_html = _to_text(scripts_html)
        (user_html_dir / "scripts.html").write_text(scripts_html, encoding="utf-8", errors="ignore")
        result["scripts"] = parse_scripts(scripts_html)[:50]
        result["scripts_count"] = len(result["scripts"])
    else:
        result["scripts"] = []
        result["scripts_count"] = 0

    result["status"] = "ok" if result.get("profile_status") == "ok" else "partial"
    parsed_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"user": user, "status": result["status"], "parsed_path": str(parsed_path),
            "ideas_count": result["ideas_count"], "scripts_count": result["scripts_count"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=int(os.environ.get("LEAP_START_RANK", "1")))
    ap.add_argument("--end", type=int, default=int(os.environ.get("LEAP_END_RANK", "250")))
    ap.add_argument("--force", action="store_true", help="Re-scrape even if cached")
    ap.add_argument("--min-delay", type=float, default=5.0)
    ap.add_argument("--max-delay", type=float, default=15.0)
    ap.add_argument("--users", help="Comma-separated usernames; overrides rank slice")
    ap.add_argument("--proxy-pool", action="store_true",
                    help="Enable free-proxy rotation fallback (TV blocks direct)")
    ap.add_argument("--max-retries", type=int, default=6,
                    help="Per-URL max proxy rotation attempts")
    args = ap.parse_args()

    init_pool(args.proxy_pool)

    leaderboard = json.loads(LEADERBOARD.read_text(encoding="utf-8"))
    rows = leaderboard["traders"]
    if args.users:
        wanted = {u.strip() for u in args.users.split(",") if u.strip()}
        rows = [r for r in rows if r["username"] in wanted]
    else:
        rows = [r for r in rows if args.start <= r["rank"] <= args.end]

    pool = get_pool()
    print(f"=== Leap top-250 serial scraper ===")
    print(f"target n: {len(rows)}  range: {args.start}-{args.end}")
    print(f"env proxy: {env_proxy() or '(none)'}")
    print(f"free-proxy pool: {'enabled (' + str(pool.healthy_count()) + ' loaded)' if pool else 'disabled'}")
    print(f"delay: {args.min_delay}-{args.max_delay}s between profiles")
    print()

    summary = {"ok": 0, "partial": 0, "fail": 0, "skipped_cached": 0}
    for i, row in enumerate(rows, 1):
        user = row["username"]
        try:
            r = scrape_one(user, force=args.force)
            status = r["status"]
            summary[status] = summary.get(status, 0) + 1
            print(f"[{i}/{len(rows)}] rank={row['rank']:3d} {user:32s} -> {status}"
                  f" ideas={r.get('ideas_count', 0)} scripts={r.get('scripts_count', 0)}",
                  flush=True)
        except KeyboardInterrupt:
            print("\nInterrupted by user", file=sys.stderr)
            break
        except Exception as e:
            summary["fail"] = summary.get("fail", 0) + 1
            print(f"[{i}/{len(rows)}] {user} -> ERROR {e!r}", file=sys.stderr, flush=True)
        if i < len(rows):
            d = random.uniform(args.min_delay, args.max_delay)
            time.sleep(d)

    print()
    print(f"=== summary ===  {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
