"""Configurable thresholds for strategy health evaluation.
All values loadable from environment variables with sensible defaults."""

import os

# --- Database ---
MYSQL_HOST = os.environ.get("MYSQL_HOST") or "mysql.50webs.com"
MYSQL_USER = os.environ.get("MYSQL_USER") or "ejaguiar1_stocks"
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD") or "stocks"
MYSQL_DB = os.environ.get("MYSQL_DB") or "ejaguiar1_stocks"

# --- Fee adjustment ---
FEE_RATE = float(os.environ.get("STRATEGY_FEE_RATE", "0.0015"))  # 0.15% per trade

# --- Ban thresholds ---
BAN_MIN_TRADES = int(os.environ.get("BAN_MIN_TRADES", "15"))
BAN_EXPECT_THRESHOLD = float(os.environ.get("BAN_EXPECT_THRESHOLD", "-0.02"))  # -2%
CATASTROPHIC_WR = float(os.environ.get("CATASTROPHIC_WR", "0.10"))  # 10%
CATASTROPHIC_MIN_TRADES = int(os.environ.get("CATASTROPHIC_MIN_TRADES", "10"))

# --- Incubator thresholds ---
INCUBATOR_MIN_TRADES = int(os.environ.get("INCUBATOR_MIN_TRADES", "10"))

# --- Core promotion thresholds ---
CORE_MIN_TRADES = int(os.environ.get("CORE_MIN_TRADES", "30"))
CORE_MIN_30D_WR = float(os.environ.get("CORE_MIN_30D_WR", "0.35"))
CORE_MIN_PF = float(os.environ.get("CORE_MIN_PF", "1.2"))
CORE_MIN_INCUBATOR_DAYS = int(os.environ.get("CORE_MIN_INCUBATOR_DAYS", "7"))

# --- Walk-forward validation ---
WF_SHARPE_DECAY_MAX = float(os.environ.get("WF_SHARPE_DECAY_MAX", "0.5"))
WF_CONSISTENCY_MIN = float(os.environ.get("WF_CONSISTENCY_MIN", "0.5"))
WF_RECHECK_DAYS = int(os.environ.get("WF_RECHECK_DAYS", "7"))

# --- Discord ---
DISCORD_HEALTH_WEBHOOK = os.environ.get("DISCORD_HEALTH_WEBHOOK", "")
