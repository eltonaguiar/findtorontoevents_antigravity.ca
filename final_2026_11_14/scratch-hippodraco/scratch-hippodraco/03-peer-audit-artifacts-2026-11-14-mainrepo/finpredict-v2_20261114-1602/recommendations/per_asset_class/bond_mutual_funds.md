# BOND + MUTUAL FUNDS remediation

**Prepared:** 2026-11-14T16:20Z · **Audit clock:** 2026-11-14T16:05Z
**Source evidence:** `MASTER_AUDIT.md`, `sub/B_dashboard_freshness.md`, `sub/D_non_crypto.md`, `sub/E_statistical.md`, `raw/{bond_detail.txt,per_strategy_agg.csv,pf_registry.json,money_ready_verdict.json,audit_surface_truth.json,summary_picks.json,live_data_dashboard_data.json}`
**Code baseline:** worktree `/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/finpredict-v2`, branch `finpredict-v2`, HEAD `1d9354ab9e2` (line numbers verified 16:20Z).
**Rule:** every number below is from the archived evidence; every `file:line` was re-opened in this worktree. Anything not re-verified is in `## UNVERIFIED`.

> **One-line verdict:** BOND is a policy-frozen, n=1 policy-clean class that renders a **green PASS** because `active_count == 0` short-circuits the quality gate; MUTUAL FUNDS is **not built** (no tracked ranker, page, emitter, or picks) and is only advertised in a dead spec file. Fix the labels and the price path first; do not manufacture picks for either class.

---

## Audited baseline (the facts the fixes must move)

| Item | Audited value | Evidence |
|---|---|---|
| BOND curated `picks.active` | **0** | `sub/D_non_crypto.md:254`; raw `asset_class_summary.BOND.activeCount=0` |
| BOND `picks.active_raw` | **15 rows / 5 instruments / 3 source_systems** | `raw/bond_detail.txt`; `sub/D_non_crypto.md:256-266` |
| BOND unpriced seeds | **9 / 15** `current_price=None`, `pnl=0` | `sub/D_non_crypto.md:264` |
| BOND seed age | 23.9–24.8 h; newest `2026-11-13T14:34:18Z` (25.5 h) | `sub/D_non_crypto.md:266` |
| BOND newest closed | `2026-11-10T13:52:26Z` = **98.2 h / 4.09 d**; n=35, WR 34.3 %, PF 0.586 | `sub/D_non_crypto.md:268-272` |
| BOND policy-clean | **n=1, 0W/1L, WR 0 %, PF 0, pnl −0.01159** | `raw/pf_registry.json` → `by_asset_class_policy_clean_net[0]` |
| BOND `bond_*` strategies | `bond_duration_rotation` n=1; `bond_yield_momentum` n=1 raw / 0 policy-clean | `raw/per_strategy_agg.csv`; `sub/E_statistical.md:209` |
| BOND quality strip | `{activeCount:0, smartCount:0, avgScore:0.0, forwardWR:0.0, thresholdPass:true}` → **green PASS** | `raw/live_data_dashboard_data.json`; `sub/B_dashboard_freshness.md:147,240` |
| BOND authoritative verdict | `INSUFFICIENT_DATA`, `n_resolved=1`, `policy_frozen=true` | `raw/money_ready_verdict.json`; `raw/audit_surface_truth.json` |
| BOND cohort conflict | tournament n=503, WR 58.1 %, +1.066 % vs policy-clean n=1 | `sub/D_non_crypto.md:282-292` |
| MUTUAL FUNDS in payload | **0 occurrences of "mutual"** in `dashboard_payload.json` | `grep -c -i mutual raw/dashboard_payload.json` → `0` |
| MUTUAL FUNDS page | `/audit/mutual-funds.html` **does not exist** | `ls audit_dashboard/*mutual*` → no match |
| MUTUAL FUND ranker | **absent from this worktree and `origin/main`**; only an **untracked** local file in the main checkout | `git ls-tree origin/main \| grep mutual`; main checkout `git status` → `?? alpha_engine/mutual_fund_ranker.py` |
| MUTUAL FUND metadata | `alpha_engine/data/mutual_fund_metadata.csv` **absent** from this worktree/`origin/main`; untracked (5,983 B) in the main checkout | `ls`; main checkout `git status` → `?? alpha_engine/data/mutual_fund_metadata.csv` |
| MUTUAL FUND spec surface | `multi_asset/portfolio_defs.py` defines a `mutual_fund` universe + `tactical_fund_rotation`, but **no live module imports `portfolio_defs`** | `multi_asset/portfolio_defs.py:382-395,677-720`; repo-wide import grep |
| MUTUAL FUND DB families | `mutual_fund_v1` (`mf_`) / `mutual_fund_v2` (`mf2_`) recognised for recon only | `tools/recon_uncharted_tables.py:29-30,162-166` |
| Legacy MF surface | `findmutualfunds2/` contains **3 PHP debug files only** | `find findmutualfunds2 -type f` → 3 |

---

## Quick wins (P0) — ≤1 day each, low risk, high impact

| ID | Fix | Primary files (`file:line`) | Effort | Expected impact | Risk |
|---|---|---|---|---|---|
| **QW-1** | Kill vacuous PASS: a class with `activeCount==0` or `resolved_n<30` becomes `INSUFFICIENT_DATA`, never `thresholdPass=true` | `audit_trail/dashboard_generator.py:6824-6826`; `audit_trail/quality_monitor.py:171-174`; `audit_dashboard/template.html:4946-4953` | S | BOND green PASS → gray **INSUFFICIENT DATA**; matches `money_ready_verdict`; also fixes ETF/FUTURES (n=15/13) | Low — visibility only, no gate relaxation |
| **QW-2** | Add explicit **MUTUAL FUNDS — NOT BUILT** badge + `summary.unbuilt_asset_classes`; mark the dead spec `RESEARCH_ONLY` | `audit_trail/dashboard_generator.py:18006-18014`; `audit_dashboard/template.html:4913-4966`; `multi_asset/portfolio_defs.py:382-395` | S | Honest class inventory; no phantom 8th class; no false green | Low — additive fields |
| **QW-3** | Fix `summary_picks` WR >100 % (BOND **127.8 %**): wins/losses must be a subset of `resolved` | `tools/sync_summary_picks_json.py:63-65,153-162` | S | Removes 7 impossible WRs (BOND 127.8 %, FUTURES 363.9 %, INDEX 1141.2 %, …) | Low — published number changes (intended) |
| **QW-4** | BOND price coverage trio: (a) read current payload schema, (b) real `FMP_API_KEY`, (c) resolver knows all bond ETFs | `audit_trail/fetch_stock_prices.py:68-77`; `audit_trail/dashboard_generator.py:1599`; `audit_trail/universal_pick_resolver.py:433-443` | S–M | BOND cache coverage 1/14 → target ≥12/14; `current_price` fill 6/15 → ≥12/15; resolver can close SHY/JNK/EMB/LQD/AGG/BND/TIP/MUB/TLH/GOVT/BNDX | Low–medium (extra API calls; fail-soft) |
| **QW-5** | Cross-source canonical dedupe for emissary classes; apply to `active_raw` too | `audit_trail/dashboard_generator.py:9831-9836,9876`; `:9538` | S–M | BOND `active_raw` **15 → 6** (5 instruments; SHY carries 2 strategies); duplicate groups 6 → 0; also helps ETF/FUTURES/COMMODITY | Low — identity collapse, not a gate |
| **QW-6** | Re-enable FRED in the bond scanner (`SKIP_FRED: '1'` is hard-coded) | `.github/workflows/etf-bond-scanner.yml:159`; `alpha_engine/bond_scanner.py:289-296` | S | `bond_yield_curve_slope` gets real FRED series instead of the TLT/SHY price proxy | Low — `fetch_bond_bundle` is fail-soft |
| **QW-7** | BOND coverage gate at payload build: `<80 %` priced ⇒ `status=DATA_STALE`, `thresholdPass=false`, picks tagged `_price_coverage_insufficient` | `audit_trail/dashboard_generator.py:18006-18014` (new helper near `:1628`) | S | A future BOND unfreeze cannot silently render green on unpriced rows | Low — default on, env kill switch |

**Recommended day-1 order:** QW-1 → QW-2 → QW-3 (labels/truth), then QW-5 (dedupe), then QW-4 → QW-7 (prices), then QW-6 (FRED).

---

## Structural (P1) — 2–10 days, higher blast radius

| ID | Fix | Primary files (`file:line`) | Effort | Expected impact | Risk |
|---|---|---|---|---|---|
| **P1-1** | One canonical BOND emitter. Keep `bond_scanner` (has OHLCV failover + FRED bundle) and retire the other two pick paths; `bond-agent` becomes a health/validation job | `.github/workflows/etf-bond-scanner.yml:150-165`; `.github/workflows/bond-agent.yml:217,246-320`; `alpha_engine/scanner.py:293` | M–L | 1 source of truth; no 3× n inflation; clean forward accrual | Medium — touches scheduling; stage behind `BOND_EMITTER_MODE` |
| **P1-2** | BOND promotion gate + shadow accrual using the documented bypass (paper-only 60 d HYG/LQD credit-spread + `bond_credit_mom` lab validation); require n≥100, WR≥50 %, PF≥1.5, coverage≥90 %, top-source ≤40 % before lifting the freeze | `audit_trail/quality_gates.py:1724-1730`; new `tools/bond_promotion_gate.py`; `tests/` | M | A falsifiable path out of `BLOCKED_ASSET_CLASSES` instead of an unbounded freeze | Medium — policy change; gate returns BLOCKED until evidence exists |
| **P1-3** | FRED bundle + persisted cache/backfill: fetch `fetch_bond_bundle(lookback_days=365)` in `bond-agent`, cache series to disk, and add a closed-pick price/yield repair job | `.github/workflows/bond-agent.yml:126-148`; `alpha_engine/bond_data_fred.py:313`; `tools/backfill_*.py` | M | FRED survives outages; yield-level reconciliation becomes possible; fewer stale-proxy signals | Medium — runtime/rate limits; flag + cache |
| **P1-4** | Class-health contract: `asset_class_summary[ac]` gains `status`, `activeRawCount`, `openRawCount`, `data_coverage`; contract tests + CI assertion | `audit_trail/dashboard_generator.py:6830-6848`; `tests/test_dashboard_payload_contract.py` | M | Summary stops lying by omission (BOND 0 vs 15, FOREX 2 vs 118) | Low–medium — additive schema |
| **P1-5** | MUTUAL FUNDS research-only surface **or** full removal. Recommended: remove from advertised classes now; optional weekly NAV research page later | `multi_asset/portfolio_defs.py:382-395,677-720`; new `alpha_engine/mutual_fund_ranker.py` (only if research approved) | S (remove) / M (research page) | No fake asset class; no fabricated prices; a credible research artifact if wanted | Low (remove) / Medium (new surface) |

---

## Per-fix detail — Quick wins (P0)

### QW-1 — Kill the vacuous threshold (BOND must be INSUFFICIENT_DATA, not PASS)

**Problem (specific audited number).** `asset_class_summary.BOND = {activeCount: 0, smartCount: 0, avgScore: 0.0, forwardWR: 0.0, thresholdPass: true}` renders a green **PASS** in the quality strip (`sub/B_dashboard_freshness.md:147,240`; `sub/D_non_crypto.md:254`). The authoritative surfaces say `INSUFFICIENT_DATA` (`raw/money_ready_verdict.json`, `raw/audit_surface_truth.json`), so the UI contradicts the verdict.

**Verified code.**
- `audit_trail/dashboard_generator.py:6824-6826` —
  ```python
  threshold_pass = (
      active_count == 0          # ← any empty class is "pass" by definition
      or (
  ```
  The `active_count == 0` disjunct short-circuits the whole gate. `min_trades` for BOND is `0` (`audit_trail/quality_gates.py:495`), so even the second branch can pass with no smart picks.
- `audit_trail/quality_monitor.py:171-174` — the same vacuity, plus `active_count < MIN_ACTIVE_FOR_ENFORCEMENT` (`MIN_ACTIVE_FOR_ENFORCEMENT = 10`, `:12`) is an `or`-pass.
- `audit_dashboard/template.html:4946` (source template; `build_html` regenerates `index.html` at `audit_trail/dashboard_generator.py:18582-18599`) —
  ```js
  const classState = hardFail ? 'fail' : (thresholdPass ? 'pass' : (activeCount > 0 ? 'warn' : 'idle'));
  ```
  Backend `thresholdPass=true` wins before the `activeCount > 0` idle branch, so gray never renders.
- `audit_trail/dashboard_generator.py:18006-18012` is where the summary is attached; `payload["performance"]["asset_class_health"]` (built at `:16959-16962`) already carries `resolved_n` (BOND=1, ETF=15, FUTURES=13).

**Change (concrete).**
1. In `_build_per_asset_quality_summary` (`:6781`), accept the per-class `resolved_n` map (or post-process at `:18012`) and compute an explicit status:
   ```python
   resolved_n = int((asset_class_health.get(ac) or {}).get("resolved_n") or 0)
   if resolved_n < 30 or active_count == 0:
       class_status = "INSUFFICIENT_DATA"
   elif smart_count == 0:
       class_status = "INSUFFICIENT_DATA"
   else:
       class_status = "EVALUATED"
   threshold_pass = (
       class_status == "EVALUATED"
       and smart_count > 0
       and avg_score >= min_score
       and (avg_fwr == 0.0 or avg_fwr >= min_fwr)
       and active_count >= min_trades
   )
   summary[ac]["status"] = class_status
   ```
   `resolved_n < 30` is a **display** threshold aligned with `audit_surface_truth`'s `INSUFFICIENT_N` behaviour (BOND n=1, ETF n=15, FUTURES n=13); it does not change any promotion gate or sizing verdict.
2. In `quality_monitor.py`, replace the `active_count == 0 or` disjunct with `active_count == 0 → thresholdPass=False, status="INSUFFICIENT_DATA"`; keep the `< 10` branch as `WARN`, not PASS.
3. In `template.html`, drive state from `status` first:
   ```js
   const status = String(row.status || '').toUpperCase();
   const classState = status === 'NOT_BUILT' ? 'notbuilt'
     : (activeCount === 0 || status === 'INSUFFICIENT_DATA') ? 'insufficient'
     : (thresholdPass ? 'pass' : 'warn');
   const stateLabel = classState === 'notbuilt' ? 'NOT BUILT'
     : classState === 'insufficient' ? 'INSUFFICIENT DATA'
     : classState === 'pass' ? 'PASS' : 'WARN';
   ```
   Add gray/amber colors and render `stateLabel` inside `.asset-quality-badge` (`:4953`), not only in the tooltip.

**Safe default / flag.** Default strict (`AUDIT_CLASS_STATUS_STRICT=1`). Kill switch `AUDIT_CLASS_STATUS_STRICT=0` restores the legacy boolean for one release.

**Expected impact.** BOND, ETF (n=15), FUTURES (n=13) stop rendering green on insufficient samples. No gate or sizing change; `money_ready_verdict` remains the authority.

**Risk + rollback.** Risk: operators lose a familiar green tile → intended. Rollback: set the env var to `0` or revert the commit (single commit, no data migration).

**Effort.** S (2–3 h including tests).

**Validation.**
```bash
python -m pytest tests/test_dashboard_payload_contract.py -q
python -m pytest tests/test_asset_class_status_labels.py -q   # new
python -c "import py_compile; py_compile.compile('audit_trail/dashboard_generator.py', doraise=True)"
python -c "import py_compile; py_compile.compile('audit_trail/quality_monitor.py', doraise=True)"
```
New test (deterministic, no DB): call `_build_per_asset_quality_summary([], [], '2026-11-14T00:00:00Z')` with an empty health map (if the new parameter is used) and assert `BOND["thresholdPass"] is False` and `BOND["status"] == "INSUFFICIENT_DATA"`.

---

### QW-2 — MUTUAL FUNDS: explicit NOT_BUILT label + de-advertise

**Problem (specific audited number).** The payload contains **zero** occurrences of "mutual" (grep count `0`), there are **0 active / 0 closed** MF picks, and no page. Yet `multi_asset/portfolio_defs.py` advertises `"asset_classes": ["mutual_fund"]` (`:382-395`) and a full MF universe (`:677-720`), and `ASSET_CLASS_MASTERPLAN_2026-03-11_0004.md:59,232` lists it as a future class. The live UI silently omits it, which reads as "covered" rather than "absent".

**Verified code.**
- `multi_asset/portfolio_defs.py:382-395` (`tactical_fund_rotation`, `asset_classes: ["mutual_fund"]`, `data_requirements: ["daily_nav","fund_flows"]`).
- `multi_asset/portfolio_defs.py:677-720` (`mutual_fund` universe: VFINX/VTSAX/VBTLX/…, `data_source: "yfinance"`).
- Repo-wide import grep: no live module imports `portfolio_defs`; it is a spec, not a pipeline.
- `alpha_engine/money_ready_verdict.py:226` — `CANONICAL_ASSET_CLASSES` has 7 classes and **excludes** MF.
- `alpha_engine/asset_class.py` — no `mutual_fund` mapping.
- `tools/recon_uncharted_tables.py:29-30,162-166` — `mf_`/`mf2_` are recon families only.
- `findmutualfunds2/` — 3 PHP debug files, no product surface.

**Change (concrete).**
1. Backend: after `payload["asset_class_summary"] = _asset_summary` (`:18012`), add:
   ```python
   payload["summary"]["unbuilt_asset_classes"] = [{
       "asset_class": "MUTUAL FUNDS",
       "status": "NOT_BUILT",
       "reason": "no tracked ranker, no emitter, no page, no picks",
       "advertised": False,
       "as_of": payload.get("generated_at"),
   }]
   ```
   Do **not** add MF to `_PER_ASSET_CLASSES` (`:6763`) or to `CANONICAL_ASSET_CLASSES`.
2. Frontend: in `renderAssetClassQuality` (`:4913-4966`), append gray `NOT BUILT` badges from `D.summary.unbuilt_asset_classes`, with tooltip "Research-only spec; no live ranker/emitter. Do not size."
3. Spec file: change `tactical_fund_rotation` to `"status": "RESEARCH_ONLY", "asset_classes": []`, or delete the block; add a module-level note that `portfolio_defs.py` is not wired to production. (One of the two; do not leave `asset_classes: ["mutual_fund"]` implying a live class.)
4. Docs: keep `ASSET_CLASS_MASTERPLAN` wording but add "NOT BUILT as of 2026-11-14 (see this remediation)".

**Safe default / flag.** Always-on label; no flag needed (it is a disclosure, not a gate).

**Expected impact.** The class inventory becomes 7 live + 1 explicitly NOT_BUILT. No phantom class, no false PASS, no change to picks.

**Risk + rollback.** Low. Rollback: remove the two additive blocks.

**Effort.** S (2 h).

**Validation.**
```bash
python -c "
import json
d=json.load(open('audit_dashboard/data/dashboard_data.json'))
assert [x['asset_class'] for x in d['summary']['unbuilt_asset_classes']]==['MUTUAL FUNDS']
assert 'MUTUAL FUNDS' not in d['asset_class_summary']
print('ok')
"
grep -n "NOT BUILT" audit_dashboard/index.html | head
```

---

### QW-3 — `summary_picks` win-rate >100 % (BOND 127.8 %)

**Problem (specific audited number).** `summary_picks.json` BOND row: `total_picks=1603, resolved=72, wins=92, losses=156, win_rate_pct=127.8` (`raw/summary_picks.json`; `sub/D_non_crypto.md:21,289`). Also COMMODITY 240.2 %, EQUITY 162.4 %, ETF 232.9 %, FOREX 147.0 %, FUTURES 363.9 %, INDEX 1141.2 %. `wins+losses` exceeds `resolved` because the `wins`/`losses` predicates include rows outside the `resolved` status set.

**Verified code.**
- `tools/sync_summary_picks_json.py:63` — `resolved = status IN ('WON','LOST','CLOSED','EXPIRED','TP_HIT','SL_HIT')`.
- `:64` — `wins = status='WON' OR (pnl_pct>0 AND status NOT IN ('LOST','ACTIVE','OPEN'))` → includes `FORCE_CLOSED`, `TIME_EXIT`, etc., which are **not** in `resolved`.
- `:65` — `losses = status='LOST' OR pnl_pct<0` → includes `OPEN` losers, which are **not** in `resolved`.
- `:161` — `win_rate_pct = 100*wins/resolved`.
- Local fallback (`:109-145`) is already cohort-consistent; only the MySQL path is broken.

**Change (concrete).** Make wins/losses a strict subset of `resolved`:
```sql
SUM(CASE
      WHEN status IN ('WON','TP_HIT') THEN 1
      WHEN status IN ('CLOSED','EXPIRED') AND pnl_pct > 0 THEN 1
      ELSE 0 END) AS wins,
SUM(CASE
      WHEN status IN ('LOST','SL_HIT') THEN 1
      WHEN status IN ('CLOSED','EXPIRED') AND pnl_pct < 0 THEN 1
      ELSE 0 END) AS losses
```
Add a guard at `:153-162`:
```python
if wins + losses > resolved:
    row["win_rate_pct"] = None
    row["status"] = "DATA_INCONSISTENT"
    row["note"] = f"wins({wins})+losses({losses}) > resolved({resolved})"
else:
    row["win_rate_pct"] = round(100.0 * wins / resolved, 1) if resolved else None
```

**Safe default / flag.** Always on; the guard is fail-safe (`None` is already an accepted value downstream — `:161` emits `None` when `resolved == 0`).

**Expected impact.** Zero classes with `win_rate_pct > 100`; BOND's value drops to a valid ≤100 % number (direction only — the exact post-fix value depends on the DB cohort, not predicted here).

**Risk + rollback.** Low; consumers that keyed on the impossible numbers were reading garbage. Rollback: revert the SQL.

**Effort.** S (1–2 h).

**Validation.**
```bash
python -m pytest tests/test_summary_picks_win_rate.py -q   # new, exercises _format_payload
python tools/sync_summary_picks_json.py
python -c "
import json
d=json.load(open('audit_dashboard/data/summary_picks.json'))
bad=[c['asset_class'] for c in d['asset_classes'] if (c.get('win_rate_pct') or 0)>100]
assert not bad, bad
print('ok')
"
```

---

### QW-4 — BOND price coverage (three verified defects)

**Problem (specific audited number).** 9/15 BOND raw rows have `current_price=None` and `pnl=0` (`sub/D_non_crypto.md:264`); the pre-cached price file has only **HYG** of the 14 bond ETFs (`audit_trail/data/stock_prices.json`: 61 symbols, `HYG=77.07`, all other bond tickers `None`).

**Verified code / root cause.**
1. `audit_trail/fetch_stock_prices.py:68-77` reads `for section in ['active_picks','closed_picks','picks']` and `items = payload.get(section, [])`. In the current payload, `picks` is a **dict** (`picks.active`, `picks.active_raw`, `picks.recent_closed`), so `not isinstance(items, list)` skips it. Only top-level arrays (if present) and the hardcoded `known` list (`:84-92`, includes `HYG` only among bonds) contribute. The asset-class allow-list at `:77` also omits `'bond'`.
2. `audit_trail/dashboard_generator.py:1599` — the FMP fallback calls `...?apikey=demo`, not the `FMP_API_KEY` that the workflow passes (`.github/workflows/audit-dashboard.yml:359`). `demo` works for almost nothing, so the fallback is a silent no-op.
3. `audit_trail/universal_pick_resolver.py:433-443` — `_EQUITY_ETF_TICKERS` contains `TLT` and `HYG` but **not** `SHY, JNK, EMB, LQD, AGG, BND, TIP, MUB, TLH, GOVT, BNDX`. `_is_non_crypto_symbol` (`:444-452`) therefore returns `False` for 12 of the 14 `BOND_SYMBOLS` (`alpha_engine/asset_class.py:28-38`), so the resolver never quotes them and never closes them.
   - Note: the dashboard's own enrichment *does* include BOND (`audit_trail/dashboard_generator.py:1628`, `market_asset_classes` includes `"BOND"`) and TLT (`:1667`), which is why the defect is partial rather than total.

**Change (concrete).**
1. `fetch_stock_prices.py`:
   ```python
   picks_blob = payload.get("picks") or {}
   sections = list(picks_blob.values()) if isinstance(picks_blob, dict) else []
   sections += [payload.get(k) or [] for k in ("active_picks", "closed_picks")]
   ...
   if ac in ("equity", "stock", "etf", "futures", "bond") or (...):
   ```
2. `dashboard_generator.py:1599`:
   ```python
   fmp_key = os.environ.get("FMP_API_KEY", "").strip()
   if fmp_key:
       url = f"https://financialmodelingprep.com/stable/quote?symbol={sym}&apikey={fmp_key}"
   ...
   else:
       log.warning("FMP_API_KEY missing — skipping FMP equity/bond fallback")
   ```
   Keep the existing per-symbol `try/except` and add a small sleep to respect rate limits.
3. `universal_pick_resolver.py`:
   ```python
   from alpha_engine.asset_class import BOND_SYMBOLS, ETF_SYMBOLS
   ...
   if base in _EQUITY_ETF_TICKERS or base in BOND_SYMBOLS or base in ETF_SYMBOLS:
       return True
   ```
   (Import inside the module's existing optional-import guard style; fall back to a local frozenset if the import fails.)

**Safe default / flag.** `BOND_PRICE_FETCH=1` (default). If unset/0, skip bond symbols but still log the count. FMP remains fail-soft.

**Expected impact.** `stock_prices.json` bond coverage 1/14 → target ≥12/14; BOND `current_price` fill 6/15 → target ≥12/15 on the next build; resolver can mark-to-market and close bond positions instead of leaving `px=None` zombies.

**Risk + rollback.** Low–medium: more network calls and possible FMP 429s. Mitigate with per-symbol try/except, a 0.25 s sleep, and a 60 s workflow timeout already present (`audit-dashboard.yml:163-168`). Rollback: set `BOND_PRICE_FETCH=0`.

**Effort.** S–M (half day including tests).

**Validation.**
```bash
python -m pytest tests/test_bond_data_feed.py tests/test_bond_agent_workflow.py -q
python -c "
from audit_trail.universal_pick_resolver import _is_non_crypto_symbol
for s in ['SHY','JNK','EMB','LQD','AGG','BND','TIP','MUB','TLH','GOVT','BNDX']:
    assert _is_non_crypto_symbol(s), s
print('resolver ok')
"
python audit_trail/fetch_stock_prices.py   # requires audit_trail/data/dashboard_payload.json, or point it at a fixture
python -c "
import json
d=json.load(open('audit_trail/data/stock_prices.json')); p=d['prices']
cov=[s for s in ['TLT','IEF','SHY','LQD','HYG','AGG','BND','EMB','TLH','GOVT','JNK','MUB','TIP','BNDX'] if p.get(s)]
print(f'bond coverage {len(cov)}/14'); assert len(cov)>=12
"
```

---

### QW-5 — Cross-source dedupe (BOND 15 rows → 5 instruments)

**Problem (specific audited number).** BOND emits **15 `active_raw` rows for 5 instruments** from `alpha_engine`, `bond_scanner`, and `orphan_emitter_bond`; 6 duplicate `symbol+strategy+direction` groups (9 extra rows). TLT SHORT appears 3× with different entries (79.72, 79.72, 79.20) (`sub/D_non_crypto.md:256-266`; `raw/bond_detail.txt`).

**Verified code / root cause.**
- The dashboard loads the same economic signal from multiple files:
  - `alpha_engine/data/active_picks.json` → `("alpha_engine", ...)` at `audit_trail/dashboard_generator.py:3686-3689`
  - `alpha_engine/data/active_picks_bond.json` → `("bond_scanner", ...)` at `:4079`
  - `non_crypto_agent/data/bond_picks.json` → `("orphan_emitter_bond", ...)` at `:4123-4124`
- `etf-bond-scanner.yml:152-156` defaults `MERGE_FLAG="--merge"` whenever the input is empty, so `bond_scanner` also writes its picks into `active_picks.json`. This is **redundant I/O, not the observed duplication**: `_merge_into_active_picks` preserves the embedded `source_system="bond_scanner"` (`alpha_engine/bond_scanner.py:319`), and `dashboard_generator.py:8790` only fills `source_system` when it is missing, so the existing dedupe collapses the merged copy with `active_picks_bond.json`. Removing the default merge is still worthwhile cleanup (less write contention), but it will not by itself reduce the 15 rows.
- The 13:39Z `alpha_engine_*` cohort is a **third independent emission** from the general scanner (`alpha_engine/scanner.py:293` imports `BOND_STRATEGIES`), not the merge.
- `bond-agent.yml:217` writes 4 more rows and `:246-320` merges them into `active_picks.json` under `source_system="bond_scanner"` (`p.setdefault("source_system", "bond_scanner")`).
- `_dedup_picks` (`audit_trail/dashboard_generator.py:9831-9836`) keys on `(source_system, symbol, direction, strategy)` — **including** `source_system` — so cross-emitter duplicates are never removed. `active_raw_snapshot = list(active)` (`:9538`) is captured before the dedupe at `:9876`, so the raw view keeps every copy.

**Change (concrete).**
1. Add a helper and call it in `collect_all_picks` before the snapshot:
   ```python
   CROSS_SOURCE_DEDUPE_CLASSES = {"BOND", "ETF", "FUTURES", "COMMODITY"}

   def _collapse_cross_source_dupes(picks):
       if os.environ.get("CROSS_SOURCE_DEDUPE", "1") != "1":
           return picks
       best = {}
       for p in picks:
           ac = str(p.get("asset_class") or "").upper()
           if ac not in CROSS_SOURCE_DEDUPE_CLASSES:
               best[id(p)] = p
               continue
           key = (ac, _normalize_symbol(p.get("symbol","")), str(p.get("direction","")).upper(), p.get("strategy",""))
           rank = (bool(p.get("current_price")), str(p.get("timestamp","")), float(p.get("score") or p.get("elite_score") or 0))
           if key not in best or rank > best[key][0]:
               best[key] = (rank, p)
       return [v[1] if isinstance(v, tuple) else v for v in best.values()]
   ```
   (Use a simple rank tuple; keep the newest priced row. Do not use `pick_id` — IDs are source-prefixed and never match across emitters.)
2. `:9538` → `active_raw_snapshot = _collapse_cross_source_dupes(list(active))`.
3. `:9876` → apply the same collapse before `_dedup_picks`, or fold the cross-source key into `_dedup_picks` for the emissary classes.
4. Keep the existing intra-source dedupe untouched.

**Safe default / flag.** `CROSS_SOURCE_DEDUPE=1`; `CROSS_SOURCE_DEDUPE_CLASSES` env override (comma list). Disable with `CROSS_SOURCE_DEDUPE=0`.

**Expected impact.** BOND `active_raw` 15 → 6 rows (5 instruments; SHY LONG legitimately carries two strategies); `duplicate_symbol_direction_groups` for BOND 6 → 0. If the operator wants one row per instrument, that is a second, separate collapse (P1-1), not this fix. Same mechanism removes the known FOREX (67 groups), FUTURES (3×/6×), and COMMODITY (4×) duplicates if those classes are added later.

**Risk + rollback.** Low: collapsing identical economic signals is identity, not filtering. Risk: if two emitters use different strategy names for the same signal, they will still duplicate — that is P1-1's job. Rollback: env `0` or revert.

**Effort.** S–M (3–5 h).

**Validation.**
```bash
python -m pytest tests/test_dedup_cross_source.py -q   # new
python -c "
import json
d=json.load(open('audit_dashboard/data/dashboard_data.json'))
b=[p for p in d['picks']['active_raw'] if str(p.get('asset_class','')).upper()=='BOND']
keys={(p['symbol'],p.get('direction'),p.get('strategy')) for p in b}
print(len(b),'rows',len(keys),'unique'); assert len(b)==len(keys)==5
"
```

---

### QW-6 — Re-enable FRED in the bond scanner

**Problem (specific audited number).** The bond scanner path has FRED code (`alpha_engine/bond_scanner.py:289-296` calls `fetch_bond_bundle` and passes `fred_data` into `bond_yield_curve_slope`/`bond_ust_tsmom`), but the workflow that runs it hard-codes `SKIP_FRED: '1'` (`.github/workflows/etf-bond-scanner.yml:159`). The audit's "FRED backfill missing" is therefore literal for this path. `bond-agent.yml` does fetch FRED, but only the single `T10Y2Y` series (`.github/workflows/bond-agent.yml:126-148`), so yield-curve strategies there still fall back to the TLT/SHY price proxy.

**Verified code.**
- `.github/workflows/etf-bond-scanner.yml:159` — `SKIP_FRED: '1'`.
- `.github/workflows/etf-bond-scanner.yml:158` — `FRED_API_KEY` is passed, so the credential exists; the flag is the only blocker.
- `alpha_engine/bond_scanner.py:289-296` — `fetch_bond_bundle(lookback_days=365)`, converted with `_convert_fred_bundle` (`:259-262`), with a `try/except` that degrades to `fred_data=None`.
- `alpha_engine/bond_data_fred.py:313` — `fetch_bond_bundle` exists; backends fail soft.

**Change (concrete).** One line:
```yaml
SKIP_FRED: ${{ vars.BOND_SKIP_FRED || '0' }}
```
Mirror the `bond-agent.yml` pattern (`:55-64` in that file) so the kill switch is a repo variable, not a code edit. Optionally set `BOND_FRED_BUNDLE=1` for the scanner to request the bundle explicitly; the scanner already defaults to the bundle when FRED is on.

**Safe default / flag.** Default on (`'0'`); instant revert via repo variable `BOND_SKIP_FRED=1`. No cache required for the first run; P1-3 adds persistence.

**Expected impact.** `bond_yield_curve_slope` and `bond_ust_tsmom` use real FRED series instead of a price proxy on the active emitter; improves signal validity for the strategies the BOND bypass names (`bond_credit_spread_mean_reversion`, duration rotation). It does **not** change sizing or unfreeze BOND.

**Risk + rollback.** Low: `fetch_bond_bundle` catches every backend error and returns empty → identical to the old skip path. Runtime risk is bounded by the 15-min job timeout; if it regresses, set `BOND_SKIP_FRED=1`.

**Effort.** S (30 min + one green run).

**Validation.**
```bash
python -m pytest tests/test_bond_data_feed.py tests/test_bond_agent_workflow.py -q
# after one workflow_dispatch run:
#   expect log line: "FRED data fetched: N/M series populated" with N >= 5
#   expect no "SKIP_FRED" branch taken
```

---

### QW-7 — BOND price-coverage gate (prevents a future false green)

**Problem (specific audited number).** 60 % of BOND seeds are unpriced (`9/15`), yet nothing in the class summary records that. If BOND is ever unfrozen without fixing QW-4, `activeCount > 0` would make the quality strip green again while most rows have no mark.

**Verified code.** `_build_per_asset_quality_summary` (`audit_trail/dashboard_generator.py:6781-6848`) computes only counts/scores; there is no price-coverage input. The enrichment that knows about prices is separate (`:1480-1615`, `:1618-1735`).

**Change (concrete).** Add a small helper next to the enrichment:
```python
def _price_coverage(rows):
    total = [r for r in rows if isinstance(r, dict)]
    priced = [r for r in total if _float(r.get("current_price", 0)) > 0]
    return {"priced": len(priced), "total": len(total),
            "pct": round(len(priced) / len(total), 3) if total else None}
```
Compute it for every class, attach `data_coverage` to `asset_class_summary[ac]`, and:
```python
if coverage["pct"] is not None and coverage["pct"] < 0.80:
    class_status = "DATA_STALE"
    threshold_pass = False
    for r in class_active:
        r["_price_coverage_insufficient"] = True
```
Use `BOND_MIN_PRICE_COVERAGE=0.80` as the env default. Do not copy `entry_price` into `current_price`.

**Safe default / flag.** Default on for BOND; `CLASS_PRICE_COVERAGE_GATE=0` disables.

**Expected impact.** BOND can never render PASS while <80 % of its rows lack a live quote. The failure is visible as `DATA_STALE`, not hidden inside an average.

**Risk + rollback.** Low. Rollback: env `0`.

**Effort.** S (2 h).

**Validation.**
```bash
python -m pytest tests/test_price_coverage_gate.py -q   # new
# fixture: 15 bond rows, 6 priced -> status DATA_STALE, thresholdPass False
# fixture: 15 bond rows, 14 priced -> status EVALUATED (if other gates pass)
```

---

## MUTUAL FUNDS — recommendation: de-advertise now, do not build a live pick class

**Recommendation: remove MUTUAL FUNDS from advertised asset classes and label it `NOT_BUILT` (QW-2). Do not build a live MF pick surface at this time.**

**Why (evidence-based, not preference).**
1. **No class exists.** `alpha_engine/money_ready_verdict.py:226` defines 7 canonical classes without MF; `alpha_engine/asset_class.py` has no MF mapping. Adding MF to the live taxonomy means touching the verdict, quality gates, resolver, dashboard, and contract tests — a multi-week cross-cutting change for a class with no data.
2. **No tracked implementation.** `alpha_engine/mutual_fund_ranker.py` is **not in `origin/main`** and not in this worktree; it exists only as an untracked file in the main checkout (`git status` → `??`). Both the ranker and `alpha_engine/data/mutual_fund_metadata.csv` are untracked in the main checkout. The ranker's output path is misspelled (`mutut_fund_rankings.json`, line 53) and no output file or NAV cache exists (`audit_dashboard/data/mutual_fund_nav_cache/` absent). A build would start from an uncommitted prototype, not a component.
3. **No page, no emitter, no picks.** `/audit/mutual-funds.html` does not exist; `findmutualfunds2/` is 3 PHP debug files; zero MF rows in any feed.
4. **The instrument cannot support the pipeline's contract.** Mutual funds price once daily at NAV (T+1 settlement; `multi_asset/portfolio_defs.py:714-718`). The audit pipeline's core artifact is an intraday pick with `entry_price`, `current_price`, TP/SL, and a resolver. A monthly-NAV fund has no intraday mark; forcing it into the pick schema is exactly how the frozen-price artifacts audited in BOND/ETF were created.
5. **It would re-open the vacuous-PASS bug.** A new class with `activeCount=0` was, until QW-1, an automatic green PASS. Even after QW-1, an MF class would sit permanently at `INSUFFICIENT_DATA` while consuming UI and gate complexity.
6. **The only "advertising" surface is dead code.** `multi_asset/portfolio_defs.py` is not imported by any live module (repo-wide import grep). Removing the claim is a 1-line edit, not a product removal.

**What "remove" means (minimal, reversible).**
- Keep the research files (`mutual_fund_metadata.csv`, the untracked ranker) out of the live path.
- Mark `tactical_fund_rotation` `RESEARCH_ONLY` and drop `asset_classes: ["mutual_fund"]` (`multi_asset/portfolio_defs.py:382-395`).
- Render `MUTUAL FUNDS — NOT BUILT` in the quality strip and `summary.unbuilt_asset_classes` (QW-2).
- Do not add MF to `CANONICAL_ASSET_CLASSES`, `_PER_ASSET_CLASSES`, `asset_class_summary`, the resolver, or sizing.

### If the operator overrides and wants the smallest credible research surface

This is a **research page**, not an asset class. 3–5 days, no picks, no sizing, no DB writes.

1. **Commit the ranker as research code** (`alpha_engine/mutual_fund_ranker.py`) with:
   - `OUT_JSON = .../data/mutual_fund_rankings.json` (fix the `mutut` typo, line 53).
   - A **coverage gate** in `main()` (`:539-559`): compute `priced/total`, minimum `nav_through`, and `nav_months`; if `coverage < 0.90` or `nav_through` older than 10 business days or fewer than 60 months for a fund, write `{"status":"DATA_GAP","coverage_pct":...,"nav_through":...}` and **exit 2**; never write rankings on a data gap.
   - Add `status`, `coverage_pct`, `nav_through`, `source`, `metadata_as_of` to every row (the header already promises this at lines 22-25).
   - Remove/guard `_pct_rank`'s neutral `50.0` default when `len(values) < 2` (line 75-79): emit `score=None, status="INSUFFICIENT_PEERS"` instead of a fake 50.
2. **Data source:** `yfinance` daily NAV is acceptable for a weekly research ranking **only** with the coverage gate above (the ranker already downloads 10 y at `:178`). Cache to `audit_dashboard/data/mutual_fund_nav_cache/` and commit the cache manifest, not the raw CSVs, if size is a concern.
3. **Weekly workflow** `mutual-fund-ranker.yml`: `cron: '0 6 * * 0'` + `workflow_dispatch`, `timeout-minutes: 20`, fails red on `DATA_GAP`.
4. **Static page** `audit_dashboard/mutual-funds.html`: table of rankings with `nav_through`, `coverage_pct`, category-relative percentiles, and a permanent banner **"RESEARCH ONLY — NOT A PICK. NAV is end-of-day; no intraday TP/SL."** No `current_price`, no TP/SL, no PnL, no "win rate".
5. **Hard invariants** (tests): the page/JSON must not contain `current_price`, `tp`, `sl`, `pnl_pct`, or `win_rate`; every row must have a non-null `nav_through` and `coverage_pct >= 0.90`; the artifact must not be referenced by `dashboard_generator`, the resolver, or any sizing module.

**Why this is the *smallest credible* option:** it reuses the existing ranker, adds one gate and one page, and never touches the pick schema. Anything larger (emitter, resolver, DB tables, `mf_`/`mf2_` consolidation) is a new asset-class program, not a remediation.

---

## Per-fix detail — Structural (P1)

### P1-1 — Single canonical BOND emitter

**Problem.** Three independent writers produce **15 `active_raw` rows for the same 5 instruments** (`sub/D_non_crypto.md:256-266`): `alpha_engine/scanner.py:293` imports `BOND_STRATEGIES` (`alpha_engine/bond_strategies.py:821-829`), `alpha_engine/bond_scanner.py` writes `active_picks_bond.json` and merges into `active_picks.json` (`.github/workflows/etf-bond-scanner.yml:152-156`), and `.github/workflows/bond-agent.yml:217` writes `non_crypto_agent/data/bond_picks.json`.

**Change.** Choose one emitter. Recommended: **`bond_scanner`** (it has chunked yfinance + `ohlcv_failover` + FRED bundle) run by `etf-bond-scanner`; make `bond-agent` a validator/health job that emits no picks; gate `BOND_STRATEGIES` in `alpha_engine/scanner.py` behind `BOND_EMITTER_MODE=bond_scanner_only` (default) so the general scanner cannot re-emit BOND. Add `source_system` priority metadata (`bond_scanner > orphan_emitter_bond > alpha_engine`) for the dedupe tie-break.

**Impact.** One n per signal; no 3× forward-accrual inflation; the P1-2 gate gets a clean sample.

**Safe default / flag.** `BOND_EMITTER_MODE=bond_scanner_only` (default); `BOND_EMITTER_MODE=legacy` restores all three emitters without a code revert.

**Risk + rollback.** Medium (scheduling). Stage with `BOND_EMITTER_MODE=legacy` to restore; run both emitters in shadow for one week and compare counts before cutting over.

**Effort.** M–L.

**Validation.** For 7 consecutive builds: BOND `active_raw` unique `(symbol,direction,strategy)` rows = 6, `duplicate_symbol_direction_groups=0`, and the three source_systems do not exceed 1 row per `(symbol,strategy,direction)`.
```bash
python -m pytest tests/test_bond_agent_workflow.py -q
python - <<'PY'
import json
d=json.load(open('audit_dashboard/data/dashboard_data.json'))
b=[p for p in d['picks']['active_raw'] if str(p.get('asset_class','')).upper()=='BOND']
ks={(p['symbol'],p.get('direction'),p.get('strategy')) for p in b}
assert len(b)==len(ks)==6, (len(b),len(ks))
print('single-emitter invariant ok')
PY
```

---

### P1-2 — BOND promotion gate + shadow accrual (use the documented bypass)

**Problem.** BOND is frozen (`audit_trail/quality_gates.py:1724`: `BLOCKED_ASSET_CLASSES = {"FOREX","COMMODITY","FUTURES","BOND"}`; rationale at `:1727-1730` cites live PF 0.37 / n=8). Policy-clean n=1 today, so the class cannot earn a verdict by waiting.

**Change.** Implement the bypass that is already written in the code comment (`:1729`): paper-only 60 days on HYG/LQD credit-spread strategies plus `bond_credit_mom` lab validation (lab PF 1.41, not live). New `tools/bond_promotion_gate.py` returns `BLOCKED` with reasons unless **all** hold: policy-clean n≥100, WR≥50 %, PF≥1.5, coverage≥90 % (QW-7), top-source share ≤40 %, 60-day paper window complete. Sizing stays `allowed=false` throughout; `_monitor_mode`/`_sizing_override=zero` keeps accrual without capital.

**Impact.** A falsifiable path out of the freeze; no silent unfreeze. Today the gate returns BLOCKED (n=1), which is the correct observable state.

**Safe default / flag.** `BOND_PROMOTION_GATE_ENFORCE=0` (report-only) until the gate has run clean for 14 days; then `1` to block promotion. Removing the freeze stays a manual `quality_gates.py` edit.

**Risk + rollback.** Medium (policy). Gate is read-only; removing the freeze remains an explicit operator action.

**Effort.** M.

**Validation.** `python tools/bond_promotion_gate.py --json` → `{"status":"BLOCKED","reasons":["policy_clean_n=1 < 100", ...]}`; unit tests for each threshold.

---

### P1-3 — FRED bundle + persisted cache/backfill

**Problem.** QW-6 turns FRED on for `bond_scanner`, but the data is transient. `bond-agent` fetches **1 of the 10 `FRED_SERIES`** — only `T10Y2Y` (`.github/workflows/bond-agent.yml:126-148`; series list at `alpha_engine/bond_data_fred.py:48`), so `bond_yield_curve_slope` gets one series and everything else uses the price proxy; there is no persisted series to repair closed picks or survive a FRED outage.

**Change.** (1) Wire `fetch_bond_bundle(lookback_days=365)` into `bond-agent` behind `BOND_FRED_BUNDLE` (initial default `0`, flip to `1` after one green run). (2) Persist the bundle to `alpha_engine/data/fred_cache/` with `as_of` + source; read cache first, network second. (3) Add a `tools/backfill_bond_marks.py` job that re-quotes open/closed BOND ETF rows from the cached OHLCV failover and never writes `current_price=entry_price` as a mark.

**Safe default / flag.** `BOND_FRED_BUNDLE=0` for the first rollout; flip to `1` after one green run. `BOND_SKIP_FRED=1` remains the hard kill switch.

**Impact.** Yield-level reconciliation becomes possible; fewer proxy-based signals; closed-pick repair instead of zombies.

**Risk + rollback.** Medium (runtime/rate limits). Flags: `BOND_FRED_BUNDLE`, `BOND_SKIP_FRED`, cache TTL. Rollback: unset the flag; the cache is additive.

**Effort.** M.

**Validation.** Workflow log shows `FRED data fetched: N/M series populated` with N≥5 and a nonzero cache file count; `pytest tests/test_bond_data_feed.py`.

---

### P1-4 — Class-health contract (stop the summary lying by omission)

**Problem.** `asset_class_summary` reports curated `activeCount` only: BOND 0 vs 15 raw, FOREX 2 vs 118 raw, EQUITY 2 vs 94 raw (`sub/D_non_crypto.md:24`). Four different class inventories exist in one payload (`sub/D_non_crypto.md:20`).

**Change.** Add to each `asset_class_summary[ac]`: `status` (from QW-1), `activeRawCount`, `openRawCount`, `data_coverage` (QW-7), `policyFrozen` (mirror `money_ready_verdict`), `thresholds`. Add contract assertions:
- `status ∈ {EVALUATED, INSUFFICIENT_DATA, DATA_STALE, NOT_BUILT}`.
- `thresholdPass is False` whenever `activeCount == 0`.
- `win_rate_pct <= 100` in `summary_picks`.
- every canonical class has `data_coverage` populated.

**Impact.** One honest inventory; the UI and the summary can no longer disagree.

**Safe default / flag.** `CLASS_HEALTH_CONTRACT_ENFORCE=0` (warn in CI) for one week; then `1` to fail CI. The fields are additive either way.

**Risk + rollback.** Low–medium (additive schema; the contract test's `KNOWN_TOP_KEYS` hash may need an intentional update).

**Effort.** M.

**Validation.** `python -m pytest tests/test_dashboard_payload_contract.py -q` plus the new assertions; update `KNOWN_TOP_KEY_HASH` only if a top-level key is added (avoid adding one — put everything under existing `summary`/`asset_class_summary`).

---

### P1-5 — MUTUAL FUNDS research surface (optional; see the recommendation above)

**Problem.** No tracked ranker, **0 ranked funds, 0 pages**, no coverage gate; the prototype writes even when NAV coverage is poor (`alpha_engine/mutual_fund_ranker.py:539-559`, untracked) and its `_pct_rank` returns a neutral 50 for a single fund (`:75-79`).

**Change.** Follow the 5-step research build in the MUTUAL FUNDS section, or stop at QW-2 (recommended). Do not create an emitter, resolver path, `asset_class_summary` row, or sizing route.

**Impact.** A truthful research artifact or a truthful absence; never a fabricated price.

**Safe default / flag.** `MF_RESEARCH_SURFACE=0` (default: not built). Set `1` only after the coverage gate and the no-price invariant test pass in CI.

**Risk + rollback.** Low (artifact-only) / Medium (new page). Delete the workflow/page to roll back; no data migration.

**Effort.** S (de-advertise, already QW-2) / M (research page).

**Validation.**
```bash
grep -ri mutual audit_dashboard/data/dashboard_data.json   # 0 hits inside asset_class_summary
python -m pytest tests/test_mutual_fund_no_prices.py -q      # new invariant test
python alpha_engine/mutual_fund_ranker.py --refresh           # fixture at 50% coverage must exit 2
```
The research JSON must contain no `current_price|pnl_pct|win_rate|tp|sl`; the coverage gate exits 2 on a 50 %-coverage fixture.

---

## Do-not-do

1. **Do not remove BOND from `BLOCKED_ASSET_CLASSES`** (`audit_trail/quality_gates.py:1724`) to make the panel look populated. Policy-clean n=1 cannot be promoted; the documented bypass (`:1729`) must be completed first.
2. **Do not backfill `current_price` with `entry_price`.** That is the exact mechanism behind the 19/20 frozen curated picks and the 100 % zero-PnL FUTURES rows (`sub/D_non_crypto.md:426-431`).
3. **Do not write a FRED yield (e.g. DGS10 / T10Y2Y) into `current_price` for a bond ETF.** Yield is not price; it would create a new fabricated mark. FRED is for signals/enrichment only.
4. **Do not add MUTUAL FUNDS to `CANONICAL_ASSET_CLASSES`** (`alpha_engine/money_ready_verdict.py:226`) or to `_PER_ASSET_CLASSES` (`audit_trail/dashboard_generator.py:6763`) to "fix" the absence. That creates a permanently n=0 class and re-opens the vacuous-PASS bug.
5. **Do not dedupe by `pick_id`/`id`.** IDs are source-prefixed (`alpha_engine_…`, `bond_scanner_…`, `orphan_emitter_bond_…`) and never match across emitters; use `(asset_class, symbol, direction, strategy)`.
6. **Do not "fix" WR>100 by dividing by `wins+losses`.** That masks the cohort mismatch. Make `wins`/`losses` a subset of `resolved`, and emit `None`/`DATA_INCONSISTENT` when the invariant fails.
7. **Do not set `thresholdPass=true` for `activeCount==0` anywhere**, including `quality_monitor.py` and any new exporter.
8. **Do not build a mutual-fund pick emitter** to satisfy a class-count KPI. Monthly NAV has no intraday mark, so TP/SL and `current_price` would be synthetic.
9. **Do not trust the D report's ranker path without re-checking git.** `alpha_engine/mutual_fund_ranker.py` is untracked and absent from this worktree/`origin/main`; do not cite it as a shipped component or copy it into production without review.
10. **Do not add a `mutual-funds.html` deploy entry** before the page passes the "no price/pick fields" invariant test; a live-looking page with NAV-only data will be mistaken for a tradable surface.

---

## UNVERIFIED

- **Exact post-fix BOND `win_rate_pct`.** The SQL fix changes the cohort; the archived file only proves the *old* value (127.8 %) was invalid. No post-fix number is predicted.
- **Whether yfinance is currently blocked from GitHub Actions runner IPs.** `alpha_engine/bond_scanner.py:218-220` asserts it; not re-tested from this environment.
- **Current live `asset_class_summary` at 16:20Z.** All quotes are from the archived 14:30Z payload; the live page may have advanced.
- **Current repo pick files vs live payload.** `alpha_engine/data/active_picks_bond.json` and `non_crypto_agent/data/bond_picks.json` in this worktree carry `2026-11-12` timestamps (worktree mtime 2026-11-14 15:44), while the live payload shows `2026-11-13` emissions. The worktree may be behind `origin/main`; line numbers are source-of-truth, file *contents* may differ.
- **Emitter attribution for the 13:39Z `alpha_engine_*` BOND rows.** Inferred from the `id` prefix and the `("alpha_engine", "alpha_engine/data/active_picks.json", …)` registration (`audit_trail/dashboard_generator.py:3686-3689`); no run log was inspected.
- **`bond_*` per-strategy closed counts beyond the registry.** Confirmed: `bond_duration_rotation` n=1 policy-clean; `bond_yield_momentum` n=1 raw / 0 policy-clean. Other five strategies have no entries in `raw/per_strategy_agg.csv` (0 or absent) — not independently queried in MySQL.
- **`mutual_fund_metadata.csv` contents.** Not parsed; the fund count/categories/`as_of` fields were not validated in this pass.
- **Mutual-fund ranker runtime behaviour.** The prototype has never produced an output file (no `mutut_fund_rankings.json`, no NAV cache), so its coverage/ranking behaviour on real data is unverified.
- **D report claim "`alpha_engine/mutual_fund_ranker.py` exists (23,931 bytes)" is contradicted for the repo:** it exists only as an untracked local file in the main checkout (`/home/eaguiar2015/findtorontoevents_antigravity.ca`), and is absent from `origin/main` and this worktree. Treated as UNVERIFIED/non-shipped.
- **Whether any consumer reads `summary_picks.json` beyond diagnostics.** `MASTER_AUDIT.md:383` also marks this UNVERIFIED; the QW-3 fix changes a published number.
- **Browser rendering of the new badges.** Not visually verified; QW-1/QW-2 validation is DOM/text-based unless a Playwright spec is added.

---

## Appendix — verification command sheet

```bash
# syntax
python -c "import py_compile; [py_compile.compile(f, doraise=True) for f in [
  'audit_trail/dashboard_generator.py','audit_trail/quality_monitor.py',
  'audit_trail/fetch_stock_prices.py','audit_trail/universal_pick_resolver.py',
  'tools/sync_summary_picks_json.py']]"

# unit / contract
python -m pytest tests/test_dashboard_payload_contract.py -q
python -m pytest tests/test_bond_agent_workflow.py tests/test_bond_data_feed.py -q
python -m pytest tests/test_asset_class_status_labels.py tests/test_summary_picks_win_rate.py \
                 tests/test_dedup_cross_source.py tests/test_price_coverage_gate.py -q

# rebuild payload + HTML (requires the usual DB env; fail-open paths log warnings)
python -m audit_trail.dashboard_generator

# post-build invariants
python - <<'PY'
import json
d = json.load(open('audit_dashboard/data/dashboard_data.json'))
s = d['asset_class_summary']
assert s['BOND']['thresholdPass'] is False
assert s['BOND']['status'] == 'INSUFFICIENT_DATA'
assert all(not (v['activeCount'] == 0 and v['thresholdPass']) for v in s.values())
b = [p for p in d['picks']['active_raw'] if str(p.get('asset_class','')).upper() == 'BOND']
assert len({(p['symbol'], p.get('direction'), p.get('strategy')) for p in b}) == len(b) == 6
print('bond/mf invariants ok')
PY
```
