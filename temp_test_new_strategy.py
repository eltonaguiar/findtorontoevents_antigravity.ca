import pandas as pd, requests, json
from baby_strategies.hoffman_variations import fetch_historical
from baby_strategies.hoffman_new_strategy import hoffman_new_strategy_signals
symbol='BTCUSDT'
url='https://api.binance.com/api/v3/klines'
resp=requests.get(url,params={'symbol':symbol,'interval':'15m','limit':1000},timeout=15)
resp.raise_for_status()
cols=["open_time","open","high","low","close","volume","close_time","qav","trades","tbbav","tbqav","ignore"]
df=pd.DataFrame(resp.json(),columns=cols)
for col in ["open","high","low","close","volume"]:
    df[col]=df[col].astype(float)
# get signals
sig=hoffman_new_strategy_signals(df,symbol)
print('signals count',len(sig))
if sig:
    print(sig[0])
