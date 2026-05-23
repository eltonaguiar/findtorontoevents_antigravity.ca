# Hedge Fund Enhancement — Phase 0 Action Plan v3

**Source:** `reports/HEDGE_FUND_ENHANCEMENT_PR_2026_05_02_VERBATIM.md`
**Repo:** [eltonaguiar/findtorontoevents_antigravity.ca](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca)
**Current:** 506 resolved trades, Sharpe 2.83, PF 3.99 | **Target:** Golden Portfolio — Sharpe 4.20, PF 7.35
**Status:** ⚠️ PLAN ONLY — No code changes made. Awaiting approval before execution.

---

## Complete Codebase Audit Results

> [!IMPORTANT]
> **9 of 13 recommended emergency items are already implemented.** Only 4 actions remain.

### ✅ Already Done (No Action Needed)

| # | Item | Evidence | File:Line |
|---|---|---|---|
| 1 | Kill `quan_engine_scalp` | In `strategy_kill_list.json` L3 AND `PERMANENTLY_KILLED_STRATEGIES` | `quality_gates.py:786` |
| 2 | Kill `st_rsi_momentum_confluence` | In `PERMANENTLY_KILLED_STRATEGIES` | `quality_gates.py:799` |
| 3 | Kill `copy_hl_lb_None` | In `PERMANENTLY_KILLED_STRATEGIES` | `quality_gates.py:834` |
| 4 | Abolish `WINNER_FILTER` | Never existed — full ripgrep returns zero matches | N/A |
| 5 | Score floor 40 | `scoreAbsoluteFloor: 40` | `hc_filter.js:24` |
| 6 | Confidence 0.85–0.90 unblocked | Gate 7b removed 2026-04-23 (commented out) | `hc_filter.js:377-385` |
| 7 | R:R floor lowered | `min_risk_reward: 0.8` (below report's proposed 1.25) | `hf_quality_gates.json:6` |
| 8 | ATR-based adaptive SL/TP | `adaptive_stops.py` exists (509 lines, MFE/MAE calibration) | `alpha_engine/adaptive_stops.py` |
| 9 | Resolver per-class noise thresholds | `PNL_WIN_THRESHOLD_BY_CLASS` with 5bp non-crypto floor | `outcome_resolver.py:115-126` |

### ⚠️ Partially Done

| # | Item | Current State | Remaining Work |
|---|---|---|---|
| 10 | Forex/Commodity suspension | Per-symbol blacklists exist (`FOREX_BANNED_SYMBOLS`, `COMMODITY_BLACKLIST`, `COMMODITY_BANNED_STRATEGIES`). Per-class confidence floors active. Resolver v2 bar-replay fix deployed. | No full class-level suspension needed — granular gates are more surgical |
| 11 | `enhanced_ml_A_xgboost` kill | Listed as mutation candidate (L806 commented out), not killed per mutate-before-kill policy | Decision needed: kill or keep mutating |
| 12 | Whitelist/kill contradiction audit | `test_kill_list_audit.py` exists with basic tests | Need cross-check test between `protected_strategies` and kill lists |

### ❌ Still Needed (4 Items)

---

## Action 1: Suspend Crypto C-Tier [P0, ~1 hour]

**Why:** PF 0.36, WR 28%, −46.59% PnL on n=318 trades. Guaranteed negative EV.

**Where:** `alpha_engine/hedge_fund_quality_gate.py`

**What:** Add C-Tier hard block at L238, before the existing CRYPTO checks:
```python
# Phase 0 triage: C-Tier suspension [Ch.1, Grade A+]
# PF 0.36, WR 28%, −46.59% PnL on n=318. Env override: HF_CRYPTO_CTIER_ENABLED=1
CRYPTO_CTIER_SUSPENDED = os.environ.get("HF_CRYPTO_CTIER_ENABLED", "0") != "1"
```

In `passes_hedge_fund_gate()`, add inside `if ac == "CRYPTO":` block (before existing banned symbol check at L239):
```python
tier = str(pick.get("hf_conviction_tier") or pick.get("tier") or "").upper()
if CRYPTO_CTIER_SUSPENDED and tier == "C":
    return False, "HF_GATE: Crypto C-Tier suspended (PF 0.36, WR 28%, −46.59% PnL on n=318)"
```

Also add to `config/hf_quality_gates.json`:
```json
"crypto_ctier_enabled": false,
"note_ctier": "C-Tier: PF 0.36 on n=318. Suspended per HEDGE_FUND_ENHANCEMENT_PR. Re-enable only after triple-screen rebuild."
```

**Done criterion:** C-Tier output = 0 for 48h; shadow log clean.

---

## Action 2: Disable LONG_ONLY Flag [P0, ~10 min]

**Why:** Shorts have 7.8pp higher WR than longs. Current flag blocks ALL crypto shorts from Smart Picks. The existing regime gate (`_crypto_short_gate_block_reason()` at L658-681) already provides env-flag-based SHORT blocking in bull regimes — so disabling LONG_ONLY doesn't remove safety.

**Where:** `audit_trail/quality_gates.py` line 534

**What:**
```python
# BEFORE:
SMART_PICKS_CRYPTO_LONG_ONLY = True

# AFTER:
SMART_PICKS_CRYPTO_LONG_ONLY = False  # Phase 0: shorts have +7.8pp WR edge; regime gate still active via CRYPTO_SHORT_REGIME_GATE_ENABLED env flag
```

**Safety net:** `CRYPTO_SHORT_REGIME_GATE_ENABLED=1` env var blocks shorts in bull regime. `CRYPTO_SHORT_DISABLED=1` is the full kill-switch.

**Done criterion:** Crypto SHORT picks flow through Smart Picks; WR monitored for 48h.

---

## Action 3: Add ml_score Gate (Shadow Mode) [P0, ~2 hours]

**Why:** elite_score has −0.17 correlation with profitability and 44.1% accuracy. ml_score AUC is 0.5785 vs elite_score 0.5458. Shadow-blocked picks at ml_score ≥ 0.82 show 58.8% WR.

**Where:** `alpha_engine/hf_quality_gate.py` lines 100-102

**What:** Replace the single elite_score check with a dual-path gate:
```python
# Phase 0: ml_score gate (shadow mode). Set use_ml_score_gate=true after 14d validation.
use_ml_gate = cfg.get("use_ml_score_gate", False)
if use_ml_gate:
    ml_score = float(scored.get("ml_score") or scored.get("ml_composite_score") or 0)
    ml_floor = float(cfg.get("min_ml_score", 0.82))
    if ml_score < ml_floor:
        return "hf_gate_ml_score"
else:
    # Legacy path — preserved until ml_score shadow validation completes
    elite = float(scored.get("elite_score") or scored.get("score") or 0)
    if elite < float(cfg.get("min_elite_score", 80)):
        return "hf_gate_elite"
```

Add to `config/hf_quality_gates.json`:
```json
"use_ml_score_gate": false,
"min_ml_score": 0.82,
"note_ml_gate": "Shadow-deploy: flip use_ml_score_gate=true after 14d validation. ml_score AUC 0.5785 vs elite AUC 0.5458."
```

**Done criterion:** Both scores logged side-by-side; flip after 14d shadow proves ≥5% WR improvement.

---

## Action 4: UNKNOWN Reclassification [P1, ~4 hours]

**Why:** 410 UNKNOWN picks deliver 45.37% WR — best average PnL across all classes. Likely mis-classified equities/ETFs routed through crypto pipeline.

**Where:** New function in `signal_aggregator/picks_router.py` or `audit_trail/quality_gates.py`

**What:** Symbol-pattern-based reclassification:
- `*USDT` / `*USDC` → CRYPTO
- `*=X` → FOREX
- `*=F` → COMMODITY
- 1-5 uppercase letters matching known ETF/equity lists → ETF/EQUITY
- Fallback: keep UNKNOWN

**Done criterion:** UNKNOWN count drops from 410 to <50; reclassified picks appear in correct AC dashboards.

---

## Items NOT Requiring Code Changes (Deferred/Already Handled)

| Item | Status | Notes |
|---|---|---|
| `MAX_RESOLVE_RETRIES` cap | Not found in codebase | Resolver v2 already uses bar-replay + `_resolve_retry_needed` flag instead of retries. No cap needed. |
| Forex class suspension | Not needed | Granular per-symbol + per-strategy bans already active. Resolver v2 fixes the measurement artifact. |
| Commodity class suspension | Not needed | `COMMODITY_BLACKLIST` restricts to HG=F + PL=F only. `COMMODITY_CONFIDENCE_MIN = 0.70` gates quality. |
| Wire adaptive stops | P1 | `adaptive_stops.py` built but not wired. Do after Phase 0 gate changes stabilize. |
| Strategy consolidation 406→50 | P2 | Large effort. Defer to Phase 2. |

---

## Per-Asset-Class Research Protocols

### CRYPTO
- Wire `adaptive_stops.py` for dynamic SL/TP (50.9% SL hit rate = static −8% too tight for 3-5% daily ATR)
- Binance funding rate API integration (free `/fapi/v1/fundingRate`)
- HMM regime classifier via `hmmlearn` library
- Score-bin recalibration (non-monotonic: bins 0–9 outperform 20–29)

### EQUITY (Crown Jewel — Sharpe 5.395)
- Scale allocation from ~20% to 35-45%
- PEAD earnings drift pipeline (`earnings_calendar_fetcher.py` exists)
- Factor attribution (`factor_attribution.py` sidecar exists)
- Sector rotation via `yfinance`

### FOREX (True WR 48.7%, PF 3.59 — measurement artifact fixed)
- Resolver v2 bar-replay already deployed — monitor resolution rate recovery
- G10 carry trade sleeve (FRED API for rate differentials)
- COT positioning data (CFTC, free weekly)

### COMMODITY (Restricted to HG=F + PL=F)
- Triple-screen rebuild (RSI + MACD + volume on weekly/daily/4h)
- Seasonal patterns via USDA/EIA reports
- COT commercial positioning

### BOND / ETF
- Bond: lower elite_score floor via per-AC override in config
- ETF: 10-day hold cap, NAV discount tracking

---

## Recommended Libraries

| Library | Purpose | Link |
|---|---|---|
| `riskfolio-lib` | HRP/MVO/CVaR portfolio optimization | [dcajasn/Riskfolio-Lib](https://github.com/dcajasn/Riskfolio-Lib) |
| `quantstats` | Sharpe/Sortino/drawdown reporting | [ranaroussi/quantstats](https://github.com/ranaroussi/quantstats) |
| `vectorbt` | Vectorized backtesting | [polakowo/vectorbt](https://github.com/polakowo/vectorbt) |
| `empyrical` | PSR/DSR calculations | [quantopian/empyrical](https://github.com/quantopian/empyrical) |
| `hmmlearn` | Regime detection | [hmmlearn/hmmlearn](https://github.com/hmmlearn/hmmlearn) |
| `pyfolio` | Portfolio tearsheets | [quantopian/pyfolio](https://github.com/quantopian/pyfolio) |

## Free APIs

| Source | Data | Already Integrated? |
|---|---|---|
| Binance Funding Rate | 8h crypto perp funding | No |
| FRED | Macro: rates, yield curves | Yes (`bond_data_fred.py`) |
| CFTC COT | Futures positioning | No |
| CryptoQuant/Glassnode | On-chain flows | No |
| Yahoo Finance | OHLCV multi-asset | Yes |
| Alternative.me | Fear & Greed | Yes |

---

## Open Questions for User

1. **LONG_ONLY:** Disable immediately or shadow-test with `CRYPTO_SHORT_REGIME_GATE_ENABLED=1` first?
2. **`enhanced_ml_A_xgboost`:** Kill outright or keep as mutation candidate? (30.8% WR LONG, but symbol-locked SEI/ALGO/JTO show 67%+ WR)
3. **Execution order:** Should I implement all 4 changes in a single branch/PR, or one per branch?
4. **Open PRs (#610, #626, #654):** Build independently or wait for merge to avoid conflicts?
