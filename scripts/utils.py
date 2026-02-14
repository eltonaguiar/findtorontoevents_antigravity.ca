"""
Shared utilities for Smart Money scripts.
"""
import requests
import time
import json
import re
import logging
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Ensure config is importable from same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import API_BASE, ADMIN_KEY

# Custom headers to bypass ModSecurity WAF (blocks python-requests User-Agent)
API_HEADERS = {"User-Agent": "SmartMoneyIntelligence/1.0"}


class RateLimiter:
    """Simple rate limiter."""
    def __init__(self, calls_per_minute):
        self.interval = 60.0 / calls_per_minute
        self.last_call = 0

    def wait(self):
        elapsed = time.time() - self.last_call
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self.last_call = time.time()


def safe_request(url, headers=None, params=None, retries=3, timeout=30):
    """HTTP GET with retries and exponential backoff."""
    logger = logging.getLogger('utils')
    merged_headers = dict(API_HEADERS)
    if headers:
        merged_headers.update(headers)
    for i in range(retries):
        try:
            resp = requests.get(url, headers=merged_headers, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            logger.warning(f"Request failed (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(2 ** i)
    return None


def post_to_api(action, data):
    """POST JSON data to the appropriate PHP API endpoint."""
    logger = logging.getLogger('utils')

    # Route to correct PHP file based on action
    regime_actions = (
        'ingest_regime', 'update_position_sizing', 'update_meta_labeler',
        'update_validation', 'update_bundles', 'ingest_worldquant'
    )
    if action in regime_actions:
        url = f"{API_BASE}/regime.php?action={action}&key={ADMIN_KEY}"
    else:
        url = f"{API_BASE}/smart_money.php?action={action}&key={ADMIN_KEY}"

    try:
        resp = requests.post(url, json=data, headers=API_HEADERS, timeout=60)
        result = resp.json()
        if result.get('ok'):
            logger.info(f"POST {action}: OK — {result}")
        else:
            logger.error(f"POST {action}: Error — {result.get('error', 'unknown')}")
        return result
    except Exception as e:
        logger.error(f"POST {action} failed: {e}")
        return {'ok': False, 'error': str(e)}


def call_api(action, params=''):
    """GET from the appropriate PHP API endpoint."""
    logger = logging.getLogger('utils')

    # Route to correct PHP file based on action
    regime_actions = (
        'get_regime', 'regime_history', 'strategy_toggles',
        'get_position_sizing', 'get_meta_labeler', 'meta_label_training_data',
        'algo_stats'
    )
    if action in regime_actions:
        url = f"{API_BASE}/regime.php?action={action}&key={ADMIN_KEY}"
    elif action in ('positions', 'dashboard', 'history'):
        url = f"{API_BASE}/live_trade.php?action={action}&key={ADMIN_KEY}"
    elif action in ('list', 'signals'):
        url = f"{API_BASE}/live_signals.php?action=list&key={ADMIN_KEY}"
    else:
        url = f"{API_BASE}/smart_money.php?action={action}&key={ADMIN_KEY}"

    if params:
        url += '&' + params
    try:
        resp = requests.get(url, headers=API_HEADERS, timeout=60)
        return resp.json()
    except Exception as e:
        logger.error(f"GET {action} failed: {e}")
        return {'ok': False, 'error': str(e)}


def post_to_bridge(module, data, summary=''):
    """POST results to quant_bridge.php for the dashboard front-end."""
    logger = logging.getLogger('utils')
    url = f"{API_BASE}/quant_bridge.php?action=store_results&key={ADMIN_KEY}"
    try:
        payload = {
            'module': module,
            'source': 'github',
            'status': 'success',
            'data': json.dumps(data) if not isinstance(data, str) else data,
            'summary': summary
        }
        resp = requests.post(url, data=payload, headers=API_HEADERS, timeout=60)
        result = resp.json()
        if result.get('ok'):
            logger.info(f"Bridge POST {module}: OK")
        else:
            logger.warning(f"Bridge POST {module}: {result.get('error', 'unknown')}")
        return result
    except Exception as e:
        logger.warning(f"Bridge POST {module} failed: {e}")
        return {'ok': False, 'error': str(e)}


def parse_tickers_from_text(text):
    """Extract stock tickers from text (e.g., $GME, $TSLA)."""
    from config import TRACKED_TICKERS, WSB_EXTRA_TICKERS

    # Match $TICKER pattern
    dollar_tickers = re.findall(r'\$([A-Z]{2,5})\b', text.upper())

    # Also match standalone uppercase words that are in our known list
    known = set(TRACKED_TICKERS + WSB_EXTRA_TICKERS)
    standalone = re.findall(r'\b([A-Z]{2,5})\b', text.upper())
    standalone_valid = [t for t in standalone if t in known]

    return list(set(dollar_tickers + standalone_valid))
