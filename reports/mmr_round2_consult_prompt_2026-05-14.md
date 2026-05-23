# MMR Round 3 — Strategy Candidate Ranking Consult

## Context

I'm running money-maker-ready audit on a multi-asset-class trading dashboard. Round 1 swarm of 10 cavecrew-investigator agents surfaced strategy candidates per asset class. Need an independent second opinion on which to ship FIRST.

Current per-class state (post-resolver-v2):

| Class | n | WR | PF | Status |
|---|---|---|---|---|
| CRYPTO | large | 46.4% | 1.33 | Tier-3 PF-pass, WR below Tier-2 |
| EQUITY | mid | 51.4% | 1.55 | Tier-2 candidate, walkforward OOS WR 61.9% sharpe 7.53 |
| ETF | small | 56.6% | 1.41 | Best walkforward (OOS WR 74%, sharpe 10.08) |
| COMMODITY | very small | 70.5% | 4.03 | Artifact — 99% is COT over-emission falsified bug being fixed in PR #994 |
| FOREX | mid | 41.8% | 0.63 | Sub-floor, walkforward broken (OOS WR 11.5%) |
| BOND | thin | 54.5% | 0.66 | R:R inverted, all LONG in rising-rate environment, n=12 |
| FUTURES | 0 closed | n/a | n/a | No production strategies actively closing — 4 wired, 4 more in pending PRs #946/#949 |

Goal #1: phenomenal performance per class. Tier-2 floor PF≥1.5 / WR≥50 / MDD<20 / n≥100.

## Candidates per class (from Round 1 swarm)

**CRYPTO** — 3 unwired modules ready to wire (each module ships multiple strategies):
1. `alpha_engine/new_crypto_strategies_20.py` — 20 vol/OI/funding/on-chain strategies (CVI volatility regime)
2. `alpha_engine/pattern_strategies.py` — 10 chart patterns (H&S, double tops, triangles)
3. `alpha_engine/proven_research_strategies.py` — 22 research-backed (VWAP, pairs, RSI confluence; some with 62-83% WR claims)

All three are zero-caller modules. Wire-up effort: 3-5h total across smart_picks_engine orchestrator.

**EQUITY** — 3 SHORT candidates (production has 98.9% LONG bias, zero SHORTs):
1. RSI-2 Overbought SHORT (mirror of futures_connors_rsi2 LONG which has 75.7% WR on SPY). Effort 2-3 days. Universe: SPY/QQQ/IWM.
2. VWAP Fade SHORT (close > VWAP * 1.03 + vol_ratio > 2). Effort 4-5 days. Filter: $500M+ cap, no earnings ±2d.
3. Earnings Negative Drift SHORT (PEAD short on EPS miss > -5%). Effort 3-4 days. Hold 30-45d.

**BOND** — 3 candidates (current state: all LONG TLT in 4.4% 10Y yield environment):
1. ZN=F / ZT=F yield curve steepener/flattener pair. Expected 50% WR, 1.2+ PF.
2. HYG / IEF spread (credit-spread proxy). Expected 52% WR, 1.3+ PF.
3. TIP / IEF real-yield momentum (regime-isolated). Expected 48% WR, 1.5+ PF.

**FUTURES** — 3 next-tier (beyond pending PRs #946/#949):
1. FX futures momentum (6E=F, 6J=F, 6B=F, 6A=F). TSMOM applied to currency futures.
2. Crack-spread RB=F + HO=F (CL=F is blocked, refiner-margin proxy).
3. ES=F vs NQ=F divergence (index-spread mean reversion).

**COMMODITY** — 3 candidates (non-COT subset stats: WR 20% / PF 0.88 on n=15 — sub-floor):
1. Copper HG=F USD-inverse carry (counter-cyclical DXY pairs trade).
2. Gold/Silver seasonal volatility crush (Aug-Sep doldrums vol-premium harvest).
3. Grains ZC/ZW/ZS post-USDA reversal (2-5d mean reversion after weekly report).

## Question

Rank these 15 candidates (5 classes × 3 each) by **expected lift to /audit Tier-2 verification within 90 days** given:
- Tier-2 floor: PF≥1.5 / WR≥50 / MDD<20 / n≥100
- Sample-rate constraints: BOND/COMMODITY are n-starved; CRYPTO/EQUITY have data abundance
- ETF is already excellent on walkforward but stuck at n=87 active — scale-up is separate from new strategies
- FUTURES n=0 makes any new strategy hard to validate without re-launch

Output:
1. TOP 5 candidates I should ship first (P0). For each: estimated 90d Tier-2-progress + main risk.
2. TOP 5 that are TRAPS (look promising but won't deliver). For each: why.
3. Any candidates I'm missing (broad market mechanics, current macro 2026, etc.).

Keep responses concrete. No hedging. Single second-opinion, not consensus narrative.
