# v3b LLM Signal Translator — Specification (2026-05-12)

Per DAILY_IDEAS 2026-05-12 entry §A — highest leverage item.

## Problem statement

`v3a` keyword router (commit `a060a87b3c8`) routes only **2/14 BOND specs**
off the SMA proxy default. Every NO_EDGE verdict across 7 asset classes is
caused by the SMA proxy not parsing natural-language `spec.entry`. Real
edge is likely hidden behind faithful signal translation.

## Design goals

1. **Parse arbitrary natural-language entry/exit rules** into a structured
   `signal_spec` JSON dispatchable to a handler registry.
2. **Validate at ingest time** — malformed specs are rejected with a
   precise reason, not silently routed to the SMA default.
3. **Support pair-strategies, regime-gated entries, multi-leg sizing** —
   the SMA proxy can't represent any of these.
4. **Replay-safe** — same input always produces same output (deterministic
   LLM + JSON-schema validation).

## JSON schema (v3b/v1)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "v3b signal_spec",
  "type": "object",
  "required": [
    "signal_id", "asset_class", "primary_ticker", "target",
    "entry", "exit", "valid_from", "schema_version"
  ],
  "properties": {
    "schema_version": { "const": "v3b/v1" },
    "signal_id": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9_]{2,63}$",
      "description": "Stable kebab-case id; never changes once published"
    },
    "asset_class": {
      "type": "string",
      "enum": ["EQUITY","CRYPTO","FOREX","COMMODITY","FUTURES","ETF","BOND","MEMECOIN","PENNY_STOCK"]
    },
    "primary_ticker": {
      "type": "string",
      "description": "yfinance ticker for non-crypto, exchange-pair for crypto",
      "examples": ["CT=F", "AAPL", "EURUSD=X", "BTCUSDT"]
    },
    "secondary_ticker": {
      "type": ["string", "null"],
      "description": "for pair-trades (e.g., TIP/IEF spread, LQD/HYG ratio)"
    },
    "target": {
      "type": "string",
      "enum": ["LONG", "SHORT", "NEUTRAL", "PAIR_LONG", "PAIR_SHORT"]
    },
    "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "0-1 scale; 0-10 leakage is rejected by validator"
    },
    "features": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "type", "source"],
        "properties": {
          "name": { "type": "string" },
          "type": { "type": "string", "enum": ["price","ratio","spread","return","oi","funding","cot","macro","sentiment","custom"] },
          "source": { "type": "string", "description": "yfinance | binance | fred | cot | onchain | custom" },
          "params": { "type": "object" }
        }
      }
    },
    "entry": {
      "type": "object",
      "required": ["handler", "params"],
      "properties": {
        "handler": {
          "type": "string",
          "enum": ["sma_cross", "rsi_threshold", "bollinger_band", "cot_extreme",
                   "regime_gate", "spread_zscore", "earnings_drift", "funding_skew",
                   "custom_python"]
        },
        "params": { "type": "object", "description": "handler-specific schema" }
      }
    },
    "exit": {
      "type": "object",
      "required": ["handler", "params"],
      "properties": {
        "handler": {
          "type": "string",
          "enum": ["tp_sl_pct", "atr_trail", "time_exit", "regime_flip",
                   "horizon_expiry", "iv_attainment", "thesis_break", "custom_python"]
        },
        "params": { "type": "object" }
      }
    },
    "regime_gate": {
      "type": ["object", "null"],
      "properties": {
        "filter": { "type": "string", "enum": ["VIX","DXY","HMM_STATE","COT_SENTIMENT","CUSTOM"] },
        "condition": { "type": "string", "description": "e.g., '<20' or 'TRENDING'" }
      }
    },
    "sizing": {
      "type": "object",
      "properties": {
        "mode": { "type": "string", "enum": ["FIXED","ATR_VOL","KELLY_CAPPED","CUSTOM"] },
        "params": { "type": "object" }
      }
    },
    "valid_from": { "type": "string", "format": "date-time" },
    "valid_to":   { "type": ["string", "null"], "format": "date-time" },
    "thesis":     { "type": "string", "maxLength": 2000 },
    "citations":  { "type": "array", "items": { "type": "string" } }
  }
}
```

## Example — cot_positioning + CT=F

```json
{
  "schema_version": "v3b/v1",
  "signal_id": "cot_positioning_ct_short_2024_2026",
  "asset_class": "COMMODITY",
  "primary_ticker": "CT=F",
  "secondary_ticker": null,
  "target": "SHORT",
  "confidence": 0.90,
  "features": [
    { "name": "cot_commercial_net", "type": "cot", "source": "cot", "params": { "lookback_weeks": 52 } },
    { "name": "atr_14", "type": "price", "source": "yfinance", "params": { "window": 14 } }
  ],
  "entry": {
    "handler": "cot_extreme",
    "params": { "percentile": 95, "side": "commercial_short" }
  },
  "exit": {
    "handler": "tp_sl_pct",
    "params": { "tp_pct": 5.0, "sl_pct": -3.0, "max_hold_hours": 336 }
  },
  "regime_gate": null,
  "sizing": { "mode": "FIXED", "params": { "contracts": 1 } },
  "valid_from": "2024-01-01T00:00:00Z",
  "valid_to": null,
  "thesis": "Commercials net-short cotton at >=95th percentile historically precedes mean-reversion. CT=F COT data has 53-year history; cotton+coffee carry the COMMODITY class edge per Miffre 2010 (SSRN 1127213).",
  "citations": [ "reports/cot_paper_pilot_testing_plan_2026-05-12.md",
                 "Miffre 2010 commodity carry+momo SSRN 1127213" ]
}
```

## Example — yield-curve flattener (BOND)

```json
{
  "schema_version": "v3b/v1",
  "signal_id": "bond_curve_flattener_tlt_ief",
  "asset_class": "BOND",
  "primary_ticker": "TLT",
  "secondary_ticker": "IEF",
  "target": "PAIR_LONG",
  "confidence": 0.62,
  "features": [
    { "name": "tlt_ief_ratio_zscore", "type": "spread", "source": "yfinance",
      "params": { "window": 60 } },
    { "name": "dgs10_dgs2_spread", "type": "macro", "source": "fred",
      "params": { "series": ["DGS10","DGS2"] } }
  ],
  "entry": {
    "handler": "spread_zscore",
    "params": { "z_threshold": 1.5, "side": "long_spread" }
  },
  "exit": {
    "handler": "regime_flip",
    "params": { "indicator": "dgs10_dgs2_spread", "flip_condition": ">0" }
  },
  "regime_gate": {
    "filter": "VIX",
    "condition": "<25"
  },
  "sizing": { "mode": "ATR_VOL", "params": { "target_vol_bp": 50 } },
  "valid_from": "2026-05-15T00:00:00Z",
  "valid_to": null,
  "thesis": "When TLT/IEF ratio is at >+1.5 sigma (long-duration overweighting short-duration) and the 10y-2y spread is still inverted, the curve typically un-inverts via TLT outperforming IEF (long-duration rallies more than short-duration). Block during VIX>25 (regime-risk-off skews TLT independently).",
  "citations": [ "Cochrane-Piazzesi bond risk premia",
                 "reports/asset_class_deep_dive_BOND_2026-05-12.md" ]
}
```

## Validation pipeline

```
LLM raw output
   ↓
JSON-schema validate (v3b/v1)
   ↓ pass                             ↓ fail
handler registry dispatch          reject with structured reason
   ↓                                   (logged to v3b_rejects.jsonl)
backtest / forward emission
```

## Handler registry mapping

| `entry.handler` | Python module |
|---|---|
| `sma_cross` | existing v3a |
| `rsi_threshold` | `alpha_engine/indicators.py::rsi` |
| `bollinger_band` | `alpha_engine/indicators.py::bollinger_bands` |
| `cot_extreme` | NEW — wraps `prediction_market_consensus` or `cot_data_fetcher` |
| `regime_gate` | `alpha_engine/regime_flip_detector.py` |
| `spread_zscore` | NEW — generic pair-spread z-score module |
| `earnings_drift` | NEW — yfinance earnings calendar + PEAD signal |
| `funding_skew` | `alpha_engine/funding_rate_arb.py` |
| `custom_python` | sandboxed exec of `params.code_b64` (HIGH risk; disabled by default) |

| `exit.handler` | Python module |
|---|---|
| `tp_sl_pct` | existing TP/SL logic |
| `atr_trail` | `alpha_engine/indicators.py::atr` |
| `time_exit` | existing time-exit logic |
| `regime_flip` | `alpha_engine/regime_flip_detector.py` |
| `horizon_expiry` | `alpha_engine/strategies/cot_paper_pilot.py` MAX_HOLD config |
| `iv_attainment` | NEW — for UEPS long-term holds |
| `thesis_break` | NEW — flag-based exit |

## Wire-up plan

Per CLAUDE.md Wire-Up Rule:

1. **PR #1 (this spec):** schema + validator + handler-registry skeleton.
   No production callers; opt-in sidecar. ~250 LOC + 100 LOC tests.
2. **PR #2:** wire validator into `research_orchestrator` input path.
   Reject malformed specs upstream; route validated specs to handler
   registry instead of SMA proxy.
3. **PR #3:** convert top-10 existing strategies to v3b specs (cot_positioning,
   stocks_rsi2_pullback, ml_enhanced_RENDERUSDT_1h, etc.).
4. **PR #4:** retire v3a keyword router after PR #3 emissions match v3a
   baseline within ±5pp.

## Sizing estimate

| PR | LOC | Effort | Risk |
|---|---|---|---|
| PR #1 schema + validator + handlers | 250 + 100 | 4h | Low (sidecar) |
| PR #2 orchestrator wire-up | 80 | 2h | Med (input-path change) |
| PR #3 strategy conversion (×10) | 50/strategy = 500 | 1d | Low (per-strategy) |
| PR #4 retire v3a | -150 | 30min | Low |
| **Total** | **~700 LOC net** | **~2 days** | Low-Med |

## Cost estimate (LLM)

Per DAILY_IDEAS §A: cost ~$1/run across all classes. v3b is a one-shot
translation per signal (vs the SMA proxy which retries continuously),
so cost is bounded by signal-emission rate — well within budget.

## Status

**SPEC COMPLETE.** Implementation queued for next session. The schema +
validator skeleton is the smallest unit and can ship as a single PR
without touching production emission paths.

## NFA

Research surface. v3b is a signal-representation layer; real-money sizing
remains gated on the 10-step Lopez de Prado AFML readiness pipeline
regardless of which translator parses the spec.

## Refs

- `DAILY_IDEAS.MD` §A (highest-leverage item, 2026-05-12)
- Existing v3a keyword router: commit `a060a87b3c8`
- `alpha_engine/strategies/cot_paper_pilot.py` (canonical v3b candidate)
- `alpha_engine/regime_flip_detector.py` (regime_gate handler)
- `alpha_engine/indicators.py` (indicator handler library)
- `prediction_market_consensus.py` (cot_extreme handler proxy)
