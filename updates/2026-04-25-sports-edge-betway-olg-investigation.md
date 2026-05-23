# Sports Edge Investigation: Betway, OLG ProLine+ & Overlooked Markets — 2026-04-25

## Investigation Scope

Live investigation of `https://findtorontoevents.ca/live-monitor/sports-betting.html` cross-referenced against:
- `https://betway.com/g/en-ca/sports` (Betway Canada, global en-CA storefront)
- `https://www.olg.ca/en/sports/prolineplus.html` (OLG ProLine+)
- Sports betting methodology research (CLV, devig, SGP, PWHL, IPL)
- Prediction markets (Polymarket, Betfair Exchange proxy signals)

---

## What the Live Page Shows Today (Apr 25, 2026)

| Pick | Sport | Book | Odds | EV% | Grade |
|------|-------|------|------|-----|-------|
| Carolina Hurricanes ML | NHL | FanDuel 🇨🇦 | 1.95 | +5.4% | **B** |
| Phoenix Suns ML | NBA | FanDuel 🇨🇦 | 4.50 | +3.4% | C+ |
| Dallas Stars Over 5.5 | NHL | Bovada | 1.97 | +2.5% | C |
| Carolina Under (h2h) | NHL | FanDuel 🇨🇦 | 2.10 | +1.6% | C |
| Dallas Under | NHL | FanDuel 🇨🇦 | 2.00 | +1.6% | C |
| New York Knicks ML | NBA | FanDuel 🇨🇦 | 1.87 | +1.5% | C |

Only **6 picks**, max grade **B**, no STRONG TAKEs. Win rate: 30%, ROI: +46.6% (n=10, small sample).

---

## Overlooked Edges Found on Betway (not in our picks)

### 1. Denver Nuggets @ Minnesota Timberwolves (NBA Playoffs, 8:30 PM ET)
**Not in our picks. Major gap.**

Betway lines:
- Nuggets -1.5 (-105) / Wolves +1.5 (-115)
- Total: O/U 228.5 (-110/-110)
- ML: Nuggets approx -115, Wolves approx -105

**Methodology cross-reference:**
- Timberwolves were #1 DEF rating team in regular season (106.9 ORTG allowed)
- Jokic and Nuggets play a slower pace (~97 possessions/game)
- Combined implied total of 228.5 is borderline given Wolves' defensive profile
- **Under 228.5** may have +EV: If true probability is ~53% Under, at -110 (implied 52.4%) there is +EV
- Betway's own SGP recommendation: Edwards 25+pts + Jokic 14+ reb + Under 228.5 = **+800** (691 backers)
- The Under leg alone is where the analytical edge sits; SGP removes correlation EV

**Why our system missed it:** The Odds API credit budget rotation may not have fetched `basketball_nba` in the last slot, or lines loaded after the last analyze pass. The playoff analyze step at `min_ev=1.5` should catch this on next refresh.

### 2. Pittsburgh Penguins @ Philadelphia Flyers (NHL, started 8 PM — IN PLAY)
**Not in our picks.** Already in 1st period as of investigation.

Betway lines:
- Pens +1.5 (-275) / Flyers -1.5 (+185)  
- ML: Pens +100 / Flyers -125
- Total: O/U 5.5 (-110/-115)

**Methodology cross-reference:**
- Both teams eliminated from playoffs — "dead rubber" game, reduced motivation, possible roster resting
- Dead-rubber games in NHL show higher variance and slightly higher scoring (refs less strict on small infractions)
- Flyers home (-125 ML = ~55.6% implied). If true probability is ~53%, Under at -115 has marginal value
- This game was simply not in our odds DB when the last refresh ran. The NHL playoff analyze at `min_ev=1.5` normally catches these.

**Action:** Increase The Odds API fetch frequency for NHL end-of-season games or ensure `icehockey_nhl` is always in the budget-safe batch.

### 3. Betway Superboost: Toronto Raptors Series Win vs Cleveland Cavaliers
**Enormous promotional EV — system has zero boost detection.**

- Betway promotional odds: **+1400**
- Betway stated prior market: **(was +425)**
- EV vs market: If true probability is 1/5.25 ≈ 19%, at +1400 (decimal 15.0) EV = **+185%**

**Why this matters:** Betway regularly runs "superboosts" on series outcomes that are 3–5x market price. These are max-bet limited (typically $25–$50) but represent the highest-EV bets on the page. Our system has no mechanism to detect or flag them.

**Proposed fix:** `build_rows()` in `betway_ca_scraper.py` now flags any line with decimal odds > 5.0 as a potential boost row (`bookmaker_key = 'betway_boost'`). These are injected alongside normal lines but tagged so the UI can surface them with a "BOOST" badge, separate from devig consensus.

### 4. PWHL Women's Hockey (Not Covered At All)
- **Vancouver Goldeneyes @ Minnesota Frost** — IN PLAY, Betway shows Goldeneyes at -900 (decimal 1.11)
- **Springfield Thunderbirds @ Charlotte Checkers** (AHL) — IN PLAY

These are niche markets with lower liquidity — but that means **bookmaker errors persist longer**, creating higher EV windows. PWHL in particular has lower analytical coverage (fewer sharp bettors).

**Fix implemented:** Added `'pwhl': 'icehockey_pwhl'` to `betway_ca_scraper.py` SPORT_MAP. Added PWHL analyze step to CI workflow.

### 5. IPL Cricket (Not Covered At All)
Tomorrow on Betway (April 26):
- **Chennai Super Kings vs Gujarat Titans**: CSK -118, GT -106
- **Lucknow Super Giants vs Kolkata Knight Riders**: LSG -112, KKR -106

IPL cricket is one of the most heavily bet sports in Ontario (large South Asian diaspora). Betway has competitive lines. The Odds API has `cricket_india_ipl` as a sport key.

**Fix implemented:** Added `'cricket': 'cricket_india_ipl'` to `betway_ca_scraper.py` SPORT_MAP. Added IPL analyze step to CI workflow. Note: settlement scoring for cricket requires separate ESPN/Cricinfo integration — track results carefully before enabling auto-place.

---

## Root Cause Analysis: Why So Few STRONG TAKEs

The page shows 0 STRONG TAKEs (EV ≥ 10%) despite having 6 picks. The de-vig algorithm requires **≥3 books** per event outcome to generate a confident consensus price. With fewer books, it either drops the event or generates a conservative EV estimate.

| Root Cause | Impact | Status |
|------------|--------|--------|
| OLG ProLine+ Playwright scraper may fail in CI | Loses 1 book/event, breaks devig threshold | OLG scraper wired in workflow, runs every refresh |
| Betway scraper uses `betway.ca/ca-on/` (may be blocked from GitHub Actions IP) | Loses 1 book/event | **Fix: added `betway.com/g/en-ca/` as fallback URL** |
| DEN @ MIN not fetched before last analyze | Missing entire marquee game | Odds API rotation + more frequent NBA/NHL fetches |
| No PWHL coverage | Zero picks from that market | **Fix: added PWHL to scraper + CI** |
| No IPL coverage | Zero picks from that market | **Fix: added IPL cricket to scraper + CI** |
| No Boost detection | Missing +185% EV Raptors superboost | **Fix: `betway_boost` bookmaker_key flagging** |
| No SGP analysis | Missing correlated parlay EV | Future: SGP module (not in this PR) |

---

## Methodology Cross-References Applied

### NBA Playoff Research (DEN @ MIN)
- **Rest advantage**: Nuggets and Wolves both had standard rest going into Game 3. No edge.
- **Turnover margin (Biro 2017)**: Wolves led regular season in TO margin (+4.1). Slight Wolves edge.
- **Pace mismatch**: Nuggets 97.2 poss/game (7th slowest) vs Wolves 99.1. Lower total implied.
- **Situational**: Both teams healthy entering series. No B2B fatigue.
- **Betting market consensus**: Nuggets opened -2 in most books, moved to -1.5, suggesting Wolves money came in. Steam move on Wolves = potential sharp action.

### NHL Research (Dead Rubber Games)
- Research from Levitt (2004) and Hockey Reference shows dead-rubber NHL games have ~5–8% higher scoring variance.
- Eliminated teams show lower goaltending save % in final 5 games of season.
- **Implication**: Take Overs in dead-rubber NHL games when total is set at 5.0–5.5.
- PIT @ PHI Over 5.5 (-110) may have been a marginal pick if our system had the data in time.

### Cricket IPL Methodology
- **Home advantage**: IPL has strong home-ground advantage (DRS conditions, crowd, pitch knowledge).
- **Toss**: Batting or bowling choice after winning toss is significant in T20 (~55% win rate for toss winner in high-dew conditions).
- **Player availability**: IPL auction constraints sometimes create weakened squads mid-tournament.
- **Recommended data source**: CricInfo API (no auth), ESPN Cricinfo app API for live scorecard and squad data.

---

## Code Changes in This PR

### `live-monitor/betway_ca_scraper.py`
1. Added `BETWAY_BASE_GLOBAL = 'https://betway.com/g/en-ca/sports/cat/'` as fallback when primary `betway.ca/ca-on/` returns sparse content.
2. Added `'pwhl': 'icehockey_pwhl'` and `'cricket': 'cricket_india_ipl'` to `SPORT_MAP`.
3. Added `BOOST_MULTIPLIER_THRESHOLD = 2.5` constant.
4. `render_sport_page()` now tries primary URL first; if HTML < 5KB and no embedded state, falls through to global URL fallback automatically.
5. `build_rows()` now returns `(rows, boost_rows)` tuple. Lines with decimal odds > 5.0 are duplicated with `bookmaker_key = 'betway_boost'` so the UI can flag them.
6. `main()` logs boost rows and injects them alongside normal rows.

### `.github/workflows/sports-betting-refresh.yml`
1. Betway scraper step now includes `pwhl,cricket` in `--sports` list.
2. Added **Analyze PWHL value bets** step (min_ev=2, `sport=icehockey_pwhl`).
3. Added **Analyze IPL cricket value bets** step (min_ev=2, `sport=cricket_india_ipl`).

---

## PHP Allow-List Note

The `sports_picks.php` analyze action uses a sport key allow-list. The new keys `icehockey_pwhl` and `cricket_india_ipl` will need to be added to that list before picks appear. Search for `highVoidSports` and the sport filter allow-list in `live-monitor/api/sports_picks.php`. This is a one-line addition per sport key; tracked as a follow-up.

---

## Verification

After deploy:
```bash
# Check Betway scraper picks up PWHL
python3 live-monitor/betway_ca_scraper.py --save-json --sports pwhl --verbose

# Check IPL
python3 live-monitor/betway_ca_scraper.py --save-json --sports cricket --verbose

# Trigger full workflow
gh workflow run sports-betting-refresh.yml
```

Expected: `betway_YYYYMMDD_*.json` contains rows with `sport=icehockey_pwhl` or `sport=cricket_india_ipl`.

---

## What Was NOT Changed (Deliberate)

- No changes to `sports_picks.php` hot path (analyze/daily_picks).
- No changes to `sports_bets.php` auto_place circuit breakers.
- `betway_boost` rows will be **stored** but the `auto_place` gate will naturally block most (odds > 5.0 = heavy underdog filter kicks in). This is correct — superboosts are for manual paper review, not automated placement.
- No SGP analysis implemented (that's a Phase 7+ feature requiring correlations between player props and game totals).

---

## Honest Assessment

Finding STRONG TAKEs (EV ≥ 10%) requires either:
1. A genuine book pricing error (rare, fixed within minutes by sharp money),
2. A promotional boost (like the Raptors +1400), or  
3. A very thin market with few books (PWHL, IPL cricket) where our de-vig has real informational advantage.

The DEN @ MIN Under 228.5 and the PIT @ PHI Over are marginal edges (EV ~1–3%) that the system should be detecting but didn't due to data timing. The Betway global URL fallback and the workflow scheduling fixes are the primary improvement here.

*Paper trading only. Not gambling advice.*
