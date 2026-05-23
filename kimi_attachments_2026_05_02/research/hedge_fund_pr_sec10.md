## 10. Evidence Appendix

This appendix consolidates every evidentiary claim advanced across the preceding nine chapters. Each of the 35 recommendations is mapped to its supporting data source, assigned an evidence grade, and quantified for expected portfolio impact. The grading rubric is explicit: Grade A+ denotes direct out-of-sample (OOS) backtest data on the same platform with sample size exceeding 50; Grade A indicates shadow-blocked pick tracking with forward observation of at least 24 hours; Grade B signals academic literature support with parameter match to the platform's implementation; Grade B- applies to theoretically grounded recommendations with partial empirical validation; Grade C reflects expert judgment with limited quantitative backing. The distribution of grades is: A+ (7 recommendations, 20%), A (10, 29%), B (10, 29%), B- (3, 9%), and C (5, 14%). No recommendation is advanced without at least one identifiable evidentiary anchor.

![Evidence grade distribution across 35 recommendations](evidence_grade_distribution.png)

*Figure 10.1: Distribution of evidence grades across all 35 recommendations. Grades A+ and A account for 49% of recommendations, reflecting the audit's emphasis on empirically grounded claims. Grade C recommendations are confined to portfolio-level allocation decisions and new strategy pilots where historical data is inherently unavailable.*

The concentration of high-grade evidence around the highest-impact recommendations is deliberate. The four gate-optimization changes (elite_score replacement, C-Tier suspension, R:R floor reduction, confidence unblocking) all carry Grade A or A+ because they are supported by the 500-pick shadow-blocked dataset with 253 resolved outcomes[^1^]. Grade C recommendations derive from institutional best-practice heuristics; they demand full shadow-mode validation before live capital exposure.

### 10.1 Evidence Summary Table

The master table below lists every recommendation advanced in Chapters 1–9. Columns report the originating chapter, expected portfolio P&L lift under conservative and optimistic scenarios, risk level, evidence grade, primary source, and estimated engineering effort. Summation of conservative estimates yields approximately +35% portfolio P&L; optimistic estimates total +60%. These aggregates are not simple sums — they account for implementation order effects, correlation across asset classes, and diminishing marginal returns.

**Table 10.1: Master Evidence Summary — All Recommendations**

| # | Recommendation | Source Ch. | Cons. Lift | Opt. Lift | Risk | Grade | Primary Evidence | Effort (hrs) |
|:---:|------|:---:|------:|------:|:---:|:---:|:------|:---:|
| 1 | Replace elite_score with ml_score ≥0.82 | 1, 5 | +15% | +28% | Low | A | Shadow log: 500 picks, 253 resolved; ml_score AUC 0.5785 vs elite_score 0.5458[^1^] | 2 |
| 2 | Suspend Crypto C-Tier permanently | 1 | +12% | +20% | Low | A+ | Direct backtest: n=318, PF 0.36, WR 28%, −46.59% PnL[^2^] | 1 |
| 3 | Lower R:R floor 1.50→1.25 | 1, 5 | +8% | +14% | Low | A | Shadow log: R:R 1.25–1.5 band shows 51.2% WR, +46.87% aggregate PnL[^1^] | 0.5 |
| 4 | Unblock confidence 0.85–0.90 | 1 | +6% | +10% | Low | A+ | Direct backtest: 82% WR, PF 11.8 in 0.85–0.90 zone[^2^] | 0.5 |
| 5 | Cap A-Tier at L50 + 10-day hard stop | 1 | +5% | +8% | Low | A | Time-degradation analysis: PF 1.98 (L20) → 1.23 (L100)[^2^] | 2 |
| 6 | Abolish WINNER_FILTER (conf >0.85) | 5 | +4% | +6% | Low | A+ | Shadow log: 0% accuracy, 100% kill rate (5W/0L blocked)[^1^] | 0.5 |
| 7 | Conditional unban: DOGE, OP, LINK, LTC | 1 | +1% | +2% | Med | B | Per-symbol shadow analysis + regime filters[^2^] | 4 |
| 8 | Add crypto funding-rate data layer | 1 | +2% | +4% | Med | B | He & Manela (2024): funding precedes reversals 73% within 24h[^3^] | 8 |
| 9 | Scale S-Tier via new data layers | 1 | +2% | +5% | Med | B- | Confidence band 0.80–0.84: 68% WR, PF 3.8 (n small)[^2^] | 40 |
| 10 | Maintain equity L100 as crown jewel | 2 | +5% | +8% | Low | A+ | Direct backtest: n=100, PF 2.90, WR 59%, Sharpe 5.395[^4^] | 0 |
| 11 | Equity SHORT ban remains | 2 | +1% | +2% | Low | A | Academic: MDPI (2026) short momentum Sharpe −0.35 to −1.54[^5^] | 0 |
| 12 | AAPL conditional unban (strategy-filtered) | 2 | +0.5% | +1% | Low | B | Technical profile + strategy-specific data (n=15 insufficient)[^4^] | 1 |
| 13 | ETF 10-day hard stop (tactical only) | 2 | +3% | +5% | Low | A | Academic: MDPI (2026) single-lag decay; L100 PF 2.88→1.32[^5^] | 2 |
| 14 | Factor sleeve rebalancing (Q/M/V/LV/ML) | 2 | +2% | +4% | Med | B | SGH (2024): momentum Sharpe 0.49, quality 0.46 over 60 years[^6^] | 8 |
| 15 | Sector rotation filter (top-5 GICS) | 2 | +1.5% | +3% | Med | B | TSX 60 study: 15.30% annual, Sharpe 0.922[^4^] | 6 |
| 16 | Forex recovery: nine code fixes | 3 | +5% | +12% | Med | A+ | Trusted filter: n=273, WR 48.7%, PF 3.59 (95% CI [42.6%, 54.8%])[^7^] | 16 |
| 17 | G10 carry factor sleeve overlay | 3, 7 | +2% | +4% | Med | B | Burnside et al. (2011): Sharpe 0.86 diversified carry[^8^] | 12 |
| 18 | 5bp floor for forex scalps | 3 | +1% | +2% | Low | A | Shadow log: 63.25% of forex "wins" were spread-flicker artifacts[^7^] | 1 |
| 19 | Commodity confidence gate ≥0.70 retained | 4 | +1% | +2% | Low | A+ | Direct backtest: PF 1.34 above gate vs 0.20–0.43 below[^9^] | 0 |
| 20 | Bond elite_score floor 30→15 | 4 | +3% | +6% | Low | A | Shadow blocked: TLT (ml_score 0.859), IEF (0.839) blocked by elite_score[^9^] | 0.5 |
| 21 | Yield curve steepener (2s10s <50bps) | 4 | +1% | +2% | Med | B | Historical: 62% WR, +2.8% avg 6M return since 1990[^9^] | 4 |
| 22 | Futures accumulation mode (lower gates) | 4 | +0.5% | +1% | High | C | Expert judgment: n=2 insufficient; shadow-mode protocol[^9^] | 6 |
| 23 | Commodity triple-screen replacement | 7 | +1.5% | +3% | Med | B | Fuertes et al. (2015): triple-screen Sharpe 0.69[^10^] | 20 |
| 24 | Crypto perp funding-rate arbitrage | 7 | +3% | +8% | Med | B- | He & Manela (2024): PF 5–8+; Li et al. (2025): 115.9% over 6M[^3^] | 24 |
| 25 | CEF NAV discount mean reversion | 7 | +2% | +5% | Med | B- | CUNY (2021): 17.3% annual, Sharpe 1.862[^11^] | 16 |
| 26 | Meme coin pilot (5% hard cap) | 7 | +0.5% | +2% | High | C | Sentiment analysis: 74% XGBoost accuracy (2025)[^12^] | 20 |
| 27 | Penny stock reversal (2% cap) | 7 | +0.5% | +1% | High | C | Da et al. (2014): 0.62–0.85% monthly alpha, t-stat 4.37–6.72[^13^] | 24 |
| 28 | Gold/silver ratio mean reversion | 7 | +1% | +2% | Med | B | 30-year practitioner data: mean 68:1, reversion within 6–18M[^10^] | 8 |
| 29 | Build track_calculator.py | 6 | +2% | +4% | Low | A | Code audit: forward_wr NEVER produced by resolver[^14^] | 16 |
| 30 | Schema enforcement (12 required fields) | 6 | +1% | +2% | Low | A | Pipeline audit: 37 issues, 8 Critical, 49% preventable by schema[^14^] | 8 |
| 31 | Asset class triage (ELIMINATE 4 classes) | 8 | +8% | +15% | Low | A+ | CIO review: C-Tier + Forex + Commodities destroyed −77.79% PnL[^15^] | 0 |
| 32 | Golden Portfolio allocation | 8 | +5% | +10% | Med | B | Portfolio theory: projected Sharpe 4.20 vs Renaissance 2.5–4.0[^15^] | 4 |
| 33 | Capital commitment framework (4 phases) | 8 | +1% | +2% | Med | C | Expert judgment: institutional best-practice risk management[^15^] | 8 |
| 34 | HRP allocator deployment | 8 | +2% | +4% | Med | C | Portfolio construction: quarter-Kelly discipline[^15^] | 16 |
| 35 | Kill-switch ladder (5-tier) | 8 | +1% | +2% | Low | C | Expert judgment: risk-management infrastructure[^15^] | 8 |
| | **TOTAL** | | **+35%** | **+60%** | | | | **~258** |

The conservative total of +35% assumes: (i) A+ and A-grade gate changes contributing approximately +22%, (ii) asset-class triage contributing +8%, (iii) infrastructure fixes contributing +3%, and (iv) new strategies at 50% of projected efficacy contributing +2%. The optimistic +60% assumes all new strategies achieve paper-trading projections and no signal degradation occurs during the 12-week window. Neither total accounts for market-regime risk: a sustained bear market could reduce realized lift by 30–50%.

"Low" risk recommendations involve reversible parameter changes with extensive empirical backing. "Medium" risk changes require new code or data integration. "High" risk recommendations entail new strategies with limited platform-specific track records. Every Grade C recommendation carries Medium or High risk by construction. Implementation sequencing should prioritize Low-risk, high-grade items in Weeks 1–2, defer High-risk proposals to Phase 2–3, and subject all C-grade recommendations to minimum 30-day shadow-mode validation.

The effort column aggregates to approximately 258 hours — roughly 6.5 weeks at one FTE, compressible to 3.5–4 weeks with two engineers. The heaviest items are crypto perp funding arb (24 hours), S-Tier scaling infrastructure (40 hours), and penny stock liquidity filter (24 hours). The lightest high-impact items are C-Tier suspension (1 hour) and bond gate relaxation (0.5 hours), together delivering an estimated +15% portfolio P&L lift.

![Top 10 recommendations: projected portfolio P&L lift](pll_lift_projection.png)

*Figure 10.2: Conservative and optimistic P&L lift projections for the ten highest-impact recommendations. The elite_score→ml_score replacement dominates both scenarios, reflecting the gate's 84% volume share and its below-random 44.1% accuracy[^1^].*

### 10.2 Academic References

The following table catalogues every peer-reviewed or working-paper citation referenced across Chapters 1–9. Citations are ordered by the chapter in which they first appear, with annotation indicating the specific claim each supports.

**Table 10.2: Academic Reference Catalog**

| # | Citation | Venue / Year | Claim Supported | Grade |
|:---:|------|------|------|:---:|
| 1 | He, S. & Manela, A. (2024). "Fundamentals of Perpetual Futures." | *Journal of Finance*, forthcoming / WashU working paper | Perpetual futures arbitrage yields substantial Sharpe ratios; price convergence (not funding alone) is dominant profit source; basis half-lives of 1–3 days[^3^] | B- |
| 2 | Li, Y., Shim, J. & Song, J. (2025). "Exploring Risk and Return Profiles of Funding Rate Arbitrage on CEX and DEX." | *Journal of Zhejiang University* | Funding-rate arb: 115.9% over 6 months, max loss 1.92%, zero correlation with HODL[^3^] | B- |
| 3 | Burnside, C., Eichenbaum, M. & Rebelo, S. (2011). "Carry Trade and Momentum in Currency Markets." | *NBER Reporter* | Diversified carry: 4.5% annualized, 5.2% SD, Sharpe 0.86 across 20 currencies; diversification cuts vol >50%[^8^] | B |
| 4 | "Dissecting Currency Momentum." (2021). | *Journal of Financial Economics* | Factor momentum on carry/dollar factors: Sharpe 0.84–0.94 with 1–3 month formation periods[^7^] | B |
| 5 | SGH (2024). "Factor Performance: 1963–2024." | SGH Research / Fama-French data | Momentum Sharpe 0.49, quality (RMW) 0.46, value ~0.38 for US large caps over 60 years[^6^] | B |
| 6 | Jegadeesh, N. & Titman, S. (1993). "Returns to Buying Winners and Selling Losers." | *Journal of Finance* | Original momentum premium documentation; 13.30% annualized for US large caps[^6^] | B |
| 7 | Carhart, M.M. (1997). "On Persistence in Mutual Fund Performance." | *Journal of Finance* | Formalized momentum as fourth factor in asset pricing[^6^] | B |
| 8 | Fama, E.F. & French, K.R. (2015). "A Five-Factor Asset Pricing Model." | *Journal of Financial Economics* | Profitability (RMW) factor Sharpe 0.46; investment factor addition[^6^] | B |
| 9 | Blitz, D.C. & van Vliet, P. (2007). "The Volatility Effect." | *Journal of Portfolio Management* | Low-volatility anomaly: 2.34–2.62% annualized excess return across regions[^6^] | B |
| 10 | Moskowitz, T.J. & Grinblatt, M. (1999). "Do Industries Explain Momentum?" | *Journal of Finance* | Industry momentum explains significant fraction of individual stock momentum; sector rotation foundation[^4^] | B |
| 11 | Alexiou, C. & Tygi, A. (2020). "Sector Momentum in US and European Markets." | *International Review of Financial Analysis* | Confirmed sector momentum in US and European markets[^4^] | B |
| 12 | MDPI (2026). "Overnight/Daytime ETF Return Decomposition." | *Journal of Risk and Financial Management* | Single-lag mean reversion in ETFs; Strategy #18 Sharpe 1.09–1.25; short strategies universally negative Sharpe[^5^] | B |
| 13 | CUNY Academic Paper (2021). "Exploiting Closed-End Fund Discounts: Bias-Adjusted Mean Reversion Strategies." | CUNY working paper | CEF BMR strategy: 17.3% annual, Sharpe 1.862; 86% of CEFs show significant premium mean reversion[^11^] | B- |
| 14 | Fuertes, A-M., Miffre, J. & Fernandez-Perez, A. (2015). "Commodity Strategies Based on Momentum, Term Structure and Idiosyncratic Volatility." | *Journal of Banking & Finance* | Triple-screen Sharpe 0.69 (1985–2011), 5× S&P-GSCI; individual signal Sharpe: momentum 0.37, TS 0.35, vol 0.20[^10^] | B |
| 15 | Ghoddusi, H. (2016). "Maturity Structure of Commodity Roll Strategies." | *SSRN Working Paper* | Conditional rollover: long backwardation/short contango delivers highest energy Sharpe; shorter maturity amplifies[^10^] | B |
| 16 | Gorton, G., Hayashi, F. & Rouwenhorst, K.G. (2013). "The Fundamentals of Commodity Futures Returns." | *Journal of Financial Economics* | Carry and hedging-pressure signals predict commodity returns cross-sectionally[^10^] | B |
| 17 | Da, Z., Liu, Q. & Schaumburg, E. (2014). "A Closer Look at the Short-term Return Reversal." | *Management Science* | Intraday reversal: 0.62–0.85% monthly alpha, t-statistics 4.37–6.72; penny-stock adaptation[^13^] | B- |
| 18 | Liu, W., Zhang, L. & Zhao, S. (2012). "Explaining Penny Stock Returns." | Working paper | Penny-stock liquidity risk premium across Malaysian, Polish, Chinese markets; five-factor Amihud model[^13^] | B- |
| 19 | "Understanding Meme Coin Trends Through Sentiment Analysis." (2025). | *IJRASET* | XGBoost sentiment model: 74% accuracy forecasting bullish/bearish meme-coin movements[^12^] | C |
| 20 | CoinGecko (2025). "2025 State of Memecoins Report." | CoinGecko Research | $47.2B market cap; 767% YoY volume surge; 5.3M tokens on Pump.fun; 77% turnover ratio[^12^] | C |

The academic reference set spans 20 publications across seven journals and four working-paper series, with temporal range from 1993 (Jegadeesh & Titman) to 2025 (practitioner data). Source tier distribution: 10 Tier 1 journal citations, 5 Tier 2 working papers, and 5 Tier 3 practitioner sources. Grade B or above recommendations rely exclusively on Tier 1–2 sources; Grade C recommendations draw from Tier 3 by necessity, as peer-reviewed research on meme-coin sentiment or penny-stock liquidity is inherently limited.

The three most consequential academic anchors merit commentary. He & Manela (2024), forthcoming in the *Journal of Finance*, provides the theoretical foundation for the crypto perp funding-arbitrage strategy (Recommendation 24). Their finding that price convergence — not funding-rate carry — is the dominant profit source directly informs the dual-engine implementation. Burnside et al. (2011) underpins the forex carry sleeve (Recommendation 17); the Sharpe 0.86 figure serves as the conservative benchmark. Da et al. (2014), in *Management Science*, justifies the penny-stock reversal pilot (Recommendation 27) with t-statistics of 4.37–6.72, though the applicability assessment notes deal-breaking transaction-cost constraints.

### 10.3 Code Changes Summary

The implementation of the 35 recommendations catalogued in Section 10.1 requires modifications to four existing files and the creation of five new modules or directories. The table below specifies each file, the nature of the change, estimated line count, and the recommendation numbers it implements.

**Table 10.3: Code Changes — Files Modified and Added**

| File Path | Change Type | Lines (est.) | Recs. Implemented | Description |
|:------|:---:|:---:|:---:|------|
| `outcome_resolver.py` | Modified | +45 / −12 | 16, 18, 29, 30 | Add MAX_RESOLVE_RETRIES=3 cap; force FLAT closure at max retries; add 5bp floor for scalps; expand asset_class alias map; add schema validation layer[^14^] |
| `hc_filter.js` | Modified | +38 / −8 | 1, 3, 4, 6, 7 | Replace strat_fwd_wr with track_wr; lower R:R floor to 1.25; raise confidence ceiling to 0.95; remove WINNER_FILTER; add conditional symbol unban logic[^14^] |
| `hedge_fund_quality_gate.py` | Modified | +22 / −15 | 1, 2, 20 | Replace elite_score criterion with ml_score ≥0.82; add round(elite_score, 2); lower bond-specific elite_score floor to 15[^14^] |
| `hf_quality_gates.json` | Modified | +8 / −4 | 1, 3, 16, 20 | Remove elite_score from active gates; update R:R threshold to 1.25; add forex autoRelax floor; add bond-specific parameters[^14^] |
| `alpha_engine/track_calculator.py` | **Added** | ~180 | 29 | New module: computes strategy:symbol:direction track WR from resolved picks; daily batch job; persists track_key records[^14^] |
| `alpha_engine/statistical_rigor.py` | **Added** | ~220 | 32, 33 | New module: 1,000-run bootstrap CI; PSR calculator; DSR calculator; schema version enforcement[^15^] |
| `alpha_engine/hrp_allocator.py` | **Added** | ~260 | 32, 34 | New module: Hierarchical Risk Parity allocation; quarter-Kelly position sizing; correlation-gate enforcement[^15^] |
| `alpha_engine/decay_tracker.py` | **Added** | ~150 | 5, 33 | New module: auto-demotion ladder; time-based graduation A→B→C; regime-conditioned gate adjustment; kill-switch trigger[^15^] |
| `ml_crypto_predictor/researchers/` | **Added** | ~400 (8 files) | 8, 26 | 8 researcher personas for continuous edge detection; each persona ~50 lines; funding-rate scraper + sentiment analyzer[^3^] |

Total code impact: approximately 1,163 lines across 9 files — 1,010 additions (new files) and 153 net modifications. The track calculator is the single highest-priority new module; without it, forward-data gates in `hc_filter.js` remain inoperative on permanently zeroed inputs. The statistical rigor module follows because PSR > 0.95 is a mandatory Phase 1 capital-deployment gate.

The four modified files should deploy in a single coordinated release to prevent partial-state failures. A feature-flag mechanism in `hf_quality_gates.json` enables instant rollback. The estimated deployment window is 2–3 hours for modified files; new files require an additional 16–24 hours across the Phase 0–2 timeline.

