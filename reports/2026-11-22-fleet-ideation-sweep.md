# Fleet ideation sweep — 2026-11-22

26 models were reachable across three engines on two hosts; 10 were asked for novel per-asset-class hypotheses under a pre-registration regime, and 6 answered usefully. The already-explored list handed to every model was the 87 registry families, so restatements were cheap to spot.

## Fleet as found

| host | engine | models | state |
|---|---|---|---|
| 192.168.2.32 | LM Studio :1234 | 11 | `gpt-oss-20b` loaded; 10 cold |
| 192.168.2.32 (Windows) | Ollama :11434 | ~70 | nothing preloaded, all cold-load |
| 127.0.0.1 (Linux) | Ollama :11434 | 27 | nothing preloaded |
| — | vLLM :8000 | 0 | not running |

**Retired server-side** (HTTP 410, all pointing at `glm-5.3-flash:cloud`): `deepseek-v3.1:671b-cloud`, `kimi-k2.5:cloud`, `kimi-k2-thinking:cloud`, `cogito-2.1:671b-cloud`, `minimax-m2:cloud`, `glm-4.6:cloud`, `qwen3-coder-next:cloud`. Live cloud tags: `glm-5.3-flash:cloud`, `gpt-oss:120b-cloud`, `gemma4:31b-cloud`, `minimax-m3:cloud`.

## What answered

| model | host | reply chars | ideas | judgement |
|---|---|---|---|---|
| gemma4:31b-cloud | ollama @ Linux, cloud tag | 10347 | 18 | best of the run — 18 ideas, concrete formulas, real economic priors |
| gpt-oss:120b-cloud | ollama @ Windows, cloud tag | 9012 | 13 | good ideas, but hit the token cap mid-JSON so only the first records survive |
| gemma3:12b | ollama @ Linux, local | 7659 | 10 | solid, several data-blocked but two genuinely new |
| llama3.1:8b | ollama @ Windows, local | 8164 | 13 | generic restatements and non-signals ("transportation costs") |
| llama-3.1-8b-lexi | LM Studio @ Windows | 5851 | 10 | pure template — every idea is "X with high Y is more likely to reverse" |

Models returning nothing usable: `minimax-m3:cloud` and `glm-5.3-flash:cloud` (reasoning consumed the whole budget at 2600 and 4000 tokens), `gpt-oss-20b` (same, three attempts), `qwen3:32b` and `deepseek-r1:32b` (cold-load timeout at 420s on a 20 GB model).

## Every idea, judged against the family list

| class | name | model | judgement | why |
|---|---|---|---|---|
| CRYPTO | Funding-Basis Divergence Mean Reversion | gemma4:31b-cloud | runner-up | adjacent to the killed H-035 (funding magnitude) but the funding-vs-basis divergence is a diffe |
| CRYPTO | Stablecoin-to-MarketCap Ratio Mean Reversion | gemma4:31b-cloud | blocked | needs stablecoin supply (DefiLlama); not in our data |
| CRYPTO | Exchange-Specific Funding Arbitrage Decay | gemma4:31b-cloud | runner-up | Binance vs Bybit funding dispersion; feasible from the funding archive |
| EQUITY | Shares Outstanding Dilution Fade | gemma4:31b-cloud | **PICK** | financing-side signal, data already cached from the H-150 run, classic economic prior |
| EQUITY | Quarterly Fact-to-Price Lag | gemma4:31b-cloud | duplicate | this is the equity_pead sidecar (H-002), already registered and harness-untested |
| EQUITY | Institutional Ownership Concentration Revers | gemma4:31b-cloud | blocked | needs 13F parsing; not in our data |
| ETF | Issuer Holdings Drift | gemma4:31b-cloud | blocked | needs issuer holdings files; not downloaded |
| ETF | Cross-ETF Factor Divergence | gemma4:31b-cloud | candidate | only needs ETF prices we already fetch |
| ETF | Holdings Concentration Spike | gemma4:31b-cloud | blocked | needs issuer holdings files |
| COMMODITY | EIA Inventory-Price Divergence | gemma4:31b-cloud | caution | EIA already burned the desk once (H-004 stale-signal artifact, H-036) |
| COMMODITY | COT Non-Commercial Extreme Reversal | gemma4:31b-cloud | caution | CFTC already produced a look-ahead kill in H-001; any COT test must prove publication lag first |
| COMMODITY | Cross-Commodity Relative Strength (Energy) | gemma4:31b-cloud | candidate | prices in hand, low data risk |
| FX | FRED Real Rate Differential Momentum | gemma4:31b-cloud | candidate | fredgraph.csv is key-free |
| FX | Credit Spread-Currency Correlation | gemma4:31b-cloud | candidate | FRED + FX prices in hand |
| FX | Calendar-Based FX Carry Mean Reversion | gemma4:31b-cloud | candidate | end-of-quarter reversal, clean calendar effect, no positioning data needed |
| BOND | Term Premium Compression Fade | gemma4:31b-cloud | candidate | FRED DGS10/DGS2 in hand |
| BOND | Inflation-Expectation Gap | gemma4:31b-cloud | candidate | FRED TIPS series in hand |
| BOND | FRED Credit Impulse Lead | gemma4:31b-cloud | candidate | FRED in hand; the credit-impulse construction needs care |
| CRYPTO | FundingRateExtremeReversal | gpt-oss:120b-cloud | unclassified | not judged against the family list |
| CRYPTO | BTC_ETH_FundingSpreadRotation | gpt-oss:120b-cloud | unclassified | not judged against the family list |
| CRYPTO | COT_Futures_Funding_Crowding | gpt-oss:120b-cloud | unclassified | not judged against the family list |
| EQUITY | QuarterlyShareIssuanceDilution | gpt-oss:120b-cloud | unclassified | not judged against the family list |
| EQUITY | ETFRebalancingLagSignal | gpt-oss:120b-cloud | unclassified | not judged against the family list |
| EQUITY | COT_RetailLongOverextension | gpt-oss:120b-cloud | unclassified | not judged against the family list |
| ETF | CreationRedemptionFlowLag | gpt-oss:120b-cloud | unclassified | not judged against the family list |
| ETF | SectorETFMacroSpreadRotation | gpt-oss:120b-cloud | unclassified | not judged against the family list |
| ETF | DiscountMeanReversion | gpt-oss:120b-cloud | unclassified | not judged against the family list |
| COMMODITY | EIA_InventorySurpriseDrawdown | gpt-oss:120b-cloud | unclassified | not judged against the family list |
| COMMODITY | FuturesBasisBackwardationBias | gpt-oss:120b-cloud | unclassified | not judged against the family list |
| COMMODITY | COT_CommercialNetShortReversal | gpt-oss:120b-cloud | unclassified | not judged against the family list |
| FX | RetailCOT_EURUSD_Overlong | gpt-oss:120b-cloud | unclassified | not judged against the family list |
| CRYPTO | DeFi Protocol Liquidation Pressure Reversal | gemma3:12b | blocked | needs liquidation event feed |
| CRYPTO | Exchange Reserve Drawdown & Flow | gemma3:12b | blocked | on-chain, paid |
| CRYPTO | Polymarket/Kalshi Futures Convergence | gemma3:12b | candidate | both APIs are public and free |
| EQUITY | Insider Open Market Buys & Retail Sentiment  | gemma3:12b | unclassified | not judged against the family list |
| EQUITY | FRED Data & Small Cap Profitability | gemma3:12b | candidate | FRED + prices in hand |
| EQUITY | Company Fact Data & Sector Breadth | gemma3:12b | candidate | companyfacts in hand |
| ETF | ETF Issuer Holdings & Underlying Asset Flows | gemma3:12b | blocked | needs issuer holdings files |
| FX | CFTC Commitments & London Open Reversal | gemma3:12b | caution | COT + intraday FX; see COT caution |
| BOND | EIA Inventories & Treasury Yield Curve | gemma3:12b | caution | cross-asset EIA -> curve link is a stretch |
| BOND | Kalshi Bond Futures & Rate Expectations | gemma3:12b | candidate | Kalshi public API |
| CRYPTO | Leverage Ratio Convergence | llama3.1:8b | noise | not a testable signal -- no instrument definition |
| CRYPTO | Overnight Funding Risk | llama3.1:8b | noise | confuses exchanges with assets |
| CRYPTO | Liquidity Provider Competition | llama3.1:8b | noise | not measurable from the named data |
| EQUITY | Insider Activity Correlation | llama3.1:8b | blocked | needs Form 4 feed |
| EQUITY | Earnings Momentum | llama3.1:8b | duplicate | post-earnings drift, already H-002 |
| EQUITY | Sector Rotation Timing | llama3.1:8b | duplicate | sector rotation family already in registry |
| ETF | Issuer Holdings Concentration | llama3.1:8b | blocked | needs issuer holdings files |
| ETF | Net Flow Timing | llama3.1:8b | blocked | ETF flow data not in hand |
| COMMODITY | Inventory-to-Production Ratio | llama3.1:8b | cautious | needs production data beyond EIA stocks |
| COMMODITY | Transportation Costs | llama3.1:8b | noise | not a signal |
| FX | Central Bank Intervention | llama3.1:8b | noise | no free intervention dataset |
| FX | Positioning Imbalance | llama3.1:8b | duplicate | COT positioning, see caution above |
| BOND | Term Structure Slope | llama3.1:8b | candidate | FRED curve |
| CRYPTO | Crypto Whale Dislocation | llama-3.1-8b-lexi | noise | no free whale/forced-seller feed; untestable as stated |
| CRYPTO | Crypto Cross-Sectional Momentum Reversal | llama-3.1-8b-lexi | duplicate | momentum family |
| CRYPTO | Crypto Flow Dislocation | llama-3.1-8b-lexi | blocked | on-chain flow data is paid (H-015 already blocked on CryptoQuant) |
| EQUITY | Equity Sector Breadth Exhaustion | llama-3.1-8b-lexi | noise | breadth definition not operationalised |
| EQUITY | Equity Positioning Extreme | llama-3.1-8b-lexi | blocked | needs positioning data |
| EQUITY | Equity Cross-Sectional Momentum Reversal | llama-3.1-8b-lexi | duplicate | momentum family |
| ETF | ETF Dual Momentum | llama-3.1-8b-lexi | duplicate | momentum family |
| COMMODITY | Commodity Roll Yield Reversal | llama-3.1-8b-lexi | blocked | needs continuous futures term structure |
| FX | FX Time Series Momentum Reversal | llama-3.1-8b-lexi | duplicate | momentum family |
| BOND | Bond Yield Curve Steepener Reversal | llama-3.1-8b-lexi | candidate | FRED curve |

## The pick: net share issuance (EQUITY)

**H-151 — Net Share Issuance (EQUITY).** 12-month change in shares outstanding from SEC EDGAR `companyfacts` predicts cross-sectional equity returns: heavy issuers underperform, net repurchasers outperform, 1-month hold after a 45-day filing lag.

Why this one out of 51 ideas:

- **The data is already on disk.** The H-150 backtest cached `companyfacts` for 2,600 CIKs and prices for 584 of them. Marginal cost of the first test is a script, not a data acquisition project.
- **The economic prior is real and old.** Managers issue when they think equity is rich and buy back when it is cheap; the demand curve for shares slopes down, so supply pressure moves price. Pontiff & Woodgate (2008) is the canonical reference. It is the financing-side quantity, not the investment-side one that H-149/H-150 already tested.
- **It is orthogonal to what just failed.** Gross profitability is an investment/cash-flow signal; issuance is a financing signal. If H-151 works it is not because H-150 was right.
- **The traps are known and can be frozen in advance**, which is the whole point of pre-registration: stock splits masquerade as 2x/3x issuance, filing dates are not period ends, and multi-class filers double-count.

Runner-ups, in order: crypto funding-vs-basis divergence (needs only the spot/futures join we have), end-of-quarter FX carry reversal (pure calendar effect), FRED credit impulse. Everything requiring 13F, issuer holdings files, on-chain flows, or Form 4 was ruled out on data grounds, not on merit.

## Practical fleet notes

- Reasoning models need a token budget of 2,500+ or they return `content: ""` with `finish_reason: length`. This cost four calls before it was diagnosed.
- Cold-loading a 20-32 GB model takes longer than a 420 s timeout on this hardware; the same model answers in 2 s once warm. `GET /api/ps` tells you what is loaded before you spend the timeout.
- One host cannot serve three large models in parallel without thrashing; the client caps parallel work but the GPU still serialises, so fan-out belongs across hosts, not within one.
- Cloud tags answer in 2-12 s and produced the best ideas of the run. Use them for ideation; keep local models for anything that must not leave the LAN.

## Prior art found after the pick

`reports/hypothesis_registry.json` contains no issuance or dilution hypothesis, but a scan of the wider `reports/` tree found proposal ET-1 (`reports/new_strategy_proposals_2026_05_18.md`, line 3460): ETF shares outstanding as an Authorized-Participant creation/redemption flow signal. Same data field, different mechanism — ETF units are arbitrage flow on a basket, company shares are managerial timing on an issuer. H-151 records this as prior art and does not cover ETFs.

Two models converged on the same idea independently (`gemma4:31b-cloud` and `gpt-oss:120b-cloud` as `QuarterlyShareIssuanceDilution`), which is mild evidence that it is an obvious-in-hindsight anomaly rather than a novel one. That cuts both ways: it is more likely to have been arbitraged away, and it is easier to defend the specification against charges of data mining.
