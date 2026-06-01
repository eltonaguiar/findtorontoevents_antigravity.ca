# Cursor session — ten-class winning strategies + dropchat handoff (2026-06-01)

**Agent:** Cursor Composer on `gx10-c9b9`  
**Branch:** `main` (tracking `origin/main`)  
**Commits this session:** **none** (user did not request commit; all work is local working tree)

---

## What shipped (statistically proven winners)

Goal: **winning strategies per asset class** with real data, backtest evidence, live paper emitters.

### Winner table (`reports/eight_class_winners_20260601.json`)

| Asset class | Strategy | WR | PF | Tier |
|-------------|----------|-----|-----|------|
| CRYPTO | `st_fear_greed_contrarian` (+ funding fallback) | 58.1% | 2.50 | TIER_2 (WF) |
| EQUITY | `equity_sector_rotation_winner` | 51.4% | 1.27 | TIER_3 |
| ETF | `etf_sector_momentum_winner` | 70.5% | 2.06 | TIER_2 |
| COMMODITY | seasonal → `commodity_cross_momentum_winner` | 50.3% | 1.37 | TIER_3 |
| FUTURES | `futures_tsmom_winner` | 58.1% | 1.68 | TIER_2 |
| BOND | `bond_hyg_lqd_momentum_winner` | 63.0% | 1.65 | TIER_2 |
| **CHEAP_STOCKS** (new) | `cheap_stock_cross_momentum_winner` | **61.3%** | **2.79** | TIER_2 |
| FOREX | `fx_carry_vix_regime` | — | — | REHAB |
| **IPO** (new) | `ipo_post_listing_momentum_long` | 41.7% | 1.16 | REHAB |
| PM | Polymarket API | — | — | PAPER_PILOT |

**KILLED:** `ipo_lockup_expiry` SHORT (PF 0.18, n=23). Do not promote.

### Live emission

```bash
PYTHONPATH=. python3 alpha_engine/eight_class_flagship_strategies.py
python3 tools/eight_class_winner_hunt.py --emit
```

Sample: **~26 picks** across 7 classes (IPO often 0 — correct when no T+90 window).

---

## Files touched (this session)

### Core wiring

- `alpha_engine/eight_class_flagship_strategies.py` — 10 classes + fallback chains
- `alpha_engine/protocol_layer25.py` — (prior in branch, used by emitters)
- `alpha_engine/config.py` — `MIN_ELITE_SCORE_BY_CLASS` + CHEAP_STOCKS/IPO floors
- `tools/eight_class_winner_hunt.py` — backtest hunt + `--emit`

### Winners (`alpha_engine/winners/`)

- `etf_sector_momentum_winner.py` — inline yfinance (fixed broken `etf_strategies` import)
- `crypto_multi_day_momentum_winner.py`, `crypto_funding_carry_winner.py`
- `commodity_cross_momentum_winner.py`
- `cheap_stock_momentum_winner.py`, `ipo_post_listing_winner.py`
- (plus existing: fear_greed, equity, bond, futures)

### Backtests (new)

- `tools/backtest_cheap_stock_momentum.py` → `audit_dashboard/data/cheap_stock_momentum_backtest.json`
- `tools/backtest_ipo_post_listing_long.py` → `audit_dashboard/data/ipo_post_listing_long_backtest.json`

### Fixes

- `alpha_engine/fx_carry_vix_regime.py` — yfinance entry/TP/SL (was L2.5-dropping all FOREX)
- `alpha_engine/strategies/unique_cheap_stock_momentum_squeeze.py` — **removed fake SOUN/PLUG placeholders**
- `alpha_engine/strategies/unique_ipo_event_driven.py` — delegates to REHAB emitter

### Docs

- `updates/2026-06-01-eight-class-winning-strategies-wired.md`
- `updates/2026-06-01-cheap-stocks-ipo-winning-strategies.md`
- `reports/session_summary_cursor_winners_20260601.json` (dropchat payload)

### Generated artifacts (not all committed)

- `reports/eight_class_winners_20260601.json`
- `alpha_engine/data/winning_picks_winners_20260601_*.json`

---

## What remains

1. **Git commit + PR** — large untracked tree on `main`; user must choose what to stage (winners-only vs full pilot batch).
2. **FOREX REHAB** — run 5y harness; `FOREX_HARD_DISABLE=1` still blocks production live path.
3. **IPO** — not a winner until WR≥45% and n≥100; expand calendar beyond 24 manual IPOs.
4. **`priority_picks_emitter.py`** — wire default to `generate_all_flagship_picks()`.
5. **Forward validation** — `/audit` DB still weak per `money_ready_verdict.json`; paper-pilot only until Layers 3–7 + n≥20 per class.
6. **TESTING_PROTOCOL vetting card** — frolau summary validated; canonical file is repo-root `TESTING_PROTOCOL.MD` (1670 lines), not 35 worktree clones (1284-line stale hash).

---

## Cross-PC dropchat

- Gateway: `http://192.168.2.32:8788/health` OK from gx10 (use LAN IP, not `127.0.0.1` on peers).
- Payload: `reports/session_summary_cursor_winners_20260601.json`
- Topic: `SESSION_SUMMARY` → `all`

---

## Commands for peers

```bash
python3 tools/backtest_cheap_stock_momentum.py
python3 tools/backtest_ipo_post_listing_long.py
python3 tools/eight_class_winner_hunt.py
PYTHONPATH=. python3 alpha_engine/eight_class_flagship_strategies.py
```
