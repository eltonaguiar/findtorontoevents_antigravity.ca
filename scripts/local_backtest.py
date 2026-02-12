import pandas as pd
import backtrader as bt

class SimpleStrategy(bt.Strategy):
    def next(self):
        if not self.position:
            self.buy()
        elif self.data.close[0] > self.data.close[-1] * 1.05:
            self.sell()

def run_backtest(csv_path):
    cerebro = bt.Cerebro()
    data = bt.feeds.PandasData(dataname=pd.read_csv(csv_path, parse_dates=True, index_col='date'))
    cerebro.adddata(data)
    cerebro.addstrategy(SimpleStrategy)
    cerebro.run()
    return cerebro.broker.getvalue()

# Usage: run_backtest('prices.csv')