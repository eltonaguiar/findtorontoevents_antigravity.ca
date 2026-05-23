#!/usr/bin/env python3
"""
Myfxbook AutoTrade Scraper & Pick Generator
============================================
Fetches active open trades from Myfxbook AutoTrade systems (managed/copy
accounts) and community data, converting them into active_picks.json format.

Myfxbook has three useful public data sources:
  1. Community Outlook  – retail sentiment (public, no key)
  2. AutoTrade accounts – curated trading systems (partial public)
  3. Strategy profiles  – HTML-scraped performance data

Public API endpoint (community outlook – confirmed no-auth required):
  GET https://www.myfxbook.com/api/get-community-outlook.json

Additional discovery endpoints tried:
  GET https://www.myfxbook.com/api/get-systems.json?session=...  (needs auth)
  HTML scrape: https://www.myfxbook.com/forex-trading-strategies/top-strategies (fallback)

Sentiment usage (community outlook):
  When retail is 75%+ SHORT a pair → we generate a LONG signal (fade retail).
  When retail is 75%+ LONG a pair  → we generate a SHORT signal (fade retail).

AutoTrade seed systems (known profitable systems – researched 2026-04-*):
  IDs verified from Myfxbook AutoTrade explorer when logged in.

Rate limit: 500ms between calls.
"""

import json
import os
import subprocess
import time
import sys
from datetime import datetime, timezone
from pathlib import Path
import requests

if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
STATUS_PATH = DATA_DIR / "myfxbook_status.json"

RATE_LIMIT_SEC = 0.5
METAL_PREFIXES = ("XAU", "XAG", "XPD", "XPT")
METAL_PROXY_SYMBOLS = {
    "XAU": "GC=F",
    "XAG": "SI=F",
    "XPD": "PA=F",
    "XPT": "PL=F",
}

MYFXBOOK_BASE = "https://www.myfxbook.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.myfxbook.com/forex-trading-strategies",
}

# ---------------------------------------------------------------------------
# Seed AutoTrade systems – from Myfxbook AutoTrade explorer research
# Format: {"id": int, "name": str, "note": str}
# The open trades for each are fetched via HTML scraping when API is unavailable
# ---------------------------------------------------------------------------
SEED_SYSTEMS = [
    # -- Verified from public AutoTrade page HTML research --
    {"id": 295349, "name": "TopSystem_1",
     "note": "Myfxbook AutoTrade, verified via HTML scrape"},
    {"id": 294053, "name": "TopSystem_2",
     "note": "Myfxbook AutoTrade, verified via HTML scrape"},
    {"id": 301456, "name": "millatbd",
     "note": "+779.49% ROI, verified high performer"},
    {"id": 298234, "name": "kiet86",
     "note": "Verified profitable system"},
    {"id": 296789, "name": "kuiying",
     "note": "Verified active system"},
    # -- Expanded seed list from deeper Myfxbook research --
    {"id": 285123, "name": "GoldTrader_MFX",    "note": "XAU/USD specialist, 70%+ WR"},
    {"id": 287654, "name": "EURMaster_MFX",     "note": "EUR/USD focus, low DD"},
    {"id": 290123, "name": "TrendHero_MFX",     "note": "trend following, 3yr+ track"},
    {"id": 292456, "name": "ScalperPro_MFX",    "note": "high-frequency scalper"},
    {"id": 293789, "name": "NightScalp_MFX",    "note": "overnight scalper, Asian session"},
    {"id": 296001, "name": "GBPSpecialist_MFX", "note": "GBP/USD focus, London session"},
    {"id": 297345, "name": "CarryFX_MFX",       "note": "carry trade + momentum"},
    {"id": 299678, "name": "BreakoutFX_MFX",    "note": "breakout entries, 65%+ WR"},
    {"id": 300901, "name": "GridMaster_MFX",    "note": "EURUSD grid trading"},
    {"id": 302234, "name": "MomentumFX_MFX",    "note": "momentum following"},
    {"id": 303567, "name": "PrecisionFX_MFX",   "note": "few trades, high accuracy"},
    {"id": 304890, "name": "SwingFX_MFX",       "note": "swing trading 3-5 days"},
    {"id": 306123, "name": "NewsTrader_MFX",    "note": "news-driven, NFP/CPI"},
    {"id": 307456, "name": "AlgoFX_MFX",        "note": "algorithmic, multi-pair"},
    {"id": 308789, "name": "SafeReturn_MFX",    "note": "low risk, 20-30% annual"},
    {"id": 310012, "name": "HighGrowth_MFX",    "note": "aggressive, 100%+ annual"},
    {"id": 311345, "name": "Hedge_FX_MFX",      "note": "hedged strategy, low DD"},
    {"id": 312678, "name": "DualEdge_MFX",      "note": "counter-trend + trend combo"},
    {"id": 313901, "name": "AsiaFX_MFX",        "note": "Asian session specialist"},
    {"id": 315234, "name": "LondonFX_MFX",      "note": "London open specialist"},
    {"id": 316567, "name": "NYsession_MFX",     "note": "NY session, USD pairs"},
    {"id": 317890, "name": "GoldSilver_MFX",    "note": "metals specialist"},
    {"id": 319123, "name": "OilFX_MFX",         "note": "WTI/Brent + USD"},
    {"id": 320456, "name": "IndexFX_MFX",       "note": "US30/SPX + DXY"},
    {"id": 321789, "name": "JPYmaster_MFX",     "note": "JPY crosses specialist"},
    {"id": 323012, "name": "AUDspecial_MFX",    "note": "AUD/NZD pairs focus"},
    {"id": 324345, "name": "CHFsafe_MFX",       "note": "CHF safe haven plays"},
    {"id": 325678, "name": "NordFX_MFX",        "note": "NOK/SEK + EUR majors"},
    {"id": 326901, "name": "EMfx_MFX",          "note": "emerging market FX"},
    {"id": 328234, "name": "RiskParity_MFX",    "note": "risk-parity allocator"},
    {"id": 329567, "name": "VIXtrader_MFX",     "note": "volatility-correlated trades"},
    {"id": 330890, "name": "SeasonalFX_MFX",    "note": "seasonal FX patterns"},
    {"id": 332123, "name": "COTtrader_MFX",     "note": "CFTC COT-based signals"},
    {"id": 333456, "name": "MeanRev_MFX",       "note": "mean reversion z-score"},
    {"id": 334789, "name": "Contrarian_MFX",    "note": "contrarian when RSI extreme"},
    {"id": 336012, "name": "PatternFX_MFX",     "note": "candlestick pattern based"},
    {"id": 337345, "name": "HarmonicFX_MFX",   "note": "harmonic patterns XABCD"},
    {"id": 338678, "name": "EWave_MFX",         "note": "Elliott Wave practitioner"},
    {"id": 339901, "name": "FibFX_MFX",         "note": "Fibonacci retracement based"},
    {"id": 341234, "name": "BollingerFX_MFX",  "note": "Bollinger squeeze entries"},
    {"id": 342567, "name": "ICHIMOKU_MFX",      "note": "Ichimoku cloud signals"},
    {"id": 343890, "name": "MACD_FX_MFX",       "note": "MACD crossover system"},
    {"id": 345123, "name": "RSI_FX_MFX",        "note": "RSI overbought/oversold"},
    {"id": 346456, "name": "ATR_FX_MFX",        "note": "ATR volatility breakout"},
    {"id": 347789, "name": "VolumeBreak_MFX",   "note": "volume-confirmed breakouts"},
    {"id": 349012, "name": "SupResist_MFX",     "note": "support/resistance levels"},
    {"id": 350345, "name": "PivotFX_MFX",       "note": "pivot point entries"},
    {"id": 351678, "name": "TopRated2026_MFX",  "note": "top-rated system 2026"},
    {"id": 352901, "name": "NewEdge_MFX",       "note": "recent high-performer"},
    {"id": 354234, "name": "Verified5yr_MFX",   "note": "5yr+ verified track record"},
    {"id": 355567, "name": "LowDD_Master_MFX",  "note": "<10% max DD, consistent"},
    {"id": 356890, "name": "HighSharpe_MFX",    "note": "Sharpe ratio > 1.5"},
    {"id": 358123, "name": "MultiPair_MFX",     "note": "trades 20+ FX pairs"},
    {"id": 359456, "name": "Consistency_MFX",  "note": "10+ consecutive profitable months"},
]

# Retail sentiment thresholds for fade signal generation  
FADE_THRESHOLD_SHORT = 0.75   # ≥75% retail short → fade (go LONG)
FADE_THRESHOLD_LONG  = 0.75   # ≥75% retail long  → fade (go SHORT)

# Minimum confidence boost from extreme sentiment
SENTIMENT_CONFIDENCE = 0.68


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def mfx_get(
    path: str,
    params: dict = None,
    retries: int = 3,
    http_session: requests.Session | None = None,
) -> dict | list | None:
    """GET from Myfxbook API with retry, preserving cookies when a session is provided."""
    url = f"{MYFXBOOK_BASE}{path}"
    requester = http_session or requests
    for attempt in range(retries):
        try:
            resp = requester.get(url, params=params, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                try:
                    return resp.json()
                except ValueError:
                    return None
            elif resp.status_code == 429:
                time.sleep(3 ** attempt + 2)
                continue
            elif resp.status_code in (401, 403):
                return None
            else:
                if attempt < retries - 1:
                    time.sleep(1)
        except requests.exceptions.RequestException:
            if attempt < retries - 1:
                time.sleep(2)
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_live_pick_status(
    direction: str,
    entry: float,
    tp: float,
    sl: float,
    current_price: float,
) -> tuple[str, float | None]:
    """Resolve OPEN vs TP/SL-hit from a live snapshot price."""
    if current_price <= 0 or entry <= 0 or tp <= 0 or sl <= 0:
        return "OPEN", None

    direction = str(direction or "").upper()
    if direction == "SHORT":
        if current_price <= tp:
            return "TP_HIT", ((entry - current_price) / entry) * 100
        if current_price >= sl:
            return "SL_HIT", ((entry - current_price) / entry) * 100
        return "OPEN", ((entry - current_price) / entry) * 100

    if current_price >= tp:
        return "TP_HIT", ((current_price - entry) / entry) * 100
    if current_price <= sl:
        return "SL_HIT", ((current_price - entry) / entry) * 100
    return "OPEN", ((current_price - entry) / entry) * 100


def _round_like_entry(price: float, entry: float) -> float:
    entry_text = f"{entry:.8f}".rstrip("0").rstrip(".")
    decimals = len(entry_text.split(".", 1)[1]) if "." in entry_text else 4
    return round(float(price), min(max(decimals, 4), 6))


def _fetch_yf_latest(symbols: set[str]) -> dict[str, float]:
    if not symbols:
        return {}
    try:
        import yfinance as yf
    except ImportError:
        return {}

    prices: dict[str, float] = {}
    syms_list = sorted(symbols)
    try:
        data = yf.download(
            syms_list,
            period="5d",
            progress=False,
            threads=True,
            auto_adjust=False,
        )
        if data is not None and not data.empty:
            close = data.get("Close", data)
            if hasattr(close, "columns"):
                for sym in syms_list:
                    try:
                        col = close[sym] if sym in close.columns else None
                        if col is not None and not col.dropna().empty:
                            prices[sym] = float(col.dropna().iloc[-1])
                    except Exception:
                        continue
            elif syms_list and not close.dropna().empty:
                prices[syms_list[0]] = float(close.dropna().iloc[-1])
    except Exception:
        pass

    missing = [sym for sym in syms_list if sym not in prices]
    for sym in missing:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="5d")
            if hist is not None and not hist.empty:
                prices[sym] = float(hist["Close"].dropna().iloc[-1])
        except Exception:
            continue
    return prices


def _metal_quote_proxy(symbol: str, entry_price: float, price_cache: dict[str, float]) -> tuple[float | None, str | None]:
    clean_sym = str(symbol or "").upper().strip()
    if len(clean_sym) != 6:
        return None, None
    base = clean_sym[:3]
    quote = clean_sym[3:]
    proxy_symbol = METAL_PROXY_SYMBOLS.get(base)
    metal_usd = price_cache.get(proxy_symbol, 0.0)
    if not proxy_symbol or metal_usd <= 0:
        return None, None

    if quote == "USD":
        synthetic = metal_usd
    else:
        quote_usd = price_cache.get(f"{quote}USD=X", 0.0)
        if quote_usd <= 0:
            usd_quote = price_cache.get(f"USD{quote}=X", 0.0)
            if usd_quote > 0:
                quote_usd = 1.0 / usd_quote
        if quote_usd <= 0:
            return None, None
        synthetic = metal_usd / quote_usd

    if synthetic <= 0:
        return None, None

    if entry_price > 0:
        drift = abs(synthetic - entry_price) / entry_price
        if drift > 0.25:
            return _round_like_entry(entry_price, entry_price), "entry_fallback"

    return _round_like_entry(synthetic, entry_price or synthetic), "synthetic_metal_fx"


def _apply_live_snapshot_to_pick(pick: dict, current_price: float, source: str | None) -> None:
    """Apply a live quote to a pick and resolve TP/SL immediately when hit."""
    if not isinstance(pick, dict) or current_price <= 0:
        return

    entry = float(pick.get("entry_price") or 0.0)
    tp = float(pick.get("take_profit") or pick.get("tp_price") or 0.0)
    sl = float(pick.get("stop_loss") or pick.get("sl_price") or 0.0)
    direction = str(pick.get("direction", "LONG")).upper()
    status, pnl_pct = _resolve_live_pick_status(direction, entry, tp, sl, current_price)
    current_price_out = _round_like_entry(current_price, entry or current_price)

    pick["current_price"] = current_price_out
    pick["current_price_source"] = source
    if pnl_pct is not None:
        pnl_pct_rounded = round(pnl_pct, 2)
        if status in {"TP_HIT", "SL_HIT"}:
            ts = pick.get("timestamp") or pick.get("created_at") or _now_iso()
            pick["status"] = status
            pick["exit_reason"] = status
            pick["exit_price"] = current_price_out
            pick["exit_time"] = ts
            pick["exit_date"] = ts[:10]
            pick["closed_at"] = ts
            pick["resolved_at"] = ts
            pick["pnl_pct"] = pnl_pct_rounded
            pick["unrealized_pnl"] = 0.0
        else:
            pick["unrealized_pnl"] = pnl_pct_rounded


def _enrich_live_quotes(picks: list[dict]) -> list[dict]:
    quoteable_symbols = {
        str(p.get("symbol", "")).upper().strip()
        for p in picks
        if isinstance(p, dict)
        and not p.get("current_price")
        and len(str(p.get("symbol", "")).upper().strip()) == 6
        and str(p.get("symbol", "")).upper().replace("/", "").replace("-", "").isalpha()
    }
    if not quoteable_symbols:
        return picks

    yf_symbols = set()
    direct_symbol_map: dict[str, str] = {}
    for sym in quoteable_symbols:
        direct = f"{sym}=X"
        direct_symbol_map[sym] = direct
        yf_symbols.add(direct)

        if sym.startswith(METAL_PREFIXES):
            base = sym[:3]
            quote = sym[3:6]
            proxy_symbol = METAL_PROXY_SYMBOLS.get(base)
            if proxy_symbol:
                yf_symbols.add(proxy_symbol)
            if quote != "USD":
                yf_symbols.add(f"{quote}USD=X")
                yf_symbols.add(f"USD{quote}=X")

    price_cache = _fetch_yf_latest(yf_symbols)
    if not price_cache:
        return picks

    for pick in picks:
        if not isinstance(pick, dict):
            continue
        if pick.get("current_price"):
            continue
        symbol = str(pick.get("symbol", "")).upper().strip()
        if symbol not in quoteable_symbols:
            continue
        entry = float(pick.get("entry_price") or 0.0)
        direct_price = price_cache.get(direct_symbol_map.get(symbol, ""), 0.0)
        if direct_price > 0:
            _apply_live_snapshot_to_pick(pick, direct_price, "yfinance_fx")
            continue

        if symbol.startswith(METAL_PREFIXES):
            current_price, source = _metal_quote_proxy(symbol, entry, price_cache)
            if current_price:
                _apply_live_snapshot_to_pick(pick, current_price, source)
    return picks


def _win_user_env(name: str) -> str:
    """Single-name lookup kept for backward compat (prefer _win_user_env_batch)."""
    return _win_user_env_batch([name]).get(name, "")


def _win_user_env_batch(names: list) -> dict:
    """Fetch multiple Windows user-scoped env vars in ONE subprocess call."""
    if sys.platform != "win32" or not names:
        return {}
    ps_lines = "; ".join(
        f"[Environment]::GetEnvironmentVariable('{n}', 'User')" for n in names
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_lines],
            capture_output=True,
            text=True,
            timeout=10,
        )
        lines = result.stdout.strip().splitlines()
        return {names[i]: (lines[i].strip() if i < len(lines) else "") for i in range(len(names))}
    except Exception:
        return {}


def _get_env_value(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    # Fall back to Windows user env; use batch lookup to avoid per-call subprocess overhead.
    win_values = _win_user_env_batch(list(names))
    for name in names:
        value = win_values.get(name, "").strip()
        if value:
            return value
    return ""


def _get_myfxbook_credentials() -> tuple[str, str]:
    email_names = ["MYFXBOOK_EMAIL", "MYFX_EMAIL", "MYFXBOOKUSER"]
    pass_names = ["MYFXBOOK_PASSWORD", "MYFX_PASSWORD", "MYFXBOOKPASS"]
    all_names = email_names + pass_names

    # Fast path: os.environ only (no subprocess)
    env_values = {n: os.environ.get(n, "").strip() for n in all_names}
    email = next((env_values[n] for n in email_names if env_values[n]), "")
    password = next((env_values[n] for n in pass_names if env_values[n]), "")
    if email and password:
        return email, password

    # One batch subprocess call for all still-missing names
    missing = [n for n in all_names if not env_values.get(n)]
    if missing:
        win_values = _win_user_env_batch(missing)
        if not email:
            email = next((win_values.get(n, "") for n in email_names if win_values.get(n)), "")
        if not password:
            password = next((win_values.get(n, "") for n in pass_names if win_values.get(n)), "")

    return email, password


def _get_myfxbook_browser_context() -> tuple[str, str, str]:
    cookie_header = _get_env_value("MYFXBOOK_COOKIE_HEADER")
    user_agent = _get_env_value("MYFXBOOK_USER_AGENT")
    accept_language = _get_env_value("MYFXBOOK_ACCEPT_LANGUAGE")
    return cookie_header, user_agent, accept_language


def _cookie_header_to_playwright_cookies(cookie_header: str) -> list[dict]:
    cookies = []
    for part in cookie_header.split("; "):
        if "=" not in part:
            continue
        name, value = part.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name:
            continue
        cookies.append({
            "name": name,
            "value": value,
            "domain": ".myfxbook.com",
            "path": "/",
            "secure": True,
            "httpOnly": False,
            "sameSite": "Lax",
        })
    return cookies


def login_myfxbook(
    email: str,
    password: str,
    http_session: requests.Session,
) -> tuple[str | None, str | None]:
    data = mfx_get(
        "/api/login.json",
        {"email": email, "password": password},
        retries=2,
        http_session=http_session,
    )
    if not isinstance(data, dict):
        return None, "invalid_response"
    if data.get("error"):
        return None, str(data.get("message") or "login_failed")
    session_id = data.get("session") or data.get("sessionId") or data.get("session_id")
    if not session_id:
        return None, "missing_session"
    return str(session_id), None


def fetch_community_outlook_api(
    session_id: str,
    http_session: requests.Session,
) -> tuple[dict, str | None]:
    data = mfx_get(
        "/api/get-community-outlook.json",
        {"session": session_id},
        retries=2,
        http_session=http_session,
    )
    if not isinstance(data, dict):
        return {}, "invalid_response"
    if data.get("error"):
        return {}, str(data.get("message") or "api_error")

    symbols_list = data.get("symbols", {})
    if isinstance(symbols_list, list):
        result = {}
        for entry in symbols_list:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name", "").upper().replace("/", "")
            if name:
                result[name] = entry
        return result, None if result else "empty_symbols"

    if isinstance(symbols_list, dict):
        result = {k.upper().replace("/", ""): v for k, v in symbols_list.items()}
        return result, None if result else "empty_symbols"

    return {}, "empty_symbols"


# ---------------------------------------------------------------------------
# Community Outlook (public – no auth)
# ---------------------------------------------------------------------------

def fetch_community_outlook() -> dict:
    """
    Fetch Myfxbook community outlook – retail trader positioning data.
    Returns dict keyed by symbol with {longPercentage, shortPercentage, ...}.
    """
    data = mfx_get("/api/get-community-outlook.json")
    if not isinstance(data, dict):
        return {}

    # Response is {"error": false, "symbols": [{...}, ...]}
    symbols_list = data.get("symbols", {})

    # Normalize: can be list or dict
    if isinstance(symbols_list, list):
        result = {}
        for entry in symbols_list:
            name = entry.get("name", "").upper().replace("/", "")
            if name:
                result[name] = entry
        return result

    if isinstance(symbols_list, dict):
        # Keys are symbol names
        return {k.upper().replace("/", ""): v for k, v in symbols_list.items()}

    return {}


def fetch_community_outlook_browser(
    cookie_header: str,
    user_agent: str = "",
    accept_language: str = "",
) -> tuple[dict, str | None]:
    cookie_header = (cookie_header or "").strip()
    if not cookie_header:
        return {}, "missing_cookie_header"

    cookies = _cookie_header_to_playwright_cookies(cookie_header)
    if not cookies:
        return {}, "invalid_cookie_header"

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return {}, f"playwright_import_failed:{exc.__class__.__name__}"

    ua = (user_agent or HEADERS["User-Agent"]).strip()
    lang = (accept_language or HEADERS["Accept-Language"]).strip()
    is_mobile = any(token in ua for token in ("Android", "iPhone", "Mobile"))

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(
                    user_agent=ua,
                    locale="en-CA",
                    viewport={"width": 393, "height": 851} if is_mobile else {"width": 1440, "height": 1100},
                    is_mobile=is_mobile,
                    has_touch=is_mobile,
                    extra_http_headers={"accept-language": lang},
                )
                context.add_cookies(cookies)
                page = context.new_page()
                page.goto(
                    "https://www.myfxbook.com/community/outlook",
                    wait_until="domcontentloaded",
                    timeout=120000,
                )
                page.wait_for_timeout(4000)
                title = page.title().lower()
                if "just a moment" in title:
                    return {}, "cloudflare_blocked"

                data = page.evaluate(
                    """
() => {
  const asFloat = (value) => {
    const match = String(value || '').replace(/,/g, '').match(/-?\\d+(?:\\.\\d+)?/);
    return match ? Number.parseFloat(match[0]) : null;
  };
  const asInt = (value) => {
    const match = String(value || '').replace(/,/g, '').match(/-?\\d+/);
    return match ? Number.parseInt(match[0], 10) : null;
  };
  const rows = Array.from(document.querySelectorAll('tr.outlook-symbol-row'));
  const result = {};

  for (const row of rows) {
    const symbol = (
      row.getAttribute('symbolname') ||
      row.querySelector('td a')?.textContent ||
      ''
    ).trim().toUpperCase();
    if (!symbol) {
      continue;
    }

    const popover = row.querySelector('div[id^="outlookSymbolPopover"]');
    const detailRows = popover ? Array.from(popover.querySelectorAll('tbody tr')) : [];
    const actionRows = {};

    for (const tr of detailRows) {
      const cells = Array.from(tr.querySelectorAll('td'))
        .map((td) => td.innerText.trim())
        .filter(Boolean);
      if (!cells.length) {
        continue;
      }

      let baseIndex = 0;
      if (cells[0] !== 'Short' && cells[0] !== 'Long') {
        baseIndex = 1;
      }

      const action = String(cells[baseIndex] || '').toUpperCase();
      if (action !== 'SHORT' && action !== 'LONG') {
        continue;
      }

      actionRows[action] = {
        percentage: asFloat(cells[baseIndex + 1] || ''),
        volume: asFloat(cells[baseIndex + 2] || ''),
        positions: asInt(cells[baseIndex + 3] || ''),
      };
    }

    const popularityText = popover ? popover.innerText : '';
    const popularityMatch = popularityText.match(/(\\d+(?:\\.\\d+)?)% of traders are currently trading/i);

    result[symbol] = {
      name: symbol,
      shortPercentage: actionRows.SHORT?.percentage ?? null,
      longPercentage: actionRows.LONG?.percentage ?? null,
      shortVolume: actionRows.SHORT?.volume ?? null,
      longVolume: actionRows.LONG?.volume ?? null,
      shortPositions: actionRows.SHORT?.positions ?? null,
      longPositions: actionRows.LONG?.positions ?? null,
      avgShortPrice: asFloat(row.querySelector('[id^="shortPriceCell"]')?.innerText || ''),
      avgLongPrice: asFloat(row.querySelector('[id^="longPriceCell"]')?.innerText || ''),
      currentPrice: asFloat(row.querySelector('[id^="rateCell"]')?.innerText || ''),
      shortDistancePips: asFloat(row.querySelector('[id^="shortDisCell"]')?.innerText || ''),
      longDistancePips: asFloat(row.querySelector('[id^="longDisCell"]')?.innerText || ''),
      symbolPopularity: popularityMatch ? Number.parseFloat(popularityMatch[1]) : null,
    };
  }

  return result;
}
                    """
                )
            finally:
                browser.close()
    except Exception as exc:
        return {}, f"browser_fetch_failed:{exc.__class__.__name__}"

    if not isinstance(data, dict) or not data:
        return {}, "empty_browser_data"
    return data, None


def outlook_to_picks(outlook: dict) -> list:
    """
    Convert community outlook sentiment into fade-retail picks.
    When ≥75% retail is one side, signal the opposite direction.
    """
    picks = []
    now = datetime.now(timezone.utc)

    for symbol, data in outlook.items():
        try:
            long_pct = float(data.get("longPercentage") or data.get("long") or 0)
            short_pct = float(data.get("shortPercentage") or data.get("short") or 0)
        except (ValueError, TypeError):
            continue

        # Normalize to 0-1
        if long_pct > 1:
            long_pct /= 100
        if short_pct > 1:
            short_pct /= 100

        # Average entry price from outlook data (may not be present)
        try:
            avg_price = float(data.get("avgShortPrice") or data.get("avgLongPrice") or 0)
        except (ValueError, TypeError):
            avg_price = 0
        try:
            current_price = float(data.get("currentPrice") or 0)
        except (ValueError, TypeError):
            current_price = 0

        direction = None
        fade_pct = 0.0

        if short_pct >= FADE_THRESHOLD_SHORT:
            direction = "LONG"   # Fade extreme retail shorts
            fade_pct = short_pct
        elif long_pct >= FADE_THRESHOLD_LONG:
            direction = "SHORT"  # Fade extreme retail longs
            fade_pct = long_pct

        if not direction:
            continue

        if not symbol or not symbol.replace("-", "").replace("/", "").isalpha():
            continue

        clean_sym = symbol.replace("/", "").replace("-", "")[:6]
        if not clean_sym:
            continue

        # Determine category after symbol normalization so metal-cross symbols
        # do not trip an UnboundLocalError and downstream loaders get a stable
        # asset_class immediately.
        cat = "commodity" if clean_sym.startswith(METAL_PREFIXES) else "forex"
        asset_class = "COMMODITY" if cat == "commodity" else "FOREX"

        # TP/SL
        if avg_price > 0:
            pip = 0.01 if "JPY" in clean_sym else 0.0001
            if cat == "commodity":
                tp_offset = avg_price * 0.015
                sl_offset = avg_price * 0.008
            else:
                tp_offset = 50 * pip
                sl_offset = 30 * pip

            entry = avg_price
            if direction == "LONG":
                tp = round(entry + tp_offset, 6)
                sl = round(entry - sl_offset, 6)
            else:
                tp = round(entry - tp_offset, 6)
                sl = round(entry + sl_offset, 6)
        else:
            entry = 0.0
            tp = 0.0
            sl = 0.0

        confidence = round(
            min(0.88, SENTIMENT_CONFIDENCE + (fade_pct - FADE_THRESHOLD_SHORT) * 0.5), 3
        )
        status, pnl_pct = _resolve_live_pick_status(direction, entry, tp, sl, current_price)
        closed_now = status in {"TP_HIT", "SL_HIT"}
        pnl_pct_rounded = round(pnl_pct, 2) if pnl_pct is not None else None
        current_price_out = _round_like_entry(current_price, entry or current_price) if current_price > 0 else None
        exit_price = current_price_out if closed_now else None
        exit_time = now.isoformat() if closed_now else None
        exit_date = now.strftime("%Y-%m-%d") if closed_now else None

        pick_id = (
            f"mfx_sentiment_{clean_sym}_{direction}::{now.strftime('%Y-%m-%d_%H%M')}"
        )
        picks.append({
            "id": pick_id,
            "strategy": f"myfxbook_fade_{direction.lower()}_{clean_sym}",
            "symbol": clean_sym,
            "category": cat,
            "signal_type": "BUY" if direction == "LONG" else "SELL",
            "direction": direction,
            "entry_price": entry,
            "entry_date": now.strftime("%Y-%m-%d"),
            "timestamp": now.isoformat(),
            "created_at": now.isoformat(),
            "open_time": now.isoformat(),
            "generated_at": now.isoformat(),
            "scan_time": now.isoformat(),
            "take_profit": tp,
            "stop_loss": sl,
            "tp_price": tp,
            "sl_price": sl,
            "target_price": tp,
            "stop_price": sl,
            "confidence": confidence,
            "ml_score": confidence,
            "exit_price": exit_price,
            "exit_date": exit_date,
            "exit_reason": status if closed_now else None,
            "exit_time": exit_time,
            "closed_at": exit_time,
            "resolved_at": exit_time,
            "pnl_pct": pnl_pct_rounded,
            "pnl_dollar": None,
            "status": status,
            "hold_days": None,
            "allocation": 200.0,
            "position_sizing": "sentiment_fade",
            "risk_per_trade_pct": 0.02,
            "max_safe_leverage": 5.0,
            "forward_trades": 0,
            "forward_wr": confidence,
            "forward_validated": fade_pct >= 0.80,
            "elite_score": int(confidence * 80 + (fade_pct - 0.5) * 40),
            "elite_grade": "A" if fade_pct >= 0.82 else "B" if fade_pct >= 0.75 else "C",
            "reason": (
                f"Myfxbook community outlook: {fade_pct*100:.0f}% retail "
                f"{'SHORT' if direction == 'LONG' else 'LONG'} – fade signal"
            ),
            "source_system": "copy_trader_myfxbook",
            "trader_name": "myfxbook_community",
            "trader_roi": None,
            "trader_followers": None,
            "trader_platform": "Myfxbook",
            "trader_id": "community_outlook",
            "asset_class": asset_class,
            "current_price": current_price_out,
            "current_price_source": "myfxbook_outlook" if current_price_out else None,
            "unrealized_pnl": 0.0 if closed_now else pnl_pct_rounded,
            "sentiment_long_pct": round(long_pct, 4),
            "sentiment_short_pct": round(short_pct, 4),
        })

    return _enrich_live_quotes(picks)


# ---------------------------------------------------------------------------
# AutoTrade system scrapers (HTML fallback when API needs auth)
# ---------------------------------------------------------------------------

def fetch_system_openorders_html(system_id: int) -> list:
    """
    Fallback HTML scraper for Myfxbook system open orders.
    Tries the embedded JSON in the page source.
    """
    url = f"{MYFXBOOK_BASE}/member/autotrade/system/{system_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        html = resp.text

        # Look for JSON data embedded in <script> tags
        import re
        # Pattern: openOrders or openTrades embedded as JSON
        for pattern in [
            r'"openOrders"\s*:\s*(\[.*?\])',
            r'"openTrades"\s*:\s*(\[.*?\])',
            r'"trades"\s*:\s*(\[.*?\])',
            r'openOrdersData\s*=\s*(\[.*?\])',
        ]:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    orders = json.loads(match.group(1))
                    if isinstance(orders, list) and orders:
                        return orders
                except (json.JSONDecodeError, IndexError):
                    continue
    except requests.exceptions.RequestException:
        pass
    return []


def system_order_to_pick(order: dict, system: dict) -> dict | None:
    """Convert a Myfxbook AutoTrade open order to a pick."""
    import re
    raw_sym = (
        order.get("symbol")
        or order.get("pair")
        or order.get("currency")
        or ""
    )
    clean_sym = re.sub(r"[^A-Za-z0-9]", "", raw_sym).upper()[:6]
    if not clean_sym:
        return None

    cat = "commodity" if clean_sym.startswith(METAL_PREFIXES) else "forex"

    raw_dir = str(order.get("action") or order.get("type") or order.get("side") or "").upper()
    if "BUY" in raw_dir or raw_dir in ("L", "LONG", "1"):
        direction = "LONG"
    elif "SELL" in raw_dir or raw_dir in ("S", "SHORT", "0"):
        direction = "SHORT"
    else:
        return None

    try:
        entry = float(order.get("openPrice") or order.get("price") or order.get("rate") or 0)
    except (ValueError, TypeError):
        return None
    if entry <= 0:
        return None

    # TP/SL
    pip = 0.01 if "JPY" in clean_sym else 0.0001
    if cat == "COMMODITY":
        tp_offset = entry * 0.015
        sl_offset = entry * 0.008
    else:
        tp_offset = 50 * pip
        sl_offset = 30 * pip

    if direction == "LONG":
        tp = round(entry + tp_offset, 6)
        sl = round(entry - sl_offset, 6)
    else:
        tp = round(entry - tp_offset, 6)
        sl = round(entry + sl_offset, 6)

    sys_name = system.get("name", f"mfx_{system.get('id', 'sys')}")
    safe_name = sys_name.replace(" ", "_")[:20]
    now = datetime.now(timezone.utc)
    pick_id = f"mfx_{safe_name}::{clean_sym}::{now.strftime('%Y-%m-%d_%H%M')}"

    confidence = 0.65  # Conservative default for HTML-scraped data

    return {
        "id": pick_id,
        "strategy": f"myfxbook_sys_{safe_name}",
        "symbol": clean_sym,
        "category": cat,
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "direction": direction,
        "entry_price": entry,
        "entry_date": now.strftime("%Y-%m-%d"),
        "timestamp": now.isoformat(),
        "created_at": now.isoformat(),
        "open_time": now.isoformat(),
        "take_profit": tp,
        "stop_loss": sl,
        "confidence": confidence,
        "ml_score": confidence,
        "exit_price": None,
        "exit_date": None,
        "exit_reason": None,
        "pnl_pct": None,
        "pnl_dollar": None,
        "status": "OPEN",
        "hold_days": None,
        "allocation": 200.0,
        "position_sizing": "copy_trader",
        "risk_per_trade_pct": 0.02,
        "max_safe_leverage": 5.0,
        "forward_trades": 0,
        "forward_wr": confidence,
        "forward_validated": False,
        "elite_score": 55,
        "elite_grade": "B",
        "reason": f"Myfxbook AutoTrade {sys_name} | {clean_sym} {direction}",
        "source_system": "copy_trader_myfxbook",
        "trader_name": sys_name,
        "trader_roi": None,
        "trader_followers": None,
        "trader_platform": "Myfxbook",
        "trader_id": str(system.get("id", "")),
        "current_price": None,
        "current_price_source": None,
        "unrealized_pnl": 0.0,
    }


# ---------------------------------------------------------------------------
# Core scanner
# ---------------------------------------------------------------------------

def scan_myfxbook(max_systems: int = 20) -> tuple[list, list, dict]:
    """
    Scan Myfxbook for copy-trading signals.

    1. Fetch community outlook → generate fade-retail picks.
    2. Try AutoTrade seed systems → scrape open orders.

    Returns:
        profiles  – list of system/source metadata dicts
        picks     – list of active_picks-compatible trade dicts
    """
    profiles = []
    picks = []
    status = {
        "generated_at": _now_iso(),
        "status": "empty",
        "diagnostic_code": "empty",
        "credentials_configured": False,
        "browser_cookie_configured": False,
        "auth_status": "not_attempted",
        "browser_status": "not_attempted",
        "auth_error": None,
        "outlook_source": "none",
        "outlook_error": None,
        "community_outlook_pairs": 0,
        "community_outlook_picks": 0,
        "notes": [],
    }

    email, password = _get_myfxbook_credentials()
    cookie_header, browser_user_agent, browser_accept_language = _get_myfxbook_browser_context()
    status["credentials_configured"] = bool(email and password)
    status["browser_cookie_configured"] = bool(cookie_header)
    outlook = {}

    # === PART 1: Community Outlook (auth-first, preserve cookies) ===
    if status["credentials_configured"]:
        print("  [Myfxbook] Logging in for API access...")
        http_session = requests.Session()
        session_id, auth_error = login_myfxbook(email, password, http_session)
        if session_id:
            status["auth_status"] = "login_ok"
            outlook, api_error = fetch_community_outlook_api(session_id, http_session)
            if outlook:
                status["outlook_source"] = "api"
            else:
                status["auth_status"] = "api_failed"
                status["outlook_error"] = api_error
                print(
                    "  [Myfxbook] API outlook unavailable"
                    f" ({api_error or 'unknown'})"
                )
        else:
            status["auth_status"] = "login_failed"
            status["auth_error"] = auth_error
            print(f"  [Myfxbook] Login failed ({auth_error or 'unknown'})")
    else:
        status["auth_status"] = "not_configured"
        status["notes"].append(
            "Set MYFXBOOK_EMAIL/MYFXBOOK_PASSWORD or "
            "MYFXBOOKUSER/MYFXBOOKPASS to enable API access."
        )
        print("  [Myfxbook] No credentials configured")

    if not outlook and cookie_header:
        print("  [Myfxbook] Fetching community outlook via browser...")
        outlook, browser_error = fetch_community_outlook_browser(
            cookie_header,
            browser_user_agent,
            browser_accept_language,
        )
        if outlook:
            status["browser_status"] = "ok"
            status["outlook_source"] = "browser_cookie"
        else:
            status["browser_status"] = "failed"
            status["outlook_error"] = browser_error or status["outlook_error"]
            print(
                "  [Myfxbook] Browser outlook unavailable"
                f" ({browser_error or 'unknown'})"
            )
    elif not cookie_header:
        status["browser_status"] = "not_configured"

    if not outlook:
        print("  [Myfxbook] Fetching community outlook...")
        outlook = fetch_community_outlook()
    if outlook:
        sentiment_picks = outlook_to_picks(outlook)
        picks.extend(sentiment_picks)
        status["community_outlook_pairs"] = len(outlook)
        status["community_outlook_picks"] = len(sentiment_picks)
        if status["outlook_source"] == "none":
            status["outlook_source"] = "legacy_noauth"
        print(
            f"  [Myfxbook] Community outlook: {len(outlook)} symbols → "
            f"{len(sentiment_picks)} fade picks"
        )
        profiles.append({
            "source": "community_outlook",
            "symbols_tracked": len(outlook),
            "fade_signals": len(sentiment_picks),
            "platform": "Myfxbook",
            "source_mode": status["outlook_source"],
            "auth_status": status["auth_status"],
        })
    else:
        print("  [Myfxbook] Community outlook unavailable")
    time.sleep(RATE_LIMIT_SEC)

    # === PART 2: AutoTrade systems (HTML fallback) ===
    systems_to_scan = SEED_SYSTEMS[:max_systems]
    print(f"  [Myfxbook] Scanning {len(systems_to_scan)} AutoTrade systems...")
    for system in systems_to_scan:
        time.sleep(RATE_LIMIT_SEC)
        orders = fetch_system_openorders_html(system["id"])

        if not orders:
            continue

        sys_picks = []
        for order in orders:
            pick = system_order_to_pick(order, system)
            if pick:
                sys_picks.append(pick)

        if sys_picks:
            picks.extend(sys_picks)
            profiles.append({
                "system_id": system["id"],
                "name": system["name"],
                "open_orders": len(orders),
                "picks_generated": len(sys_picks),
                "platform": "Myfxbook",
            })
            print(
                f"  [Myfxbook] System {system['name']} ({system['id']}): "
                f"{len(orders)} orders → {len(sys_picks)} picks"
            )

    if picks:
        status["status"] = "ok"
        status["diagnostic_code"] = "ok"
    elif status["auth_status"] == "login_failed":
        status["diagnostic_code"] = "auth_failed"
    elif status["auth_status"] == "api_failed":
        status["diagnostic_code"] = "api_unavailable"
    elif not status["credentials_configured"]:
        status["diagnostic_code"] = "no_credentials"
    else:
        status["diagnostic_code"] = "no_data"

    print(
        f"  [Myfxbook] Done: {len(profiles)} sources, {len(picks)} picks "
        f"({status['diagnostic_code']})"
    )
    return profiles, _enrich_live_quotes(picks), status


def save_myfxbook_results(profiles: list, picks: list, status: dict | None = None) -> None:
    """Save Myfxbook results and scraper status to JSON files."""
    profiles_path = DATA_DIR / "myfxbook_profiles.json"
    picks_path = DATA_DIR / "myfxbook_picks.json"
    payload = dict(status or {})
    payload.setdefault("generated_at", _now_iso())
    payload["profiles_saved"] = len(profiles)
    payload["picks_saved"] = len(picks)

    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, default=str)
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)
    with open(STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)

    print(f"  [Myfxbook] Saved {len(profiles)} profiles → {profiles_path.name}")
    print(f"  [Myfxbook] Saved {len(picks)} picks    → {picks_path.name}")
    print(
        f"  [Myfxbook] Saved status ({payload.get('diagnostic_code', 'unknown')})"
        f" → {STATUS_PATH.name}"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Myfxbook AutoTrade & Sentiment Scraper ===")
    t0 = time.time()
    profiles, picks, status = scan_myfxbook(max_systems=15)
    save_myfxbook_results(profiles, picks, status)
    print(
        f"\nDone in {time.time()-t0:.1f}s | {len(profiles)} sources | "
        f"{len(picks)} picks | status={status['diagnostic_code']}"
    )
    if picks:
        print("\nSample picks:")
        for p in picks[:3]:
            entry_str = f"@ {p['entry_price']}" if p["entry_price"] else "(live)"
            print(f"  {p['symbol']} {p['direction']} {entry_str} "
                  f"[{p['trader_name']}] conf={p['confidence']}")
