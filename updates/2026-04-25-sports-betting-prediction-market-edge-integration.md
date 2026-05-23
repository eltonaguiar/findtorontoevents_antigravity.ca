# Sports Betting: Prediction Market + OLG/Betway Edge Integration

**Date:** 2026-04-25  
**Scope:** Integrate Polymarket prediction-market signals, OLG ProLine+, Betway, and research-backed situational edges into the existing sports betting pipeline.  
**Author:** Antigravity AI  
**Branch:** `feature/sports-betting-edge`  

---

## 1. Executive Summary

The existing `live-monitor/sports-betting.html` stack already has:
- The Odds API (bet365, FanDuel, DraftKings, BetMGM, PointsBet, Caesars)
- OLG ProLine+ and Betway scrapers (Playwright, inject into `lm_sports_odds`)
- Devig (Jensen / Pinnacle anchor), +EV, quarter-Kelly, auto_place
- PM signal JSON loader (optional, consumed by `sports_picks.php`)

**What was missing:**
1. No automated generation of `sports_prediction_market_signals.json` — it was manual/placeholder.
2. The Python `sports_edge_finder.py` and `sports_betting_edge.py` used mocked data.
3. No arbitrage scanner across OLG/Betway/The Odds API books.
4. No research-backed situational adjustments (rest, B2B, divisional dogs, etc.).

**What this PR adds:**
| Module | Purpose |
|--------|---------|
| `alpha_engine/sports_prediction_market_sync.py` | Fetches Polymarket sports events via public Gamma API, writes JSON signal file |
| `alpha_engine/sports_arbitrage_scanner.py` | Queries `lm_sports_odds`, detects pure arbitrage across all books including OLG/Betway |
| `alpha_engine/sports_situational_edge.py` | Research-backed prob adjustments (NBA rest, NHL B2B, MLB div dogs, NFL key #s, soccer draw bias) |
| `alpha_engine/sports_edge_finder.py` | **Rewritten** — now reads real DB odds, matches PM signals, applies situational model, outputs +EV edges |
| `alpha_engine/sports_betting_edge.py` | **Rewritten** — orchestrates PM sync + arb scan + value-bet scan into unified output |
| `.github/workflows/sports-prediction-market-sync.yml` | CI job that syncs PM signals 2x daily and commits JSON with `[skip ci]` |
| `live-monitor/sports-betting.html` | Updated disclaimer to list OLG + Betway; added "Prediction Market Integration (Live)" section in Research tab |

---

## 2. Investigation Findings

### 2.1 URLs Analyzed
- **https://findtorontoevents.ca/live-monitor/sports-betting.html** — Existing paper-trading dashboard. Mature PHP pipeline with devig, CLV tracking, ML filter bridge.
- **https://www.olg.ca/en/sports/prolineplus.html#home** — Ontario-regulated book. Already scraped by `live-monitor/olg_prolineplus_scraper.py` (Playwright, Next.js SPA). Injects `olg_prolineplus` rows into `lm_sports_odds`.
- **https://betway.com/g/en-ca/sports** — International book with ON storefront. Already scraped by `live-monitor/betway_ca_scraper.py` (Playwright, multi-sport). Injects `betway` rows.

### 2.2 Prediction Markets Researched
| Source | Sports Coverage | Auth | Integration Complexity |
|--------|-----------------|------|------------------------|
| **Polymarket Gamma API** | NBA, NHL, NFL, MLB, soccer, UFC | None (public read) | Low — used |
| **Kalshi REST API** | NBA, NFL, soccer, tennis | RSA-PSS + session tokens | High — deferred |
| **Prediction Hunt** | Cross-platform aggregation (Kalshi+Polymarket+…) | `X-API-Key` | Medium — future option |
| **BALLDONTLIE** | Odds comparison including PMs | API key | Medium — future option |

**Decision:** Use Polymarket Gamma API for the initial integration because it requires zero authentication, has live sports game markets (e.g. "Thunder vs. Suns"), and the `lastTradePrice` field directly maps to win probability.

### 2.3 Methodologies & Edges Found
From academic literature and sharp-betting communities:

| Sport | Edge | Research Source | Adjustment |
|-------|------|-----------------|------------|
| NBA | Rest advantage (3+ days vs B2B) | Entine & Small 2008; Dean Oliver 2004 | ±6.5% true prob |
| NHL | Back-to-back fatigue | Hockey Graphs 2014 | ±5.5% true prob |
| MLB | Divisional underdogs in low-total games | Sabermetric research 2017-2020 | +2-3.5% true prob |
| NFL | Home dogs +3 or less in divisional | Key-number theory + public bias | +3% true prob |
| NFL | Wind >15 mph | Weather lag inefficiency | +2% to underdog/draw |
| Soccer | Draw bias in low-scoring leagues | European league efficiency studies | +1.5-2.5% draw prob |

These are implemented as additive adjustments in `sports_situational_edge.py`.

---

## 3. How the New Data Flows

```
Polymarket Gamma API
       |
       v
sports_prediction_market_sync.py  ---->  backfill/sports_prediction_market_signals.json
       |                                          ^
       |                                          | (CI commits 2x daily)
       v                                          |
lm_sports_odds  <---- OLG scraper / Betway scraper / The Odds API
       |
       v
sports_arbitrage_scanner.py  ---->  backfill/sports_arbitrage_alerts.json
       |
       v
sports_edge_finder.py  (reads DB + PM JSON + situational model)
       |
       v
sports_betting_edge.py  (orchestrator)
       |
       v
production_scanner.py  (optional hook)  /  dashboard / manual review
```

---

## 4. File-by-File Changes

### 4.1 NEW: `alpha_engine/sports_prediction_market_sync.py`
- Fetches `gamma-api.polymarket.com/events` (public, no auth)
- Filters sports events by title/tag keywords
- Extracts moneyline market (skips spread/total/prop markets)
- Uses `lastTradePrice` as probability estimate
- Writes JSON in exact format expected by `sports_picks.php`:
  ```json
  {"signals": [{"question": "...", "confidence": 0.54, "volume_usd": 12345, "source": "polymarket"}]}
  ```
- Self-degrades to empty signals on network failure (safe for CI)

### 4.2 NEW: `alpha_engine/sports_arbitrage_scanner.py`
- Connects to `ejaguiar1_sportsbet` via `pymysql` (mirrors `db_config.php` credentials)
- Queries `lm_sports_odds` for upcoming games (48h window)
- For each (event, market), finds best price per outcome across books
- If sum of implied probabilities < 1.0, flags arbitrage
- Highlights when OLG or Betway is the best price (Canadian-legal execution)
- Outputs `backfill/sports_arbitrage_alerts.json`

### 4.3 NEW: `alpha_engine/sports_situational_edge.py`
- `SituationalEdgeEngine` class with methods:
  - `adjust_nba_prob()` — rest differential, B2B penalty
  - `adjust_nhl_prob()` — B2B, goalie fatigue
  - `adjust_mlb_prob()` — divisional, low total, home dog
  - `adjust_nfl_prob()` — divisional home dog +3, wind
  - `adjust_soccer_draw_prob()` — low-scoring league draw bias
- All adjustments are bounded [0.05, 0.95] to avoid extreme probabilities

### 4.4 UPDATED: `alpha_engine/sports_edge_finder.py`
**Before:** Mock data, async stubs, `get_true_probability()` returned constant 0.55.
**After:**
- Sync `pymysql` connection to read `lm_sports_odds`
- Fuzzy-matches Polymarket signals to DB events by team name
- Applies situational adjustments per sport
- Calculates EV = (true_prob * (decimal_odds - 1)) - (1 - true_prob)
- Returns sorted list of +EV edges with book, event, outcome, and PM match flag

### 4.5 UPDATED: `alpha_engine/sports_betting_edge.py`
**Before:** Placeholder scraper stubs, no DB connection, mock picks.
**After:**
- Orchestrates PM sync + arbitrage scan + value-bet scan
- CLI with `--sport`, `--min-ev`, `--no-arb`, `--output`
- Outputs unified JSON compatible with downstream consumers

### 4.6 NEW: `.github/workflows/sports-prediction-market-sync.yml`
- Runs `sports_prediction_market_sync.py` at 10am and 4pm EST
- Commits output JSON to repo with `[skip ci]`
- Zero-cost (no paid API keys)

### 4.7 UPDATED: `live-monitor/sports-betting.html`
- Disclaimer now explicitly lists **OLG ProLine+** and **Betway**
- Added "Prediction Market Integration (Live)" section in Research tab describing:
  - Polymarket Gamma API sync
  - Arbitrage scanner
  - Situational edge engine

---

## 5. Testing & Verification

### 5.1 Local Python tests
```bash
# 1. PM sync (no DB needed)
python3 alpha_engine/sports_prediction_market_sync.py --verbose

# 2. Arb scanner (needs DB credentials or env vars)
python3 alpha_engine/sports_arbitrage_scanner.py --verbose

# 3. Full edge scan
python3 alpha_engine/sports_betting_edge.py --sport basketball_nba --min-ev 0.02 --verbose
```

### 5.2 Expected outputs
- `backfill/sports_prediction_market_signals.json` — non-empty `signals` array when sports markets are live on Polymarket
- `backfill/sports_arbitrage_alerts.json` — `arbitrages` array (usually empty in efficient markets, which is correct)
- Console output shows `Value bets: N` where N depends on current odds

### 5.3 PHP compatibility
- `sports_picks.php` already loads `sports_prediction_market_signals.json` from `backfill/` or `alpha_engine/data/`
- No PHP changes required — the JSON contract is unchanged

---

## 6. Honest Limitations

1. **Polymarket coverage gaps:** Daily game moneylines exist for NBA/NHL playoffs and major soccer, but regular-season MLB/NFL game markets are sparse. The system falls back to devigged consensus when PM is missing.
2. **Kalshi not yet integrated:** Requires RSA-PSS authentication. Planned for Phase 2 if prediction-market coverage needs expansion.
3. **Situational data requires ESPN scrapers:** Rest-day and injury adjustments depend on existing `lm_{sport}_schedule` tables. If scrapers are stale, situational edges default to neutral.
4. **No automated execution:** The stack is still paper-trading / signal generation only. Arbitrage alerts are informational.
5. **"High-probability wins" are not guaranteed:** The correct framing is "more stable +EV detection with transparent disagreement signals." Markets are efficient; any edge is small and noisy.

---

## 7. PR Checklist

- [x] `alpha_engine/sports_prediction_market_sync.py` created and tested
- [x] `alpha_engine/sports_arbitrage_scanner.py` created and tested
- [x] `alpha_engine/sports_situational_edge.py` created and tested
- [x] `alpha_engine/sports_edge_finder.py` rewritten with real DB integration
- [x] `alpha_engine/sports_betting_edge.py` rewritten as orchestrator
- [x] `.github/workflows/sports-prediction-market-sync.yml` created
- [x] `live-monitor/sports-betting.html` updated (disclaimer + Research tab)
- [x] `updates/2026-04-25-sports-betting-prediction-market-edge-integration.md` written
- [ ] E2E: Verify `sports_picks.php?action=today` shows `prediction_market_*` fields after CI sync
- [ ] E2E: Verify `sports_arbitrage_scanner.py` connects to production DB without credential issues

---

## 8. References

- `docs/SPORTS_EDGE_OLG_BETWAY_PM_INTEGRATION.md` — earlier integration plan (superseded by this implementation)
- `live-monitor/olg_prolineplus_scraper.py` — working OLG scraper
- `live-monitor/betway_ca_scraper.py` — working Betway scraper
- `live-monitor/api/sports_picks.php` — PM signal consumer
- `live-monitor/api/sports_value_analyze_lib.php` — devig + EV math
