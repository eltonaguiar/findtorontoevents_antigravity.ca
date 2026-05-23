"""
Skyrocket Detector Configuration
=================================
Thresholds, symbols, and model hyperparameters for the skyrocket detector.
"""

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "SUIUSDT", "NEARUSDT",
    "UNIUSDT", "AAVEUSDT", "ARBUSDT", "INJUSDT", "ATOMUSDT", "FETUSDT",
    "HYPEUSDT", "TRXUSDT", "XLMUSDT", "TAOUSDT", "KASUSDT", "RENDERUSDT",
    "ONDOUSDT", "ICPUSDT", "ETCUSDT", "LTCUSDT", "TONUSDT", "SHIBUSDT",
    # Wave 2 additions (2026-03-19)
    "ETHFIUSDT", "QNTUSDT", "DEXEUSDT", "ENJUSDT", "THEUSDT",
    "PIXELUSDT", "ANKRUSDT", "HOTUSDT", "SAHARAUSDT",
]

SKYROCKET_THRESHOLD = 0.10  # 10% MFE in 24h
LOOKBACK_BARS = 24          # 24 hours of 1h bars for features
FORWARD_WINDOW = 24         # Look 24h ahead for label
MIN_CONFIDENCE = 0.65       # Minimum model probability to emit signal
TP_PCT = 0.08               # 8% take profit
SL_PCT = 0.03               # 3% stop loss
