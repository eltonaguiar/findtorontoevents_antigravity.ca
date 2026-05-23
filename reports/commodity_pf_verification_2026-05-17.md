# COMMODITY PF Verification — Action Item A5

**Date:** 2026-05-17
**Scope:** `multi_asset_cot` strategy on `CT=F` (cotton futures) — disputed profit factor.
**Method:** read-only recompute from `alpha_engine/data/closed_picks.json` (+ `closed_picks_fast.json`), cross-checked against `dashboard_data.json` and `tools/verify_system_pf.py`.

---

## 1. verify_system_pf.py verdict

`python tools/verify_system_pf.py --system multi_asset_cot`

- **Verdict: `DB_MISSING`** — `DB_STOCKS_PASSWORD` env var not set, so no DB ground-truth available.
- Dashboard side reported by the tool: n=131, wins=104, losses=27, **WR 79.4%, PF 4.72**, total_pnl_pct 407.35, MDD 79.97.
- Tool flags `toxic_concentration: true`, `toxic_symbol: CT=F` (94.4% of the system's volume is one symbol).
- DB-vs-JSON cross-check could **not** be completed → MATCH/INFLATED could not be decided by the tool itself.

## 2. Independent recompute (closed_picks.json + closed_picks_fast.json)

Filter: `source_system == multi_asset_cot` AND `symbol` contains `CT=F`.
De-dup rule: rows sharing `(symbol, direction, entry_date, entry_price≈2dp)` are COT re-emissions of one signal; keep one. Verified each duplicate group carries a **single identical `pnl_pct`** → exact re-emissions, not independent fills.

| Metric        | RAW    | DEDUPED |
|---------------|--------|---------|
| n             | 114    | 40      |
| wins / losses | 99 / 15| 31 / 9  |
| Win rate      | 86.8%  | 77.5%   |
| Gross profit  | 489.51 | 151.89  |
| Gross loss    | 56.49  | 32.40   |
| **Profit factor** | **8.67** | **4.69** |

- 74 of 114 picks (65%) are duplicate re-emissions across only 16 unique trade dates.
- Duplication is **asymmetric**: winning signals were re-emitted up to 9× while losers fewer times → raw PF inflated 8.67 vs deduped 4.69.
- Sample dup groups: `(SHORT, 2026-05-04, 83.35)` ×9, `(SHORT, 2026-05-08, 84.26)` ×9, `(SHORT, 2026-04-28, 79.56)` ×8.

## 3. Dashboard cross-check (`dashboard_data.json`)

- `systems.multi_asset_cot`: n=131, WR 79.4%, **PF 4.72**, gross_win 516.8, gross_loss −109.45 — partially deduped (131 < 114 raw CT=F implies it pools a few non-CT=F rows but still over-counts emissions).
- `asset_class_health.COMMODITY`: n=228, WR 85.5%, **PF 7.71**, `sizing_allowed: true` — dominated by the same un-deduped CT=F COT volume.
- The disputed "PF 21.33" figure does not appear in current data; the live aggregator already shows 4.72–7.71. None of these match the deduped 4.69.

## 4. Verdict: **INFLATED**

Every dashboard COMMODITY/`multi_asset_cot` PF figure (4.72 system, 7.71 asset-class, and the historical 21.33) is **inflated by un-deduplicated COT re-emissions**. The true, signal-level profit factor for `multi_asset_cot` on CT=F is **PF ≈ 4.69, WR ≈ 77.5%, n = 40** unique signals.

Caveats keeping this short of a clean "sizing-ready" call:
- No DB ground-truth (`DB_STOCKS_PASSWORD` unset) — could not independently confirm `pnl_pct` exit logic.
- Single-symbol concentration (CT=F = 94.4% of the system) — PF 4.69 is one cotton trade idea, not a diversified COMMODITY edge.
- CT=F is in `COMMODITY_BLACKLIST` (Phase 2-D kill, ref `project_cotton_blacklisted_2026_05_15.md`) — these picks are forward-test artifacts.

## 5. Sizing recommendation

**Block COMMODITY sizing on `multi_asset_cot`/CT=F.** True deduped PF (4.69) is healthy in isolation but rests on n=40 single-symbol blacklisted-instrument signals — fix the COT emission de-dup in the aggregator, then re-evaluate COMMODITY on non-CT=F breadth before sizing up.
