#!/usr/bin/env python3
"""Standalone crawler for public MQL5 signals with a forex-focused filter.

The script:
1. Crawls public MQL5 signal listing pages (MT4 / MT5, multiple presets).
2. Follows signal detail pages and extracts public metrics from HTML.
3. Filters for likely forex signals using symbol mix and name heuristics.
4. Writes JSON and CSV outputs in tmp/.

This is intentionally conservative: if a detail page is blocked or metrics are
missing, the crawler records the blocker and moves on.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import logging
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

try:
    import requests
except ImportError as exc:  # pragma: no cover - environment specific
    raise SystemExit("requests is required") from exc

try:
    from bs4 import BeautifulSoup
except ImportError as exc:  # pragma: no cover - environment specific
    raise SystemExit("beautifulsoup4 is required") from exc

try:  # pragma: no cover - optional browser fallback
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - environment specific
    sync_playwright = None


BASE_URL = "https://www.mql5.com"
DEFAULT_OUT_JSON = Path("tmp/mql5_forex_signals.json")
DEFAULT_OUT_CSV = Path("tmp/mql5_forex_signals.csv")

FX_SYMBOLS = {
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
    "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "CHFJPY", "EURCHF",
    "GBPAUD", "GBPCAD", "GBPCHF", "AUDCAD", "AUDCHF", "AUDNZD", "EURAUD",
    "EURCAD", "EURNZD", "GBPNZD", "NZDCAD", "NZDCHF", "NZDJPY", "CADCHF",
    "USDSEK", "USDNOK", "USDPLN", "USDHUF", "USDMXN", "USDZAR", "USDSGD",
}

NON_FX_HINTS = {
    "XAUUSD", "XAGUSD", "BTCUSD", "BTCUSDT", "ETHUSD", "ETHUSDT", "SOLUSD",
    "US30", "NAS100", "SPX500", "SP500", "GER40", "UK100", "JP225", "WTI",
    "BRENT", "DAX", "GOLD", "SILVER", "OIL", "COPPER",
}

LIST_VARIANTS = [
    ("mt5", "reliability", 11),
    ("mt5", "intraday", 12),
    ("mt5", "max_profit", 2),
    ("mt5", "reviews", 5),
    ("mt5", "robots", 7),
    ("mt4", "reliability", 11),
    ("mt4", "intraday", 12),
    ("mt4", "max_profit", 2),
]


@dataclass
class SignalRecord:
    signal_id: str
    url: str
    title: str = ""
    author: str = ""
    growth_pct: Optional[float] = None
    reliability_pct: Optional[float] = None
    profit_usd: Optional[float] = None
    equity_usd: Optional[float] = None
    initial_deposit_usd: Optional[float] = None
    trading_days: Optional[int] = None
    weeks: Optional[int] = None
    subscribers: Optional[int] = None
    trades_per_week: Optional[int] = None
    avg_holding_hours: Optional[float] = None
    latest_trade_days_ago: Optional[float] = None
    drawdown_pct: Optional[float] = None
    profit_trades: Optional[int] = None
    loss_trades: Optional[int] = None
    symbol_counts: Dict[str, int] = dataclasses.field(default_factory=dict)
    forex_symbol_count: int = 0
    non_fx_symbol_count: int = 0
    likely_forex: bool = False
    quality_score: float = 0.0
    blocker: str = ""
    source_pages: List[str] = dataclasses.field(default_factory=list)


def build_headers(referer: Optional[str] = None) -> Dict[str, str]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    if referer:
        headers["Referer"] = referer
    return headers


def normalize_int(value: str) -> Optional[int]:
    if value is None:
        return None
    cleaned = re.sub(r"[^\d-]", "", value)
    return int(cleaned) if cleaned not in {"", "-"} else None


def normalize_float(value: str) -> Optional[float]:
    if value is None:
        return None
    cleaned = value.replace(" ", "")
    cleaned = cleaned.replace(",", "")
    cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
    return float(cleaned) if cleaned not in {"", ".", "-", "-."} else None


def latest_trade_to_days(count: int, unit: str) -> float:
    unit = unit.lower()
    if unit.startswith("minute"):
        return count / 1440.0
    if unit.startswith("hour"):
        return count / 24.0
    if unit.startswith("day"):
        return float(count)
    if unit.startswith("week"):
        return count * 7.0
    if unit.startswith("month"):
        return count * 30.0
    return float(count)


def holding_to_hours(count: float, unit: str) -> float:
    unit = unit.lower()
    if unit.startswith("minute"):
        return count / 60.0
    if unit.startswith("hour"):
        return count
    if unit.startswith("day"):
        return count * 24.0
    return count


def parse_signal_links(html: str) -> List[Tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    links: List[Tuple[str, str]] = []
    seen = set()
    for a in soup.select('a[href^="/en/signals/"]'):
        href = a.get("href") or ""
        m = re.match(r"/en/signals/(\d+)", href)
        if not m:
            continue
        sid = m.group(1)
        if sid in seen:
            continue
        seen.add(sid)
        text = " ".join(a.get_text(" ", strip=True).split())
        links.append((sid, href))
    return links


def extract_text(soup: BeautifulSoup) -> str:
    return " ".join(soup.get_text(" ", strip=True).split())


def find_first(pattern: str, text: str, flags: int = 0) -> Optional[re.Match]:
    return re.search(pattern, text, flags)


def parse_metrics(html: str, signal_id: str, url: str) -> SignalRecord:
    soup = BeautifulSoup(html, "html.parser")
    text = extract_text(soup)

    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    author = ""
    title_match = re.search(r"-\s+MQL5$", title)
    if title_match:
        title = title[: title_match.start()].strip()
    # Best-effort author extraction from the title line.
    author_match = re.search(r"for the (.+?) trading signal", title, re.I)
    if author_match:
        author = author_match.group(1).strip()

    rec = SignalRecord(signal_id=signal_id, url=url, title=title, author=author)

    patterns = {
        "growth_pct": r"Growth[:\s]+([\d\s.,]+)%",
        "reliability_pct": r"Reliability\s+([\d.]+)%",
        "profit_usd": r"Profit:\s*([\d\s.,-]+)\s*USD",
        "equity_usd": r"Equity:\s*([\d\s.,-]+)\s*USD",
        "initial_deposit_usd": r"Initial Deposit:\s*([\d\s.,-]+)\s*USD",
        "trading_days": r"Trading Days:\s*([\d,]+)",
        "weeks": r"Weeks:\s*([\d,]+)",
        "subscribers": r"Subscribers:\s*([\d,]+)",
        "trades_per_week": r"Trades per week:\s*([\d,]+)",
        "avg_holding_hours": r"Avg holding time:\s*([\d.]+)\s*(minute|minutes|hour|hours|day|days)",
        "latest_trade": r"Latest trade:\s*([\d.]+)\s*(minute|minutes|hour|hours|day|days|week|weeks|month|months)\s*ago",
        "drawdown_pct": r"Drawdown[:\s]+([\d.]+)%",
        "profit_trades": r"Profit Trades:\s*([\d,]+)",
        "loss_trades": r"Loss Trades:\s*([\d,]+)",
    }

    for field, pattern in patterns.items():
        m = find_first(pattern, text, re.I)
        if not m:
            continue
        if field == "avg_holding_hours":
            rec.avg_holding_hours = holding_to_hours(float(m.group(1)), m.group(2))
        elif field == "latest_trade":
            rec.latest_trade_days_ago = latest_trade_to_days(float(m.group(1)), m.group(2))
        elif field in {"growth_pct", "reliability_pct", "profit_usd", "equity_usd", "initial_deposit_usd", "drawdown_pct"}:
            setattr(rec, field, normalize_float(m.group(1)))
        else:
            setattr(rec, field, normalize_int(m.group(1)))

    # Symbol distribution: most pages render a table with td.col-symbol and a
    # nearby numeric cell. When unavailable, we fall back to name heuristics.
    symbol_counts: Dict[str, int] = {}
    for row in soup.select("tr"):
        symbol_cell = row.select_one("td.col-symbol")
        if not symbol_cell:
            continue
        symbol = " ".join(symbol_cell.get_text(" ", strip=True).split()).upper()
        if not symbol:
            continue
        count = None
        for cell in row.select("td"):
            cell_text = " ".join(cell.get_text(" ", strip=True).split())
            if cell is symbol_cell:
                continue
            if re.fullmatch(r"[\d,]+", cell_text):
                count = normalize_int(cell_text)
                if count is not None:
                    break
        symbol_counts[symbol] = symbol_counts.get(symbol, 0) + (count or 1)

    # Some pages surface symbols only in plain text or the title.
    for sym in re.findall(
        r"\b[A-Z0-9]{2,12}\b", f"{title} {text} {html[:5000]}"
    ):
        if sym in FX_SYMBOLS or sym in NON_FX_HINTS:
            symbol_counts.setdefault(sym, 1)

    rec.symbol_counts = dict(sorted(symbol_counts.items(), key=lambda kv: (-kv[1], kv[0])))
    rec.forex_symbol_count = sum(v for k, v in rec.symbol_counts.items() if k in FX_SYMBOLS)
    rec.non_fx_symbol_count = sum(v for k, v in rec.symbol_counts.items() if k in NON_FX_HINTS)

    fx_title_hit = bool(re.search(r"(EURUSD|GBPUSD|USDJPY|AUDUSD|USDCAD|USDCHF|NZDUSD|EURGBP|EURJPY|GBPJPY|AUDJPY|CADJPY|forex|fx)", f"{title} {text}", re.I))
    rec.likely_forex = (
        (rec.forex_symbol_count > 0 and rec.forex_symbol_count >= rec.non_fx_symbol_count)
        or fx_title_hit
    )
    return rec


def score_record(rec: SignalRecord) -> float:
    score = 0.0
    if rec.reliability_pct is not None:
        score += min(rec.reliability_pct, 100.0) * 0.45
    if rec.trades_per_week is not None:
        score += min(rec.trades_per_week, 50) * 1.6
    if rec.latest_trade_days_ago is not None:
        score += max(0.0, 25.0 - rec.latest_trade_days_ago) * 1.2
    if rec.weeks is not None:
        score += min(rec.weeks, 104) * 0.25
    if rec.growth_pct is not None:
        score += min(max(rec.growth_pct, 0.0), 5000.0) * 0.01
    if rec.drawdown_pct is not None:
        score += max(0.0, 35.0 - rec.drawdown_pct) * 0.7
    if rec.avg_holding_hours is not None:
        score += max(0.0, 24.0 - rec.avg_holding_hours) * 0.15
    if rec.forex_symbol_count:
        score += min(rec.forex_symbol_count, 20) * 1.0
    if rec.non_fx_symbol_count == 0:
        score += 4.0
    return round(score, 3)


def quality_pass(rec: SignalRecord, min_reliability: float, min_trades_per_week: int, min_weeks: int, max_latest_days: float) -> bool:
    if not rec.likely_forex:
        return False
    if rec.reliability_pct is not None and rec.reliability_pct < min_reliability:
        return False
    if rec.trades_per_week is None or rec.trades_per_week < min_trades_per_week:
        return False
    if rec.weeks is None or rec.weeks < min_weeks:
        return False
    if rec.latest_trade_days_ago is None or rec.latest_trade_days_ago > max_latest_days:
        return False
    if rec.drawdown_pct is not None and rec.drawdown_pct > 35.0:
        return False
    if rec.growth_pct is not None and rec.growth_pct < 0:
        return False
    return True


def fetch(session: requests.Session, url: str, referer: Optional[str] = None, timeout: int = 30) -> Tuple[int, str]:
    resp = session.get(url, headers=build_headers(referer), timeout=timeout)
    return resp.status_code, resp.text


class BrowserFetcher:
    """Lightweight Playwright fallback for pages blocked by requests."""

    def __init__(self) -> None:
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None

    def __enter__(self) -> "BrowserFetcher":
        if sync_playwright is None:
            raise RuntimeError("playwright is not installed")
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)
        self._context = self._browser.new_context(
            user_agent=build_headers()["User-Agent"],
            locale="en-US",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        )
        self._page = self._context.new_page()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._page is not None:
            self._page.close()
        if self._context is not None:
            self._context.close()
        if self._browser is not None:
            self._browser.close()
        if self._pw is not None:
            self._pw.stop()

    def fetch(self, url: str, referer: Optional[str] = None, timeout: int = 30000) -> Tuple[int, str]:
        if self._page is None:
            raise RuntimeError("browser not initialized")
        kwargs = {"wait_until": "domcontentloaded", "timeout": timeout}
        if referer:
            kwargs["referer"] = referer
        response = self._page.goto(url, **kwargs)
        status = response.status if response else 200
        html = self._page.content()
        return status, html


def collect_signal_ids(session: requests.Session, max_pages: int, logger: logging.Logger) -> Tuple[Dict[str, Dict[str, object]], Dict[str, int]]:
    signal_meta: Dict[str, Dict[str, object]] = {}
    stats = Counter()
    browser = None
    try:
        for market, preset_name, preset in LIST_VARIANTS:
            for page in range(1, max_pages + 1):
                url = f"{BASE_URL}/en/signals/{market}/page{page}?preset={preset}"
                try:
                    status, html = fetch(session, url, referer=f"{BASE_URL}/en/signals/{market}")
                except Exception as exc:
                    logger.warning("list page request failed %s: %s", url, exc)
                    status, html = 0, ""
                if status != 200 or "Just a moment" in html or not html.strip():
                    if browser is None and sync_playwright is not None:
                        browser = BrowserFetcher().__enter__()
                    if browser is not None:
                        try:
                            status, html = browser.fetch(url, referer=f"{BASE_URL}/en/signals/{market}")
                        except Exception as exc:
                            logger.warning("list page browser failed %s: %s", url, exc)
                            status, html = 0, ""
                if status != 200 or not html.strip():
                    stats["blocked"] += 1
                    stats[f"blocked_{status}"] += 1
                    logger.warning("list page blocked %s status=%s", url, status)
                    continue
                stats["fetched"] += 1
                links = parse_signal_links(html)
                if not links:
                    logger.info("no links on %s", url)
                    continue
                new_count = 0
                for sid, href in links:
                    meta = signal_meta.setdefault(sid, {"list_hrefs": [], "source_pages": []})
                    meta["list_hrefs"].append(href)
                    meta["source_pages"].append(url)
                    if len(meta["source_pages"]) == 1:
                        new_count += 1
                logger.info("scanned %s links=%d new=%d unique=%d", url, len(links), new_count, len(signal_meta))
                if new_count == 0 and page > 2:
                    # Repeated pages are usually exhausted; stop early for this variant.
                    break
                time.sleep(0.15)
    finally:
        if browser is not None:
            browser.__exit__(None, None, None)
    return signal_meta, dict(stats)


def fetch_signals(session: requests.Session, signal_meta: Dict[str, Dict[str, object]], logger: logging.Logger, detail_delay: float = 0.25) -> Tuple[List[SignalRecord], Dict[str, int]]:
    records: List[SignalRecord] = []
    stats = Counter()
    browser = None
    try:
        for idx, (sid, meta) in enumerate(signal_meta.items(), 1):
            source_pages = meta.get("source_pages") or []
            referer = source_pages[0] if source_pages else f"{BASE_URL}/en/signals/mt5"
            candidates = [f"{BASE_URL}/en/signals/{sid}"]
            # Some pages appear more willing to serve when the original list source is echoed back.
            if source_pages:
                candidates.insert(0, f"{BASE_URL}/en/signals/{sid}?source=Site+Signals+MT5+Tile")
            parsed = None
            last_status = None
            last_html = ""
            for url in candidates:
                try:
                    last_status, last_html = fetch(session, url, referer=referer)
                except Exception as exc:
                    last_status = -1
                    last_html = ""
                    logger.debug("detail fetch error sid=%s url=%s err=%s", sid, url, exc)
                    continue
                if last_status != 200 or "Just a moment" in last_html or not last_html.strip():
                    if browser is None and sync_playwright is not None:
                        browser = BrowserFetcher().__enter__()
                    if browser is not None:
                        try:
                            last_status, last_html = browser.fetch(url, referer=referer)
                        except Exception as exc:
                            logger.debug("detail browser error sid=%s url=%s err=%s", sid, url, exc)
                            last_status = -1
                            last_html = ""
                if last_status == 200 and "Just a moment" not in last_html and last_html.strip():
                    parsed = parse_metrics(last_html, sid, url)
                    parsed.source_pages = list(source_pages)
                    break
            if parsed is None:
                stats[f"blocked_{last_status}"] += 1
                stats["blocked"] += 1
                logger.info("blocked sid=%s status=%s", sid, last_status)
                time.sleep(detail_delay)
                continue
            parsed.quality_score = score_record(parsed)
            stats["fetched"] += 1
            if parsed.likely_forex:
                stats["likely_forex"] += 1
            if parsed.trades_per_week is not None and parsed.trades_per_week >= 5:
                stats["frequent"] += 1
            if parsed.reliability_pct is not None and parsed.reliability_pct >= 70:
                stats["reliable"] += 1
            records.append(parsed)
            if idx % 25 == 0:
                logger.info("detail progress %d/%d fetched=%d forex=%d", idx, len(signal_meta), stats["fetched"], stats["likely_forex"])
            time.sleep(detail_delay)
    finally:
        if browser is not None:
            browser.__exit__(None, None, None)
    return records, dict(stats)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(path: Path, records: Iterable[SignalRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(r) for r in records]
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = sorted({k for row in rows for k in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items()})


def main() -> int:
    parser = argparse.ArgumentParser(description="MQL5 forex signal crawler")
    parser.add_argument("--max-pages", type=int, default=8, help="max list pages per list variant")
    parser.add_argument("--detail-delay", type=float, default=0.25, help="delay between detail requests in seconds")
    parser.add_argument("--min-reliability", type=float, default=70.0)
    parser.add_argument("--min-trades-per-week", type=int, default=5)
    parser.add_argument("--min-weeks", type=int, default=12)
    parser.add_argument("--max-latest-days", type=float, default=14.0)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUT_CSV)
    parser.add_argument("--limit-records", type=int, default=0, help="optional cap on detail pages to fetch (0 = no cap)")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logger = logging.getLogger("mql5-forex-crawler")

    session = requests.Session()
    started = datetime.now(timezone.utc)

    signal_meta, list_stats = collect_signal_ids(session, args.max_pages, logger)
    if args.limit_records > 0:
        signal_meta = dict(list(signal_meta.items())[: args.limit_records])

    records, stats = fetch_signals(session, signal_meta, logger, detail_delay=args.detail_delay)
    quality = [
        r for r in records
        if quality_pass(
            r,
            min_reliability=args.min_reliability,
            min_trades_per_week=args.min_trades_per_week,
            min_weeks=args.min_weeks,
            max_latest_days=args.max_latest_days,
        )
    ]
    quality.sort(key=lambda r: (r.quality_score, r.reliability_pct or 0, r.trades_per_week or 0, r.weeks or 0), reverse=True)
    records.sort(key=lambda r: (r.quality_score, r.reliability_pct or 0, r.trades_per_week or 0, r.weeks or 0), reverse=True)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "started_at": started.isoformat(),
        "source": "MQL5 public signals",
        "list_variants": LIST_VARIANTS,
        "thresholds": {
            "min_reliability": args.min_reliability,
            "min_trades_per_week": args.min_trades_per_week,
            "min_weeks": args.min_weeks,
            "max_latest_days": args.max_latest_days,
        },
        "stats": {
            "unique_signal_ids": len(signal_meta),
            "list_stats": list_stats,
            "detail_records": len(records),
            "quality_records": len(quality),
            "blocked": stats.get("blocked", 0),
            "blocked_breakdown": {k: v for k, v in stats.items() if k.startswith("blocked_")},
            "fetched": stats.get("fetched", 0),
            "likely_forex": stats.get("likely_forex", 0),
            "frequent": stats.get("frequent", 0),
            "reliable": stats.get("reliable", 0),
        },
        "records": [asdict(r) for r in records],
        "quality_roster": [asdict(r) for r in quality],
    }

    write_json(args.output_json, output)
    write_csv(args.output_csv, quality if quality else records)

    print(json.dumps({
        "output_json": str(args.output_json),
        "output_csv": str(args.output_csv),
        "unique_signal_ids": len(signal_meta),
        "list_blocked": list_stats.get("blocked", 0),
        "detail_records": len(records),
        "quality_records": len(quality),
        "blocked": stats.get("blocked", 0),
        "fetched": stats.get("fetched", 0),
        "likely_forex": stats.get("likely_forex", 0),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
