// dashboard_data.js - Symbol data mappings for the dynamic portfolio
// This file populates the global data objects declared in dashboard_live.html

ICONS = {
    'BTC-USD': '\u20bf', 'ETH-USD': '\u039e', 'BNB-USD': '\ud83d\udd36', 'SOL-USD': '\u25ce',
    'DOGE-USD': '\ud83d\udc15', 'AVAX-USD': '\ud83d\udd3a', 'LTC-USD': '\u0141', 'XRP-USD': '\ud83d\udca7',
    'ADA-USD': '\ud83d\udd35', 'APT-USD': '\ud83e\uddca', 'QQQ': '\ud83d\udcc8', 'SPY': '\ud83c\udfdb\ufe0f',
    'RIVN': '\ud83d\ude9b', 'GLD': '\ud83e\udd47', 'TLT': '\ud83d\udcca', 'IWM': '\ud83d\udcc9',
    'XOM': '\u26fd', 'CVX': '\ud83d\udee2\ufe0f', 'COIN': '\ud83e\ude99', 'META': '\ud83d\udc64',
    'TSLA': '\u26a1', 'XLV': '\ud83d\udc8a', 'XLE': '\u26a1', 'XLI': '\ud83c\udfed',
    'XLF': '\ud83c\udfe6', 'NFLX': '\ud83c\udfac', 'AMD': '\ud83d\udcbb', 'ARKK': '\ud83d\ude80',
    'MARA': '\u26cf\ufe0f', 'LCID': '\ud83d\udd0b', 'SOXX': '\ud83d\udd0c', 'SLV': '\ud83e\udd48'
};

NAMES = {
    'BTC-USD': 'Bitcoin', 'ETH-USD': 'Ethereum', 'BNB-USD': 'Binance Coin', 'SOL-USD': 'Solana',
    'DOGE-USD': 'Dogecoin', 'AVAX-USD': 'Avalanche', 'LTC-USD': 'Litecoin', 'XRP-USD': 'Ripple',
    'ADA-USD': 'Cardano', 'APT-USD': 'Aptos', 'QQQ': 'Nasdaq 100 ETF', 'SPY': 'S&P 500 ETF',
    'RIVN': 'Rivian', 'GLD': 'Gold ETF', 'TLT': 'Treasury Bond ETF', 'IWM': 'Russell 2000 ETF',
    'XOM': 'ExxonMobil', 'CVX': 'Chevron', 'COIN': 'Coinbase', 'META': 'Meta',
    'TSLA': 'Tesla', 'XLV': 'Health Care ETF', 'XLE': 'Energy ETF', 'XLI': 'Industrial ETF',
    'XLF': 'Financial ETF', 'NFLX': 'Netflix', 'AMD': 'AMD', 'ARKK': 'ARK Innovation',
    'MARA': 'Marathon Digital', 'LCID': 'Lucid Motors', 'SOXX': 'Semiconductor ETF', 'SLV': 'Silver ETF',
    'AUDUSD=X': 'AUD/USD', 'NZDUSD=X': 'NZD/USD'
};

CG_IDS = {
    'BTC-USD': 'bitcoin', 'ETH-USD': 'ethereum', 'BNB-USD': 'binancecoin', 'SOL-USD': 'solana',
    'DOGE-USD': 'dogecoin', 'AVAX-USD': 'avalanche-2', 'LTC-USD': 'litecoin', 'XRP-USD': 'ripple',
    'ADA-USD': 'cardano', 'APT-USD': 'aptos'
};

BINANCE_IDS = {
    'BTC-USD': 'BTCUSDT', 'ETH-USD': 'ETHUSDT', 'BNB-USD': 'BNBUSDT', 'SOL-USD': 'SOLUSDT',
    'DOGE-USD': 'DOGEUSDT', 'AVAX-USD': 'AVAXUSDT', 'LTC-USD': 'LTCUSDT', 'XRP-USD': 'XRPUSDT',
    'ADA-USD': 'ADAUSDT', 'APT-USD': 'APTUSDT'
};

// CryptoCompare symbol map (symbol minus -USD)
CC_SYMS = {
    'BTC-USD': 'BTC', 'ETH-USD': 'ETH', 'BNB-USD': 'BNB', 'SOL-USD': 'SOL',
    'DOGE-USD': 'DOGE', 'AVAX-USD': 'AVAX', 'LTC-USD': 'LTC', 'XRP-USD': 'XRP',
    'ADA-USD': 'ADA', 'APT-USD': 'APT'
};
