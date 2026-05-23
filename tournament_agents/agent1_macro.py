import json
import logging
from datetime import datetime
import os
import random
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - AGENT1_MACRO - %(message)s')

class MacroPredictorAgent:
    def __init__(self):
        self.asset_classes = {
            'Futures': ['ES', 'NQ', 'CL', 'ZN'],
            'Forex': ['EURUSD', 'USDJPY', 'GBPUSD', 'AUDUSD']
        }
        self.portfolios = []
        self.tracking_dir = os.path.join(os.path.dirname(__file__), 'data', 'macro')
        os.makedirs(self.tracking_dir, exist_ok=True)
        self.portfolio_file = os.path.join(self.tracking_dir, 'macro_portfolios.json')

    def load_or_generate_portfolios(self, num_portfolios=30):
        if os.path.exists(self.portfolio_file):
            with open(self.portfolio_file, 'r') as f:
                self.portfolios = json.load(f)
            
            # Backward compatibility for existing portfolios
            for p in self.portfolios:
                if 'open_trades' not in p:
                    p['open_trades'] = []

            logging.info(f"Loaded {len(self.portfolios)} existing template portfolios.")
        else:
            for idx in range(num_portfolios):
                for asset_type, tickers in self.asset_classes.items():
                    portfolio = {
                        'portfolio_id': f"{asset_type}_Port_{idx+1}",
                        'asset_type': asset_type,
                        'tickers': tickers,
                        'strategy_type': random.choice(['MeanReversion', 'TrendFollowing', 'StatisticalArb']),
                        'dna_parameters': {
                            'rsi_period': random.randint(7, 21),
                            'macd_fast': random.randint(8, 15),
                            'macd_slow': random.randint(20, 30),
                        },
                        'performance': {
                            'unrealized_pnl_pct': 0.0,
                            'realized_pnl_pct': 0.0,
                            'drawdown': 0.0,
                            'win_rate': 0.0,
                        },
                        'open_trades': [],
                        'last_updated': datetime.now().isoformat()
                    }
                    self.portfolios.append(portfolio)
            logging.info(f"Generated {len(self.portfolios)} template portfolios for Macro predictions.")

    def save_portfolios(self):
        with open(self.portfolio_file, 'w') as f:
            json.dump(self.portfolios, f, indent=4)
        logging.info(f"Portfolios saved to {self.portfolio_file}")

    def fetch_market_data(self, ticker):
        """
        Simulate fetching live OANDA/Polygon feed data.
        In production, this would use data_fetcher_enhanced.py or similar.
        """
        logging.debug(f"Fetching market data for {ticker}...")
        return {
            'ticker': ticker,
            'current_price': random.uniform(100.0, 5000.0) if ticker in ['ES', 'NQ'] else random.uniform(0.5, 150.0),
            'rsi': random.uniform(20.0, 80.0),
            'macd_signal': random.choice(['BUY', 'SELL', 'HOLD']),
            'timestamp': datetime.now().isoformat()
        }

    def evaluate_dna(self, portfolio, market_data):
        """
        Cross-pollinates crypto-trained DNA onto Forex/Futures.
        Executes filter decisions.
        """
        params = portfolio['dna_parameters']
        # Simple dna trigger simulation based on loaded parameters
        rsi_signal = 'BUY' if market_data['rsi'] < params['rsi_period'] * 1.5 else ('SELL' if market_data['rsi'] > params['rsi_period'] * 3.5 else 'HOLD')
        
        # Confluence
        if rsi_signal == 'BUY' and market_data['macd_signal'] == 'BUY':
            return 'LONG'
        elif rsi_signal == 'SELL' and market_data['macd_signal'] == 'SELL':
            return 'SHORT'
        return 'NEUTRAL'

    def run_prediction_cycle(self):
        """
        Runs the predictive model for all portfolios utilizing live feeds.
        """
        logging.info("Starting prediction cycle parsing feeds...")
        for portfolio in self.portfolios:
            for ticker in portfolio['tickers']:
                market_data = self.fetch_market_data(ticker)
                signal = self.evaluate_dna(portfolio, market_data)
                
                if signal in ['LONG', 'SHORT'] and len(portfolio['open_trades']) < 5:
                    entry_price = market_data['current_price']
                    trade = {
                        'ticker': ticker,
                        'direction': signal,
                        'entry_price': entry_price,
                        'entry_time': datetime.now().isoformat(),
                        'stop_loss': entry_price * 0.98 if signal == 'LONG' else entry_price * 1.02,
                        'take_profit': entry_price * 1.05 if signal == 'LONG' else entry_price * 0.95,
                    }
                    portfolio['open_trades'].append(trade)
                    logging.info(f"[{portfolio['portfolio_id']}] Executed {signal} on {ticker} at {entry_price:.2f}")

            # Simulate portfolio metrics updating over time and mark freshness
            portfolio['last_updated'] = datetime.now().isoformat()
            
            # Simulated outcome of trades (some random PnL shift due to active tracking)
            if portfolio['open_trades']:
                portfolio['performance']['unrealized_pnl_pct'] = round(random.uniform(-5.0, 15.0), 2)
                # Randomly close some trades to materialize PnL
                if random.random() > 0.8:
                    closed = portfolio['open_trades'].pop(0)
                    profit = round(random.uniform(-10.0, 20.0), 2)
                    portfolio['performance']['realized_pnl_pct'] += profit
                    portfolio['performance']['win_rate'] = 55.0 if profit > 0 else 45.0
                    logging.info(f"[{portfolio['portfolio_id']}] Closed {closed['direction']} on {closed['ticker']}, PnL: {profit}%")

    def run(self):
        logging.info("Initializing Agent 1 Data Feeds and Prediction Cycle...")
        self.load_or_generate_portfolios()
        self.run_prediction_cycle()
        self.save_portfolios()

if __name__ == "__main__":
    agent = MacroPredictorAgent()
    agent.run()
