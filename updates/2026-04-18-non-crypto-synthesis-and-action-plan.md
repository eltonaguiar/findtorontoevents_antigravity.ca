# Non-crypto active-picks + WR/PF — 5-doc synthesis and prioritized action plan

**Date:** 2026-04-18
**Scope:** Synthesizes diagnoses from Cursor, Kimi, Codebuff (codebuff agent), GitHub Copilot web agent, and ChatGPT Codex into a single canonical action list with ordering corrected for data-integrity prerequisites.

---

## Source diagnoses

| Author | File / branch | Length | Distinctive contribution |
|---|---|---|---|
| Cursor | [updates/2026-04-18-non-crypto-actives-and-wr-diagnosis.md](2026-04-18-non-crypto-actives-and-wr-diagnosis.md) (main) | 92 lines | Winner-filter + forex<30% gate analysis |
| Kimi | [updates/2026-04-19-non-crypto-zero-picks-and-low-wr-diagnosis.md](2026-04-19-non-crypto-zero-picks-and-low-wr-diagnosis.md) (`docs/nc-diagnosis-2026-04-19`) | 248 lines | 5-layer suppression model + killed-strategy supply gap with dates |
| Codebuff | [updates/NON_CRYPTO_ASSET_CLASS_DIAGNOSIS_2026-04-18.md](NON_CRYPTO_ASSET_CLASS_DIAGNOSIS_2026-04-18.md) (`diagnosis/non-crypto-asset-class-2026-04-18`) | 413 lines | Confidence cap squeeze math + 13-fix gate-blockage matrix |
| Copilot | [updates/2026-04-16-non-crypto-active-picks-diagnosis.md](2026-04-16-non-crypto-active-picks-diagnosis.md) (`copilot/investigate-non-crypto-assets-picks`) | ~120 lines | `multi_asset` mirror→payload empirical commodity dropout + 2nd-layer dashboard gate |
| Codex | [updates/2026-04-16-noncrypto-active-picks-and-fx-equity-diagnosis.md](2026-04-16-noncrypto-active-picks-and-fx-equity-diagnosis.md) (`codex/noncrypto-diagnosis-2026-04-16`) | 144 lines | Forex PF=0.034 = data-corruption artifact; equity loss concentrated in 6 sym + 6 strat; `active_raw` is post-killlist |
| Antigravity | [updates/2026-04-16-non-crypto-assets-active-picks-diagnosis.md](2026-04-16-non-crypto-assets-active-picks-diagnosis.md) (`docs-non-crypto-picks-diagnosis-2026-04-16`) | 53 lines | **Filename typos in `non_crypto_consensus.py` starve commodity/equity supply; futures file ignored entirely; equity TPs use 12-month yfinance analyst targets** |

---

## Critical reordering (per Codex finding #1)

**Every other doc's "fix forex edge" recommendation is operating on poisoned numbers.** Five corrupt JPY rows (`GBPJPY=X` and `AUDJPY=X` from `ig_contrarian_sentiment` and `myfxbook_retail_contrarian`) have `|pnl_pct| > 20` while actual entry→exit price move is < 1%. They sum to **-4855% PnL** and dominate the headline.

Reproduced and verified (2026-04-18):

```
FOREX (raw):              n=733  WR=50.75%  PF=0.007  total_pnl=-7212.36%
FOREX (|pnl|<=10 only):   n=726  WR=51.24%  PF=2.233  total_pnl=  +28.52%
FOREX (excl GBPJPY/AUDJPY): n=547  WR=53.56%  PF=2.284  total_pnl=  +25.61%
```

**Five rows reproduced:**
| symbol | strategy | direction | entry | exit | recorded pnl_pct | implied move % |
|---|---|---|---|---|---|---|
| GBPJPY=X | ig_contrarian_sentiment | SHORT | 215.557 | 215.856 | **-2305.15** | -0.139 |
| GBPJPY=X | ig_contrarian_sentiment | SHORT | 215.799 | 215.834 | **-2304.92** | -0.016 |
| AUDJPY=X | myfxbook_retail_contrarian | SHORT | 114.035 | 114.089 | **-81.73** | -0.047 |
| AUDJPY=X | ig_contrarian_sentiment | SHORT | 114.035 | 114.049 | **-81.70** | -0.012 |
| AUDJPY=X | myfxbook_retail_contrarian | SHORT | 113.805 | 114.062 | **-81.71** | -0.226 |

**Implication:** Until the ledger is sanitized, **do not adjust forex TP/SL caps, do not change the Forex<30% WR gate, and do not kill any forex strategy.** All those decisions need clean numbers.

---

## Prioritized action plan

### P0 — Data integrity (prerequisite for everything else)

| # | Action | File(s) | Risk | Status |
|---|---|---|---|---|
| 0.1 | Add `pnl_pct` sanity-check helper that flags rows where `|pnl_pct| > 20` AND `|implied_move_pct| < 1` AND prices are sane | [audit_trail/dashboard_generator.py](audit_trail/dashboard_generator.py) | Low — pure exclusion, no recompute | **DONE this branch** |
| 0.2 | Apply check inside `_is_valid_resolved_pick()` so corrupt rows fall out of all PF/WR/total-PnL aggregations | same | Low — single chokepoint | **DONE this branch** |
| 0.3 | Investigate upstream writer for the 5 corrupt rows (`copy_trader_intel/multi_asset_copytrader_scraper.py:1587, 2036, 2103`) — likely JPY pip-vs-percent confusion | [copy_trader_intel/multi_asset_copytrader_scraper.py](copy_trader_intel/multi_asset_copytrader_scraper.py) | Medium — needs reproduction | Deferred (P0a fix neutralizes blast radius first) |
| 0.4 | Move gate-attribution instrumentation **upstream of** [dashboard_generator.py:7173](audit_trail/dashboard_generator.py#L7173) (the kill-list filter that runs *before* `active_raw` snapshot) — Codex finding #3 corrects every other doc's instrumentation proposal | [audit_trail/dashboard_generator.py](audit_trail/dashboard_generator.py) | Low — read-only logging | Deferred to P1 |

### P0.5 — Trivial supply-pipeline bug fixes (Antigravity findings — safe to apply immediately)

These are isolated bugs with no policy implications. Even after fix, downstream Gate 0 still blocks equity/commodity at the alpha_engine layer, so the changes only restore the consensus engine to its designed behavior.

| # | Action | File:line | Bug | Status |
|---|---|---|---|---|
| 0.5a | Fix commodity filename typo: looks for `commodities_copytrader_picks.json`, actual is `commodity_copytrader_picks.json` | [copy_trader_intel/non_crypto_consensus.py:161](copy_trader_intel/non_crypto_consensus.py#L161) | 1-char typo, loads 0 picks | **DONE this branch** |
| 0.5b | Fix equity filename typo: looks for `equity_copytrader_picks.json`, actual is `stocks_copytrader_picks.json` | [copy_trader_intel/non_crypto_consensus.py:166](copy_trader_intel/non_crypto_consensus.py#L166) | Filename mismatch, loads 0 picks | **DONE this branch** |
| 0.5c | Add futures loader: `futures_copytrader_picks.json` exists and is populated but `non_crypto_consensus.py` never references it | same file | Missing block — not a typo, an omission | **DONE this branch** |

### P1 — Empirical instrumentation (unblocks informed policy decisions)

| # | Action | File(s) | Notes |
|---|---|---|---|
| 1.1 | Per-stage signal-count log: raw → after winner_filter → after Gate 0/1/8/9 → after dashboard kill list → final payload | `forward_validator.py`, `production_scanner.py`, `dashboard_generator.py` | Output as artifact; one CI run |
| 1.2 | Run [tools/_hc_noncrypto_diagnostic.py](tools/_hc_noncrypto_diagnostic.py) once with verbose mode to capture per-pick reject reasons | `tools/_hc_noncrypto_diagnostic.py` | Already exists, just need to run + log |
| 1.3 | Reconcile the 5 forex WR figures cited across docs (28.6% / 33.9% / 41.4% / 46.6% / 75%) to one canonical source | new tool | Each is from different aggregation window |

### P2 — Feeder metadata fixes (Codex findings #3, #6)

| # | Action | File(s) | Concrete target |
|---|---|---|---|
| 2.1 | `BND` arrives labeled `category="stock"` from KIMI feeder → routed to EQUITY | [KIMI_CLAW_RESEARCH_FEB162026/data/active_picks.json](KIMI_CLAW_RESEARCH_FEB162026/data/active_picks.json) writer | Fix at writer source, not at consumer |
| 2.2 | `SLV` arrives labeled `asset_class="Crypto"` from crypto_ml_edge feeder | [crypto_ml_edge/data/active_picks.json](crypto_ml_edge/data/active_picks.json) writer | Same |
| 2.3 | `_derive_asset_class()` trusts raw category before symbol-set lookup | [audit_trail/dashboard_generator.py:2948-3003](audit_trail/dashboard_generator.py#L2948-L3003) | Reorder: BOND_SYMBOLS / ETF_SYMBOLS check first for known-symbol overrides |
| 2.4 | `=F` contracts with `cta/cot/commodity` strategy hints get re-bucketed to COMMODITY (futures double-starvation) | [audit_trail/dashboard_generator.py:3049-3156](audit_trail/dashboard_generator.py#L3049-L3156) | Trust symbol prefix (`NQ=F`, `ES=F`, `YM=F`, `ZN=F` = futures), not strategy name |
| 2.5 | 83 EQUITY rows are misclassified non-equity (`QQQ`, `XLE`, `GLD`, `TLT`, `BCH-USD`, `GC=F`) | same | Resolved by 2.3 + 2.4 |

### P3 — Production-path supply gap (my finding + Kimi's #1.3)

| # | Action | File(s) | Notes |
|---|---|---|---|
| 3.1 | `production_scanner.py` does not import `BOND_STRATEGIES` / `ETF_STRATEGIES` / `FUTURES_STRATEGIES` / `FOREX_STRATEGIES` (`grep -c "_strategies"` = 0) | [alpha_engine/production_scanner.py](alpha_engine/production_scanner.py) | Either wire them in (multi-asset live), or remove from `non_crypto_policy.py` (crypto-only live) |
| 3.2 | Decide policy intent: crypto-only vs multi-asset live | new policy doc | Drives 3.1 direction |
| 3.3 | If multi-asset: align `WINNER_FILTER_CONFIG["allowed_asset_classes"]` (`forward_validator.py:399`) with `non_crypto_policy.NON_CRYPTO_STRATEGY_POLICY` | [forward_validator.py](alpha_engine/forward_validator.py) | Per-strategy allowlist replaces blanket class filter |

### P4 — Per-strategy / per-symbol surgery (Codex findings #4, #5)

| # | Action | Target | Empirical justification |
|---|---|---|---|
| 4.1 | Replace Gate 0 `_BLOCKED_CATEGORIES` blanket equity block with per-strategy + per-symbol blocks | [production_scanner.py:2074-2080](alpha_engine/production_scanner.py#L2074-L2080) | Excluding 6 sym (CRM, ADBE, NKE, ACN, PG, HD) lifts equity PF 0.834→1.071. Excluding 6 strategies lifts PF→1.195 |
| 4.2 | Hard-block toxic equity strategies: `goldmine_2x_consensus`, `Value + Quality`, `Earnings Drift`, `Dividend Aristocrats`, `Consecutive Beats`, `ML Ranker` | [audit_trail/quality_gates.py](audit_trail/quality_gates.py) `BLOCKED_STRATEGIES` | Codex per-strategy attribution |
| 4.3 | Hard-block toxic equity symbols (per-symbol kill list): CRM, ADBE, NKE, ACN, PG, HD | [audit_trail/quality_gates.py](audit_trail/quality_gates.py) `BLOCKED_ASSET_STRATEGY_PAIRS` | Codex per-symbol attribution |
| 4.4 | Reduce confidence cap squeeze (Codebuff finding) — replace flat 0.58 cap with confidence ramp tied to forward trade count | [non_crypto_quality_gate.py:634/670/697](alpha_engine/non_crypto_quality_gate.py#L670) | Only after P0 numbers are clean |
| 4.5 | Resolve TP/SL cap conflict (Codebuff finding, but Codebuff math wrong) — trace call order between `non_crypto_policy.clamp_non_crypto_tp_sl()` and `production_scanner.cap_tp_targets()`, decide which wins | [non_crypto_policy.py:182](alpha_engine/non_crypto_policy.py#L182), [production_scanner.py:936/942](alpha_engine/production_scanner.py#L936) | Independent of P0 |

### P5 — Followups not yet validated

- Forex<30% WR gate uses empty bucket (Cursor) — check whether `closed_picks.json` rows get tagged with `category="forex"` after asset_class normalization runs. If not, the gate will still be unreachable post-P0.
- ETF→equity normalization in `non_crypto_policy.normalize_asset_category()` line 269 — verify whether it's actually reached in any live path or is dead code.
- Killed strategy timeline (Kimi) — confirm `futures_ema_stack_momentum` / `futures_mean_reversion` / `extreme_oversold_bounce` / `vix_reversal` are gone via repo grep, not just claimed.

---

## What each doc got right and where they overlap

(See [Coverage matrix in conversation history] — abbreviated here.)

| Topic | Cursor | Kimi | Codebuff | Copilot | Codex | Antigravity |
|---|---|---|---|---|---|---|
| Gate 0 block | ✓ | ✓ | ✓ | ✓ stale-list | ✓ stale-list | ✗ |
| Conf cap 0.58 squeeze | ✗ | ~ | ✓ | ✗ | ✗ | ✗ |
| TP/SL conflict | ✗ | ✗ | ✓ math wrong | ✗ | ✗ | ✗ |
| Empty supply pipeline (alpha_engine side) | ✗ | ~ | ✗ | ✗ | ✗ | ✗ |
| Winner filter `crypto/meme` | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Forex WR<30% gate broken | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| ETF→equity normalization | ✗ | ✗ | ✓ note | ✗ | **✓ feeder evidence** | ✗ |
| Killed-strategy supply gap | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ |
| `multi_asset` mirror dropout | ✗ | ✗ | ✗ | ✓ | **✓ + strategy attribution** | ✗ |
| Dashboard 2nd-layer gate | ✗ | ✗ | ✗ | ✓ | ✓ | ✗ |
| Payoff asymmetry named | ✗ | ✗ | ✗ | ✓ | ✓ | ✗ |
| **Forex PF=0.034 = corruption** | ✗ | ✗ | ✗ | ✗ | **✓ only** | ✗ |
| **Equity loss concentrated in 6+6** | ✗ | ✗ | ✗ | ✗ | **✓ only** | ✗ |
| **`active_raw` is not pre-filter** | ✗ | ✗ | ✗ | ✗ | **✓ only** | ✗ |
| **`non_crypto_consensus.py` filename typos** | ✗ | ✗ | ✗ | ✗ | ✗ | **✓ only** |
| **Futures consensus loader missing entirely** | ✗ | ✗ | ✗ | ✗ | ✗ | **✓ only** |
| **Forex 0% close rate (no max-hold expiration)** | ✗ | ✗ | ✗ | ✗ | ✗ | **✓ only** |
| **Equity TPs from 12-mo yfinance analyst targets** | ✗ | ✗ | ✗ | ✗ | ✗ | **✓ only** |
| **Equity LONGs below 200d SMA** | ✗ | ✗ | ✗ | ✗ | ✗ | **✓ only** |

---

## Cross-doc inaccuracies (caught during review)

| Doc | Claim | Status |
|---|---|---|
| Codebuff | "Most non-crypto strategies have `allow_without_forward=False`" | **Wrong.** ETF/futures strategies in [non_crypto_policy.py:91-165](alpha_engine/non_crypto_policy.py#L91-L165) have `allow_without_forward=True` |
| Codebuff | "Scanner caps to 0.3%/0.2% → R:R can be < 1.0" | **Misleading.** 0.3/0.2 = 1.5 R:R, *higher* than policy's 1.25. Real conflict is which cap fires first |
| Cursor | "`scanner.py` strategies are wired" | **Wrong in spirit.** Wired in `scanner.py`, but `scanner.py` doesn't run in the emit path (`production_scanner.py` does, and it doesn't import them) |
| Copilot | Gate 0 blocks `etf, futures, bond` too | **Stale by ~2 days.** Current block is `{"equity", "stock", "commodity"}` only |
| Codex | Same as Copilot above | Same — both investigated before the 2026-04-18 narrowing |
| Kimi (chat summary) | "fail Gate2_compound_score_trust" | This is a [tools/_hc_noncrypto_diagnostic.py](tools/_hc_noncrypto_diagnostic.py) **diagnostic** name, not a live gate. Don't try to "fix Gate2" thinking it's a production gate |

---

## Convergent recommendation (5 of 5 agree)

Where every doc points the same direction (highest confidence to act on, but only AFTER P0):

1. **Replace `_BLOCKED_CATEGORIES` Gate 0** with per-strategy logic — Codex provides the empirical target list (P4.1, 4.2, 4.3).
2. **Add per-stage attribution logging** — corrected per Codex to insert *before* dashboard_generator.py:7173, not at the snapshot point (P1.1).
3. **Decide policy intent (crypto-only vs multi-asset live)** before any gate change — Codex's symbol/strategy concentration data shrinks this from "block all equity?" to "block CRM+ADBE+NKE+ACN+PG+HD and 6 strategies?" (P3.2).

---

## Measured impact of P0 fix (verified 2026-04-18 against the live ledger)

After adding `_pnl_pct_looks_corrupt()` and wiring it into `_is_valid_resolved_pick()`:

| Metric | Before P0 | After P0 | Δ |
|---|---|---|---|
| Forex rows excluded | 0 | 5 (exactly the Codex-identified set) | +5 |
| Forex total_pnl_pct | -7212.36 | **-2357.14** | +4855.22 |
| Forex headline PF | 0.007 | 0.021 | +0.014 |
| Crypto rows incorrectly excluded | n/a | **0** (verified against 8 crypto rows with `|pnl|>20`) | — |
| Total ledger size | 3500 | 3495 | -5 |

**Important nuance Codex's analysis missed:** Stripping the 5 corrupt rows does NOT flip forex to PF=2.07 as Codex implied. Codex's PF=2.07 figure came from `|pnl_pct| <= 10`, which removes legitimate large losses too. The conservative (correct) fix only removes the 5 demonstrably-corrupt rows.

**Updated reading of the forex problem:**
- ~67% of the headline forex bleed was the measurement artifact (-4855 / -7212)
- ~33% is real strategy underperformance (-2357 across 728 trades, avg -3.24%/trade)
- The "forex crisis" is *partly* a data bug, *partly* real edge problem — both warrant action, but with different urgencies

This refines the P4 priority: per-strategy forex attribution (which strategies / sources contribute the residual -2357%) is still needed, just with less catastrophic framing.

## Validation checklist (after P0 lands in CI)

- [x] `_pnl_pct_looks_corrupt()` correctly flags 5 known-corrupt JPY rows
- [x] Zero false positives on crypto rows with `|pnl_pct| > 20`
- [x] `_is_valid_resolved_pick()` propagates the exclusion to all `_filter_valid_resolved_picks` callers
- [x] `py_compile` passes
- [ ] Next CI dashboard run shows `picks.recent_closed` count drop by 5 vs prior run
- [ ] `summary.non_crypto_performance.categories.FOREX.total_pnl_pct` improves by ~+4855%
- [ ] No drop in CRYPTO row count (no false positives)
- [ ] P0.3 root-cause investigation: locate the writer that produced JPY pnl_pct as pip values

After P0 passes, the remaining policy questions in P3-P4 can be answered against trustworthy numbers — but with the refined understanding that forex still has a real (smaller) edge problem, not just a measurement artifact.
