# Fabrication Red-Team: PR #232 (5 Operator-Ready Diffs)

**Date:** 2026-05-31
**Reviewer:** claude-opus-4-7 (red-team subagent)
**Source under review:** `reports/peer_claude-OPERATOR_READY_DIFFS_5_ITEMS_2026-05-31.md`
**PR:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/232

## TL;DR

| # | Item | Verdict | Reason |
|---|------|---------|--------|
| 1 | Confidence 0.8-bucket dampen | **NEEDS_CORRECTION** | Live-data citation is correct (PR #227 verified) but `_compute_ml_composite` patch is CRYPTO-only per PR #227 — Item 1 applies to ALL classes |
| 2 | FOREX kill + dxy_trend_filter add | **FABRICATED** | `dxy_trend_filter` strategy does NOT exist in `trading_picks` (n=0); "n=995 PF 1.63" citation invented. `forex_carry` (exact) also absent; real name `forex_carry_momentum` (n=1182) |
| 3 | COMMODITY COT quarantine | **FABRICATED** | `cot_commercial_extreme`, `cot_speculator_reversal`, `cot_managed_money_flip` — NONE exist. Real COT strategies: `cot_positioning` (n=59), `cftc_cot_commercial_signal` (n=41) |
| 4 | EQUITY `stocks_rsi2_pullback` un-kill | **NEEDS_CORRECTION** | Premise verified (strategy at config.py:270 in BLACKLIST, n=1421 in DB) BUT references wrong dict name `NON_CRYPTO_STRATEGY_POLICIES` (actual: `NON_CRYPTO_STRATEGY_POLICY` singular) |
| 5 | PENNY+MEMECOIN score floor | **FABRICATED** | Dict `MIN_SCORE_FLOORS_BY_CLASS` does NOT exist in `quality_gates.py`. Real dict is `ASSET_CLASS_SMART_THRESHOLDS` at line 488. Tests would import nonexistent symbol |

**Score: VERIFIED=0, NEEDS_CORRECTION=2, FABRICATED=3**

## Detailed per-item verification

### Item 1 — confidence 0.8-bucket dampen — NEEDS_CORRECTION

- Target file `alpha_engine/smart_picks_engine.py` exists.
- `_compute_ml_composite` defined at line 82 — MATCHES diff claim.
- Surrounding code lines 100-106 (`_calibrate_confidence`, `_effective_confidence_for_ranking`, `_trusted_forward_wr`) — MATCH diff context exactly.
- Live citation "0.8 bucket WR 22% vs 39-43%" — partial match. PR #227 body shows CRYPTO conf=0.7→42.3%, 0.8→22.0%, 0.9→37.5%. The "39-43%" claim slightly overstates 0.9 (actually 37.5%).
- **Scoping bug**: PR #227 explicitly proposes dampener gated `asset_class == CRYPTO`. The Item 1 diff omits the CRYPTO check, applying the dampener to ALL asset classes. This would dampen 0.8 conf EQUITY/FOREX/etc. picks for which the inverted-edge claim has not been verified.

**Fix**: add `pick.get("asset_class") == "CRYPTO"` to the gate.

### Item 2 — FOREX kill list — FABRICATED

- `BLACKLISTED_STRATEGIES` exists at `alpha_engine/config.py:257` — symbol VERIFIED.
- Live DB (`ejaguiar1_stocks.trading_picks`) strategy search:
  - `dxy_trend_filter` — **0 rows**. Strategy does not exist.
  - `cross_momentum_dxy` — 1 row. `dxy_correlation_regime` — 1 row.
  - `cta_cross_asset_tsmom` — 2015 rows (kill target exists).
  - `forex_carry` (exact) — 0 rows. Closest: `forex_carry_momentum` — 1182 rows.
- The cited "(n=995 PF 1.63 dxy_trend_filter)" is invented. The phrase "dxy_trend" appears only as a *concept* (variable name) in `reports/forex_salvage_2026-05-13.md` line 45 — never as a deployed strategy.
- Adding `dxy_trend_filter` to `NON_CRYPTO_STRATEGY_POLICY` would be a dead entry — no scanner emits it.
- Killing `forex_carry` (exact) would be a no-op since the live emitter is `forex_carry_momentum`.

**Recommendation**: rewrite Item 2 against actual strategy names. The killable losers are `cta_cross_asset_tsmom` (n=2015) and `forex_carry_momentum` (n=1182); the winning FOREX strategy claim needs to be re-derived from `pf_registry` or a real DB query, not paraphrased from a 2026-05-13 concept doc.

### Item 3 — COMMODITY COT quarantine — FABRICATED

- Live DB search for COT strategies returned only `cot_positioning` (n=59) and `cftc_cot_commercial_signal` (n=41).
- All three names in the diff (`cot_commercial_extreme`, `cot_speculator_reversal`, `cot_managed_money_flip`) — **0 rows each**, not emitted by any scanner.
- Quarantining nonexistent strategies has no effect. The real COT-only emitters that the COMMODITY "CT=F 57% concentration" pain comes from must be re-identified before any kill.

**Recommendation**: rerun mutation analysis on actual COMMODITY trading_picks rows and identify the real bleeding source-system × strategy pair. The non-COT rebuild stubs (`commodity_term_structure_contango`, etc.) are reasonable as opt-in proposals but cannot be justified by a kill of fictitious siblings.

### Item 4 — EQUITY rsi2 un-kill — NEEDS_CORRECTION

- `stocks_rsi2_pullback` is at `alpha_engine/config.py:270` in `BLACKLISTED_STRATEGIES` — VERIFIED.
- DB shows n=1421 picks — strategy is real.
- Diff at Item 4 references the dict `NON_CRYPTO_STRATEGY_POLICIES` (plural). Actual symbol is `NON_CRYPTO_STRATEGY_POLICY` (singular) at `alpha_engine/non_crypto_policy.py:182`.
- The diff's verification command `assert p['stocks_rsi2_pullback']['min_forward_wr']==0.55` would fail with ImportError because the imported name is wrong.
- "Phase 3 MC P(T2)=52%" — cited in narrative; not verified against `reports/`. Operator should confirm before un-killing a strategy with documented 10-trade 30% live WR.

**Fix**: rename all `NON_CRYPTO_STRATEGY_POLICIES` → `NON_CRYPTO_STRATEGY_POLICY` (also applies to Item 2's diff text).

### Item 5 — PENNY+MEMECOIN score floor — FABRICATED

- `audit_trail/quality_gates.py` does NOT contain `MIN_SCORE_FLOORS_BY_CLASS`. Confirmed via grep.
- The real dict at line 488 is `ASSET_CLASS_SMART_THRESHOLDS` with the same row shape (`min_score`, `min_fwr`, `min_trades`).
- The diff's "@@ -489,6 +489,9 @@" hunk header is plausibly the right line, but the dict name is wrong — `git apply` would fail.
- `get_effective_min_score` exists (line 545) — but it reads from `STRATEGY_SCORE_OVERRIDES` + `_class_floors` (a local helper), not from a top-level `MIN_SCORE_FLOORS_BY_CLASS`. Test `get_effective_min_score("ueps", "PENNY_STOCK")` would not behave as Item 5 expects without separately wiring the class-floor table into the function body.
- Pytest in the diff (`from audit_trail.quality_gates import MIN_SCORE_FLOORS_BY_CLASS`) would ImportError on first run.

**Fix**: rewrite Item 5 to target `ASSET_CLASS_SMART_THRESHOLDS`, and verify whether `passes_penny_meme_class_gate` actually consults this table for PENNY/MEMECOIN dispatch (it does not, per current code — class-membership only). A real fix likely needs a code change inside that function as well, not just a table addition.

## Summary

3 of 5 items are FABRICATED (invented function/dict names or live-data citations that do not exist in DB).
2 of 5 are NEEDS_CORRECTION (real targets but wrong identifier names or missing scoping gates).
0 of 5 are ready to apply as-is.

## Recommendation

**Revoke PR #232.** Reopen with corrected diffs after:
1. Re-grep target dict names from real source (`NON_CRYPTO_STRATEGY_POLICY`, `ASSET_CLASS_SMART_THRESHOLDS`).
2. Re-derive winning-FOREX strategy from actual `pf_registry.json` or DB query, not a 2026-05-13 concept doc.
3. Re-identify the bleeding COMMODITY COT emitters from real `trading_picks` rows (only `cot_positioning` and `cftc_cot_commercial_signal` exist).
4. Add CRYPTO-only scope gate to Item 1 per PR #227's stated cohort.

Follow-up correction PR will be opened separately with the docs-only red-team report itself.
