import sys, json, time
from datetime import datetime, timezone

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError as e:
    print(f"Missing: {e}")
    sys.exit(1)

ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
print(f"=== LIVE SCAN: {ts} ===")
print()
CRYPTO = ['BTC-USD','ETH-USD','SOL-USD','DOGE-USD','XRP-USD','ADA-USD',
          'AVAX-USD','LINK-USD','DOT-USD','MATIC-USD','NEAR-USD','ATOM-USD',
          'UNI-USD','LTC-USD','BCH-USD','PEPE24478-USD','SHIB-USD','ARB11841-USD']
FOREX = ['EURUSD=X','GBPUSD=X','USDJPY=X','AUDUSD=X','USDCAD=X','NZDUSD=X',
         'USDCHF=X','GBPJPY=X','EURJPY=X']
ALL = CRYPTO + FOREX

print('Fetching 60d daily data...')
try:
    raw = yf.download(' '.join(ALL), period='60d', interval='1d', group_by='ticker',
                      auto_adjust=True, threads=True, progress=False)
    print(f'  Got data shape: {raw.shape}')
except Exception as e:
    print(f'  yfinance FAILED: {e}'); sys.exit(1)

def get_df(sym):
    try:
        df = raw[sym].dropna(subset=['Close'])
        return df if len(df) >= 30 else None
    except: return None

def calc_rsi(s, p=14):
    d = s.diff()
    g = d.where(d>0,0).rolling(p).mean()
    l = (-d.where(d<0,0)).rolling(p).mean()
    return 100-(100/(1+g/(l+1e-10)))

def calc_atr(df, p=14):
    h,l,c = df['High'],df['Low'],df['Close']
    tr = pd.concat([h-l,abs(h-c.shift(1)),abs(l-c.shift(1))],axis=1).max(axis=1)
    return tr.rolling(p).mean()

def calc_adx(df, p=14):
    h,l,c = df['High'],df['Low'],df['Close']
    pdm = h.diff(); mdm = -l.diff()
    pdm = pdm.where((pdm>mdm)&(pdm>0),0)
    mdm = mdm.where((mdm>pdm)&(mdm>0),0)
    tr = pd.concat([h-l,abs(h-c.shift(1)),abs(l-c.shift(1))],axis=1).max(axis=1)
    atr = tr.rolling(p).mean()
    pdi = 100*pdm.rolling(p).mean()/(atr+1e-10)
    mdi = 100*mdm.rolling(p).mean()/(atr+1e-10)
    dx = 100*abs(pdi-mdi)/(pdi+mdi+1e-10)
    return dx.rolling(p).mean(), pdi, mdi

def scan(sym, df):
    sigs = []
    c = df['Close']; price = float(c.iloc[-1])
    atr = calc_atr(df); atr_v = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else None
    r14 = calc_rsi(c,14); r2 = calc_rsi(c,2)
    rn = float(r14.iloc[-1]) if not pd.isna(r14.iloc[-1]) else 50
    r2n = float(r2.iloc[-1]) if not pd.isna(r2.iloc[-1]) else 50
    adx_s,pdi,mdi = calc_adx(df)
    an = float(adx_s.iloc[-1]) if not pd.isna(adx_s.iloc[-1]) else None
    reg = 'unknown'
    if an:
        if an>=25: reg='trending'
        elif an<=20: reg='ranging'
        else: reg='transitional'
    e9=c.ewm(span=9).mean(); e21=c.ewm(span=21).mean(); e50=c.ewm(span=50).mean()
    e12=c.ewm(span=12).mean(); e26=c.ewm(span=26).mean()
    macd=e12-e26; ms=macd.ewm(span=9).mean(); mh=macd-ms
    bm=c.rolling(20).mean(); bs=c.rolling(20).std()
    bu=bm+2*bs; bl=bm-2*bs
    vol=df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))
    vsma=vol.rolling(20).mean()
    vr=float(vol.iloc[-1]/vsma.iloc[-1]) if vsma.iloc[-1]>0 else 1.0

    # RSI-2
    if r2n<5 and reg in ('ranging','transitional','unknown'):
        st=40 if r2n<2 else(35 if r2n<3 else 30)
        sigs.append(dict(strat='connors_rsi2',dir='BUY',reason='RSI-2=%.1f (oversold extreme)'%r2n,bs=st,br='ranging'))
    elif r2n>95 and reg in ('ranging','transitional','unknown'):
        st=40 if r2n>98 else(35 if r2n>97 else 30)
        sigs.append(dict(strat='connors_rsi2',dir='SELL',reason='RSI-2=%.1f (overbought extreme)'%r2n,bs=st,br='ranging'))

    # MACD
    if len(mh)>=3:
        m1=mh.iloc[-1]; m0=mh.iloc[-2]
        if m1>0 and m0<=0 and reg in ('trending','transitional','unknown'):
            st=35 if abs(m1)>1.5*abs(m0) else 30
            sigs.append(dict(strat='macd_momentum',dir='BUY',reason='MACD hist crossed positive (%.4f)'%m1,bs=st,br='trending'))
        elif m1<0 and m0>=0 and reg in ('trending','transitional','unknown'):
            st=35 if abs(m1)>1.5*abs(m0) else 30
            sigs.append(dict(strat='macd_momentum',dir='SELL',reason='MACD hist crossed negative (%.4f)'%m1,bs=st,br='trending'))

    # EMA Stack
    v9=float(e9.iloc[-1]); v21=float(e21.iloc[-1]); v50f=float(e50.iloc[-1])
    if v9>v21>v50f:
        gap=(v9-v50f)/price*100
        if gap>0.5 and reg in ('trending','transitional'):
            st=35 if gap>2 else 30
            sigs.append(dict(strat='ema_stack',dir='BUY',reason='EMA 9>21>50 bullish (gap=%.1f%%)'%gap,bs=st,br='trending'))
    elif v9<v21<v50f:
        gap=(v50f-v9)/price*100
        if gap>0.5 and reg in ('trending','transitional'):
            st=35 if gap>2 else 30
            sigs.append(dict(strat='ema_stack',dir='SELL',reason='EMA 9<21<50 bearish (gap=%.1f%%)'%gap,bs=st,br='trending'))

    # Bollinger
    if price<float(bl.iloc[-1]) and rn<35:
        sigs.append(dict(strat='bollinger_bounce',dir='BUY',reason='Price below lower BB + RSI=%.1f'%rn,bs=35,br='ranging'))
    elif price>float(bu.iloc[-1]) and rn>65:
        sigs.append(dict(strat='bollinger_bounce',dir='SELL',reason='Price above upper BB + RSI=%.1f'%rn,bs=35,br='ranging'))

    # RSI Divergence
    if len(c)>=10:
        if c.iloc[-1]<c.iloc[-5] and r14.iloc[-1]>r14.iloc[-5] and rn<40:
            sigs.append(dict(strat='rsi_divergence',dir='BUY',reason='Bullish RSI divergence (RSI=%.1f)'%rn,bs=35,br='ranging'))

    # VWAP Reversion
    if 'USD' in sym and '-' in sym:
        vwap=(c*vol).rolling(20).sum()/(vol.rolling(20).sum()+1e-10)
        if not pd.isna(vwap.iloc[-1]) and not pd.isna(bs.iloc[-1]):
            z=(price-float(vwap.iloc[-1]))/(float(bs.iloc[-1])+1e-10)
            if z<-2.0:
                st=40 if z<-3 else 35
                sigs.append(dict(strat='vwap_reversion',dir='BUY',reason='VWAP Z=%.2f (deeply oversold)'%z,bs=st,br='ranging'))

    # Supertrend
    if atr_v and atr_v>0:
        hl2=(df['High']+df['Low'])/2
        ust=hl2+3.0*atr
        try:
            if not pd.isna(ust.iloc[-2]) and price>float(ust.iloc[-2]):
                sigs.append(dict(strat='supertrend',dir='BUY',reason='Price broke above Supertrend (ATR*3)',bs=30,br='trending'))
        except: pass

    # TP/SL computation
    ic='-USD' in sym and '=' not in sym
    ifx='=X' in sym
    for s in sigs:
        if atr_v and atr_v>0:
            if ic: tm,sm=2.5,1.5
            elif ifx: tm,sm=2.0,1.0
            else: tm,sm=2.0,1.2
            if s['dir']=='BUY': tp=price+atr_v*tm; sl=price-atr_v*sm
            else: tp=price-atr_v*tm; sl=price+atr_v*sm
            mtd='ATR'
        else:
            if ic: tpp,slp=0.08,0.04
            elif ifx: tpp,slp=0.02,0.01
            else: tpp,slp=0.05,0.03
            if s['dir']=='BUY': tp=price*(1+tpp); sl=price*(1-slp)
            else: tp=price*(1-tpp); sl=price*(1+slp)
            mtd='static'
        td=abs(tp-price); sd=abs(sl-price)
        prob=sd/(td+sd)*100 if(td+sd)>0 else 50
        base=s['bs']
        vb=15 if vr>=2 else(10 if vr>=1.2 else(0 if vr<0.8 else 5))
        rb=15 if reg==s['br'] else(5 if reg in('transitional','unknown') else -5)
        conf=min(100,base+vb+rb)
        rr=td/sd if sd>0 else 0
        s.update(dict(symbol=sym,price=round(price,8),tp=round(tp,8),sl=round(sl,8),
                  tp_pct=round(td/price*100,2),sl_pct=round(sd/price*100,2),
                  rr_ratio=round(rr,2),probability=round(prob,1),confidence=conf,
                  regime=reg,adx=round(an,1) if an else None,
                  rsi14=round(rn,1),rsi2=round(r2n,1),vol_ratio=round(vr,2),method=mtd,
                  strategy=s['strat'],direction=s['dir']))
    return sigs

all_sigs = []
for sym in ALL:
    df = get_df(sym)
    if df is None: continue
    all_sigs.extend(scan(sym,df))

all_sigs.sort(key=lambda x:(x['confidence'],x['probability']),reverse=True)

print('='*80)
print('  LIVE TRADING SIGNALS -- %d signals found' % len(all_sigs))
print('='*80)
print()

top=[s for s in all_sigs if s['confidence']>=50 and s['rr_ratio']>=1.5]
if top:
    print('  HIGH CONFIDENCE PICKS (%d):' % len(top))
    print('  %-12s %-5s %12s %12s %12s %5s %4s %5s %12s %s' % ('Symbol','Dir','Price','TP','SL','R:R','Conf','Prob','Regime','Strategy'))
    print('  ' + '-'*100)
    for s in top:
        print('  %-12s %-5s %12.4f %12.4f %12.4f %5.2f %4d %5.1f %12s %s' % (s['symbol'],s['direction'],s['price'],s['tp'],s['sl'],s['rr_ratio'],s['confidence'],s['probability'],s['regime'],s['strategy']))
        print('    Reason: %s' % s['reason'])
        print('    RSI14=%s, RSI2=%s, Vol=%sx, ADX=%s, TP/SL=%s' % (s['rsi14'],s['rsi2'],s['vol_ratio'],s['adx'],s['method']))
        print()

med=[s for s in all_sigs if s['confidence']>=40 and s not in top]
if med:
    print('  MEDIUM CONFIDENCE (%d):' % len(med))
    for s in med:
        print('  %-12s %-5s @ %.4f  TP=%.4f  SL=%.4f  R:R=%.1f  Conf=%d  [%s] %s' % (s['symbol'],s['direction'],s['price'],s['tp'],s['sl'],s['rr_ratio'],s['confidence'],s['strategy'],s['reason']))

low=[s for s in all_sigs if s['confidence']<40]
if low:
    print('  LOW CONFIDENCE (%d signals suppressed)' % len(low))

output = dict(
    scan_time=datetime.now(timezone.utc).isoformat(),
    total_signals=len(all_sigs),
    high_confidence=len(top),
    medium_confidence=len(med),
    signals=all_sigs
)
outpath='e:/findtorontoevents_antigravity.ca/alpha_engine/data/live_scan_now.json'
with open(outpath,'w') as f:
    json.dump(output,f,indent=2)
print()
print('Saved to %s' % outpath)
