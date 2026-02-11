#!/usr/bin/env python3
"""
Penny Stock Daily Picks Engine
===============================
Multi-factor scoring system for NYSE/NASDAQ penny stocks ($1-$5).
Designed for retirement-safe picks with high Sharpe ratio.

Scoring Architecture (0-100 composite):
  - Financial Health (30%): Altman Z''-Score, Piotroski F-Score, ratios
  - Momentum (25%): Multi-period price momentum with Clenow regression
  - Volume (10%): RVOL, OBV trend, liquidity
  - Technical (10%): RSI, EMA alignment
  - Earnings (10%): Post-Earnings Announcement Drift (PEAD)
  - Smart Money (10%): Insider buying, institutional signals
  - Quality (5%): Frog-in-the-Pan momentum quality

Hard Filters (REJECT):
  - OTC/Pink Sheets (only NYSE, NASDAQ, TSX, TSX-V)
  - Price < $1.00 or > $5.00
  - Average volume < 200K
  - Market cap < $50M
  - Z''-Score < 1.5 (distress zone)
  - Both net income AND operating cash flow negative

Risk Parameters:
  - Stop loss: 15% initial
  - Take profit: 30% target
  - Max hold: 90 days
  - Position sizing: Quarter-Kelly (~1.5% each)
  - Max 15-20 positions, max 25% per sector
"""

import sys
import os
import json
import time
import logging
import traceback
import datetime
import requests
import numpy as np
import pandas as pd

# yfinance
try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed. Run: pip install yfinance")
    sys.exit(1)

try:
    from scipy.stats import linregress
except ImportError:
    linregress = None

# ── Config ──
API_BASE = os.environ.get('PENNY_API_BASE',
    'https://findtorontoevents.ca/findstocks/portfolio2/api')
ADMIN_KEY = os.environ.get('PENNY_ADMIN_KEY', 'livetrader2026')
API_HEADERS = {"User-Agent": "PennyStockIntelligence/1.0"}

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('penny_picks')

# ── Constants ──
MIN_PRICE = 1.00
MAX_PRICE = 5.00
MIN_VOLUME = 200000
MIN_MARKET_CAP = 50_000_000
MAX_PICKS = 20
RATE_LIMIT_DELAY = 1.5  # seconds between yfinance calls

# Factor weights (sum to 1.0)
WEIGHTS = {
    'financial_health': 0.30,
    'momentum': 0.25,
    'volume': 0.10,
    'technical': 0.10,
    'earnings': 0.10,
    'smart_money': 0.10,
    'quality': 0.05,
}

# Whitelisted exchanges
ALLOWED_EXCHANGES = {
    'NYQ', 'NMS', 'NGM', 'NCM', 'ASE', 'PCX', 'BTS',  # US
    'TOR', 'CVE', 'CNQ', 'NEO', 'VAN',  # Canada
}
BLOCKED_EXCHANGES = {
    'PNK', 'OTC', 'OBB', 'OTCQX', 'OTCQB', 'OTCBB', 'PKC', 'OQX', 'OQB'
}


# ============================================================================
# STEP 1: GET CANDIDATE UNIVERSE
# ============================================================================

def get_penny_universe():
    """Fetch penny stock universe from our screener API."""
    candidates = []

    for region in ['us', 'ca']:
        for offset in range(0, 200, 100):
            url = f"{API_BASE}/penny_stocks.php"
            params = {
                'region': region,
                'max_price': MAX_PRICE,
                'min_price': MIN_PRICE,
                'min_volume': MIN_VOLUME,
                'sort': 'dayvolume',
                'sort_dir': 'DESC',
                'offset': offset,
                'size': 100,
            }
            try:
                resp = requests.get(url, params=params, headers=API_HEADERS, timeout=30)
                data = resp.json()
                if data.get('ok') and data.get('stocks'):
                    for s in data['stocks']:
                        # Apply whitelist / market cap filter
                        exch = s.get('exchange_raw', s.get('exchange', ''))
                        mcap = s.get('market_cap', 0)
                        price = s.get('price', 0)
                        vol = s.get('avg_volume_3m', s.get('volume', 0))

                        if exch in BLOCKED_EXCHANGES:
                            continue
                        if mcap and mcap < MIN_MARKET_CAP:
                            continue
                        if price < MIN_PRICE or price > MAX_PRICE:
                            continue
                        if vol < MIN_VOLUME:
                            continue

                        candidates.append({
                            'symbol': s['symbol'],
                            'name': s.get('name', ''),
                            'price': price,
                            'volume': s.get('volume', 0),
                            'avg_volume_3m': s.get('avg_volume_3m', 0),
                            'market_cap': mcap,
                            'exchange': s.get('exchange', exch),
                            'exchange_raw': exch,
                            'country': s.get('country', ''),
                            'rrsp_eligible': s.get('rrsp_eligible', False),
                            'change_pct': s.get('change_pct', 0),
                        })
                    if len(data['stocks']) < 100:
                        break
                else:
                    break
            except Exception as e:
                logger.warning(f"Failed to fetch {region} offset={offset}: {e}")
                break

    # Deduplicate by symbol
    seen = set()
    unique = []
    for c in candidates:
        if c['symbol'] not in seen:
            seen.add(c['symbol'])
            unique.append(c)

    logger.info(f"Universe: {len(unique)} candidates after filtering")
    return unique


# ============================================================================
# STEP 2: SCORING FUNCTIONS
# ============================================================================

def safe_get(df, label, col=0, default=0.0):
    """Safely extract value from yfinance financial DataFrame."""
    if df is None or df.empty:
        return default
    for idx_label in df.index:
        if isinstance(idx_label, str) and label.lower() in str(idx_label).lower():
            try:
                val = df.loc[idx_label].iloc[col]
                if pd.isna(val):
                    return default
                if hasattr(val, 'values'):
                    val = val.values.flatten()[0]
                return float(val)
            except (IndexError, TypeError, ValueError):
                return default
    return default


def score_financial_health(tk, info):
    """
    Score financial health (0-100) using:
    - Altman Z''-Score (40% of sub-score)
    - Piotroski F-Score (35%)
    - Liquidity ratios (25%)

    Returns (score, details_dict, reject_flag)
    """
    details = {}
    reject = False

    try:
        bs = tk.balance_sheet
        inc = tk.financials
        cf = tk.cashflow
    except Exception:
        return 30.0, {'error': 'no_financials'}, False

    if bs is None or bs.empty or inc is None or inc.empty:
        return 30.0, {'error': 'no_financials'}, False

    # ── Extract balance sheet items ──
    total_assets = safe_get(bs, 'Total Assets')
    current_assets = safe_get(bs, 'Current Assets')
    current_liab = safe_get(bs, 'Current Liabilities')
    total_liab = safe_get(bs, 'Total Liabilities')
    retained_earnings = safe_get(bs, 'Retained Earnings')
    stockholder_eq = safe_get(bs, 'Stockholders Equity')
    if stockholder_eq == 0:
        stockholder_eq = safe_get(bs, 'Total Stockholder Equity')
    long_term_debt = safe_get(bs, 'Long Term Debt')
    inventory = safe_get(bs, 'Inventory')

    # ── Income statement ──
    ebit = safe_get(inc, 'EBIT')
    revenue = safe_get(inc, 'Total Revenue')
    net_income = safe_get(inc, 'Net Income')
    gross_profit = safe_get(inc, 'Gross Profit')

    # ── Cash flow ──
    op_cashflow = 0
    if cf is not None and not cf.empty:
        op_cashflow = safe_get(cf, 'Operating Cash Flow')
        if op_cashflow == 0:
            op_cashflow = safe_get(cf, 'Cash From Operating')

    # ── Hard reject: both net income AND operating cash flow negative ──
    if net_income < 0 and op_cashflow < 0:
        reject = True
        details['reject_reason'] = 'negative_income_and_cashflow'

    # ── Altman Z''-Score (non-manufacturing) ──
    z_score = 0
    if total_assets > 0 and total_liab > 0:
        working_capital = current_assets - current_liab
        x1 = working_capital / total_assets
        x2 = retained_earnings / total_assets
        x3 = ebit / total_assets
        x4 = stockholder_eq / total_liab if total_liab > 0 else 0
        z_score = 3.25 + 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4
        details['z_score'] = round(z_score, 2)

        if z_score < 1.5:
            reject = True
            details['reject_reason'] = f'z_score_distress_{z_score:.1f}'

    # Z-Score sub-score (0-100): Z < 1.5 = 0, Z > 4.0 = 100
    z_subscore = np.clip((z_score - 1.5) / 2.5 * 100, 0, 100)

    # ── Piotroski F-Score (0-9) ──
    f_score = 0
    f_criteria = {}

    # 1. Positive ROA
    f1 = 1 if net_income > 0 else 0
    f_criteria['positive_roi'] = f1
    f_score += f1

    # 2. Positive operating cash flow
    f2 = 1 if op_cashflow > 0 else 0
    f_criteria['positive_cfo'] = f2
    f_score += f2

    # 3. Improving ROA (need 2 periods)
    if inc.shape[1] >= 2 and total_assets > 0:
        prev_ni = safe_get(inc, 'Net Income', 1)
        prev_ta = safe_get(bs, 'Total Assets', 1) if bs.shape[1] >= 2 else total_assets
        roa_curr = net_income / total_assets
        roa_prev = prev_ni / prev_ta if prev_ta > 0 else 0
        f3 = 1 if roa_curr > roa_prev else 0
    else:
        f3 = 0
    f_criteria['improving_roa'] = f3
    f_score += f3

    # 4. Accrual quality (cash flow > net income)
    f4 = 1 if op_cashflow > net_income else 0
    f_criteria['accrual_quality'] = f4
    f_score += f4

    # 5. Deleveraging
    if bs.shape[1] >= 2 and total_assets > 0:
        prev_ltd = safe_get(bs, 'Long Term Debt', 1)
        prev_ta = safe_get(bs, 'Total Assets', 1) if bs.shape[1] >= 2 else total_assets
        lev_curr = long_term_debt / total_assets
        lev_prev = prev_ltd / prev_ta if prev_ta > 0 else 0
        f5 = 1 if lev_curr < lev_prev else 0
    else:
        f5 = 0
    f_criteria['deleveraging'] = f5
    f_score += f5

    # 6. Improving liquidity
    if bs.shape[1] >= 2 and current_liab > 0:
        prev_ca = safe_get(bs, 'Current Assets', 1)
        prev_cl = safe_get(bs, 'Current Liabilities', 1)
        cr_curr = current_assets / current_liab
        cr_prev = prev_ca / prev_cl if prev_cl > 0 else 0
        f6 = 1 if cr_curr > cr_prev else 0
    else:
        f6 = 0
    f_criteria['improving_liquidity'] = f6
    f_score += f6

    # 7. No dilution
    shares_curr = info.get('sharesOutstanding', 0) or 0
    shares_prev = safe_get(bs, 'Share Issued', 1) if bs.shape[1] >= 2 else shares_curr
    f7 = 1 if shares_curr > 0 and shares_curr <= shares_prev * 1.02 else 0  # 2% tolerance
    f_criteria['no_dilution'] = f7
    f_score += f7

    # 8. Improving gross margin
    if inc.shape[1] >= 2 and revenue > 0:
        prev_gp = safe_get(inc, 'Gross Profit', 1)
        prev_rev = safe_get(inc, 'Total Revenue', 1)
        gm_curr = gross_profit / revenue
        gm_prev = prev_gp / prev_rev if prev_rev > 0 else 0
        f8 = 1 if gm_curr > gm_prev else 0
    else:
        f8 = 0
    f_criteria['improving_margin'] = f8
    f_score += f8

    # 9. Improving asset turnover
    if inc.shape[1] >= 2 and total_assets > 0:
        prev_rev = safe_get(inc, 'Total Revenue', 1)
        prev_ta = safe_get(bs, 'Total Assets', 1) if bs.shape[1] >= 2 else total_assets
        at_curr = revenue / total_assets
        at_prev = prev_rev / prev_ta if prev_ta > 0 else 0
        f9 = 1 if at_curr > at_prev else 0
    else:
        f9 = 0
    f_criteria['improving_turnover'] = f9
    f_score += f9

    details['f_score'] = f_score
    details['f_criteria'] = f_criteria

    # F-Score sub-score: 0-9 mapped to 0-100
    f_subscore = (f_score / 9.0) * 100

    # ── Liquidity Ratios ──
    current_ratio = current_assets / current_liab if current_liab > 0 else 0
    quick_ratio = (current_assets - inventory) / current_liab if current_liab > 0 else 0
    debt_equity = total_liab / stockholder_eq if stockholder_eq > 0 else 999

    details['current_ratio'] = round(current_ratio, 2)
    details['quick_ratio'] = round(quick_ratio, 2)
    details['debt_equity'] = round(debt_equity, 2) if debt_equity < 100 else 'N/A'

    # Ratio sub-score
    cr_score = np.clip(current_ratio / 3.0 * 100, 0, 100)
    de_penalty = max(0, 100 - debt_equity * 30) if debt_equity < 100 else 0
    ratio_subscore = (cr_score * 0.6 + de_penalty * 0.4)

    # ── Combined financial health score ──
    score = z_subscore * 0.40 + f_subscore * 0.35 + ratio_subscore * 0.25
    return np.clip(score, 0, 100), details, reject


def score_momentum(hist, info):
    """
    Score multi-period price momentum (0-100).
    Uses 3m, 6m, 12m lookbacks + Clenow regression.
    Skips most recent 21 days (short-term reversal avoidance).
    """
    if hist is None or len(hist) < 65:
        return 50.0, {'error': 'insufficient_price_data'}

    close = hist['Close'].values.flatten()
    details = {}
    scores = []

    # Skip last 21 days for reversal avoidance
    skip = min(21, len(close) - 42)
    c = close[:-skip] if skip > 0 else close

    # 3-month momentum (63 days)
    if len(c) >= 63:
        mom_3m = (c[-1] / c[-63]) - 1.0
        details['mom_3m'] = round(mom_3m * 100, 1)
        scores.append(('3m', mom_3m, 0.35))

    # 6-month momentum (126 days)
    if len(c) >= 126:
        mom_6m = (c[-1] / c[-126]) - 1.0
        details['mom_6m'] = round(mom_6m * 100, 1)
        scores.append(('6m', mom_6m, 0.30))

    # 12-month momentum (252 days)
    if len(c) >= 252:
        mom_12m = (c[-1] / c[-252]) - 1.0
        details['mom_12m'] = round(mom_12m * 100, 1)
        scores.append(('12m', mom_12m, 0.20))

    # Clenow momentum (90-day exponential regression)
    if linregress is not None and len(c) >= 90:
        try:
            log_close = np.log(c[-90:])
            x = np.arange(90)
            slope, _, r_value, _, _ = linregress(x, log_close)
            clenow = ((1 + slope) ** 252) * (r_value ** 2)
            details['clenow'] = round(clenow, 3)
            clenow_norm = np.clip((clenow - 0.5) / 1.5, -1, 1)
            scores.append(('clenow', clenow_norm, 0.15))
        except Exception:
            pass

    if not scores:
        return 50.0, details

    total_w = sum(w for _, _, w in scores)
    weighted = sum(s * w for _, s, w in scores) / total_w

    # Map to 0-100: -50% return = 0, +200% = 100
    score = np.clip((weighted + 0.5) / 2.5 * 100, 0, 100)
    return score, details


def score_volume(hist, info):
    """Score volume confirmation (0-100): RVOL, OBV trend, liquidity."""
    if hist is None or len(hist) < 30:
        return 50.0, {}

    close = hist['Close'].values.flatten()
    volume = hist['Volume'].values.flatten()
    details = {}

    # RVOL: 20-day avg vs 90-day avg
    vol_20 = np.mean(volume[-20:]) if len(volume) >= 20 else np.mean(volume)
    vol_90 = np.mean(volume[-90:]) if len(volume) >= 90 else np.mean(volume)
    rvol = vol_20 / vol_90 if vol_90 > 0 else 1.0
    details['rvol'] = round(rvol, 2)

    # Volume trend (recent vs older)
    if len(volume) >= 30:
        vol_recent = np.mean(volume[-10:])
        vol_older = np.mean(volume[-30:-20])
        vol_trend = (vol_recent - vol_older) / vol_older if vol_older > 0 else 0
    else:
        vol_trend = 0
    details['vol_trend'] = round(vol_trend, 2)

    # OBV trend
    if len(close) >= 20:
        obv = np.zeros(len(close))
        for i in range(1, len(close)):
            if close[i] > close[i - 1]:
                obv[i] = obv[i - 1] + volume[i]
            elif close[i] < close[i - 1]:
                obv[i] = obv[i - 1] - volume[i]
            else:
                obv[i] = obv[i - 1]
        obv_slope = (obv[-1] - obv[-20]) / abs(obv[-20]) if abs(obv[-20]) > 1 else 0
        details['obv_trend'] = round(obv_slope, 3)
    else:
        obv_slope = 0

    # Liquidity check (penalize if avg vol < 500K)
    avg_vol = info.get('averageVolume', vol_20) or vol_20
    liquidity_factor = min(avg_vol / 500000, 1.0)
    details['avg_vol'] = int(avg_vol)

    # Combine
    rvol_score = np.clip(rvol / 3.0 * 50, 0, 50)
    trend_score = np.clip((vol_trend + 0.5) * 25, 0, 25)
    obv_score = np.clip((obv_slope + 0.5) * 25, 0, 25)

    raw = (rvol_score + trend_score + obv_score) * liquidity_factor
    return np.clip(raw, 0, 100), details


def score_technical(hist, info):
    """Score technical indicators (0-100): RSI(14) + EMA alignment."""
    if hist is None or len(hist) < 50:
        return 50.0, {}

    close = hist['Close'].values.flatten()
    details = {}

    # ── RSI(14) ──
    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = pd.Series(gains).rolling(14).mean().iloc[-1]
    avg_loss = pd.Series(losses).rolling(14).mean().iloc[-1]

    if avg_loss > 0:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    else:
        rsi = 100
    details['rsi'] = round(rsi, 1)

    # RSI scoring: 40-60 neutral, <30 buy opportunity, >80 overbought caution
    if rsi < 30:
        rsi_score = 75 + (30 - rsi)  # Oversold = buy signal
    elif rsi > 70:
        rsi_score = max(10, 50 - (rsi - 70) * 2)  # Overbought = caution
    else:
        rsi_score = 50  # Neutral

    # ── EMA alignment (9/21/50) ──
    ema_9 = pd.Series(close).ewm(span=9, adjust=False).mean().iloc[-1]
    ema_21 = pd.Series(close).ewm(span=21, adjust=False).mean().iloc[-1]
    sma_50 = np.mean(close[-50:])

    alignment = 0
    if close[-1] > ema_9:
        alignment += 1
    if ema_9 > ema_21:
        alignment += 1
    if ema_21 > sma_50:
        alignment += 1

    details['ema_alignment'] = alignment  # 0-3
    details['price_vs_sma50'] = round((close[-1] / sma_50 - 1) * 100, 1)

    ma_score = alignment / 3.0 * 100

    return np.clip(rsi_score * 0.5 + ma_score * 0.5, 0, 100), details


def score_earnings(tk, info):
    """Score earnings momentum / PEAD (0-100)."""
    try:
        earnings = tk.earnings_dates
        if earnings is None or len(earnings) < 1:
            return 50.0, {'status': 'no_data'}

        recent = earnings.dropna(subset=['Reported EPS', 'EPS Estimate']).head(4)
        if len(recent) < 1:
            return 50.0, {'status': 'no_reported_eps'}

        actual = float(recent['Reported EPS'].iloc[0])
        estimate = float(recent['EPS Estimate'].iloc[0])
        surprise = actual - estimate

        if estimate != 0:
            surprise_pct = surprise / abs(estimate) * 100
        else:
            surprise_pct = surprise * 100

        # Days since last earnings
        last_date = recent.index[0]
        now = pd.Timestamp.now(tz=last_date.tzinfo) if last_date.tzinfo else pd.Timestamp.now()
        days_since = (now - last_date).days

        # PEAD decay: strongest in first 60 days
        if days_since <= 60:
            pead_factor = 1.0
        elif days_since <= 180:
            pead_factor = 0.5
        else:
            pead_factor = 0.1

        details = {
            'surprise_pct': round(surprise_pct, 1),
            'days_since_earnings': days_since,
            'pead_window': 'active' if days_since <= 60 else 'fading' if days_since <= 180 else 'expired',
        }

        # Score: +50% surprise with active PEAD = 100
        raw = 50 + (surprise_pct * pead_factor * 0.5)
        return np.clip(raw, 0, 100), details

    except Exception:
        return 50.0, {'status': 'error'}


def score_smart_money(info):
    """Score smart money signals (0-100): institutional + insider buying."""
    details = {}
    score = 50.0  # Neutral baseline

    # Institutional ownership
    inst_pct = info.get('heldPercentInstitutions', 0) or 0
    inst_holders = info.get('institutionCount', 0) or 0
    details['inst_pct'] = round(inst_pct * 100, 1) if inst_pct else 0
    details['inst_holders'] = inst_holders

    # Institutional score: 10-60% ownership is ideal
    if inst_pct > 0.10 and inst_pct < 0.60:
        score += 15
    elif inst_pct >= 0.60:
        score += 5  # Too crowded
    elif inst_pct > 0.05:
        score += 8

    # Number of institutional holders
    if inst_holders >= 10:
        score += 10
    elif inst_holders >= 5:
        score += 5

    # Insider ownership (management alignment)
    insider_pct = info.get('heldPercentInsiders', 0) or 0
    details['insider_pct'] = round(insider_pct * 100, 1) if insider_pct else 0
    if 0.05 < insider_pct < 0.30:
        score += 10  # Moderate insider ownership = aligned management
    elif insider_pct >= 0.30:
        score += 5  # Very high insider = less float

    # Short interest (contrarian signal)
    short_ratio = info.get('shortRatio', 0) or 0
    short_pct = info.get('shortPercentOfFloat', 0) or 0
    details['short_ratio'] = round(short_ratio, 1)
    details['short_pct'] = round(short_pct * 100, 1) if short_pct else 0

    if short_ratio > 5 and short_pct > 0.15:
        score += 10  # High squeeze potential
    elif short_ratio > 3:
        score += 5

    return np.clip(score, 0, 100), details


def score_quality(hist):
    """
    Score momentum quality (0-100) using Frog-in-the-Pan metric.
    Smooth, consistent momentum > choppy, volatile jumps.
    """
    if hist is None or len(hist) < 90:
        return 50.0, {}

    close = hist['Close'].values.flatten()
    details = {}

    # Use last 252 days or available
    window = min(252, len(close) - 1)
    prices = close[-(window + 1):]
    daily_returns = np.diff(prices) / prices[:-1]

    pct_positive = np.sum(daily_returns > 0) / len(daily_returns)
    overall_return = (prices[-1] / prices[0]) - 1.0

    # Frog-in-the-Pan: winners with more positive days = higher quality
    sign_return = np.sign(overall_return) if overall_return != 0 else 0
    fip = sign_return * (np.sum(daily_returns < 0) / len(daily_returns) -
                         np.sum(daily_returns > 0) / len(daily_returns))
    details['fip'] = round(fip, 3)
    details['pct_positive_days'] = round(pct_positive * 100, 1)

    # Annualized volatility (lower = smoother)
    ann_vol = np.std(daily_returns) * np.sqrt(252)
    details['ann_volatility'] = round(ann_vol * 100, 1)

    # FIP score: more negative = better (for winning stocks)
    fip_score = np.clip(((-fip) + 0.3) / 0.6 * 60, 0, 60)

    # Vol score: lower vol = better quality momentum
    vol_score = np.clip((1.5 - ann_vol) / 1.2 * 40, 0, 40)

    return np.clip(fip_score + vol_score, 0, 100), details


# ============================================================================
# STEP 3: COMPOSITE SCORER
# ============================================================================

def score_stock(symbol, hist, tk, info):
    """
    Calculate full composite score for a single stock.
    Returns (score, rating, details, reject_flag)
    """
    details = {'symbol': symbol}

    # Financial Health (30%)
    health_score, health_details, reject = score_financial_health(tk, info)
    details['financial_health'] = {'score': round(health_score, 1), **health_details}

    # Momentum (25%)
    mom_score, mom_details = score_momentum(hist, info)
    details['momentum'] = {'score': round(mom_score, 1), **mom_details}

    # Volume (10%)
    vol_score, vol_details = score_volume(hist, info)
    details['volume'] = {'score': round(vol_score, 1), **vol_details}

    # Technical (10%)
    tech_score, tech_details = score_technical(hist, info)
    details['technical'] = {'score': round(tech_score, 1), **tech_details}

    # Earnings (10%)
    earn_score, earn_details = score_earnings(tk, info)
    details['earnings'] = {'score': round(earn_score, 1), **earn_details}

    # Smart Money (10%)
    smart_score, smart_details = score_smart_money(info)
    details['smart_money'] = {'score': round(smart_score, 1), **smart_details}

    # Quality (5%)
    qual_score, qual_details = score_quality(hist)
    details['quality'] = {'score': round(qual_score, 1), **qual_details}

    # Composite
    composite = (
        health_score * WEIGHTS['financial_health'] +
        mom_score * WEIGHTS['momentum'] +
        vol_score * WEIGHTS['volume'] +
        tech_score * WEIGHTS['technical'] +
        earn_score * WEIGHTS['earnings'] +
        smart_score * WEIGHTS['smart_money'] +
        qual_score * WEIGHTS['quality']
    )

    # Rating
    if composite >= 75:
        rating = 'STRONG_BUY'
    elif composite >= 62:
        rating = 'BUY'
    elif composite >= 48:
        rating = 'HOLD'
    elif composite >= 35:
        rating = 'SELL'
    else:
        rating = 'STRONG_SELL'

    # Risk parameters
    price = info.get('currentPrice', info.get('regularMarketPrice', 0)) or 0
    if price == 0 and hist is not None and len(hist) > 0:
        price = float(hist['Close'].values.flatten()[-1])

    details['risk'] = {
        'entry_price': round(price, 4),
        'stop_loss_pct': 15.0,
        'take_profit_pct': 30.0,
        'stop_loss_price': round(price * 0.85, 4),
        'take_profit_price': round(price * 1.30, 4),
        'max_hold_days': 90,
        'position_size_pct': 1.5,  # Quarter-Kelly
    }

    return round(composite, 2), rating, details, reject


# ============================================================================
# STEP 4: MAIN PIPELINE
# ============================================================================

def run_scoring_pipeline(candidates):
    """Score all candidates and return ranked picks."""
    results = []
    rejected = 0
    errors = 0

    logger.info(f"Scoring {len(candidates)} candidates...")

    for i, cand in enumerate(candidates):
        symbol = cand['symbol']
        logger.info(f"[{i + 1}/{len(candidates)}] Scoring {symbol}...")

        try:
            # Fetch data
            tk = yf.Ticker(symbol)
            info = tk.info or {}

            # Download historical prices
            hist = yf.download(symbol, period="18mo", progress=False)
            if hist is None or len(hist) < 30:
                logger.warning(f"  {symbol}: insufficient price history, skipping")
                errors += 1
                continue

            # Score
            composite, rating, details, reject = score_stock(symbol, hist, tk, info)

            if reject:
                logger.info(f"  {symbol}: REJECTED - {details.get('financial_health', {}).get('reject_reason', 'unknown')}")
                rejected += 1
                continue

            results.append({
                'symbol': symbol,
                'name': cand.get('name', info.get('shortName', '')),
                'price': cand.get('price', details.get('risk', {}).get('entry_price', 0)),
                'composite_score': composite,
                'rating': rating,
                'market_cap': cand.get('market_cap', info.get('marketCap', 0)),
                'exchange': cand.get('exchange', ''),
                'country': cand.get('country', ''),
                'rrsp_eligible': cand.get('rrsp_eligible', False),
                'avg_volume': cand.get('avg_volume_3m', info.get('averageVolume', 0)),
                'details': details,
            })

        except Exception as e:
            logger.warning(f"  {symbol}: ERROR - {e}")
            errors += 1

        # Rate limit
        time.sleep(RATE_LIMIT_DELAY)

    # Sort by composite score descending
    results.sort(key=lambda x: x['composite_score'], reverse=True)

    logger.info(f"Scoring complete: {len(results)} scored, {rejected} rejected, {errors} errors")
    return results


def post_picks_to_api(picks):
    """POST daily picks to PHP API for storage."""
    url = f"{API_BASE}/penny_stock_picks.php?action=store_picks&key={ADMIN_KEY}"

    payload = {
        'date': datetime.date.today().strftime('%Y-%m-%d'),
        'total_scored': len(picks),
        'picks': []
    }

    for p in picks[:MAX_PICKS]:
        pick_data = {
            'symbol': p['symbol'],
            'name': p['name'],
            'price': p['price'],
            'composite_score': p['composite_score'],
            'rating': p['rating'],
            'market_cap': p['market_cap'],
            'exchange': p['exchange'],
            'country': p['country'],
            'rrsp_eligible': p['rrsp_eligible'],
            'avg_volume': p['avg_volume'],
            'stop_loss_pct': 15.0,
            'take_profit_pct': 30.0,
            'max_hold_days': 90,
            'position_size_pct': 1.5,
            # Factor scores
            'health_score': p['details'].get('financial_health', {}).get('score', 0),
            'momentum_score': p['details'].get('momentum', {}).get('score', 0),
            'volume_score': p['details'].get('volume', {}).get('score', 0),
            'technical_score': p['details'].get('technical', {}).get('score', 0),
            'earnings_score': p['details'].get('earnings', {}).get('score', 0),
            'smart_money_score': p['details'].get('smart_money', {}).get('score', 0),
            'quality_score': p['details'].get('quality', {}).get('score', 0),
            # Key metrics
            'z_score': p['details'].get('financial_health', {}).get('z_score', 0),
            'f_score': p['details'].get('financial_health', {}).get('f_score', 0),
            'current_ratio': p['details'].get('financial_health', {}).get('current_ratio', 0),
            'rsi': p['details'].get('technical', {}).get('rsi', 0),
            'ema_alignment': p['details'].get('technical', {}).get('ema_alignment', 0),
            'rvol': p['details'].get('volume', {}).get('rvol', 0),
            'mom_3m': p['details'].get('momentum', {}).get('mom_3m', 0),
            'mom_6m': p['details'].get('momentum', {}).get('mom_6m', 0),
            'inst_pct': p['details'].get('smart_money', {}).get('inst_pct', 0),
            'short_pct': p['details'].get('smart_money', {}).get('short_pct', 0),
            'ann_volatility': p['details'].get('quality', {}).get('ann_volatility', 0),
        }
        payload['picks'].append(pick_data)

    try:
        resp = requests.post(url, json=payload, headers=API_HEADERS, timeout=60)
        result = resp.json()
        if result.get('ok'):
            logger.info(f"Successfully stored {len(payload['picks'])} picks via API")
        else:
            logger.error(f"API error: {result.get('error', 'unknown')}")
        return result
    except Exception as e:
        logger.error(f"Failed to POST picks: {e}")
        return {'ok': False, 'error': str(e)}


def save_local_report(picks, all_results):
    """Save local JSON report for debugging and git tracking."""
    report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              '..', 'findstocks', 'portfolio2', 'data')
    os.makedirs(report_dir, exist_ok=True)

    today = datetime.date.today().strftime('%Y-%m-%d')
    report = {
        'date': today,
        'generated_at': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'total_candidates': len(all_results),
        'top_picks_count': min(MAX_PICKS, len(picks)),
        'top_picks': [],
        'all_scores': [],
    }

    for p in picks[:MAX_PICKS]:
        report['top_picks'].append({
            'symbol': p['symbol'],
            'name': p['name'],
            'price': p['price'],
            'score': p['composite_score'],
            'rating': p['rating'],
            'exchange': p['exchange'],
            'country': p['country'],
            'rrsp_eligible': p['rrsp_eligible'],
            'z_score': p['details'].get('financial_health', {}).get('z_score', 0),
            'f_score': p['details'].get('financial_health', {}).get('f_score', 0),
            'rsi': p['details'].get('technical', {}).get('rsi', 0),
            'mom_3m': p['details'].get('momentum', {}).get('mom_3m', 0),
            'stop_loss': p['details'].get('risk', {}).get('stop_loss_price', 0),
            'take_profit': p['details'].get('risk', {}).get('take_profit_price', 0),
        })

    for r in all_results:
        report['all_scores'].append({
            'symbol': r['symbol'],
            'score': r['composite_score'],
            'rating': r['rating'],
        })

    report_file = os.path.join(report_dir, 'penny_picks_latest.json')
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    logger.info(f"Saved local report: {report_file}")
    return report_file


# ============================================================================
# MAIN
# ============================================================================

def main():
    logger.info("=" * 60)
    logger.info("PENNY STOCK DAILY PICKS ENGINE")
    logger.info(f"Date: {datetime.date.today()}")
    logger.info("=" * 60)

    # Step 1: Get universe
    logger.info("Step 1: Fetching penny stock universe...")
    candidates = get_penny_universe()
    if not candidates:
        logger.error("No candidates found. Exiting.")
        sys.exit(1)

    # Step 2: Score all candidates
    logger.info("Step 2: Scoring candidates...")
    results = run_scoring_pipeline(candidates)
    if not results:
        logger.error("No stocks survived scoring. Exiting.")
        sys.exit(1)

    # Step 3: Select top picks
    top_picks = results[:MAX_PICKS]
    logger.info(f"\nStep 3: Top {len(top_picks)} picks:")
    logger.info("-" * 60)
    for i, p in enumerate(top_picks):
        logger.info(f"  {i + 1:2d}. {p['symbol']:8s}  Score: {p['composite_score']:5.1f}  "
                     f"Rating: {p['rating']:12s}  ${p['price']:.2f}  "
                     f"({p['exchange']})")
    logger.info("-" * 60)

    # Step 4: Save local report
    logger.info("Step 4: Saving local report...")
    save_local_report(top_picks, results)

    # Step 5: POST to API
    logger.info("Step 5: Posting picks to API...")
    api_result = post_picks_to_api(top_picks)

    # Summary
    logger.info("=" * 60)
    buy_count = sum(1 for p in top_picks if 'BUY' in p['rating'])
    hold_count = sum(1 for p in top_picks if p['rating'] == 'HOLD')
    avg_score = np.mean([p['composite_score'] for p in top_picks])
    logger.info(f"SUMMARY:")
    logger.info(f"  Universe: {len(candidates)} candidates")
    logger.info(f"  Scored:   {len(results)} passed filters")
    logger.info(f"  Top {len(top_picks)} picks: {buy_count} BUY, {hold_count} HOLD")
    logger.info(f"  Avg score: {avg_score:.1f}")
    logger.info(f"  API:      {'OK' if api_result.get('ok') else 'FAILED'}")
    logger.info("=" * 60)

    return results


if __name__ == '__main__':
    main()
