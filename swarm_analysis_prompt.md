Analyze the following audit dashboard content from findtorontoevents.ca/audit for trading strategy performance and identify:

1. **Failing Strategies**: Identify strategies or asset classes with poor performance metrics (low WR, PF <1.0, negative avg PnL). Specifically look for those that might benefit from:
   - More backtesting (n<100 closed trades)
   - DNA mutation (changing parameters, combining with other strategies, or fundamental redesign)

2. **Areas of Improvement**: 
   - Asset classes below tier targets (T2: PF>1.5/WR>50/MDD<20)
   - Strategies with BT-forward gaps (good backtest but weak forward performance)
   - Filters or gates that are currently harmful (e.g., R:R ≥1.5 underperforming)
   - Systems needing continuous monitoring for decay

3. **Winning Patterns**: Confirm what is working well to avoid regressions:
   - Proven strategies with high WR/PF
   - Effective filters (confidence 0.85-0.90 for crypto)
   - Strong asset classes (crypto ML-enhanced, etc.)

4. **Recommendations**: Provide specific, actionable suggestions for each failing area:
   - Backtest expansions (more symbols, time periods)
   - Parameter mutations (R:R adjustments, confidence thresholds)
   - Strategy combinations or new features
   - Kill lists for permanently failing systems

Focus on data-driven insights from the provided metrics. Prioritize high-impact changes that could turn sub-T2 asset classes into winners.

Audit Dashboard Content:

[Unified Audit Dashboard v99.0

Birds-eye view of ALL picks, portfolios, and system performance - loading...

🎯 MAJOR GOAL Phenomenal performance across **ALL** asset classes — sustainable, hedge-fund-grade.

**EQUITY** — T2 candidate (PF 1.41, WR 52.7%, n=421). Scale.ⓘ **CRYPTO** — PF 1.25, WR 44.6%, n=8067 (clean). Sub-T2; cut `quan_engine` drag. **ETF** — PF 1.24, WR 55.2%, n=87. Borderline T3; n→100. **COMMODITY** — PF 1.78, WR 46.9%, n=750 (post-resolver-v2). Meets T2 PF; lift WR. **FOREX** — PF 0.27, WR 46.4%, n=1169 (post-resolver-v2). Sub-floor; investigate-before-kill. **BOND** — PF 1.72, WR 55.6%, n=18. Meets T2 PF; n<100 charter floor. Roadmap: [Top-5 ROI actions](/updates/2026-04-28-per-asset-class-performance-summary.md)

**Tier definitions:** T1 PF>2/WR>55/MDD<10 (Renaissance). T2 PF>1.5/WR>50/MDD<20 (Institutional). T3 PF>1.2/WR>48/MDD<30 (Retail-OK). Source: `asset_class_health` in `audit_dashboard/data/dashboard_data.json` (post-resolver-v2 noise filter, generated 2026-05-03T00:06Z). Resolver fix shipped 2026-04-28; FOREX/COMMODITY numbers above are now genuine, not noise.

**⚠️ Two PF/WR figures may appear per class on this page.** The card above pulls `asset_class_health` (full-history closed-trade aggregate, post-resolver-v2 noise filter). The lower-down `hf_stats.by_asset_class` panel uses a recent-subset window (typically last 60-90d closed picks). Recent figures often diverge from headline — CRYPTO recent PF 0.89 vs headline 1.25 (n=1650 vs n=8067), COMMODITY recent 1.09 vs 1.78. **For deploy/sizing decisions, weigh the recent panel.** For long-horizon strategy validation, weigh the headline. Source: `dashboard_data.json::hf_stats.by_asset_class`.

📊 Per-asset-class walk-forward (OOS) Out-of-sample metrics from `walk_forward_by_class()` — Sharpe colored: green > 0.5, yellow 0–0.5, red < 0.

Loading…

🏆 TIER-2 PROVEN Buried high-edge strategies promoted from the alphabetical systems grid. Tier badges per [CHARTER §2](/docs/PERFORMANCE_CHARTER.md).

### Strategy detail

×

### Crypto + Non-Crypto Performance ? Guide

### How to Find the Best Picks — Definitions & Edge

×

#### 📖 Definitions (No Fancy Words Without Meaning)

**PROVEN** — A pick qualifies as PROVEN when its *strategy* has: (1) ≥5 closed trades, (2) ≥55% win rate after Bayesian shrink, (3) Profit Factor ≥1.5, and (4) confidence ≥0.7. Manually vetted systems (e.g., alpha\_engine, battleground+) can also earn PROVEN status.  
**Smart Picks** — An AI-curated basket. Every active pick is scored on 6 dimensions: *Regime match (25%)*, *Quality score (35%)*, *Freshness (15%)*, *TP upside remaining (15%)*, *Higher-timeframe alignment (10%)*, plus a *Proven Winner Boost (+8–15 pts)*. Only the top-ranked picks make it in.  
**Verified Alpha** — Signals that are auditable and verifiable: prediction-market consensus (Polymarket/Kalshi), audited copy-trader clones, or any strategy with ≥55% forward win rate on ≥5 trades.  
**High Conviction** — The strictest preset. It applies shared hard gates (score ≥40, trust tier, forward WR, regime alignment, consensus) *plus* per-asset-class floors. If a row shows here, it passed every single gate.  
**Trust Tiers** — PROVEN = elite edge. DEVELOPING = good edge. WATCH = marginal. SANDBOX = unproven/new. PROBATION = broken/banned system.

#### 🎯 Where Our Edge Actually Is (Closed-Pick Data, n=4,618)

**Crypto Confidence 0.85–0.90** — the strongest single filter: **82% WR**, PF **11.8** (n from per-class audit). Crypto >0.90 hits an overfit cliff (47% WR).  
**Proven ML Strategies** — 8 ML-enhanced strategies with n≥5, WR>55%, PF≥1.5: **79.4% WR**, avg +**0.08%**, PF **11.34** (n=199). Top: DYDX 15m (95.5% WR), STRK 15m (95.2% WR), INJ 1d (95.0% WR), BNB 15m (89.5% WR).  
**Proven + High Confidence Combo** — PROVEN strategy + CONF 0.8–0.9: **71.3% WR**, avg +**0.11%**, PF **13.21** (n=94).  
**R:R Truth (CRYPTO, verified 2026-04-17 across 1,916 closed picks)** — R:R 1.0–1.5: 62.3% WR, PF 1.66, +0.71% avg (n=150 — highest WR band). R:R 1.5–2.0: 52.5% WR, PF 1.92, +0.69% avg (n=983 — volume sweet spot). R:R ≥2.0: 58.0% WR, PF 3.06, +0.99% avg (n=715 — highest PF AND avg). R:R <1.0: 55.9% WR but PF 0.93, -0.19% avg (n=68 — high WR can't overcome bad geometry). Prior tooltip claimed R:R≥2.0 was 29.5% WR catastrophic — empirically wrong; triple-verified via DeepSeek + Inception mercury-2 + Ollama Cloud gpt-oss:20b.  
**Confidence is NOT global** — FOREX peak is 0.75–0.80 only (49% WR); 0.70–0.75 is DANGER (25% WR). EQUITY is bipolar: >0.90 works (67% WR) but 0.85–0.90 is the WORST bucket (20% WR). COMMODITY peak is 0.70–0.75 (48% WR). A single confidence threshold cannot work across asset classes.  
**Direction = BUY** — 3,909 picks, 28.9% WR, PF 0.38. **Direction = LONG** — 441 picks, 54.9% WR, PF 3.14. (The winning cohort is signal\_type=BUY + direction=LONG at 62.6% WR.)  
**High-grade A/B** — **NOT** an edge: 49.3% WR, PF 0.66, -0.08% avg (n=483).  
**Asset Class Edge** — ML-Enhanced (crypto) = 55.1% WR, PF 1.77. Quan Engine (crypto) = 29.0% WR, PF 0.38. Non-crypto closed-book data is thin or unprofitable; size smaller or avoid.  
Bottom line: For crypto, prioritize *ML-enhanced proven strategies* and *confidence 0.85–0.90*. Avoid quan\_engine scalps, wide R:R, and BUY-only signals. For non-crypto, be aware that tile PnL is now cost-adjusted (net), which can flip the sign on thin edges.

#### Best Filter by Asset Class

Asset

Use This Filter

WR (filtered)

WR (all picks)

Lift

PF (filtered)

Crypto

Confidence ≥0.8 or Proven strategy

69.2%

49.6%

+19.6pp

10.39

Stocks

Trusted + score ≥50

69.2%

43.4%

+25.8pp

0.77\*

Forex

Trusted

49.0%

42.9%

+6.0pp

3.59

Commodities

Trusted

44.5%

42.3%

+2.2pp

1.26†

\* Stocks *Trusted* produces a high WR but PF 0.77 on a small n=13 — one outsized loser offsets many small wins. **Not** a verified edge by the PF > 1.5 rule; combine with **Maximum Conviction Combo** (PROVEN + score ≥ 50), which matches the closed-book equity filter in `MERCURYPROMPT.md` (Score ≥ 50 + Trust ≥ 3, PF 2.62).  
† Commodities *Trusted*: PF 1.28 with bootstrap CI straddling 1.0 on n=273 — **inconclusive** in `MERCURYPROMPT.md`; listed here for WR lift only, **not** gold-standard edge.  
**R:R ≥ 1.5** filter currently underperforms baseline across *every* asset class (crypto −0.4pp, equity −1.0pp, forex −9.2pp, commodity −32.3pp). Use cautiously.

#### Maximum Conviction Combo (under re-validation)

**PROVEN strategy + confidence 0.8–0.9 — *insufficient sample***  
Original claim (71.3% WR, PF 13.21, n=94) is not reproducible on the current `recent_closed` window (n=0 matching picks). The band is hidden from display until it repopulates ≥20 closed picks under the post-correction PROVEN tier (`claude_gainer_st` was demoted 2026-04-20). Re-evaluate weekly. See `docs/AUDIT_EFFECTIVENESS_AUDIT_2026_04_20.md` and `docs/REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md` for the methodology under reconstruction.

#### What the Badges Mean

🏆 **Forward-proven** — strategy verified in BOTH backtest AND forward testing. The real deal.  
⚠️ **BT-forward gap** — backtest looks great but forward performance is weaker. Proceed with caution.  
(n=X) **on Profit Factor** — small sample warning. PF on <30 trades can be dominated by one lucky trade.

#### What to Avoid

• **Grade D & F picks** — 725 trades at 33.4% WR, PF 0.82, −131.8% cum PnL (improved from −509% after blocked-source sweep)  
• **Commodities SHORT on copy\_trader** — 50% of picks come back as LOST (unresolved), masking real TP/SL performance  
• **Futures** — 6.3% WR on n=17 with 76% LOST-exit rate. Kill list pending.  
• **ETFs** — PF 0.28 on 19 trades, dominated by `extreme_oversold_bounce` at 0% WR  
• **Low-confidence crypto** — confidence <0.6 shows 26–44% WR and deep negative avg PnL  
• **R:R ≥ 1.5 filter on non-crypto** — currently harmful across equity, forex, commodity (see footnote above)

#### Understanding Profit Factor

PF = gross wins ÷ gross losses. **PF > 1.5** on adequate `recent_closed` sample with PF CI above 1.0 is our **verified edge** bar (same criterion as `MERCURYPROMPT.md`). PF > 2.0 = strong. PF > 3.0 = exceptional.  
**HIGH CONVICTION** on Active Picks enforces forward (**FWD WR**) + score + trust gates from that evidence so the live table stays consistent with these PF-verified cohorts (crypto / equity / forex only in strict mode).  
The **Avg PnL/trade** row grounds the Realized PnL sum — a +621% PnL on 1,745 trades is really +0.36% per trade on average.

[Full User Guide →](/updates/2026-04-12-user-guide-optimal-filters.md)

... (truncated for brevity, but include full content in actual prompt)]

Provide your analysis in a structured format with sections for each asset class, failing strategies, improvement recommendations, and priority actions.