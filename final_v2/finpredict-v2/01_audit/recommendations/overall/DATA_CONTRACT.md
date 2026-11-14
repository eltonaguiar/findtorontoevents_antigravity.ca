# DATA_CONTRACT — published pick/outcome fields

**Status:** proposed normative contract for `dashboard_data.json`, `dashboard_payload.json`, `summary_picks.json`, `pf_registry.json`, `db_health.json`, and every `audit_dashboard/data/*.json` sidecar.
**Version:** `schema_version: "2.0.0"` (breaking vs the current implicit schema).
**Scope:** read-side contract for the audit dashboard + write-side contract for producers.

Motivation (audited): the same concept currently has incompatible shapes — 4,148 raw rows / 3,851 unique IDs, 3,377 `EXPIRED` rows counted as inventory, 19/20 curated picks frozen at 0.00 %, 7 classes with WR > 100 % in `summary_picks`, `NaN`/`Infinity` literals that crash `JSON.parse`. This document makes every one of those representable and detectable.

---

## 0. Global rules

1. **JSON must be strict.** No `NaN`, `Infinity`, `-Infinity`. Non-finite numeric values serialize as `null`. `json.dump(..., allow_nan=False)` and `json.loads` on every payload.
2. **Unknown vs zero are different.** A missing observation is `null` plus a status; it is never `0`, `0.0`, `""`, `"N/A"`, or `"0%"`.
3. **Every payload carries provenance.** `generated_at`, `schema_version`, and `source` (producer id) are mandatory.
4. **All instants are ISO-8601 UTC with an explicit offset or `Z`.** Date-only strings are not instants; see §1.
5. **Every percentage is stored as percent points** (`2.74` = 2.74 %), never a 0–1 fraction, unless the field name ends in `_ratio`.
6. **Every derived metric declares its population** (§7). WR/PF without a population is invalid.

---

## 1. Timestamps

| Field | Type | Meaning | Rules |
|---|---|---|---|
| `signal_at` | string\|null | when the signal was generated | ISO-8601 UTC (`2026-11-14T13:53:28.525051Z`) |
| `entry_at` | string\|null | when the entry became effective | ISO-8601 UTC; if the source only has a date, set `entry_at_precision: "DATE"` |
| `closed_at` | string\|null | when the position closed | required when `status` is terminal |
| `quote_at` | string\|null | when `current_price`/`exit_price` was observed | required when `quote_status == "QUOTED"` |
| `generated_at` | string | payload build time | required on every payload |
| `entry_at_precision` | enum | `EXACT` \| `MINUTE` \| `DATE` | default `EXACT` |

Rules:
- Do **not** overload `entry_time`/`timestamp`/`created_at`. Producers may keep legacy aliases for one release, but the dashboards read only the canonical fields.
- `closed_at >= entry_at` and `closed_at <= generated_at + 5 min`; a violation is `INVALID_CHRONOLOGY`.
- Date-only rows (e.g. `ES=F` `entry_time: "2026-11-14"`) must set `entry_at_precision: "DATE"` and are excluded from age-in-hours calculations; age uses the UTC day boundary.

---

## 2. Price and quote provenance

### 2.1 Price fields

| Field | Type | Rules |
|---|---|---|
| `entry_price` | number\|null | `> 0` when set; `null` if unknown. Never `0` (85 raw rows currently have `entry_price <= 0` — invalid). |
| `current_price` | number\|null | last observed mark; `null` when unquoted |
| `exit_price` | number\|null | required for terminal `TP_HIT`/`SL_HIT`/`TIME_EXIT` |
| `take_profit` / `stop_loss` | number\|null | geometry: LONG `sl < entry < tp`; SHORT `tp < entry < sl` |

### 2.2 Quote provenance (new, mandatory on active rows)

```json
"quote_status": "QUOTED" | "UNQUOTED",
"quote_at": "2026-11-14T16:00:00Z" | null,
"quote_source": "BINANCE" | "BINANCE_VISION" | "BINANCE_US" | "COINGECKO"
              | "KUCOIN" | "CRYPTOCOMPARE" | "YAHOO" | "STOOQ" | "ER_API"
              | "CFTC" | "DB_CACHE" | "NONE",
"quote_age_minutes": 12.4 | null
```

Definition of `QUOTED`: `current_price > 0`, `entry_price > 0`, `quote_source != "NONE"`, and `quote_at` present. It does **not** require `current_price != entry_price` (a genuinely flat position is allowed), but the build-time honesty rule below overrides display:

> **Honesty rule H1 (build-time):** if `current_price` is missing, or `quote_source` is `NONE`, or `current_price == entry_price` and no quote was observed this build, then emit `quote_status: "UNQUOTED"`, `pnl_pct: null`, `pnl_status: "UNQUOTED"`. Never emit `pnl_pct: 0.0` as a substitute.
>
> **Honesty rule H2 (display):** the UI renders `UNQUOTED` as a grey `—`/`UNQUOTED` badge, never as `0.00 %`.

Today's violations this fixes: `picks.active` 19/20 at `pnl_pct == 0.0` (7 exact `current == entry`); `active_raw` 3,584/4,148 null `current_price`, 3,832/4,148 `pnl_pct == 0.0`.

---

## 3. PnL

| Field | Type | Rules |
|---|---|---|
| `pnl_pct` | number\|null | percent points, direction-aware, slippage-adjusted if `pnl_basis == "NET"`. `null` when not measurable. |
| `pnl_status` | enum | `REALIZED` \| `UNREALIZED` \| `UNQUOTED` \| `VOID` |
| `pnl_basis` | enum | `GROSS` \| `NET` (slippage/fees) |
| `exit_reason` | enum | `TP_HIT` \| `SL_HIT` \| `TIME_EXIT` \| `FORCE_CLOSED` \| `EXPIRED` \| `UNKNOWN` |

Rules:
- `pnl_status == "UNQUOTED"` ⇒ `pnl_pct is null`.
- Terminal status ⇒ `pnl_status == "REALIZED"` and `pnl_pct` finite, **except** `EXPIRED`/`VOID` which may be `null` with `pnl_status: "VOID"`.
- Sanity bounds: `|pnl_pct| <= 500` for active rows, `<= 100` for closed rows after the dollar-scale artifact filter (`tools/build_pf_registry.py` `DOLLAR_SCALE_ARTIFACT_THRESHOLD`). Out-of-range ⇒ `pnl_flagged: true`, `pnl_pct: null`, keep `pnl_raw`.
- Sign is the outcome of record for WR: `pnl_pct > 0` = win, `< 0` = loss, `== 0` = flat. Status labels (`TP_HIT`/`SL_HIT`) must agree with sign; contradictions become `status_conflict: true` and are excluded from WR.

---

## 4. Status

### 4.1 Lifecycle status (the only allowed values)

```
PENDING | OPEN | ACTIVE                     # unresolved
WON | LOST | TP_HIT | SL_HIT                # resolved with a directional outcome
CLOSED | TIME_EXIT | FORCE_CLOSED           # resolved by a rule, sign may be +/−/0
EXPIRED | VOID                              # never produced a measurable outcome
```

- `EXPIRED`/`VOID` **must not** be counted as active inventory and **must not** be in the WR denominator. They belong in an archive lane.
- Terminal set (for `summary_picks`): `WON, LOST, TP_HIT, SL_HIT, CLOSED, TIME_EXIT, FORCE_CLOSED, EXPIRED, VOID`.
- `status` is uppercase, normalized at write time (the DB currently stores `TP_HIT`, `SL_HIT`, `EXPIRED`, `CLOSED`, `WON`, `LOST`, `FORCE_CLOSED`, `UNKNOWN`).

### 4.2 Derived flags

| Flag | Meaning |
|---|---|
| `is_active` | `status in (PENDING, OPEN, ACTIVE)` **and** not expired by age |
| `is_terminal` | `status in (terminal set)` |
| `is_win` | terminal and `pnl_pct > 0` |
| `is_loss` | terminal and `pnl_pct < 0` |
| `is_flat` | terminal and `pnl_pct == 0` |
| `is_unquoted` | `quote_status == "UNQUOTED"` |

Invariant: `is_win + is_loss + is_flat == is_terminal` for every population; `is_win + is_loss <= is_terminal`.

---

## 5. Asset class

Canonical set (uppercase): `CRYPTO, EQUITY, ETF, FOREX, FUTURES, COMMODITY, BOND, INDEX, MEME, PENNY_STOCK, MANAGED_FUTURES, SPORTS, UNKNOWN`.

Normalization (`tools/sync_summary_picks_json.py:18-22` is the current partial version):
- `MEMECOIN` → `MEME` (currently mapped to `PENNY_STOCK`; that hides a separate class)
- `PENNY`, `PENNYSTOCK` → `PENNY_STOCK`
- empty/unknown → `UNKNOWN` and excluded from class-level rankings (never silently dropped from totals).
- `BOND`, `INDEX`, `MANAGED_FUTURES` are first-class, not aliases.

Every pick carries `asset_class` and `asset_class_source` (`EMITTER` \| `INFERRED` \| `FALLBACK`).

---

## 6. Identity / dedup

**Canonical dedup key** (matches `tools/build_pf_registry.py:818-835`):

```
(strategy_normalized, symbol_normalized, direction_normalized, trade_date, round(entry_price, 4))
```

where `trade_date = date(entry_at or signal_at or created_at)` in UTC.

Rules:
- `id` is a stable UUID/hash derived from the dedup key; re-emissions must reuse it.
- A payload's `active_raw` must have unique `id`s; duplicates are a contract violation.
- No `id` may appear in both `active_raw` and `recent_closed`.
- `EXPIRED`/`VOID` rows older than 30 days are archived, not carried.
- Current violations: 4,148 rows / 3,851 unique IDs (248 duplicated IDs, 297 extra rows); 381 duplicated `(symbol,strategy,direction)` groups with 3,213 extra rows; 56 cross-surface ID collisions; `db_health` 22,947 constant-PnL ghost rows.

---

## 7. Metric population envelope (mandatory on every WR/PF)

Every published statistic is wrapped:

```json
"metric": {
  "name": "win_rate_pct",
  "value": 42.21,
  "n": 22941,
  "n_emitted": 143156,
  "coverage_pct": 16.03,
  "population": "closed_deduped_policy_clean_net",
  "universe": "all_sources",
  "status_filter": ["WON","LOST","TP_HIT","SL_HIT","CLOSED","TIME_EXIT","FORCE_CLOSED"],
  "slippage_model": "M-069_round_trip_bps",
  "single_source_pct": 1.0,
  "computed_at": "2026-11-14T14:30:05Z"
}
```

Rules:
- `n` (rows in the metric) is never confused with `n_emitted` (rows attempted).
- If `n < 30` → `display: "INSUFFICIENT"` and the value is shown as `n<30` plus the count, not a percentage.
- If `single_source_pct >= 0.95` → `flag: "SINGLE_SOURCE_ARTIFACT"` and the metric is excluded from "winner" counts.
- The UI renders the population label next to the number (tooltip is not sufficient).
- `summary_picks` must be generated from a **single** population: `wins`, `losses`, `flat`, and `resolved` share one `WHERE status IN (terminal set)`; `wins+losses+flat == resolved`.

Current violation: `summary_picks` uses `resolved` from terminal statuses and `wins`/`losses` from all rows with a non-null PnL (`tools/sync_summary_picks_json.py:63-65`), then divides at `:161` → 7 classes > 100 %.

---

## 8. Sidecar metadata (all `audit_dashboard/data/*.json` except the main payload)

```json
"generated_at": "...",
"schema_version": "2.0.0",
"source": "tools/build_ic_analysis.py",
"owner_workflow": ".github/workflows/ic-analysis.yml",
"max_age_hours": 24,
"stale_policy": "HIDE"      // HIDE | WARN | DELETE
```

- Missing `generated_at` is allowed only for explicitly static config files, which must set `"static": true`.
- `hyrotrader_picks.json` currently has **no timestamp**; it must either gain one or be marked `static: true` and removed from "current account" panels.
- A central `sidecar_freshness_manifest.json` aggregates all of them for CI and the UI.

---

## 9. Payload envelope

```json
{
  "schema_version": "2.0.0",
  "generated_at": "2026-11-14T14:30:07Z",
  "source": "audit_trail.dashboard_generator",
  "picks": {
    "active": [...],
    "active_raw": [...],
    "recent_closed": [...]
  },
  "summary": {
    "total_active_picks": 0,
    "total_active_raw_picks": 0,
    "raw_preprune_count": 0,
    "pruned_expired": 0,
    "total_closed_picks": 0,
    "valid_closed_picks": 0
  },
  "data_freshness": { "age_hours": 1.6, "stale_warning": false }
}
```

Invariants:
- `total_active_picks == len(picks.active)`
- `total_active_raw_picks == len(picks.active_raw)`
- `pruned_expired` + `len(active_raw)` ≥ `raw_preprune_count` (archive accounting)
- `valid_closed_picks <= total_closed_picks`

Current violations: `summary.total_active_picks` 20 vs `performance.by_asset_class` active 158 vs `concentration_summary.total_active` 263 vs `active_raw` 4,148. The contract requires `performance.by_asset_class[].active` to equal the corresponding `picks.active` count or carry an explicit `population: "all_sources_active"` label.

---

## 10. Validation ladder

| Layer | Check | Fail behavior |
|---|---|---|
| Write | JSON-Schema (`audit_dashboard/data/schemas/pick.schema.json`) | quarantine row, log `INVALID_SCHEMA` |
| Write | honesty H1 (no fabricated 0 %) | force `UNQUOTED` |
| Build | population invariants (§7) | abort build |
| Build | dedup/identity invariants (§6) | prune + count |
| Build | strict JSON (no NaN/Infinity) | abort build |
| Deploy | sidecar manifest freshness | hide panel |
| CI | pytest contract suite (`acceptance_tests.md`) | fail PR |

---

## 11. Migration (non-breaking path)

1. **Release A (additive):** emit `quote_status`, `quote_at`, `quote_source`, `pnl_status`, `schema_version`; keep legacy fields. UI reads new fields when present.
2. **Release B (normalize):** honesty H1 on; `pnl_pct: null` for unquoted rows; UI `UNQUOTED` badge; `summary_picks` single population.
3. **Release C (enforce):** schema validation hard-fails; dedup/prune on; delete legacy aliases.

Each release is independently revertible; the contract fields are additive until Release C.
