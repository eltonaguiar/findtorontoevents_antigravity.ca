# 2026-11-15 — ETF SHORT class gate, whole-ledger headline, catalyst/flow features

Three changes, all measured before and after.

## 1. ETF SHORT class gate (`ETF_SHORT_CLASS_BLOCK`)

**What was broken.** The ledger showed ETF SHORT as a class-wide sign error, not a per-strategy fluke
(`ai_tournament_picks_latest.json`, 2,242 closed picks):

| | n | WR | mean | PF | sum |
|---|---|---|---|---|---|
| ETF SHORT | 75 | **10.7%** | −2.56% | **0.09** | −192.1 |
| ETF LONG | 116 | **84.5%** | +2.66% | **8.28** | +309.0 |

The inversion is stable across the timeline (8.1% WR in the first half, 13.2% in the second), so it is a
structural error rather than one bad regime.

**What changed.**
- `alpha_engine/config.py`: `ETF_BLOCKED_DIRECTIONS = frozenset({"SHORT", "SELL"})`, with the evidence in the comment.
  ETF LONG is deliberately not in the set.
- `audit_trail/quality_gates.py`: gate inside `passes_active_gate()`, **placed first in the chain**. It tags
  `pick["_hf_quality_gate_reason"] = "etf_short_class_block"`.
  Exempt: `forward_test_only`, `forward_observation`, `paper_pilot`, `_monitor_mode` (measurement lanes keep collecting
  counter-evidence). Kill-switch: `ETF_SHORT_GATE_ENABLED=0`. Fail-open on any exception.
- `tests/test_etf_short_gate.py`: 7 tests — SHORT/SELL blocked, ETF LONG never tagged, reason string set, kill-switch
  bypass, all four measurement exemptions, and that `CRYPTO_BLOCKED_DIRECTIONS` still contains BUY/LONG/STRONG_BUY.

**A bug the tests caught.** The first version was inserted just before the M-042 COMMODITY gate, deep in the chain.
It never fired for real picks: an earlier gate rejected them first, so `passes_active_gate()` returned False for the
wrong reason and the block was untestable. The two failing tests (SHORT/SELL not tagged) exposed it; the gate was moved
to the top of the function, immediately after the monitor-tagging calls. Second run: **7/7 pass**.

**Effect of shipping only this gate** (crypto LONG excluded — it is already blocked in production by
`CRYPTO_BLOCKED_DIRECTIONS`, so counting it here would double-count a live fix):

| class | n | WR | mean | PF | compound (±10% cap) |
|---|---|---|---|---|---|
| ETF | 191 → 116 | 55.5% → **84.5%** | +0.61% → **+2.66%** | 1.46 → **8.28** | +186.6% → **+1,936.5%** |
| ALL | 2,242 → 2,167 | 46.3% → 47.5% | −0.94% → −0.89% | 0.77 → 0.79 | −99.7% → −98.2% |

Dropped: 75 trades, mean −2.56%, Σ −192.1, best of the dropped +4.4% (so nothing large was thrown away).
BOND, COMMODITY, CRYPTO, EQUITY, FOREX, FUTURES and PENNY are byte-identical before/after — the gate touches ETF only.

Honest limit: on the second ledger (`dashboard_data.json`, 4,142 picks) ETF SHORT is only n=8 and the change is
slightly negative (compound 13.4% → 7.2%). The 75-pick tournament sample is what makes this a class-level claim; the
second sample is too small to confirm or deny, and is reported rather than hidden.

Regression: `tests/test_direction_triple_gate.py` + `tests/test_crypto_gates_p0.py` + `tests/test_quality_gates.py`
→ **162 passed, 2 failed**. Both failures are FOREX tests
(`TestM044GateParity::test_forex_hard_disable_default_on`,
`TestForexCopytradeBypas::test_gate_on_still_blocks_other_forex_sources`) and they fail identically with
`ETF_SHORT_GATE_ENABLED=0`; the diff adds **zero** FOREX lines. Pre-existing, not caused by this change.

## 2. Whole-ledger compound next to the rolling-100 headline

**What was broken.** `summary.total_pnl_pct` is `total_pnl_pct_compounded_rolling_100` — the last 100 trades
(`dashboard_generator.py:16911`). A long positive ledger reads as dead after one bad week. `data/dashboard_payload.json`
shows it plainly: `compounded_ew +1631.88` vs `rolling_100 -45.04`.

**What changed.** `audit_dashboard/template.html`: a **"Whole ledger"** metric card rendered next to "Rolling 100",
sourced from `summary.total_pnl_pct_compounded_ew`, with a tooltip that explains the difference and prints
"Rolling-100 minus whole-ledger" so the gap is visible without arithmetic. Additive change — the existing headline,
its tooltip and every other card are untouched.

## 3. Catalyst, options-flow and VIX features in the hours harness

`tools/hours_skyrocket_reverse_engineer.py` now has three extra feature groups:

- **VIX regime** (hourly `^VIX` level and 1-bar change) — historical, 82% coverage after aligning to equity bars.
- **SEC catalyst recency** (EDGAR `8-K`, `10-Q`, `10-K`, `S-1`, `424B5`, `8-K/A` filing timestamps) — historical,
  29/35 tickers resolved, `hrs_since_filing` + `log1p` + `filing_24h`.
- **Options flow** (nearest-expiry put/call volume, put/call OI, ATM IV skew) — **live snapshot only**. yfinance has no
  historical chains, so these are printed for the watchlist and deliberately kept out of the label statistics.

Results (324,581 bars, base rate 14.52%):

| rule / feature | test precision | lift | note |
|---|---|---|---|
| VIX > 25 (stressed regime) | 18.61% | **1.39x** | n=17,182, avg fwd +0.41% — the strongest single rule found |
| filing in last 24h + breakout | 19.51% | **1.45x** | n=142, avg fwd **−0.30%** → statistically lifted but not tradeable |
| VIX falling + squeeze | 16.08% | 1.20x | n=48,150 |
| filing in last 24h (alone) | 14.79% | 1.10x | n=8,272, avg fwd −0.16% |

Model: **AUC 0.5549 with all features vs 0.5423 candle-only (+0.013)**, top-1% precision 14.37% vs 13.43% base.
VIX is the useful addition (`vix_level` AUC 0.512, 1.17x top-decile lift); filing recency barely moves the model
(`filing_24h` AUC 0.508, 1.0x) even though the breakout-conditioned rule lifts — a classic case of a conditional
pattern that is too rare and too costly to trade.

**Two defects found and fixed during this work:**
1. The rewrite dropped the `dist52` feature assignment while `build()` still referenced it → `KeyError: 'dist52'`.
   A presence check matched the *usage* and skipped the fix; the assignment is now verified by grep, not by a substring test.
2. EDGAR returns gzip regardless of the requested encoding, so the first run silently resolved **0 tickers**
   (`UnicodeDecodeError`). Now the response is decoded explicitly (`gzip.decompress` when the magic bytes are present) and
   the run reports `filings=29`.

## Verification performed

- `py_compile`: `quality_gates.py`, `alpha_engine/config.py`, both harnesses.
- `pytest tests/test_etf_short_gate.py` → 7 passed. Regression subset → 162 passed, 2 pre-existing FOREX failures.
- `python3 tools/direction_gate_analysis.py` → before/after tables above (dedup fixed: the ledger file was being analysed twice).
- `grep` confirms exactly one "Whole ledger" card, wired to `summary.total_pnl_pct_compounded_ew`.
- Harness run end-to-end twice: 324,581 bars, 6 classes, filings 29, options chains 10, report written (103 lines).

## Not done / next

- The full `tests/test_quality_gates.py` suite has two pre-existing FOREX failures that predate this change and should be
  triaged separately.
- Options flow stays snapshot-only until a historical chain source exists; until then it must not enter any backtest.
- Changes are local and uncommitted: `alpha_engine/config.py`, `audit_trail/quality_gates.py`, `audit_dashboard/template.html`,
  `tests/test_etf_short_gate.py`, `tools/hours_skyrocket_reverse_engineer.py`, `tools/direction_gate_analysis.py`, this file.
