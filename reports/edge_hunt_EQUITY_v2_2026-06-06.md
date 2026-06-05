# EQUITY Edge Hunt v2 — Analyst Picks, Earnings, Financials Acceleration

**Date:** 2026-06-06  
**Scope:** MeanReversionBB / pf_registry gap, PEAD earnings cache, UEPS fundamentals, dead emitters, live sleeve census  
**Rule:** All numbers below are from live MySQL `at_pick_outcomes`, `pf_registry.json`, `money_ready_verdict.json`, or on-disk JSON unless marked *source file only*.

---

## Executive verdict: **LATENT_EDGE — not money-ready at class level**

| Layer | Verdict | Why |
|-------|---------|-----|
| Class (policy-clean) | **FAIL** | `money_ready_verdict.json` EQUITY: n=45, WR=24.4%, PF=0.26, MDD=75.9%, `top_sleeves=[]` |
| Best resolver sleeve | **T2-candidate** | `MeanReversionBB` in `at_pick_outcomes`: n=175 resolved, WR=54.9%, PF=1.82 |
| Fundamentals (UEPS) | **Overlay only** | 22 real LONG theses; 3y+ horizon, not a swing timing edge |
| PEAD lane | **Blocked by window** | Earnings cache usable; production PEAD gates miss all cached beats |

**Fast path:** isolate `MeanReversionBB` + UEPS quality filter + extended PEAD drift window. Do **not** size on class-level pf_registry until `regime_terminal` and other toxic sleeves are excluded from the EQUITY book.

---

## 1. MeanReversionBB — why missing from `pf_registry`

### Live stats (`ejaguiar1_stocks.at_pick_outcomes`, queried 2026-06-06)

| Slice | n | WR | PF | Notes |
|-------|---|-----|-----|-------|
| EQUITY, WON+LOST only | **175** | **54.9%** | **1.82** | Tier-2 candidate on n/WR/PF |
| EQUITY, incl. EXPIRED | **214** | 44.9% | **1.88** | 39 EXPIRED rows explain n=214 headline |
| CRYPTO (same strategy) | 20 | 65.0% | 2.79 | Blocked class-wide |

Status breakdown (EQUITY): WON=96, LOST=79, EXPIRED=39, OPEN=0.

### Why absent from `pf_registry.json`

Three independent exclusions — any one is sufficient:

1. **Data source mismatch.** `tools/build_pf_registry.py` ingests `*/data/closed_picks.json` files only. `MeanReversionBB` has **zero rows** in `alpha_engine/data/closed_picks.json`. Resolver-grade performance lives in MySQL `at_pick_outcomes`, which pf_registry does not read.

2. **Policy-clean pair block.** `audit_trail/quality_gates.py:2679-2680`:
   ```python
   ("CRYPTO", "MeanReversionBB"),
   ("EQUITY", "MeanReversionBB"),
   ```
   Added 2026-05-19 after 7d WR decay alert (−35pp vs baseline). `build_pf_registry._is_policy_excluded()` layer 3 drops all directions for this pair.

3. **Source-system block.** `multi_asset` is in `BLOCKED_SOURCE_SYSTEMS` (PF 0.32 / WR 45.5% class-wide, 2026-05-14). Scanner tags `source_system="multi_asset_scanner"` — scored −25 globally in `NC_SOURCE_CLASS_SCORE_ADJ`.

`money_ready_verdict.json` EQUITY `top_sleeves: []` and `data_source: "closed_picks"` — so the best live sleeve cannot surface in Money Ready UI today.

### Emission path (`multi_asset/scanner.py`)

```
mean_reversion_bollinger(df, symbol, info)     # scanner.py:837
  → strategy: "mean_reversion_bollinger"
  → scan() loop:2373 sets source_system="multi_asset_scanner", asset_class from cat
  → multi_asset/data/multi_asset_picks.json
  → sync_all_picks_to_mysql.py (JSON_SOURCES line 318)
  → trading_picks / at_pick_outcomes
  → STRATEGY_TRACK_ALIASES in alpha_engine/config.py:2223
       mean_reversion_bollinger → MeanReversionBB
```

Alias applied in `production_scanner.py` at pick-normalization (lines ~5405, ~6289). Template maps the same alias in `LEADERBOARD_STRATEGY_ALIASES`.

**Current state:** strategy is **historically proven in resolver DB** but **policy-blocked** for new EQUITY emissions and **invisible** to pf_registry / money_ready top_sleeves.

---

## 2. Earnings cache — PEAD with extended window (5–30d)

### `data/earnings/*/latest.json` (yfinance, fetched 2026-06-05)

| Ticker | Last beat date | surprise_pct | Days since (as-of 2026-06-06) | In 3d gate | In 30d drift |
|--------|----------------|--------------|-------------------------------|------------|--------------|
| GOOGL | 2026-04-29 | +94.3% | 38 | ✗ | ✗ |
| MSFT | 2026-04-29 | +5.2% | 38 | ✗ | ✗ |
| AAPL | 2026-04-30 | +3.5% | 37 | ✗ | ✗ |
| XYZ | 2026-05-07 | +25.6% | 30 | ✗ | ✓ (edge) |

Next catalysts: Jul 2026 (AAPL Jul-30, MSFT Jul-29, GOOGL Jul-23). No imminent earnings this week.

### Production PEAD modules — window mismatch

| Module | Entry window | Hold | Wired? | Live n |
|--------|-------------|------|--------|--------|
| `equity_pead_strategy.py` | **≤3 days** post-beat (`days_since > 3` → skip) | 30d | Opt-in shadow; `EQUITY_PEAD_ENABLED` env | 0 in outcomes |
| `strategies/pead_equity.py` | **2 days** | short swing | **NOT wired** (wiring plan only) | 0 |
| `at_pick_outcomes` `Earnings Drift` | — | — | sidecar | **n=1, WR=0%** |

**Finding:** Academic PEAD drift runs 30–60d, but both code paths use 2–3d entry gates. With the cached beats above, **only XYZ** qualifies for a 30d continuation window; GOOGL/MSFT/AAPL beats are 37–38d old — missed entirely.

**Extended-window recommendation:** change `equity_pead_strategy.py` `_HOLD_DAYS` companion gate from `days_since > 3` to allow **5–30d post-beat continuation entries** on symbols with surprise ≥5% and positive price drift vs SPY since report. Feed from `data/earnings/*/latest.json` + `EarningsCalendarFetcher` rather than per-ticker yfinance round-trips.

---

## 3. `audit_dashboard/data/ueps_picks.json` — fundamental longs

**Generated:** 2026-06-05T13:27:35Z  
**Universe:** 51 tickers scored → 49 passed filters → **22 LONG**, 0 SHORT, 0 swing

Top ranks (Magic Formula × Piotroski × Acquirer's):

| Rank | Symbol | F-score | ROIC |
|------|--------|---------|------|
| 1 | ADBE | 7 | 45.1% |
| 3 | HD | 6 | 28.7% |
| 4 | MA | 7 | 60.2% |
| 5 | QCOM | 7 | 30.1% |
| 9 | META | 5 | 25.7% |

**Earnings-cache overlap:** GOOGL is in UEPS longs (rank ~mid-pack); AAPL and MSFT are **not** in the 22. XYZ is not in UEPS.

**Role:** conviction overlay / quality gate — `pick_type: long_term_value`, `holding_horizon: 3y+`, thesis-break rules on ROIC/D/E/Altman. Not a substitute for MeanReversionBB timing.

**GHA gap:** `reports/value_screener_runs/2026-06-05.md` shows weekly workflow scored **n=1** universe → 0 picks. Dashboard `ueps_picks.json` (22 picks) came from a separate fuller run (`tools/run_ueps_pickers.py` path). Fix universe fetch in GHA before relying on weekly refresh.

---

## 4. Module status: PEAD, value screener, yahoo analyst

| Module | Status | Evidence |
|--------|--------|----------|
| `equity_pead_strategy.py` | Shadow / opt-in | Doc says OFF; code default `EQUITY_PEAD_ENABLED=1`; 3d window; not in `production_scanner.py` grep |
| `value_screener_runner.py` | **Wired** (weekly GHA) | First production caller for UEPS sidecar; writes `active_picks.json` + reports |
| `yahoo_analyst_consensus` | **KILLED** | `PERMANENTLY_KILLED_STRATEGIES` (`quality_gates.py:1374`); 0% WR history; zombie loop purged per updates |

`strategies/pead_equity.py` documents PF≥1.5 / WR≥50% / n≥50 backtest gate before wire to `_run_equity_scanner()` — gate not met (no production caller).

---

## 5. Other EQUITY sleeves with n≥30 (`at_pick_outcomes`)

| Strategy | n | WR | PF | Action |
|----------|---|-----|-----|--------|
| **MeanReversionBB** | 175 | 54.9% | 1.82 | **Promote** (isolated book) |
| stocks_rsi2_pullback | 81 | 46.9% | 1.22 | **Do not unban** — `banned_strategies.json`; PBO overfit dispute |
| MomentumEMA | 54 | 18.5% | 0.34 | **Kill** |

All other EQUITY strategies in pf_registry policy-clean view: n&lt;30 or PF&lt;1 (e.g. `regime_terminal` n=17 WR=17.6% in pf_registry; **n=0** in `at_pick_outcomes` — ledger vs resolver divergence).

---

## 6. Two-week wire-up plan (real-money picks, not months)

### Week 1 — unblock the proven sleeve

| Day | Action | File / command |
|-----|--------|----------------|
| D1 | **Partial unblock** `("EQUITY", "MeanReversionBB")` from `BLOCKED_ASSET_STRATEGY_PAIRS`; keep CRYPTO block | `audit_trail/quality_gates.py:2680` |
| D1 | Add **EQUITY-only** allowlist emitter: `mean_reversion_bollinger` on blue-chip universe (SPY/QQQ/AAPL/MSFT/GOOGL + UEPS top-10) bypassing global `multi_asset` source block via dedicated `source_system="equity_bb_pilot"` | `multi_asset/scanner.py` + `production_scanner.py` |
| D2 | **Merge resolver stats into money_ready** — extend `_top_money_ready_sleeves()` to read `at_pick_outcomes` when pf_registry row missing | `alpha_engine/money_ready_verdict.py` |
| D2 | Block `regime_terminal` EQUITY emissions (already toxic in pf_registry n=17) | `quality_gates.py` / `eagle_gates.py` |
| D3–D5 | Paper pilot at **0.25×**; TV account TRUSTOURSCORE; require n≥10 new closed with PF&gt;1.2 | `verified_strategies/paper_pilot/` |

### Week 2 — fundamentals + PEAD acceleration

| Day | Action | File / command |
|-----|--------|----------------|
| D6 | Fix value screener GHA universe (n=1 → full S&P-100); refresh `ueps_picks.json` | `.github/workflows/value_screener_weekly.yml` |
| D7 | Extend PEAD entry to **5–30d** post-beat; wire `data/earnings/*/latest.json` as primary surprise source | `equity_pead_strategy.py` |
| D8 | **Confluence gate:** emit PEAD only when symbol ∈ UEPS longs OR surprise ≥10% (GOOGL-class) | new gate in `fundamental_macro_gates.py` or `non_crypto_policy.py` |
| D9–D12 | Resolve 10+ paper trades; if MeanReversionBB 14d WR stays ≥50% and PF≥1.5 → **0.5× live** | monitor via `tools/strategy_tier_tracker.py` |
| D14 | If PEAD paper n≥5 with PF&gt;1.0 on extended window → add as secondary sleeve at 0.15× | — |

### Do NOT (saves capital)

- Re-enable `yahoo_analyst_consensus`
- Unban `stocks_rsi2_pullback` on pf_registry n=5 / 100% WR artifact
- Size on class-level EQUITY verdict (PF 0.26) without sleeve isolation
- Trust n=214 WR=55.6% headline without excluding EXPIRED (true resolved WR=54.9%)

---

## Reproduce

```bash
# EQUITY sleeve census (requires DB creds)
python3 -c "
import sys; sys.path.insert(0,'.')
from tools.db_env import get_stocks_creds
import pymysql
c=get_stocks_creds(raise_on_missing=True)
conn=pymysql.connect(host=c['host'],user=c['user'],password=c['password'],
  database=c['database'],port=c['port'],cursorclass=pymysql.cursors.DictCursor)
cur=conn.cursor()
cur.execute('''SELECT strategy,COUNT(*) n,
  ROUND(100*SUM(status='WON')/COUNT(*),1) wr,
  ROUND(SUM(CASE WHEN pnl_pct>0 THEN pnl_pct ELSE 0 END)/
    NULLIF(ABS(SUM(CASE WHEN pnl_pct<0 THEN pnl_pct ELSE 0 END)),0),2) pf
  FROM at_pick_outcomes WHERE UPPER(asset_class)='EQUITY' AND status IN ('WON','LOST')
  GROUP BY strategy HAVING n>=30 ORDER BY pf DESC''')
for r in cur.fetchall(): print(r)
"

python3 tools/strategy_tier_tracker.py
grep -n "MeanReversionBB" audit_trail/quality_gates.py
```

---

*Generated 2026-06-06. DB query timestamp: live `ejaguiar1_stocks`. No fabricated stats.*
