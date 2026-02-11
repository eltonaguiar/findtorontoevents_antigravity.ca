"""
Smart Money Intelligence — Configuration
All sensitive values come from environment variables (GitHub Secrets).
"""
import os

# API endpoints
API_BASE = os.environ.get('SM_API_BASE', 'https://findtorontoevents.ca/live-monitor/api')
ADMIN_KEY = os.environ.get('SM_ADMIN_KEY', 'livetrader2026')

# SEC EDGAR (free, unlimited, just needs proper User-Agent)
SEC_USER_AGENT = 'FindTorontoEvents contact@findtorontoevents.ca'

# Finnhub (free tier: 60 calls/min) — backup if PHP fetch fails
FINNHUB_API_KEY = os.environ.get('FINNHUB', '')

# Alpha Vantage (free tier: 25 calls/day)
ALPHA_VANTAGE_KEY = os.environ.get('ALPHA_VANTAGE_KEY', 'RWEA2JVI0NKYVXEF')

# CoinDesk API (crypto news/data)
COINDESK_API_KEY = os.environ.get('COIN_DESK', '')

# X/Twitter API (free tier: 1500 tweets/month read)
# Used for tracking crypto sentiment and sharp bettors
X_BEARER_TOKEN = os.environ.get('X_BEARER', '')

# Reddit API (free, needs app registration at reddit.com/prefs/apps)
# App type: "script", redirect URI: http://localhost:8080
# Registration: go to reddit.com/prefs/apps > "create another app" > choose "script"
# If Reddit routes through Devvit, go directly to reddit.com/prefs/apps
REDDIT_CLIENT_ID = os.environ.get('REDDIT_CLIENT_ID', '')
REDDIT_CLIENT_SECRET = os.environ.get('REDDIT_CLIENT_SECRET', '')
REDDIT_USER_AGENT = 'SmartMoneyBot/1.0 (by /u/findtorontoevents)'
REDDIT_REDIRECT_URI = 'http://localhost:8080'

# Top hedge funds to track (CIK numbers from SEC)
TOP_FUNDS = {
    '0001067983': 'Berkshire Hathaway',
    '0001336528': 'Bridgewater Associates',
    '0001649339': 'Citadel Advisors',
    '0001061768': 'Renaissance Technologies',
    '0001350694': 'Two Sigma Investments',
    '0001364742': 'DE Shaw',
    '0001037389': 'Soros Fund Management',
    '0001510524': 'Appaloosa Management',
    '0001336326': 'Baupost Group',
    '0001279708': 'Viking Global',
    '0001273087': 'Millennium Management',
    '0001543157': 'ARK Investment',
    '0001656456': 'Third Point',
    '0001618732': 'Tiger Global',
}

# Tickers we track (must match PHP side)
TRACKED_TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META',
                   'JPM', 'WMT', 'XOM', 'NFLX', 'JNJ', 'BAC']

# CUSIP to Ticker mapping for 13F parsing
# (13F filings use CUSIP, not ticker symbols)
CUSIP_TO_TICKER = {
    '037833100': 'AAPL', '594918104': 'MSFT', '02079K305': 'GOOGL',
    '023135106': 'AMZN', '67066G104': 'NVDA', '30303M102': 'META',
    '46625H100': 'JPM',  '931142103': 'WMT',  '30231G102': 'XOM',
    '64110L106': 'NFLX', '478160104': 'JNJ',  '060505104': 'BAC',
}

# WSB-specific tickers to also track (beyond our core 12)
WSB_EXTRA_TICKERS = ['GME', 'AMC', 'TSLA', 'AMD', 'PLTR', 'COIN',
                     'SOFI', 'RIVN', 'LCID', 'BB', 'HOOD', 'MARA']
