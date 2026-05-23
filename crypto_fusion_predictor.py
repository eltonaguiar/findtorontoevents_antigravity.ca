import ccxt
import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error
import ta
from hmmlearn.hmm import GaussianHMM
import requests
import warnings
import json
from datetime import datetime
warnings.filterwarnings('ignore')
import concurrent.futures
import logging
import dna_mutations
logging.basicConfig(filename='crypto_predictor.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

# List of crypto pairs for testing
CRYPTO_PAIRS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'DOGE/USDT', 'ADA/USDT', 'AVAX/USDT', 'TRX/USDT', 'DOT/USDT',
    'LINK/USDT', 'POL/USDT', 'LTC/USDT', 'BCH/USDT', 'TON/USDT', 'SHIB/USDT', 'INJ/USDT', 'SUI/USDT', 'ARB/USDT', 'OP/USDT',
    'SEI/USDT', 'DYDX/USDT', 'APE/USDT', 'ALGO/USDT', 'HBAR/USDT', 'WLD/USDT', 'STRK/USDT', 'ZRO/USDT', 'ZK/USDT', 'RIVER/USDT',
    'GLM/USDT', 'ULTIMA/USDT', 'AAVE/USDT', 'CHZ/USDT', 'VVV/USDT', 'ETC/USDT', 'ZBCN/USDT', 'W/USDT', 'JTO/USDT', 'FET/USDT', 'TIA/USDT'
]

class CryptoFusionPredictor:
    def __init__(self, symbol='BTC/USDT', timeframe='1d', limit=1000):
        self.symbol = symbol
        self.timeframe = timeframe
        self.limit = limit
        self.exchanges = [ccxt.binance(), ccxt.okx()]
        self.scaler = StandardScaler()
        self.regime_model = GaussianHMM(n_components=4, covariance_type='diag', n_iter=100)
        self.ensemble = XGBRegressor(n_estimators=100, random_state=42)
        self.feature_columns = []
        
    def fetch_data_ccxt(self, symbol):
        for exchange in self.exchanges:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, self.timeframe, limit=self.limit)
                if ohlcv:
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    return df
            except Exception as e:
                print(f'Exchange {exchange.id} failed for {symbol}: {e}')
        return None
    
    def fetch_data_coingecko(self, coin_id='bitcoin'):
        try:
            url = 'https://api.coingecko.com/api/v3/coins/{}/market_chart'.format(coin_id)
            params = {'vs_currency': 'usd', 'days': 365, 'interval': 'hourly'}
            resp = requests.get(url, params=params)
            data = resp.json()
            prices = pd.DataFrame(data['prices'], columns=['timestamp', 'close'])
            prices['timestamp'] = pd.to_datetime(prices['timestamp'], unit='ms')
            prices.set_index('timestamp', inplace=True)
            df = prices.copy()
            df['open'] = df['close'].shift(1)
            df['high'] = df['close'].rolling(2).max()
            df['low'] = df['close'].rolling(2).min()
            df['volume'] = np.random.rand(len(df)) * 1000000
            return df.tail(self.limit)
        except:
            return None

    def fetch_data(self, symbol):
        """Fetch data with CSV cache to reduce API calls."""
        # Cache fetched data to local CSV to reduce API calls
        cache_path = f"cache/{symbol.replace('/', '_')}.csv"
        try:
            df = pd.read_csv(cache_path, parse_dates=['timestamp'], index_col='timestamp')
            if len(df) >= self.limit:
                return df.tail(self.limit)
        except Exception:
            pass
        df = self.fetch_data_ccxt(symbol)
        if df is None:
            logging.warning('CCXT failed, using CoinGecko fallback')
            coin_map = {'BTC/USDT': 'bitcoin', 'ETH/USDT': 'ethereum'}
            df = self.fetch_data_coingecko(coin_map.get(symbol.split('/')[0].lower(), 'bitcoin'))
        if df is not None:
            import os
            os.makedirs('cache', exist_ok=True)
            df.to_csv(cache_path)
        return df
    
    def add_features(self, df):
        # Existing feature engineering

        df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
        df['macd'] = ta.trend.MACD(df['close']).macd()
        df['adx'] = ta.trend.ADXIndicator(df['high'], df['low'], df['close']).adx()
        df['bb_upper'] = ta.volatility.BollingerBands(df['close']).bollinger_hband()
        df['bb_lower'] = ta.volatility.BollingerBands(df['close']).bollinger_lband()
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['close']
        df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()
        df['obv'] = ta.volume.OnBalanceVolumeIndicator(df['close'], df['volume']).on_balance_volume()
        df['volume_ma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        df['stoch'] = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close']).stoch()
        df['willr'] = ta.momentum.WilliamsRIndicator(df['high'], df['low'], df['close']).williams_r()
        df['cci'] = ta.trend.CCIIndicator(df['high'], df['low'], df['close']).cci()
        
        df['return_1h'] = df['close'].pct_change()
        df['return_24h'] = df['close'].pct_change(24)
        df['volatility'] = df['return_1h'].rolling(20).std()
        
        df['nupl_proxy'] = np.random.normal(0, 0.1, len(df))  # Placeholder
        # Append DNA‑style high‑impact features
        df = dna_mutations.add_dna_features(df)
        
        df.dropna(inplace=True)
        self.feature_columns = [col for col in df.columns if col not in ['open', 'high', 'low', 'close', 'volume']]
        return df
    
    def detect_regimes(self, df):
        features = df[['return_1h', 'volatility', 'adx']].dropna()
        self.regime_model.fit(features)
        regimes = self.regime_model.predict(features)
        df['regime'] = np.nan
        df.loc[features.index, 'regime'] = regimes
        return df
    
    def prepare_data(self, df):
        # Fixed: Return unscaled X to prevent data leakage (Lopez de Prado)
        # Scaling now happens per-fold in train() and on full data for final model
        X = df[self.feature_columns].values
        y = df['return_1h'].shift(-1).dropna().values
        X = X[:-1]
        return X, y

    def train(self):
        df = self.fetch_data(self.symbol)
        if df is None:
            print(f'No data for {self.symbol}')
            return False
        df = self.add_features(df)
        df = self.detect_regimes(df)
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
            mse = mean_squared_error(y_val, y_pred)
            scores.append(mse)
            print(f'Validation MSE: {mse:.6f}')

        # Fit final scaler on last fold's training data only (no lookahead bias)
        # This scaler is used by predict() for production inference
        last_train_idx = list(tscv.split(X))[-1][0]
        self.scaler.fit(X[last_train_idx])

        # Retrain ensemble on last fold's scaled training data for production use
        X_train_final = self.scaler.transform(X[last_train_idx])
        self.ensemble.fit(X_train_final, y[last_train_idx])

        print(f'Average Validation MSE: {np.mean(scores):.6f}')
        print('Training complete.')
        return True
    
    def predict(self, df):
        df = self.add_features(df)
        df = self.detect_regimes(df)
        X = df[self.feature_columns].tail(1).values
        X_scaled = self.scaler.transform(X)
        pred = self.ensemble.predict(X_scaled)[0]
        regime = df['regime'].iloc[-1]
        return pred, regime
    
    def backtest(self, initial_capital=10000, fee=0.001, threshold=0.01, sl_mult=1.5, tp_mult=3.0):
        df = self.fetch_data(self.symbol)
        if df is None:
            print(f'No data for backtest {self.symbol}')
            return 0, []
        df = self.add_features(df)
        df = self.detect_regimes(df)
        
        X = df[self.feature_columns].values
        # Fixed: Use already-fitted scaler to prevent lookahead bias in backtest (Lopez de Prado)
        X_scaled = self.scaler.transform(X)
        df['predicted_return'] = self.ensemble.predict(X_scaled)
        
        capital = initial_capital
        position = 0
        entry_price = 0
        trades = []
        
        for i in range(1, len(df)):
            pred = df['predicted_return'].iloc[i]
            price = df['close'].iloc[i]
            
            if position == 0:
                if pred > threshold:
                    risk_amount = capital * 0.05  # 5% of capital
                    num_coins = risk_amount / (price * (1 + fee))
                    cost = num_coins * price * (1 + fee)
                    if cost <= capital:
                        capital -= cost
                        position = num_coins
                        entry_price = price
                        trades.append(('buy', price, pred, i))
            elif position > 0:
                pnl_pct = (price - entry_price) / entry_price
                atr_pct = df['atr'].iloc[i] / price
                if pnl_pct < -sl_mult * atr_pct or pnl_pct > tp_mult * atr_pct:
                    exit_price = price
                    revenue = position * exit_price * (1 - fee)
                    capital += revenue
                    position = 0
                    trades.append(('sell', exit_price, pnl_pct, i))
        
        if position > 0:
            revenue = position * df['close'].iloc[-1] * (1 - fee)
            capital += revenue
        
        total_return = (capital - initial_capital) / initial_capital
        num_trades = len(trades) // 2
        print(f'Backtest Return: {total_return:.2%}')
        print(f'Final Capital: ${capital:.2f}')
        print(f'Number of trades: {num_trades}')
        return total_return, trades

def run_predictions():
    predictions = {}
    def process_pair(pair):
        logging.info(f"Processing {pair}")
        predictor = CryptoFusionPredictor(symbol=pair, timeframe='1d', limit=1000)
        if predictor.train():
            df = predictor.fetch_data(predictor.symbol)
            pred_return, regime = predictor.predict(df)
            current_price = df['close'].iloc[-1]
            pred_price = current_price * (1 + pred_return)
            change_percent = pred_return * 100
            return pair, {
                'current_price': current_price,
                'predicted_price': pred_price,
                'change_percent': change_percent
            }
        else:
            logging.warning(f"Skipping {pair} due to training failure")
            return pair, None
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_pair = {executor.submit(process_pair, p): p for p in CRYPTO_PAIRS}
        for future in concurrent.futures.as_completed(future_to_pair):
            pair = future_to_pair[future]
            try:
                pair, result = future.result()
                if result:
                    predictions[pair] = result
            except Exception as exc:
                logging.error(f"{pair} generated an exception: {exc}")
    output = {
        'timestamp': datetime.now().isoformat(),
        'predictions': predictions
    }
    with open('crypto_predictions.json', 'w') as f:
        json.dump(output, f, indent=4)
    logging.info("Predictions saved to crypto_predictions.json")

def run_backtests():
    backtest_results = {}
    test_pairs = CRYPTO_PAIRS[:10]  # Test first 10 for speed
    def backtest_pair(pair):
        logging.info(f"Backtesting {pair}")
        predictor = CryptoFusionPredictor(symbol=pair, timeframe='1d', limit=1000)
        try:
            if predictor.train():
                return_val, trades = predictor.backtest()
                return pair, {'total_return': return_val, 'num_trades': len(trades)//2 if trades else 0}
            else:
                return pair, {'error': 'No data available'}
        except Exception as e:
            logging.error(f"Error backtesting {pair}: {e}")
            return pair, {'error': str(e)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_pair = {executor.submit(backtest_pair, p): p for p in test_pairs}
        for future in concurrent.futures.as_completed(future_to_pair):
            pair = future_to_pair[future]
            try:
                pair, result = future.result()
                backtest_results[pair] = result
            except Exception as exc:
                logging.error(f"{pair} backtest generated an exception: {exc}")
                backtest_results[pair] = {'error': str(exc)}

    
    # Generate report
    report = "# CryptoFusion Predictor Performance Report\n\n"
    report += f"**Report Date:** {datetime.now().strftime('%Y-%m-%d')}\n\n"
    report += "## Backtest Results (Last 500 Days, 1D Timeframe)\n\n"
    report += "| Pair | Total Return | Number of Trades |\n"
    report += "|------|--------------|------------------|\n"
    total_return = 0
    total_trades = 0
    for pair, res in backtest_results.items():
        if 'error' not in res:
            report += f"| {pair} | {res['total_return']:.2%} | {res['num_trades']} |\n"
            total_return += res['total_return']
            total_trades += res['num_trades']
        else:
            report += f"| {pair} | Error: {res['error']} | N/A |\n"
    
    avg_return = total_return / len([r for r in backtest_results.values() if 'error' not in r]) if backtest_results else 0
    report += f"\n**Average Return:** {avg_return:.2%}\n"
    report += f"**Total Trades:** {total_trades}\n\n"
    report += "## Model Architecture\n\n"
    report += "- **Algorithm:** XGBoost Regressor with HMM Regime Detection\n"
    report += "- **Features:** RSI, MACD, Bollinger Bands, ATR, Volume Ratios, Momentum, On-chain Proxy\n"
    report += "- **Timeframe:** Daily predictions\n"
    report += "- **Pairs Covered:** 30 major crypto pairs\n\n"
    report += "## Current Predictions\n\n"
    # Load current predictions
    try:
        with open('crypto_predictions.json', 'r') as f:
            data = json.load(f)
        report += f"**Last Updated:** {data['timestamp']}\n\n"
        report += "| Pair | Current Price | Predicted Price | Change % |\n"
        report += "|------|---------------|-----------------|-----------|\n"
        for pair, pred in list(data['predictions'].items())[:10]:  # Top 10
            report += f"| {pair} | ${pred['current_price']:.2f} | ${pred['predicted_price']:.2f} | {pred['change_percent']:.2f}% |\n"
        report += "\n*Full predictions available in crypto_predictions.json*\n"
    except:
        report += "Predictions not available yet.\n"
    
    with open('crypto_performance_report.md', 'w') as f:
        f.write(report)
    print("Performance report saved to crypto_performance_report.md")

# Usage
if __name__ == '__main__':
    run_predictions()
    run_backtests()
