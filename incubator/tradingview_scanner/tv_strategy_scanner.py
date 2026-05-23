"""
TradingView Strategy Scanner & Baby Strategy Pipeline
======================================================

Automated scanner that:
1. Fetches trending/editors' pick scripts from TradingView
2. Extracts strategy concepts (indicators, logic, parameters)
3. Cross-references against existing incubator strategies (dedup)
4. Generates baby strategy candidates for review

Designed to run every 4 hours via GitHub Actions or locally.
Uses TradingView's public pages (no API key required).

Output: data/tv_scan_results.json — list of strategy candidates
"""

import json
import os
import re
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from html.parser import HTMLParser


# === Configuration ===

SCAN_URLS = {
    "editors_picks": "https://www.tradingview.com/scripts/editors-picks/",
    "trending": "https://www.tradingview.com/scripts/trending/",
    "crypto_strategies": "https://www.tradingview.com/scripts/crypto-strategy/",
    "newest": "https://www.tradingview.com/scripts/newest/",
    "ideas_recent": "https://www.tradingview.com/ideas/?sort=recent_extended",
    "ideas_crypto": "https://www.tradingview.com/ideas/cryptocurrency/",
}

LUXALGO_SCRIPTS = [
    "https://www.tradingview.com/u/LuxAlgo/#published-scripts",
]

DATA_DIR = Path(__file__).parent / "data"
SEEN_FILE = DATA_DIR / "seen_scripts.json"
RESULTS_FILE = DATA_DIR / "tv_scan_results.json"
CANDIDATES_FILE = DATA_DIR / "baby_candidates.json"

# Existing strategy fingerprints (names) for dedup
EXISTING_STRATEGIES_DIR = Path(__file__).parent.parent / "agents"


@dataclass
class ScriptEntry:
    """A TradingView script discovered by the scanner."""
    title: str
    author: str
    url: str
    script_type: str  # "indicator", "strategy", "library"
    description: str
    tags: List[str] = field(default_factory=list)
    indicators_mentioned: List[str] = field(default_factory=list)
    scan_source: str = ""  # which page we found it on
    first_seen: str = ""
    fingerprint: str = ""  # hash for dedup
    relevance_score: float = 0.0  # 0-1, how relevant to our incubator


class TVPageParser(HTMLParser):
    """Extract script cards from TradingView script listing pages."""

    def __init__(self):
        super().__init__()
        self.scripts = []
        self._current = {}
        self._in_title = False
        self._in_desc = False
        self._in_author = False
        self._capture_text = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        # Look for script card links
        if tag == "a":
            href = attrs_dict.get("href", "")
            if "/script/" in href:
                self._current = {"url": href, "title": "", "description": "", "author": ""}
                self._in_title = True
                self._capture_text = ""

    def handle_data(self, data):
        if self._in_title:
            self._capture_text += data.strip()

    def handle_endtag(self, tag):
        if tag == "a" and self._in_title and self._current:
            self._current["title"] = self._capture_text.strip()
            self._in_title = False
            if self._current["title"]:
                self.scripts.append(self._current)
            self._current = {}


# === Indicator Detection ===

KNOWN_INDICATORS = [
    "RSI", "MACD", "EMA", "SMA", "Bollinger Bands", "ATR", "ADX",
    "Stochastic", "CCI", "Williams %R", "Ichimoku", "VWAP",
    "Volume Profile", "OBV", "MFI", "Fibonacci", "Donchian",
    "Keltner", "Supertrend", "Parabolic SAR", "Hull MA", "DEMA", "TEMA",
    "KST", "ROC", "Momentum", "Heikin Ashi", "Renko",
    "Order Flow", "Delta", "CVD", "Footprint", "VPVR",
    "Fair Value Gap", "FVG", "Order Block", "Liquidity", "BOS", "CHOCH",
    "Smart Money", "ICT", "Wyckoff", "Elliott Wave",
    "Mean Reversion", "Breakout", "Scalp", "Swing",
    "Trailing Stop", "Chandelier Exit", "Pivot Points",
]


def detect_indicators(text: str) -> List[str]:
    """Detect which indicators are mentioned in a description."""
    found = []
    text_lower = text.lower()
    for ind in KNOWN_INDICATORS:
        if ind.lower() in text_lower:
            found.append(ind)
    return list(set(found))


def compute_fingerprint(title: str, author: str) -> str:
    """Create a stable fingerprint for dedup."""
    raw = f"{title.lower().strip()}|{author.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def compute_relevance(entry: ScriptEntry) -> float:
    """Score how relevant a script is for our crypto incubator."""
    score = 0.0
    text = f"{entry.title} {entry.description}".lower()

    # Crypto relevance
    crypto_terms = ["crypto", "bitcoin", "btc", "eth", "sol", "doge", "altcoin", "defi"]
    for term in crypto_terms:
        if term in text:
            score += 0.15
            break

    # Strategy vs indicator (strategies are more actionable)
    if entry.script_type == "strategy":
        score += 0.2
    elif "strategy" in text:
        score += 0.15

    # Backtested / proven
    if any(w in text for w in ["backtest", "win rate", "profit factor", "sharpe"]):
        score += 0.15

    # Indicator density (more indicators = more complex/interesting)
    score += min(len(entry.indicators_mentioned) * 0.05, 0.2)

    # Popular concepts
    hot_concepts = ["momentum", "breakout", "reversal", "scalp", "mean reversion",
                    "order flow", "smart money", "liquidity", "volume profile"]
    for concept in hot_concepts:
        if concept in text:
            score += 0.05

    # LuxAlgo bonus
    if "luxalgo" in entry.author.lower():
        score += 0.1

    return min(score, 1.0)


# === Existing Strategy Dedup ===

def load_existing_strategy_names() -> set:
    """Get names of strategies we already have in the incubator."""
    names = set()
    if EXISTING_STRATEGIES_DIR.exists():
        for agent_dir in EXISTING_STRATEGIES_DIR.iterdir():
            if agent_dir.is_dir():
                for f in agent_dir.glob("*.py"):
                    names.add(f.stem.lower())
    return names


def load_seen_scripts() -> Dict[str, dict]:
    """Load previously seen scripts to avoid re-processing."""
    if SEEN_FILE.exists():
        with open(SEEN_FILE, "r") as f:
            return json.load(f)
    return {}


def save_seen_scripts(seen: Dict[str, dict]):
    """Save seen scripts registry."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f, indent=2)


# === Page Fetching ===

def fetch_page(url: str, retries: int = 2) -> str:
    """Fetch a URL with basic retry and user-agent spoofing."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError) as e:
            if attempt < retries:
                time.sleep(2)
                continue
            print(f"  [WARN] Failed to fetch {url}: {e}")
            return ""


def extract_scripts_from_page(html: str, source: str) -> List[ScriptEntry]:
    """Extract script entries from a TradingView page."""
    entries = []

    # Pattern: /script/XXXXX-Title-Here
    script_pattern = re.compile(r'/script/([A-Za-z0-9]+)-([^"\'<>]+)')
    matches = script_pattern.findall(html)

    seen_in_page = set()
    for script_id, title_slug in matches:
        title = title_slug.replace("-", " ").strip()
        if not title or len(title) < 3:
            continue

        fp = compute_fingerprint(title, script_id)
        if fp in seen_in_page:
            continue
        seen_in_page.add(fp)

        url = f"https://www.tradingview.com/script/{script_id}-{title_slug}/"

        # Try to extract author from nearby context
        author = ""
        author_pattern = re.compile(rf'by\s+([A-Za-z0-9_]+)\s', re.IGNORECASE)
        # Look for author near the script reference
        idx = html.find(script_id)
        if idx > 0:
            context = html[max(0, idx - 200):idx + 500]
            author_match = author_pattern.search(context)
            if author_match:
                author = author_match.group(1)

        # Detect script type
        script_type = "indicator"
        if "strategy" in title.lower():
            script_type = "strategy"
        elif "library" in title.lower():
            script_type = "library"

        indicators = detect_indicators(title)

        entry = ScriptEntry(
            title=title,
            author=author,
            url=url,
            script_type=script_type,
            description=title,  # Will be enriched if we fetch individual pages
            tags=[],
            indicators_mentioned=indicators,
            scan_source=source,
            first_seen=datetime.now(timezone.utc).isoformat(),
            fingerprint=fp,
        )
        entry.relevance_score = compute_relevance(entry)
        entries.append(entry)

    return entries


# === Main Scanner ===

def run_scan(fetch_details: bool = False) -> List[ScriptEntry]:
    """
    Run a full scan of TradingView pages.

    Args:
        fetch_details: If True, fetch individual script pages for more details (slower)

    Returns:
        List of new (unseen) script entries, sorted by relevance
    """
    print(f"\n{'='*60}")
    print(f"TradingView Strategy Scanner — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")

    seen = load_seen_scripts()
    existing_names = load_existing_strategy_names()
    all_new = []

    for source_name, url in SCAN_URLS.items():
        print(f"Scanning: {source_name} ({url})")
        html = fetch_page(url)
        if not html:
            continue

        entries = extract_scripts_from_page(html, source_name)
        new_count = 0

        for entry in entries:
            if entry.fingerprint in seen:
                continue  # Already seen

            # Check if we already have a similar strategy
            title_normalized = entry.title.lower().replace(" ", "_").replace("-", "_")
            if any(title_normalized in name or name in title_normalized for name in existing_names):
                entry.description += " [SIMILAR EXISTS IN INCUBATOR]"

            seen[entry.fingerprint] = {
                "title": entry.title,
                "first_seen": entry.first_seen,
                "source": source_name,
            }
            all_new.append(entry)
            new_count += 1

        print(f"  Found {len(entries)} scripts, {new_count} new")

    # Sort by relevance
    all_new.sort(key=lambda x: x.relevance_score, reverse=True)

    # Save results
    save_seen_scripts(seen)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    results = [asdict(e) for e in all_new]
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)

    # Filter top candidates (relevance > 0.3)
    candidates = [e for e in all_new if e.relevance_score >= 0.3]
    with open(CANDIDATES_FILE, "w") as f:
        json.dump([asdict(e) for e in candidates], f, indent=2)

    print(f"\n{'='*60}")
    print(f"Scan complete: {len(all_new)} new scripts found")
    print(f"  Top candidates (relevance >= 0.3): {len(candidates)}")
    print(f"  Results saved to: {RESULTS_FILE}")
    print(f"  Candidates saved to: {CANDIDATES_FILE}")
    print(f"  Seen registry: {len(seen)} total scripts tracked")
    print(f"{'='*60}\n")

    # Print top 10 candidates
    if candidates:
        print("Top 10 Baby Strategy Candidates:")
        print("-" * 80)
        for i, c in enumerate(candidates[:10], 1):
            print(f"  {i}. [{c.relevance_score:.2f}] {c.title}")
            print(f"     Author: {c.author} | Type: {c.script_type}")
            print(f"     Indicators: {', '.join(c.indicators_mentioned) or 'N/A'}")
            print(f"     URL: {c.url}")
            print()

    return all_new


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TradingView Strategy Scanner")
    parser.add_argument("--details", action="store_true", help="Fetch individual script pages")
    parser.add_argument("--reset", action="store_true", help="Reset seen scripts registry")
    args = parser.parse_args()

    if args.reset:
        if SEEN_FILE.exists():
            os.remove(SEEN_FILE)
            print("Seen scripts registry reset.")

    run_scan(fetch_details=args.details)
