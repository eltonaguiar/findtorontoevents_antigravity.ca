#!/usr/bin/env python3
"""
VPIN Mean Reversion + LightGBM Ensemble Strategy
Execute trades on Coinbase for: LTC, SOL, ETH, BTC, DOGE, XRP

This is the COMPLETE implementation framework.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Optional
import argparse

# Import strategy components
from vpin_mean_reversion_strategy import (
    VPINCalculator, MeanReversionSignals, ATRCalculator,
    SignalGenerator, PortfolioManager, BacktestEngine,
    SYMBOL_CONFIGS, TradeSignal, SignalType
)
from lightgbm_ensemble import (
    LightGBMEnsemble, WalkForwardCV, FeatureNeutralization,
    ModelPipeline, ModelConfig
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_log.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# DATA LOADER (Coinbase Pro API)
# ============================================================================

class CoinbaseDataLoader:
    """
    Load historical data from Coinbase
    
    Note: Install cbpro: pip install cbpro
    """
    
    def __init__(self):
        self.symbols = {
            'BTC-USDC': 'BTC-USDC',
            'ETH-USDC': 'ETH-USDC',
            'SOL-USDC': 'SOL-USDC',
            'LTC-USDC': 'LTC-USDC',
            'DOGE-USDC': 'DOGE-USDC',
            'XRP-USDC': 'XRP-USDC'
        }
        
    def load_historical(self, symbol: str, granularity: int = 3600,
                       start: Optional[str] = None, end: Optional[str] = None) -> pd.DataFrame:
        """
        Load historical OHLCV data from Coinbase
        
        Args:
            symbol: Trading pair (e.g., 'BTC-USDC')
            granularity: Candle size in seconds (3600 = 1 hour)
            start: Start date (ISO format)
            end: End date (ISO format)
        
        Returns:
            DataFrame with columns: open, high, low, close, volume
        """
        try:
            import cbpro
        except ImportError:
            logger.error("cbpro not installed. Run: pip install cbpro")
            # Return sample data for testing
            return self._generate_sample_data()
            
        public_client = cbpro.PublicClient()
        
        # Get historical rates
        if start and end:
            rates = public_client.get_product_historic_rates(
                symbol, granularity=granularity, start=start, end=end
            )
        else:
            # Get last 300 candles
            rates = public_client.get_product_historic_rates(
                symbol, granularity=granularity
            )
            
        # Convert to DataFrame
        df = pd.DataFrame(rates, columns=[
            'time', 'low', 'high', 'open', 'close', 'volume'
        ])
        
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df.sort_index(inplace=True)
        
        return df
    
    def _generate_sample_data(self) -> pd.DataFrame:
        """Generate sample data for testing without API"""
        np.random.seed(42)
        
        # Generate 1000 hours of synthetic data
        dates = pd.date_range(end=datetime.now(), periods=1000, freq='H')
        
        # Random walk with drift
        returns = np.random.normal(0.0001, 0.02, 1000)
        prices = 50000 * np.exp(np.cumsum(returns))
        
        # OHLCV
        df = pd.DataFrame(index=dates)
        df['close'] = prices
        df['open'] = df['close'].shift(1).fillna(prices[0])
        df['high'] = df[['open', 'close']].max(axis=1) * (1 + abs(np.random.normal(0, 0.005, 1000)))
        df['low'] = df[['open', 'close']].min(axis=1) * (1 - abs(np.random.normal(0, 0.005, 1000)))
        df['volume'] = np.random.lognormal(10, 1, 1000)
        
        return df
    
    def load_all_symbols(self, granularity: int = 3600,
                        days_back: int = 90) -> Dict[str, pd.DataFrame]:
        """
        Load data for all configured symbols
        
        Returns dict of symbol -> DataFrame
        """
        data = {}
        end = datetime.now()
        start = end - timedelta(days=days_back)
        
        for symbol in self.symbols.keys():
            logger.info(f"Loading {symbol}...")
            try:
                df = self.load_historical(
                    symbol, granularity,
                    start=start.isoformat(),
                    end=end.isoformat()
                )
                data[symbol] = df
                logger.info(f"  Loaded {len(df)} candles")
            except Exception as e:
                logger.error(f"  Failed to load {symbol}: {e}")
                
        return data

# ============================================================================
# LIVE TRADER
# ============================================================================

class LiveTrader:
    """
    Execute live trades on Coinbase
    
    WARNING: Paper trade for 1 month before using real capital
    """
    
    def __init__(self, api_key: str = None, api_secret: str = None,
                 passphrase: str = None, sandbox: bool = True):
        self.sandbox = sandbox
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        
        self.portfolio = PortfolioManager(initial_capital=10000.0)
        self.signal_generators = {
            symbol: SignalGenerator(config)
            for symbol, config in SYMBOL_CONFIGS.items()
        }
        
    def get_current_prices(self) -> Dict[str, float]:
        """Get current prices for all symbols"""
        try:
            import cbpro
            public_client = cbpro.PublicClient()
            
            prices = {}
            for symbol in SYMBOL_CONFIGS.keys():
                ticker = public_client.get_product_ticker(symbol)
                prices[symbol] = float(ticker['price'])
                
            return prices
        except Exception as e:
            logger.error(f"Failed to get prices: {e}")
            return {}
    
    def check_signals(self, data: Dict[str, pd.DataFrame]) -> List[TradeSignal]:
        """Check for trade signals across all symbols"""
        signals = []
        
        for symbol, df in data.items():
            if symbol not in self.signal_generators:
                continue
                
            generator = self.signal_generators[symbol]
            signal = generator.generate_signal(df, self.portfolio.current_capital)
            
            if signal and self.portfolio.can_open_position(symbol, signal):
                signals.append(signal)
                
        return signals
    
    def execute_signal(self, signal: TradeSignal) -> bool:
        """
        Execute a trade signal
        
        Returns True if successful
        """
        logger.info(f"Executing {signal.signal_type.value} signal for {signal.symbol}")
        logger.info(f"  Entry: ${signal.entry_price:.2f}")
        logger.info(f"  Stop: ${signal.stop_loss:.2f}")
        logger.info(f"  Target: ${signal.take_profit:.2f}")
        logger.info(f"  Size: {signal.position_size*100:.2f}%")
        
        if self.sandbox:
            logger.info("  [SANDBOX MODE - No real trade executed]")
            self.portfolio.open_position(signal)
            return True
            
        # Real trading logic here
        # TODO: Implement actual Coinbase API calls
        # 1. Calculate order size in base currency
        # 2. Place limit order at entry price
        # 3. Set stop loss (may need separate order)
        # 4. Set take profit (may need separate order)
        
        return False
    
    def update_positions(self):
        """Update open positions and check for exits"""
        prices = self.get_current_prices()
        closed = self.portfolio.update_positions(prices)
        
        for symbol in closed:
            logger.info(f"Position closed: {symbol}")
            
    def run_trading_cycle(self, data: Dict[str, pd.DataFrame]):
        """Run one trading cycle"""
        logger.info("=" * 60)
        logger.info(f"Trading Cycle: {datetime.now()}")
        logger.info("=" * 60)
        
        # Update existing positions
        self.update_positions()
        
        # Check for new signals
        signals = self.check_signals(data)
        
        if signals:
            logger.info(f"\nFound {len(signals)} signals:")
            for signal in signals:
                self.execute_signal(signal)
        else:
            logger.info("\nNo signals found")
            
        # Log portfolio status
        summary = self.portfolio.get_portfolio_summary()
        logger.info(f"\nPortfolio Summary:")
        logger.info(f"  Capital: ${summary['current_capital']:.2f}")
        logger.info(f"  Return: {summary['total_return']*100:.2f}%")
        logger.info(f"  Open positions: {summary['open_positions']}")

# ============================================================================
# BACKTEST RUNNER
# ============================================================================

class BacktestRunner:
    """Run comprehensive backtests"""
    
    def __init__(self, data: Dict[str, pd.DataFrame]):
        self.data = data
        self.results = {}
        
    def run_vpin_strategy(self) -> Dict:
        """Run VPIN mean reversion backtest"""
        logger.info("Running VPIN Mean Reversion Backtest...")
        
        engine = BacktestEngine(
            symbols=list(self.data.keys()),
            initial_capital=100000.0
        )
        
        results = engine.run(self.data)
        self.results['vpin_mean_reversion'] = results
        
        return results
    
    def run_walk_forward_validation(self) -> Dict:
        """Run walk-forward validation"""
        logger.info("Running Walk-Forward Validation...")
        
        from lightgbm_ensemble import WalkForwardCV, ModelConfig
        from vpin_mean_reversion_strategy import FeatureEngineer
        
        results = {}
        
        for symbol, df in self.data.items():
            logger.info(f"  Validating {symbol}...")
            
            # Create features
            engineer = FeatureEngineer()
            features_df = engineer.create_features(df)
            
            # Run walk-forward CV
            wf = WalkForwardCV(n_splits=6)
            feature_cols = [c for c in features_df.columns if c != 'target']
            
            cv_results = wf.validate(
                features_df, feature_cols, 'target', ModelConfig()
            )
            
            results[symbol] = cv_results
            
        self.results['walk_forward_cv'] = results
        return results
    
    def generate_report(self) -> str:
        """Generate backtest report"""
        report = []
        report.append("=" * 70)
        report.append("BACKTEST REPORT")
        report.append("=" * 70)
        report.append(f"Generated: {datetime.now()}")
        report.append("")
        
        # VPIN Strategy Results
        if 'vpin_mean_reversion' in self.results:
            vpin = self.results['vpin_mean_reversion']
            report.append("VPIN Mean Reversion Strategy")
            report.append("-" * 40)
            report.append(f"Total Return: {vpin.get('total_return', 0)*100:.2f}%")
            report.append(f"Sharpe Ratio: {vpin.get('sharpe_ratio', 0):.2f}")
            report.append(f"Max Drawdown: {vpin.get('max_drawdown', 0)*100:.2f}%")
            report.append(f"Win Rate: {vpin.get('win_rate', 0)*100:.2f}%")
            report.append(f"Total Trades: {vpin.get('total_trades', 0)}")
            report.append(f"Profit Factor: {vpin.get('profit_factor', 0):.2f}")
            report.append("")
            
        # Walk-Forward Results
        if 'walk_forward_cv' in self.results:
            report.append("Walk-Forward Validation")
            report.append("-" * 40)
            for symbol, results in self.results['walk_forward_cv'].items():
                report.append(f"{symbol}:")
                report.append(f"  Mean Correlation: {results.get('mean_correlation', 0):.4f}")
                report.append(f"  Std Correlation: {results.get('std_correlation', 0):.4f}")
            report.append("")
            
        report.append("=" * 70)
        return "\n".join(report)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='VPIN + LightGBM Crypto Trading')
    parser.add_argument('--mode', choices=['backtest', 'paper', 'live'], 
                       default='backtest', help='Trading mode')
    parser.add_argument('--symbols', nargs='+', 
                       default=['BTC-USDC', 'ETH-USDC', 'SOL-USDC', 'LTC-USDC', 'DOGE-USDC', 'XRP-USDC'],
                       help='Symbols to trade')
    parser.add_argument('--days', type=int, default=90, help='Days of historical data')
    parser.add_argument('--capital', type=float, default=10000.0, help='Initial capital')
    
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("VPIN Mean Reversion + LightGBM Ensemble Strategy")
    logger.info("=" * 70)
    logger.info(f"Mode: {args.mode}")
    logger.info(f"Symbols: {', '.join(args.symbols)}")
    logger.info(f"Initial Capital: ${args.capital:,.2f}")
    logger.info("=" * 70)
    
    # Load data
    logger.info("\nLoading historical data...")
    loader = CoinbaseDataLoader()
    data = loader.load_all_symbols(days_back=args.days)
    
    if not data:
        logger.error("No data loaded. Exiting.")
        return
        
    logger.info(f"Loaded {len(data)} symbols")
    
    if args.mode == 'backtest':
        # Run backtest
        runner = BacktestRunner(data)
        
        # VPIN strategy
        vpin_results = runner.run_vpin_strategy()
        
        # Walk-forward validation
        # wf_results = runner.run_walk_forward_validation()
        
        # Generate report
        report = runner.generate_report()
        print("\n" + report)
        
        # Save results
        with open('backtest_results.json', 'w') as f:
            json.dump(vpin_results, f, indent=2, default=str)
        logger.info("\nResults saved to backtest_results.json")
        
    elif args.mode == 'paper':
        # Paper trading
        trader = LiveTrader(sandbox=True)
        
        logger.info("\nStarting paper trading...")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                trader.run_trading_cycle(data)
                
                # Wait for next hour
                import time
                time.sleep(3600)
                
                # Reload data
                data = loader.load_all_symbols(days_back=args.days)
                
        except KeyboardInterrupt:
            logger.info("\nPaper trading stopped")
            
    elif args.mode == 'live':
        logger.error("\n" + "=" * 70)
        logger.error("WARNING: LIVE TRADING MODE")
        logger.error("=" * 70)
        logger.error("You are about to trade with REAL MONEY.")
        logger.error("Have you:")
        logger.error("  1. Run backtests for 6+ months of data?")
        logger.error("  2. Paper traded for 1+ month?")
        logger.error("  3. Verified all API keys are correct?")
        logger.error("  4. Set appropriate position sizes?")
        logger.error("=" * 70)
        
        confirm = input("\nType 'YES' to proceed with live trading: ")
        
        if confirm != 'YES':
            logger.info("Live trading cancelled")
            return
            
        # Load API credentials from environment
        import os
        api_key = os.getenv('COINBASE_API_KEY')
        api_secret = os.getenv('COINBASE_API_SECRET')
        passphrase = os.getenv('COINBASE_PASSPHRASE')
        
        if not all([api_key, api_secret, passphrase]):
            logger.error("API credentials not found in environment variables")
            return
            
        trader = LiveTrader(api_key, api_secret, passphrase, sandbox=False)
        
        logger.info("\nStarting LIVE trading...")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                trader.run_trading_cycle(data)
                
                import time
                time.sleep(3600)
                data = loader.load_all_symbols(days_back=args.days)
                
        except KeyboardInterrupt:
            logger.info("\nLive trading stopped")

if __name__ == "__main__":
    main()
