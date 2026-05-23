"""
SUPERPOWERS Quick — speed-optimized parameters for bootstrap training.
Target: all three systems trained in < 20 minutes on ubuntu-latest CPU.

Timing budget (GitHub Actions 2-core runner):
  Phase 0: Data download (12 pairs x 2 TF)          ~1.0 min
  Phase 1: System A training                         ~4.0 min
  Phase 2: System B training                         ~3.5 min
  Phase 3: System C training                         ~8.0 min
  Phase 4: Diagnostics                               ~0.5 min
  Total:                                             ~17.0 min
"""

# -- Data fetch ---------------------------------------------------------------
# Rotated Feb 26 2026: DOT → TAO (AI narrative momentum)
DATA_PAIRS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",    # Tier 1
    "ADAUSDT", "LINKUSDT", "TAOUSDT", "AVAXUSDT",   # Tier 2
    "DOGEUSDT", "FILUSDT", "ARBUSDT", "FETUSDT",    # Tier 3
]

OHLCV_LIMIT_1H = 720     # 30 days at 1h
OHLCV_LIMIT_15M = 720    # ~7.5 days at 15m

# -- System A (XGBoost Filter) ------------------------------------------------
A_PAIRS = DATA_PAIRS[:12]
A_STRIDE = 5              # step between historical slices (strategies fire rarely, need many windows)
A_MIN_SAMPLES = 30
A_N_ESTIMATORS = 150
A_TP_ATR_MULT = 2.5
A_SL_ATR_MULT = 2.0
A_MAX_HORIZON = 24

# -- System B (Regime Classifier) ---------------------------------------------
B_PAIRS = DATA_PAIRS[:12]
B_LOOKBACK_MIN = 80       # original=210; ADX(14)+EMA50+ATR(60) all OK at 80
B_LABEL_STRIDE = 5
B_N_ESTIMATORS = 150

# -- System C (GRU-Attention Neural Net) --------------------------------------
C_PAIRS = DATA_PAIRS[:10]
C_SEQ_LEN = 100           # original=200; 100 bars ~4 days of 1h context
C_HIDDEN_SIZE = 64         # original=128; parameter count drops ~4x
C_NUM_LAYERS = 1           # original=2
C_N_HEADS = 2              # original=4; matches embed_dim=128 (64*2)
C_DROPOUT = 0.2            # original=0.3
C_BATCH_SIZE = 64          # original=32; larger batch → faster epochs
C_NUM_EPOCHS = 30          # original=100; early stopping ~15-20
C_PATIENCE = 7             # original=10
C_NUM_FOLDS = 3            # original=5
C_PURGE_GAP = 24           # original=50; 24 bars = 1 day
C_MAX_HORIZON = 24         # original=48; 24 1h bars = 1 day
C_TP_ATR_MULT = 2.0        # original=2.5
C_SL_ATR_MULT = 1.5        # original=2.0
C_MIN_SAMPLES = 80
