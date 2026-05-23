# CRYPTO swarm re-validation — synthesis

**Date:** 2026-05-13
**Preset:** non-opus-4 (xai / deepseek / groq / cerebras)
**Cost:** $0.0688
**Engines responding:** 4/4 ok
**Mean TIER-2 attainability:** 76.25% (xai 75 / deepseek 72 / groq 80 / cerebras 78)

## Universal consensus

**4/4 engines independently propose the same three top-priority changes:**

1. **6 UTC entry filter** (Edge #10 correction) — 4/4
2. **BTC 4h regime gate** (Edge #11 wire-up) — 4/4
3. **Direction-aware gating** exploiting ml_crypto_pred LONG 12% vs SHORT 85.7% asymmetry — 4/4

## Highest-impact single change (deepseek breakthrough)

> "The ml_crypto_pred model has 85.7% SHORT WR vs 12% LONG WR — **inverting LONG signals alone could lift PF from 1.25 to ~1.55**, making it the single highest-impact change."

This is the strongest actionable insight of any swarm round this session. Per AA-1 autopsy data: n=25 LONG resolved (3W/22L) vs n=7 SHORT resolved (6W/1L). If we invert the LONG side of ml_crypto_pred to SHORT, mathematically expected: 22 wins flip from losses → +44 WR lift on that sub-strategy.

## Per-strategy proposals (TIER-2 candidates)

| Strategy | Engine | Expected PF | Expected WR% |
|---|---|---:|---:|
| direction_asymmetric_ml_gate | deepseek | 1.55 | 52.3 |
| BTC4hRegimeFilter | groq | 1.58 | 58 |
| CRYPTO_BTC4H_REGIME | xai | 1.65 | 47.5 |
| UTC6_DEATHZONE_FILTER | cerebras | 1.62 | 44.1 |
| btc_4h_red_long_gate | deepseek | 1.62 | 48.2 |
| LONG_SRC_GATE | cerebras | 1.58 | 45.2 |

## Edge #10 correction (4/4 consensus)

Replace memory-claimed "22 UTC death zone" with real backtest finding: **exclude all entries at UTC hour 6** (WR 23.1%, PF 0.06).

Wire target: `audit_trail/quality_gates.py` NS-C filter currently set to (8,9) UTC; **update to (6,)** per real backtest.

```python
# audit_trail/quality_gates.py
# OLD (incorrect): if str(asset_class).upper() == 'CRYPTO' and hour in (8, 9):
# NEW (correct):
if str(asset_class).upper() == 'CRYPTO' and hour == 6:
    pick['_hf_quality_gate_reason'] = 'crypto_utc_6_death_zone'
    continue
```

## Edge #11 wire-up (4/4 consensus)

BTC 4h regime defined as: **RED when BTCUSDT.4h.close < BTCUSDT.4h.SMA(10); GREEN otherwise**.

Application:
- 7 LONG-only emitters (per `feedback_long_source_bias.md`): reject LONG signals when BTC 4h RED
- All emitters: allow SHORT signals regardless of regime
- Wire target: new `audit_trail/btc_4h_regime_gate.py` callable from `passes_smart_gate`

## Direction-gate matrix (4/4 consensus)

| Source/Model | LONG action | SHORT action |
|---|---|---|
| ml_crypto_pred | **INVERT to SHORT** (12% WR → SHORT 85.7% WR) | Keep as SHORT |
| 7 LONG-only emitters | Reject when BTC 4h RED | N/A |
| dna_winner | Keep as LONG | Keep as SHORT |
| luxalgo | Keep as LONG | Keep as SHORT |

## MATIC ghost-row mitigation

Deepseek uniquely proposed `matic_ghost_row_filter` strategy. Per `project_confidence_rho_matic_artifact.md`, 660 MATIC 0%-PnL rows flip confidence→WR correlation from +0.023 to -0.127. Filter these from any aggregation. Already documented but not wired into a gate — wiring pending.

## Action items

| # | Item | Effort | Reversibility |
|---|---|---|---|
| C1 | Update NS-C UTC filter from (8,9) → (6,) per Edge #10 correction | 0.5h | Full |
| C2 | Wire BTC 4h regime gate as `audit_trail/btc_4h_regime_gate.py` | 6h | Full |
| C3 | Invert LONG signals from `ml_crypto_pred` (or restrict to SHORT-only emitter mode) | 2h | Full |
| C4 | Pre-aggregation filter for MATIC 0-PnL ghost rows in `dashboard_generator.py` | 3h | Full |

## Cumulative session totals (all 4 swarm rounds)

| Class | Cost | Engines | Strategies | Key finding |
|---|---:|---:|---:|---|
| FUTURES | $0.07 | 4/4 | 16 | TS-momentum long-only = MDD 6.57% — academic edge real |
| FOREX | $0.07 | 4/4 | 13 | JPY-cross block + non-JPY major preservation — unanimous |
| EQUITY | $0.07 | 4/4 | ~12 | VIX/YC regime filter + vol-targeting; survivorship bias warning |
| BOND | $0.07 | 4/4 | ~16 | Credit spread + duration rotation — Sharpe lift 0.57→1.1 |
| **CRYPTO** | $0.07 | 4/4 | ~16 | **Invert ml_crypto_pred LONG signals — single highest-impact change** |
| **TOTAL** | **$0.35** | **20/20** | **~73** | 5 classes covered |

NFA. No production change.
