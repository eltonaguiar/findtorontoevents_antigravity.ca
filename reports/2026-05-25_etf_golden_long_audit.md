# ETF "Golden Long" Autopsy — SOXX & XLK

**Date:** 2026-05-25
**Trigger:** User report that SOXX + XLK are flagged as "golden long trades" on `findtorontoevents.ca/audit` while both are losing live.
**Verdict (TL;DR):** The "golden" appearance is **NOT** earned via the closed-ledger GOLDEN/VERIFIED edge index. The combo `(etf_sector_momentum, XLK)` has **n=1 / 0 wins / 1 loss** in the closed ledger — it cannot pass the GOLDEN gate (which needs n>=5 / WR>=60% / PF>=2.0). The yellow glow the user is seeing is almost certainly the `display_tier='ELITE'` row-styling cascade in `audit_dashboard/template.html:8786` (gold gradient + inset gold bar) layered with the GOLDEN row-class CSS. The label is **NOT a closed-ledger statistical edge endorsement** — it's a forward-WR heuristic on a tiny sample. The picks are also overshadowed by the fact that **every closed XLK position from this exact strategy lost (1/1 LOST, no wins).**

---

## 1. The Currently OPEN SOXX/XLK Picks (DB `trading_picks`, status='OPEN', as of 2026-05-25 01:19Z)

| # | Symbol | Source System            | Strategy             | Dir  | Conf | Elite | Entry  | TP       | SL       | Created (UTC)       |
|---|--------|--------------------------|----------------------|------|------|-------|--------|----------|----------|---------------------|
| 1 | XLK    | etf_all_strategies       | etf_sector_momentum  | LONG | 0.63 | 50    | 180.39 | 189.7508 | 174.7735 | 2026-05-25 01:19:35 |
| 2 | XLK    | etf_all_strategies       | etf_sector_momentum  | LONG | 0.63 | 50    | 180.39 | 189.7508 | 174.7735 | 2026-05-24 18:35:57 |
| 3 | XLK    | etf_all_strategies       | etf_sector_momentum  | LONG | 0.63 | 50    | 180.39 | 189.7508 | 174.7735 | 2026-05-23 18:33:34 |
| 4 | XLK    | etf_all_strategies       | etf_sector_momentum  | LONG | 0.63 | 50    | 180.98 | 190.3408 | 175.3635 | 2026-05-22 18:51:28 |
| 5 | XLK    | new_equity_commodity_s   | sector_rotation_etf  | LONG | 0.63 | 50    | 181.15 | 190.46   | 175.57   | 2026-05-22 15:47:15 |

**SOXX active in dashboard JSON (`audit/data/dashboard_data.json::picks.active_raw`):**
- SOXX | `kimi_riseoftheclaw` | `rs-breakout-scout` | LONG | conf=0.61 | entry=388.29 | current=386.60 | **unrealized = -0.44%**

(No SOXX appears in `picks.active`; the kimi entry is in `active_raw`. The DB shows no current OPEN SOXX from the ETF surface — only TIME_EXIT history.)

Critical facts:
- All 5 OPEN XLK picks are **duplicates** of one signal (same entry/TP/SL, fired daily by two source-systems). 4 are from `etf_sector_momentum`, 1 from `sector_rotation_etf`.
- `category` column is **blank/NULL** for these rows — they're not even properly classified as ETF in the DB.
- Confidence 0.63 / elite_score 50 — neither is high; both are below the typical "Money Ready" thresholds.

---

## 2. Where the "Golden" Label Comes From — Gate Citations

The audit page surfaces three orthogonal "looks golden" pathways. SOXX/XLK do **NOT** qualify for the strictest one (closed-ledger GOLDEN); they only qualify for forward-WR-based tier styling.

### 2a. Closed-Ledger GOLDEN/VERIFIED — `audit_dashboard/template.html:2608-2622`

```js
// Gate (template.html:2613)
if (cs && cs.n >= 5 && cs.losses >= 1 && cs.wr >= 60 && cs.pf != null && cs.pf >= 2.0) {
  goldenCombos[ck] = cs;   // (strategy, symbol) — GOLDEN
}
// VERIFIED strategy-level (template.html:2620)
if (ss && ss.n >= 30 && ss.losses >= 1 && ss.wr >= 55 && ss.pf != null && ss.pf >= 1.5) {
  verifiedStrats[sk] = ss;
}
```

Closed-ledger reality for these combos (full all-time, query: `SELECT ... WHERE strategy='X' AND status IN ('WON','LOST')`):

| (strategy, symbol)              | n | W | L | WR    | PF   | Verdict        |
|---------------------------------|---|---|---|-------|------|----------------|
| etf_sector_momentum × XLK       | 1 | 0 | 1 | 0.0%  | 0.00 | **FAIL GOLDEN** (n<5, WR<60, PF<2) |
| sector_rotation_etf × XLK       | 0 | 0 | 0 | n/a   | n/a  | **FAIL GOLDEN** (zero closed) |
| etf_sector_momentum (strategy)  | 1 | 0 | 1 | 0.0%  | 0.00 | **FAIL VERIFIED** (n<30) |
| sector_rotation_etf (strategy)  | 0 | 0 | 0 | n/a   | n/a  | **FAIL VERIFIED** (no closes) |

Neither pick can earn the `verified-edge-golden-row` class (`template.html:8796-8800`).

### 2b. `display_tier='ELITE'` row gold-glow — `audit_trail/dashboard_generator.py:17448`

```python
if _dt_strong and _dt_trust == "PROVEN" and _dt_score >= 70 and _dt_fwd_wr >= 65 and _dt_fwd_n >= 10:
    _p["display_tier"] = "ELITE"
```
Rendered at `audit_dashboard/template.html:8786`:
```js
trStyle = ' style="background:linear-gradient(90deg,rgba(251,191,36,0.13) 0%,transparent 70%);box-shadow:inset 5px 0 0 #fbbf24;..."';
```
This is the **most-likely culprit** for the user's "golden" perception. It uses **forward-test 30-day WR** (`strat_fwd_wr`), which can be 65% on n=10 even when the closed-ledger sample says PF=0. Forward WR is path-dependent and inflated by `TIME_EXIT` flat-zero outcomes (we have 39 `leveraged_etf_decay` TIME_EXITs in 90 days).

### 2c. MONEY READY filter — `audit_dashboard/money_ready_filter.js:29-49`

`SUPREME_EDGE_REAL` whitelist: `cot_positioning`, `cftc_cot_commercial_signal`, `ml_enhanced_INJUSDT/FETUSDT/DYDXUSDT/RENDERUSDT`, `stocks_rsi2_pullback`. **Neither `etf_sector_momentum` nor `sector_rotation_etf` is on this list.** If the user toggled MONEY READY, SOXX/XLK would be hidden.

---

## 3. ETF Strategy Stats — Last 90 Days, Closed Only (DB `trading_picks WHERE category='ETF'`)

| Strategy                    | n  | W/L  | WR    | PF   | Avg PnL  |
|-----------------------------|----|------|-------|------|----------|
| extreme_oversold_bounce     | 5  | 0/5  | 0.0%  | 0.00 | -3.10%   |
| vix_reversal                | 3  | 1/2  | 33.3% | 0.02 | -0.01%   |

**There are NO ETF strategies with a credible closed-trade edge in the last 90 days.** Most ETF traffic is `TIME_EXIT` flat-zero outcomes (e.g. `leveraged_etf_decay`: 39 TIME_EXIT vs 0 W / 0 L; `etf_sector_momentum` ALL 12 of the 90d XLK rows are OPEN or TIME_EXIT — only 1 ever resolved, and it LOST). The "edge" is invisible because positions are exiting on time-stop before TP/SL trigger.

This is consistent with `CLAUDE.md` Major Goal #1 status: **"ETF borderline (PF 1.24 / WR 55.2% / n=87, n→100)"** — but that PF/WR is dashboard-aggregate including the inflated TIME_EXIT zeros and CRYPTO bleed-over. Closed-only ETF edge is **negative**.

---

## 4. Verdict — Was the "Golden" Label Justified Ex-Ante?

**NO.** Three converging pieces of evidence:

1. **Closed-ledger combo gate (the canonical GOLDEN definition) is FAILED** for both `(etf_sector_momentum, XLK)` and `(sector_rotation_etf, XLK)`. The template's own strict gate would not paint these GOLDEN.
2. **Strategy-level VERIFIED gate FAILS** (n=1 and n=0 are far below the n>=30 floor).
3. **MONEY READY whitelist EXCLUDES these strategies.**

The "golden look" is the `display_tier='ELITE'` gold-gradient row style — which is a **forward-WR heuristic, not a closed-ledger edge proof.** Forward WR can be inflated by `TIME_EXIT` flat outcomes (which count as neither win nor loss in the standard formula but inflate the denominator of "didn't lose"). With only 1 LOST and 0 WON ever resolved for `etf_sector_momentum`, the live underperformance is **fully consistent with the historical record** — there is no anomaly to debug, only a misleading visual cue.

---

## 5. Top 3 Concrete Fixes

### Fix #1 — Decouple ELITE gold-glow from forward-WR-only signal (template.html:8785-8786)
Add a closed-ledger sanity gate: do NOT apply the ELITE gold gradient unless the pick's `(strategy, symbol)` combo has **at least n>=5 CLOSED trades (WON+LOST, excluding TIME_EXIT)** AND closed-WR >= 50%. Otherwise downgrade to `display_tier='STANDARD'` regardless of forward-WR. This is a 5-line patch in `audit_trail/dashboard_generator.py:17448`.

### Fix #2 — Blacklist `etf_sector_momentum` + `sector_rotation_etf` from active surfacing until n>=10 with WR>=50%
Add to `alpha_engine/strategy_blocklist.py` (or whatever drives `SUPPRESSED_STRATEGIES`). Per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` this requires the mutation-first protocol — but the data is unambiguous: 0/1 ever resolved, all live picks are duplicate emissions of one stale signal from 3 days ago.

### Fix #3 — Surface TIME_EXIT-adjusted strategy stats on the row's EDGE tooltip
The dashboard currently shows "no closed history" indirectly via a dash. Replace with explicit text: `"TIME_EXIT rate: 39/40 = 97.5% — strategy almost never reaches TP/SL; edge unresolvable."` This makes the absence of edge legible to operators without forcing them to read the closed-ledger. Patch site: `audit_dashboard/template.html:8504` (the `tipDash` template).

---

## Reproducer

```bash
# Pull the OPEN SOXX/XLK picks
python3 -c "
import os, pymysql
from pymysql.constants import FIELD_TYPE
cn=pymysql.connect(host='mysql.50webs.com',user='ejaguiar1_stocks',
  password=os.environ['DB_PASS_STOCKS'],db=os.environ['DB_NAME_STOCKS'],
  conv={FIELD_TYPE.NEWDECIMAL: float})
c=cn.cursor(pymysql.cursors.DictCursor)
c.execute(\"SELECT symbol,source_system,strategy,status,pnl_pct,created_at FROM trading_picks WHERE symbol IN ('SOXX','XLK') ORDER BY created_at DESC LIMIT 30\")
for r in c.fetchall(): print(r)
"

# Inspect the GOLDEN gate
grep -n "n >= 5 && cs.losses >= 1 && cs.wr >= 60" audit_dashboard/template.html

# Inspect the ELITE display_tier (the actual gold-row culprit)
grep -n "display_tier..*ELITE\|verified-edge-golden-row" audit_dashboard/template.html audit_trail/dashboard_generator.py
```

---

**Sources cited:**
- `audit_dashboard/template.html:2608-2622` (GOLDEN/VERIFIED gate logic)
- `audit_dashboard/template.html:8785-8800` (row class application)
- `audit_trail/dashboard_generator.py:17448-17455` (display_tier assignment)
- `audit_dashboard/money_ready_filter.js:29-49` (MONEY READY whitelist)
- `ejaguiar1_stocks.trading_picks` (live DB, queried 2026-05-25)
- `audit/data/dashboard_data.json` (dashboard build 2026-05-23 09:23Z)
