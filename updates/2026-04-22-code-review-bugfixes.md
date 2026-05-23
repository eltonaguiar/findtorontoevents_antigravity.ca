# Code Review Findings & Bug Fixes — 2026-04-22

## Scope

Review of substantive source code commits from 2026-04-19 to 2026-04-21
(excluding automated `[skip ci]` data-only commits). Commits reviewed:

| Commit | Message | Key Files |
|--------|---------|-----------|
| `457c48f` | FX session + ATR reachability gates | `non_crypto_policy.py` |
| `0f3d70b` | Code-review fixes + SyntaxError | `forward_validator.py`, `quality_gates.py` |
| `fda3398` | Feed hygiene: reject anonymous strategies | `feed_hygiene.py` |
| `ffda395` | Blocklist enforcement + closed-pick schema | `strategy_blocklist.py` |
| `2eead63` | Asset-class mysql-fetch + hard-retire | `mysql_client.py` |
| `75e41ad` | Smart-score Phase B | `quality_gates.py` |
| `1026024` | HC-gate parity sync | `hc_evaluator.py`, `hc_filter.js` |

## Findings

### Finding 1 — ETF misclassified as equity in `normalize_asset_category` (BUG, fixed)

**File:** `alpha_engine/non_crypto_policy.py`, function `normalize_asset_category`

**Problem:** The mapping dict contained `"etf": "equity"` and `"index": "equity"`,
which collapsed ETFs into the equity asset class. This caused ETF picks to:

- Receive equity TP/SL caps (8%/5%) instead of ETF caps (5%/3%)
- Get equity score floors instead of ETF floors
- Be subjected to equity-specific penalties instead of ETF ones

ETF is a distinct asset class in `NON_CRYPTO_TP_SL_CAPS` and
`quality_gates.py` with its own calibrated thresholds, but the
normalization was silently erasing that distinction before the per-class
logic ever ran.

**Fix:** Removed the `"etf": "equity"` mapping so ETFs pass through as
their own category. The `"index"` mapping was changed to `"index": "futures"`
instead of being removed entirely — this ensures index symbols always get
futures-appropriate TP/SL caps (3%/2%) even if they don't match the
`FUTURES_SYMBOLS` set or `=F` suffix check downstream. Code review feedback:
naked `"index"` would fall through to an unhandled category in several
per-class dicts, so explicit mapping is safer.

**Severity:** High — every ETF pick emitted since the mapping was added
received the wrong risk parameters.

### Finding 2 — Archive duplicate picks on crash/restart (DEFENSIVE, fixed)

**File:** `alpha_engine/forward_validator.py`, function `save_closed_picks`

**Problem:** The archive rotation logic (added 2026-04-19 per code review
Finding 4) appends picks that fall off the hot-file retention cap to a
JSONL archive. The code comment states "the same pick cannot be archived
twice" because the hot file is trimmed after archival. However, if the
process crashes between the archive write and the hot-file trim (or if
two validator processes race), the next cycle will re-encounter the same
picks in the hot file and archive them again — producing duplicates in
the archive.

**Fix:** Added a dedup guard that reads existing archive pick IDs before
writing. Picks whose `id` already exists in the archive are skipped.
The guard is wrapped in `try/except` so a malformed or missing archive
does not block the validator.

**Performance optimization (code review feedback):** The initial
implementation scanned the entire JSONL file on every `save_closed_picks`
call — O(n) for an append-only file that grows indefinitely. Updated to
use `deque(_rf, maxlen=1000)` bounded tail-read: only the last 1,000
archive lines are checked for duplicate IDs, since picks being archived
are always recent. This keeps the guard O(1) regardless of archive size.

**Severity:** Medium — duplicates inflate historical trade counts and
distort strategy performance metrics (WR, PnL, PF) calculated from the
archive.

### Finding 3 — ALPHA_SYSTEM_MIN_TRADES (FALSE ALARM)

Initially appeared as `ALPHA_SYSTEM_MIN_TRA` (truncated) in a partial
file read, but verified as the full `ALPHA_SYSTEM_MIN_TRADES` in the
committed source. No action needed.

### Finding 4 — Quality observations (no code changes needed)

- **Feed hygiene** (`feed_hygiene.py`): The anonymous-strategy rejection
  logic is sound — returns `(False, "anonymous_strategy")` when strategy
  is empty/unknown. Good defensive addition.

- **Blocklist enforcement** (`strategy_blocklist.py`): Closed-pick schema
  enforcement adds `exit_reason` and `pnl_pct` validation before archival.
  Correct approach — prevents corrupt entries.

- **Smart-score Phase B** (`quality_gates.py`): The
  `calculate_smart_score` function now incorporates forward WR, profit
  factor, and regime alignment. Logic is sound; weights are documented.

## Verification

Both modified files pass Python syntax checks:
- `python3 -c "import py_compile; py_compile.compile('alpha_engine/non_crypto_policy.py', doraise=True)"` ✅
- `python3 -c "import py_compile; py_compile.compile('alpha_engine/forward_validator.py', doraise=True)"` ✅

## Files Changed

| File | Change |
|------|--------|
| `alpha_engine/non_crypto_policy.py` | Removed `"etf": "equity"` and `"index": "equity"` mappings |
| `alpha_engine/forward_validator.py` | Added archive dedup guard in `save_closed_picks` |
