import pandas as pd, numpy as np
from baby_strategies.hoffman_new_strategy import hoffman_new_strategy_signals
# generate dummy data
np.random.seed(0)
price = np.cumsum(np.random.randn(200)) + 100
cols = {
    "open": price,
    "high": price + np.random.rand(200) * 0.5,
    "low": price - np.random.rand(200) * 0.5,
    "close": price + np.random.randn(200) * 0.1,
    "volume": np.random.rand(200) * 10,
}
df = pd.DataFrame(cols)
signals = hoffman_new_strategy_signals(df, "BTCUSDT")
print(signals)
