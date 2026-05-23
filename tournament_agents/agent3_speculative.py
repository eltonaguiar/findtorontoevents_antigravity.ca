import json
import logging
from datetime import datetime
import os
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - AGENT3_SPECULATIVE - %(message)s')

class SpeculativeRiskAgent:
    def __init__(self):
        self.asset_classes = {
            'PennyStocks': ['CTRM', 'SNDL', 'MULN', 'BBIG', 'TYDE'],
            'MemeCoins': ['DOGE', 'SHIB', 'PEPE', 'WIF', 'BONK']
        }
        self.portfolios = []
        self.tracking_dir = os.path.join(os.path.dirname(__file__), 'data', 'speculative')
        os.makedirs(self.tracking_dir, exist_ok=True)
        self.portfolio_file = os.path.join(self.tracking_dir, 'speculative_portfolios.json')

    def load_or_generate_portfolios(self, num_portfolios=30):
        if os.path.exists(self.portfolio_file):
            with open(self.portfolio_file, 'r') as f:
                self.portfolios = json.load(f)
            
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
                        'tickers': random.choices(tickers, k=2),
                        'strategy_type': random.choice(['SocialSentimentPump', 'VolumeAnomaly', 'InfluencerWalletCopy']),
                        'risk_management': {
                            'position_size_pct': 1.0, # Highly volatile, very small position
                            'stop_loss_pct': 50.0, # Wide stops or auto-kill conditions
                            'take_profit_pct': 300.0
                        },
                        'performance': {
                            'unrealized_pnl_pct': 0.0,
                            'realized_pnl_pct': 0.0,
                            'drawdown': 0.0,
                            'win_rate': 0.0
                        },
                        'open_trades': [],
                        'last_updated': datetime.now().isoformat()
                    }
                    self.portfolios.append(portfolio)
            logging.info(f"Generated {len(self.portfolios)} template portfolios for Speculative assets.")

    def save_portfolios(self):
        with open(self.portfolio_file, 'w') as f:
            json.dump(self.portfolios, f, indent=4)
        logging.info(f"Portfolios saved to {self.portfolio_file}")

    def fetch_sentiment_data(self, ticker):
        """
        Simulate fetching social sentiment / volume metrics from APIs.
        """
        return {
            'ticker': ticker,
            'current_price': random.uniform(0.00001, 2.50) if ticker in self.asset_classes['MemeCoins'] else random.uniform(0.1, 5.0),
            'sentiment_score': random.uniform(-1.0, 1.0), # -1 is extremely bearish, 1 is extremely bullish
            'volume_spike_multiplier': random.uniform(0.5, 10.0), # Normal is ~1.0
            'timestamp': datetime.now().isoformat()
        }

    def execute_speculative_logic(self, portfolio, market_data):
        """
        These assets rely heavily on sentiment triggers or volume anomalies.
        """
        s_type = portfolio['strategy_type']
        
        if s_type == 'SocialSentimentPump' and market_data['sentiment_score'] > 0.8:
            return 'LONG'
        elif s_type == 'VolumeAnomaly' and market_data['volume_spike_multiplier'] > 5.0:
            return 'LONG'
        elif s_type == 'InfluencerWalletCopy' and random.random() > 0.95: # Very rare trigger
            return 'LONG'
            
        # Due to speculative nature, we rarely short meme coins and penny stocks here, focusing on moonshots
        return 'NEUTRAL'

    def run_speculative_cycle(self):
        logging.info("Scanning Twitter/On-chain anomalies for Speculations...")
        for portfolio in self.portfolios:
            for ticker in portfolio['tickers']:
                market_data = self.fetch_sentiment_data(ticker)
                signal = self.execute_speculative_logic(portfolio, market_data)
                
                if signal == 'LONG' and len(portfolio['open_trades']) < 2: # Keep concentrated
                    entry_price = market_data['current_price']
                    rm = portfolio['risk_management']
                    trade = {
                        'ticker': ticker,
                        'direction': signal,
                        'entry_price': entry_price,
                        'entry_time': datetime.now().isoformat(),
                        'stop_loss': entry_price * (1 - rm['stop_loss_pct']/100.0),
                        'take_profit': entry_price * (1 + rm['take_profit_pct']/100.0)
                    }
                    portfolio['open_trades'].append(trade)
                    logging.info(f"[{portfolio['portfolio_id']}] YOLO {signal} on {ticker} at {entry_price:.6f} (Target TP: {rm['take_profit_pct']}%)")

            # Risk updating logic
            if portfolio['open_trades']:
                # More extreme PnL swing simulation for specularives
                portfolio['performance']['unrealized_pnl_pct'] = round(random.uniform(-60.0, 150.0), 2)
                
                if random.random() > 0.85:
                    closed = portfolio['open_trades'].pop(0)
                    # Profit distributions are fat-tailed (mostly losses, rare massive gains)
                    profit = round(random.uniform(-50.0, 10.0) if random.random() > 0.2 else random.uniform(50.0, 300.0), 2)
                    portfolio['performance']['realized_pnl_pct'] += profit
                    
                    # Update win rate
                    current_wins = (portfolio['performance']['win_rate'] / 100.0) * 10
                    portfolio['performance']['win_rate'] = ((current_wins + (1 if profit > 0 else 0)) / 11.0) * 100
                    logging.info(f"[{portfolio['portfolio_id']}] Closed SPECULATIVE TRADE on {closed['ticker']}, PnL: {profit}%")

            portfolio['last_updated'] = datetime.now().isoformat()

    def run(self):
        logging.info("Starting Agent 3: Speculative Assymetric Risk Engine...")
        self.load_or_generate_portfolios()
        self.run_speculative_cycle()
        self.save_portfolios()

if __name__ == "__main__":
    agent = SpeculativeRiskAgent()
    agent.run()
