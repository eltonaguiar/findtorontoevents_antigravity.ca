# Multi-Asset Prediction Gameplan
> Master reference — 2026-03-11 | Skip crypto (unreliable prediction track record)

## Goal
Generate and track trade picks across **6 asset classes** using our DNA evolution engine, proven strategies, and tournament ranking. Identify the most predictable markets and produce a live leaderboard.

---

## Asset Classes & Reference Files

| # | Asset Class | Reference File | Portfolios | Status |
|---|------------|----------------|------------|--------|
| 1 | **Futures & Index** (ES, NQ, CL, GC, ZN) | [FUTURES_INDEX.md](asset_classes/FUTURES_INDEX.md) | 3 defined | Ready to scan |
| 2 | **Stocks** (Blue-chip + growth) | [STOCKS.md](asset_classes/STOCKS.md) | 2 defined | Ready to scan |
| 3 | **Forex** (Major + cross pairs) | [FOREX.md](asset_classes/FOREX.md) | 2 defined | Ready to scan |
| 4 | **ETFs** (Sector, bond, commodity) | [ETFS.md](asset_classes/ETFS.md) | 2 defined | Ready to scan |
| 5 | **Penny Stocks** (Micro-cap) | [PENNY_STOCKS.md](asset_classes/PENNY_STOCKS.md) | 1 defined | Ready to scan |
| 6 | **Meme Coins** (Sentiment-driven) | [MEME_COINS.md](asset_classes/MEME_COINS.md) | 0 | Deprioritized |

**Crypto (core):** Excluded — our systems have failed to predict it reliably. Existing crypto portfolios remain in monitoring mode only.

---

## Existing Infrastructure

### Strategy Modules (alpha_engine/)
| Module | Strategies | Asset Classes |
|--------|-----------|---------------|
| `equity_strategies.py` | 6 (momentum, mean-rev, breakout, meme, penny, factor) | Stocks, penny |
| `forex_strategies.py` | 6 (carry, London breakout, mean-rev, CCI divergence, session, squeeze) | Forex |
| `connors_rsi2` (in scanner.py) | 1 | Stocks, futures (★★★ PROVEN 75.7% WR) |
| `baby_strategies/` | 200+ experimental | All classes |
| `community_strategies.py` | ~10 per class | Stocks, forex |

### Portfolio Definitions
- **File:** `multi_asset/portfolio_defs.py` — 10 portfolios already defined
- **Schema:** strategy, asset_class, symbols, risk params (SL/TP ATR mult, max hold, max positions, risk %)

### Data Pipeline
- **Yahoo Finance** via `yfinance` — stocks, ETFs, futures, forex
- **Binance** — crypto only (not used for this gameplan)
- **Scanner:** `alpha_engine/scanner.py` — currently crypto-focused, needs multi-asset extension

### Scoring & Ranking
- **Tournament engine:** `alpha_engine/tournament_engine.py`
- **Scoring formula:** Sharpe × 0.4 + Realized P&L × 0.3 + Max-DD⁻¹ × 0.2 + Win-rate × 0.1
- **Live dashboard:** `audit_dashboard/` + consensus dashboard

---

## Predictability Hypothesis (ranked by expected reliability)

| Rank | Asset Class | Expected Grade | Rationale |
|------|------------|---------------|-----------|
| 1 | Futures (ES, NQ) | A / A+ | Deepest liquidity, mean-reversion well-documented, Connors RSI-2 proven |
| 2 | Blue-chip stocks | A- / B+ | Same strategies as futures, slightly more noise |
| 3 | Forex majors | B+ / B | Carry trade decades of alpha, slower-moving, central bank driven |
| 4 | ETFs | B / B- | Follows underlying, sector rotation has modest edge |
| 5 | Penny stocks | C+ / C | High noise, volume breakouts work but inconsistent |
| 6 | Meme coins | D / F | Pure sentiment, no fundamental anchor |

---

## Implementation Phases

### Phase 1: Documentation (NOW)
- [x] Master gameplan (this file)
- [ ] Per-asset reference files with strategies, symbols, risk params, action items

### Phase 2: Scanner Extension
- Extend `alpha_engine/scanner.py` to accept multi-asset data from `yfinance`
- Wire `multi_asset/portfolio_defs.py` into the scanning loop
- Add `multi_asset/scanner.py` as unified entry point

### Phase 3: Automated Scanning
- GitHub Actions workflow running every 30-60 min (market hours only for stocks/futures)
- Output: `multi_asset/data/active_picks.json`

### Phase 4: Tournament
- Feed results into `tournament_engine.py`
- Per-class leaderboard + global leaderboard
- Identify which classes actually produce alpha

### Phase 5: Dashboard
- Extend consensus dashboard or create `multi_asset/dashboard.html`
- Sortable by asset class, score, freshness
- Risk-profile filter (Conservative / Balanced / Aggressive)

### Phase 6: Forward Testing
- 30-day live paper trading per class
- Statistical significance test (p < 0.05) before declaring any class "proven"
- Kill underperformers, scale winners

---

## Related Plans
- [MULTI_ASSET_TOURNAMENT_PLAN.md](MULTI_ASSET_TOURNAMENT_PLAN.md) — Detailed 580-line tournament design
- [ASSET_CLASS_MASTERPLAN_2026-03-11_0004.md](../ASSET_CLASS_MASTERPLAN_2026-03-11_0004.md) — Gemini's parallel plan with scoring formulas

---

## Key Decision: Start with Futures
Connors RSI-2 has **p = 6×10⁻⁶** on SPY. Index futures (ES, NQ) are the closest analogue with deeper liquidity and 23-hour trading. This is our highest-confidence starting point.
