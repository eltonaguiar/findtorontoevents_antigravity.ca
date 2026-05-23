# Kimi Swarm Sports Betting Research — Cross-Reference Review

**Date:** 2026-04-26
**Reviewer:** Claude Opus 4.7 (via Explore subagent)
**Source artifacts:** `Kimi_Agent_Sports Betting Market Analysis/` (12 dimensions + final report + insight cross-verification)

## TL;DR

Kimi research is high-quality but **mis-sequences priorities** — pushes $49/mo Prediction Hunt before fixing the underlying 2–3 hour Odds API refresh bottleneck. Correct sequence:

1. **Upgrade The Odds API to $20/mo paid tier** (1-min refresh) — foundational, unlocks every downstream signal
2. Validate 4 weeks: does CLV move from −1.22% toward 0?
3. **Then** consider niche markets (WNBA, CS2) and prediction-market integration
4. **Reject** Prediction Hunt — Kalshi + Polymarket APIs are free and we already have a Polymarket scanner shipped
5. **Reject** the "Canada tax-free" framing — legally true for recreational players, **risky at scale** for systematic bettors (CRA professional-gambler reclassification triggers all 4 factors here)

## Top 5 actionable recommendations (re-ranked)

| Rank | Action | Cost | Effort | Why |
|---|---|---|---|---|
| 1 | Upgrade The Odds API → paid tier | $20/mo | <1 day | Current 2–3h refresh makes steam/arb capture structurally impossible. Single arb opportunity pays months of subscription. |
| 2 | Add WNBA + CS2 e-sports pilots | $0 | 1–2 wk | Soft lines, less sharp competition, leverages existing pipeline. |
| 3 | Enable sport-specific NHL + NBA models | $0 | 3–4 wk | Universal model with 9 bets is statistically inactive; domain heuristics outperform premature ML. |
| 4 | Build steam-move + reverse-line-movement detection | $0–100/mo | 2–3 wk | Requires #1 first. Sharp Sports API or DIY 1-min snapshots. |
| 5 | Build Polymarket whale-tracker layer | $0 | 1 wk | Top wallets specialize narrowly (Swiss Tony, HyperLiquid0xb, ColdMath); copy-trade as independent signal. |

## What this repo already has (Kimi over-claimed gaps)

| Component | Status in this repo | Notes |
|---|---|---|
| Polymarket edge scanner | **Shipped** | `tools/polymarket_edge_scan.py` (Gamma API) |
| Polymarket pick verifier | **Shipped** | `tools/verify_manual_sports_picks.py` (UFC/Tennis/Golf cross-check) |
| Pinnacle ML scraper | **Shipped (this PR session)** | `tools/pinnacle_anchor_scrape.py` — committed in PR #401 |
| Shin devig | **Shipped (this PR session)** | `sports_value_devig_shin()` in PR #401 |
| CLV backfill via OddsPortal | **Shipped** | `live-monitor/oddsharvester_clv_backfill.py` |
| Live CLV summary | **Live** | `sports_picks.php?action=clv` returning real numbers |
| Manual grading bypass | **Shipped (this PR session)** | `grade_manual` admin endpoint in PR #402 |
| `lookback_days` settle fix | **Shipped (this PR session)** | PR #402 |

The Kimi review missed all of the above — it was working off a stale snapshot. Anyone reading the report should mentally subtract these items from its "missing" list.

## Items the user should reject

- **Prediction Hunt $49/mo** — premature. Kalshi + Polymarket APIs are free; arbitrage matching can be in-house (we have the Gamma scanner already). Revisit only after #1 above is validated.
- **"Canada tax-free edge" framing** — legally true under ITA Para 40(2)(F) for recreational players, but a system with 105K+ commits, daily ML, and active EV optimization checks all 4 CRA professional-classification factors. Treat as secondary bonus, not edge.
- **Predictive Hunt as required for cross-platform arbitrage** — false. Cross-platform arb requires fast odds (Odds API paid tier), not aggregation as a service.

## What to verify before acting

- **Current Odds API tier** — audit `live-monitor/api/sports_odds.php` for the API key and refresh schedule. If already on paid tier, the refresh complaint may be a Kimi misread of a stale snapshot.
- **`avg_clv_pct` trend over the next 4 weeks** (after Pinnacle Shin lands + cron runs) — the weekly remote agent already scheduled handles this.

## Dimension index (one-line each)

| Dim | Topic | Takeaway |
|---|---|---|
| 01 | Current System Gap | 35+ ML features, 9 bets — model statistically inactive |
| 02 | Ontario Sportsbook Landscape | OLG Proline+ now competitive post-2022; legacy edges fading |
| 03 | Prediction Markets | Kalshi + Polymarket APIs free; cross-platform arb viable |
| 04 | OSS Libraries | 12 production-ready libs (sports-betting, surebet, penaltyblog, etc.) |
| 05 | Arbitrage Types | Pure rare/short; cross-platform + steam + promo viable |
| 06 | Polymarket Wallets | Top traders specialize narrowly — domain expertise wins |
| 07 | Niche Markets | WNBA / PWHL / CS2 / LoL — soft lines, less sharp competition |
| 08 | ML Architectures | Need 50–200 features + 200+ bets; sport-specific > universal |
| 09 | Steam Detection | Sub-50ms latency ideal; SHARP framework; needs <1min refresh |
| 10 | Data Infrastructure | The Odds API tier is THE bottleneck; $20/mo unlocks everything |
| 11 | Regulatory & Tax | Canada Para 40(2)(F) recreational-only; pro reclassification risk |
| 12 | Integration Roadmap | Tier 1: Odds API + niches; Tier 2: steam; Tier 3: whale; Tier 4: ML |

## Action items folded into existing todo list

1. Verify current Odds API tier (audit `sports_odds.php`).
2. If on free tier — open a tracking issue / PR proposal for the $20/mo upgrade.
3. Defer Prediction Hunt and prediction-market subscription items until Tier 1 validates.
4. Add WNBA + CS2 to the candidate niche-markets list once data feed is fast enough to surface real edges.
5. Update the auto-place gate doc to remove any reliance on the tax-free framing as a sizing input.
