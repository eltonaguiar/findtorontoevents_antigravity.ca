# Sports Picks Quality Analysis — 2026-04-25

## Dashboard Overview

| Metric | Value |
|--------|-------|
| Bankroll | $1,045.28 (+$45.28) |
| Total directional bets | 27 (3W 7L 17V) |
| Sport void splits | NBA 3V, NCAAB 2V, NHL 2V, **MLS 10V** |
| All-time win rate (w/L only) | 30.0% |
| All-time ROI | +46.61% |
| Active/pending bets | 8 ($85.43 stake locked) |
| Stale pending (>14d) | 7 bets ($85.43) |

> **Key problem:** 7 pending bets are >14 days old with no settlement. These are tied to games that finished but couldn't be matched by the Odds API scores endpoint (team name mismatch, league deprecation, or API response drift). They're locking $85.43 (8.2% of bankroll).

## Today's Value Bets (7 picks)

| Pick | Sport | Book | Odds | EV% | Win% | Score | Grade |
|------|-------|------|------|-----|------|-------|-------|
| Lakers ML | NBA | FanDuel 🇨🇦 | +325 | 10.46% | 23.5% | 76 | STRONG TAKE |
| VGK @ UTA o6.0 | NHL | Unibet 🇨🇦 | +110 | 3.22% | 47.6% | 47 | LEAN |
| TBL @ MTL u6.0 | NHL | FanDuel 🇨🇦 | +102 | 2.93% | 49.5% | 46 | LEAN |
| Spurs ML | NBA | FanDuel 🇨🇦 | -120 | 2.33% | 54.5% | 44 | LOW EDGE |
| POR ML | NBA | Unibet 🇨🇦 | +140 | 1.88% | 41.7% | 42 | LOW EDGE |
| VGK @ UTA u6.0 | NHL | FanDuel 🇨🇦 | -104 | 1.88% | 51.0% | 42 | LOW EDGE |
| HOU -8.5 | NBA | William Hill | +100 | 1.76% | 50.0% | 42 | LOW EDGE |

**Canadian sportsbook access:** 6/7 picks available on Canadian books ✅

### Top Picks Assessment

**1. Lakers ML (+325 @ FanDuel) — Score 76, EV 10.46%**
- Pros: Highest value bet in the deck. 10.46% EV justifies the longshot. Full Kelly sizing.
- Pros: FanDuel is a major Canadian book — actionable immediately.
- Cons: 23.5% win probability means this will lose ~3 out of 4 times. Proper bankroll management required.
- **Verdict:** Best EV play available today. Low confidence single-session outcome, high expected value over many trials.

**2. Spurs ML (-120 @ FanDuel) — Score 44, EV 2.33%**
- Pros: Highest win probability today (54.6%). Favorite odds.
- Pros: FanDuel is Canadian and live.
- Cons: Very thin edge (2.33%). One bad call by oddsmakers erases it.
- **Verdict:** Decent low-risk anchor bet. Use ½ Kelly.

**3. TBL @ MTL u6.0 (+102 @ FanDuel) — Score 46, EV 2.93%**
- Pros: Near-coin flip (49.5%) with plus-money odds. Solid edge for NHL.
- Pros: Canadian teams (Montreal-based) which may attract sharper local lines.
- **Verdict:** Good NHL playoff under play. Reasonable for a small roster play.

## Per-Sport Quality Analysis

### NBA (2W 2L 3V: ∞% n/a WR on settled)
- **Issue:** 3 voids — likely from summer league/preseason games. The scraper fetches all NBA events including exhibitions.
- **Fix:** Add `completed` game type filter or exclude July-September events.

### NCAAB (1W 5L 2V: 16.67% WR)
- **Key problem:** 5 losses in 6 settled bets. Wilson CI: [10.78%, 60.32%] — massive uncertainty at n=6, but the losses outnumber wins.
- **Root cause:** NCAAB lines are notoriously volatile. Mid-major tournament games have limited market depth, causing wider spreads and lower efficient odds.
- **Recommendation:** Pause NCAAB value betting until n=20+. The sample is too small to trust, but the direction is concerning.

### MLS (0W 0L 10V: 100% void rate)
- **Key problem:** All 10 MLS bets voided. None settled as win or loss.
- **Root cause analysis:**
  1. The Odds API `/scores` endpoint for `soccer_usa_mls` may not include completed scores for the specific competition stage (Leagues Cup, regular season, etc.)
  2. MLS team name variants ("Vancouver Whitecaps FC" vs "Vancouver" vs "Whitecaps") may not match between the odds data and scores data — though the alias system handles FC/SC/CF suffixes, MLS also has "Inter Miami CF" vs "Inter Miami" vs "Miami" variants that may not be covered.
  3. MLS games often have non-standard commence times that drift past the stale threshold before scoring data arrives.
  4. The stale threshold (likely 7-14 days) eventually voids unmatched bets, which is why they show as "void" instead of "pending".
- **Impact:** 37% of all bets by count (10/27) are voided MLS picks. This wastes Kelly stake allocation and pollutes the dashboard metrics.
- **Proposed fix:** Exclude `soccer_usa_mls` from the analyze pipeline if its sample shows >50% void rate until score matching is fixed.

### NHL (0W 0L 2V: n/a)
- Both picks from the regular season that never matched scores.
- Playoff markets (current) should settle better since The Odds API prioritizes playoff games.

## Pipeline Health

| Component | Status |
|-----------|--------|
| Odds API fetch (NBA/NHL/MLB/NFL/MLS) | ✅ 5+ books per event for NBA |
| Devigging (multi-book no-vig) | ✅ 75%+ of events have 3+ books |
| Value bet analysis | ✅ Running at 2-4% min EV thresholds |
| Auto-place with bankroll mgmt | ✅ Kelly sizing active |
| Score settlement | ⚠️ MLS 100% void, NHL 100% void |
| Daily picks snapshot | ✅ Generating 7 picks/day |

## Recommendations

1. **Clear stale pending picks** — The 7 stale pending bets ($85.43 locked) should be manually voided after age-based review (14d+). This frees capital.

2. **Pause MLS value betting** — 100% void rate is unacceptable. Score matching for `soccer_usa_mls` is unreliable. Re-enable only after confirming correct score data arrives within 48h of game end.

3. **Monitor NCAAB** — The 16.67% WR over 6 settled picks is below any reasonable threshold. Set a minimum sports-level confidence filter: if WR < 25% after n≥10, auto-pause.

4. **Track post-guardrail cohort** — The April 2026 guardrail policy shows 1W 0L +$28.62 (215% ROI). Track this cohort separately and compare against pre-guardrail performance.

5. **No changes to the NBA/NHL/MLB pipeline** — These sports have positive EV picks flowing and the devig system is working as designed. Fix only the voiding issues.

## Highest-Confidence Bets for Canadian Sportsbooks Today

Ranked by a combined metric of (EV × WinProb × available_on_Canadian_book):

| Rank | Pick | Book 🇨🇦 | Why |
|------|------|---------|-----|
| 1 | **Lakers ML (+325)** | FanDuel | Strongest value. 10.46% EV supports the Kelly edge model. |
| 2 | **Spurs ML (-120)** | FanDuel | Highest win prob at 54.6%. Low-risk edge. |
| 3 | **TBL @ MTL u6.0 (+102)** | FanDuel | Plus-money on a near coin flip. NHL playoffs. |
| 4 | **VGK @ UTA u6.0 (-104)** | FanDuel | 51% win prob, tiny edge. Lowest conviction. |

*Generated by OpenClaude on 2026-04-25.*
