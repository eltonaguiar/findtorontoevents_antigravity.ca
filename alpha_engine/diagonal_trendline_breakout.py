"""
Diagonal Trendline Breakout Strategy (Short on Breakdown)

Detects diagonal uptrend support via 3 recent pivot lows with high R² linear fit.
Validates trend integrity then shorts on confirmed breakdown with volume confirmation.

Backtest suggestion: 0.10% slippage/comm, 1h crypto futures.
Position sizing: 1% risk per trade based on SL distance.
"""
import numpy as np
import pandas as pd
from scipy.stats import linregress
from typing import Dict

class DiagonalTrendlineBreakout:
    def __init__(
        self,
        strength: int = 5,
        min_sep: float = 0.02,
        r2_min: float = 0.95,
        tol_mult: float = 0.5,
        vol_mult: float = 1.5,
        atr_period: int = 14,
        atr_sl_mult: float = 1.0,
        spacing_min: int = 20,
        slope_consist: float = 0.25,
        sma_vol_period: int = 20,
        sma_close_period: int = 50,
        adx_period: int = 14,
        rsi_period: int = 14,
        min_bars: int = 200,
    ):
        self.strength = strength
        self.min_sep = min_sep
        self.r2_min = r2_min
        self.tol_mult = tol_mult
        self.vol_mult = vol_mult
        self.atr_period = atr_period
        self.atr_sl_mult = atr_sl_mult
        self.spacing_min = spacing_min
        self.slope_consist = slope_consist
        self.sma_vol_period = sma_vol_period
        self.sma_close_period = sma_close_period
        self.adx_period = adx_period
        self.rsi_period = rsi_period
        self.min_bars = min_bars

    def _atr(self, high: pd.Series, low: pd.Series, close: pd.Series, n: int) -> pd.Series:
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(n).mean()

    def _adx(self, high: pd.Series, low: pd.Series, close: pd.Series, n: int) -> pd.Series:
        up = high.diff()
        down = low.shift(1) - low
        plus_dm = np.where((up > down) & (up > 0), up, 0)
        minus_dm = np.where((down > up) & (down > 0), down, 0)
        tr = self._atr(high, low, close, n)
        plus_di = 100 * pd.Series(plus_dm, index=high.index).rolling(n).mean() / tr
        minus_di = 100 * pd.Series(minus_dm, index=high.index).rolling(n).mean() / tr
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        return dx.rolling(n).mean()

    def _rsi(self, close: pd.Series, n: int) -> pd.Series:
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(n).mean()
        avg_loss = loss.rolling(n).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _find_pivot_low_bars(self, lows: pd.Series) -> np.ndarray:
        n = len(lows)
        pivots = []
        for i in range(self.strength, n - self.strength):
            is_pivot = all(lows.iloc[i] < lows.iloc[i - k] for k in range(1, self.strength + 1)) and \
                       all(lows.iloc[i] < lows.iloc[i + k] for k in range(1, self.strength + 1))
            if is_pivot:
                neighbors = pd.concat([lows.iloc[i - self.strength:i], lows.iloc[i + 1:i + self.strength + 1]])
                min_neighbor = neighbors.min()
                if lows.iloc[i] <= min_neighbor * (1 - self.min_sep):
                    pivots.append(i)
        return np.array(pivots)

    def _find_pivot_high_bars(self, highs: pd.Series) -> np.ndarray:
        n = len(highs)
        pivots = []
        for i in range(self.strength, n - self.strength):
            is_pivot = all(highs.iloc[i] > highs.iloc[i - k] for k in range(1, self.strength + 1)) and \
                       all(highs.iloc[i] > highs.iloc[i + k] for k in range(1, self.strength + 1))
            if is_pivot:
                neighbors = pd.concat([highs.iloc[i - self.strength:i], highs.iloc[i + 1:i + self.strength + 1]])
                max_neighbor = neighbors.max()
                if highs.iloc[i] >= max_neighbor * (1 + self.min_sep):
                    pivots.append(i)
        return np.array(pivots)

    def _check_respect(self, df: pd.DataFrame, pivot_bars: np.ndarray, slope: float, intercept: float) -> bool:
        for k in range(len(pivot_bars) - 1):
            start, end = pivot_bars[k], pivot_bars[k + 1]
            for j in range(start + 1, end):
                line_j = intercept + slope * j
                tol_j = self.tol_mult * df['atr'].iloc[j]
                if df['high'].iloc[j] < line_j - tol_j:
                    return False
        return True

    def generate_signals(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        df = df[['open', 'high', 'low', 'close', 'volume']].copy().reset_index(drop=True)
        n = len(df)

        # Indicators
        df['atr'] = self._atr(df['high'], df['low'], df['close'], self.atr_period)
        df['vol_sma'] = df['volume'].rolling(self.sma_vol_period).mean()
        df['sma50'] = df['close'].rolling(self.sma_close_period).mean()
        df['adx'] = self._adx(df['high'], df['low'], df['close'], self.adx_period)
        df['rsi'] = self._rsi(df['close'], self.rsi_period)

        pivot_low_bars = self._find_pivot_low_bars(df['low'])
        pivot_high_bars = self._find_pivot_high_bars(df['high'])

        entry_short = pd.Series(False, index=df.index)
        exit_short = pd.Series(False, index=df.index)
        sl_price = pd.Series(np.nan, index=df.index)

        in_position = False

        for i in range(self.min_bars, n):
            if pd.isna(df['atr'].iloc[i]) or pd.isna(df['vol_sma'].iloc[i]) or pd.isna(df['sma50'].iloc[i]) \
               or pd.isna(df['adx'].iloc[i]) or pd.isna(df['rsi'].iloc[i]):
                continue

            recent_low_bars = pivot_low_bars[pivot_low_bars < i]
            if len(recent_low_bars) < 3:
                continue
            recent_low_bars = recent_low_bars[-3:]

            x = recent_low_bars
            y = df['low'].iloc[x].values
            res = linregress(x, y)
            if res.rvalue ** 2 < self.r2_min or res.slope <= 0:
                continue

            # Spacing
            if (x[1] - x[0] < self.spacing_min) or (x[2] - x[1] < self.spacing_min):
                continue

            # Slope consistency
            res1 = linregress(x[:2], y[:2])
            res2 = linregress(x[1:], y[1:])
            if res1.slope <= 0 or res2.slope <= 0:
                continue
            diff = abs(res1.slope - res2.slope) / max(res1.slope, res2.slope)
            if diff > self.slope_consist:
                continue

            # Respect check
            if not self._check_respect(df, x, res.slope, res.intercept):
                continue

            # Projection
            line_i = res.intercept + res.slope * i
            atr_i = df['atr'].iloc[i]
            breakdown = df['close'].iloc[i] < line_i - self.tol_mult * atr_i
            high_vol = df['volume'].iloc[i] > self.vol_mult * df['vol_sma'].iloc[i]

            if breakdown and high_vol and not in_position:
                entry_short.iloc[i] = True

                # SL
                recent_high_bars = pivot_high_bars[pivot_high_bars < i]
                recent_ph_price = np.nan
                if len(recent_high_bars) > 0:
                    recent_ph_bar = recent_high_bars[-1]
                    recent_ph_price = df['high'].iloc[recent_ph_bar]
                line_entry = line_i
                sl = max(recent_ph_price, line_entry + self.atr_sl_mult * atr_i) if not np.isnan(recent_ph_price) else line_entry + self.atr_sl_mult * atr_i
                sl_price.iloc[i] = sl
                in_position = True

            if in_position:
                exit_cond = (
                    df['close'].iloc[i] > df['sma50'].iloc[i]
                    or df['adx'].iloc[i] < 25
                    or df['rsi'].iloc[i] < 30
                )
                if exit_cond:
                    exit_short.iloc[i] = True
                    in_position = False

        return {
            'entry_short': entry_short,
            'exit_long': exit_short,
            'sl': sl_price,
        }

if __name__ == "__main__":
    # Synthetic data test
    np.random.seed(42)
    n = 500
    slope = 0.0013
    trend_low = 1.0 + slope * np.arange(n)
    noise = np.random.normal(0, 0.01, n)
    lows = trend_low + noise

    # Force 3 pivot lows
    pivot_bars = [100, 160, 230]
    pivot_lows = [1.0, 1.08, 1.17]
    for pb, pl in zip(pivot_bars, pivot_lows):
        lows[pb] = pl
        for k in range(1, 6):
            if pb - k >= 0:
                lows[pb - k] = pl + np.random.uniform(0.015, 0.035)
            if pb + k < n:
                lows[pb + k] = pl + np.random.uniform(0.015, 0.035)

    highs = lows + np.random.uniform(0.02, 0.05, n)
    closes = (highs + lows)/2 + np.random.normal(0, 0.01, n)
    opens = closes - np.random.normal(0, 0.005, n)
    volumes = np.random.uniform(1000, 4000, n)

    # Breakdown at 250
    proj_250 = 1.0 + slope * 250
    closes[250] = proj_250 - 0.03  # below
    volumes[250] = 8000  # high vol

    df_test = pd.DataFrame({
        'open': opens, 'high': highs, 'low': lows, 'close': closes, 'volume': volumes
    })

    strat = DiagonalTrendlineBreakout()
    signals = strat.generate_signals(df_test)

    print("Pivot lows found:", len(strat._find_pivot_low_bars(df_test['low'])))
    print("Entry shorts:", signals['entry_short'].sum())
    print("Exit longs:", signals['exit_long'].sum())
    print("SL at entries:")
    entry_bars = signals['entry_short'][signals['entry_short']].index.tolist()
    for eb in entry_bars:
        print(f"  Bar {eb}: close={df_test['close'].iloc[eb]:.4f}, sl={signals['sl'].iloc[eb]:.4f}")
    print("Test complete. Ready for backtesting.")