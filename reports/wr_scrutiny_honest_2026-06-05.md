# Honest Win-Rate Scrutiny Report — 2026-06-05

**Purpose:** Establish ground truth on which source systems / strategies have statistically valid edge, suitable for real-money sizing. All numbers are from live DB queries (`ejaguiar1_stocks.trading_picks`, closed_at NOT NULL, 2026+), not from the audit dashboard JSON cache.

---

## Summary Verdict

| Finding | Status |
|---------|--------|
| Audit dashboard "78.9% CRYPTO Smart Picks" | **DISPUTED** — computed on `claude_gainer_st` n=7, WR=0% in live DB |
| `kimi_signal_tracking` 73.3% WR n=146 | **ARTIFACT** — all 146 closes on single date 2026-04-10 (batch import) |
| `prediction_market_agents` 86.5% WR n=96 | **SUSPECT** — recent picks have NULL pnl_pct; overall source WR=1.3% |
| `mega_mutation` 63.9% WR n=296 | **GENUINE** — 39 distinct dates, 8 symbols, HHI=0.128 |
| `alpha_engine` 50.7% WR n=1140 | **PF=0.58 FAIL** — wins less per win than losses per loss |
| 0/9 asset classes at T2 | **CONFIRMED** — no class has n≥100, WR≥50%, PF≥1.5 simultaneously |

---

## Real Closed Picks by Asset Class (closed_at NOT NULL, 2026+)

| Asset Class | n | WR% | PF | Avg% | Verdict |
|-------------|---|-----|----|------|---------|
| CRYPTO | 4,571 | 13.1 | 0.71 | — | FAIL (garbage sources dominate) |
| FOREX | 1,557 | 1.5 | 0.04 | — | FAIL |
| COMMODITY | 657 | 1.4 | 1.33 | — | SUSPECT (PF>1 with 1.4% WR = anomaly) |
| EQUITY | 85 | 23.5 | 0.89 | — | FAIL + INSUFF-N |
| STOCKS | 82 | 52.4 | 0.59 | — | WR ok but PF fail |
| MEME | 54 | 1.9 | 0.04 | — | FAIL |
| ETF | 22 | 0.0 | n/a | — | INSUFF-N + FAIL |

---

## Genuine CRYPTO Edges (source-level, concentration-verified)

### 1. `mega_mutation` — THE REAL EDGE

| Metric | Value | Gate |
|--------|-------|------|
| n (closed, real dates) | 296 | T2 requires ≥100 ✅ |
| WR | 63.9% | T2 requires ≥50% ✅ |
| PF | 3.12 | T2 requires ≥1.5 ✅ |
| Avg PnL/pick | +2.41% | Positive ✅ |
| HHI (symbol) | 0.128 | Gate <0.30 ✅ |
| Date distribution | 39 distinct days, Apr–Jun 2026 | Distributed ✅ |
| Date range | 2026-04-02 → 2026-06-04 | 63 calendar days |

**Symbol breakdown:**

| Symbol | n | WR% | Avg% |
|--------|---|-----|------|
| JUPUSDT | 47 (15.9%) | 85.1 | +4.77 |
| WIFUSDT | 45 (15.2%) | 68.9 | +3.69 |
| AVAXUSDT | 40 (13.5%) | 50.0 | -0.37 |
| DOTUSDT | 39 (13.2%) | 53.8 | +0.02 |
| RENDERUSDT | 37 (12.5%) | 51.4 | +1.39 |
| STXUSDT | 31 (10.5%) | 41.9 | +0.83 |
| ENAUSDT | 30 (10.1%) | 80.0 | +6.16 |
| ADAUSDT | 27 (9.1%) | 77.8 | +2.77 |

**Weak symbols within this source:** STXUSDT (41.9% WR) — consider filtering out.  
**Verdict: mega_mutation PASSES T2 as a whole. Nearest to money-ready of any CRYPTO source.**

### 2. `battleground_luxalgo` (real-closed slice)

- n=129, WR=51.9%, PF=1.76 — passes T2 PF gate; distributed dates
- Has 109 null-close picks in total — those are excluded from these stats

### 3. `ml_crypto_predictor` (real-closed slice)

- n=289, WR=50.9%, PF=1.83 — borderline T2
- Distributed across Mar–Apr 2026 (multiple distinct days)
- Note: overall source has 1517 null-close picks — those dilute it to 0.3% WR total; use only real-closed slice

---

## Garbage Sources — Ban From Production

These source systems have near-0% WR on real closed picks and flood the DB with unresolvable picks:

| Source | n_total | WR_total | null_close_pct | Action |
|--------|---------|----------|----------------|--------|
| `polymarket_whale_tracker` | 1,582 | 0.0% | 100% | **BAN** |
| `short_dominant_engine` | 1,840 | 0.0% | 99.9% | **BAN** |
| `polymarket_momentum` | 389 | 0.0% | 100% | **BAN** |
| `copy_trader_polymarket` | 1,183 | 0.1% | 99.9% | **BAN** |
| `signal_validation` | 353 open | stale=322 | — | **RESOLVE AS ABANDONED** |
| `prediction_market_agents` | 2,731 | 1.3% | 96.5% | **BAN from scoring** |
| `luxalgo_filters` | 2,121 | 0.0% | 3.8% | **BAN** |

---

## Stale OPEN Picks (ghost picks polluting stats)

- **CRYPTO**: 878 open, 258 older than 30 days, 326 older than 14 days
- Top stale source: `signal_validation` — 322 of 353 stale (>7d)
- Action: resolve `signal_validation` OPEN picks older than 7 days as ABANDONED

---

## Dashboard Wording Issues

### `/audit` pick_funnel.html "78.9% CRYPTO Smart-Picks"
- **Source in DB:** `claude_gainer_st` strategy `super signal` — n=7, WR=0% in live DB
- **What this number likely is:** stale `pick_summary_stats_14d.json` from a window when n was too small to be meaningful
- **Required fix:** dashboard must show source-system-filtered stats and label them with source + n

### `/audit/ai_leaderboard.html`
- Leaderboard is computed from tournament results (separate `ai_tournament_picks` table)
- 73-91% WR on tournament = resolver artifact (single-snapshot, intrabar replay needed)
- Until intrabar OHLCV replay is complete, all tournament WR claims are **UNVERIFIED**

### `/audit/ai-tournament.html`
- Shows portfolio-level WRs which are all pre-intrabar-fix
- 15 affected portfolios noted in `reports/affected_portfolios_resolver_artifact_2026-06-03.md`

---

## Next Actions to Reach Money-Ready

### Immediate (this session)
1. **OHLCV populate running** — `refresh_crypto_ohlcv.py --execute` started (443 symbols, 30d 1h bars)
2. **Run stale picks resolver** — resolve `signal_validation` OPEN picks >7d as ABANDONED
3. **Add source bans** — add polymarket_whale_tracker, short_dominant_engine, polymarket_momentum to BLOCKED_SOURCE_SYSTEMS

### Next 7 days
4. **Intrabar replay** — once crypto_ohlcv populated, run resolver with `--ohlcv` flag on 2026+ picks
5. **Recalculate mega_mutation PF** — post-intrabar-replay to confirm PF>1.5 holds
6. **Paper-pilot wiring** — wire mega_mutation as the primary forward pilot sleeve

### 30-day target
7. **mega_mutation n → 200** — at current pace (~5/day), n=200 reachable in ~20 days
8. **T2 certification** — binomial p-value test on WR=64% with n=200: p << 0.001

---

## Methodology Note

All stats computed via:
```sql
WHERE status NOT IN ('OPEN','ABANDONED','FLAT')
  AND closed_at IS NOT NULL
  AND closed_at > '2026-01-01'
```

This excludes:
- Picks with NULL closed_at (backfill/unresolved)
- Picks marked ABANDONED, FLAT (correctly excluded from WR)
- Pre-2026 data (before current strategy generation era)

**Do not cite numbers from this report for pre-2026 periods or from JSON cache files older than 24h.**

---

*Generated: 2026-06-05 | Source: live `ejaguiar1_stocks.trading_picks` DB queries*
