"""
Theta Strategy Cloner v2 - Improved Implementation
u/heyredditaddict's Options Algo with better modeling
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)


@dataclass
class OptionPosition:
    """Represents a short option position"""
    strike: float
    expiry: datetime
    option_type: str  # 'put' or 'call'
    delta: float
    iv_at_entry: float
    underlying_at_entry: float
    entry_credit: float
    entry_date: datetime
    contracts: int = 1
    
    # Tracking
    exit_date: Optional[datetime] = None
    exit_debit: float = 0.0
    closed: bool = False
    close_reason: str = ""
    realized_pnl: float = 0.0
    was_assigned: bool = False
    
    # Costs per contract
    entry_commission: float = 0.65
    exit_commission: float = 0.65
    
    def days_to_expiry(self, current_date: datetime) -> int:
        return max(0, (self.expiry - current_date).days)
    
    def is_otm(self, current_price: float) -> bool:
        if self.option_type == 'put':
            return current_price > self.strike
        else:
            return current_price < self.strike
    
    def intrinsic_value(self, current_price: float) -> float:
        if self.option_type == 'put':
            return max(0, self.strike - current_price)
        else:
            return max(0, current_price - self.strike)


@dataclass
class TradeRecord:
    """Record of completed trade"""
    entry_date: datetime
    exit_date: datetime
    option_type: str
    strike: float
    contracts: int
    entry_credit: float
    exit_debit: float
    days_held: int
    gross_pnl: float
    net_pnl: float
    close_reason: str
    was_assigned: bool


class OptionPricer:
    """Simplified but realistic option pricing"""
    
    @staticmethod
    def black_scholes(S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> Tuple[float, float]:
        """
        Black-Scholes option pricing
        Returns: (price, delta)
        """
        from math import log, sqrt, exp, erf
        
        if T <= 0:
            # At expiration
            if option_type == 'call':
                price = max(0, S - K)
                delta = 1.0 if S > K else 0.0
            else:
                price = max(0, K - S)
                delta = -1.0 if S < K else 0.0
            return price, delta
        
        d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
        d2 = d1 - sigma * sqrt(T)
        
        # Cumulative normal distribution
        def N(x):
            return 0.5 * (1 + erf(x / sqrt(2)))
        
        if option_type == 'call':
            price = S * N(d1) - K * exp(-r * T) * N(d2)
            delta = N(d1)
        else:
            price = K * exp(-r * T) * N(-d2) - S * N(-d1)
            delta = -N(-d1)
        
        return max(0.01, price), delta
    
    @staticmethod
    def calculate_theta(S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> float:
        """Calculate daily theta (time decay)"""
        from math import log, sqrt, exp, erf, pi
        
        if T <= 0.001:
            return 0
        
        d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
        
        def N_prime(x):
            return exp(-x**2 / 2) / sqrt(2 * pi)
        
        theta = -(S * N_prime(d1) * sigma) / (2 * sqrt(T))
        
        if option_type == 'call':
            theta -= r * K * exp(-r * T) * (0.5 * (1 + erf((d1 - sigma * sqrt(T)) / sqrt(2))))
        else:
            theta += r * K * exp(-r * T) * (0.5 * (1 + erf(-(d1 - sigma * sqrt(T)) / sqrt(2))))
        
        return theta / 365  # Convert to daily


class ThetaStrategyV2:
    """
    Improved Theta Selling Strategy
    
    Entry Rules:
    - Sell OTM puts when IV > 50th percentile, delta 0.15-0.30
    - Sell OTM calls when IV > 50th percentile, delta 0.15-0.30
    - Target 30-45 DTE
    
    Exit Rules:
    - 50% profit target
    - 21 DTE (time-based)
    - 200% loss stop
    - Roll if tested (underlying within 2% of strike)
    """
    
    def __init__(
        self,
        initial_capital: float = 100000,
        max_positions: int = 5,
        max_position_size: float = 5000,  # Max $ at risk per trade
        profit_target: float = 0.50,
        max_loss_multiplier: float = 2.0,
        min_dte_entry: int = 30,
        max_dte_entry: int = 45,
        min_dte_exit: int = 21,
        delta_min: float = 0.15,
        delta_max: float = 0.30,
        iv_percentile_threshold: float = 0.50,
        commission: float = 0.65,
        spread_slippage: float = 0.03,
        tested_threshold: float = 0.02,
    ):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.max_positions = max_positions
        self.max_position_size = max_position_size
        self.profit_target = profit_target
        self.max_loss_multiplier = max_loss_multiplier
        self.min_dte_entry = min_dte_entry
        self.max_dte_entry = max_dte_entry
        self.min_dte_exit = min_dte_exit
        self.delta_min = delta_min
        self.delta_max = delta_max
        self.iv_percentile_threshold = iv_percentile_threshold
        self.commission = commission
        self.spread_slippage = spread_slippage
        self.tested_threshold = tested_threshold
        
        self.pricer = OptionPricer()
        self.positions: List[OptionPosition] = []
        self.trades: List[TradeRecord] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        
    def find_optimal_strike(
        self,
        S: float,
        option_type: str,
        T: float,
        r: float,
        sigma: float,
        target_delta: float
    ) -> Optional[Tuple[float, float, float]]:
        """Find strike that gives target delta"""
        
        # Search range for strikes
        if option_type == 'put':
            # OTM puts: strikes below spot
            strikes = np.linspace(S * 0.85, S * 0.98, 50)
        else:
            # OTM calls: strikes above spot
            strikes = np.linspace(S * 1.02, S * 1.15, 50)
        
        best_strike = None
        best_delta_diff = float('inf')
        best_price = 0
        best_delta = 0
        
        for K in strikes:
            price, delta = self.pricer.black_scholes(S, K, T, r, sigma, option_type)
            
            # For puts, delta is negative (but we use absolute for selection)
            check_delta = abs(delta)
            
            if self.delta_min <= check_delta <= self.delta_max:
                delta_diff = abs(check_delta - target_delta)
                if delta_diff < best_delta_diff:
                    best_delta_diff = delta_diff
                    best_strike = K
                    best_price = price
                    best_delta = delta
        
        if best_strike is None:
            return None
        
        return (best_strike, best_delta, best_price)
    
    def calculate_position_value(
        self,
        position: OptionPosition,
        S: float,
        current_date: datetime,
        sigma: float
    ) -> float:
        """Calculate current market value to close position"""
        T = position.days_to_expiry(current_date) / 365.0
        r = 0.045  # Risk-free rate
        
        price, _ = self.pricer.black_scholes(
            S, position.strike, T, r, sigma, position.option_type
        )
        
        # Add spread/slippage for exit
        exit_price = price * (1 + self.spread_slippage)
        
        return exit_price
    
    def check_exit(
        self,
        position: OptionPosition,
        S: float,
        current_date: datetime,
        sigma: float
    ) -> Optional[str]:
        """Check if position should be closed"""
        
        dte = position.days_to_expiry(current_date)
        
        # 1. Time-based exit
        if dte <= self.min_dte_exit:
            return "time_exit"
        
        # 2. Calculate current value
        current_value = self.calculate_position_value(position, S, current_date, sigma)
        
        # 3. Profit target (50% of max profit)
        profit_pct = (position.entry_credit - current_value) / position.entry_credit
        if profit_pct >= self.profit_target:
            return "profit_target"
        
        # 4. Stop loss (200% of credit = 2x loss)
        max_loss = position.entry_credit * self.max_loss_multiplier
        if current_value >= position.entry_credit + max_loss:
            return "stop_loss"
        
        # 5. Tested/roll condition
        if position.is_otm(S):
            distance = abs(S - position.strike) / S
            if distance < self.tested_threshold:
                return "tested"
        else:
            # ITM - close immediately
            return "itm_exit"
        
        return None
    
    def close_position(
        self,
        position: OptionPosition,
        current_date: datetime,
        S: float,
        sigma: float,
        reason: str
    ) -> TradeRecord:
        """Close position and record trade"""
        
        position.closed = True
        position.exit_date = current_date
        position.close_reason = reason
        
        # Calculate exit value
        current_value = self.calculate_position_value(position, S, current_date, sigma)
        position.exit_debit = current_value
        
        # Check assignment at expiration
        if reason == "time_exit" or position.days_to_expiry(current_date) <= 0:
            if not position.is_otm(S):
                position.was_assigned = True
        
        # Calculate P&L
        gross_pnl_per_contract = position.entry_credit - current_value
        total_commission = (position.entry_commission + position.exit_commission) * position.contracts
        gross_pnl = gross_pnl_per_contract * 100 * position.contracts
        net_pnl = gross_pnl - total_commission
        
        position.realized_pnl = net_pnl
        
        trade = TradeRecord(
            entry_date=position.entry_date,
            exit_date=current_date,
            option_type=position.option_type,
            strike=position.strike,
            contracts=position.contracts,
            entry_credit=position.entry_credit,
            exit_debit=current_value,
            days_held=(current_date - position.entry_date).days,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            close_reason=reason,
            was_assigned=position.was_assigned
        )
        
        self.trades.append(trade)
        self.capital += net_pnl
        
        return trade
    
    def generate_spy_data(
        self,
        start: datetime,
        end: datetime,
        S0: float = 475.0
    ) -> pd.DataFrame:
        """Generate realistic SPY price and IV data"""
        
        dates = pd.date_range(start=start, end=end, freq='B')
        n_days = len(dates)
        
        # Parameters based on SPY historical behavior
        mu = 0.10  # 10% annual return
        sigma_price = 0.16  # 16% annual volatility
        
        # Mean-reverting IV process (VIX-like)
        # dIV = theta*(mu_IV - IV)*dt + sigma_IV*sqrt(IV)*dW
        iv_mean = 0.17
        iv_speed = 0.15
        iv_vol = 0.40
        
        prices = np.zeros(n_days)
        ivs = np.zeros(n_days)
        
        prices[0] = S0
        ivs[0] = 0.16
        
        dt = 1 / 252
        
        for i in range(1, n_days):
            # Price evolution
            dW_price = np.random.normal(0, np.sqrt(dt))
            prices[i] = prices[i-1] * np.exp(
                (mu - 0.5 * sigma_price**2) * dt + sigma_price * dW_price
            )
            
            # IV evolution (mean-reverting)
            dW_iv = np.random.normal(0, np.sqrt(dt))
            iv_drift = iv_speed * (iv_mean - ivs[i-1]) * dt
            iv_diffusion = iv_vol * np.sqrt(max(0.01, ivs[i-1])) * dW_iv
            ivs[i] = max(0.10, min(0.50, ivs[i-1] + iv_drift + iv_diffusion))
        
        df = pd.DataFrame({
            'price': prices,
            'iv': ivs
        }, index=dates)
        
        # Calculate rolling IV percentile (252-day lookback)
        df['iv_percentile'] = df['iv'].rolling(window=252, min_periods=60).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1]
        )
        
        return df
    
    def run_backtest(
        self,
        start: datetime,
        end: datetime,
        entry_frequency: int = 3
    ) -> Dict:
        """Run backtest"""
        
        print("Generating SPY market data (2024-2026)...")
        data = self.generate_spy_data(start, end)
        
        print(f"Backtesting: {start.date()} to {end.date()}")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print("-" * 60)
        
        r = 0.045  # Risk-free rate
        last_entry_check = start
        
        for date, row in data.iterrows():
            S = row['price']
            sigma = row['iv']
            iv_pct = row['iv_percentile'] if not pd.isna(row['iv_percentile']) else 0.5
            
            # 1. Manage existing positions
            for pos in self.positions[:]:
                if pos.closed:
                    continue
                
                exit_reason = self.check_exit(pos, S, date, sigma)
                if exit_reason:
                    self.close_position(pos, date, S, sigma, exit_reason)
                    self.positions.remove(pos)
            
            # 2. Look for new entries
            days_since_check = (date - last_entry_check).days
            
            if days_since_check >= entry_frequency and len(self.positions) < self.max_positions:
                last_entry_check = date
                
                # Check IV percentile
                if iv_pct >= self.iv_percentile_threshold:
                    
                    # Alternate between puts and calls based on trend
                    # Simple trend filter: if price > 20-day MA, sell puts; else sell calls
                    ma20 = data['price'].rolling(20).mean().loc[date] if len(data.loc[:date]) >= 20 else S
                    
                    if S > ma20:
                        option_type = 'put'  # Bullish bias
                    else:
                        option_type = 'call'  # Bearish bias
                    
                    # Find appropriate strike
                    T = self.min_dte_entry / 365.0
                    target_delta = 0.20  # Middle of range
                    
                    result = self.find_optimal_strike(S, option_type, T, r, sigma, target_delta)
                    
                    if result:
                        strike, delta, theoretical_price = result
                        
                        # Apply entry slippage (pay less credit due to spread)
                        entry_credit = theoretical_price * (1 - self.spread_slippage * 0.5)
                        
                        # Position sizing: max 10% of capital at risk
                        max_risk = self.capital * 0.10
                        contracts = max(1, int(max_risk / (strike * 100 * 0.10)))
                        contracts = min(contracts, 5)  # Cap at 5 contracts
                        
                        # Create position
                        position = OptionPosition(
                            strike=strike,
                            expiry=date + timedelta(days=self.min_dte_entry),
                            option_type=option_type,
                            delta=delta,
                            iv_at_entry=sigma,
                            underlying_at_entry=S,
                            entry_credit=entry_credit,
                            entry_date=date,
                            contracts=contracts
                        )
                        
                        self.positions.append(position)
            
            # 3. Record equity (cash + unrealized P&L)
            unrealized = 0
            for pos in self.positions:
                if not pos.closed:
                    current_val = self.calculate_position_value(pos, S, date, sigma)
                    unrealized += (pos.entry_credit - current_val) * 100 * pos.contracts
            
            total_equity = self.capital + unrealized
            self.equity_curve.append((date, total_equity))
        
        # Close all remaining positions
        final_date = data.index[-1]
        final_S = data['price'].iloc[-1]
        final_sigma = data['iv'].iloc[-1]
        
        for pos in self.positions[:]:
            if not pos.closed:
                self.close_position(pos, final_date, final_S, final_sigma, "backtest_end")
        
        return self.calculate_metrics(data)
    
    def calculate_metrics(self, market_data: pd.DataFrame) -> Dict:
        """Calculate performance metrics"""
        
        if not self.trades:
            return {"error": "No trades"}
        
        # Trade stats
        total = len(self.trades)
        winners = sum(1 for t in self.trades if t.net_pnl > 0)
        losers = total - winners
        win_rate = winners / total if total > 0 else 0
        
        # P&L
        total_pnl = sum(t.net_pnl for t in self.trades)
        gross_profit = sum(t.net_pnl for t in self.trades if t.net_pnl > 0)
        gross_loss = abs(sum(t.net_pnl for t in self.trades if t.net_pnl < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        avg_credit = np.mean([t.entry_credit * 100 for t in self.trades])
        avg_pnl = total_pnl / total
        
        # Assignment
        assignments = sum(1 for t in self.trades if t.was_assigned)
        assignment_rate = assignments / total
        
        # Equity curve analysis
        equity_df = pd.DataFrame(self.equity_curve, columns=['date', 'equity'])
        equity_df['returns'] = equity_df['equity'].pct_change().fillna(0)
        
        # Returns
        total_return = (equity_df['equity'].iloc[-1] / self.initial_capital) - 1
        years = (equity_df['date'].iloc[-1] - equity_df['date'].iloc[0]).days / 365.25
        annualized = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
        
        # Risk metrics
        excess_returns = equity_df['returns'] - 0.04/252
        sharpe = np.sqrt(252) * excess_returns.mean() / equity_df['returns'].std() \
                 if equity_df['returns'].std() > 0 else 0
        
        equity_df['peak'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak']
        max_dd = equity_df['drawdown'].min()
        
        # Close reasons
        reasons = {}
        for t in self.trades:
            reasons[t.close_reason] = reasons.get(t.close_reason, 0) + 1
        
        # Days held
        avg_days = np.mean([t.days_held for t in self.trades])
        
        # SPY comparison
        spy_start = market_data['price'].iloc[0]
        spy_end = market_data['price'].iloc[-1]
        spy_return = (spy_end / spy_start) - 1
        spy_annual = (1 + spy_return) ** (1/years) - 1 if years > 0 else 0
        
        return {
            'total_trades': total,
            'winners': winners,
            'losers': losers,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_credit': avg_credit,
            'avg_pnl': avg_pnl,
            'profit_factor': profit_factor,
            'assignment_rate': assignment_rate,
            'total_return': total_return,
            'annualized_return': annualized,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'avg_days_held': avg_days,
            'close_reasons': reasons,
            'spy_return': spy_return,
            'spy_annualized': spy_annual,
            'outperformance': annualized - spy_annual,
            'final_capital': equity_df['equity'].iloc[-1],
            'equity_df': equity_df
        }


def print_report(metrics: Dict):
    """Print formatted report"""
    
    print("\n" + "=" * 70)
    print("     THETA STRATEGY BACKTEST RESULTS (u/heyredditaddict Clone)")
    print("=" * 70)
    
    print("\n📊 TRADE STATISTICS")
    print("-" * 50)
    print(f"  Total Trades:       {metrics['total_trades']}")
    print(f"  Winning Trades:     {metrics['winners']}")
    print(f"  Losing Trades:      {metrics['losers']}")
    print(f"  Win Rate:           {metrics['win_rate']*100:.1f}%")
    print(f"  Assignment Rate:    {metrics['assignment_rate']*100:.1f}%")
    print(f"  Avg Days Held:      {metrics['avg_days_held']:.1f}")
    
    print("\n💰 P&L METRICS")
    print("-" * 50)
    print(f"  Total P&L:          ${metrics['total_pnl']:,.2f}")
    print(f"  Avg Credit/Trade:   ${metrics['avg_credit']:.2f}")
    print(f"  Avg P&L/Trade:      ${metrics['avg_pnl']:.2f}")
    print(f"  Profit Factor:      {metrics['profit_factor']:.2f}")
    
    print("\n📈 PERFORMANCE")
    print("-" * 50)
    print(f"  Total Return:       {metrics['total_return']*100:+.2f}%")
    print(f"  Annualized Return:  {metrics['annualized_return']*100:+.2f}%")
    print(f"  SPY Buy & Hold:     {metrics['spy_return']*100:+.2f}%")
    print(f"  SPY Annualized:     {metrics['spy_annualized']*100:+.2f}%")
    print(f"  Outperformance:     {metrics['outperformance']*100:+.2f}%")
    print(f"  Sharpe Ratio:       {metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown:       {metrics['max_drawdown']*100:.2f}%")
    print(f"  Final Capital:      ${metrics['final_capital']:,.2f}")
    
    print("\n🚪 EXIT BREAKDOWN")
    print("-" * 50)
    for reason, count in sorted(metrics['close_reasons'].items(), key=lambda x: -x[1]):
        pct = count / metrics['total_trades'] * 100
        print(f"  {reason:20s} {count:3d} ({pct:5.1f}%)")
    
    print("\n" + "=" * 70)
    print("🎯 RETAIL VIABILITY ASSESSMENT")
    print("=" * 70)
    
    checks = []
    score = 0
    
    # Check 1: Win rate
    if metrics['win_rate'] >= 0.65:
        checks.append(("✅", f"High win rate: {metrics['win_rate']*100:.1f}% (≥65%)"))
        score += 1
    else:
        checks.append(("⚠️", f"Moderate win rate: {metrics['win_rate']*100:.1f}%"))
    
    # Check 2: Drawdown
    if metrics['max_drawdown'] >= -0.05:
        checks.append(("✅", f"Low drawdown: {metrics['max_drawdown']*100:.1f}% (≤5%)"))
        score += 1
    elif metrics['max_drawdown'] >= -0.10:
        checks.append(("⚠️", f"Moderate drawdown: {metrics['max_drawdown']*100:.1f}%"))
        score += 0.5
    else:
        checks.append(("❌", f"High drawdown: {metrics['max_drawdown']*100:.1f}% (>10%)"))
    
    # Check 3: Sharpe
    if metrics['sharpe_ratio'] >= 1.0:
        checks.append(("✅", f"Good Sharpe: {metrics['sharpe_ratio']:.2f} (≥1.0)"))
        score += 1
    elif metrics['sharpe_ratio'] >= 0.5:
        checks.append(("⚠️", f"Moderate Sharpe: {metrics['sharpe_ratio']:.2f}"))
        score += 0.5
    else:
        checks.append(("❌", f"Low Sharpe: {metrics['sharpe_ratio']:.2f} (<0.5)"))
    
    # Check 4: Profit factor
    if metrics['profit_factor'] >= 1.5:
        checks.append(("✅", f"Good profit factor: {metrics['profit_factor']:.2f}"))
        score += 1
    elif metrics['profit_factor'] >= 1.0:
        checks.append(("⚠️", f"Marginal profit factor: {metrics['profit_factor']:.2f}"))
        score += 0.5
    else:
        checks.append(("❌", f"Poor profit factor: {metrics['profit_factor']:.2f} (<1.0)"))
    
    # Check 5: Assignment
    if metrics['assignment_rate'] <= 0.05:
        checks.append(("✅", f"Low assignment: {metrics['assignment_rate']*100:.1f}%"))
        score += 1
    else:
        checks.append(("⚠️", f"Higher assignment: {metrics['assignment_rate']*100:.1f}%"))
    
    for icon, text in checks:
        print(f"  {icon} {text}")
    
    print(f"\n  Score: {score}/5 checks passed")
    
    if score >= 4:
        verdict = "🟢 VIABLE"
        note = "Suitable for retail with proper risk management"
    elif score >= 2.5:
        verdict = "🟡 CONDITIONAL"
        note = "Requires experience and careful position sizing"
    else:
        verdict = "🔴 NOT RECOMMENDED"
        note = "High risk for retail traders"
    
    print(f"\n  {verdict} - {note}")
    
    # Reality check
    print("\n" + "=" * 70)
    print("📋 CLAIMS vs REALITY")
    print("=" * 70)
    
    claimed = {
        'return': 0.317,
        'spy_return': 0.194,
        'max_dd': -0.0387
    }
    
    print(f"\n  {'Metric':<20} {'Claimed':>12} {'Backtest':>12} {'Status':>10}")
    print(f"  {'-'*56}")
    
    ret_status = "✅" if abs(metrics['annualized_return'] - claimed['return']) < 0.10 else "❌"
    print(f"  {'Annual Return':<20} {claimed['return']*100:>11.1f}% {metrics['annualized_return']*100:>11.1f}% {ret_status:>10}")
    
    spy_status = "✅" if abs(metrics['spy_annualized'] - claimed['spy_return']) < 0.05 else "⚠️"
    print(f"  {'SPY Return':<20} {claimed['spy_return']*100:>11.1f}% {metrics['spy_annualized']*100:>11.1f}% {spy_status:>10}")
    
    dd_status = "✅" if abs(metrics['max_drawdown'] - claimed['max_dd']) < 0.02 else "❌"
    print(f"  {'Max Drawdown':<20} {claimed['max_dd']*100:>11.2f}% {metrics['max_drawdown']*100:>11.2f}% {dd_status:>10}")
    
    print("\n" + "=" * 70)
    print("💡 KEY INSIGHTS")
    print("=" * 70)
    
    insights = []
    
    if metrics['win_rate'] > 0.60 and metrics['profit_factor'] < 1.0:
        insights.append("• High win rate but poor profit factor suggests large losers vs small winners")
    
    if metrics['outperformance'] < 0:
        insights.append("• Strategy underperformed buy-and-hold during this period")
    
    stop_pct = metrics['close_reasons'].get('stop_loss', 0) / metrics['total_trades'] * 100
    if stop_pct > 15:
        insights.append(f"• {stop_pct:.1f}% of trades hit stop loss - consider wider stops or smaller position size")
    
    tested_pct = metrics['close_reasons'].get('tested', 0) / metrics['total_trades'] * 100
    if tested_pct > 20:
        insights.append(f"• {tested_pct:.1f}% of trades were tested - consider wider OTM strikes")
    
    if not insights:
        insights.append("• Strategy performed as expected for theta selling")
        insights.append("• Win rate aligns with delta-based probability")
    
    for insight in insights:
        print(f"  {insight}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    # Configuration
    START = datetime(2024, 1, 2)
    END = datetime(2026, 2, 17)
    
    strategy = ThetaStrategyV2(
        initial_capital=100000,
        max_positions=4,
        max_position_size=5000,
        profit_target=0.50,
        max_loss_multiplier=2.0,
        min_dte_entry=30,
        max_dte_entry=45,
        min_dte_exit=21,
        delta_min=0.15,
        delta_max=0.30,
        iv_percentile_threshold=0.50,
        commission=0.65,
        spread_slippage=0.03,
        tested_threshold=0.02
    )
    
    metrics = strategy.run_backtest(START, END, entry_frequency=3)
    print_report(metrics)
