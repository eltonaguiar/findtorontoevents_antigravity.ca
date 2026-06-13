# P2-11 Reverse-Split Detector for MEME/PENNY/CHEAP_STOCKS — 2026-06-13

**Author:** miniMax (claude opus 4 / miniMax-m3)
**Worktree:** `/home/eaguiar2015/findtorontoevents_antigravity.ca-worktrees/feat-minimax-next-steps`
**Branch:** `feat-minimax-next-steps` (will batch-push via orchestrator)
**Status:** v2 SCAFFOLD + v1-compat read-only sidecar. Wire-up to resolver deferred (see Wiring Plan §9).

## 1. Setup

Per CLAUDE.md Wire-Up Rule (lines 59-75) and Critical File Rules (lines 45-53),
this PR ships an **opt-in sidecar** with a documented `## Wiring Plan` (see §9).
It does not change production behavior.  The deliverable is:

- **`tools/detect_reverse_splits.py`** — `ReverseSplitDetector` class + CLI
- **`audit_dashboard/data/reverse_split_events.json`** — generated snapshot
  (66 symbols scanned; 23 split events found since 2023-01-01)
- **`data/splits/<symbol>.json`** — yfinance cache, TTL=7d (created on first run)

## 2. Existing handling (file:line evidence)

The codebase already has three layers of reverse-split handling.  Each is
referenced (and v2 augments) here:

### 2.1. v1 static registry

- `audit_trail/reverse_split_symbols.py:31-82` — hand-curated dict
  `REVERSE_SPLIT_SYMBOLS` mapping 7 known tickers (LODE, FFIE, WKHS, KULR, HOLO,
  GSAT, GE) to cumulative (ratio, date) tuples.  Updated 2026-06-04 to
  fix wrong dates and add missing cumulative splits (see
  `updates/2026-06-04-reverse-split-registry-fix.md`).
- `audit_trail/reverse_split_symbols.py:145-192` — `should_adjust_for_split()`
  computes the cumulative product of all splits whose effective date is
  AFTER the pick's submission timestamp.

### 2.2. v1 live-call site

- `audit_trail/universal_pick_resolver.py:30` — `from audit_trail.reverse_split_symbols import should_adjust_for_split`
- `audit_trail/universal_pick_resolver.py:1232-1271` — the actual adjustment
  in the resolver.  Three paths:
  1. Date guard (line 1238) — pick predates split → adjust.
  2. Price heuristic (lines 1247-1255) — post-split pick but `entry × factor ≈ current_price`.
  3. (Negative path) — no adjustment, no flag.

### 2.3. v1 consumer code

- `audit_trail/dashboard_generator.py:60-76, 5549` — `reverse_split_affected` field on output
- `tools/audit_truth_scan.py:160-164` — print flag in audit scan
- `tools/clean_ingest_v2.py:33, 116` — flag at ingest time
- `tools/audit_truth_review.py:20, 172` — flag in audit review
- `tools/build_clean_ledger_v2.py:99, 159` — schema column + WHERE filter for clean ledger

### 2.4. v1 known limitations (closed in v2)

- **Hand-curated only**: the registry has 7 symbols, but the cheap_stocks
  universe (`data/penny_universe_seed.json`) is 59 symbols and the live DB
  has symbols not in the registry (ACB, CYPH, EVTL — all had reverse
  splits in 2023-2024 that v1 missed).  v2 closes this gap by querying
  yfinance for every symbol in the universe.
- **At-resolve-time only**: the v1 site is `universal_pick_resolver.py:1242`.
  There is no proactive "this pick is at risk of being inflation-contaminated"
  warning at ingest time.  v2's `flag_picks()` provides this.

## 3. DB schema findings

Searched `information_schema.columns` for `split|adjust|corporate_action`:

| DB | Table | Column | Type | Notes |
|---|---|---|---|---|
| `ejaguiar1_stocks` | `trading_picks_v2` | `reverse_split_affected` | `tinyint(1)` | Set at clean-ledger build time |
| `ejaguiar1_stocks` | `at_raw_picks` | `reverse_split_affected` | `tinyint(1)` | Same |
| `ejaguiar1_stocks` | `at_signal_outcomes` | `reverse_split_affected` | `tinyint(1)` | Same |
| `ejaguiar1_stocks` | `at_raw_picks_kimi_archive_2026_06_05` | `reverse_split_affected` | `tinyint(1)` | Archive |
| `ejaguiar1_stocks` | `at_signal_outcomes_kimi_archive_2026_06_05` | `reverse_split_affected` | `tinyint(1)` | Archive |
| `ejaguiar1_stocks` | `trading_picks_v2` | (none) | — | No split events table |
| `ejaguiar1_backtests` | (none) | (none) | — | No split columns at all |

**Conclusion:** there is NO native split-events table in either DB.  The
`reverse_split_affected` column is a derived boolean, not a foreign key to
a splits table.  **Yfinance is the only available splits data source** for v2.

`trading_picks_v2` asset_class enum:
`('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','BOND','UNKNOWN')`
— note the DB uses `PENNY_STOCK` / `MEMECOIN`, NOT the legacy `PENNY` / `MEME`
names used in some strategy modules.  v2's `--class-filter` accepts
`MEME` / `PENNY` / `CHEAP_STOCKS` and maps them via `ASSET_CLASS_ALIASES`.

## 4. Live MEME/PENNY top losers (90d, trading_picks_v2)

| Symbol | n | Reverse-split-affected? |
|---|---:|---|
| DOGEUSDT | 649 | No (crypto, no splits) |
| PEPEUSDT | 104 | No |
| SHIBUSDT | 101 | No |
| TURBOUSDT | 69 | No |
| BONKUSDT | 64 | No |
| WIFUSDT | 53 | No |
| FLOKIUSDT | 36 | No |
| DOGEUSD | 9 | No |

Total MEME/PENNY closed in last 90d: **1346 rows; 0 with `reverse_split_affected=1`**.

Top 5 worst pnl_pct (last 90d, all MEMECOIN):

| Symbol | Source | pnl_pct | entry | exit | ts |
|---|---|---:|---:|---:|---|
| DOGEUSDT | predictions | -12.00% | 0.250 | 0.220 | NULL |
| DOGEUSD | KIMI_RiseOfTheClaw | -11.99% | 0.106 | 0.093 | 2026-02-25 |
| DOGEUSDT | sandbox_opposite | -11.34% | 0.093 | 0.082 | 2026-03-04 |
| DOGEUSDT | sandbox_opposite | -9.57% | 0.093 | 0.084 | 2026-03-04 |
| DOGEUSDT | sandbox_opposite | -7.96% | 0.093 | 0.086 | 2026-03-04 |

**Finding:** the MEME/PENNY live DB is dominated by crypto meme coins, which
do not have reverse splits.  The actual reverse-split exposure lives in
the EQUITY cohort (PLTR, NIO, MARA, GME, IONQ, RIOT — symbols that appear
in the cheap_stocks seed but get classified as EQUITY in the DB).  Of
those, only **WKHS** appears in production tables (2 rows in
`trading_picks_v2`, 1 row in `at_signal_outcomes`, all 3 correctly
flagged `reverse_split_affected=1`).

**Verdict:** the v1 registry has 7 tickers, but only 1 (WKHS) has any live
DB exposure.  The cheap_stocks universe (59 tickers) is broader than the
v1 registry (3-4 overlapping symbols: KULR, GSAT, GE, LODE).  v2 closes
the gap by querying yfinance for all 59 universe symbols.

## 5. Detector design

### 5.1. Three sources, merged in priority order

1. **v1 static registry** (`audit_trail/reverse_split_symbols.REVERSE_SPLIT_SYMBOLS`)
   — covers the 7 known tickers with verified dates/ratios.
2. **yfinance** (`yfinance.Ticker(symbol).splits`) — covers everything else
   in the cheap_stocks universe + any new symbols added by the user via
   `--symbols`.  Cached in `data/splits/<symbol>.json` with TTL=7d.
3. **Drift-based candidate discovery** (DB query) — for any new symbol
   not in the v1 registry, run a DB scan to find picks whose
   `entry_price` is implausibly small relative to a yfinance current-price
   snapshot.  Threshold per-class (mirrors `tools/ai_tournament/price_tracker.py`).

### 5.2. `SplitEvent` dataclass

```python
@dataclass
class SplitEvent:
    symbol: str
    split_date: str          # ISO YYYY-MM-DD
    ratio: float             # price-multiplier (1/yf for reverse, yf for forward)
    type: str                # 'reverse' or 'forward'
    source: str              # 'yfinance' | 'registry' | 'drift' | 'cache'
    confidence: float = 1.0  # 1.0 for confirmed, <1.0 for drift-only
    notes: str = ""
```

### 5.3. `flag_picks()` semantics

A pick is flagged `reverse_split_warning=True` if the symbol has a
registered split event with `evt_dt >= pick.signal_timestamp`.  The
cumulative factor is computed by v1's `should_adjust_for_split()`; v2
just decides *whether* to call it.

### 5.4. Cache contract

- `data/splits/<symbol>.json` written on first yfinance hit.
- TTL=7d (configurable via `ReverseSplitDetector(ttl_days=...)`).
- Empty splits are cached as `[]` (so we don't repeatedly hit yfinance
  for no-split tickers like AAPL).
- yfinance errors (delisted symbols) are caught and the next run retries
  (no negative caching for errors).

## 6. CLI usage

```bash
# Default run — registry + cheap_stocks universe, since 2026-03-01
python3 tools/detect_reverse_splits.py \\
    --class-filter PENNY --since 2026-03-01 \\
    --out audit_dashboard/data/reverse_split_events.json

# Wider window + drift-scan (DB query) for the MEMECOIN class
python3 tools/detect_reverse_splits.py \\
    --class-filter MEME --since 2024-01-01 \\
    --drift-scan --out /tmp/drift_audit.json

# Custom symbol list
python3 tools/detect_reverse_splits.py \\
    --symbols GME BBBYQ CTRM --since 2023-01-01

# Dry-run (no file write)
python3 tools/detect_reverse_splits.py \\
    --class-filter PENNY --since 2026-03-01 --dry-run
```

Output: stdout summary + JSON file.  JSON schema:
```json
{
  "generated_at_utc": "...",
  "source": "registry+yfinance",
  "filter": {"class_filter": "PENNY", "since": "2023-01-01", "until": "2026-06-13"},
  "symbols_scanned": [...],
  "drift_candidates": [...],
  "events": [
    {"symbol": "LODE", "split_date": "2025-02-25", "ratio": 10.0,
     "type": "reverse", "source": "registry", "confidence": 1.0, "notes": "1-for-10"}
  ]
}
```

## 7. Reproducer

```bash
cd /home/eaguiar2015/findtorontoevents_antigravity.ca-worktrees/feat-minimax-next-steps
python3 -c "import py_compile; py_compile.compile('tools/detect_reverse_splits.py', doraise=True)" && echo "PYCOMPILE OK"
python3 tools/detect_reverse_splits.py --class-filter PENNY --since 2023-01-01 --out /tmp/p2-11_repro.json
# Idempotency check (events list must be identical):
python3 tools/detect_reverse_splits.py --class-filter PENNY --since 2023-01-01 --out /tmp/p2-11_repro2.json
python3 -c "
import json
a=json.load(open('/tmp/p2-11_repro.json'))['events']
b=json.load(open('/tmp/p2-11_repro2.json'))['events']
print('idempotent:', sorted(map(str,a)) == sorted(map(str,b)))
"
```

Expected: `PYCOMPILE OK`, `23 events` (in 2023-01-01..2026-06-13), `idempotent: True`.

## 8. Live result (2026-06-13 05:01 UTC)

- `audit_dashboard/data/reverse_split_events.json` (5517 bytes)
- 66 symbols scanned (7 from v1 registry + 59 from
  `data/penny_universe_seed.json`)
- 23 split events found across 13 symbols
- All splits are in 2023-2025; **0 splits in 2026-03-01..2026-06-13** (the
  user's target window) — i.e. the live DB is clean for the most recent
  90d, but the v2 detector would catch any new reverse splits via the
  yfinance cache TTL=7d.

Sample of the events found:
```
LODE   2025-02-25 x 10.00 reverse src=registry
FFIE   2023-08-28 x 80.00 reverse src=registry
FFIE   2024-03-01 x  3.00 reverse src=registry
FFIE   2024-08-19 x 40.00 reverse src=registry
WKHS   2024-06-17 x 20.00 reverse src=registry
WKHS   2025-03-17 x 12.50 reverse src=registry
WKHS   2025-12-08 x 12.00 reverse src=registry
KULR   2025-06-23 x  8.00 reverse src=registry
GSAT   2025-02-11 x 15.00 reverse src=registry
HOLO   2024-02-20 x 10.00 reverse src=yfinance
HOLO   2024-10-09 x 20.00 reverse src=yfinance
HOLO   2025-04-21 x 40.00 reverse src=registry
GE     2021-08-02 x  8.00 reverse src=yfinance
ACB    2024-02-20 x 10.00 reverse src=yfinance   # NOT in v1 registry
CYPH   2023-06-21 x 10.00 reverse src=yfinance   # NOT in v1 registry
EVTL   2024-09-23 x 10.00 reverse src=yfinance   # NOT in v1 registry
WIT    2024-12-11 x  0.50 forward src=yfinance
CIG    2024-05-24 x  0.77 forward src=yfinance
(...)
```

**Newly-detected (v2-only, NOT in v1 registry):** ACB, CIG, CYPH, EVTL,
WIT.  v2 covers **6 more symbols** than v1 for the 2023-2025 window.

## 9. Wiring Plan

**Target caller:** `audit_trail/outcome_resolver.py::resolve_pick`
(specifically the function that calls
`audit_trail/universal_pick_resolver.py:1242 should_adjust_for_split(...)`).

**Wire-up scope:** in addition to the v1 registry check at line 1242,
add a fallback call to `ReverseSplitDetector().detect(symbol, since=...,
until=...)` to catch any symbol NOT in the v1 registry.  This would
close the ACB/CYPH/EVTL/WIT gap surfaced in §8.

**Caller file/function:**
- File: `audit_trail/outcome_resolver.py`
- Function: `resolve_pick(symbol, pick_timestamp, entry_price, current_price)`
- Specific insertion point: immediately before the
  `should_adjust_for_split(pick.get("symbol", ""), _pick_ts)` call on
  `audit_trail/universal_pick_resolver.py:1242` (since v1 is the importer).

**Expected PR:** batch with the next `outcome_resolver` refactor
(proposed PR title: `feat(resolver): v2 reverse-split discovery layer
(v1 registry + yfinance drift detection)`).  Target: **next sprint
(2026-06-15 .. 2026-06-19)**.

**Acceptance criteria for the wire-up PR:**
1. Re-run `tools/detect_reverse_splits.py --class-filter PENNY --since
   2024-01-01 --drift-scan` and confirm the new symbol list is loaded by
   the resolver.
2. Pick a known affected symbol (ACB, CYPH, EVTL — none in v1 registry)
   and submit a synthetic pre-split pick; confirm the entry price is
   adjusted by the correct cumulative factor.
3. Live DB scan: `SELECT COUNT(*) FROM trading_picks_v2 WHERE
   asset_class IN ('PENNY_STOCK','MEMECOIN') AND entry_price * 1.0 <
   (current_price / 10)` to find pre-split picks the resolver would now
   catch.

## 10. Open questions

1. **DB-driven source preferred** — Is there a corporate-actions feed
   in production (e.g. Finnhub, FMP, NASDAQ API) we should wire to
   instead of yfinance?  yfinance is fine for this scaffolding, but a
   production-grade data source would have higher reliability.  The
   scanner `data/earnings/*/latest.json` files don't include splits.
2. **FFIE yfinance error** — yfinance 1.3.0 raises
   `AttributeError: 'PriceHistory' object has no attribute '_dividends'`
   for FFIE (delisted).  v2 falls back to v1 registry (which has FFIE
   with correct 80×3×40=9600 cumulative factor).  When yfinance 1.4+
   ships the fix, the v2 cache for FFIE will refresh.
3. **Forward splits** — the detector emits forward splits (e.g. WIT,
   CIG) as `type=forward` with `ratio<1.0`.  The v1 registry only
   tracks reverse splits.  Decision needed: do we want to flag forward
   splits in the resolver?  They would *deflate* WR, not inflate, so
   the case is weaker.  Current v2 behavior: emit them in the events
   list but `flag_picks()` only matches on `evt_dt >= pick.signal_timestamp`
   (irrespective of type) — operator can filter on `type` in the JSON.
4. **Split events in 2026** — as of 2026-06-13, there are 0 reverse
   splits in the cheap_stocks universe with effective dates in 2026.
   This is consistent with the v2-vs-v1 finding in §8 (the cheap_stocks
   universe is currently quiet).  If a 2026 split occurs, the yfinance
   cache TTL=7d will pick it up on the next CLI run.
5. **The drift-scan is per-class** — the current implementation queries
   `trading_picks_v2` only.  The cheap_stocks universe also has rows
   in `at_signal_outcomes`.  A future enhancement could UNION across
   all relevant tables.

## 11. Files

- `/home/eaguiar2015/findtorontoevents_antigravity.ca-worktrees/feat-minimax-next-steps/tools/detect_reverse_splits.py` (new, 432 lines)
- `/home/eaguiar2015/findtorontoevents_antigravity.ca-worktrees/feat-minimax-next-steps/audit_dashboard/data/reverse_split_events.json` (new, 5.5 KB)
- `/home/eaguiar2015/findtorontoevents_antigravity.ca-worktrees/feat-minimax-next-steps/data/splits/*.json` (new, yfinance cache)
- `/home/eaguiar2015/findtorontoevents_antigravity.ca-worktrees/feat-minimax-next-steps/reports/p2-11_reverse_split_detector_2026-06-13.md` (this file)

## 12. References

- `audit_trail/reverse_split_symbols.py` — v1 static registry
- `audit_trail/universal_pick_resolver.py:1232-1271` — v1 live call site
- `updates/2026-06-04-reverse-split-registry-fix.md` — recent v1 refactor
- `reports/zoo_reverse_split_scope_gap_2026-06-04.md` — 63 pre-split
  tournament_picks caught by drift detection (zoo, 2026-06-04)
- `tools/ai_tournament/price_tracker.py:496-540` — drift-based
  MISPRICED_ENTRY detection (the zoo-suggested replacement for the
  hand-curated registry; v2 keeps the registry as ground truth and
  adds discovery on top)
- `data/penny_universe_seed.json` — 59-symbol cheap_stocks universe
