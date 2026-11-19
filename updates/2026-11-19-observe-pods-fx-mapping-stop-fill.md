# audit3 — observe pods, FX symbol mapping fix, stop-fill overshoot (2026-11-19)

**Author:** Kilo (worktree `universal-pisces`, branch `review-financial-prediction-strategies`)
**Scope:** `reports/audit3_confirmatory.json`, `reports/hypothesis_registry.json`,
`alpha_engine/audit3_tribunal.py`, `alpha_engine/audit3_selection_alpha.py`,
`alpha_engine/stop_fill_overshoot.py` (new), `tools/fx_backfill.py` (new),
and their tests.

## 1. `observe` pod status (no honest `pre_registered` claim)

The quick-start candidate menu (VWAP MR, Bollinger MR, Faber TAA, USDJPY
momentum, commodity roll-yield) was going to be pre-registered. On inspection
none has a real hypothesis id, several are below the 100-trade forward floor,
and the strongest (VWAP reversion) is **contested**: a 1-bar execution lag
drops PF to 0.957 and CSCV PBO to 0.84–0.97 (`research/profitability/validation/
VWAP_VERDICT.md`). Pre-registering them would have been a false claim.

- Added an `observe` status to `audit3.confirmatory.v1` (`status_meaning`), and
  5 pods in that status, each with the contesting evidence and an
  `observe_reason`.
- Filed matching hypotheses `H-2026-11-19-01..05` in the registry (status
  `PRE_REGISTERED`, result verdict `OBSERVE`) so the `hypothesis_id` FK is real
  and the "declare before data" rule holds.
- `_pod_for` now confers confirmatory status **only** to `status ==
  "pre_registered"` (previously it allowed anything not in a blocklist, so an
  `observe` pod would have laundered rows into a promotion). New test
  `test_observe_pod_does_not_confer_confirmatory` pins it.

## 2. FX symbol mapping fix (forex selection alpha was silently 0)

`audit3_selection_alpha.symbol_candidates` only swapped `.`/`-` for non-CRYPTO,
so `AUDJPY=X`, `AUD-USD` and `AUD/JPY` never produced the bare `AUDJPY` that
`fx_prices.pair` stores. It now strips `=X`, `-`, `/`, `.`. Test added
(`test_fx_symbol_candidates_strip_the_vendor_suffixes`). 16 passed.

## 3. Stop-fill overshoot as a tracked measurement

New `alpha_engine/stop_fill_overshoot.py` (stdlib only) computes per-class and
overall planned vs realized stopped-trade loss, mean and **median** overshoot,
and exit-at-stop vs off-stop counts, over any closed-pick ledger. Makes the
quant-audit finding (crypto mean +1.071pp; median +41.9%) reproducible.
6 tests pass.

## 4. FX backfill tool (not applied)

New `tools/fx_backfill.py`: normalizes FX symbols, classifies USDT-quotes as
CRYPTO, preserves the PHP writer's inverse Yahoo tickers (`JPY=X` etc.), and
has a `--dry-run` that plans 15 pairs × 203 days without touching network/DB.
`--apply` is the only write path and is idempotent. **Not run** — needs DB
credentials and an operator decision.

## Verification

- `pytest` on the audit3 + stop-fill suites → **67 passed**.
- `reports/audit3_confirmatory.json` and `reports/hypothesis_registry.json`
  parse; 104 hypotheses (5 new); 8 pods (1 pre_registered, 1 post_hoc,
  1 declined, 5 observe).
- `python3 tools/fx_backfill.py --dry-run` → plan only, no network/DB.

## Not done / follow-ups

- The USDT→CRYPTO carve-out in `audit_trail/asset_classification.py:552-571`
  (which keeps `EURUSDT` as FOREX) is still in place; changing it reclassifies
  rows broadly and needs its own review.
- `fx_prices` is still stale; the backfill is planned, not applied.
- The 5 observe pods emit nothing yet; they need emitters wired before the
  forward clock can accrue rows for them.
