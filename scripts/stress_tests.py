# stress_tests.py - Historical stress testing with 2008 data
# Requirements: pip install pandas yfinance backtrader

import backtrader as bt
import yfinance as yf
import datetime

class StressStrategy(bt.Strategy):
    def __init__(self):
        self.rsi = bt.indicators.RSI(self.data.close)

    def next(self):
        if self.rsi < 30:
            self.buy()
        elif self.rsi > 70:
            self.sell()

def run_stress_test(ticker, start='2007-01-01', end='2009-12-31'):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(StressStrategy)
    
    data = bt.feeds.PandasData(dataname=yf.download(ticker, start, end))
    cerebro.adddata(data)
    
    cerebro.broker.setcash(10000.0)
    cerebro.run()
    
    final_value = cerebro.broker.getvalue()
    drawdown = (10000 - final_value) / 10000 * 100 if final_value < 10000 else 0
    return final_value, drawdown

if __name__ == '__main__':
    tickers = ['SPY', 'AAPL', 'MSFT']
    for t in tickers:
        val, dd = run_stress_test(t)
        print(f"{t}: Final {val:.2f}, Drawdown {dd:.1f}%")