# FOREX Carry Trade Amplification Plan — 2026-06-12

**Source:** DAILY_IDEAS.MD analysis + live `money_ready_verdict.py` + `strategy_tier_tracker.py`

## Current State (main branch baseline)

| Metric | Value |
|--------|-------|
| Class verdict | INSUFFICIENT_DATA (n=25) |
| CRYPTO only class above floor (NOT_READY, n=178) |
| All other classes also INSUFFICIENT_DATA |

**Key finding:** On `intrabar-resolve-signal-outcomes-2026-06-09` branch (unmerged), FOREX reaches T2 (n=115, PF=1.79, WR=57.4%) with `carry_trade` at T1 (PF=2.01, WR=73.1%, n=26). This suggests the resolver/pipeline improvements on that branch unlock the carry_trade edge. Main lacks these results.

## Relevant DAILY_IDEAS.MD Items

| Idea | Score | Relevance |
|------|-------|-----------|
| IDEA-A: Proven criteria per asset class | 7/10 | FOREX `carry_trade` is the #1 proven class-specific criterion |
| Grok Phase 2 #3: FOREX carry factor scaffold | High | Implement realized vol + carry/vol gate |
| Phase 2-D kill audit: existing gates working | Confirmed | carry_trade_momentum is blocked (strategy_blocklist) but `carry_trade` is not |
| FX carry isolated from multi_asset_copytrader | Actionable | carry_trade's edge is suppressed when bundled with failing systems |

## Concrete Action Items (ranked by ROI)

### 1. Amplify FOREX carry_trade pair coverage (THIS PR)
- Add G10 crosses (EUR/CHF, GBP/CHF, EUR/GBP, NZD/JPY, CAD/JPY, CHF/JPY, AUD/CAD, NZD/CAD)
- Add realized volatility filter: `carry/vol > 0.5 AND 20d realized vol < 8%`
- Sync carry yields between `forex_smart_picks.py` and `multi_asset/forex_strategies.py`
- **Expected impact:** +40-60% more carry_trade picks with higher quality (vol filter removes high-volatility regimes where carry trades blow up)

### 2. Resolver/pipeline merge (already in feature branch)
- The `intrabar-resolve-signal-outcomes-2026-06-09` branch has the resolver improvements that unlock carry_trade's T1 stats
- Without that branch, carry_trade doesn't appear in pf_registry at all
- **Priority:** Merge that branch or port its carry_trade wiring

### 3. Carry-vol regime gate (future)
- Add DXY correlation breakout → reduce carry exposure
- Add VIX regime filter for FOREX carry (carry trades break during vol spikes)
- Academic basis: Lustig, Roussanov & Verdelhan (2011) — carry trades lose during high-VIX regimes

## Risk Notes

| Risk | Mitigation |
|------|-----------|
| More pairs = more noise | Vol filter gates entry; ADX > 18 minimum trend strength |
| Carry yields change quarterly | Hardcoded values need regular updates; automate via FRED API |
| Cross-pair correlation | AUD/CAD and NZD/CAD are >0.75 correlated; cap total carry position size |
| DSR still failing on unmerged branch | Need more n (≥30 per strategy) for statistical significance |
