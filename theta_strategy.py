"""
Theta Strategy Cloner - u/heyredditaddict's Options Algo
Backtest of OTM put/call selling strategy on SPY
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

# Set random seed for reproducibility
np.random.seed(42)


@dataclass
class OptionContract:
    """Represents a single option contract"""
    strike: float
    expiry: datetime
    option_type: str  # 'put' or 'call'
    delta: float
    iv: float
    underlying_price: float
    entry_credit: float
    entry_date: datetime
    dte_at_entry: int
    
    # Position tracking
    exit_date: Optional[datetime] = None
    exit_debit: Optional[float] = None
    closed: bool = False
    close_reason: Optional[str] = None
    pnl: float = 0.0
    
    # Costs
    entry_commission: float = 0.65
    exit_commission: float = 0.65
    entry_slippage: float = 0.0
    exit_slippage: float = 0.0
    
    def days_held(self, current_date: datetime) -> int:
        return (current_date - self.entry_date).days
    
    def dte(self, current_date: datetime) -> int:
        return max(0, (self.expiry - current_date).days)
    
    def is_expired(self, current_date: datetime) -> bool:
        return current_date >= self.expiry
    
    def moneyness(self, current_price: float) -> float:
        """Returns how far ITM/OTM the option is (negative = OTM for shorts)"""
        if self.option_type == 'put':
            return (self.strike - current_price) / current_price
        else:
            return (current_price - self.strike) / current_price
    
    def is_tested(self, current_price: float) -> bool:
        """Option is tested if underlying moves toward strike (within 1%)"""
        return abs(self.moneyness(current_price)) < 0.01


@dataclass
class Trade:
    """Completed trade record"""
    entry_date: datetime
    exit_date: datetime
    option_type: str
    strike: float
    entry_credit: float
    exit_debit: float
    dte_at_entry: int
    days_held: int
    pnl: float
    close_reason: str
    was_assigned: bool = False


class ThetaStrategy:
    """
    Theta Selling Strategy
    - Sell OTM puts when IV > 50th percentile, delta 0.15-0.30
    - Sell OTM calls when IV > 50th percentile, delta 0.15-0.30
    - Exit: 50% profit target or 21 DTE
    - Risk: Roll if tested, close at 200% loss
    """
    
    def __init__(
        self,
        initial_capital: float = 100000,
        max_position_size: float = 0.10,  # Max 10% per trade
        profit_target: float = 0.50,  # 50% of max profit
        max_loss_pct: float = 2.0,  # 200% loss (2x credit received)
        min_dte_entry: int = 30,
        min_dte_exit: int = 21,
        delta_min: float = 0.15,
        delta_max: float = 0.30,
        iv_percentile_threshold: float = 0.50,
        commission_per_contract: float = 0.65,
        spread_slippage: float = 0.03,  # Average spread cost
    ):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.max_position_size = max_position_size
        self.profit_target = profit_target
        self.max_loss_pct = max_loss_pct
        self.min_dte_entry = min_dte_entry
        self.min_dte_exit = min_dte_exit
        self.delta_min = delta_min
        self.delta_max = delta_max
        self.iv_percentile_threshold = iv_percentile_threshold
        self.commission = commission_per_contract
        self.spread_slippage = spread_slippage
        
        # State
        self.positions: List[OptionContract] = []
        self.closed_trades: List[Trade] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.daily_returns: List[float] = []
        
    def calculate_iv_percentile(self, current_iv: float, iv_history: List[float]) -> float:
        """Calculate IV percentile from historical data"""
        if not iv_history or len(iv_history) < 30:
            return 0.5  # Default to median if insufficient data
        return sum(1 for iv in iv_history if iv < current_iv) / len(iv_history)
    
    def find_otm_option(
        self,
        underlying_price: float,
        option_type: str,
        target_delta: float,
        available_strikes: List[float],
        current_iv: float,
        dte: int
    ) -> Optional[Tuple[float, float, float]]:
        """
        Find appropriate OTM option
        Returns: (strike, delta, iv) or None
        """
        # Filter strikes based on OTM direction
        if option_type == 'put':
            # OTM puts are below current price
            valid_strikes = [s for s in available_strikes if s < underlying_price * 0.98]
        else:
            # OTM calls are above current price
            valid_strikes = [s for s in available_strikes if s > underlying_price * 1.02]
        
        if not valid_strikes:
            return None
        
        # Simulate delta based on distance from current price and IV
        # Delta approximation: further OTM = lower delta
        best_strike = None
        best_delta_diff = float('inf')
        
        for strike in valid_strikes:
            distance = abs(strike - underlying_price) / underlying_price
            # Approximate delta: closer to ATM = higher delta
            approx_delta = max(0.05, 0.5 - distance * 5 + current_iv * 0.5)
            approx_delta = min(0.50, approx_delta)
            
            if self.delta_min <= approx_delta <= self.delta_max:
                delta_diff = abs(approx_delta - target_delta)
                if delta_diff < best_delta_diff:
                    best_delta_diff = delta_diff
                    best_strike = strike
        
        if best_strike is None:
            return None
            
        # Calculate actual delta for selected strike
        distance = abs(best_strike - underlying_price) / underlying_price
        delta = max(0.05, 0.5 - distance * 5 + current_iv * 0.5)
        delta = min(0.50, delta)
        
        return (best_strike, delta, current_iv)
    
    def calculate_option_price(
        self,
        strike: float,
        underlying: float,
        dte: int,
        iv: float,
        option_type: str
    ) -> float:
        """Simplified Black-Scholes approximation for credit calculation"""
        # Time decay factor
        t = dte / 365.0
        
        # Distance from strike
        if option_type == 'put':
            intrinsic = max(0, strike - underlying)
        else:
            intrinsic = max(0, underlying - strike)
        
        # Time value approximation
        time_value = underlying * iv * np.sqrt(t) * 0.4
        
        # OTM options have no intrinsic, only time value
        if option_type == 'put' and underlying > strike:
            price = time_value * (1 - (underlying - strike) / (underlying * 0.1))
        elif option_type == 'call' and underlying < strike:
            price = time_value * (1 - (strike - underlying) / (underlying * 0.1))
        else:
            price = intrinsic + time_value * 0.5
        
        return max(0.01, price)
    
    def simulate_market_move(
        self,
        current_price: float,
        days: int,
        annual_vol: float = 0.16  # SPY typical vol
    ) -> float:
        """Simulate price movement using geometric Brownian motion"""
        daily_vol = annual_vol / np.sqrt(252)
        drift = 0.08 / 252  # ~8% annual return for SPY
        
        price = current_price
        for _ in range(days):
            shock = np.random.normal(0, 1)
            price *= np.exp((drift - 0.5 * daily_vol**2) + daily_vol * shock)
        
        return price
    
    def calculate_position_value(
        self,
        position: OptionContract,
        current_price: float,
        current_date: datetime,
        current_iv: float
    ) -> float:
        """Calculate current value to close position (debit paid)"""
        dte = position.dte(current_date)
        
        if dte <= 0:
            # Expired - intrinsic value only
            if position.option_type == 'put':
                return max(0, position.strike - current_price)
            else:
                return max(0, current_price - position.strike)
        
        # Calculate current theoretical price
        current_option_price = self.calculate_option_price(
            position.strike, current_price, dte, current_iv, position.option_type
        )
        
        # Add spread slippage for exit
        exit_slippage = current_option_price * self.spread_slippage
        
        return current_option_price + exit_slippage
    
    def check_exit_conditions(
        self,
        position: OptionContract,
        current_price: float,
        current_date: datetime,
        current_iv: float
    ) -> Optional[str]:
        """Check if position should be closed. Returns reason or None"""
        dte = position.dte(current_date)
        
        # 1. DTE exit
        if dte <= self.min_dte_exit:
            return "dte_exit"
        
        # 2. Calculate current value
        current_value = self.calculate_position_value(position, current_price, current_date, current_iv)
        
        # 3. Profit target (50% of max profit = paying back 50% of credit)
        profit_pct = (position.entry_credit - current_value) / position.entry_credit
        if profit_pct >= self.profit_target:
            return "profit_target"
        
        # 4. Max loss (200% of credit received)
        max_loss = position.entry_credit * self.max_loss_pct
        if current_value >= position.entry_credit + max_loss:
            return "max_loss"
        
        # 5. Roll if tested (price within 1% of strike)
        if position.is_tested(current_price):
            return "tested_roll"
        
        return None
    
    def close_position(
        self,
        position: OptionContract,
        current_date: datetime,
        current_price: float,
        current_iv: float,
        reason: str
    ) -> Trade:
        """Close a position and record the trade"""
        position.closed = True
        position.exit_date = current_date
        position.close_reason = reason
        
        # Calculate exit value
        exit_value = self.calculate_position_value(position, current_price, current_date, current_iv)
        position.exit_debit = exit_value
        
        # Calculate P&L
        gross_pnl = position.entry_credit - exit_value
        total_costs = position.entry_commission + position.exit_commission
        net_pnl = gross_pnl - total_costs
        position.pnl = net_pnl
        
        # Check for assignment at expiration
        was_assigned = False
        if reason == "dte_exit" or position.dte(current_date) <= 0:
            if position.option_type == 'put' and current_price < position.strike:
                was_assigned = True
            elif position.option_type == 'call' and current_price > position.strike:
                was_assigned = True
        
        trade = Trade(
            entry_date=position.entry_date,
            exit_date=current_date,
            option_type=position.option_type,
            strike=position.strike,
            entry_credit=position.entry_credit,
            exit_debit=exit_value,
            dte_at_entry=position.dte_at_entry,
            days_held=position.days_held(current_date),
            pnl=net_pnl,
            close_reason=reason,
            was_assigned=was_assigned
        )
        
        self.closed_trades.append(trade)
        self.capital += net_pnl * 100  # Options are 100 shares per contract
        
        return trade
    
    def generate_spy_data(
        self,
        start_date: datetime,
        end_date: datetime,
        initial_price: float = 470.0
    ) -> pd.DataFrame:
        """Generate synthetic SPY price and IV data for backtesting"""
        dates = pd.date_range(start=start_date, end=end_date, freq='B')  # Business days
        
        prices = []
        ivs = []
        current_price = initial_price
        
        # SPY historical parameters (approximate)
        annual_return = 0.10  # 10% annual return
        annual_vol = 0.16     # 16% annual volatility
        
        for i, date in enumerate(dates):
            # Mean-reverting IV (VIX-like behavior)
            if i == 0:
                current_iv = 0.18  # Start at 18%
            else:
                # IV mean reverts to ~16% with noise
                iv_drift = 0.16 - current_iv
                iv_noise = np.random.normal(0, 0.02)
                current_iv = max(0.10, min(0.50, current_iv + iv_drift * 0.02 + iv_noise))
            
            ivs.append(current_iv)
            
            # Price movement
            if i > 0:
                daily_return = np.random.normal(annual_return/252, annual_vol/np.sqrt(252))
                current_price *= (1 + daily_return)
            
            prices.append(current_price)
        
        df = pd.DataFrame({
            'date': dates,
            'price': prices,
            'iv': ivs
        })
        df.set_index('date', inplace=True)
        
        return df
    
    def run_backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        trade_frequency: int = 5  # Check for new trades every N days
    ) -> Dict:
        """Run the full backtest"""
        
        # Generate market data
        print("Generating SPY market data...")
        market_data = self.generate_spy_data(start_date, end_date)
        
        # Calculate rolling IV percentiles
        market_data['iv_percentile'] = market_data['iv'].rolling(window=252, min_periods=30).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1]
        )
        
        print(f"Backtesting from {start_date.date()} to {end_date.date()}")
        print(f"Initial capital: ${self.initial_capital:,.2f}")
        print("-" * 60)
        
        # Run simulation
        last_trade_check = start_date
        
        for date, row in market_data.iterrows():
            current_price = row['price']
            current_iv = row['iv']
            iv_percentile = row['iv_percentile'] if not pd.isna(row['iv_percentile']) else 0.5
            
            # 1. Manage existing positions
            positions_to_close = []
            for pos in self.positions:
                if pos.closed:
                    continue
                    
                exit_reason = self.check_exit_conditions(pos, current_price, date, current_iv)
                if exit_reason:
                    positions_to_close.append((pos, exit_reason))
            
            for pos, reason in positions_to_close:
                self.close_position(pos, date, current_price, current_iv, reason)
                self.positions.remove(pos)
            
            # 2. Look for new entries (every N days, max positions)
            if (date - last_trade_check).days >= trade_frequency and len(self.positions) < 3:
                last_trade_check = date
                
                # Check IV percentile condition
                if iv_percentile >= self.iv_percentile_threshold:
                    # Generate available strikes (SPY strikes every $1)
                    atm_strike = round(current_price)
                    available_strikes = list(range(atm_strike - 50, atm_strike + 51))
                    
                    # Decide put or call based on trend (simplified: alternate)
                    option_type = 'put' if len(self.closed_trades) % 2 == 0 else 'call'
                    target_delta = 0.20  # Middle of 0.15-0.30 range
                    
                    option_data = self.find_otm_option(
                        current_price, option_type, target_delta,
                        available_strikes, current_iv, self.min_dte_entry
                    )
                    
                    if option_data:
                        strike, delta, iv = option_data
                        
                        # Calculate credit received
                        credit = self.calculate_option_price(
                            strike, current_price, self.min_dte_entry, iv, option_type
                        )
                        
                        # Apply entry slippage
                        entry_slippage = credit * self.spread_slippage * 0.5
                        net_credit = credit - entry_slippage
                        
                        # Check position sizing
                        max_position_value = self.capital * self.max_position_size
                        contracts = int(max_position_value / (strike * 100))
                        contracts = max(1, min(contracts, 10))  # Cap at 10 contracts
                        
                        # Create position
                        position = OptionContract(
                            strike=strike,
                            expiry=date + timedelta(days=self.min_dte_entry),
                            option_type=option_type,
                            delta=delta,
                            iv=iv,
                            underlying_price=current_price,
                            entry_credit=net_credit,
                            entry_date=date,
                            dte_at_entry=self.min_dte_entry,
                            entry_commission=self.commission,
                            exit_commission=self.commission,
                            entry_slippage=entry_slippage
                        )
                        
                        self.positions.append(position)
            
            # Record equity
            # Calculate unrealized P&L for open positions
            unrealized_pnl = 0
            for pos in self.positions:
                if not pos.closed:
                    current_value = self.calculate_position_value(pos, current_price, date, current_iv)
                    unrealized_pnl += (pos.entry_credit - current_value) * 100
            
            total_equity = self.capital + unrealized_pnl
            self.equity_curve.append((date, total_equity))
        
        # Close any remaining positions at final price
        final_price = market_data['price'].iloc[-1]
        final_iv = market_data['iv'].iloc[-1]
        final_date = market_data.index[-1]
        
        for pos in self.positions[:]:
            if not pos.closed:
                self.close_position(pos, final_date, final_price, final_iv, "backtest_end")
        
        return self.calculate_metrics(market_data)
    
    def calculate_metrics(self, market_data: pd.DataFrame) -> Dict:
        """Calculate all performance metrics"""
        
        if not self.closed_trades:
            return {"error": "No trades executed"}
        
        # Basic counts
        total_trades = len(self.closed_trades)
        winning_trades = sum(1 for t in self.closed_trades if t.pnl > 0)
        losing_trades = total_trades - winning_trades
        
        # Win rate
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # P&L metrics
        total_pnl = sum(t.pnl * 100 for t in self.closed_trades)  # Per contract
        gross_profits = sum(t.pnl * 100 for t in self.closed_trades if t.pnl > 0)
        gross_losses = abs(sum(t.pnl * 100 for t in self.closed_trades if t.pnl < 0))
        
        avg_credit = np.mean([t.entry_credit * 100 for t in self.closed_trades])
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        # Profit factor
        profit_factor = gross_profits / gross_losses if gross_losses > 0 else float('inf')
        
        # Assignment rate
        assignments = sum(1 for t in self.closed_trades if t.was_assigned)
        assignment_rate = assignments / total_trades if total_trades > 0 else 0
        
        # Equity curve analysis
        equity_df = pd.DataFrame(self.equity_curve, columns=['date', 'equity'])
        equity_df['returns'] = equity_df['equity'].pct_change().fillna(0)
        
        # Total return
        total_return = (equity_df['equity'].iloc[-1] / self.initial_capital) - 1
        
        # Annualized return
        years = (equity_df['date'].iloc[-1] - equity_df['date'].iloc[0]).days / 365.25
        annualized_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
        
        # Sharpe ratio (assuming risk-free rate of 4%)
        excess_returns = equity_df['returns'] - 0.04/252
        sharpe_ratio = np.sqrt(252) * excess_returns.mean() / equity_df['returns'].std() \
                       if equity_df['returns'].std() > 0 else 0
        
        # Max drawdown
        equity_df['peak'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak']
        max_drawdown = equity_df['drawdown'].min()
        
        # Close reason breakdown
        close_reasons = {}
        for t in self.closed_trades:
            close_reasons[t.close_reason] = close_reasons.get(t.close_reason, 0) + 1
        
        # Days held stats
        avg_days_held = np.mean([t.days_held for t in self.closed_trades])
        
        # Buy and hold comparison
        spy_start = market_data['price'].iloc[0]
        spy_end = market_data['price'].iloc[-1]
        spy_return = (spy_end / spy_start) - 1
        spy_annualized = (1 + spy_return) ** (1/years) - 1 if years > 0 else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_credit': avg_credit,
            'avg_pnl': avg_pnl,
            'profit_factor': profit_factor,
            'assignment_rate': assignment_rate,
            'total_return': total_return,
            'annualized_return': annualized_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'avg_days_held': avg_days_held,
            'close_reasons': close_reasons,
            'spy_return': spy_return,
            'spy_annualized': spy_annualized,
            'outperformance': annualized_return - spy_annualized,
            'final_capital': equity_df['equity'].iloc[-1],
            'equity_curve': equity_df
        }


def print_results(metrics: Dict):
    """Print formatted backtest results"""
    
    print("\n" + "=" * 70)
    print("THETA STRATEGY BACKTEST RESULTS")
    print("=" * 70)
    
    print("\n📊 TRADE STATISTICS")
    print("-" * 40)
    print(f"Total Trades:        {metrics['total_trades']}")
    print(f"Winning Trades:      {metrics['winning_trades']}")
    print(f"Losing Trades:       {metrics['losing_trades']}")
    print(f"Win Rate:            {metrics['win_rate']*100:.1f}%")
    print(f"Assignment Rate:     {metrics['assignment_rate']*100:.1f}%")
    print(f"Avg Days Held:       {metrics['avg_days_held']:.1f}")
    
    print("\n💰 P&L METRICS")
    print("-" * 40)
    print(f"Total P&L:           ${metrics['total_pnl']:,.2f}")
    print(f"Avg Credit/Trade:    ${metrics['avg_credit']:.2f}")
    print(f"Avg P&L/Trade:       ${metrics['avg_pnl']:.2f}")
    print(f"Profit Factor:       {metrics['profit_factor']:.2f}")
    
    print("\n📈 PERFORMANCE")
    print("-" * 40)
    print(f"Total Return:        {metrics['total_return']*100:.2f}%")
    print(f"Annualized Return:   {metrics['annualized_return']*100:.2f}%")
    print(f"SPY Buy & Hold:      {metrics['spy_return']*100:.2f}%")
    print(f"SPY Annualized:      {metrics['spy_annualized']*100:.2f}%")
    print(f"Outperformance:      {metrics['outperformance']*100:.2f}%")
    print(f"Sharpe Ratio:        {metrics['sharpe_ratio']:.2f}")
    print(f"Max Drawdown:        {metrics['max_drawdown']*100:.2f}%")
    print(f"Final Capital:       ${metrics['final_capital']:,.2f}")
    
    print("\n🚪 EXIT REASONS")
    print("-" * 40)
    for reason, count in sorted(metrics['close_reasons'].items(), key=lambda x: -x[1]):
        pct = count / metrics['total_trades'] * 100
        print(f"  {reason:20s} {count:3d} ({pct:5.1f}%)")
    
    print("\n" + "=" * 70)
    
    # Viability assessment
    print("\n🎯 VIABILITY ASSESSMENT FOR RETAIL TRADERS")
    print("-" * 40)
    
    score = 0
    checks = []
    
    if metrics['win_rate'] > 0.60:
        checks.append("✅ High win rate (>60%)")
        score += 1
    else:
        checks.append("❌ Win rate below 60%")
    
    if metrics['max_drawdown'] > -0.10:
        checks.append("✅ Max drawdown < 10%")
        score += 1
    else:
        checks.append("❌ Max drawdown exceeds 10%")
    
    if metrics['sharpe_ratio'] > 1.0:
        checks.append("✅ Sharpe ratio > 1.0")
        score += 1
    else:
        checks.append("❌ Sharpe ratio below 1.0")
    
    if metrics['outperformance'] > 0:
        checks.append("✅ Outperforms SPY")
        score += 1
    else:
        checks.append("❌ Underperforms SPY")
    
    if metrics['assignment_rate'] < 0.10:
        checks.append("✅ Low assignment rate (<10%)")
        score += 1
    else:
        checks.append("⚠️  Higher assignment rate")
    
    for check in checks:
        print(f"  {check}")
    
    print(f"\n  Score: {score}/5 viability checks passed")
    
    if score >= 4:
        print("\n  🟢 VERDICT: VIABLE for retail with proper risk management")
    elif score >= 3:
        print("\n  🟡 VERDICT: CONDITIONALLY VIABLE - requires experience")
    else:
        print("\n  🔴 VERDICT: NOT RECOMMENDED for retail traders")
    
    # Reality check vs claimed returns
    print("\n📋 REALITY CHECK")
    print("-" * 40)
    claimed_return = 0.317  # 31.7%
    actual_return = metrics['annualized_return']
    
    print(f"  Claimed Return:    {claimed_return*100:.1f}%")
    print(f"  Backtest Return:   {actual_return*100:.1f}%")
    
    if actual_return >= claimed_return * 0.8:
        print("  ✅ Returns are in line with claims")
    elif actual_return >= claimed_return * 0.5:
        print("  ⚠️  Returns are lower but directionally similar")
    else:
        print("  ❌ Returns significantly differ from claims")
        print("     (May be due to different market conditions or overfitting)")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    # Run backtest for 2024-2026 period
    start_date = datetime(2024, 1, 2)
    end_date = datetime(2026, 2, 17)
    
    strategy = ThetaStrategy(
        initial_capital=100000,
        max_position_size=0.10,
        profit_target=0.50,
        max_loss_pct=2.0,
        min_dte_entry=45,
        min_dte_exit=21,
        delta_min=0.15,
        delta_max=0.30,
        iv_percentile_threshold=0.50,
        commission_per_contract=0.65,
        spread_slippage=0.035  # Average of 0.02-0.05
    )
    
    metrics = strategy.run_backtest(start_date, end_date, trade_frequency=3)
    print_results(metrics)
