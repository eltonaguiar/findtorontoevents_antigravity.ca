# Recommended Columns for a Crypto/Stock Prediction System

| Column | Description |
|--------|-------------|
| **Symbol** | Ticker symbol of the asset (e.g., BTCUSD, AAPL) |
| **AssetClass** | Type of asset (Crypto, Equity, ETF, Futures, Bond, Commodity) |
| **Direction** | Predicted direction (Long/Short/Neutral) |
| **DirectionReason** | Brief rationale for the direction prediction |
| **System** | Name or ID of the prediction system/model used |
| **Strategy** | Specific strategy or algorithm identifier |
| **EntryPrice** | Suggested entry price for the trade |
| **TargetPrice** | Predicted price target (TP) |
| **StopLoss** | Predicted stop‑loss price (SL) |
| **LivePrice** | Current market price at the time of recommendation |
| **PnLPercent** | Current profit/loss percentage if the trade is live |
| **RiskRewardRatio** | Expected risk‑to‑reward ratio (R:R) |
| **Score** | Overall confidence score (numeric) |
| **Grade** | Qualitative grade (A‑F) based on score |
| **TrustScore** | Trustworthiness rating (0‑10) |
| **MetaWinProb** | Model‑estimated probability of win |
| **MetaGrade** | Meta‑grade derived from win probability |
| **ScoreBreakdown** | Human‑readable explanation of the score components |
| **Confidence** | Confidence level (High/Medium/Low) |
| **TrustTier** | Tiered trust level (e.g., Tier 1, Tier 2) |
| **TrustReason** | Reason for assigned trust tier |
| **ForwardWR** | Forward win‑rate based on back‑testing |
| **ForwardTrades** | Number of forward trades used for validation |
| **ForwardValidated** | Boolean indicating if forward validation passed |
| **ConfluenceCount** | Number of overlapping signals supporting the pick |
| **ConsensusSystemReasons** | Reasons from consensus among multiple systems |
| **EntryReasonRaw** | Raw entry rationale text |
| **EntryReasonFullAudit** | Full audit‑ready entry justification |
| **MarketRegime** | Current market regime (e.g., Trending, Ranging) |
| **RegimeSentinel** | Indicator of regime change detection |
| **RegimeAdjustment** | Any adjustments made due to regime shift |
| **StrategyDescription** | Detailed description of the strategy logic |
| **SystemDescription** | Description of the underlying system/model |
| **Status** | Current status (Active, Closed, Pending) |
| **Timeframe** | Timeframe for the prediction (e.g., 1h, 4h, Daily) |
| **AgeHours** | Age of the pick in hours |
| **PickedAt** | Timestamp when the pick was generated |
| **DupStatus** | Duplicate detection status |
| **CollapsedStrategies** | Merged/aggregated strategies for the pick |
| **Volume** | Average daily volume of the asset (helps filter high‑liquidity picks) |
| **LiquidityScore** | Score indicating ease of execution based on volume and spread |
| **Volatility** | Recent price volatility (e.g., 30‑day ATR) |
| **MarketCap** | Market capitalization (for equities/crypto) |
| **Exchange** | Primary exchange or venue where the asset trades |
| **SectorIndustry** | Sector/industry classification (for equities) |
| **SentimentScore** | Sentiment metric from news/social data |
| **FundamentalScore** | Fundamental health score (e.g., earnings, revenue) |
| **TechnicalIndicators** | List or JSON of key technical indicator values |
| **RiskLimit** | Position size limit based on risk management rules |
| **ExecutionSignal** | Signal indicating if the trade should be executed now |
| **Notes** | Free‑form notes for analysts |
