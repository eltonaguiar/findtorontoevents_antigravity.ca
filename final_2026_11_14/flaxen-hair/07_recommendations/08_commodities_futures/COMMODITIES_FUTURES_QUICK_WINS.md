# Commodities / Futures Quick Wins — MERGED

**Scope:** Commodities / futures (SI=F silver, HG=F copper, KC=F coffee, PL=F platinum, CL=F crude, GC=F gold, ZN=F 10Y T-note, NG=F natural gas)
**Merged sources:** My flaxen-hair audit + peer `finpredict-v4` audit + peer `childlike-airport` proposed fixes
**Date:** 2026-11-14

## Consolidated findings

| # | Finding | Severity | Effort | Files | Source |
|---|---|---|---|---|---|
| CM-1 | PnL unit normalization for futures closed picks (4 verified ×100 mismatches + mixed units) | HIGH | LOW | `multi_asset_closed.json`, `institutional_closed.json`, `quick_wins/shared/normalize_pnl_units.py` | My audit |
| CM-2 | Resolve stale commodity open picks (all 2026-11-12, `forward_test_only`, null PnL, 11 picks) | HIGH | LOW-MED | `multi_asset_picks.json` | My audit |
| CM-3 | Fix non-unique pick IDs (`vix_reversal::SI=F::2026-03-11` duplicated) | HIGH | LOW | `multi_asset_closed.json`, `multi_asset_picks.json`, `quick_wins/shared/validate_pick_ids.py` | My audit |
| CM-4 | Decouple `ml_score` from `confidence` (identical on every commodity pick) — ML code sound; inversion is data bug | MED | LOW | `multi_asset_picks.json`, `commodity_futures_strategies.py` | My audit + peer childlike |
| CM-5 | COT data freshness check (calendar.json stub from 2026-06-05; fetcher defaults OFF) | MED | LOW | `cftc_cot_fetcher.py`, `data/cftc_cot/calendar.json` | My audit |
| CM-6 | FUTURES: 0 live picks; only artifact YM=F from 2026-10-19 (26 days stale); last close 2026-03-13 (~245 days) | HIGH | LOW | `dashboard_data.json`, `nonzero_deep_dive.md` | Peer audits |
| CM-7 | COMMODITY: 4 picks, all 156+ days old (newest 2026-06-11), no emission since June 2026 | HIGH | LOW | `multi_asset/data/multi_asset_picks.json`, `nonzero_deep_dive.md` | Peer audits |
| CM-8 | CT=F DSR=1.0 claim falsified 2026-05-13 (6.33x over-emission artifact) | MED | LOW | `nonzero_deep_dive.md` | Peer audits |
| CM-9 | Raw DB PF 131.6 nonsensical (driven by 1–2 extreme wins across 2,681 rows; sum_pos 1,008,846 vs sum_neg -7,666) | MED | LOW | `evidence_pick_summary_stats.json` | Peer audits |

## Key observations
**PnL mismatches (verified by recomputation):**
- `GC=F vix_reversal` (multi_asset_closed.json:78): stated `-0.7481`, recompute ratio `-0.00748` (entry 5213.5 → close 5174.5)
- `SI=F vix_reversal #2` (multi_asset_closed.json:104): stated `-3.6402`, recompute `-0.03640` (entry 88.595 → close 85.37)
- `ZN=F vix_reversal` (multi_asset_closed.json:130): stated `-0.3754`, recompute `-0.003754` (entry 112.390625 → close 111.96875)
- `ZN=F futures_mean_reversion` (institutional_closed.json:500): stated `-0.8789`, recompute `-0.008789` (entry 112.0 → current 111.015625)

Contrast — correct (ratio-form): `SI=F vix_reversal #1` (multi_asset_closed.json:51): `pnl_pct=-0.04244034182993861` matches `(84.835-88.595)/88.595 = -0.04244`. File mixes units → must normalize to ratio.

**Stale commodity open picks:** 11 picks in `multi_asset_picks.json` all dated 2026-11-12, `forward_test_only: true`, `pnl_pct: null`, `status: OPEN`, `forward_trades: 0`, `forward_validated: false`. Entries: SI=F, HG=F, KC=F, PL=F (futures_momentum); CL=F (cot_positioning); GC=F (cftc_cot_commercial_signal); CL=F, NG=F, HG=F (cta_commodity_momentum_term); NG=F (cta_golden_cross_200); CL=F (cta_cross_asset_tsmom).

**Non-unique IDs:** `vix_reversal::SI=F::2026-03-11` appears multiple times in `multi_asset_closed.json` (lines 41, 93, 1093; GC=F/ZN=F variants at 67, 119, 353, 405, 743, 768, 1119, 1144). Same `id` reused across distinct rows — breaks pick lookup/dedup.

**ml_score == confidence:** every commodity pick has `confidence == ml_score` exactly (0.75/0.75, 0.6/0.6, 0.735/0.735, 0.7/0.7). Scanner `vix_reversal` (scanner.py:1047) sets `confidence` but never `ml_score`; the multi_asset engine copies confidence → ml_score.

**COT freshness:** `data/cftc_cot/calendar.json` is a stub generated 2026-06-05 (~5+ months old), `tickers: []`, `note: "stub - CFTC_COT_FETCHER_ENABLED was not '1' on last run"`. No COT cache files for GC=F/SI=F/HG=F/ZN=F — only `.gitkeep`. `multi_asset_picks.json` line 2322 cites `report_date: "2026-11-03"` for GC=F COT (~11 days stale; weekly COT publishes Fridays ~3:30pm ET). Fetcher defaults OFF (`CFTC_COT_FETCHER_ENABLED=1` required).

**Asset-class state (peer audits):**
- COMMODITY: 4 live picks, all 156+ days old, avg PnL +3.57% (skewed: ZS=F +8.54%, ZS=F +9.00%, LE=F -10.03%, ZM=F +6.79%). Honest intrabar: n=229, WR 40.2%, PF 1.026, avg 0.027%. CT=F DSR=1.0 claim falsified 2026-05-13 (6.33x over-emission artifact). Money-ready: WATCH (PF 1.03, WR 40.17%, expectancy -0.004, policy frozen).
- FUTURES: 0 live picks. Only artifact: YM=F LONG from 2026-10-19 (26 days stale) in `dashboard_data.json`. HTML dashboard declares FUTURES "BLOCKED... 6.3% WR on n=17 with 76% LOST-exit rate. Kill list pending." Raw DB PF 131.6 (nonsensical, driven by 1–2 extreme wins across 2,681 rows). Honest intrabar: n=52, WR 42.3%, PF 1.094, avg 0.0791%. Money-ready: INSUFFICIENT_DATA, policy frozen, last close 2026-03-13 (~245.7 days).

## Verification (commodities/futures)
### QW1 — PnL unit normalization
Recompute each futures closed pick's ratio PnL = `(close_price - entry_price) / entry_price` (LONG) or `1 - (close_price/entry_price)` (SHORT), then compare to the stored `realized_pnl_pct` / `pnl_pct`. A stored value ≈ ratio × 100 confirms the percent-vs-ratio bug.
Confirmed mismatches (all ≈ 100× too large): GC=F stated `-0.7481` vs recompute `-0.00748`; SI=F #2 stated `-3.6402` vs recompute `-0.03640`; ZN=F stated `-0.3754` vs recompute `-0.003754`; ZN=F futures_mean_reversion stated `-0.8789` vs recompute `-0.008789`.

### QW2 — Stale commodity open picks
grep `forward_test_only.*true` + `pnl_pct.*null` + `category.*commodity` in `multi_asset_picks.json` → confirm count == 11 and all `entry_date == "2026-11-12"`.

### QW3 — Non-unique pick IDs
`grep -c "vix_reversal::SI=F::2026-03-11" multi_asset_closed.json` → expect >1 before fix, ==1 after. Cross-check `multi_asset_picks.json` IDs against `multi_asset_closed.json` IDs for collisions.

### QW4 — ml_score == confidence coupling
load `multi_asset_picks.json`, filter `category == commodity`, assert `abs(confidence - ml_score) < 1e-9` for all; confirm count of coupled == total commodity picks.

### QW5 — COT data freshness
`cat data/cftc_cot/calendar.json` → confirm stub + old `generated_at`; `ls data/cftc_cot/` → confirm only `.gitkeep` + `calendar.json`; check `CFTC_COT_FETCHER_ENABLED` not set in CI/workflow env.

## Code snippets

**QW1 — Normalize PnL to ratio (one-time repair + guard):**
```python
def _pnl_ratio(entry, close, direction):
    if entry is None or close is None or entry == 0: return None
    return (close / entry) - 1.0 if direction == "LONG" else 1.0 - (close / entry)

def normalize_pick(p):
    field = "realized_pnl_pct" if "realized_pnl_pct" in p else "pnl_pct"
    val = p.get(field)
    if val is None: return p
    entry = p.get("entry_price") or p.get("close_price")
    close = p.get("close_price") or p.get("current_price")
    direction = p.get("direction", "LONG")
    if entry and close:
        recompute = _pnl_ratio(entry, close, direction)
        if abs(val - recompute * 100) < 0.01 and abs(val - recompute) > 0.01:
            p[field] = recompute  # percent-scaled → divide by 100
    return p
```
Guard: after computing `pnl_pct`, assert `abs(pnl_pct) <= 1.0` (ratio) or explicitly store `pnl_pct_pct` for percent form — never mix.

**QW3 — Enforce unique pick IDs:**
```python
SEEN_IDS = set()
def make_id(strategy, symbol, date, suffix=""):
    pid = f"{strategy}::{symbol}::{date}{suffix}"
    if pid in SEEN_IDS:
        pid = f"{strategy}::{symbol}::{date}:{suffix or 'dup'}"
    SEEN_IDS.add(pid); return pid
```
Disambiguate existing duplicates in `multi_asset_closed.json` by appending `_<hold_days>` or `_<close_timestamp>` to repeated `vix_reversal::SI=F::2026-03-11` rows, then rebuild any ID-keyed index.

**QW4 — Decouple ml_score from confidence:**
```python
signals.append({
    ...
    "confidence": round(confidence, 3),          # rule-based, from strategy
    "ml_score": round(ml_model.predict(features), 3),  # independent ML view
    ...
})
```
In `multi_asset_picks.json` writer, stop `ml_score = confidence`. Emit `ml_score` from actual ML model (or `null` if unavailable). Schema guard: do not require equality.

**QW5 — COT freshness check + enable fetch:**
```python
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
def cot_is_fresh(cache_dir, contract, max_age_days=7):
    p = Path(cache_dir) / f"{contract.replace('=F','')}_latest.json"
    if not p.exists(): return False, "missing"
    rec = json.loads(p.read_text()); fetched = rec.get("fetched_at")
    if not fetched: return False, "no timestamp"
    age = datetime.now(timezone.utc) - datetime.fromisoformat(fetched)
    return age <= timedelta(days=max_age_days), f"{age.days}d old"
```
Skip/reject any `cftc_cot_commercial_signal` pick whose COT report is older than 7 days (or flag `data_stale=true`). Flip CI gate: `CFTC_COT_FETCHER_ENABLED=1` so `tools/cftc_cot_fetcher.py` writes `data/cftc_cot/*_latest.json` weekly (CFTC publishes Fridays ~3:30pm ET).

## Recommended fix order
1. **QW1 (PnL units)** — highest data-integrity impact; 4 verified ×100 mismatches + mixed units.
2. **QW3 (unique IDs)** — prevents silent overwrites in ID-keyed joins; trivial `make_id` guard.
3. **QW2 (stale picks)** — 11 zombie commodity opens; either forward-validate them or mark `status: EXPIRED` / set `forward_test_only: false` with real PnL.
4. **QW4 (ml_score/confidence)** — stops ml_score from being a copy of confidence; restores it as an independent signal.
5. **QW5 (COT freshness)** — enable `CFTC_COT_FETCHER_ENABLED=1`, populate `data/cftc_cot/`, add freshness guard before emitting COT picks.

All file paths are absolute under `/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/flaxen-hair/`. No secrets (`dbpasses.txt`) were read or exposed.
