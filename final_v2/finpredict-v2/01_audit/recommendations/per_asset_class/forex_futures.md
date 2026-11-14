# FOREX + FUTURES remediation

**Scope:** FOREX and FUTURES only, from the 2026-11-14 audit (`finpredict-v2_20261114-1602`).
**Audit clock:** 2026-11-14T16:20Z (Saturday). **Repo (read-only):** `finpredict-v2`.
**Rule:** every number below is either copied from the audit evidence or recomputed from the archived payload/code path; every code location was opened and line-checked. Items that could not be confirmed are in `## UNVERIFIED` — nothing is estimated.

Evidence used: `MASTER_AUDIT.md`, `sub/B_dashboard_freshness.md`, `sub/D_non_crypto.md`, `sub/F_sources.md`, plus a re-read of `raw/dashboard_data.json`.
Code verified in: `audit_trail/dashboard_generator.py`, `audit_trail/universal_pick_resolver.py`, `audit_trail/quality_gates.py`, `alpha_engine/config.py`, `alpha_engine/non_crypto_policy.py`, `alpha_engine/asset_class.py`, `alpha_engine/strategy_blocklist.py`, `copy_trader_intel/multi_asset_copytrader_scraper.py`, `copy_trader_intel/non_crypto_consensus.py`, `.github/workflows/multi-asset-scanner.yml`, `.github/workflows/futures-agent.yml`.

**Core diagnosis (one sentence):** FOREX and FUTURES are not broken by bad strategies so much as by **missing provenance and unenforced policy** — the payload cannot distinguish "not quoted" from "flat", cannot represent a full entry time, and the FOREX class block that the UI advertises exists only in a function with **zero call sites**.

**Verified population baseline (recomputed from `raw/dashboard_data.json`, 2026-11-14T16:20Z):**

| Metric | FOREX | FUTURES |
|---|---:|---:|
| `picks.active_raw` rows | 277 | 13 |
| `OPEN` | 118 | 3 |
| `EXPIRED` / `_auto_expired` | 158 | 10 |
| `SL_HIT` | 1 | 0 |
| `picks.recent_closed` rows | 187 | **0** |
| `pnl_pct == 0.0` | 273 / 277 | 13 / 13 |
| `current_price` null/0 | 242 / 277 | 8 / 13 |
| OPEN frozen (`pnl==0` and price null or == entry) | **93 / 118 (78.8%)** | **3 / 3** |
| Oldest parseable timestamp | 2026-02-20 (267.3 d) | 2026-04-02 (225.7 d) |
| Duplicate `id` groups / extra rows | 40 / 67 | 3 ES=F rows share 1 ID |
| Duplicate `symbol+strategy+direction` groups / extra rows | 67 / 198 | YM=F combo emitted 6× |
| Currency-ETF rows labelled FOREX | 44 (FXA 13, CEW 10, UUP 9, FXC 5, FXY 4, FXE 2, FXB 1) | — |
| `EURUSDT` (crypto) rows labelled FOREX | 5 | — |
| Rows with date-only `timestamp` | 12 | 6 (YM=F 2026-08-07…12) |
| Rows with **no** parseable timestamp | 44 | 0 |
| Rows in the FOREX consolidation allowlist | **0 / 277** | — |

> Correction to `sub/D_non_crypto.md:155`: its "158 rows >30 d stale" is exactly the `EXPIRED` count, not a measured age count. Among the 233 FOREX rows with a parseable timestamp, **114 are >30 d** and 44 have no timestamp. The oldest row (2026-02-20) and the 57% expired share are correct.

---

## Quick wins (P0)

All P0 items are ≤1 day, reversible, and **do not change any trading signal or resolver output**. Default is annotation/shadow; enforcement is P1.

| ID | Fix | Audited problem (verified) | Primary location | Effort | Risk / rollback | Expected impact |
|---|---|---|---|---|---|---|
| **P0-1** | Reject date-only timestamps at ingest; prefer full ISO-8601 for `entry_time`/`signal_time` | FUTURES: all 3 OPEN ES=F rows have `entry_time = signal_time = "2026-11-14"`; 6 YM=F rows have date-only `timestamp`; 9/13 have date-only `entry_time`. FOREX: 12 date-only `timestamp`, 44 undated. Resolver cannot parse date-only (`_parse_timestamp` formats have no `%Y-%m-%d`). | `audit_trail/dashboard_generator.py:8136-8154`, `:8351-8352`; emitter `copy_trader_intel/multi_asset_copytrader_scraper.py:452` (full ts at `:471`) | S | Low — falls back to existing full `timestamp`; `STRICT_ENTRY_TS_ISO=0` | No date-only entry times on new payloads; FUTURES/ FOREX hold-window math becomes exact instead of skipping unparseable rows |
| **P0-2** | Add `quote_status` + `quote_at`; mark identity prices `UNQUOTED` instead of `0.00%` | 93/118 FOREX OPEN are frozen (90 null price, 3 `current==entry`); curated USDCAD/NZDUSD store `pnl_pct = -0.0` with `current_price == entry_price`. The quote miss path silently leaves the carried value. | `audit_trail/dashboard_generator.py:1681-1688` (carried price), `:1752-1755` (miss), `:1821-1822` (hit); post-pass `:17481-17485` | S | Low — additive fields only; `QUOTE_STATUS_ENABLED=0` | The 93 frozen OPEN rows become countable as `UNQUOTED`; `-0.0%` stops being presented as a market observation |
| **P0-3** | Class-correctness **shadow audit** at ingest: currency ETFs and `EURUSDT` | 44 currency-ETF rows + 5 EURUSDT = **49/277 (17.7%)** are not spot FX. `_coerce_asset_class` trusts any non-UNKNOWN label; `_derive_asset_class` returns the explicit `FOREX` hint before its ETF symbol set; `EURUSDT` is deliberately excluded from crypto. | `audit_trail/dashboard_generator.py:3659-3661` (trust label), `:3439-3444` (EURUSDT exclusion), `:3516-3532` (hint wins), `:3567-3568` (ETF set too late); `alpha_engine/asset_class.py:37-53` (no currency ETFs in `ETF_SYMBOLS`) | S | Low — shadow fields only; `CLASS_NORMALIZE_ENFORCE=0` | Exact mismatch count (49) and a per-strategy list (Quality Compounders 36, Value + Quality 4, Consecutive Beats 4) without changing class buckets |
| **P0-4** | Stop emitting FUTURES seeds outside the CME session | 3 OPEN ES=F rows are one ID emitted 3× on **Saturday 13:06Z** at Friday's close (7583.0); the workflow runs `*/30 * * * *` every day; the emitter has no session/bar-freshness check. | `.github/workflows/multi-asset-scanner.yml:10`, `:36-38`; `copy_trader_intel/multi_asset_copytrader_scraper.py:798-854`, save at `:2700-2705` | M | Medium-low — writes deferred file; `FUTURES_SESSION_GUARD=0` | No new weekend/untradeable FUTURES seeds; pipeline stays green because `futures_copytrader_picks.json` is still written (possibly `[]`) |
| **P0-5** | Quarantine exact duplicate IDs from counts | 40 duplicate-ID groups / 67 extra FOREX rows; ES=F appears 3× under the same ID; 3,377 `EXPIRED` rows still counted in `active_raw`. | `audit_trail/dashboard_generator.py:17481-17485` (`active_raw` assembly); `:9538` (snapshot) | S | Low — annotate `_duplicate_of`, do not delete; `DEDUP_EXACT_IDS=0` | FOREX raw inventory drops 277 → 210 unique IDs without losing audit rows |
| **P0-6** | Make the FOREX class block observable (shadow) and reconcile the kill-switch contradictions | The FOREX allowlist exists only in `evaluate_non_crypto_candidate()` — **0 call sites repo-wide**. The live gate `passes_non_crypto_policy()` checks only FX session + ATR. Emitters write JSON that the dashboard ingests directly. **0/277 FOREX rows pass the advertised allowlist.** | `alpha_engine/non_crypto_policy.py:698-741` (allowlist), `:1026-1040` (live gate omits it); `copy_trader_intel/non_crypto_consensus.py:143-147` (FOREX threshold = 1); `audit_trail/dashboard_generator.py:3907`, `:3912`, `:3927`, `:4128-4130` (direct ingest); `alpha_engine/config.py:298`, `:345`; `audit_dashboard/template.html:909`, `:13539` (claims block) | S | Low — annotation only; `CLASS_POLICY_SHADOW=0` | Quantifies the bypass as 277/277 (not a guess); creates the count needed before any enforcement |

### P0-1 — ISO-8601 entry-time enforcement

**Problem (verified).** `_entry_ts_keys` in `audit_trail/dashboard_generator.py:8136-8148` lists `entry_date` **first** and takes the first non-empty value (`:8149-8154`) with no format check. `entry_ts` is then written verbatim to `signal_time` and `entry_time` (`:8351-8352`). The multi-asset emitter writes `entry_date` as `now.strftime("%Y-%m-%d")` (`copy_trader_intel/multi_asset_copytrader_scraper.py:452`) even though it also writes a full ISO `timestamp` (`:471`). The result is exactly what the payload shows: ES=F `timestamp = 2026-11-14T13:06:02.734149+00:00` but `entry_time = signal_time = 2026-11-14`.

The resolver cannot recover: `_parse_timestamp` (`audit_trail/universal_pick_resolver.py:743-755`) has no date-only format, so a date-only `timestamp` returns `None` and the per-class hold/TIME_EXIT branch is skipped (`:1299-1304`).

**Change (safe default):**
- Add `_iso8601_has_time(value)` (accept `YYYY-MM-DDTHH:MM…`, reject `YYYY-MM-DD`).
- Reorder `_entry_ts_keys` to full timestamps first: `entry_time`, `entryDate`, `signal_time`, `created_at`, `generated_at`, `timestamp`, then `entry_date`.
- If only a date-only value exists, set `entry_time` from the full `timestamp` (always present on these rows) and stamp `_ts_precision = "DATE_ONLY"` for diagnostics. Never invent `T00:00:00Z`.
- Env `STRICT_ENTRY_TS_ISO` (default `1`); on failure log once per symbol and keep the old value.

**Expected impact:** fixes 9/13 FUTURES `entry_time` values and at least 12 FOREX date-only rows on the next build; makes resolver hold-window math possible for all rows that still carry a full `timestamp`.

**Risk / rollback:** low — the fallback is the existing generic `timestamp`. `STRICT_ENTRY_TS_ISO=0` restores today's precedence.

**Validation:** the archived snapshot is the **pre-fix baseline**, so run the assertion against the next rebuilt payload (`audit_dashboard/data/dashboard_data.json`) after the generator build, not against `2026-11-14/.../raw/`:

```bash
python3 - <<'PY'
import json,re
d=json.load(open('audit_dashboard/data/dashboard_data.json'))
for x in d['picks']['active_raw']:
    if x.get('asset_class')=='FUTURES' and x.get('status')=='OPEN':
        assert not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(x.get('entry_time'))), x['id']
print('OK')
PY
python3 -m pytest tests/test_dashboard_generator.py tests/test_dashboard_generator_regressions.py -q
```
New test: `tests/test_entry_timestamp_iso.py` — feed a pick with `entry_date` + full `timestamp`, assert `entry_time` has a time component; feed date-only only, assert `_ts_precision == "DATE_ONLY"` and no midnight fabrication.

### P0-2 — Quote provenance and `UNQUOTED` status

**Problem (verified).** On a quote miss the enrichment loop leaves the pick untouched (`audit_trail/dashboard_generator.py:1752-1755`), and a carried `current_price` is accepted as a fallback (`:1681-1688`). The payload therefore has no way to distinguish:
- a real flat move,
- a row whose `current_price` was copied from entry, and
- a row with no price at all.

Recomputed: 93/118 FOREX OPEN rows are frozen (90 null price; 3 `current == entry`); the two curated rows are `USDCAD=X` (`1.4269` vs `1.426900029182434`) and `NZDUSD=X` (`0.552517` vs `0.5525166988372803`), both `pnl_pct = -0.0`.

**Change (safe default):**
- Miss path (`:1752-1755`): `p["quote_status"]="UNQUOTED"`, `p["quote_source"]="none"`, `p["quote_at"]=None`, `p["_price_is_entry"]=True` when `current_price == entry_price`.
- Hit path (`:1821-1822`): `p["quote_status"]="LIVE"` (or `LAST_CLOSE` for a closed session), `p["quote_source"]` from the fetcher, `p["quote_at"]` from the quote timestamp, `p["quote_age_s"]`.
- Post-pass after `active_raw` assembly (`:17481-17485`): apply the same stamp to both `picks.active` and `picks.active_raw`, because not every raw row passes the overlay.
- **Do not** zero or null `pnl_pct` in P0; that is a P1 resolver decision. The point is to label the value, not rewrite it.
- Add the fields to the closed-pick keep list (`:279-309`) so they survive the closed pipeline.

**Expected impact:** 93 FOREX OPEN rows reclassified from "flat" to `UNQUOTED`; `-0.0%` on USDCAD/NZDUSD becomes explicitly `IDENTITY`/unquoted. Downstream WR/PF can exclude them without changing the raw payload.

**Risk / rollback:** additive fields only; UI ignores unknown keys. `QUOTE_STATUS_ENABLED=0`.

**Validation:** after a rebuilt payload (not the archived pre-fix snapshot):
```bash
python3 - <<'PY'
import json
d=json.load(open('audit_dashboard/data/dashboard_data.json'))
fx=[x for x in d['picks']['active_raw'] if x.get('asset_class')=='FOREX' and x.get('status')=='OPEN']
assert len(fx)==118
assert sum(1 for x in fx if x.get('quote_status')=='UNQUOTED')==93
print('OK 93 UNQUOTED')
PY
```
New test: `tests/test_quote_provenance_forex_futures.py` — simulate a total fetcher miss and assert `UNQUOTED`; simulate a hit and assert `quote_at` is populated.

### P0-3 — Class-correctness shadow audit (49 rows)

**Problem (verified).** Three code paths combine to keep 49 non-FX rows in FOREX:
1. `_coerce_asset_class` returns any stamped label that is not `UNKNOWN`/`NONE` (`audit_trail/dashboard_generator.py:3659-3661`) — so `asset_class="FOREX"` is final.
2. `_derive_asset_class` returns an explicit hint (`:3516-3532`) before the ETF symbol set (`:3567-3568`).
3. `_symbol_strongly_crypto` explicitly excludes any `EUR…USDT` from crypto (`:3439-3444`), so `EURUSDT` can never reach the CRYPTO branch; the `FOREX` hint wins.

`alpha_engine/asset_class.py:37-53` does not contain `FXA/FXC/CEW/FXE/FXY/FXB/UUP`, so the canonical module would not call them ETFs either. Separately, `alpha_engine/asset_class.py:222-224` already classifies `EURUSDT` as crypto (stablecoin suffix), so the dashboard and the canonical module disagree on the same row.

**Change (safe default — shadow only):**
- Add `CURRENCY_ETF_SYMBOLS` (`UUP, FXA, FXC, CEW, FXE, FXY, FXB`) to the dashboard's canonical lookup.
- Compute `canonical_asset_class` for every pick: symbol evidence first for the unambiguous cases (`=X` → FOREX, `=F` → FUTURES/COMMODITY, `*USDT` with an FX base → CRYPTO, currency ETF → ETF), then compare with the stamped label.
- Emit `class_mismatch = true`, `class_label_raw`, `class_canonical`, and `class_mismatch_reason`; **do not** change `asset_class` while `CLASS_NORMALIZE_ENFORCE=0` (default).
- Log a single summary line: `FOREX mismatches: 49 (44 currency ETF, 5 EURUSDT)`.

**Expected impact:** exact, auditable list of the 49 rows and the 3 strategies responsible, with no change to any tile or count.

**Risk / rollback:** zero behavior change by design. `CLASS_NORMALIZE_ENFORCE` controls the P1 flip.

**Validation:** after a rebuilt payload:
```bash
python3 - <<'PY'
import json
d=json.load(open('audit_dashboard/data/dashboard_data.json'))
fx=[x for x in d['picks']['active_raw'] if x.get('asset_class')=='FOREX']
assert sum(1 for x in fx if x.get('class_mismatch'))==49
print('OK 49 mismatches')
PY
python3 -m pytest tests/test_derive_asset_class_precedence.py tests/test_dashboard_asset_class_hints.py tests/test_asset_class.py -q
```

### P0-4 — Stop emitting untradeable FUTURES seeds (minimal safe path)

**Problem (verified).** `.github/workflows/multi-asset-scanner.yml:10` runs every 30 minutes on **every day** (`*/30 * * * *`), and step 1a executes `python copy_trader_intel/multi_asset_copytrader_scraper.py` (`:36-38`). `scan_futures_connors_rsi2` (`copy_trader_intel/multi_asset_copytrader_scraper.py:798-854`) has no session check and prices the pick from the last daily bar (`current = closes[-1]`, `:811`). On Saturday 2026-11-14 at 13:06Z this produced three copies of the same ES=F ID at Friday's close 7583.0, with `current_price = entry_price` and `pnl_pct = 0.0`. The separate `futures-agent.yml` is correctly weekday-gated (`cron: '0 14 * * 1-5'`), so the weekend path is specifically the multi-asset scanner.

**Minimal safe path (no pipeline break):**
1. Add `_futures_session_open(now_utc)` to `multi_asset_copytrader_scraper.py`, using `zoneinfo.ZoneInfo("America/New_York")` so DST is handled: open Sunday 18:00 ET through Friday 17:00 ET (on 2026-11-14 EST that is Sunday 23:00 UTC → Friday 22:00 UTC). A holiday calendar is P1, not P0.
2. In `save_results`, before `by_class` is built (`:2700-2705`), partition `FUTURES` picks:
   - session open → keep in `futures_copytrader_picks.json` as today;
   - session closed → write to **`futures_deferred_picks.json`** and exclude from `all_picks`/the dashboard source.
3. Always write `futures_copytrader_picks.json` (possibly `[]`) so `audit_trail/dashboard_generator.py:4128` (`orphan_emitter_futures`) keeps a valid file.
4. If a closed-session row must be retained for research, set `status="PLACEHOLDER"` and `quote_status="UNQUOTED"`; do not leave it `OPEN`.

Env `FUTURES_SESSION_GUARD` default `1`. This does **not** delete the emitter, does not change the workflow, and does not require a schema migration.

**Expected impact:** zero new weekend/untradeable FUTURES seeds. The existing 3 OPEN ES=F copies remain until P0-5/P1-6 quarantines them; no break if yfinance or the scraper fails, because the file contract is unchanged.

**Risk / rollback:** risk is a missed Sunday reopen signal if the clock window is wrong. Use ET via `zoneinfo`, not a hard-coded UTC offset; `FUTURES_SESSION_GUARD=0` is an immediate rollback. Do not gate the whole workflow, or FOREX/equities stop too.

**Validation:**
```bash
python3 - <<'PY'
# frozen-clock test: Saturday 2026-11-14T13:06Z -> futures list must be deferred
from datetime import datetime, timezone
from copy_trader_intel.multi_asset_copytrader_scraper import _futures_session_open
assert _futures_session_open(datetime(2026,11,14,13,6,tzinfo=timezone.utc)) is False
assert _futures_session_open(datetime(2026,11,16,14,0,tzinfo=timezone.utc)) is True
print('OK')
PY
```
New test: `tests/test_futures_session_guard.py` (Sat closed, Sun 23:30 UTC open in EST, Mon 14:00 UTC open, Fri 22:30 UTC closed).

### P0-5 — Exact-ID dedup / duplicate annotation

**Problem (verified).** FOREX has 40 duplicate-`id` groups producing 67 extra rows. The most visible FUTURES case is the same `multi_asset_futures_connors_rsi2::ES=F::2026-11-14_1306` emitted 3×. These rows inflate `active_raw` counts and every per-class denominator.

**Change (safe default):**
- In the `active_raw` post-pass (`audit_trail/dashboard_generator.py:17481-17485`), group by `id`; keep the row with the newest parseable `timestamp`; set `_duplicate_of=<kept id>` and `_duplicate=True` on the rest.
- Do not delete the rows from `active_raw` (the view is explicitly the pre-filter audit pool); exclude `_duplicate` from `open_count`/class counts and from default sorting.
- Do **not** dedup by `symbol+strategy+direction` yet — that is P1-4 because legitimate re-entries share that key. Exact IDs only is safe.

Env `DEDUP_EXACT_IDS` default `1`.

**Expected impact:** FOREX unique IDs 210 (from 277 rows); ES=F triple collapses to one counted row. Raw audit trail is preserved.

**Risk / rollback:** low; `_duplicate` is additive. `DEDUP_EXACT_IDS=0`.

**Validation:**
```bash
python3 - <<'PY'
import json
d=json.load(open('2026-11-14/finpredict-v2_20261114-1602/raw/dashboard_data.json'))
fx=[x for x in d['picks']['active_raw'] if x.get('asset_class')=='FOREX']
ids={x['id'] for x in fx}
print(len(fx), len(ids))
assert len(fx)==277 and len(ids)==210
PY
```

### P0-6 — FOREX block vs consensus bypass (verified)

**Problem (verified, and this is the exact "PR #6" mismatch).** `audit_dashboard/template.html:909` tells the user: *"FOREX — BLOCKED (PR #6 consolidation 2026-05-31: all FOREX strategies blocked except cta_cross_asset_tsmom SHORT) … Hard disable default ON in `non_crypto_policy.py`"*. The same claim is repeated at `:13539`. The code does not support it:

- The FOREX consolidation policy is in `evaluate_non_crypto_candidate()` (`alpha_engine/non_crypto_policy.py:698`), with the allowlist at `:723-741`:
  ```python
  _FOREX_ALLOWED = frozenset({"cta_cross_asset_tsmom", "forex_carry", "forex_carry_g10"})
  ```
- Repo-wide search for `evaluate_non_crypto_candidate` returns **only the definition** — zero callers. That also makes the entire `NON_CRYPTO_STRATEGY_POLICY` registry (including `cta_cross_asset_tsmom` at `:395-402`) unreachable from the live path.
- Every live emitter instead calls `passes_non_crypto_policy()` (`multi_asset/scanner.py:705`, `multi_asset/forex_strategies.py:986`, `alpha_engine/forex_smart_picks.py:483`, `alpha_engine/commodities_strategies.py:1057`, `alpha_engine/commodity_signal_generator.py:211`), and that function composes only `passes_fx_session_gate` + `passes_atr_reachability_gate` (`alpha_engine/non_crypto_policy.py:1026-1040`). It never sees the allowlist.

Two more bypasses compound it:
- `copy_trader_intel/non_crypto_consensus.py:143-147` lowers the FOREX agreement threshold to **1**, so one strategy can emit a "consensus" FOREX pick; the dashboard ingests that file directly (`audit_trail/dashboard_generator.py:3927`).
- The multi-asset emitter writes `multi_asset_picks.json`/`forex_copytrader_picks.json` (`copy_trader_intel/multi_asset_copytrader_scraper.py:2687-2705`) and never calls the policy; the dashboard ingests both (`audit_trail/dashboard_generator.py:3907`, `:3912`).

Recomputed against the live payload: **0 of 277** FOREX rows pass the advertised allowlist. The top strategies are `MeanReversionBB` 74, `Quality Compounders` 36, `ig_contrarian_sentiment` 30, `forex_rsi2_mean_reversion` 24, `MomentumEMA` 21, `non_crypto_consensus` 20 (itself in `_RETIRED_STRATEGIES`, `alpha_engine/strategy_blocklist.py:125` and `:144`).

There are also two authority contradictions that must be resolved before enforcement:
- `alpha_engine/config.py:298` blacklists `cta_cross_asset_tsmom`, while `non_crypto_policy.py:724` allowlists it.
- `alpha_engine/config.py:345` computes `FOREX_HARD_DISABLE` **default OFF** (`get(..., "0") not in ("0", …)` is `False`), while the adjacent comment and `quality_gates.py:8848-8866` describe it as default ON and the dashboard copy says "BLOCKED". The 277 rows confirm it is currently OFF.

**Change (P0 = observe, do not enforce):**
- Add `_policy_blocked_reason` to each non-crypto row at ingest, using the allowlist plus the FOREX-threshold rule, and log `FOREX: 277 rows, 0 pass, 277 blocked (forex_strategy_consolidation_blocked)`.
- Add `tests/test_policy_emission_parity.py` that asserts: (a) every function in the live emission path calls the same policy function; (b) the allowlist and `BLACKLISTED_STRATEGIES` have no intersection; (c) `FOREX_HARD_DISABLE`'s documented default matches its computed value.
- Do **not** switch enforcement in this fix.

**Expected impact:** the "class blocked" claim on `/audit` becomes measurable and falsifiable; the operator sees that today's FOREX surface is 100% policy-invalid instead of discovering it after a sizing decision.

**Risk / rollback:** none — annotation only. `CLASS_POLICY_SHADOW=0`.

**Validation:**
```bash
python3 - <<'PY'
import json
d=json.load(open('2026-11-14/finpredict-v2_20261114-1602/raw/dashboard_data.json'))
fx=[x for x in d['picks']['active_raw'] if x.get('asset_class')=='FOREX']
allowed={'cta_cross_asset_tsmom','forex_carry','forex_carry_g10'}
ok=[x for x in fx if x.get('strategy') in allowed and (x.get('strategy')!='cta_cross_asset_tsmom' or x.get('direction')=='SHORT')]
assert len(fx)==277 and len(ok)==0
print('OK 0/277 pass')
PY
python3 -m pytest tests/test_forex_f1_gate_p1.py tests/test_quality_gates.py -q -k forex
```

---

## Structural (P1)

| ID | Fix | Audited problem (verified) | Primary location | Effort | Risk / rollback | Expected impact |
|---|---|---|---|---|---|---|
| **P1-1** | Enforce one canonical classifier (flip P0-3 from shadow to enforce) | 49/277 FOREX rows are not FX; `EURUSDT` is CRYPTO in `alpha_engine` but FOREX on the dashboard; currency ETFs are in neither ETF set | `audit_trail/dashboard_generator.py:3645-3680`, `:3439-3444`, `:3567-3568`; `alpha_engine/asset_class.py:37-53`, `:222-224` | M | Medium — class counts move; dual-write `asset_class_raw` for one release; `CLASS_NORMALIZE_ENFORCE=1` | FOREX means spot FX; the 44 currency ETFs land in ETF, the 5 EURUSDT rows in CRYPTO; class PF denominators become honest |
| **P1-2** | Put the class policy in the **live** emission path, not a dead function | `evaluate_non_crypto_candidate()` has 0 callers; live gate omits the FOREX allowlist; 0/277 pass; consensus threshold for FOREX = 1; retired `non_crypto_consensus` still emits | `alpha_engine/non_crypto_policy.py:698-741`, `:1026-1040`; `multi_asset/scanner.py:705`; `copy_trader_intel/non_crypto_consensus.py:143-147`; `audit_trail/dashboard_generator.py:3927` | M | High — enforcing today drops all 277 rows; stage: shadow (P0-6) → warn → block **new** emissions only, retain history | The advertised block becomes true for new picks; no silent 277-row class |
| **P1-3** | FX/FUTURES quote pipeline v2 (as-of, session calendar, fail-closed) | 242/277 FOREX rows have no `current_price`; 90/118 OPEN are null; futures prices freeze at April/August closes (ZN=F 111.015625 = 2026-04-02; CL=F 112.06 vs 88.56; GC=F 4702.70 vs 3886.30); `stock_prices.json` covers only 61 symbols and no FX/futures | `audit_trail/dashboard_generator.py:1490-1600`, `:1690-1755`; `audit_trail/universal_pick_resolver.py:334-507`; `audit_trail/fetch_stock_prices.py` | M | Medium — provider/rate-limit risk; cache-first + explicit `UNQUOTED` on failure | Every FX/futures row is either freshly quoted with `quote_at` or visibly unquoted; no frozen April price can present as today's mark |
| **P1-4** | Canonical trade-key dedup with an emission window | 67 duplicate `symbol+strategy+direction` groups / 198 extra rows; 3 ES=F under one ID; YM=F SHORT emitted 6× daily 2026-08-07…12 | `audit_trail/dashboard_generator.py:17481-17485`; `copy_trader_intel/multi_asset_copytrader_scraper.py:444` (ID minute-granular); `:2411` (day-level signal timestamp) | M | Medium — legitimate re-entries share the key; require same UTC day **and** same entry price within tolerance; keep all rows | Raw count reflects trades, not emission retries; 198 phantom FOREX rows and 5 phantom YM=F rows stop polluting denominators |
| **P1-5** | FUTURES closed-ledger + resolver support | `picks.recent_closed` has **0** FUTURES rows; all 13 raw futures rows are `pnl=0`; `_parse_timestamp` cannot parse the 6 date-only YM=F rows; no rollover handling for `=F` | `audit_trail/universal_pick_resolver.py:743-755`, `:1294-1304`, `:1460-1510`; `audit_trail/dashboard_generator.py:4128` (futures source) | L | High — resolver changes affect realized outcomes; never retro-edit history; add a new `FUTURES_V2` cohort | FUTURES gets a real closed sample instead of `0`; no class verdict can be computed from zero closes |
| **P1-6** | Retention contract for `EXPIRED`/`PLACEHOLDER` seeds | 158/277 FOREX rows are `_auto_expired` zombies; 10/13 FUTURES rows are `EXPIRED` (6 date-only); `active_raw` is append-only; 3,377 `EXPIRED` rows still counted payload-wide | `audit_trail/dashboard_generator.py:9538`, `:9540-9617`, `:17481-17485`; `audit_trail/universal_pick_resolver.py:931-963` (`_heal_no_price_row`) | S/M | Low — annotation/partition, no deletion; `ACTIVE_RAW_QUARANTINE=0` | "Open" and "inventory" stop being synonyms; the 158 FOREX and 10 FUTURES expired rows are retained for audit but excluded from counts |
| **P1-7** | Stop publishing `summary_picks` WR for FOREX/FUTURES until the denominator is fixed | FOREX `win_rate_pct = 147.0` (8,536 W / 8,968 L vs `resolved = 5,806`); FUTURES `363.9` (222/357 vs 61) — arithmetically impossible | `tools/sync_summary_picks_json.py:63-65`, `:161`; live artifact `summary_picks.json` | S | Low — mark the two classes `invalid_denominator: true` or omit; fix is shared with the EQUITY/ETF plan P0-4 | Removes the two most extreme impossible WRs from the only surface publishing them; no FOREX/FUTURES decision can cite 147%/363.9% |

### P1-1 — One canonical classifier (enforcement)

**Problem (verified).** P0-3 proves the mismatch (49/277). The classifier has three bypass layers: the label fast-path (`audit_trail/dashboard_generator.py:3659-3661`), the hint-before-symbol ordering (`:3516-3532` vs `:3567-3568`), and the deliberate `EUR…USDT` → non-crypto exclusion (`:3439-3444`). `alpha_engine/asset_class.py` has no currency-ETF set (`:37-53`) but already treats `EURUSDT` as crypto (`:222-224`), so there is no single source of truth.

**Change:**
- Add `CURRENCY_ETF_SYMBOLS` to `alpha_engine/asset_class.py` and check it in `asset_class_from_symbol` before the `unknown` fallback.
- In `_derive_asset_class`, move unambiguous symbol checks (currency ETF, `=X`, `=F`, stablecoin-with-FX-base) **above** the explicit-hint loop, or require the hint to agree with the symbol for these sets.
- Keep `_coerce_asset_class`'s fast path, but add a narrow override list; do not re-derive every label.
- Dual-write `asset_class_raw` and `class_canonical` for one release; flip `CLASS_NORMALIZE_ENFORCE=1` after counts are reviewed.

**Expected impact:** 44 rows move FOREX → ETF and 5 → CRYPTO. FOREX raw inventory becomes 228 spot-FX rows (before dedup); the class no longer includes equity-strategy ETF picks.

**Risk / rollback:** class tiles and per-class PF move; downstream consumers keyed on `FOREX` may see fewer rows. `CLASS_NORMALIZE_ENFORCE=0` and the dual-write make rollback a config flip.

**Validation:** `python3 -m pytest tests/test_derive_asset_class_precedence.py tests/test_dashboard_asset_class_hints.py tests/test_asset_class.py -q`, plus the 49-row assertion from P0-3 with enforcement on.

### P1-2 — Wire the live policy path

**Problem (verified).** This is the structural version of P0-6. The allowlist is unreachable code; the live gate omits it; the copy-trader emitters do not call any class policy; the consensus module lowers FOREX to a single vote. The UI copy (`BLOCKED — n consolidation 2026-05-31`) and the code default (`FOREX_HARD_DISABLE=False`) disagree.

**Change:**
- Extract `passes_forex_consolidation(pick)` (allowlist + SHORT-only rule) and call it from `passes_non_crypto_policy()`.
- Call `passes_non_crypto_policy` from `copy_trader_intel/multi_asset_copytrader_scraper.save_results` and `non_crypto_consensus.py` before writing.
- Decide one authority for `cta_cross_asset_tsmom` (allowlist vs `BLACKLISTED_STRATEGIES`) and remove it from the other.
- Make `FOREX_HARD_DISABLE`'s documented default and computed default identical; add a startup log line.
- Stage enforcement: annotate (P0-6) → log `would_block` for 7 days → block **new** emissions; never delete existing rows.

**Expected impact:** new emissions respect the advertised policy. If enforced today, the curated FOREX panel would go from 2 rows to 0 (both are `non_crypto_consensus`); that is the point, and it must be an explicit operator decision, not a silent filter.

**Risk / rollback:** high if flipped in one step — 277 rows disappear from the raw view and FOREX shows empty. Keep a `POLICY_ENFORCE_FOREX=0` kill switch and a `policy_blocked` lane for observation.

**Validation:** `python3 -m pytest tests/test_quality_gates.py -q -k forex` and new `tests/test_policy_emission_parity.py`; a dry-run that asserts `would_block = 277` today.

### P1-3 — FX/FUTURES quote pipeline v2

**Problem (verified).** `_fetch_equity_prices` only queues `=X`/`=F` symbols after the fallback branches (`audit_trail/dashboard_generator.py:1690-1710`), and a miss leaves the carried value (`:1752-1755`). The payload proves the outcome: 242/277 FOREX rows have no price; 90/118 OPEN are null; `stock_prices.json` has 61 symbols and no FX/futures. Futures zombies retain April/August prices (ZN=F 111.015625 = 2026-04-02, CL=F 112.06 vs 88.56, GC=F 4702.70 vs 3886.30), all with `pnl_pct = 0.0`.

**Change:**
- Add a provider chain dedicated to `=X` (open.er-api, yfinance `=X`) and `=F` (yfinance, CME settlement), each returning `{price, as_of, source, session}`.
- Reject a quote older than the class threshold (FX: 24 h weekend-aware; futures: last session close or `UNQUOTED`).
- Persist `quote_at`/`quote_source` per symbol; never write `current_price` from a stale cache without `quote_status="STALE"`.
- Keep the existing fail-open behavior: a provider failure produces `UNQUOTED`, not a fabricated price.

**Expected impact:** the 93 frozen FOREX OPEN rows become either genuinely priced or explicitly `UNQUOTED`; the FUTURES zombies stop presenting April prices as current.

**Risk / rollback:** new network paths can rate-limit or fail; cache-first, fail-closed to `UNQUOTED`, and `QUOTE_PROVIDER_V2=0` to revert.

**Validation:** fixture-based tests for `=X` and `=F` (no network), then one live smoke with `quote_at` assertions; compare 20 sampled FX pairs to open.er-api within 0.5%.

### P1-4 — Dedup by trade key with an emission window

**Problem (verified).** Exact-ID dedup (P0-5) leaves 67 `symbol+strategy+direction` groups / 198 extra FOREX rows. The emitter's ID uses minute granularity (`copy_trader_intel/multi_asset_copytrader_scraper.py:444`), and one scanner writes `signal_timestamp` at midnight (`:2411`), so the same trade re-emits across runs.

**Change:** canonical key `(symbol, strategy, direction, UTC-day, entry_price bucket)`; keep the first/latest by policy, annotate the rest `_duplicate_key`. Do **not** collapse different entry prices or different days — those are real re-entries. Publish `duplicate_groups`/`extra_rows` per class in the payload.

**Expected impact:** 198 phantom FOREX rows and 5 YM=F rows stop inflating counts; the audit trail remains complete.

**Risk / rollback:** medium — an over-broad key hides re-entries. Keep the window at one UTC day and the price tolerance ≤0.1%; `DEDUP_TRADE_KEY=0` reverts.

**Validation:** recompute the baseline from the archived payload (67 groups / 198 extras, verified) and assert the rebuilt payload has 0 uncollapsed same-day/same-price groups; add fixtures for a same-day re-entry at a different price (must survive) and the same price (must collapse).

### P1-5 — FUTURES closed ledger

**Problem (verified).** `picks.recent_closed` contains **0** FUTURES rows; `active_raw` has 13, all `pnl_pct = 0`; 6 YM=F rows are date-only and `_parse_timestamp` cannot parse them (`audit_trail/universal_pick_resolver.py:743-755`); there is no rollover/settlement handling for `=F`. Any FUTURES WR/PF from other surfaces (MRV n=52, pf_registry n=13) is therefore not backed by the primary feed.

**Change:** add `=F` to the resolver's price map (settlement or last trade), parse date-only as end-of-session (explicitly, with `_ts_precision="DATE_ONLY"`), add rollover-aware symbol continuity, and write resolved FUTURES rows to the same `recent_closed` feed. Start a new `FUTURES_V2` cohort; do not rewrite old rows.

**Expected impact:** FUTURES gets its first honest closed sample; the `0 closed ever` blocker is removed.

**Risk / rollback:** high — wrong settlement or rollover creates fake PnL. Gate behind `FUTURES_RESOLVER_V2=0` default, shadow-compare 50 rows, then enable; never retro-edit.

**Validation:** `python3 -m pytest tests/test_universal_pick_resolver.py tests/test_outcome_resolver_asset_class_persist.py -q`; replay 20 known futures bars and assert exit prices equal the session close.

### P1-6 — Retention contract

**Problem (verified).** `active_raw` is explicitly the pre-filter pool (`audit_trail/dashboard_generator.py:9529-9538`) and keeps everything: 158/277 FOREX `EXPIRED`, 10/13 FUTURES `EXPIRED`, 3,377 `EXPIRED` payload-wide. `_heal_no_price_row` (`audit_trail/universal_pick_resolver.py:931-963`) already nulls fabricated flat closes but does not remove them from inventory.

**Change:** add `lifecycle_state` (`OPEN`, `EXPIRED`, `PLACEHOLDER`, `RESOLVED`) and publish `inventory_count` vs `open_count` separately. Never delete; quarantine `EXPIRED` from default counts and sorting. Add `PLACEHOLDER` for FUTURES seeds that never had a tradable session. This is also the contract that P0-2's `UNQUOTED` and P0-4's `PLACEHOLDER` depend on.

**Expected impact:** FOREX "277 active" becomes "118 OPEN / 158 expired / 1 resolved"; FUTURES "13 active" becomes "3 OPEN / 10 expired". The user-facing number matches the tradeable number.

**Risk / rollback:** low — additive state and counts; `ACTIVE_RAW_QUARANTINE=0`.

**Validation:** assert `open_count + expired_count + resolved_count == total` for both classes on the next payload.

### P1-7 — Suppress impossible FOREX/FUTURES WR

**Problem (verified).** The live `summary_picks.json` publishes FOREX `win_rate_pct = 147.0` (8,536 wins / 8,968 losses against `resolved = 5,806`) and FUTURES `363.9` (222 / 357 against 61). The MySQL query counts `wins` and `losses` as overlapping sets and lets non-terminal rows with negative PnL count as losses (`tools/sync_summary_picks_json.py:63-65`), then divides by a different `resolved` set (`:161`).

**Change:** mark FOREX and FUTURES entries `invalid_denominator: true` (or omit `win_rate_pct`) until the denominator is rebuilt as `wins / (wins + losses)` over one resolved set. The full fix is shared with the EQUITY/ETF plan P0-4; this class plan only needs the suppression so no FOREX/FUTURES decision cites 147%/363.9%.

**Expected impact:** removes the two most extreme impossible class WRs from the only artifact publishing them; no other surface changes.

**Risk / rollback:** low — artifact-level only; consumers that ignore it see the old value if the flag is removed.

**Validation:** `python3 -c "import json;d=json.load(open('summary_picks.json'));assert all(not c.get('win_rate_pct') or c.get('invalid_denominator') for c in d['asset_classes'] if c['asset_class'] in ('FOREX','FUTURES'))"`.

---

## Do-not-do

1. **Do not flip `FOREX_HARD_DISABLE` to `1` as the first action.** It would hide 277 rows and the 118 OPEN inventory without fixing provenance, and the code default is currently OFF (`alpha_engine/config.py:345`), so the first observable effect would be a silent disappearance, not a clean block. Shadow-count first (P0-6), then enforce on new emissions (P1-2).
2. **Do not delete the 158 `EXPIRED` FOREX rows or the 10 `EXPIRED` FUTURES rows.** They are the only evidence of the zombie/auto-expiry rate; quarantine them instead (P1-6).
3. **Do not backfill date-only timestamps with `T00:00:00Z`.** That fabricates a midnight entry and corrupts hold-window and age math. Use the existing full `timestamp` or stamp `DATE_ONLY` (P0-1).
4. **Do not dedup by `symbol+strategy+direction` alone.** 67 groups include legitimate same-day re-entries. Require the UTC-day + entry-price window (P1-4).
5. **Do not relabel the 44 currency ETFs into ETF and then price them as FX.** The pricing provider differs (`=X` vs exchange ETF); the class fix (P1-1) and the quote fix (P1-3) must land together for those rows.
6. **Do not cite `summary_picks.win_rate_pct` for FOREX (147.0%) or FUTURES (363.9%).** The denominator is a different population (`tools/sync_summary_picks_json.py:63-65`, `:161`). Fix or suppress it (P1-7).
7. **Do not enable `FOREX_COPYTRADER_ENABLE=1`.** The existing gate comment documents WR 16.5% / PF 0.23 / n=696 for that source (`audit_trail/quality_gates.py:8850-8854`).
8. **Do not treat `current_price == entry_price` as a flat market.** On a Saturday that is Friday's close copied into both fields; the audited external deviations are −0.061% (USDCAD) and +0.038% (NZDUSD) (`sub/D_non_crypto.md:177-178`).
9. **Do not make the weekend fix by disabling the whole `multi-asset-scanner` workflow.** It would also stop valid FX/equity emissions; gate only the futures partition (P0-4).
10. **Do not retro-edit `recent_closed` or resolved history.** Add a new cohort/version tag instead (P1-5).

---

## UNVERIFIED

- **Exact DB write that persists `entry_time = "2026-11-14"`.** The dashboard path is verified end to end (emitter writes date-only `entry_date`; `_entry_ts_keys` prefers it at `dashboard_generator.py:8136-8154`; the value is written at `:8351-8352`), and the payload shows `entry_date = None` with `entry_time = "2026-11-14"`, consistent with the normalized pick dropping `entry_date`. The intervening MySQL row that supplied `entry_time` was not traced.
- **The audit's "158 FOREX rows >30 d".** Not reproducible as an age count. Verified: 158 `EXPIRED`; among 233 parseable rows, 114 are >30 d; 44 rows have no timestamp. Oldest `2026-02-20` is correct.
- **Live CI value of `FOREX_HARD_DISABLE`.** The repo default computes `False`; the deployed environment variable was not observable from the read-only repo. The 277 FOREX rows imply the gate was not active at build time.
- **Whether `cta_cross_asset_tsmom` is intentionally allowlisted or a stale entry.** It is blacklisted in `alpha_engine/config.py:298` and allowlisted in `non_crypto_policy.py:724`; the commit rationale for the divergence was not reconstructed.
- **CME holiday calendar.** P0-4's session guard covers weekends only unless a holiday calendar is added; US futures holidays (e.g. Thanksgiving) would still emit at the prior close. `UNVERIFIED` until the calendar is wired.
- **Realized slippage/fill quality for the FOREX/FUTURES picks.** All entries are candidate prices; no live fills exist in the repo. `UNVERIFIED`.
- **Visual/browser rendering of the new `UNQUOTED`/`PLACEHOLDER` badges.** Not implemented in this plan; no browser check was run.
