import sys, json, time
from datetime import datetime, timezone

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError as e:
    print(f"Missing: {e}")
    sys.exit(1)
