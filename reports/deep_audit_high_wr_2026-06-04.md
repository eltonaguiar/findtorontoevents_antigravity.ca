# Deep Audit — High-WR Performance Verification (2026-06-04)

Operator asked: "look at each performance >80% in detail and verify if its legit, or skewed and if so how is it skewed."

## >80% WR cells found (pre-cleanup)

| Source | Cell | Cleanup | Verdict |
|---|---|---|---|
| Tournament | `gemini_2_5_flash` COMMODITY 94.1% (n=17) | **R6 caught all 16 wins** | Artifact (NG=F $2.65 vs $3, CL=F $77 vs $85 stale-quote LONGs) |
| Tournament | `kimi_direct` ETF 83.3% (n=12) | Within 7% drift; passes R5 | Real but small edge — max pnl 5.2% |
| Production | `cta_golden_cross` ETF 90% (n=20 unique, 270 raw) | INCIDENT #91 dup inflation | **Real edge** on SPY/QQQ uptrend; raw n inflated 5-13x by NULL opened_at dups |
| Production | `claude_ml_moderate_mut` CRYPTO avg +2129% | **Cleaned 1 outlier** (JUPUSDT entry $0.00024) | avg dropped to **+4.98%** post-clean |
| Production | `rapid_momentum_filter_mut` avg +367% | **Cleaned 1 outlier** (ARBUSDT entry $0.000757) | avg dropped to **-0.27%** (losing!) |
| Production | `luxalgo_confluence` avg +113% | **Cleaned 1 outlier** (ARBUSDT) | avg dropped to **0.07%** (no-edge) |
| Production | LINK 4chan picks +826% (n=2) | **Cleaned** | LINK $1 entry was 2020 4chan scrape |

## Round 6: per-class drift threshold for COMMODITY/FUTURES

`tools/ai_tournament/price_tracker.py` updated:
```python
_DRIFT_BY_CLASS = {"ETF": 7.0, "EQUITY": 10.0, "BOND": 5.0, "FOREX": 3.0,
                   "COMMODITY": 12.0, "FUTURES": 12.0, "PENNY": 25.0}
```

Re-audit: **235 of 498 COMMODITY/FUTURES picks mispriced** (47% rate). Same pattern as ETF — energy commodities don't move 25% in a day, so the default 50% threshold missed legit stale-quote artifacts.

**Cumulative MISPRICED: 4,137** across 6 rounds.

## Honest per-class verdict POST-R6

### Tournament (`tournament_picks`):

| Class | n | WR | PF | Verdict |
|---|---:|---:|---:|---|
| COMMODITY | 243 | 53.5% | **1.79** | T2 PASS — only solid edge |
| ETF | 216 | 57.4% | 1.33 | Sub-T2 PF |
| FUTURES | 20 | 50.0% | 1.35 | Small-n T2-shaped |
| CRYPTO | 428 | 46.7% | 1.07 | Sub-50% WR |
| BOND | 314 | 51.3% | 0.69 | Losing edge |
| FOREX | 189 | 54.5% | 0.56 | Confirmed losing |
| EQUITY | 266 | 38.3% | 0.94 | No-edge |
| PENNY | 45 | 42.2% | 0.85 | Sub-50% |

### Production (`at_signal_outcomes` 30d):

| Class | n_raw | WR_raw | Note |
|---|---:|---:|---|
| CRYPTO | 19,673 | 28.4% | Real bleed, 8-43x dup inflation |
| EQUITY | 1,746 | 39.6% | |
| FOREX | 609 | 31.7% | Confirmed losing |
| ETF | 270 | **96.7%** | **INFLATED** by cta_golden_cross dups (n=20 unique not 270) |
| MEMECOIN | 87 | 6.9% | Dead class |
| COMMODITY | 18 | 22.2% | Small n |
| BOND | 13 | 61.5% | Small n |

## Stale-data check on /audit pages

| Page | Last-modified | Status |
|---|---|---|
| /audit/ | 2026-06-04 16:08 GMT | Fresh |
| /audit/ai_leaderboard.html | 2026-06-04 16:03 GMT | Fresh |
| /audit/ai-tournament.html | 2026-06-04 16:03 GMT | Fresh |
| /audit/pick_funnel.html | 2026-06-04 16:22 GMT | Fresh |
| /audit/curated_picks_20260524.html | 2026-05-31 04:36 GMT | **Frozen snapshot** (date in URL) |

## Timestamp format gap (operator ask)

Most JSON `generated_at` fields use UTC ISO 8601 (`2026-06-04T15:57:10+00:00`). Only `incidents_enhancements_feed.json` uses EST format (`2026-06-04 05:52 EDT`). Recommend extending the EST renderer to other dashboard JSONs in a follow-up PR.
