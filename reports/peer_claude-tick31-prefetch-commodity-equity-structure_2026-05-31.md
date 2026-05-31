# Tick 31 — Pre-fetch: COMMODITY + EQUITY Code Structure

**Date:** 2026-05-31
**Author:** claude-opus-4.7 (tick 31 ground-truth)
**Purpose:** Verbatim ground-truth of where COMMODITY/EQUITY strategies actually live and which entry points dispatch them, before any PR #269 / PR #270 follow-up swap is proposed.

---

## EXECUTIVE SUMMARY

| Question | Answer |
|---|---|
| Where are strategy gates declared? | `alpha_engine/non_crypto_policy.py` → `NON_CRYPTO_STRATEGY_POLICY` dict |
| Where are strategies registered for dispatch? | `alpha_engine/equity_strategies.py::EQUITY_STRATEGIES`, `alpha_engine/commodities_strategies.py::COMMODITY_STRATEGIES`, `alpha_engine/cot_positioning.py::COT_STRATEGIES`, `alpha_engine/cta_bridge.py::CTA_BRIDGE_STRATEGIES`, `multi_asset/scanner.py` (gold_safe_haven, futures_momentum) |
| Where does the scanner dispatch them? | `alpha_engine/scanner.py` lines ~2070-2200 (`strategies.update(...)`) |
| Is the killed-strategies blocklist? | `alpha_engine/config.py::BLACKLISTED_STRATEGIES` (lines 257-273) |
| Does production_scanner.py route EQUITY? | **MOSTLY NO** — `alpha_engine/production_scanner.py` is a quality-gate / write layer; the real strategy dispatch lives in `alpha_engine/scanner.py`. INCIDENT_STOCKS #3 wording "production_scanner doesn't route EQUITY" is **NUANCED-CORRECT**: production_scanner.py applies blocks/gates to EQUITY (lines 2641-2701, 4006-4122) but does not itself iterate `EQUITY_STRATEGIES` — that's `scanner.py:2070-2071`. PEAD equity is wired here as a shadow sidecar (line 4006-4030). |
| INCIDENT_STOCKS #3 confirmed? | **PARTIALLY** — see refutation below. |

---

## PART A — COMMODITY STRUCTURE

### A.1 Policy gate (`alpha_engine/non_crypto_policy.py`)

**File:line 213-239 (verbatim, cot_positioning + cta_tsmom_blend + cta_commodity_momentum_term):**
```
    "cot_positioning": {
        "categories": {"forex", "commodity", "futures", "bond", "equity"},
        "min_confidence": 0.55,
        "min_rr": 1.25,
        "min_elite_score": 60,
        "min_forward_trades": 20,
        "min_forward_wr": 0.35,
        "allow_without_forward": False,
    },
    "cta_tsmom_blend": {
        "categories": {"forex", "commodity", "futures", "bond", "equity"},
        ...
    },
    "cta_commodity_momentum_term": {
        "categories": {"commodity", "futures"},
        "min_confidence": 0.67,
        ...
    },
```

**File:line 441-453 (commodity_tsmom_12m, verbatim):**
```
    # ── Commodity TSMOM (Moskowitz, Ooi & Pedersen 2012) ────────────────────
    "commodity_tsmom_12m": {
        "categories": {"commodity", "futures"},
        "min_confidence": 0.55,
        "min_rr": 1.20,
        "min_elite_score": 50,
        "min_forward_trades": 5,
        "min_forward_wr": 0.45,
        "allow_without_forward": True,
    },
```

### A.2 Strategy registries

**`alpha_engine/commodities_strategies.py:1074-1084` (verbatim, full registry):**
```
COMMODITY_STRATEGIES = {
    "seasonal_momentum":         seasonal_momentum,
    "gold_safe_haven":           gold_safe_haven,
    "oil_inventory_momentum":    oil_inventory_momentum,
    "metals_mean_reversion":     metals_mean_reversion,
    "agricultural_spread":       agricultural_spread,
    "energy_momentum_breakout":  energy_momentum_breakout,
    "commodity_rsi_divergence":  commodity_rsi_divergence,
    "dxy_inverse_commodities":   dxy_inverse_commodities,
    "commodity_tsmom_12m":       commodity_tsmom_12m,
}
```

**`alpha_engine/cot_positioning.py:395-396`:**
```
COT_STRATEGIES = {
    "cot_positioning": cot_positioning_strategy,
}
```
`cftc_cot_commercial_signal` appears only as an emitted strategy NAME inside `cot_positioning_strategy()` (line 434), it is **not a separate registered function**.

**`alpha_engine/cta_bridge.py:380` — cta_cross_asset_tsmom registered:**
```
"cta_cross_asset_tsmom": cta_cross_asset_tsmom,
```

### A.3 Scanner dispatch (`alpha_engine/scanner.py`)

**File:line 290 (import):** `from commodities_strategies import COMMODITY_STRATEGIES`
**File:line 382-384:**
```
    from cot_positioning import COT_STRATEGIES
except Exception:
    COT_STRATEGIES = {}
```
**File:line 2097-2101 (verbatim — KEY DISPATCH BLOCK):**
```
    if strategy_filter in ("all", "forex") and COT_STRATEGIES:
        strategies.update(COT_STRATEGIES)
    ...
    if strategy_filter in ("all", "commodity") and COMMODITY_STRATEGIES:
        strategies.update(COMMODITY_STRATEGIES)
```
**File:line 2190-2191 (CTA bridge):**
```
    # CTA Bridge: academic CTA strategies across forex, equity, commodity
    if strategy_filter in ("all", "forex", "equity") and CTA_BRIDGE_STRATEGIES:
```

**KEY GAP:** Line 2097 dispatches `COT_STRATEGIES` only when `strategy_filter in ("all", "forex")` — **NOT** `commodity`. So `cot_positioning` reaches commodity symbols only via `strategy_filter == "all"`. CTA bridge is dispatched on `("all","forex","equity")` — also **NOT** `commodity`. Multi-asset `gold_safe_haven` + `futures_momentum` live in `multi_asset/scanner.py:87-91, 2741, 2809` — a separate scanner.

### A.4 Per-strategy REGISTERED + CALLED status (COMMODITY)

| Strategy | Registered in | Has gate in policy? | Called from prod path? | Status |
|---|---|---|---|---|
| `cot_positioning` | `cot_positioning.py:COT_STRATEGIES` | YES (line 213) | `scanner.py:2098` (forex/all only) | **ACTIVE (forex/all)**, reaches commodity only via "all" filter |
| `cftc_cot_commercial_signal` | NONE (emitted name inside `cot_positioning_strategy`) | No standalone gate (only `cot_positioning` covers it) | Through `cot_positioning` only | **RETIRED** per `strategy_blocklist.py:165,176` (2026-05-02); also blocked for `("commodity","cftc_cot_commercial_signal")` at `production_scanner.py:2691` |
| `cta_cross_asset_tsmom` | `cta_bridge.py:380` `CTA_BRIDGE_STRATEGIES` | NO standalone (uses `cta_tsmom_blend` umbrella line 222) | `scanner.py:2191` (forex/equity/all — NOT commodity) | **CALLABLE via all-filter**; FOREX leg killed via cta_bridge cap (tick 30 note in non_crypto_policy line 246) |
| `futures_momentum` | `multi_asset/scanner.py:91,2809` | NO | `multi_asset/scanner.py` only | BANNED via `hedge_fund_quality_gate.py:186 FUTURES_BANNED_STRATEGIES` + `crypto_risk_gates.py:61` |
| `ema_stack_momentum` | `live_forward_test.py:481` only (test harness) | NO | NONE in production scanner | **DEAD CODE per Wire-Up Rule** (test-only); `auto_tuner.py:158,185` also kills `futures_ema_stack_momentum` variant; `production_scanner.py:2694` blocks `("futures","ema_stack_momentum")` |
| `commodity_tsmom_12m` | `commodities_strategies.py:1083` | YES (line 445) | `scanner.py:2101` (commodity/all) | **ACTIVE** |
| `gold_safe_haven` | `commodities_strategies.py:1076` + `multi_asset/scanner.py:87,2741` | NO standalone gate | `scanner.py:2101` (commodity/all) | **ACTIVE** but no policy gate — defaults to default-deny via `_default_policy` (probationary) |

### A.5 Wire-Up Rule compliance summary (COMMODITY)

- **DORMANT / DEAD per Wire-Up Rule:** `ema_stack_momentum` (test-harness only, never in prod registry).
- **HARD-BLOCKED in production_scanner:** `cftc_cot_commercial_signal` (commodity, line 2691), `ema_stack_momentum` (futures, line 2694).
- **ACTIVE through scanner.py "all" filter:** `cot_positioning`, `cta_cross_asset_tsmom`.
- **ACTIVE through commodity filter:** all 9 in `COMMODITY_STRATEGIES`.

---

## PART B — EQUITY STRUCTURE

### B.1 Policy gate (`alpha_engine/non_crypto_policy.py`)

**File:line 183-211 (verbatim, EQUITY-tagged entries):**
```
    "post-earnings-rev-scout": {
        "categories": {"equity"}, "min_confidence": 0.68, ...
    },
    "quality-momentum-scout": {
        "categories": {"equity"}, "min_confidence": 0.68, ...
    },
    # PR4 (2026-05-27): Promote equity_pead from shadow to probation.
    "equity_pead": {
        "categories": {"equity"},
        "min_confidence": 0.58,
        "min_rr": 1.50,
        "min_elite_score": 50,
        "min_forward_trades": 5,
        "min_forward_wr": 0.50,
        "allow_without_forward": True,  # Probation: build forward record
    },
```

`stocks_rsi2_pullback`, `connors_rsi2`, `quality_compounders`, `equity_momentum_regime`, `pead_equity` (note hyphen vs underscore mismatch with `equity_pead`) **DO NOT** appear as separate gate entries.

### B.2 Strategy registry — `alpha_engine/equity_strategies.py:1323-1348`

```
_RAW_EQUITY_STRATEGIES = {
    "momentum_factor_12m":            momentum_factor_12m,
    "penny_volume_breakout":          penny_volume_breakout,
    "meme_social_velocity":           meme_social_velocity,
    "optimized_stock_momentum":       optimized_stock_momentum,
    "quality_value_composite":        quality_value_composite,
    "intermarket_risk_on":            intermarket_risk_on,
    "support_resistance_bounce":      support_resistance_bounce,
    "connors_rsi2_scanner":           connors_rsi2_scanner,
    "connors_rsi2_short_scanner":     connors_rsi2_short_scanner,
    "equity_two_bar_rsi_reversal":    equity_two_bar_rsi_reversal,
    "triple_rsi_scanner":             triple_rsi_scanner,
    "vix_spike_reversal_scanner":     vix_spike_reversal_scanner,
    "turn_of_month_scanner":          turn_of_month_scanner,
    "earnings_gap_reversal_scanner":  earnings_gap_reversal_scanner,
    "gap_reversal_tech_stocks":       gap_reversal_tech_stocks,
    **COMMUNITY_EQUITY_STRATEGIES,
}
...
EQUITY_STRATEGIES = {
    name: _wrap_with_factor_model(fn) for name, fn in _RAW_EQUITY_STRATEGIES.items()
}
```

### B.3 Scanner dispatch — `alpha_engine/scanner.py:2070-2071` (verbatim)
```
    if strategy_filter in ("all", "equity"):
        strategies.update(EQUITY_STRATEGIES)
```

### B.4 Production gate — `alpha_engine/production_scanner.py`

EQUITY appears extensively in `production_scanner.py` as a normalization + blocking layer:
- **line 2641-2643:** `if category in ("stock", "etf", "bond"): category = "equity"` — normalization.
- **line 2670-2686:** `_BLOCKED_CATEGORY_STRATEGIES` blocks: `yahoo_analyst_consensus`, `claude_gainer_ml`, `value_quality_factor`, `consecutive_beats`, `earnings_drift`, `dividend_aristocrats`, `penny_deep_oversold`, `extreme_oversold_bounce`, `goldmine_{1,2,3,4}x_consensus`.
- **line 384 (comment):** "2026-05-28: `stocks_rsi2_pullback` REMOVED — 30% WR / PF 0.032 …"
- **line 4006-4030 (PEAD shadow wiring):** `_PEAD_ENABLED = os.environ.get("PEAD_EQUITY_ENABLED", "0") == "1"` then `from strategies.pead_equity import generate_pead_signals` — an opt-in sidecar.
- **line 5241-5252:** macro equity gate (yield-curve inverted + Fed hiking → conf >= 0.90).

**production_scanner.py does NOT iterate `EQUITY_STRATEGIES` itself.** The dispatch is in `scanner.py:2070`. production_scanner is the post-emission gate/quality/write layer.

### B.5 Per-strategy REGISTERED + CALLED status (EQUITY)

| Strategy | Registered in | Has gate in policy? | Called from prod path? | Status |
|---|---|---|---|---|
| `stocks_rsi2_pullback` | NOT in `EQUITY_STRATEGIES`. References: `config.py:270 (BLACKLISTED_STRATEGIES)`, `score_booster.py:232,274`, `non_crypto_boosters.py:443`, `forward_validator.py:421,833`, `tools/add_strategy_descriptions.py:103,110` | NO | **BLOCKED via `config.BLACKLISTED_STRATEGIES`** (line 270) | KILLED 2026-05-28; **un-kill blocker = `alpha_engine/config.py:257-273 BLACKLISTED_STRATEGIES`**. The list itself is the kill-switch (not `BLOCKED_SOURCE_SYSTEMS`). |
| `connors_rsi2` (Connors RSI-2) | `equity_strategies.py:1331-1332` as `connors_rsi2_scanner` + `connors_rsi2_short_scanner`. Also `cross_asset_edge_discovery.py:1281`, `live_forward_test.py:477` (test). | NO standalone (covered by default policy) | `scanner.py:2071` (EQUITY_STRATEGIES) | **ACTIVE** under names `connors_rsi2_scanner` / `connors_rsi2_short_scanner` |
| `quality_compounders` | NONE FOUND | NO | NO | **NOT IN CODEBASE** (PR #270 reference must be aspirational — does not exist) |
| `equity_momentum_regime` | Likely `regime_filtered_momentum` (`equity_strategies.py:1311-1320, 1343`) | NO | `scanner.py:2071` (opt-in via env `REGIME_MOMENTUM_DISABLED`) | **ACTIVE (opt-in)** under name `regime_filtered_momentum` |
| `pead_equity` | `strategies/pead_equity.py` (referenced `production_scanner.py:4021`) | YES as `equity_pead` (note name mismatch — registered name vs policy key) | `production_scanner.py:4006-4030` (env-gated `PEAD_EQUITY_ENABLED=1`) | **SHADOW** by default; policy gate exists |
| UEPS composite (Magic Formula × Piotroski × Acquirer's × SafetyGate) | `alpha_engine/value_screener_runner.py` (entry point) calls `ValueScreener.screen_universe` | NO standalone gate (emits `pick_type=long_term_value`) | `.github/workflows/value_screener_weekly.yml` (cron) + `tools/run_ueps_pickers.py` | **ACTIVE (weekly cron, paper)** — does NOT route through scanner.py |

### B.6 INCIDENT_STOCKS #3 verdict

**Claim:** "production_scanner doesn't route EQUITY."

**Verdict: NUANCED — partially confirmed, partially refuted.**

- **CONFIRMED:** `production_scanner.py` does not call `EQUITY_STRATEGIES` directly. Real dispatch is in `alpha_engine/scanner.py:2070-2071`.
- **REFUTED:** production_scanner.py is heavily EQUITY-aware: it normalizes `stock/etf/bond → equity` (2641), blocks 12 known-toxic EQUITY strategies (2674-2686), wires PEAD as shadow (4006-4030), and applies a macro EQUITY conf-floor (5241).
- **CORRECTED FRAMING:** "production_scanner.py is a post-emission gate, not a strategy iterator. The scanner that iterates EQUITY_STRATEGIES is `alpha_engine/scanner.py`." Any incident remedy aimed at "make production_scanner route EQUITY" is pointed at the wrong layer.

### B.7 Un-kill blocker for `stocks_rsi2_pullback`

**Location:** `alpha_engine/config.py:257-273` — `BLACKLISTED_STRATEGIES` list, entry at line 270:
```
    'stocks_rsi2_pullback',      # 10 EQUITY trades, WR 30%, PF 0.032 — catastrophically bad
```
To un-kill: remove that line (per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md` per CLAUDE.md). **Also register** it into `EQUITY_STRATEGIES` in `alpha_engine/equity_strategies.py:1323-1340` (currently absent — the kill removed it from the dispatch registry too). Note `score_booster.py:232,274`, `non_crypto_boosters.py:443`, `forward_validator.py:421,833` still reference the name in score/booster paths — those won't fire while the strategy is blacklisted but will when un-killed.

---

## PART C — CORRECT DIFF TARGETS FOR FUTURE SWAPS

### C.1 If proposing a COMMODITY strategy swap (PR #269 follow-up)

- **Policy gate edit:** `alpha_engine/non_crypto_policy.py` — `NON_CRYPTO_STRATEGY_POLICY` dict (lines 182-454). Add/remove `"commodity"` from each strategy's `"categories"` set.
- **Registry edit:** `alpha_engine/commodities_strategies.py:1074-1084` `COMMODITY_STRATEGIES` dict.
- **Scanner dispatch:** `alpha_engine/scanner.py:2097-2101`. To route `COT_STRATEGIES` to commodity, change line 2097 to `if strategy_filter in ("all", "forex", "commodity") and COT_STRATEGIES:`.
- **Block list edit:** `alpha_engine/production_scanner.py:2670-2701` `_BLOCKED_CATEGORY_STRATEGIES` set.
- **Hard kill list:** `alpha_engine/config.py:257-273` `BLACKLISTED_STRATEGIES`.
- **Commodity-specific kill switch:** `alpha_engine/commodity_kill_switch.py:48 _KNOWN_TOXIC_COMMODITY_STRATEGIES`.

### C.2 If proposing an EQUITY strategy swap (PR #270 follow-up)

- **Policy gate edit:** `alpha_engine/non_crypto_policy.py:183-212` (and 204 for `equity_pead`).
- **Registry edit:** `alpha_engine/equity_strategies.py:1323-1340` `_RAW_EQUITY_STRATEGIES` dict — **THIS is where new EQUITY strategies must be added to be dispatched**.
- **Scanner dispatch:** `alpha_engine/scanner.py:2070-2071` (already routes EQUITY).
- **Block list edit:** `alpha_engine/production_scanner.py:2670-2686` `_BLOCKED_CATEGORY_STRATEGIES`.
- **Hard kill list (un-kill target):** `alpha_engine/config.py:257-273` `BLACKLISTED_STRATEGIES`.
- **PEAD shadow toggle:** `alpha_engine/production_scanner.py:4018` `PEAD_EQUITY_ENABLED=1` env.
- **UEPS weekly wiring (already done):** `alpha_engine/value_screener_runner.py` + `.github/workflows/value_screener_weekly.yml`. Don't re-wire — extend the universe / fundamentals.

### C.3 NOT-IN-CODEBASE strategies named in PR deep-dives

- `quality_compounders` — **does not exist** anywhere in `alpha_engine/`, `multi_asset/`, `tools/`. Either rename (closest: `quality_value_composite`, `quality-momentum-scout`) or implement from scratch.
- `equity_momentum_regime` — **closest match** is `regime_filtered_momentum` (`equity_strategies.py:1311-1320`).
- `pead_equity` — **registered as** `equity_pead` in policy but loaded from `strategies/pead_equity.py` (note registry-name vs policy-key mismatch — they are intentionally aligned via `strategy=equity_pead` emission inside the module, verify before swap).

---

## APPENDIX — Counts

- **COMMODITY strategies mapped:** 7 (cot_positioning, cftc_cot_commercial_signal, cta_cross_asset_tsmom, futures_momentum, ema_stack_momentum, commodity_tsmom_12m, gold_safe_haven).
- **EQUITY strategies mapped:** 6 (stocks_rsi2_pullback, connors_rsi2, quality_compounders, equity_momentum_regime, pead_equity, UEPS composite).
- **INCIDENT_STOCKS #3 confirmed:** PARTIAL (production_scanner is a gate-layer, not the dispatcher; scanner.py is the dispatcher and it DOES route EQUITY).
