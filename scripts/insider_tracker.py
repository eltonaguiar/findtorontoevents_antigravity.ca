#!/usr/bin/env python3
"""
Insider Tracker — Fetches and scores SEC Form 4 insider transactions.

For each tracked ticker:
  1. Fetch recent Form 4 filings from SEC EDGAR submissions API
  2. Parse insider transaction details (name, title, buy/sell, shares, price)
  3. Calculate insider conviction score based on role, dollar amount, and clustering
  4. POST scored results to smart_money.php?action=ingest_insider

The primary value of this script (vs the PHP sec_edgar.php fetch_form4) is:
  - Conviction SCORING logic
  - Cluster DETECTION (multiple insiders buying same stock same week)
  - Aggregation into a single scored payload for the consensus engine

Rate limited to 10 requests/minute to SEC EDGAR.
"""
import sys
import os
import re
import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import TRACKED_TICKERS, SEC_USER_AGENT
from utils import safe_request, post_to_api, call_api, RateLimiter

logger = logging.getLogger('insider_tracker')

# Rate limit: 10 requests/minute to SEC EDGAR
sec_limiter = RateLimiter(10)

# Ticker to CIK mapping — fetched dynamically from SEC
_ticker_cik_cache = {}


def sec_get(url):
    """Make a rate-limited GET request to SEC EDGAR."""
    sec_limiter.wait()
    headers = {
        'User-Agent': SEC_USER_AGENT,
        'Accept': 'application/json, application/xml, text/xml, text/html, */*',
        'Accept-Encoding': 'gzip, deflate',
    }
    return safe_request(url, headers=headers, retries=3, timeout=30)


def get_ticker_cik_map():
    """
    Fetch SEC company_tickers.json and build ticker -> CIK mapping.
    Cached for the duration of the script run.
    """
    global _ticker_cik_cache
    if _ticker_cik_cache:
        return _ticker_cik_cache

    logger.info("Fetching SEC company_tickers.json for CIK mapping...")
    resp = sec_get('https://www.sec.gov/files/company_tickers.json')
    if not resp or resp.status_code != 200:
        logger.error("Failed to fetch company_tickers.json")
        return {}

    try:
        data = resp.json()
    except (json.JSONDecodeError, ValueError):
        logger.error("Invalid JSON from company_tickers.json")
        return {}

    for entry in data.values():
        ticker = entry.get('ticker', '').upper()
        cik = str(entry.get('cik_str', '')).zfill(10)
        if ticker and cik:
            _ticker_cik_cache[ticker] = cik

    logger.info(f"Loaded {len(_ticker_cik_cache)} ticker-to-CIK mappings")
    return _ticker_cik_cache


def parse_form4_xml(xml_text, ticker, cik):
    """
    Parse a Form 4 XML filing and extract insider transactions.
    Returns list of transaction dicts.
    """
    trades = []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.debug(f"XML parse error for {ticker}: {e}")
        return trades

    # Extract filer info
    filer_name = ''
    filer_title = ''
    is_director = False
    is_officer = False
    is_ten_pct = False

    # Find reportingOwner element
    for owner in root.iter():
        tag = owner.tag.split('}')[-1] if '}' in owner.tag else owner.tag
        if tag == 'reportingOwner':
            for child in owner.iter():
                ctag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if ctag == 'rptOwnerName' and child.text:
                    filer_name = child.text.strip()
                elif ctag == 'officerTitle' and child.text:
                    filer_title = child.text.strip()
                elif ctag == 'isDirector':
                    is_director = (child.text or '').strip() in ('1', 'true', 'True')
                elif ctag == 'isOfficer':
                    is_officer = (child.text or '').strip() in ('1', 'true', 'True')
                elif ctag == 'isTenPercentOwner':
                    is_ten_pct = (child.text or '').strip() in ('1', 'true', 'True')
            break  # Only process first owner

    # Extract transactions
    for txn in root.iter():
        tag = txn.tag.split('}')[-1] if '}' in txn.tag else txn.tag
        if tag not in ('nonDerivativeTransaction', 'derivativeTransaction'):
            continue

        txn_date = ''
        txn_code = ''
        shares = 0.0
        price = 0.0
        shares_after = 0.0

        for child in txn.iter():
            ctag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

            # Transaction date (inside transactionDate/value)
            if ctag == 'transactionDate':
                for sub in child.iter():
                    stag = sub.tag.split('}')[-1] if '}' in sub.tag else sub.tag
                    if stag == 'value' and sub.text:
                        txn_date = sub.text.strip()

            # Transaction code (P=Purchase, S=Sale, A=Award, M=Exercise, etc.)
            if ctag == 'transactionCode' and child.text:
                txn_code = child.text.strip().upper()

            # Shares
            if ctag == 'transactionShares':
                for sub in child.iter():
                    stag = sub.tag.split('}')[-1] if '}' in sub.tag else sub.tag
                    if stag == 'value' and sub.text:
                        try:
                            shares = float(sub.text.strip())
                        except (ValueError, TypeError):
                            pass

            # Price per share
            if ctag == 'transactionPricePerShare':
                for sub in child.iter():
                    stag = sub.tag.split('}')[-1] if '}' in sub.tag else sub.tag
                    if stag == 'value' and sub.text:
                        try:
                            price = float(sub.text.strip())
                        except (ValueError, TypeError):
                            pass

            # Shares owned after transaction
            if ctag == 'sharesOwnedFollowingTransaction':
                for sub in child.iter():
                    stag = sub.tag.split('}')[-1] if '}' in sub.tag else sub.tag
                    if stag == 'value' and sub.text:
                        try:
                            shares_after = float(sub.text.strip())
                        except (ValueError, TypeError):
                            pass

        if not txn_date:
            continue

        # We mainly care about P (purchases) and S (sales)
        if txn_code not in ('P', 'S', 'A', 'M', 'F', 'G'):
            if txn_code:
                txn_code = txn_code
            else:
                continue

        total_value = shares * price

        trades.append({
            'ticker': ticker,
            'cik': cik,
            'filer_name': filer_name,
            'filer_title': filer_title,
            'transaction_date': txn_date,
            'transaction_type': txn_code,
            'shares': shares,
            'price_per_share': price,
            'total_value': total_value,
            'shares_owned_after': shares_after,
            'is_director': is_director,
            'is_officer': is_officer,
            'is_ten_pct_owner': is_ten_pct,
        })

    return trades


def calculate_conviction_score(trade):
    """
    Calculate insider conviction score for a single trade.
    Higher = more significant.

    Scoring:
      - CEO/CFO buying: 40 pts
      - President: 30 pts
      - Director: 20 pts
      - Other officer: 15 pts
      - Other: 10 pts
      - Purchase > $1M: +30 pts
      - Purchase > $500K: +25 pts
      - Purchase > $100K: +20 pts
      - Purchase > $50K: +15 pts
      - Purchase > $10K: +10 pts
      - Sale penalty: score * 0.3 (sales are less informative)
    """
    score = 0
    title = (trade.get('filer_title') or '').upper()
    is_purchase = trade.get('transaction_type') == 'P'
    total_value = abs(trade.get('total_value', 0))

    # Role-based scoring
    if 'CEO' in title or 'CHIEF EXECUTIVE' in title:
        score += 40
    elif 'CFO' in title or 'CHIEF FINANCIAL' in title:
        score += 40
    elif 'PRESIDENT' in title:
        score += 30
    elif trade.get('is_director'):
        score += 20
    elif trade.get('is_officer'):
        score += 15
    elif trade.get('is_ten_pct_owner'):
        score += 25
    else:
        score += 10

    # Dollar-amount scoring
    if total_value > 1_000_000:
        score += 30
    elif total_value > 500_000:
        score += 25
    elif total_value > 100_000:
        score += 20
    elif total_value > 50_000:
        score += 15
    elif total_value > 10_000:
        score += 10

    # Sales are less informative than purchases
    if not is_purchase:
        score = int(score * 0.3)

    # Award (A) and exercise (M) are routine, low conviction
    if trade.get('transaction_type') in ('A', 'M', 'F', 'G'):
        score = int(score * 0.1)

    return score


def detect_clusters(all_trades):
    """
    Detect insider clusters: multiple insiders buying the same stock within 7 days.
    Returns dict: ticker -> {cluster_count, cluster_bonus, buyers}
    """
    clusters = defaultdict(lambda: {'buyers': set(), 'dates': [], 'total_value': 0})

    for trade in all_trades:
        if trade.get('transaction_type') != 'P':
            continue

        ticker = trade['ticker']
        clusters[ticker]['buyers'].add(trade['filer_name'])
        clusters[ticker]['dates'].append(trade['transaction_date'])
        clusters[ticker]['total_value'] += trade.get('total_value', 0)

    result = {}
    for ticker, data in clusters.items():
        if len(data['buyers']) < 2:
            continue

        # Check if purchases are within 7 days of each other
        dates = sorted(data['dates'])
        if len(dates) >= 2:
            try:
                first = datetime.strptime(dates[0], '%Y-%m-%d')
                last = datetime.strptime(dates[-1], '%Y-%m-%d')
                span = (last - first).days
            except (ValueError, TypeError):
                span = 999

            if span <= 7:
                cluster_bonus = 15 if len(data['buyers']) >= 3 else 10
                result[ticker] = {
                    'cluster_count': len(data['buyers']),
                    'cluster_bonus': cluster_bonus,
                    'buyers': list(data['buyers']),
                    'total_value': data['total_value'],
                    'date_span_days': span,
                }

    return result


def fetch_insider_trades_for_ticker(ticker, cik, lookback_days=30, max_filings=10):
    """
    Fetch recent Form 4 filings for a specific ticker.
    Returns list of parsed trade dicts.
    """
    padded_cik = cik.zfill(10)
    logger.info(f"Fetching Form 4 filings for {ticker} (CIK {padded_cik})")

    url = f'https://data.sec.gov/submissions/CIK{padded_cik}.json'
    resp = sec_get(url)
    if not resp or resp.status_code != 200:
        logger.warning(f"{ticker}: Failed to fetch submissions")
        return []

    try:
        sub = resp.json()
    except (json.JSONDecodeError, ValueError):
        logger.warning(f"{ticker}: Invalid JSON in submissions")
        return []

    if 'filings' not in sub or 'recent' not in sub.get('filings', {}):
        logger.warning(f"{ticker}: No recent filings data")
        return []

    recent = sub['filings']['recent']
    forms = recent.get('form', [])
    accessions = recent.get('accessionNumber', [])
    dates = recent.get('filingDate', [])
    primary_docs = recent.get('primaryDocument', [])

    cutoff = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
    all_trades = []
    form4_count = 0

    for i, form in enumerate(forms):
        if form4_count >= max_filings:
            break
        if form != '4':
            continue
        if i < len(dates) and dates[i] < cutoff:
            continue

        accession = accessions[i] if i < len(accessions) else ''
        filing_date = dates[i] if i < len(dates) else ''
        primary_doc = primary_docs[i] if i < len(primary_docs) else ''

        if not accession or not primary_doc:
            continue

        form4_count += 1

        # Build XML URL
        acc_nodash = accession.replace('-', '')
        cik_num = padded_cik.lstrip('0') or '0'

        # Strip XSL transform prefix
        raw_doc = primary_doc
        if raw_doc.startswith('xsl'):
            slash_pos = raw_doc.find('/')
            if slash_pos != -1:
                raw_doc = raw_doc[slash_pos + 1:]

        xml_url = f'https://www.sec.gov/Archives/edgar/data/{cik_num}/{acc_nodash}/{raw_doc}'

        xml_resp = sec_get(xml_url)
        if not xml_resp or xml_resp.status_code != 200:
            logger.debug(f"{ticker}: Failed to fetch Form 4 XML from {xml_url}")
            continue

        trades = parse_form4_xml(xml_resp.text, ticker, padded_cik)
        for t in trades:
            t['filing_date'] = filing_date
            t['accession'] = accession
        all_trades.extend(trades)

    logger.info(f"{ticker}: Found {len(all_trades)} transactions from {form4_count} Form 4 filings")
    return all_trades


def main():
    """Main entry point for insider tracking."""
    logger.info("=" * 60)
    logger.info("Insider Tracker — Starting")
    logger.info(f"Tracking {len(TRACKED_TICKERS)} tickers: {', '.join(TRACKED_TICKERS)}")
    logger.info("=" * 60)

    # Get ticker-to-CIK mapping
    cik_map = get_ticker_cik_map()
    if not cik_map:
        logger.error("Cannot proceed without CIK mapping")
        return {'error': 'No CIK mapping'}

    all_trades = []
    tickers_processed = 0
    tickers_skipped = 0

    for ticker in TRACKED_TICKERS:
        if ticker not in cik_map:
            logger.warning(f"{ticker}: CIK not found, skipping")
            tickers_skipped += 1
            continue

        tickers_processed += 1
        trades = fetch_insider_trades_for_ticker(ticker, cik_map[ticker])
        all_trades.extend(trades)

    # Calculate conviction scores
    for trade in all_trades:
        trade['conviction_score'] = calculate_conviction_score(trade)

    # Detect clusters
    clusters = detect_clusters(all_trades)
    if clusters:
        logger.info(f"Detected insider clusters in {len(clusters)} tickers:")
        for ticker, info in clusters.items():
            logger.info(
                f"  {ticker}: {info['cluster_count']} insiders bought within "
                f"{info['date_span_days']} days, total ${info['total_value']:,.0f}"
            )
            # Apply cluster bonus to matching trades
            for trade in all_trades:
                if trade['ticker'] == ticker and trade.get('transaction_type') == 'P':
                    trade['conviction_score'] += info['cluster_bonus']
                    trade['cluster_bonus'] = info['cluster_bonus']

    # Filter to meaningful transactions only (purchases and sales)
    meaningful = [t for t in all_trades if t.get('transaction_type') in ('P', 'S')]
    purchases = [t for t in meaningful if t['transaction_type'] == 'P']
    sales = [t for t in meaningful if t['transaction_type'] == 'S']

    # Aggregate per ticker
    ticker_summary = defaultdict(lambda: {
        'purchases': 0, 'sales': 0,
        'buy_value': 0, 'sell_value': 0,
        'max_conviction': 0, 'avg_conviction': 0,
        'scores': [], 'buyers': set(), 'sellers': set(),
    })

    for trade in meaningful:
        ticker = trade['ticker']
        if trade['transaction_type'] == 'P':
            ticker_summary[ticker]['purchases'] += 1
            ticker_summary[ticker]['buy_value'] += trade.get('total_value', 0)
            ticker_summary[ticker]['buyers'].add(trade['filer_name'])
        else:
            ticker_summary[ticker]['sales'] += 1
            ticker_summary[ticker]['sell_value'] += trade.get('total_value', 0)
            ticker_summary[ticker]['sellers'].add(trade['filer_name'])
        ticker_summary[ticker]['scores'].append(trade.get('conviction_score', 0))

    for ticker, summary in ticker_summary.items():
        scores = summary['scores']
        summary['max_conviction'] = max(scores) if scores else 0
        summary['avg_conviction'] = round(sum(scores) / len(scores), 1) if scores else 0
        summary['buyers'] = list(summary['buyers'])
        summary['sellers'] = list(summary['sellers'])
        del summary['scores']

    # POST to API
    payload = {
        'trades': meaningful,
        'clusters': {k: {**v, 'buyers': list(v['buyers'])} if isinstance(v.get('buyers'), set) else v
                     for k, v in clusters.items()},
        'ticker_summary': dict(ticker_summary),
        'stats': {
            'tickers_processed': tickers_processed,
            'tickers_skipped': tickers_skipped,
            'total_transactions': len(meaningful),
            'total_purchases': len(purchases),
            'total_sales': len(sales),
            'clusters_detected': len(clusters),
        },
    }

    result = post_to_api('ingest_insider', payload)
    if not result.get('ok'):
        # Fallback: trigger PHP-side fetch_form4
        logger.info("ingest_insider not available, triggering PHP fetch_form4 as fallback")
        # Process in batches of 5 tickers
        batch_size = 5
        total_batches = (len(TRACKED_TICKERS) + batch_size - 1) // batch_size
        for batch_idx in range(total_batches):
            fb_result = call_api('fetch_form4', f'batch={batch_idx}')
            if fb_result.get('ok'):
                stats = fb_result.get('stats', {})
                logger.info(
                    f"PHP fetch_form4 batch {batch_idx}: "
                    f"inserted={stats.get('trades_inserted', 0)}, "
                    f"skipped={stats.get('trades_skipped', 0)}"
                )
            else:
                logger.warning(f"PHP fetch_form4 batch {batch_idx} failed: {fb_result.get('error', 'unknown')}")

    # Summary
    logger.info("=" * 60)
    logger.info("INSIDER TRACKER SUMMARY")
    logger.info(f"  Tickers processed: {tickers_processed}")
    logger.info(f"  Tickers skipped:   {tickers_skipped}")
    logger.info(f"  Total transactions: {len(meaningful)} ({len(purchases)} buys, {len(sales)} sells)")
    logger.info(f"  Clusters detected:  {len(clusters)}")

    # Top conviction trades
    top_conviction = sorted(meaningful, key=lambda t: t.get('conviction_score', 0), reverse=True)[:5]
    if top_conviction:
        logger.info("  Top conviction trades:")
        for t in top_conviction:
            logger.info(
                f"    {t['ticker']:5s} | {t['filer_name'][:25]:25s} | "
                f"{'BUY' if t['transaction_type'] == 'P' else 'SELL':4s} | "
                f"${t.get('total_value', 0):>12,.0f} | score={t.get('conviction_score', 0)}"
            )

    logger.info("=" * 60)

    return {
        'tickers_processed': tickers_processed,
        'transactions': len(meaningful),
        'purchases': len(purchases),
        'sales': len(sales),
        'clusters': len(clusters),
    }


if __name__ == '__main__':
    main()
