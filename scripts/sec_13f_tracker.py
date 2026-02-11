#!/usr/bin/env python3
"""
SEC 13F Tracker — Fetches latest 13F-HR institutional holdings filings.

For each fund in TOP_FUNDS:
  1. Fetch latest 13F-HR filing from SEC EDGAR submissions API
  2. Download and parse the 13F XML holdings table
  3. Map CUSIPs to our tracked tickers
  4. Detect quarter-over-quarter changes (new, increased, decreased, maintained, sold_out)
  5. POST results to smart_money.php?action=ingest_13f

Rate limited to 10 requests/minute to SEC (be respectful to the free API).
"""
import sys
import os
import re
import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import TOP_FUNDS, TRACKED_TICKERS, CUSIP_TO_TICKER, SEC_USER_AGENT
from utils import safe_request, post_to_api, call_api, RateLimiter

logger = logging.getLogger('sec_13f')

# Rate limit: 10 requests/minute to SEC EDGAR
sec_limiter = RateLimiter(10)

# 13F XML namespace
NS_13F = 'http://www.sec.gov/edgar/document/thirteenf/informationtable'

# Extended CUSIP map (includes extra common tickers from the PHP side)
EXTENDED_CUSIP = {
    '037833100': 'AAPL',
    '594918104': 'MSFT',
    '02079K305': 'GOOGL',
    '02079K107': 'GOOG',
    '023135106': 'AMZN',
    '67066G104': 'NVDA',
    '30303M102': 'META',
    '46625H100': 'JPM',
    '931142103': 'WMT',
    '30231G102': 'XOM',
    '64110L106': 'NFLX',
    '478160104': 'JNJ',
    '060505104': 'BAC',
    '38141G104': 'GS',
    '88160R101': 'TSLA',
    '92826C839': 'V',
    '57636Q104': 'MA',
    '254687106': 'DIS',
    '22160K105': 'COST',
    '742718109': 'PG',
    '91324P102': 'UNH',
    '437076102': 'HD',
    '79466L302': 'CRM',
    '458140100': 'INTC',
    '007903107': 'AMD',
    '70450Y103': 'PYPL',
    '852234103': 'SQ',
    '82509L107': 'SHOP',
    '00917P104': 'ABNB',
}

# Issuer name to ticker fallback (if CUSIP lookup fails)
ISSUER_NAME_MAP = {
    'APPLE': 'AAPL', 'MICROSOFT': 'MSFT', 'ALPHABET': 'GOOGL',
    'AMAZON': 'AMZN', 'NVIDIA': 'NVDA', 'META PLATFORMS': 'META',
    'JPMORGAN': 'JPM', 'WALMART': 'WMT', 'EXXON': 'XOM',
    'NETFLIX': 'NFLX', 'JOHNSON': 'JNJ', 'BANK OF AMERICA': 'BAC',
    'BANK OF AMER': 'BAC', 'GOLDMAN': 'GS', 'TESLA': 'TSLA',
}

# Merge config CUSIP map into extended map
for cusip, ticker in CUSIP_TO_TICKER.items():
    if cusip not in EXTENDED_CUSIP:
        EXTENDED_CUSIP[cusip] = ticker


def sec_get(url):
    """Make a rate-limited GET request to SEC EDGAR."""
    sec_limiter.wait()
    headers = {
        'User-Agent': SEC_USER_AGENT,
        'Accept': 'application/json, application/xml, text/xml, text/html, */*',
        'Accept-Encoding': 'gzip, deflate',
    }
    return safe_request(url, headers=headers, retries=3, timeout=30)


def derive_quarter(filing_date_str):
    """
    Derive which quarter a 13F filing covers based on filing date.
    13F filings cover the prior quarter-end:
      Filed Jan-Mar => Q4 prior year
      Filed Apr-Jun => Q1 current year
      Filed Jul-Sep => Q2 current year
      Filed Oct-Dec => Q3 current year
    """
    try:
        dt = datetime.strptime(filing_date_str, '%Y-%m-%d')
    except (ValueError, TypeError):
        return 'Q?-????'

    month = dt.month
    year = dt.year

    if 1 <= month <= 3:
        return f'Q4-{year - 1}'
    elif 4 <= month <= 6:
        return f'Q1-{year}'
    elif 7 <= month <= 9:
        return f'Q2-{year}'
    else:
        return f'Q3-{year}'


def prev_quarter(quarter_str):
    """Get previous quarter string, e.g. Q1-2026 -> Q4-2025."""
    match = re.match(r'^Q(\d)-(\d{4})$', quarter_str)
    if not match:
        return ''
    q = int(match.group(1))
    y = int(match.group(2))
    if q == 1:
        return f'Q4-{y - 1}'
    else:
        return f'Q{q - 1}-{y}'


def guess_ticker_from_issuer(issuer_name):
    """Attempt to map an issuer name to a ticker symbol."""
    name = issuer_name.upper().strip()
    for keyword, ticker in ISSUER_NAME_MAP.items():
        if keyword in name:
            return ticker
    return ''


def cusip_to_ticker(cusip):
    """Map a CUSIP to a ticker symbol."""
    cusip = cusip.strip()
    if cusip in EXTENDED_CUSIP:
        return EXTENDED_CUSIP[cusip]
    return ''


def find_infotable_url(index_url, acc_nodash, cik_num):
    """
    Given a filing index URL, find the infotable XML URL.
    Strategy 1: Parse the filing index page for links containing 'info' or 'table'.
    Strategy 2: Try common infotable filenames.
    """
    resp = sec_get(index_url)
    if resp and resp.status_code == 200:
        html = resp.text
        # Look for XML links containing 'info' or 'table'
        matches = re.findall(r'href="([^"]*(?:info|table)[^"]*\.xml)"', html, re.IGNORECASE)
        for candidate in matches:
            if 'primary_doc' in candidate.lower():
                continue
            # Resolve relative/absolute URLs
            if candidate.startswith('/'):
                return f'https://www.sec.gov{candidate}'
            elif candidate.startswith('http'):
                return candidate
            else:
                return f'{index_url}{candidate}'

    # Strategy 2: Try common filenames
    common_names = ['infotable.xml', 'InfoTable.xml', 'INFOTABLE.XML',
                    'information_table.xml', '0000infotable.xml']
    for name in common_names:
        try_url = f'{index_url}{name}'
        sec_limiter.wait()
        try:
            test_resp = safe_request(try_url, headers={
                'User-Agent': SEC_USER_AGENT,
                'Accept': '*/*',
            }, retries=1, timeout=15)
            if test_resp and test_resp.status_code == 200 and 'infoTable' in test_resp.text:
                return try_url
        except Exception:
            continue

    return None


def parse_13f_xml(xml_text):
    """
    Parse 13F infotable XML and extract holdings.
    Returns list of dicts: {cusip, issuer, value_thousands, shares, ticker}
    """
    holdings = []

    # Try parsing with namespace
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        # Try stripping namespaces as fallback
        cleaned = re.sub(r'xmlns[^=]*="[^"]*"', '', xml_text)
        cleaned = re.sub(r'<([a-zA-Z0-9]+):', '<', cleaned)
        cleaned = re.sub(r'</([a-zA-Z0-9]+):', '</', cleaned)
        try:
            root = ET.fromstring(cleaned)
        except ET.ParseError as e:
            logger.error(f"Failed to parse 13F XML: {e}")
            return holdings

    # Search for infoTable entries with various namespace patterns
    # Pattern 1: With namespace
    entries = root.findall(f'.//{{{NS_13F}}}infoTable')
    # Pattern 2: No namespace (after stripping)
    if not entries:
        entries = root.findall('.//infoTable')
    # Pattern 3: Try as direct children
    if not entries:
        for child in root:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if tag.lower() == 'infotable':
                entries.append(child)

    for entry in entries:
        cusip = ''
        issuer = ''
        value = 0
        shares = 0

        # Extract fields (handle namespace variants)
        for child in entry:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            tag_lower = tag.lower()

            if tag_lower == 'cusip':
                cusip = (child.text or '').strip()
            elif tag_lower == 'nameofissuer':
                issuer = (child.text or '').strip()
            elif tag_lower == 'value':
                try:
                    value = int(child.text or '0')
                except (ValueError, TypeError):
                    value = 0
            elif tag_lower in ('shrsOrPrnamt', 'shrsorprnamt'):
                # Nested: <sshPrnamt> inside <shrsOrPrnAmt>
                for sub in child:
                    sub_tag = sub.tag.split('}')[-1] if '}' in sub.tag else sub.tag
                    if sub_tag.lower() in ('sshprnamt',):
                        try:
                            shares = int(sub.text or '0')
                        except (ValueError, TypeError):
                            shares = 0

        # Also try direct xpath for nested shares
        if shares == 0:
            for ns_prefix in [f'{{{NS_13F}}}', '']:
                sh_el = entry.find(f'{ns_prefix}shrsOrPrnAmt/{ns_prefix}sshPrnamt')
                if sh_el is None:
                    sh_el = entry.find(f'{ns_prefix}shrsOrPrnAmt/{ns_prefix}sshPrnamtType/{ns_prefix}sshPrnamt')
                if sh_el is not None and sh_el.text:
                    try:
                        shares = int(sh_el.text.strip())
                        break
                    except (ValueError, TypeError):
                        pass

        if not cusip:
            continue

        # Map to ticker
        ticker = cusip_to_ticker(cusip)
        if not ticker:
            ticker = guess_ticker_from_issuer(issuer)

        holdings.append({
            'cusip': cusip,
            'issuer': issuer,
            'value_thousands': value,
            'shares': shares,
            'ticker': ticker,
        })

    return holdings


def fetch_fund_13f(cik, fund_name):
    """
    Fetch the latest 13F-HR filing for a single fund.
    Returns dict with filing info and parsed holdings, or None on failure.
    """
    padded_cik = cik.zfill(10)
    logger.info(f"Fetching submissions for {fund_name} (CIK {padded_cik})")

    # Step 1: Get fund submissions index
    url = f'https://data.sec.gov/submissions/CIK{padded_cik}.json'
    resp = sec_get(url)
    if not resp or resp.status_code != 200:
        logger.warning(f"{fund_name}: Failed to fetch submissions (status={getattr(resp, 'status_code', 'N/A')})")
        return None

    try:
        sub = resp.json()
    except (json.JSONDecodeError, ValueError):
        logger.warning(f"{fund_name}: Invalid JSON in submissions response")
        return None

    if 'filings' not in sub or 'recent' not in sub.get('filings', {}):
        logger.warning(f"{fund_name}: No filings.recent in response")
        return None

    recent = sub['filings']['recent']
    forms = recent.get('form', [])
    accessions = recent.get('accessionNumber', [])
    dates = recent.get('filingDate', [])
    primary_docs = recent.get('primaryDocument', [])

    # Step 2: Find the latest 13F-HR or 13F-HR/A
    filing_idx = None
    for i, form in enumerate(forms):
        if form in ('13F-HR', '13F-HR/A'):
            filing_idx = i
            break

    if filing_idx is None:
        logger.warning(f"{fund_name}: No 13F-HR filing found in recent submissions")
        return None

    filing_accession = accessions[filing_idx] if filing_idx < len(accessions) else ''
    filing_date = dates[filing_idx] if filing_idx < len(dates) else ''
    filing_doc = primary_docs[filing_idx] if filing_idx < len(primary_docs) else ''

    if not filing_accession:
        logger.warning(f"{fund_name}: No accession number for 13F filing")
        return None

    filing_quarter = derive_quarter(filing_date)
    logger.info(f"{fund_name}: Found 13F-HR filed {filing_date} (covers {filing_quarter}), accession={filing_accession}")

    # Step 3: Build URL and find the infotable XML
    acc_nodash = filing_accession.replace('-', '')
    cik_num = padded_cik.lstrip('0') or '0'
    index_url = f'https://www.sec.gov/Archives/edgar/data/{cik_num}/{acc_nodash}/'

    infotable_url = find_infotable_url(index_url, acc_nodash, cik_num)

    # Fallback: try the primary doc if it's XML
    if not infotable_url and filing_doc:
        raw_doc = filing_doc
        if raw_doc.startswith('xsl'):
            slash_pos = raw_doc.find('/')
            if slash_pos != -1:
                raw_doc = raw_doc[slash_pos + 1:]
        if raw_doc.lower().endswith('.xml') and raw_doc != 'primary_doc.xml':
            infotable_url = f'{index_url}{raw_doc}'

    if not infotable_url:
        logger.warning(f"{fund_name}: Could not locate infotable XML in filing")
        return None

    # Step 4: Download and parse the infotable XML
    logger.info(f"{fund_name}: Downloading infotable from {infotable_url}")
    xml_resp = sec_get(infotable_url)
    if not xml_resp or xml_resp.status_code != 200:
        logger.warning(f"{fund_name}: Failed to download infotable XML")
        return None

    holdings = parse_13f_xml(xml_resp.text)
    logger.info(f"{fund_name}: Parsed {len(holdings)} total holdings from 13F XML")

    return {
        'fund_name': fund_name,
        'cik': padded_cik,
        'filing_date': filing_date,
        'filing_quarter': filing_quarter,
        'accession': filing_accession,
        'holdings': holdings,
    }


def detect_changes(current_holdings, previous_holdings):
    """
    Compare current quarter holdings against previous quarter.
    Returns list of holdings with change_type and change_pct added.

    previous_holdings: dict keyed by cusip -> {shares, value_thousands}
    """
    results = []
    current_cusips = set()

    for h in current_holdings:
        cusip = h['cusip']
        current_cusips.add(cusip)
        cur_shares = h['shares']

        if cusip in previous_holdings:
            prev_shares = previous_holdings[cusip]['shares']
            if prev_shares == 0 and cur_shares > 0:
                h['change_type'] = 'NEW_POSITION'
                h['change_pct'] = 100.0
            elif cur_shares == 0 and prev_shares > 0:
                h['change_type'] = 'SOLD_OUT'
                h['change_pct'] = -100.0
            else:
                pct = ((cur_shares - prev_shares) / max(prev_shares, 1)) * 100
                if pct > 10:
                    h['change_type'] = 'INCREASED'
                elif pct < -10:
                    h['change_type'] = 'DECREASED'
                else:
                    h['change_type'] = 'MAINTAINED'
                h['change_pct'] = round(pct, 2)
            h['prev_shares'] = prev_shares
        else:
            h['change_type'] = 'NEW_POSITION'
            h['change_pct'] = 100.0
            h['prev_shares'] = 0

        results.append(h)

    # Check for sold-out positions (in previous but not in current)
    for cusip, prev_data in previous_holdings.items():
        if cusip not in current_cusips:
            ticker = cusip_to_ticker(cusip)
            if ticker and ticker in TRACKED_TICKERS:
                results.append({
                    'cusip': cusip,
                    'issuer': prev_data.get('issuer', ''),
                    'value_thousands': 0,
                    'shares': 0,
                    'ticker': ticker,
                    'change_type': 'SOLD_OUT',
                    'change_pct': -100.0,
                    'prev_shares': prev_data['shares'],
                })

    return results


def fetch_previous_quarter(cik, fund_name, current_quarter):
    """
    Try to get the previous quarter's holdings from the API.
    Returns dict keyed by cusip -> {shares, value_thousands, issuer}
    """
    prev_q = prev_quarter(current_quarter)
    if not prev_q:
        return {}

    # Try to get from our API first
    result = call_api('fund_13f_quarter', f'cik={cik}&quarter={prev_q}')
    if result.get('ok') and result.get('holdings'):
        prev = {}
        for h in result['holdings']:
            cusip = h.get('cusip', '')
            if cusip:
                prev[cusip] = {
                    'shares': int(h.get('shares', 0)),
                    'value_thousands': int(h.get('value_thousands', 0)),
                    'issuer': h.get('name_of_issuer', ''),
                }
        if prev:
            logger.info(f"{fund_name}: Loaded {len(prev)} previous holdings from API for {prev_q}")
            return prev

    # Fallback: fetch previous 13F from SEC directly
    # This is expensive, so only do it if the API doesn't have the data
    logger.info(f"{fund_name}: No previous quarter data from API for {prev_q}, will compare without history")
    return {}


def main():
    """Main entry point for SEC 13F tracking."""
    logger.info("=" * 60)
    logger.info("SEC 13F Tracker — Starting")
    logger.info(f"Tracking {len(TOP_FUNDS)} hedge funds")
    logger.info(f"Watching {len(TRACKED_TICKERS)} tickers: {', '.join(TRACKED_TICKERS)}")
    logger.info("=" * 60)

    total_funds = 0
    total_holdings_matched = 0
    total_changes = 0
    errors = []

    for cik, fund_name in TOP_FUNDS.items():
        total_funds += 1

        try:
            result = fetch_fund_13f(cik, fund_name)
        except Exception as e:
            logger.error(f"{fund_name}: Exception during fetch — {e}")
            errors.append(f"{fund_name}: {e}")
            continue

        if not result:
            errors.append(f"{fund_name}: No filing data retrieved")
            continue

        # Filter to our tracked tickers only
        matched = [h for h in result['holdings'] if h.get('ticker') in TRACKED_TICKERS]
        logger.info(f"{fund_name}: {len(matched)} holdings match our tracked tickers")

        if not matched:
            continue

        total_holdings_matched += len(matched)

        # Try to get previous quarter for change detection
        prev_holdings = fetch_previous_quarter(
            result['cik'], fund_name, result['filing_quarter']
        )

        # Detect changes
        if prev_holdings:
            matched_with_changes = detect_changes(matched, prev_holdings)
            changes = [h for h in matched_with_changes if h.get('change_type') != 'MAINTAINED']
            total_changes += len(changes)
        else:
            # No previous data — mark all as NEW_POSITION
            for h in matched:
                h['change_type'] = 'NEW_POSITION'
                h['change_pct'] = 0.0
                h['prev_shares'] = 0
            matched_with_changes = matched

        # POST to API
        payload = {
            'fund_name': fund_name,
            'cik': result['cik'],
            'filing_date': result['filing_date'],
            'filing_quarter': result['filing_quarter'],
            'accession': result['accession'],
            'holdings': matched_with_changes,
        }

        api_result = post_to_api('ingest_13f', payload)
        if not api_result.get('ok'):
            # Try the PHP-side fetch_13f as fallback (it does its own SEC fetching)
            logger.info(f"{fund_name}: ingest_13f not available, trying PHP fetch_13f")
            fallback = call_api('fetch_13f', f'fund_cik={cik}')
            if fallback.get('ok'):
                logger.info(f"{fund_name}: PHP fetch_13f succeeded as fallback")
            else:
                logger.warning(f"{fund_name}: Both ingest_13f and fetch_13f failed")

        # Log detailed changes
        for h in matched_with_changes:
            if h.get('change_type') and h['change_type'] != 'MAINTAINED':
                logger.info(
                    f"  {fund_name} | {h['ticker']:5s} | {h['change_type']:14s} | "
                    f"shares: {h.get('prev_shares', 0):>12,} -> {h['shares']:>12,} "
                    f"({h.get('change_pct', 0):+.1f}%) | "
                    f"value: ${h['value_thousands']:,}K"
                )

    # Summary
    logger.info("=" * 60)
    logger.info("SEC 13F TRACKER SUMMARY")
    logger.info(f"  Funds processed:  {total_funds}")
    logger.info(f"  Holdings matched: {total_holdings_matched}")
    logger.info(f"  Changes detected: {total_changes}")
    logger.info(f"  Errors:           {len(errors)}")
    if errors:
        for err in errors:
            logger.warning(f"  - {err}")
    logger.info("=" * 60)

    return {
        'funds_processed': total_funds,
        'holdings_matched': total_holdings_matched,
        'changes_detected': total_changes,
        'errors': len(errors),
    }


if __name__ == '__main__':
    main()
