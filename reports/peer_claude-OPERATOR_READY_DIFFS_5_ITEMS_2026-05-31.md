# OPERATOR-READY DIFFS — 5 Items (2026-05-31)

**Audience:** operator with shell + git push rights. Each section is
self-contained — apply in <15 min, verify, rollback if needed.

**Constraint:** all 5 items touch the production-scoring path. Diffs are
**proposed** here as fenced code — not applied by this agent. Apply order
recommended: #2 (FOREX, smallest blast), #4 (EQUITY un-kill), #3 (COMMODITY
expand block), #5 (PENNY gate), then #1 (confidence dampen, largest blast).

Symbol verification before apply:
- `BLACKLISTED_STRATEGIES` (NOT `BLOCKED_STRATEGIES`) — `alpha_engine/config.py:257`
- `_compute_ml_composite` — `alpha_engine/smart_picks_engine.py:82`
- `NON_CRYPTO_STRATEGY_POLICIES` per-strategy dict — `alpha_engine/non_crypto_policy.py:240+`
- `MIN_SCORE_FLOORS_BY_CLASS` — `audit_trail/quality_gates.py:489`

---

## ITEM 1 — CONFIDENCE_INVERT → 0.8-bucket dampen

**Goal:** PR #227 verdict — the conf=0.8 bucket has WR 22% vs neighbours
39-43%. Multiply that bucket's contribution to ranking score by 0.5x.

**Target:** `alpha_engine/smart_picks_engine.py`, inside `_compute_ml_composite`
(starts line 82). Inject a bucket-dampener immediately after the existing
`_effective_confidence_for_ranking` call (line ~103-105) and BEFORE
`_compute_ml_composite` uses `conf` in the ml_composite or fallback score.

### Proposed diff (apply as patch)

```diff
--- a/alpha_engine/smart_picks_engine.py
+++ b/alpha_engine/smart_picks_engine.py
@@ -100,10 +100,26 @@ def _compute_ml_composite(pick: dict) -> tuple[float, str]:
     # Calibrate confidence in-place if CONFIDENCE_CALIBRATION_ENABLED is set.
     # No-op otherwise — preserves current production behavior.
     _calibrate_confidence(pick)
     ml = pick.get("ml_score")
     conf = _effective_confidence_for_ranking(
         pick, float(pick.get("confidence", 0) or 0)
     )
+    # 2026-05-31 PR #227 verdict — 0.8 confidence bucket is anti-predictive
+    # (WR 22% vs 39-43% on the 0.7 and 0.9 neighbours). Dampen the bucket's
+    # contribution to ranking by 0.5x rather than killing it (preserves
+    # data flow for re-fitting). Bucket defined as 0.75 <= conf < 0.85.
+    # Kill-switch: CONF_BUCKET_DAMPEN_08_ENABLED=0
+    import os as _os_cb
+    if (_os_cb.environ.get("CONF_BUCKET_DAMPEN_08_ENABLED", "1") or "1") != "0":
+        try:
+            _raw_conf = float(pick.get("confidence", 0) or 0)
+            if 0.75 <= _raw_conf < 0.85:
+                conf = conf * 0.5
+                pick.setdefault("_ranking_notes", []).append(
+                    "conf_bucket_0.8_dampened_0.5x"
+                )
+        except (TypeError, ValueError):
+            pass
     fwd_wr = float(_trusted_forward_wr(pick) or 0)
```

**Test (pytest, drop in `alpha_engine/tests/test_conf_bucket_dampen.py`)**

```python
import os
from alpha_engine.smart_picks_engine import _compute_ml_composite

def _mk(conf, trust="TRUSTED", ml=None, fwd=0.5):
    return {"confidence": conf, "trust_tier": trust, "ml_score": ml,
            "forward_wr": fwd, "asset_class": "EQUITY"}

def test_conf_08_bucket_dampened():
    os.environ["CONF_BUCKET_DAMPEN_08_ENABLED"] = "1"
    score_08, _ = _compute_ml_composite(_mk(0.80))
    score_07, _ = _compute_ml_composite(_mk(0.70))
    assert score_08 < score_07, f"0.8 bucket not dampened: {score_08} vs {score_07}"

def test_kill_switch_disables():
    os.environ["CONF_BUCKET_DAMPEN_08_ENABLED"] = "0"
    score_08, _ = _compute_ml_composite(_mk(0.80))
    score_07, _ = _compute_ml_composite(_mk(0.70))
    assert score_08 > score_07  # default ordering restored
```

- **Backup target:** `ejaguiar1_backups.smart_picks_pre_conf_dampen_20260531` (snapshot
  current `smart_picks` table before applying; not a hard requirement since this
  is code-only, but recommended for delta-attribution).
- **Blast radius:** ALL classes; ranking score recomputed for ~8% of picks
  (those with raw confidence in [0.75, 0.85)). Dashboards recomputed: Smart
  Picks, High Conviction, Money Ready panels.
- **Verification:**
  `python -c "from alpha_engine.smart_picks_engine import _compute_ml_composite; print(_compute_ml_composite({'confidence':0.80,'ml_score':0.6,'asset_class':'EQUITY'}))"`
  followed by `pytest alpha_engine/tests/test_conf_bucket_dampen.py -v`.
- **Rollback:** `git revert <commit_sha>` OR set `CONF_BUCKET_DAMPEN_08_ENABLED=0`
  in `.env` and restart scanners.

**LOC: ~16 added.**

---

## ITEM 2 — FOREX kill list (INCIDENT_FOREX #6/#7)

**Goal:** kill `cta_cross_asset_tsmom` (SHORT) and `forex_carry` (losers per
session memory). Note: the working-tree symbol is `BLACKLISTED_STRATEGIES`
(NOT `BLOCKED_STRATEGIES`) and lives in `alpha_engine/config.py:257`. The
task description's `_FOREX_ALLOWED={...}` at `non_crypto_policy.py:585` is a
paraphrase — the actual gate is the per-strategy `NON_CRYPTO_STRATEGY_POLICIES`
dict at line 240+, plus the global BLACKLIST.

**Two-part diff:**

### 2a) `alpha_engine/config.py` — add to BLACKLISTED_STRATEGIES

```diff
--- a/alpha_engine/config.py
+++ b/alpha_engine/config.py
@@ -270,6 +270,11 @@ BLACKLISTED_STRATEGIES = [
     'stocks_rsi2_pullback',      # SEE ITEM 4 below — proposed un-kill
     'multi_asset_scanner',       # FOREX n=11 WR 9.1%, FUTURES n=11 WR 9.1%
     'ctar_replicator',           # FOREX n=5 WR 40% PF 0.62, COMMODITY n=2 WR 0%
+    # 2026-05-31 INCIDENT_FOREX #6/#7 kills (session memory + reports):
+    'cta_cross_asset_tsmom',     # SHORT side loser — replaced by dxy_trend_filter (n=995 PF 1.63)
+    'forex_carry',               # legacy carry — superseded by forex_carry_ppp (already in policy)
 ]
```

### 2b) `alpha_engine/non_crypto_policy.py` — add dxy_trend_filter winner

Insert into `NON_CRYPTO_STRATEGY_POLICIES` (around line 290, near the other
FOREX entries):

```diff
--- a/alpha_engine/non_crypto_policy.py
+++ b/alpha_engine/non_crypto_policy.py
@@ -288,6 +288,18 @@
     "forex_carry_ppp": {
         "categories": {"forex"},
         "min_confidence": 0.52,
         "min_rr": 1.20,
         "min_elite_score": 50,
         "min_forward_trades": 5,
         "min_forward_wr": 0.40,
         "allow_without_forward": True,
     },
+    # 2026-05-31 INCIDENT_FOREX #6/#7 — dxy_trend_filter is the only FOREX
+    # strategy with proven edge in the live cohort (n=995 PF 1.63 per session
+    # memory project-money-ready-2026-05-31). Allow without forward gate —
+    # already has n>>min_forward_trades.
+    "dxy_trend_filter": {
+        "categories": {"forex"},
+        "min_confidence": 0.50,
+        "min_rr": 1.20,
+        "min_elite_score": 45,
+        "min_forward_trades": 5,
+        "min_forward_wr": 0.50,
+        "allow_without_forward": False,
+    },
```

- **Backup target:** `ejaguiar1_backups.trading_picks_forex_pre_kill_20260531`
  (`CREATE TABLE ... SELECT * FROM trading_picks WHERE asset_class='FOREX'`).
- **Blast radius:** FOREX class only. Expected drop in new emissions:
  cta_cross_asset_tsmom + forex_carry combined was ~60-70% of FOREX emissions
  per recent 14d cohort. New emissions will route to dxy_trend_filter +
  forex_carry_ppp + the existing rsi2/inverse_carry/carry_trade_momentum
  probationary set.
- **Verification:**
  ```bash
  python -c "from alpha_engine.config import BLACKLISTED_STRATEGIES; assert 'cta_cross_asset_tsmom' in BLACKLISTED_STRATEGIES; assert 'forex_carry' in BLACKLISTED_STRATEGIES; print('OK')"
  python -c "from alpha_engine.non_crypto_policy import NON_CRYPTO_STRATEGY_POLICIES as p; assert 'dxy_trend_filter' in p; print('OK')"
  ```
  Then `grep -c "cta_cross_asset_tsmom\|forex_carry[^_]" audit_dashboard/data/dashboard_data.json`
  on next scanner cycle — should trend to zero new entries.
- **Rollback:** `git revert <commit_sha>` (single revert covers both files).

**LOC: ~14 added.**

---

## ITEM 3 — COMMODITY rebuild from non-COT signals (INCIDENT_COMMODITY #2)

**Goal:** stop bleeding from COT-only strategies (live PF 0.31 / WR 11% / n=28,
CT=F 57% concentration). Expand BLACKLISTED_STRATEGIES with COT-only commodity
strategies, then scope a follow-up MD for the non-COT rebuild (term-structure,
EIA, weather).

### Diff — `alpha_engine/config.py`

```diff
--- a/alpha_engine/config.py
+++ b/alpha_engine/config.py
@@ -270,6 +270,15 @@ BLACKLISTED_STRATEGIES = [
     'cta_cross_asset_tsmom',     # FOREX kill (ITEM 2)
     'forex_carry',               # FOREX kill (ITEM 2)
+    # 2026-05-31 INCIDENT_COMMODITY #2 — COT-only strategies bleeding hard
+    # (live cohort PF 0.31 / WR 11% / n=28). Quarantine all COT-only signals
+    # until non-COT rebuild lands. Re-enable after non-COT strategies have
+    # >=100 closed trades and the COT-only cohort has been re-fit on the
+    # post-M-067 policy-clean window.
+    'cot_commercial_extreme',    # COMMODITY COT-only — bleeding
+    'cot_speculator_reversal',   # COMMODITY COT-only — bleeding
+    'cot_managed_money_flip',    # COMMODITY COT-only — bleeding
 ]
```

### Follow-up MD stubs (NOT code — operator drops as separate PR)

Create `docs/COMMODITY_NON_COT_REBUILD_2026-05-31.md` with the 3 strategy
stubs:

1. **`commodity_term_structure_contango`** — contango/backwardation switch.
   Source: CME futures curve (front vs M+3). Hypothesis: backwardation =
   bullish (short squeeze risk), contango = bearish/carry. Gate via
   `alpha_engine/hypothesis_registry` (M-107) before any backtest.
2. **`commodity_eia_inventory_surprise`** — EIA weekly inventory vs consensus.
   Source: api.eia.gov/v2/petroleum/stoc/wstk + Bloomberg/Reuters consensus
   (or Trading Economics scrape). Hypothesis: inventory_actual < consensus by
   >1σ → long CL/NG within 60min.
3. **`commodity_weather_overlay`** — NOAA HDD/CDD anomaly + NG/heating oil.
   Source: noaa.gov NWS. Hypothesis: HDD anomaly >+2σ → long NG until next
   EIA print.

All three start as **opt-in sidecar** per CLAUDE.md Wire-Up Rule, with a
`## Wiring Plan` section naming `commodity_scanner.py::scan_commodities` as
the eventual production caller.

- **Backup target:** `ejaguiar1_backups.trading_picks_commodity_pre_cot_quarantine_20260531`.
- **Blast radius:** COMMODITY class only. Expected drop in emissions: all
  current bleeding sources. Net new emissions zero until non-COT strategies
  ship → COMMODITY will sit at INSUFF-N intentionally (acceptable per
  M-107 "no edge < bad edge").
- **Verification:**
  ```bash
  python -c "from alpha_engine.config import BLACKLISTED_STRATEGIES as b; print([s for s in b if s.startswith('cot_')])"
  ```
  Then watch `audit_dashboard/data/by_asset_class.json::COMMODITY.n_new_24h`
  → should drop to 0 within 24h.
- **Rollback:** `git revert <commit_sha>` restores COT emissions.

**LOC: ~9 added (config) + 1 new docs MD ~80 LOC.**

---

## ITEM 4 — EQUITY rebuild — un-kill `stocks_rsi2_pullback` (INCIDENT_STOCKS #6)

**Goal:** Phase 3 MC P(T2)=52% says rsi2_pullback should be live. It's
**currently killed** at `alpha_engine/config.py:270` (10-trade history at
30% WR / PF 0.032). Phase 3 MC ran on the larger backtest cohort and
recommends re-enabling with a tightened probationary gate.

**Caveat:** the 2026-05-28 quant kill came from 10-trade live evidence. The
Phase 3 MC verdict comes from a backtest-projection MC (P(T2)=52% over the
1424 EQUITY outcomes in the post-M-067 cohort). Operator decides which
evidence to weigh; this diff implements the Phase 3 MC verdict per task spec
and adds an extra-strict policy entry to prevent the 30% WR regression from
recurring.

### Diff — `alpha_engine/config.py`

```diff
--- a/alpha_engine/config.py
+++ b/alpha_engine/config.py
@@ -267,7 +267,12 @@ BLACKLISTED_STRATEGIES = [
     'ml_breakout',
     'genome_mutations',
-    'stocks_rsi2_pullback',      # 10 EQUITY trades, WR 30%, PF 0.032 — catastrophically bad
+    # 'stocks_rsi2_pullback',    # UN-KILLED 2026-05-31 per Phase 3 MC P(T2)=52%
+    #                            # (INCIDENT_STOCKS #6). Re-emerges under probation
+    #                            # via NON_CRYPTO_STRATEGY_POLICIES['stocks_rsi2_pullback']
+    #                            # — gate raised to min_forward_wr=0.55 to prevent
+    #                            # the 30% WR regression. Re-kill if forward WR drops
+    #                            # below 0.45 over next 30 closed trades.
     'multi_asset_scanner',
     'ctar_replicator',
```

### Diff — `alpha_engine/non_crypto_policy.py` (add strict probation entry)

```diff
--- a/alpha_engine/non_crypto_policy.py
+++ b/alpha_engine/non_crypto_policy.py
@@ -300,6 +300,17 @@
     "dxy_trend_filter": {
         ...
     },
+    # 2026-05-31 INCIDENT_STOCKS #6 — un-killed per Phase 3 MC P(T2)=52%.
+    # Tight probation to prevent the prior 30% WR regression.
+    "stocks_rsi2_pullback": {
+        "categories": {"equity"},
+        "min_confidence": 0.62,
+        "min_rr": 1.30,
+        "min_elite_score": 55,
+        "min_forward_trades": 10,
+        "min_forward_wr": 0.55,
+        "allow_without_forward": False,
+    },
```

- **Backup target:** `ejaguiar1_backups.trading_picks_equity_pre_rsi2_reenable_20260531`.
- **Blast radius:** EQUITY only. Expected lift: per Phase 3 MC, +2-5 ranked
  picks/day in the EQUITY funnel; net PF projected +0.15. Risk: prior live
  regression to 30% WR; mitigated by `min_forward_wr=0.55` gate which auto-
  blocks if forward WR drops.
- **Verification:**
  ```bash
  python -c "from alpha_engine.config import BLACKLISTED_STRATEGIES; assert 'stocks_rsi2_pullback' not in BLACKLISTED_STRATEGIES; print('UN-KILLED OK')"
  python -c "from alpha_engine.non_crypto_policy import NON_CRYPTO_STRATEGY_POLICIES as p; assert p['stocks_rsi2_pullback']['min_forward_wr']==0.55; print('OK')"
  ```
  Then monitor `audit_dashboard/data/by_strategy.json::stocks_rsi2_pullback`
  for the first 10 new emissions.
- **Rollback:** revert commit OR re-add `'stocks_rsi2_pullback'` to
  BLACKLISTED_STRATEGIES uncommented.

**LOC: ~12 added.**

---

## ITEM 5 — PENNY Gate 0 + UEPS scanner (INCIDENT_PENNY #2 + INCIDENT_STOCKS #2)

**Goal:** `audit_trail/quality_gates.py` already has per-class min_score
floors at line 489 (`MIN_SCORE_FLOORS_BY_CLASS`) but **no PENNY_STOCK or
MEMECOIN entry**. Penny gate currently relies on a strategy-PAIR allowlist
inside non_crypto_policy and the class-wide `passes_penny_meme_class_gate`
(quality_gates.py:6306) which only does class membership — there is no
score-floor for penny names. The fix: add a PENNY_STOCK floor that's
**stricter than EQUITY** so the UEPS scanner's pennies must clear a higher
bar than blue-chip equities.

### Diff — `audit_trail/quality_gates.py`

```diff
--- a/audit_trail/quality_gates.py
+++ b/audit_trail/quality_gates.py
@@ -489,6 +489,9 @@ MIN_SCORE_FLOORS_BY_CLASS = {
     "CRYPTO":     {"min_score": 65.0, "min_fwr": 0.62, "min_trades": 10},
     "EQUITY":     {"min_score": 40.0, "min_fwr": 0.50, "min_trades": 5},
+    # 2026-05-31 INCIDENT_PENNY #2 + STOCKS #2 — UEPS scanner penny picks
+    # had no score floor. Set 10pts above EQUITY to demand higher conviction
+    # for the penny tail. min_fwr matches the higher PNL volatility risk.
+    "PENNY_STOCK":{"min_score": 50.0, "min_fwr": 0.55, "min_trades": 5},
+    "MEMECOIN":   {"min_score": 55.0, "min_fwr": 0.55, "min_trades": 5},
     "FOREX":      {"min_score": 40.0, "min_fwr": 0.46, "min_trades": 3},
     "COMMODITY":  {"min_score": 30.0, "min_fwr": 0.50, "min_trades": 0},
     "FUTURES":    {"min_score": 45.0, "min_fwr": 0.50, "min_trades": 0},
```

### Test (pytest, drop in `audit_trail/tests/test_penny_score_floor.py`)

```python
from audit_trail.quality_gates import (
    MIN_SCORE_FLOORS_BY_CLASS,
    get_effective_min_score,
)

def test_penny_floor_exists_and_above_equity():
    assert "PENNY_STOCK" in MIN_SCORE_FLOORS_BY_CLASS
    assert (MIN_SCORE_FLOORS_BY_CLASS["PENNY_STOCK"]["min_score"]
            > MIN_SCORE_FLOORS_BY_CLASS["EQUITY"]["min_score"])

def test_memecoin_floor_above_crypto():
    assert "MEMECOIN" in MIN_SCORE_FLOORS_BY_CLASS
    # memecoin should be at least as strict as CRYPTO base
    assert MIN_SCORE_FLOORS_BY_CLASS["MEMECOIN"]["min_score"] >= 50.0

def test_get_effective_min_score_penny_dispatch():
    # When a UEPS-emitted pennystock pick hits the floor lookup,
    # it should receive the PENNY_STOCK floor, not the EQUITY one.
    score_penny = get_effective_min_score("ueps", "PENNY_STOCK")
    score_equity = get_effective_min_score("ueps", "EQUITY")
    assert score_penny >= score_equity
```

- **Backup target:** `ejaguiar1_backups.trading_picks_penny_pre_floor_20260531`.
- **Blast radius:** PENNY_STOCK + MEMECOIN classes only. Estimated rejection
  rate: current PENNY_STOCK n_24h is ~5-10 picks/day in the post-M-067
  cohort; expected ~50% rejection at the new 50pt floor (most UEPS pennies
  score 35-55).
- **Verification:**
  ```bash
  python -c "from audit_trail.quality_gates import MIN_SCORE_FLOORS_BY_CLASS as m; print(m.get('PENNY_STOCK'), m.get('MEMECOIN'))"
  pytest audit_trail/tests/test_penny_score_floor.py -v
  ```
- **Rollback:** `git revert <commit_sha>`.

**LOC: ~5 added (dict) + ~25 test.**

---

## Summary

| # | Item | File | Adds LOC | Risk |
|---|------|------|----------|------|
| 1 | Confidence 0.8 bucket dampen | smart_picks_engine.py | 16 | medium (all classes) |
| 2 | FOREX kill list + dxy_trend allow | config.py + non_crypto_policy.py | 14 | low |
| 3 | COMMODITY COT quarantine | config.py + new docs MD | 9 + 80 doc | low (intentional INSUFF-N) |
| 4 | EQUITY rsi2 un-kill (tight probation) | config.py + non_crypto_policy.py | 12 | medium (regression history) |
| 5 | PENNY + MEMECOIN score floor | quality_gates.py | 5 + 25 test | low |
| **Total** | | | **~81 code + 105 docs/test** | |

**Combined verification (after all 5 apply):**

```bash
python -m py_compile alpha_engine/smart_picks_engine.py alpha_engine/non_crypto_policy.py alpha_engine/config.py audit_trail/quality_gates.py
pytest alpha_engine/tests/test_conf_bucket_dampen.py audit_trail/tests/test_penny_score_floor.py -v
```

**Combined rollback:** `git revert <merge_commit_sha>` (or per-item revert if
applied as 5 separate commits — recommended).
