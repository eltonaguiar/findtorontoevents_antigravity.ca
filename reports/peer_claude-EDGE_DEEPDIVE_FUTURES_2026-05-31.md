# Edge Deep-Dive — FUTURES (2026-05-31)

**Agent:** claude-opus-4-7 (peer subagent)
**Class:** FUTURES
**Dashboard verdict:** INSUFF_DATA (n=0 closed via `trading_picks.category='FUTURES'` — uppercase)
**Raw DB reality:** n=3,978 raw, n=2,869 clean-closed in `at_raw_picks.asset_class='FUTURES'`
**Live `trading_picks.category='futures'` (lowercase):** n=430 (374 TIME_EXIT, 16 LOST, 3 TP_HIT, 37 OPEN)

---

## 1. Root cause — why the dashboard says n=0

**Three compounding bugs, not one:**

### Bug A — Casing/category-key mismatch (drops 3,548 picks)
- `at_raw_picks.asset_class = 'FUTURES'` (uppercase)
- `trading_picks.category = 'futures'` (lowercase)
- Dashboard verdict reads `trading_picks` with `category='FUTURES'` filter → 0 hits
- Same root family as the EQUITY/`stock`/`stocks` case-mess (memory: `confidence/trust edges 2026-05-31`)
- 3,548 of 3,978 raw picks never make it into the verdict path

### Bug B — Resolver direction-blindness (dir-blind PnL)
Direction × status distribution proves it:

| direction | WON  | LOST | WR%   |
|-----------|------|------|-------|
| LONG      | 1214 | 335  | 78.4% |
| SHORT     | 241  | 1079 | 18.3% |

A working resolver should be roughly symmetric. 78% LONG / 18% SHORT means the resolver is computing `pnl = (exit-entry)/entry` regardless of direction, then labeling WON/LOST by sign without flipping for SHORT. This is the **dir-blind PnL** bug already flagged for db_health in PR #208 — FUTURES has the largest absolute exposure to it.

Confirming artifact: 5 WON rows with `pnl_pct=0.0000` on SHORT side (entry==exit, mislabeled WON).

### Bug C — Corrupt entry-price ingestion (long tail blow-up)
Spot-checked top outliers:
- `YM=F` entry `0.26060000` → exit `49726.00` → `pnl_pct=999999.9999` (entry is corrupt: missing `e+5` or wrong decimal cast)
- `NG=F` entry `0.59504` → exit `3.025` → 408% (entry one order off real NG price ~$2-3 region — still suspect)
- 3 WON rows with `pnl_pct >= 100%`
- `YM=F` mean WON PnL = **7043%** (n=142) → at least one massive outlier dominates the symbol

This pollutes any raw-mean PF/Sharpe computed off `at_raw_picks` without winsorization.

### Reality check after cleanup
Filter to `ABS(pnl_pct)<50` (drops the 3 ingestion-corrupt + bounds heavy tail), clean-closed `was_banned=0 AND was_demoted=0`:
- n=2,864
- Gross win = 8419.84%, Gross loss = 7778.21%
- **PF = 1.08** → **sub-Tier-2** (T2 needs PF>1.5)
- AVG pnl = +0.22% → marginally positive, swamped by tx-cost in real fills

Per-strategy WRs (n>=50, |pnl|<50%, clean):
- `cta_golden_cross_200`: **98.2% (270/275)** — implausible, almost certainly direction-mislabel artifact concentrated in LONGs during 2026 rally
- `futures_connors_rsi2`: 96.1% — same suspicion, but this matches the `trading_picks.futures` strategy with 373 TIME_EXIT / 3 TP_HIT (live picks rarely actually TP)
- `futures_momentum`: 61.2%, avg +0.15% (likely real)
- `cta_cross_asset_tsmom`: 56.2%, avg +1.33%
- `cot_positioning`: 43.4%, avg +0.81%
- `cta_commodity_momentum_term`: 35.7% — likely real signal that the dir-blind bug *under*-reports
- `cftc_cot_commercial_signal`: 9.2% (25/273) — likely real signal **destroyed** by dir-blind bug on SHORTs

**Conclusion:** FUTURES is not "no closed picks." It is **emitting 1,300+ picks/month** that hit the raw-pick table, then **three pipeline bugs hide them from the verdict**. Until A+B+C are fixed, any per-strategy WR/PF reported by an AI from the dashboard is fabricated noise.

---

## 2. Concentration check

Top symbols (raw): ZC=F (516), NG=F (397), SI=F (386), ZW=F (318), ZS=F (314), HG=F (310), GC=F (308), CL=F (302), CT=F (284). HHI on top-10 ≈ 0.105 → **diversified, not concentrated**. Source-system HHI: `alpha_engine_unified` 86% → meta-engine concentration (expected and per-policy not flagged at the strategy level per memory `concentration = strategy not engine`).

---

## 3. Five untried edge angles, ranked by feasibility

| # | Angle                                  | Feasibility | Data avail today                              | Edge thesis                                                                                                                |
|---|----------------------------------------|-------------|-----------------------------------------------|----------------------------------------------------------------------------------------------------------------------------|
| 1 | **VX term-structure (vol carry)**      | HIGH        | yfinance `^VIX`, `VX1!`-`VX2!` via CME proxy  | Sell VX1, buy VX2 when contango > 5% / monthly; mean-reverts 70% historically. Backtestable today, fits existing `vix_reversal` strategy slot. |
| 2 | **Calendar-spread roll yield (CL, NG)**| HIGH        | yfinance front+back: `CL=F` + manual `M`/`N` ticker series | Front-month vs 2nd-month spread predicts roll cost; carry trade buys backwardation, shorts contango. Strategy `contango_roll_yield` already exists (10 picks) — extend universe. |
| 3 | **Macro event window (NFP/CPI/FOMC)**  | HIGH        | FRED scrape + `ES=F` 5-min bars                | First-15-min post-release reversal on ES (institutional fade) — documented edge in CME white papers. Calendar known a week ahead. |
| 4 | **COT extreme z-score (all symbols)**  | MEDIUM      | CFTC weekly disagg COT (free), already partial via `commodity_cot_contrarian` | Extend `cot_positioning` from commodity-only to currencies + rates (ZN, ZB, 6E) at z>2σ percentile. `cot_positioning` already n=640 raw but WR 43% → entry needs the **extreme** condition not "any". |
| 5 | **Crack spread (heat-oil vs gasoline)**| MEDIUM      | yfinance `HO=F` `RB=F` `CL=F`                  | Seasonal 3:2:1 crack widens spring (driving season). Inter-commodity spread already on CME calendar, low correlation with single-leg momentum strats. |

(Inter-market `ES/NQ` rotation and OI-extreme mean-reversion considered but deprioritized: ES/NQ rotation needs minute-bar synced data we don't have clean, OI-extreme requires CFTC OI which is the same source as #4.)

---

## 4. Two concrete strategy proposals

### Proposal A — `vix_term_carry_v1` (highest priority)
- **Entry:** when (VX1-VX2)/VX2 > +0.05 (contango wide) → SHORT VX1 + LONG VX2; reverse when (VX1-VX2)/VX2 < -0.05 (backwardation).
- **TP/SL:** TP at spread mean-reversion to 0, SL at 2σ further dislocation.
- **Holding period:** 3-10 trading days median.
- **Why now:** zero current FUTURES strategy targets vol-carry; orthogonal to the 8 trend/momentum strats already running.
- **Expected n:** ~2-4 picks/week.
- **Wiring:** new file `alpha_engine/vix_term_carry_strategy.py`, register in `alpha_engine_unified.py`, add to `claude_futures_strategy`'s strategy list.

### Proposal B — `cot_extreme_v2` (rescue existing signal)
- **Entry:** weekly CFTC commercial net z-score > +2.0σ → LONG (commercials are smart money, extreme accumulation predicts rally); z < -2.0σ → SHORT.
- **Symbols:** ZN, ZB, 6E, 6J, GC, CL (rates + FX + 2 metals/energy).
- **TP/SL:** TP at z-score reverting to 0, SL at z > 3σ (deeper extreme).
- **Holding period:** 2-6 weeks (matches COT report cadence).
- **Why now:** `cot_positioning` n=640 / WR 43% suggests the signal exists but is being *blunted* by triggering at every z-shift, not extreme z. Tightening to z>2 should raise WR substantially while still emitting ~1/week.
- **Wiring:** modify existing `cot_positioning` thresholds in-place (no new strategy), require explicit before/after backtest in PR.

---

## 5. Recommendation

**Priority order:**

1. **P0 — FIX RESOLVER (Bugs A+B) BEFORE proposing new strategies.** Right now FUTURES is the largest single-class proof of the dir-blind PnL bug. Until the resolver flips sign for SHORT and the casing mismatch is patched, no per-strategy WR/PF for FUTURES is admissible per M-107. This is **prerequisite plumbing** (matches memory `Money-ready 2026-05-31`).

2. **P0 — INGESTION sanitizer (Bug C):** add a guard in `at_raw_picks` insert path: if `ABS(pnl_pct) > 100` flag `was_demoted=1` and log to a corrupt-ingest table. 3 rows polluting raw means + 1 row at 999999.9999% is a flashing red light.

3. **P1 — Validate research-only flag.** Memory says "FUTURES research-only mode set 2026-05-31 morning per `incident_overall_pre_futures_research_only_20260531`." If that incident table marks FUTURES as research-only, picks **are** flowing (430 in `trading_picks`) but **dashboard surfaces them under wrong category**. Confirm the research-only flag actually gates emission, or surface the 430 properly.

4. **P2 — Wire `vix_term_carry_v1` AFTER fixing #1-#3.** Don't introduce new strategies into a pipeline with three known data-integrity bugs.

5. **P2 — Tighten `cot_positioning` thresholds.** Cheap experiment, single-file diff.

**Do NOT promote FUTURES from INSUFF_DATA based on a 98% `cta_golden_cross_200` WR.** That number is the dir-blind bug screaming in the dataset.

---

## Reproducer

```bash
python3 -c "
import pymysql
c=pymysql.connect(host='mysql.50webs.com',user='ejaguiar1_stocks',password='stocks1234560',database='ejaguiar1_stocks',connect_timeout=15)
cur=c.cursor()
cur.execute(\"SELECT direction, status, COUNT(*) FROM at_raw_picks WHERE asset_class='FUTURES' AND status IN ('WON','LOST') GROUP BY direction, status\")
print(cur.fetchall())
"
```

Expected output (dir-blind bug signature):
`[('LONG','WON',1214), ('SHORT','LOST',1079), ('LONG','LOST',335), ('SHORT','WON',241)]`

---

## Linked work / memory

- Memory `Confidence/trust edges 2026-05-31` — category case-mess pattern (`stock`/`stocks`/`equity`); FUTURES adds `FUTURES`/`futures`.
- Memory `Money-ready 2026-05-31` — "plumbing not strategies" diagnosis applies verbatim.
- Memory `SL optimization needs price-path` — do not winsorize-then-tune-TP/SL on FUTURES until intrabar OHLC replay is wired.
- PR #208 (db_health bugs) — overlaps Bug B.
- Incident `incident_overall_pre_futures_research_only_20260531` (backup table referenced in skill memory) — verify before assuming emission is on.
