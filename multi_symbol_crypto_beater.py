import ccxt
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score
import ta
from hmmlearn.hmm import GaussianHMM
import warnings
warnings.filterwarnings('ignore')

SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'SOLUSDT', 'BNB/USDT', 'XRP/USDT', 'DOGE/USDT', 'ADA/USDT', 'AVAX/USDT', 'TRX/USDT', 'DOT/USDT',
    'LINK/USDT', 'POL/USDT', 'LTC/USDT', 'BCH/USDT', 'TON/USDT', 'SHIB/USDT', 'INJ/USDT', 'SUI/USDT', 'ARB/USDT', 'OP/USDT',
    'SEI/USDT', 'DYDX/USDT', 'APE/USDT', 'ALGO/USDT', 'HBAR/USDT', 'WLD/USDT', 'STRK/USDT', 'ZRO/USDT', 'ZK/USDT', 'RIVER/USDT',
    'GLM/USDT', 'ULTIMA/USDT', 'AAVE/USDT', 'CHZ/USDT', 'VVV/USDT', 'ETC/USDT', 'ZBCN/USDT', 'W/USDT', 'JTO/USDT', 'FET/USDT', 'TIA/USDT'
]

class MultiSymbolCryptoBeater:
    def __init__(self, timeframe='1h', limit=5000):
        self.timeframe = timeframe
        self.limit = limit
        self.exchange = ccxt.binance()
        self.scaler = StandardScaler()
        self.symbol_encoder = LabelEncoder()
        self.ensemble = GradientBoostingClassifier(n_estimators=500, learning_rate=0.01, max_depth=8)
        self.regime_model = GaussianHMM(n_components=4, covariance_type='diag', n_iter=100)
        self.feature_columns = []
        
    def fetch_all_data(self):
        all_data = []
        for symbol in SYMBOLS:
            try:
                ohlcv = self.exchange.fetch_ohlcv(symbol, self.timeframe, limit=self.limit)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                df['symbol'] = symbol
                all_data.append(df)
            except Exception as e:
                print(f'Failed to fetch {symbol}: {e}')
        combined = pd.concat(all_data)
        combined = combined.sort_index()
        return combined
    
    def add_features(self, df):
        df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
        df['macd'] = ta.trend.MACD(df['close']).macd()
        df['adx'] = ta.trend.ADXIndicator(df['high'], df['low'], df['close']).adx()
        df['bb_width'] = ta.volatility.BollingerBands(df['close']).bollinger_wband()
        df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        df['return_1h'] = df['close'].pct_change()
        df['volatility'] = df['return_1h'].rolling(20).std()
        
        df.dropna(inplace=True)
        self.feature_columns = ['rsi', 'macd', 'adx', 'bb_width', 'atr', 'volume_ratio', 'volatility']
        return df
    
    def prepare_data(self, df):
        # Fixed: Return unscaled X to prevent data leakage (Lopez de Prado)
        # Scaling now happens per-fold in train()
        df['symbol_encoded'] = self.symbol_encoder.fit_transform(df['symbol'])
        X = df[self.feature_columns + ['symbol_encoded']].values
        y = (df['return_1h'].shift(-1) > 0).astype(int).dropna().values
        X = X[:-1]
        return X, y

    def train(self):
        df = self.fetch_all_data()
        df = self.add_features(df)
        X, y = self.prepare_data(df)

        # Fixed: Scaler fit on train fold only to prevent data leakage (Lopez de Prado)
        tscv = TimeSeriesSplit(n_splits=5)
        scores = []
        for train_idx, val_idx in tscv.split(X):
            fold_scaler = StandardScaler()
            X_train = fold_scaler.fit_transform(X[train_idx])
            X_val = fold_scaler.transform(X[val_idx])
            y_train, y_val = y[train_idx], y[val_idx]
            self.ensemble.fit(X_train, y_train)
            y_pred = self.ensemble.predict(X_val)
            acc = accuracy_score(y_val, y_pred)
            scores.append(acc)
            print(f'Validation Accuracy: {acc:.4f}')

        # Fit final scaler on all data for production use
        self.scaler.fit(X)

        print(f'Average Validation Accuracy: {np.mean(scores):.4f}')
    
    def portfolio_backtest(self, initial_capital=10000):
        df = self.fetch_all_data()
        df = self.add_features(df)
        df['symbol_encoded'] = self.symbol_encoder.transform(df['symbol'])
        X = df[self.feature_columns + ['symbol_encoded']].values
        X_scaled = self.scaler.transform(X)
        df['proba_long'] = self.ensemble.predict_proba(X_scaled)[:, 1]
        
        # Portfolio backtest
        portfolio_returns = []
        for symbol in SYMBOLS:
            symbol_df = df[df['symbol'] == symbol].copy()
            if len(symbol_df) < 100:
                continue
            symbol_df['signal'] = (symbol_df['proba_long'] > 0.6).astype(int) - (symbol_df['proba_long'] < 0.4).astype(int)
            symbol_df['strategy_return'] = symbol_df['signal'].shift(1) * symbol_df['return_1h']
            portfolio_returns.append(symbol_df['strategy_return'].dropna())
        
        portfolio_return = pd.concat(portfolio_returns).mean()
        cumulative = (1 + portfolio_return).cumprod()
        sharpe = portfolio_return.mean() / portfolio_return.std() * np.sqrt(365*24)
        max_dd = (cumulative / cumulative.cummax() - 1).min()
        win_rate = (portfolio_return > 0).mean()
        
        print(f'Portfolio Sharpe: {sharpe:.2f}')
        print(f'Max DD: {max_dd:.2%}')
        print(f'Win Rate: {win_rate:.2%}')
        print(f'Total Return: {(cumulative.iloc[-1] - 1):.2%}')
        
        return sharpe, max_dd, win_rate

# Usage
if __name__ == '__main__':
    beater = MultiSymbolCryptoBeater()
    beater.train()
    beater.portfolio_backtest()
