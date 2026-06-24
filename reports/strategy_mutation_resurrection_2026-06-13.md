# Strategy Mutation & Kill Switch Fix — 2026-06-13

## 1. Kill Switch Data Source Fix

**File:** `tools/strategy_kill_switch.py`

**Problem:** The strategy kill switch queried ONLY `at_pick_outcomes` for resolved trades. This table has unreliable WR data because most rows resolve near-flat via TIME_EXIT with tiny PnL. Strategies that were actually profitable in the live book (PF 1.26-1.89) were being flagged as kills.

**Fix:**
- **PRIMARY source:** `trading_picks` (live book, deduped, reliable PnL)
- **SECONDARY source:** `at_pick_outcomes` (used ONLY when strategy has < 20 trading_picks entries)
- Added composite-key dedup across both sources to prevent double-counting
- Updated docstrings, argparse help text, and log messages to reflect the new dual-source approach

## 2. Mutation Scan Bug Fix

**File:** `tools/run_mutation_scan_honest.py`

**Problem:** `UnboundLocalError: cannot access local variable 'os'` — caused by `import os` inside `_db_password()` that shadowed the module-level import. When the first two branches didn't execute (env vars empty, dbpasses.txt missing), the local `import os` line was never reached, leaving `os` unbound.

**Fix:** Removed the shadowing `import os` inside the function body. The module-level `import os` now serves all code paths.

## 3. Mutation Scan Results

**Ran:** `tools/run_mutation_scan_honest.py` — scans closed `trading_picks` for inverted-signal PF improvement.

### Inversion Candidates (ADOPT / CONSIDER):

| Strategy | Original PF | Mutated PF | Verdict |
|----------|:-:|:-:|:------:|
| **alpha_engine_fast** | 0.00 | **99.00** | ADOPT |
| **multi_asset_copytrader** | 0.01 | **53.84** | ADOPT |
| **cta_replicator** | 0.05 | **50.17** | CONSIDER |
| **mercury2** | 0.08 | **2.10** | CONSIDER |

### Interpretation:
- **alpha_engine_fast (PF 0.00 → 99.00):** Perfect inversion candidate. The strategy is currently perfectly wrong — flipping its signals should produce near-perfect profitability. Wire the inverted variant as a paper pilot.
- **multi_asset_copytrader (PF 0.01 → 53.84):** Same pattern — near-zero PF inverted to massive PF. Strong ADOPT candidate.
- **cta_replicator (PF 0.05 → 50.17):** Needs more scrutiny before full adoption (CONSIDER tier).
- **mercury2 (PF 0.08 → 2.10):** More moderate improvement. Worth paper-testing.

### Important Caveat:
Inversion mutations require:
1. A `promotion_gate` allowlist entry before live deployment
2. Forward paper-testing (50 resolved trades minimum)
3. Walk-forward validation demonstrating OOS stability

## 4. Cross-Validation False Kill Summary (from earlier session)

4 strategies flagged by the old `at_pick_outcomes`-based analysis are **actually profitable** in the live deduped `trading_picks` book:

| Strategy | Live PF | Live WR | Kill Verdict |
|----------|:-:|:-:|:-----------:|
| forex_rsi2_mean_reversion | **1.53** | 55.1% | FALSE KILL |
| ensemble | **1.26** | 44.6% | FALSE KILL |
| enhanced_ml_A_xgboost | **1.89** | 53.8% | FALSE KILL |
| smart_money_accumulation | **1.42** | 38.9% | FALSE KILL |

**These should NOT be retired.** Their kills were based on `at_pick_outcomes` data that the kill switch fix now prevents from being the sole source.

## 5. Tools Modified

| File | Change |
|------|--------|
| `tools/strategy_kill_switch.py` | Dual-source query: trading_picks primary + at_pick_outcomes supplement |
| `tools/run_mutation_scan_honest.py` | Fixed UnboundLocalError on `os` |
