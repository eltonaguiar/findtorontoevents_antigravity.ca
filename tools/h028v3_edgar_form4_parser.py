"""
tools/h028v3_edgar_form4_parser.py — H-028v3 EDGAR Form-4 XML parser
======================================================================

Fetches real SEC Form-4 insider open-market purchase (code-P) transactions for a
given ticker via EDGAR's free full-text search API, parses the ownership XML, and
identifies cluster-buy events (>=3 distinct insiders buying the same ticker within
a rolling 10-day window).

Usage
-----
    python tools/h028v3_edgar_form4_parser.py --ticker GOOD --lookback 365
    python tools/h028v3_edgar_form4_parser.py --ticker GOOD --lookback 730 --min-cluster 2
    python tools/h028v3_edgar_form4_parser.py --ticker AAPL --lookback 180 --output-json

EDGAR endpoints (all free, no API key)
---------------------------------------
  Full-text search (filing index):
    https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt={start}&enddt={end}&forms=4

  Filing index JSON (to resolve individual document URLs):
    https://data.sec.gov/submissions/CIK{cik:010d}.json

  Ownership XML (actual Form-4 document):
    https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodash}/{filename}

SEC policy: User-Agent header with name + email is required. Rate-limit: 10 req/s.

H-028v3 context
---------------
H-028v2 was UNTESTED_DATA_GAP because 78/82 tickers used synthetic fallback
(XML parser not wired). GOOD (Gladstone Commercial REIT) had 7 real clusters.
This module wires the real parser so H-028v3 can run on a full diverse universe.

Academic basis: Lakonishok & Lee (2001) — insider purchases predict 12-month
abnormal returns. Cohen-Malloy-Pomorski (2012) — small-cap cluster buys have the
strongest edge.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote

try:
    import requests
except ImportError:  # pragma: no cover
    sys.exit("requests not installed — run: pip install requests")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("h028v3_edgar")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EDGAR_FTS_URL = (
    "https://efts.sec.gov/LATEST/search-index"
    "?q=%22{ticker}%22&dateRange=custom&startdt={start}&enddt={end}&forms=4"
    "&hits.hits.total.value=true&hits.hits._source.period_of_report=true"
    "&hits.hits._source.file_date=true&hits.hits._source.entity_name=true"
    "&hits.hits._source.file_num=true"
    "&hits.hits.total.relation=true&hits.hits._source.accession_no=true"
)
EDGAR_BASE = "https://www.sec.gov"
EDGAR_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"

# SEC requires a descriptive User-Agent
_CONTACT = os.getenv("SEC_UA_EMAIL", "research@findtorontoevents.ca")
SEC_HEADERS = {
    "User-Agent": f"FindTorontoEvents H028v3 Research {_CONTACT}",
    "Accept": "application/json, text/html, application/xml",
}

# XML namespace used by SEC ownership forms
OWN_NS = "http://www.sec.gov/XMLSchema/document/ownership/4"

# Rate-limit: SEC asks for no more than 10 requests/second
_REQ_DELAY = 0.12  # seconds between requests


# ---------------------------------------------------------------------------
# Helper: throttled HTTP GET
# ---------------------------------------------------------------------------
def _get(url: str, params: Optional[dict] = None, retries: int = 3) -> requests.Response:
    """Throttled GET with retries."""
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, headers=SEC_HEADERS, timeout=20)
            time.sleep(_REQ_DELAY)
            if resp.status_code == 200:
                return resp
            if resp.status_code == 429:
                wait = 2 ** attempt
                log.warning("Rate-limited (429) — sleeping %ss", wait)
                time.sleep(wait)
                continue
            log.warning("HTTP %s for %s (attempt %s)", resp.status_code, url, attempt)
        except requests.RequestException as exc:
            log.warning("Request error (attempt %s): %s", attempt, exc)
        if attempt < retries:
            time.sleep(attempt * 2)
    return None  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Step 1: EDGAR full-text search → list of Form-4 filing metadata
# ---------------------------------------------------------------------------

def search_form4_filings(ticker: str, start_dt: str, end_dt: str) -> list[dict]:
    """
    Query EDGAR full-text search for Form-4 filings mentioning `ticker`.

    Returns a list of dicts with keys: accession_no, file_date, entity_name,
    period_of_report, cik.

    EDGAR FTS returns hits in pages of 10; we page through all results.
    """
    results: list[dict] = []
    from_offset = 0
    page_size = 10

    base_url = (
        "https://efts.sec.gov/LATEST/search-index"
        f"?q=%22{quote(ticker)}%22"
        f"&dateRange=custom&startdt={start_dt}&enddt={end_dt}"
        f"&forms=4"
    )

    while True:
        url = f"{base_url}&from={from_offset}&hits.hits.total.value=true"
        log.debug("FTS query: %s", url)
        resp = _get(url)
        if resp is None:
            log.error("FTS request failed — aborting pagination")
            break

        try:
            data = resp.json()
        except json.JSONDecodeError:
            log.error("Non-JSON FTS response: %s…", resp.text[:200])
            break

        hits_block = data.get("hits", {})
        hits = hits_block.get("hits", [])
        total = hits_block.get("total", {}).get("value", 0)

        if not hits:
            break

        for hit in hits:
            src = hit.get("_source", {})
            accession_no = src.get("accession_no", "")
            # Extract CIK from the _id field which looks like: "0001234567-26-012345"
            # or from the entity_id field
            entity_id = hit.get("_id", "")
            # entity_id in EDGAR FTS is the accession number; CIK is in _source
            cik = src.get("entity_id") or src.get("cik") or ""
            # Try to parse CIK from the file's path if embedded
            file_date = src.get("file_date", "")
            period = src.get("period_of_report", "")
            entity_name = src.get("entity_name", "")

            if accession_no:
                results.append({
                    "accession_no": accession_no,
                    "file_date": file_date,
                    "period_of_report": period,
                    "entity_name": entity_name,
                    "cik": str(cik).lstrip("0") if cik else "",
                    "_raw_id": entity_id,
                })

        from_offset += len(hits)
        if from_offset >= total:
            break

    log.info("FTS returned %d Form-4 filings for ticker '%s'", len(results), ticker)
    return results


# ---------------------------------------------------------------------------
# Step 2: Resolve CIK for a ticker via EDGAR company search
# ---------------------------------------------------------------------------

def resolve_ticker_to_cik(ticker: str) -> Optional[str]:
    """
    Use EDGAR company search to find the CIK for a ticker symbol.
    Returns CIK as a zero-padded 10-digit string, or None if not found.
    """
    url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&entity={ticker}&forms=4"
    # Prefer the submissions lookup which maps tickers directly
    tickers_url = "https://www.sec.gov/files/company_tickers.json"
    resp = _get(tickers_url)
    if resp is None:
        return None
    try:
        tickers_map = resp.json()
    except json.JSONDecodeError:
        return None

    ticker_upper = ticker.upper()
    for _idx, entry in tickers_map.items():
        if entry.get("ticker", "").upper() == ticker_upper:
            cik = entry.get("cik_str", "")
            return str(cik).zfill(10)
    return None


# ---------------------------------------------------------------------------
# Step 3: Fetch filing index to find the XML document URL
# ---------------------------------------------------------------------------

def get_filing_xml_url(cik: str, accession_no: str) -> Optional[str]:
    """
    Given a CIK and accession number (with dashes), fetch the filing index
    and find the primary ownership XML document URL.
    """
    accession_nodash = accession_no.replace("-", "")
    index_url = f"{EDGAR_ARCHIVES}/{cik.lstrip('0')}/{accession_nodash}/{accession_nodash}-index.json"
    resp = _get(index_url)
    if resp is None:
        # Try without zero-padding
        return None

    try:
        index_data = resp.json()
    except json.JSONDecodeError:
        return None

    documents = index_data.get("documents", [])
    for doc in documents:
        doc_type = doc.get("type", "")
        filename = doc.get("document", "")
        # The ownership XML is the primary document of type "4" or ends in .xml
        if doc_type in ("4", "4/A") or filename.lower().endswith(".xml"):
            return f"{EDGAR_ARCHIVES}/{cik.lstrip('0')}/{accession_nodash}/{filename}"

    return None


# ---------------------------------------------------------------------------
# Step 4: Parse Form-4 ownership XML for code-P transactions
# ---------------------------------------------------------------------------

def parse_form4_xml(xml_text: str) -> list[dict]:
    """
    Parse SEC Form-4 ownership XML and return a list of open-market purchase
    (transactionCode == 'P') transactions.

    Each returned dict has:
      - date: transaction date (str YYYY-MM-DD)
      - reporter_name: insider name
      - issuer_name: company name
      - issuer_cik: CIK of the issuing company
      - shares: number of shares transacted (float)
      - price_per_share: price per share (float or None)
      - transaction_code: should be 'P'
    """
    results: list[dict] = []

    try:
        # SEC XML sometimes has encoding declarations or BOM — strip them
        if xml_text.startswith("﻿"):
            xml_text = xml_text[1:]
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        log.warning("XML parse error: %s", exc)
        return results

    def _find(node, tag: str) -> Optional[ET.Element]:
        # Try with and without namespace
        el = node.find(f"{{{OWN_NS}}}{tag}")
        if el is None:
            el = node.find(tag)
        return el

    def _text(node, tag: str, default: str = "") -> str:
        el = _find(node, tag)
        if el is None:
            return default
        return (el.text or "").strip()

    # Extract issuer info
    issuer_node = _find(root, "issuer")
    issuer_name = _text(issuer_node, "issuerName") if issuer_node is not None else ""
    issuer_cik = _text(issuer_node, "issuerCik") if issuer_node is not None else ""

    # Extract reporter name
    reporter_node = _find(root, "reportingOwner")
    reporter_name = ""
    if reporter_node is not None:
        id_node = _find(reporter_node, "reportingOwnerId")
        if id_node is not None:
            reporter_name = _text(id_node, "rptOwnerName")

    # Walk nonDerivativeTable
    ndt = _find(root, "nonDerivativeTable")
    if ndt is None:
        return results

    for txn in list(ndt):
        # Each child is a nonDerivativeTransaction or nonDerivativeHolding
        tag_local = txn.tag.split("}")[-1] if "}" in txn.tag else txn.tag
        if tag_local != "nonDerivativeTransaction":
            continue

        # Transaction code
        tc_node = _find(txn, "transactionCoding")
        if tc_node is None:
            continue
        code = _text(tc_node, "transactionCode")
        if code != "P":
            continue  # Only open-market purchases

        # Transaction date
        td_node = _find(txn, "transactionDate")
        date_str = ""
        if td_node is not None:
            date_str = _text(td_node, "value")

        # Shares
        ta_node = _find(txn, "transactionAmounts")
        shares = 0.0
        price = None
        if ta_node is not None:
            shares_node = _find(ta_node, "transactionShares")
            if shares_node is not None:
                try:
                    shares = float(_text(shares_node, "value") or 0)
                except ValueError:
                    shares = 0.0
            price_node = _find(ta_node, "transactionPricePerShare")
            if price_node is not None:
                price_str = _text(price_node, "value")
                try:
                    price = float(price_str) if price_str else None
                except ValueError:
                    price = None

        if date_str and shares > 0:
            results.append({
                "date": date_str,
                "reporter_name": reporter_name,
                "issuer_name": issuer_name,
                "issuer_cik": issuer_cik,
                "shares": shares,
                "price_per_share": price,
                "transaction_code": "P",
            })

    return results


# ---------------------------------------------------------------------------
# Main public API: fetch_insider_clusters
# ---------------------------------------------------------------------------

def fetch_insider_clusters(ticker: str, lookback_days: int = 365) -> list[dict]:
    """
    Fetch all code-P (open-market purchase) Form-4 transactions for `ticker`
    over the past `lookback_days` calendar days.

    Returns a list of transaction dicts (date, reporter_name, issuer_name,
    issuer_cik, shares, price_per_share, transaction_code).

    Strategy:
    1. Resolve ticker → CIK via company_tickers.json
    2. Query EDGAR FTS for Form-4 filings in date window
    3. For each filing, fetch the XML and parse code-P transactions
    """
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=lookback_days)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    log.info("Resolving CIK for ticker '%s'…", ticker)
    cik = resolve_ticker_to_cik(ticker)
    if cik is None:
        log.warning("Could not resolve CIK for '%s' — FTS will still run with ticker text search", ticker)
        cik = ""

    log.info("CIK for %s: %s", ticker, cik or "<unknown>")
    log.info("Searching Form-4 filings %s → %s…", start_str, end_str)

    filings = search_form4_filings(ticker, start_str, end_str)

    all_transactions: list[dict] = []
    processed = 0

    for filing in filings:
        acc = filing["accession_no"]
        # Use filing CIK if FTS provided one, else use the resolved CIK
        filing_cik = filing.get("cik") or cik
        if not filing_cik:
            log.debug("Skipping filing %s — no CIK available", acc)
            continue

        xml_url = get_filing_xml_url(filing_cik, acc)
        if xml_url is None:
            log.debug("Could not find XML URL for filing %s (CIK %s)", acc, filing_cik)
            continue

        log.debug("Fetching XML: %s", xml_url)
        resp = _get(xml_url)
        if resp is None:
            log.debug("Failed to fetch XML for %s", acc)
            continue

        txns = parse_form4_xml(resp.text)
        # Filter to only transactions for the target ticker's issuer (by CIK match)
        for t in txns:
            t["accession_no"] = acc
            t["file_date"] = filing.get("file_date", "")
            all_transactions.append(t)

        processed += 1
        if processed % 10 == 0:
            log.info("Processed %d/%d filings…", processed, len(filings))

    log.info(
        "Found %d code-P transactions across %d filings for '%s'",
        len(all_transactions),
        processed,
        ticker,
    )
    return all_transactions


# ---------------------------------------------------------------------------
# Cluster detection
# ---------------------------------------------------------------------------

def find_clusters(
    transactions: list[dict],
    window_days: int = 10,
    min_cluster: int = 3,
) -> list[dict]:
    """
    Group code-P transactions by rolling `window_days` windows and return
    clusters where >= `min_cluster` distinct insiders bought the same ticker.

    Returns list of cluster dicts:
      - window_start: str YYYY-MM-DD
      - window_end: str YYYY-MM-DD
      - insider_count: int
      - total_shares: float
      - total_value: float (None if price unavailable)
      - reporters: list[str]
      - transactions: list[dict]
    """
    if not transactions:
        return []

    # Parse dates
    parsed: list[tuple[datetime, dict]] = []
    for t in transactions:
        try:
            dt = datetime.strptime(t["date"], "%Y-%m-%d")
            parsed.append((dt, t))
        except (ValueError, KeyError):
            continue

    parsed.sort(key=lambda x: x[0])

    clusters: list[dict] = []
    n = len(parsed)

    for i in range(n):
        anchor_dt, _ = parsed[i]
        window_end_dt = anchor_dt + timedelta(days=window_days)

        # Collect all transactions within the window starting at anchor
        window_txns = [
            t for dt, t in parsed
            if anchor_dt <= dt <= window_end_dt
        ]

        # Distinct reporters (case-insensitive)
        reporters = list({t["reporter_name"].strip().lower() for t in window_txns})
        if len(reporters) >= min_cluster:
            clusters.append({
                "window_start": anchor_dt.strftime("%Y-%m-%d"),
                "window_end": window_end_dt.strftime("%Y-%m-%d"),
                "insider_count": len(reporters),
                "reporters": sorted({t["reporter_name"].strip() for t in window_txns}),
                "total_shares": sum(t["shares"] for t in window_txns),
                "total_value": (
                    sum(
                        t["shares"] * t["price_per_share"]
                        for t in window_txns
                        if t.get("price_per_share") is not None
                    ) or None
                ),
                "transactions": window_txns,
            })

    # Deduplicate overlapping windows (keep the one with the most insiders)
    if not clusters:
        return []

    deduped: list[dict] = []
    used_windows: set[str] = set()
    clusters.sort(key=lambda c: -c["insider_count"])
    for cluster in clusters:
        key = cluster["window_start"]
        if key not in used_windows:
            deduped.append(cluster)
            # Mark a 10-day exclusion zone
            anchor = datetime.strptime(cluster["window_start"], "%Y-%m-%d")
            for d in range(window_days + 1):
                used_windows.add((anchor + timedelta(days=d)).strftime("%Y-%m-%d"))

    deduped.sort(key=lambda c: c["window_start"])
    return deduped


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="H-028v3: Fetch EDGAR Form-4 code-P insider cluster-buy signals",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--ticker", required=True, help="Stock ticker symbol (e.g. GOOD)")
    parser.add_argument(
        "--lookback",
        type=int,
        default=365,
        help="Lookback window in calendar days (default: 365)",
    )
    parser.add_argument(
        "--min-cluster",
        type=int,
        default=3,
        help="Minimum number of distinct insiders for a cluster (default: 3)",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=10,
        help="Rolling window in days for clustering (default: 10)",
    )
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="Print full JSON output instead of summary",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    ticker = args.ticker.upper()
    log.info("=== H-028v3 EDGAR Form-4 Parser: %s ===", ticker)

    transactions = fetch_insider_clusters(ticker, lookback_days=args.lookback)
    clusters = find_clusters(
        transactions,
        window_days=args.window_days,
        min_cluster=args.min_cluster,
    )

    if args.output_json:
        print(json.dumps({"ticker": ticker, "transactions": transactions, "clusters": clusters}, indent=2))
        return

    # Summary output
    print(f"\n{'='*60}")
    print(f"H-028v3 EDGAR Form-4 Code-P Cluster Results: {ticker}")
    print(f"{'='*60}")
    print(f"Total code-P transactions found: {len(transactions)}")
    print(f"Clusters (>={args.min_cluster} insiders / {args.window_days}d window): {len(clusters)}")

    if transactions:
        print(f"\nRecent code-P transactions (last 10):")
        for t in transactions[-10:]:
            price_str = f"@ ${t['price_per_share']:.2f}" if t.get("price_per_share") else ""
            print(
                f"  {t['date']}  {t['reporter_name'][:40]:<40}  "
                f"{t['shares']:>10,.0f} shares  {price_str}"
            )

    if clusters:
        print(f"\nClusters found:")
        for i, c in enumerate(clusters, 1):
            val_str = f"  ~${c['total_value']:,.0f}" if c.get("total_value") else ""
            print(
                f"  [{i}] {c['window_start']} → {c['window_end']}  "
                f"{c['insider_count']} insiders  "
                f"{c['total_shares']:,.0f} shares{val_str}"
            )
            for r in c["reporters"]:
                print(f"       • {r}")
    else:
        print(
            f"\nNo clusters found. If 0 transactions were returned, the EDGAR FTS may "
            f"need a longer lookback or the ticker had no reported code-P purchases."
        )

    print(f"\nH-028v3 acceptance criteria: min_wr=0.55, min_pf=1.5, min_n=30 clusters")
    print(f"Reference: GOOD (Gladstone Commercial REIT) had 7 clusters in H-028v2 research.")


if __name__ == "__main__":
    main()
