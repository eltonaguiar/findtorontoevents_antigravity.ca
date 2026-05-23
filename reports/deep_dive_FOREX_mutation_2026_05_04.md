======================================================================
1. STRATEGIES THAT FLIP WR BY DIRECTION (same strategy)
======================================================================

  ig_contrarian_sentiment:
    SHORT   :  57.1% WR |   42 trades | avg +0.00%
    LONG    :  20.9% WR |  110 trades | avg -0.00%
    SPREAD: 36pp  -> consider LONG-only / SHORT-only mutation

  myfxbook_retail_contrarian:
    SHORT   :  46.2% WR |   13 trades | avg -0.00%
    LONG    :  10.5% WR |   86 trades | avg -0.01%
    SPREAD: 36pp  -> consider LONG-only / SHORT-only mutation

  cta_cross_asset_tsmom:
    SHORT   :  60.0% WR |   55 trades | avg +0.00%
    LONG    :  35.3% WR |   51 trades | avg -0.00%
    SPREAD: 25pp  -> consider LONG-only / SHORT-only mutation

  forex_rsi2_mean_reversion:
    SHORT   :  27.3% WR |   11 trades | avg -0.00%
    LONG    :   2.7% WR |   73 trades | avg -0.00%
    SPREAD: 25pp  -> consider LONG-only / SHORT-only mutation

======================================================================
2. STRATEGIES THAT FLIP WR BY TIMEFRAME
======================================================================

======================================================================
3. SYSTEMS WITH HIGH SYMBOL VARIANCE (winner vs loser symbols)
======================================================================

  multi_asset_copytrader (WR spread: 100pp across symbols with >=8 trades each):
    USDCHF=X      : 100.0% WR |   8 trades | avg +0.01%
    AUDUSD=X      :  83.3% WR |  12 trades | avg +0.01%
    CT=F          :  64.2% WR |  53 trades | avg +0.02%
    EURGBP=X      :  61.9% WR |  21 trades | avg +0.00%
    RIOT          :  58.3% WR |  12 trades | avg +0.02%
    GBPUSD=X      :  50.0% WR |  20 trades | avg +0.00%
    WORST: AMD (0%), ZW=F (0%), EURJPY=X (2%)  -> consider symbol-allowlist mutation (SANDBOX)

  quan_engine (WR spread: 51pp across symbols with >=8 trades each):
    XRPUSDT       :  51.0% WR |  51 trades | avg -0.02%
    TRXUSDT       :  49.4% WR | 245 trades | avg -0.02%
    BNBUSDT       :  46.3% WR |  67 trades | avg -0.04%
    ETCUSDT       :  45.0% WR | 211 trades | avg -0.05%
    DOGEUSDT      :  43.8% WR | 130 trades | avg -0.10%
    HYPEUSDT      :  41.6% WR | 553 trades | avg -0.22%
    WORST: MATICUSDT (0%), ONDOUSDT (22%), SOLUSDT (23%)  -> consider symbol-allowlist mutation (SANDBOX)

  rapid_fire (WR spread: 89pp across symbols with >=8 trades each):
    ENJUSDT       :  88.9% WR |   9 trades | avg +0.03%
    TAOUSDT       :   5.6% WR |  18 trades | avg -0.57%
    UUSDT         :   0.0% WR |  34 trades | avg -0.17%
    WORST: UUSDT (0%), TAOUSDT (6%), ENJUSDT (89%)  -> consider symbol-allowlist mutation (SANDBOX)

======================================================================
NEXT: See docs/MUTATION_THREE_AXIS_PROTOCOL.md (mutation quality, allowlist rules)
======================================================================
