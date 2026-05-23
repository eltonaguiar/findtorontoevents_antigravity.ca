"""
Funding Rate Arbitrage Backtester
Strategy: Long Spot + Short Perpetual Futures (Delta Neutral)
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION
# =============================================================================

# Trading fees
SPOT_MAKER_FEE = 0.001  # 0.1%
SPOT_TAKER_FEE = 0.001  # 0.1%
FUTURES_MAKER_FEE = 0.0002  # 0.02%
FUTURES_TAKER_FEE = 0.0005  # 0.05%

# Assume taker fees for entry/exit (conservative)
SPOT_FEE = SPOT_TAKER_FEE
FUTURES_FEE = FUTURES_TAKER_FEE

# Funding occurs every 8 hours on most exchanges
FUNDING_PERIODS_PER_DAY = 3

# Risk-free rate (approximate for Sharpe calculation)
RISK_FREE_RATE = 0.05  # 5% annual

# =============================================================================
# DATA FETCHING FUNCTIONS
# =============================================================================

class FundingRateFetcher:
    """Fetch historical funding rates from major exchanges"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch_binance_funding(self, symbol: str, start_time: int, end_time: int) -> pd.DataFrame:
        """Fetch Binance funding rate history"""
        url = "https://fapi.binance.com/fapi/v1/fundingRate"
        
        all_data = []
        current_start = start_time
        
        while current_start < end_time:
            params = {
                'symbol': symbol,
                'startTime': current_start,
                'endTime': min(current_start + 90 * 24 * 3600 * 1000, end_time),  # 90 days max
                'limit': 1000
            }
            
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if not data:
                    break
                    
                all_data.extend(data)
                
                # Move to next batch
                last_time = data[-1]['fundingTime']
                current_start = last_time + 1
                
                if len(data) < 1000:
                    break
                    
            except Exception as e:
                print(f"Error fetching Binance funding: {e}")
                break
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        df['datetime'] = pd.to_datetime(df['fundingTime'], unit='ms')
        df['fundingRate'] = df['fundingRate'].astype(float)
        df = df.rename(columns={'fundingRate': 'rate'})
        df = df.sort_values('datetime').reset_index(drop=True)
        
        return df[['datetime', 'rate']]
    
    def fetch_binance_klines(self, symbol: str, start_time: int, end_time: int, 
                             interval: str = '8h') -> pd.DataFrame:
        """Fetch Binance spot klines (candlestick data)"""
        url = "https://api.binance.com/api/v3/klines"
        
        all_data = []
        current_start = start_time
        
        while current_start < end_time:
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': current_start,
                'endTime': min(current_start + 500 * 8 * 3600 * 1000, end_time),
                'limit': 500
            }
            
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if not data:
                    break
                    
                all_data.extend(data)
                
                last_time = data[-1][0]
                current_start = last_time + 1
                
                if len(data) < 500:
                    break
                    
            except Exception as e:
                print(f"Error fetching Binance klines: {e}")
                break
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_volume',
            'taker_buy_quote_volume', 'ignore'
        ])
        
        df['datetime'] = pd.to_datetime(df['open_time'], unit='ms')
        df['close'] = df['close'].astype(float)
        df = df.sort_values('datetime').reset_index(drop=True)
        
        return df[['datetime', 'close']]
    
    def fetch_okx_funding(self, symbol: str, start_time: int, end_time: int) -> pd.DataFrame:
        """Fetch OKX funding rate history"""
        url = "https://www.okx.com/api/v5/public/funding-rate-history"
        
        all_data = []
        current_start = start_time
        
        while current_start < end_time:
            params = {
                'instId': symbol,
                'before': '',
                'after': str(min(current_start + 90 * 24 * 3600 * 1000, end_time)),
                'limit': '100'
            }
            
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if data.get('code') != '0' or not data.get('data'):
                    break
                    
                all_data.extend(data['data'])
                
                if len(data['data']) < 100:
                    break
                    
                last_time = int(data['data'][-1]['fundingTime'])
                current_start = last_time + 1
                    
            except Exception as e:
                print(f"Error fetching OKX funding: {e}")
                break
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        df['datetime'] = pd.to_datetime(df['fundingTime'].astype(int), unit='ms')
        df['rate'] = df['fundingRate'].astype(float)
        df = df.sort_values('datetime').reset_index(drop=True)
        
        return df[['datetime', 'rate']]
    
    def fetch_bybit_funding(self, symbol: str, start_time: int, end_time: int) -> pd.DataFrame:
        """Fetch Bybit funding rate history"""
        url = "https://api.bybit.com/v5/market/funding/history"
        
        all_data = []
        cursor = None
        
        while True:
            params = {
                'category': 'linear',
                'symbol': symbol,
                'startTime': str(start_time),
                'endTime': str(end_time),
                'limit': '200'
            }
            if cursor:
                params['cursor'] = cursor
            
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if data.get('retCode') != 0 or not data.get('result', {}).get('list'):
                    break
                
                items = data['result']['list']
                all_data.extend(items)
                
                cursor = data['result'].get('nextPageCursor')
                if not cursor or len(items) < 200:
                    break
                    
            except Exception as e:
                print(f"Error fetching Bybit funding: {e}")
                break
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        df['datetime'] = pd.to_datetime(df['fundingRateTimestamp'].astype(int), unit='ms')
        df['rate'] = df['fundingRate'].astype(float)
        df = df.sort_values('datetime').reset_index(drop=True)
        
        return df[['datetime', 'rate']]


# =============================================================================
# BACKTEST ENGINE
# =============================================================================

class FundingArbBacktester:
    """
    Funding Rate Arbitrage Backtester
    Strategy: Long Spot + Short Perpetual Futures
    """
    
    def __init__(self, capital: float, leverage: float = 1.0):
        self.capital = capital
        self.leverage = leverage
        self.position_size = capital * leverage
        
        # Track state
        self.position_open = False
        self.entry_spot_price = 0
        self.entry_futures_price = 0
        self.cumulative_funding = 0
        self.trades = []
        
    def calculate_entry_costs(self, position_value: float) -> float:
        """Calculate costs to enter position"""
        spot_cost = position_value * SPOT_FEE
        futures_cost = position_value * FUTURES_FEE
        return spot_cost + futures_cost
    
    def calculate_exit_costs(self, position_value: float) -> float:
        """Calculate costs to exit position"""
        spot_cost = position_value * SPOT_FEE
        futures_cost = position_value * FUTURES_FEE
        return spot_cost + futures_cost
    
    def calculate_basis_pnl(self, spot_entry: float, spot_exit: float,
                           futures_entry: float, futures_exit: float,
                           position_value: float) -> float:
        """
        Calculate PnL from basis convergence/divergence
        Long spot: profit when spot goes up
        Short futures: profit when futures goes down
        """
        spot_pnl = position_value * (spot_exit - spot_entry) / spot_entry
        futures_pnl = position_value * (futures_entry - futures_exit) / futures_entry
        return spot_pnl + futures_pnl
    
    def run_backtest(self, funding_df: pd.DataFrame, price_df: pd.DataFrame,
                     start_date: str, end_date: str) -> Dict:
        """
        Run funding arbitrage backtest
        
        Returns dict with performance metrics
        """
        # Filter date range
        funding_df = funding_df[
            (funding_df['datetime'] >= start_date) & 
            (funding_df['datetime'] <= end_date)
        ].copy()
        
        price_df = price_df[
            (price_df['datetime'] >= start_date) & 
            (price_df['datetime'] <= end_date)
        ].copy()
        
        if len(funding_df) == 0 or len(price_df) == 0:
            return {'error': 'No data available for date range'}
        
        # Merge funding and price data
        # Use forward fill for prices to match funding timestamps
        price_df = price_df.set_index('datetime').resample('8h').last().ffill().reset_index()
        
        # Merge on datetime
        merged = pd.merge_asof(
            funding_df.sort_values('datetime'),
            price_df.sort_values('datetime'),
            on='datetime',
            direction='backward'
        )
        
        merged = merged.dropna()
        
        if len(merged) == 0:
            return {'error': 'No merged data available'}
        
        # Initialize tracking
        position_value = self.capital * self.leverage
        entry_costs = self.calculate_entry_costs(position_value)
        
        # Calculate funding payments received (we're short futures, so we receive when rate > 0)
        merged['funding_payment'] = position_value * merged['rate']
        
        # Total funding received
        total_funding = merged['funding_payment'].sum()
        
        # Calculate basis risk (price difference between spot and implied futures)
        # For simplicity, assume futures price = spot * (1 + basis)
        # We'll estimate basis from funding rate (approximate)
        merged['estimated_basis'] = merged['rate'] * 3  # Rough estimate: 8hr rate * 3 for daily
        
        # Calculate mark-to-market PnL from basis changes
        # This is the main risk - if basis widens, we lose money
        merged['basis_change'] = merged['estimated_basis'].diff()
        merged['basis_pnl'] = -position_value * merged['basis_change']
        
        # Calculate cumulative returns
        merged['cumulative_funding'] = merged['funding_payment'].cumsum()
        merged['cumulative_basis_pnl'] = merged['basis_pnl'].cumsum()
        merged['cumulative_total'] = merged['cumulative_funding'] + merged['cumulative_basis_pnl'] - entry_costs
        
        # Calculate exit costs (at the end)
        exit_costs = self.calculate_exit_costs(position_value)
        final_pnl = merged['cumulative_total'].iloc[-1] - exit_costs
        
        # Calculate metrics
        total_days = (merged['datetime'].iloc[-1] - merged['datetime'].iloc[0]).days
        if total_days == 0:
            total_days = 1
        
        # Daily returns for Sharpe
        merged['daily_return'] = merged['funding_payment'] / self.capital
        daily_returns = merged.groupby(merged['datetime'].dt.date)['daily_return'].sum()
        
        # Performance metrics
        avg_daily_funding = total_funding / total_days
        annualized_return = (final_pnl / self.capital) * (365 / total_days)
        
        # Sharpe ratio
        if len(daily_returns) > 1 and daily_returns.std() > 0:
            excess_returns = daily_returns - RISK_FREE_RATE / 365
            sharpe_ratio = np.sqrt(365) * excess_returns.mean() / daily_returns.std()
        else:
            sharpe_ratio = 0
        
        # Max drawdown
        cumulative = merged['cumulative_total']
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / self.capital
        max_drawdown = drawdown.min()
        
        # Win rate (positive funding periods)
        positive_periods = (merged['funding_payment'] > 0).sum()
        total_periods = len(merged)
        win_rate = positive_periods / total_periods if total_periods > 0 else 0
        
        return {
            'capital': self.capital,
            'position_size': position_value,
            'total_days': total_days,
            'total_funding_received': total_funding,
            'entry_costs': entry_costs,
            'exit_costs': exit_costs,
            'total_costs': entry_costs + exit_costs,
            'final_pnl': final_pnl,
            'final_pnl_pct': (final_pnl / self.capital) * 100,
            'avg_daily_funding': avg_daily_funding,
            'avg_daily_funding_pct': (avg_daily_funding / self.capital) * 100,
            'annualized_return_pct': annualized_return * 100,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': max_drawdown * 100,
            'win_rate': win_rate * 100,
            'total_periods': total_periods,
            'avg_funding_rate': merged['rate'].mean() * 100,
            'data': merged
        }


# =============================================================================
# SYNTHETIC DATA GENERATOR (for testing when API fails)
# =============================================================================

def generate_synthetic_data(start_date: str, end_date: str, 
                            avg_funding_rate: float = 0.0001,
                            volatility: float = 0.0005) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate synthetic funding rate and price data for backtesting
    """
    # Generate 8-hour intervals
    dates = pd.date_range(start=start_date, end=end_date, freq='8h')
    
    # Generate funding rates (mean-reverting process)
    np.random.seed(42)
    funding_rates = []
    current_rate = avg_funding_rate
    
    for _ in range(len(dates)):
        # Mean reversion
        current_rate += 0.1 * (avg_funding_rate - current_rate)
        # Add noise
        current_rate += np.random.normal(0, volatility)
        # Clamp to realistic range
        current_rate = np.clip(current_rate, -0.01, 0.01)
        funding_rates.append(current_rate)
    
    funding_df = pd.DataFrame({
        'datetime': dates,
        'rate': funding_rates
    })
    
    # Generate price data (random walk)
    initial_price = 50000 if 'BTC' in str(start_date) else 3000
    returns = np.random.normal(0.0001, 0.02, len(dates))
    prices = initial_price * np.exp(np.cumsum(returns))
    
    price_df = pd.DataFrame({
        'datetime': dates,
        'close': prices
    })
    
    return funding_df, price_df


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def fetch_real_data(symbol: str, start_date: str, end_date: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Try to fetch real data from exchanges"""
    fetcher = FundingRateFetcher()
    
    start_ts = int(pd.Timestamp(start_date).timestamp() * 1000)
    end_ts = int(pd.Timestamp(end_date).timestamp() * 1000)
    
    # Map symbols
    if symbol == 'BTC':
        futures_symbol = 'BTCUSDT'
        spot_symbol = 'BTCUSDT'
    elif symbol == 'ETH':
        futures_symbol = 'ETHUSDT'
        spot_symbol = 'ETHUSDT'
    else:
        futures_symbol = f'{symbol}USDT'
        spot_symbol = f'{symbol}USDT'
    
    print(f"Fetching funding rates for {futures_symbol}...")
    funding_df = fetcher.fetch_binance_funding(futures_symbol, start_ts, end_ts)
    
    print(f"Fetching price data for {spot_symbol}...")
    price_df = fetcher.fetch_binance_klines(spot_symbol, start_ts, end_ts, interval='8h')
    
    return funding_df, price_df


def run_full_backtest(symbol: str, capital_levels: List[float], 
                      start_date: str = '2024-01-01', 
                      end_date: str = '2025-12-31'):
    """Run backtest for a symbol across multiple capital levels"""
    
    print(f"\n{'='*60}")
    print(f"FUNDING ARBITRAGE BACKTEST: {symbol}")
    print(f"Period: {start_date} to {end_date}")
    print(f"{'='*60}\n")
    
    # Try to fetch real data
    funding_df, price_df = fetch_real_data(symbol, start_date, end_date)
    
    use_synthetic = False
    if len(funding_df) == 0 or len(price_df) == 0:
        print(f"⚠️  Could not fetch real data, using synthetic data...")
        funding_df, price_df = generate_synthetic_data(start_date, end_date)
        use_synthetic = True
    else:
        print(f"✓ Retrieved {len(funding_df)} funding records and {len(price_df)} price records")
    
    results = {}
    
    for capital in capital_levels:
        print(f"\n--- Capital: ${capital:,.0f} ---")
        
        backtester = FundingArbBacktester(capital=capital, leverage=1.0)
        result = backtester.run_backtest(funding_df, price_df, start_date, end_date)
        
        if 'error' in result:
            print(f"Error: {result['error']}")
            continue
        
        results[f"${capital:,.0f}"] = result
        
        print(f"  Position Size: ${result['position_size']:,.0f}")
        print(f"  Total Funding Received: ${result['total_funding_received']:,.2f}")
        print(f"  Trading Costs: ${result['total_costs']:,.2f}")
        print(f"  Final PnL: ${result['final_pnl']:,.2f} ({result['final_pnl_pct']:.2f}%)")
        print(f"  Avg Daily Funding: ${result['avg_daily_funding']:,.2f} ({result['avg_daily_funding_pct']:.4f}%)")
        print(f"  Annualized Return: {result['annualized_return_pct']:.2f}%")
        print(f"  Sharpe Ratio: {result['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: {result['max_drawdown_pct']:.2f}%")
        print(f"  Win Rate: {result['win_rate']:.1f}%")
        print(f"  Avg Funding Rate: {result['avg_funding_rate']:.4f}% per 8h")
    
    return results, funding_df, price_df, use_synthetic


def print_summary(btc_results: Dict, eth_results: Dict, use_synthetic: bool):
    """Print comprehensive summary"""
    
    print(f"\n{'='*70}")
    print("SUMMARY: FUNDING RATE ARBITRAGE STRATEGY")
    print(f"{'='*70}")
    
    if use_synthetic:
        print("\n⚠️  NOTE: Using SYNTHETIC data (API fetch failed)")
        print("    Real-world results may vary significantly\n")
    
    print("\n📊 STRATEGY OVERVIEW:")
    print("  • Long Spot + Short Perpetual Futures")
    print("  • Delta-neutral (no directional price risk)")
    print("  • Profit from funding rate payments")
    print("  • Risk: Basis convergence/divergence")
    
    print(f"\n💰 COSTS ASSUMED:")
    print(f"  • Spot Trading: {SPOT_FEE*100:.2f}% (taker)")
    print(f"  • Futures Trading: {FUTURES_FEE*100:.3f}% (taker)")
    print(f"  • Entry + Exit costs apply to full position size")
    
    print(f"\n📈 BTC RESULTS:")
    for capital_key, result in btc_results.items():
        print(f"  {capital_key}:")
        print(f"    Annualized Return: {result['annualized_return_pct']:.2f}%")
        print(f"    Sharpe Ratio: {result['sharpe_ratio']:.2f}")
        print(f"    Max Drawdown: {result['max_drawdown_pct']:.2f}%")
        print(f"    Daily Income: ${result['avg_daily_funding']:,.2f}")
    
    print(f"\n📈 ETH RESULTS:")
    for capital_key, result in eth_results.items():
        print(f"  {capital_key}:")
        print(f"    Annualized Return: {result['annualized_return_pct']:.2f}%")
        print(f"    Sharpe Ratio: {result['sharpe_ratio']:.2f}")
        print(f"    Max Drawdown: {result['max_drawdown_pct']:.2f}%")
        print(f"    Daily Income: ${result['avg_daily_funding']:,.2f}")
    
    print(f"\n{'='*70}")
    print("IS THIS THE SAFEST CRYPTO STRATEGY FOR RETAIL?")
    print(f"{'='*70}")
    
    analysis = """
PROS (Why it might be safe):
✓ Delta-neutral: No exposure to price direction
✓ Predictable income: Funding rates are known in advance
✓ No liquidation risk if fully collateralized (1x leverage)
✓ Exchange risk is the main concern, not market risk

CONS (Why it might NOT be safe):
✗ Basis risk: Spot-futures spread can widen unexpectedly
✗ Exchange risk: Counterparty risk, withdrawal freezes, hacks
✗ Capital intensive: Requires full collateral on both sides
✗ Low returns: Often 5-15% annualized before costs
✗ Funding can turn negative: You pay instead of receiving
✗ Execution complexity: Requires two simultaneous trades

RISKS NOT CAPTURED IN BACKTEST:
• Exchange insolvency (FTX, etc.)
• Withdrawal freezes during volatility
• API failures during critical moments
• Slippage on large positions
• Borrow costs for shorting spot (if not owned)

VERDICT:
This is ONE OF the safer crypto strategies, but NOT risk-free.
It's safer than directional trading but carries unique risks.
For retail: Start small, use reputable exchanges, monitor basis.
"""
    print(analysis)


if __name__ == "__main__":
    # Capital levels to test
    capital_levels = [5000, 10000, 50000]
    
    # Date range (2024-2026 as requested, but limited by data availability)
    start_date = '2024-01-01'
    end_date = '2025-02-01'  # Adjust based on current date
    
    # Run BTC backtest
    btc_results, btc_funding, btc_price, use_synthetic = run_full_backtest(
        'BTC', capital_levels, start_date, end_date
    )
    
    # Run ETH backtest
    eth_results, eth_funding, eth_price, _ = run_full_backtest(
        'ETH', capital_levels, start_date, end_date
    )
    
    # Print summary
    print_summary(btc_results, eth_results, use_synthetic)
