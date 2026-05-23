#!/usr/bin/env python3
"""
FRED Macro Overlay — Fetches key macroeconomic indicators from the FRED API
and derives a macro regime score for trading system regime detection.

Indicators tracked:
  1. T10Y2Y  — 10Y-2Y yield spread (recession indicator)
  2. UNRATE  — Unemployment rate (labor market health)
  3. VIXCLS  — VIX close (fear gauge)
  4. FEDFUNDS — Federal funds rate (monetary policy)
  5. DGS10   — 10-year treasury yield
  6. DTWEXBGS — Trade-weighted USD index (broad)
  7. T10YIE  — 10-year breakeven inflation rate

Output:
  - POST macro_update to smart_money.php
  - Write data/macro_regime.json for other scripts

Requires: pip install requests
FRED API key: env var FRED_API_KEY (free at https://fred.stlouisfed.org/docs/api/api_key.html)
"""
import sys
import os
import json
import logging
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import post_to_api, API_HEADERS
from config import API_BASE, ADMIN_KEY

logger = logging.getLogger('fred_macro')

# FRED API configuration
FRED_BASE_URL = 'https://api.stlouisfed.org/fred/series/observations'
FRED_API_KEY = os.environ.get('FRED_API_KEY', '')

# Indicators to fetch
INDICATORS = {
    'T10Y2Y':   '10Y-2Y Yield Spread',
    'UNRATE':   'Unemployment Rate',
    'VIXCLS':   'VIX Close',
    'FEDFUNDS': 'Federal Funds Rate',
    'DGS10':    '10-Year Treasury Yield',
    'DTWEXBGS': 'Trade-Weighted USD Index',
    'T10YIE':   '10-Year Breakeven Inflation',
}


# ---------------------------------------------------------------------------
# FRED Data Fetching
# ---------------------------------------------------------------------------

def fetch_fred_series(series_id, lookback_days=90):
    """
    Fetch observations for a FRED series over the last N days.
    Returns list of (date_str, float_value) tuples, newest last.
    """
    import requests

    if not FRED_API_KEY:
        logger.warning("FRED_API_KEY not set — skipping %s", series_id)
        return []

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=lookback_days)

    params = {
        'series_id': series_id,
        'api_key': FRED_API_KEY,
        'file_type': 'json',
        'observation_start': start_date.strftime('%Y-%m-%d'),
        'observation_end': end_date.strftime('%Y-%m-%d'),
        'sort_order': 'asc',
    }

    try:
        resp = requests.get(
            FRED_BASE_URL,
            params=params,
            headers=API_HEADERS,
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error("FRED fetch failed for %s: %s", series_id, e)
        return []

    observations = data.get('observations', [])
    results = []
    for obs in observations:
        val = obs.get('value', '.')
        if val == '.':
            continue  # FRED uses '.' for missing data
        try:
            results.append((obs['date'], float(val)))
        except (ValueError, KeyError):
            continue

    logger.info("  %s: fetched %d observations", series_id, len(results))
    return results


def calculate_trend(values, window=30):
    """
    Calculate trend direction over last `window` data points.
    Returns: 'rising', 'falling', or 'flat' plus the percentage change.
    """
    if len(values) < 2:
        return 'flat', 0.0

    # Use up to `window` most recent values
    recent = values[-window:]
    first_val = recent[0]
    last_val = recent[-1]

    if abs(first_val) < 1e-10:
        return 'flat', 0.0

    pct_change = (last_val - first_val) / abs(first_val) * 100

    if pct_change > 2.0:
        return 'rising', round(pct_change, 2)
    elif pct_change < -2.0:
        return 'falling', round(pct_change, 2)
    else:
        return 'flat', round(pct_change, 2)


# ---------------------------------------------------------------------------
# Macro Regime Scoring
# ---------------------------------------------------------------------------

def derive_macro_regime(indicators_data):
    """
    Derive a macro regime score (0-100) and classification from FRED indicators.

    Scoring logic:
      - Bullish (70-100): Yield curve positive + VIX < 20 + unemployment falling
      - Cautious (40-69): Yield curve flat + VIX 20-25 + mixed signals
      - Bearish (0-39): Yield curve inverted + VIX > 25 + unemployment rising

    Returns dict with score, regime label, and per-indicator details.
    """
    score = 50  # Neutral baseline
    details = {}

    # --- T10Y2Y: Yield Curve Spread ---
    yc = indicators_data.get('T10Y2Y', {})
    yc_val = yc.get('current')
    if yc_val is not None:
        if yc_val > 0.5:
            score += 15
            details['yield_curve'] = 'positive'
        elif yc_val > 0:
            score += 5
            details['yield_curve'] = 'slightly_positive'
        elif yc_val > -0.5:
            score -= 10
            details['yield_curve'] = 'inverted'
        else:
            score -= 20
            details['yield_curve'] = 'deeply_inverted'
        details['yield_spread'] = yc_val
    else:
        details['yield_curve'] = 'unknown'

    # --- VIXCLS: Fear Gauge ---
    vix = indicators_data.get('VIXCLS', {})
    vix_val = vix.get('current')
    if vix_val is not None:
        if vix_val < 15:
            score += 10
            details['vix_regime'] = 'low_vol'
        elif vix_val < 20:
            score += 5
            details['vix_regime'] = 'normal'
        elif vix_val < 25:
            score -= 5
            details['vix_regime'] = 'elevated'
        elif vix_val < 30:
            score -= 10
            details['vix_regime'] = 'high'
        else:
            score -= 15
            details['vix_regime'] = 'fear'
        details['vix_level'] = vix_val
    else:
        details['vix_regime'] = 'unknown'

    # --- UNRATE: Unemployment ---
    unemp = indicators_data.get('UNRATE', {})
    unemp_trend = unemp.get('trend', 'flat')
    unemp_val = unemp.get('current')
    if unemp_val is not None:
        if unemp_trend == 'falling':
            score += 10
            details['unemployment'] = 'improving'
        elif unemp_trend == 'rising':
            score -= 10
            details['unemployment'] = 'deteriorating'
        else:
            details['unemployment'] = 'stable'
        details['unemployment_rate'] = unemp_val
    else:
        details['unemployment'] = 'unknown'

    # --- FEDFUNDS: Monetary Policy ---
    fed = indicators_data.get('FEDFUNDS', {})
    fed_trend = fed.get('trend', 'flat')
    fed_val = fed.get('current')
    if fed_val is not None:
        if fed_trend == 'rising':
            score -= 5  # Hawkish = headwind
            details['fed_policy'] = 'hawkish'
        elif fed_trend == 'falling':
            score += 5  # Dovish = tailwind
            details['fed_policy'] = 'dovish'
        else:
            details['fed_policy'] = 'neutral'
        details['fed_funds_rate'] = fed_val
    else:
        details['fed_policy'] = 'unknown'

    # --- DGS10: 10-Year Treasury ---
    t10 = indicators_data.get('DGS10', {})
    t10_val = t10.get('current')
    t10_trend = t10.get('trend', 'flat')
    if t10_val is not None:
        if t10_val > 5.0:
            score -= 5  # Very high rates = headwind
        elif t10_val < 3.0:
            score += 5  # Low rates = tailwind
        details['treasury_10y'] = t10_val
        details['treasury_10y_trend'] = t10_trend
    else:
        details['treasury_10y_trend'] = 'unknown'

    # --- DTWEXBGS: USD Strength ---
    usd = indicators_data.get('DTWEXBGS', {})
    usd_trend = usd.get('trend', 'flat')
    usd_val = usd.get('current')
    if usd_val is not None:
        if usd_trend == 'rising':
            score -= 3  # Strong dollar = headwind for equities
            details['usd_strength'] = 'strengthening'
        elif usd_trend == 'falling':
            score += 3  # Weak dollar = tailwind
            details['usd_strength'] = 'weakening'
        else:
            details['usd_strength'] = 'stable'
        details['usd_index'] = usd_val
    else:
        details['usd_strength'] = 'unknown'

    # --- T10YIE: Inflation Expectations ---
    infl = indicators_data.get('T10YIE', {})
    infl_val = infl.get('current')
    infl_trend = infl.get('trend', 'flat')
    if infl_val is not None:
        if infl_val > 3.0:
            score -= 5  # High inflation expectations = headwind
            details['inflation_expectations'] = 'high'
        elif infl_val < 1.5:
            score -= 3  # Too low = deflation risk
            details['inflation_expectations'] = 'low'
        else:
            score += 3  # Goldilocks zone
            details['inflation_expectations'] = 'moderate'
        details['breakeven_inflation'] = infl_val
        details['inflation_trend'] = infl_trend
    else:
        details['inflation_expectations'] = 'unknown'

    # Clamp score
    score = max(0, min(100, score))

    # Derive regime label
    if score >= 70:
        regime = 'bullish'
    elif score >= 40:
        regime = 'cautious'
    else:
        regime = 'bearish'

    details['macro_score'] = score
    details['macro_regime'] = regime

    return score, regime, details


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run_fred_macro():
    """
    Full FRED macro overlay pipeline:
    1. Fetch 90 days of each indicator
    2. Calculate current value + 30-day trend
    3. Derive macro regime score
    4. POST to PHP API
    5. Write data/macro_regime.json
    """
    logger.info("=" * 60)
    logger.info("FRED MACRO OVERLAY — Starting")
    logger.info("=" * 60)

    if not FRED_API_KEY:
        logger.error("FRED_API_KEY environment variable not set.")
        logger.error("Get a free key at: https://fred.stlouisfed.org/docs/api/api_key.html")
        return None

    # Step 1: Fetch all indicators
    logger.info("Fetching FRED indicators...")
    indicators_data = {}

    for series_id, name in INDICATORS.items():
        observations = fetch_fred_series(series_id, lookback_days=90)

        if not observations:
            indicators_data[series_id] = {
                'name': name,
                'current': None,
                'trend': 'unknown',
                'trend_pct': 0.0,
                'observations': 0,
            }
            continue

        values = [v for _, v in observations]
        current = values[-1]
        trend, trend_pct = calculate_trend(values, window=30)

        indicators_data[series_id] = {
            'name': name,
            'current': round(current, 4),
            'trend': trend,
            'trend_pct': trend_pct,
            'observations': len(values),
            'first_date': observations[0][0],
            'last_date': observations[-1][0],
        }

    # Step 2: Derive macro regime
    logger.info("Deriving macro regime score...")
    score, regime, details = derive_macro_regime(indicators_data)

    # Step 3: Compile result
    result = {
        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'macro_score': score,
        'macro_regime': regime,
        'indicators': indicators_data,
        'details': details,
    }

    # Print summary
    logger.info("=" * 60)
    logger.info("FRED MACRO OVERLAY RESULTS")
    logger.info("=" * 60)
    logger.info("  Macro Score:  %d / 100", score)
    logger.info("  Regime:       %s", regime.upper())
    logger.info("  Indicators:")
    for sid, info in indicators_data.items():
        val = info.get('current')
        trend = info.get('trend', '?')
        name = info.get('name', sid)
        if val is not None:
            logger.info("    %-30s  %8.4f  (%s, %+.2f%%)", name, val, trend, info.get('trend_pct', 0))
        else:
            logger.info("    %-30s  %8s  (no data)", name, 'N/A')
    logger.info("=" * 60)

    # Step 4: POST to PHP API
    logger.info("Posting macro data to API...")
    api_result = post_to_api('macro_update', result)

    if api_result.get('ok'):
        logger.info("Macro data saved to API successfully")
    else:
        logger.warning("API post returned: %s", api_result.get('error', 'unknown'))

    # Step 5: Write data/macro_regime.json
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    os.makedirs(data_dir, exist_ok=True)
    output_path = os.path.join(data_dir, 'macro_regime.json')

    try:
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        logger.info("Wrote macro regime to %s", output_path)
    except Exception as e:
        logger.error("Failed to write macro_regime.json: %s", e)

    # Print JSON for GitHub Actions log
    print("\n--- FRED MACRO JSON OUTPUT ---")
    print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """Entry point for run_all.py integration."""
    return run_fred_macro()


if __name__ == '__main__':
    main()
