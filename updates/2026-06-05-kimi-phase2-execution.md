# KIMI Phase 2 Execution — 2026-06-05

**Author**: KIMI (Claude Code CLI) + 4 parallel subagents  
**Branch**: `pr/money-ready-bridge-truth`  
**Scope**: Clean ledger build, feature signal emitters, PMC paper pilot, TP/SL asymmetry root cause  
**Companion docs**: `MASTERPLAN_JUNE52026_KIMI.MD`, `updates/2026-06-05-at-pick-outcomes-tp-sl-misclassification-root-cause.md`

---

## 1. TP/SL Asymmetry — ROOT CAUSE FOUND & FIXED

### The Smoking Gun

The "impossible" TP_HIT 92.4% WR vs SL_HIT 4.5% WR was **100% caused by a single bad batch**: `resolver_version = 'signflip_purge_20260'`.

| Issue | Count | Detail |
|-------|-------|--------|
| TP_HIT with negative PnL | 222 | Labeled TP_HIT but avg PnL -10.0%, down to -98.98% |
| SL_HIT with positive PnL | 145 | Labeled SL_HIT but avg PnL +9.54%, up to +93.59% |
| **All other versions** | **0 misclassifications** | universal_v2, backfill_2026-06-01, backfill_widened all pristine |

**Root cause**: `sign_flip_purge.py` (run 2026-06-03) fixed `status` and `pnl_pct` signs but **never updated `resolution_method`**. For rows where the original bug swapped exit labels, the purge fixed PnL but left the wrong label.

**Fix executed** (live MySQL):

```sql
UPDATE at_pick_outcomes SET resolution_method = 'SL_HIT'
WHERE resolver_version = 'signflip_purge_20260' AND resolution_method = 'TP_HIT' AND pnl_pct < 0;
-- 222 rows fixed

UPDATE at_pick_outcomes SET resolution_method = 'TP_HIT'
WHERE resolver_version = 'signflip_purge_20260' AND resolution_method = 'SL_HIT' AND pnl_pct > 0;
-- 145 rows fixed
```

**Post-fix verification**: June+ data was already 100% clean (0 misclassifications). The all-time stats are now trustworthy.

---

## 2. Clean Ledger Built (`trading_picks_v2` + `at_pick_outcomes_v2`)

Created by `tools/build_clean_ledger_v2.py`:

| Table | Rows | Clean | Banned | Backfill | Duplicate | Stale | Split |
|-------|------|-------|--------|----------|-----------|-------|-------|
| `trading_picks_v2` | 74,314 | 38,182 | 11,901 | 1 | 18,791 | 5,437 | 2 |
| `at_pick_outcomes_v2` | 38,017 | — | — | — | — | — | — |

**Clean picks**: 38,182 (51.4% of raw) — deduped, source-banned, split-adjusted, backfill-quarantined.

**Key filters applied**:
- `was_banned=1` → excluded (poison sources)
- `exit_reason LIKE '%BACKFILL%'` → excluded
- `ABS(pnl_pct) > 1000` → excluded
- `reverse_split_affected=1` → excluded
- `status='ABANDONED' AND exit_reason='STALE_TIMEOUT'` → excluded
- Duplicate `(symbol, direction, DATE(signal_timestamp))` → keep first only

---

## 3. Non-LLM Feature Emitters Deployed

Generated live picks in `alpha_engine/data/feature_signals_20260605.json`:

### Funding Rate Mean Reversion (5 picks)
| Symbol | Direction | Entry | TP | SL | Funding Rate |
|--------|-----------|-------|-----|-----|--------------|
| AERGOUSDT | LONG | 0.0437 | 0.0451 | 0.0429 | -0.985% |
| SKHYNIXUSDT | SHORT | 1344.3 | 1304.0 | 1371.2 | +0.610% |
| HOMEUSDT | LONG | 0.0487 | 0.0502 | 0.0478 | -0.524% |
| VICUSDT | LONG | 0.0459 | 0.0473 | 0.0450 | -0.495% |
| GODSUSDT | LONG | 0.0628 | 0.0647 | 0.0616 | -0.467% |

**Logic**: Extreme funding (>0.1% / 8h) implies overleveraged crowd → fade it.

### VIX Regime (1 pick)
| Symbol | Direction | Entry | TP | SL | Regime |
|--------|-----------|-------|-----|-----|--------|
| SPY | LONG | 757.09 | 787.37 | 738.16 | VIX9D (13.41) < VIX (15.40) → risk-on |

### Futures Term Structure (1 pick)
| Symbol | Direction | Entry | TP | SL | Spread |
|--------|-----------|-------|-----|-----|--------|
| CL=F | LONG | 92.72 | 98.28 | 89.01 | Backwardation 13.3% (front vs 6-mo) |

---

## 4. Prediction Market Consensus Paper Pilot

Created `tools/prediction_market_consensus_pilot.py` + `verified_strategies/paper_pilot/prediction_market_consensus_pilot.json`.

**Current stats (from DB)**:
- **N = 110 resolved picks**
- **WR = 79.1%**
- **Avg PnL = +2.35%**
- **Total PnL = +258.6%**

This is the **single genuine candidate** in the entire database. The pilot tracks:
- New forward picks automatically
- Running WR, PF, avg PnL, max drawdown
- `promotion_ready=true` threshold: forward n>=50, WR>=60%, PF>=1.5

---

## 5. Files Created / Modified

| File | Action | Purpose |
|------|--------|---------|
| `tools/build_clean_ledger_v2.py` | Created | Build trading_picks_v2 + at_pick_outcomes_v2 |
| `tools/feature_signals/funding_rate.py` | Created | Binance funding rate extreme emitter |
| `tools/feature_signals/term_structure.py` | Created | Futures contango/backwardation emitter |
| `tools/feature_signals/vix_regime.py` | Created | VIX9D/VIX regime classifier |
| `tools/feature_signals/orchestrator.py` | Created | Aggregate all feature sleeves |
| `tools/prediction_market_consensus_pilot.py` | Created | PMC forward pilot tracker |
| `alpha_engine/data/feature_signals_20260605.json` | Created | 7 live feature-signal picks |
| `verified_strategies/paper_pilot/prediction_market_consensus_pilot.json` | Created | 525KB historical PMC track record |
| `updates/2026-06-05-at-pick-outcomes-tp-sl-misclassification-root-cause.md` | Created | TP/SL bug root cause analysis |
| `investigate_tp_sl_bug.py` | Created | TP/SL investigation script |
| `tp_sl_bug_report.json` | Created | TP/SL evidence data |
| `at_pick_outcomes` (MySQL) | Modified | 367 misclassifications fixed |

---

## 6. Verification Commands

```bash
# Confirm TP/SL fix
python3 -c "import pymysql; c=pymysql.connect(host='mysql.50webs.com',user='ejaguiar1_stocks',password=get_stocks_creds()["password"],database='ejaguiar1_stocks'); cur=c.cursor(); cur.execute(\"SELECT resolution_method, COUNT(*), SUM(CASE WHEN pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*)*100 as wr FROM at_pick_outcomes WHERE resolution_method IN ('TP_HIT','SL_HIT') GROUP BY resolution_method\"); [print(r) for r in cur.fetchall()]; c.close()"

# Confirm clean ledger
python3 -c "import pymysql; c=pymysql.connect(host='mysql.50webs.com',user='ejaguiar1_stocks',password=get_stocks_creds()["password"],database='ejaguiar1_stocks'); cur=c.cursor(); cur.execute('SELECT clean_status, COUNT(*) FROM trading_picks_v2 GROUP BY clean_status'); [print(r) for r in cur.fetchall()]; c.close()"

# Check PMC pilot
python3 tools/prediction_market_consensus_pilot.py --snapshot

# Regenerate feature signals
python3 -m tools.feature_signals.orchestrator
```

---

## 7. What Remains (Phase 2 Tail → Phase 3)

- [ ] **Wire feature signals into production scanner**: Currently they write to JSON only; need MySQL `feature_signals` table + scanner ingestion
- [ ] **Promotion gate v2**: 8-check gate (n≥100, WR≥55%, PF≥1.4, OOS≥0.85×IS, DSR≥0.80, two-regime, source-ban, TP/SL ratio≤3:1)
- [ ] **30-day live-or-die test**: Start tracking feature-signal picks vs frozen LLM tournament
- [ ] **Prediction market consensus sizing**: If forward n→50 with WR≥60%, enable 0.5% risk pilot
- [ ] **Daily coherence check**: SQL query to flag `resolution_method` vs `pnl_pct` sign mismatches

---

*Generated 2026-06-05 by KIMI Phase 2 execution session.*
