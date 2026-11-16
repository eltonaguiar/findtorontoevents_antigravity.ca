# FINAL STRATEGY V1 — Finpredict-v4

**Folder**: `WIRED_IN/final_v001/2026-11-15T0740Z_finpredict-v4/`
**Author**: Kilo finpredict-v4 worktree
**Generated**: 2026-11-15T07:40Z UTC
**Purpose**: Digest all peer WIRED_IN proposals + last-48h code changes, and devise the finalized strategy to **find and prove profitable strategies per asset class** that feed `findtorontoevents.ca/audit`.

---

## 0. What this document is

This is the **decision** document. It synthesizes:

- The `WIRED_IN/2026-11-15T0700Z_finpredict-summary/` audit (inventory, failure taxonomy, methods catalogue, per-asset-class PLAN.md).
- All other agents' WIRED_IN proposals (childlike-airport, scratch-hippodraco, hilarious-seer, buffy, copilot, _0125 finpredict-v4).
- The last-48h code changes (BMA200 wealth-gate backtest, Faber emitter, forward-tracker, scoring framework spec) and the workflow YAML fixes in this worktree.

It devises a **realistic, provable path per asset class**. The single binding constraint is the **proof-protocol standard**: nothing is called "profitable" until it passes the 10 gates. No current candidate passes all 10. This plan is the roadmap to change that.

---

## 1. The hard truth (from evidence)

| Candidate | Sharpe (s vs B&H) | Final wealth (s vs B&H) | Verdict |
|---|---|---|---|
| BTC sma200 | 0.57 vs 0.46 | 1.94 vs 1.67 | **WEALTH_BEAT** (only crypto) |
| GLD sma200 | 1.14 vs 0.93 | 2.12 vs 2.01 | **WEALTH_BEAT** (only commodity) |
| SPY/QQQ/VTI sma200 | 0.92-0.96 vs 0.80-0.88 | LOSES wealth | **DD_OVERLAY** |
| TLT / BND | negative | LOSES wealth | **REJECT** |
| IWM / ETH / SGOV | weak/negative | mixed | **REJECT** |
| Mixed Faber sleeve vs SPY | 0.95 vs 0.88 | 2.03 vs 1.85 | **WEALTH_BEAT** (vs SPY) |
| Equity-only Faber sleeve vs SPY | 1.12 vs 0.88 | 1.856 vs 1.851 | **REJECT_VS_BENCH** (marginally fails 1.01 wealth gate) |

**Key finding**: the ONLY clean, cost-adjusted, OOS, benchmark-relative beats are **BTC sma200**, **GLD sma200**, and the **mixed Faber sleeve** (risk assets above 200dMA else SGOV). Equity standalone overlays improve risk (DD/Sharpe) but *reduce* terminal wealth vs same-asset buy-and-hold — so they are **risk management, not alpha**.

---

## 2. The final strategy (high level)

**Adopt a two-track model:**

1. **Track A — "Proven Sleeves" (beta/tactical)**: the mixed Faber sleeve (SPY/QQQ/VTI/GLD/BTC when above 200dMA, else SGOV) is the ONLY construct that beats SPY on **both** wealth and Sharpe in the OOS window. This becomes the **baseline portfolio sleeve** and the dashboard's honesty benchmark. It is not "alpha" — it is a documented tactical-beta overlay.

2. **Track B — "Forward Alpha Candidates"**: the only candidates worth running a **pre-registered forward test** on:
   - `vwap-reversion-scout` (EQUITY) — prior +1.96pp excess, t=1.99, 28 picks. Needs ~155 trades (≈3 yr at 48/yr) for power; only plausible near-term alpha.
   - BTC sma200 and GLD sma200 — must FIRST pass the full 10-gate protocol before forward test.

---

## 3. Per-asset-class finalized strategy

### 3.1 CRYPTO (BTC sma200)
- **Signal**: weekly sma200 overlay on BTC-USD, `shift(1)` lag, 10bp cost + Binance maker-taker.
- **Already**: wealth beat (1.94 vs 1.67), Sharpe beat (0.57 vs 0.46). Clean, cost-adjusted, OOS.
- **Missing (the fix)**: bootstrap CI, walk-forward folds, DSR, Bonferroni across the ~20 crypto configs, shuffle control, regime split, pre-registered forward test. **These are exactly the 10 gates.** Run `python3 experiments/crypto_sma200_oos_protocol.py`.
- **Decision gate**: pass 10/10 → promote to forward paper test (n≥100, PF≥1.3, WR≥55%). Fail any → **mark dead**, no re-test (stop wasting cycles).

### 3.2 COMMODITY (GLD sma200)
- **Signal**: weekly sma200 overlay on GLD, `shift(1)` lag, 10bp.
- **Already**: wealth beat (2.12 vs 2.01), Sharpe beat (1.14 vs 0.93). Window-sensitive; apply the **1% wealth-margin gate** (`beats_wealth = s.final > b.final * 1.01`).
- **Missing**: same 10 gates as BTC. Run protocol for GLD.
- **Decision gate**: same promotion rule. If GLD is window-sensitive and fails stability, discard.

### 3.3 EQUITIES (the honest answer)
- **No standalone equity overlay beats buy-and-hold wealth.** Stop trying to sell it as alpha.
- **Finalized product**: the **equity tactical-beta sleeve** (SPY/QQQ/VTI above 200dMA else SGOV) as the *baseline benchmark* — it beats SPY on risk and is near wealth-neutral. It is the **comparator** for all other claims.
- **Forward alpha candidate**: `vwap-reversion-scout`. Pre-register the clock (as in buffy's `FORWARD_TEST.md`). No promotion off interim look; require n≈155, |t|≥3.54 (multiplicity bar) or PF+CI.
- **Rule**: equities are reported as **DD_OVERLAY** (risk reduction) not alpha, until vwap crosses its forward threshold.

### 3.4 BONDS
- TLT/BND **rejected** (negative Sharpe, lose wealth). Confirmed by the emitter change that killed live TLT/BND STRONG_BUY below 200dMA.
- **Finalized**: bonds stay as **cash/defensive allocation** (SGOV). No active bond strategy is pursued this cycle. This is the *correct* negative result; do not re-test.

### 3.5 FOREX
- **Insufficient data** (`^DXY n=0`); no clean OHLCV history of sufficient length. All major-pair hypotheses died on data, not signal.
- **Finalized**: block forex until a clean, long, validated FX feed exists. Pre-register the window when it does. No live forex today.

### 3.6 PREDICTION MARKETS
- Structurally rejected (zero-sum, adverse selection, fees, size mismatch, PBO=0.603). Shadow-only. **Not in scope** for the profitability claim.

---

## 4. What feeds `findtorontoevents.ca/audit`

The dashboard should expose, per asset class, a **single, honest verdict** driven by the proof protocol:

| Asset class | Verdict | Evidence source |
|---|---|---|
| CRYPTO | `WEALTH_BEAT` (pending 10-gate) | `reports/sma200_wealth_gate_backtest.json` → BTC |
| COMMODITY | `WEALTH_BEAT` (pending 10-gate) | same → GLD |
| EQUITIES | `DD_OVERLAY` (baseline sleeve) + forward alpha clock | equity sleeve + `FORWARD_TEST.md` clock |
| BONDS | `REJECT` (no active strategy) | TLT/BND sma200 |
| FOREX | `REJECT` (insufficient data) | n=0 diagnostics |
| Prediction markets | `REJECT` (structural) | PBO gate |

**Deliverables to wire into the audit:**
1. Extend `benchmark_proof.html` (already reads `benchmark_ledger_proof.json`) with a per-class verdict table from `sma200_wealth_gate_backtest.json`.
2. Publish the **forward-test clock** status (n, t-stat, PF, boundary) for `vwap-reversion-scout` and the two protocol candidates.
3. Label every live pick with `sizing_allowed:false` until its class verdict is `PROVEN`.

---

## 5. Rules that must not be violated

- **No profitability claim without 10/10 gates.**
- **No re-testing of a dead class** (bonds, prediction markets) this cycle.
- **No backfill after seeing a result** — forward clock only.
- **Multiplicity correction always** (Bonferroni for certification, BH-FDR for discovery).
- **No live capital** until ≥1 candidate passes Phase 4 and the forward paper protocol.

---

## 6. Files in this folder

- `README.md` — this summary.
- `STRATEGY_FINAL_PLAN.md` — the complete per-asset-class implementation plan.
- `PROOF_PROTOCOL_IMPLEMENTATION.md` — exactly how each gate is run for BTC/GLD/vwap.
- `AUDIT_FEED_SCHEMA.md` — the JSON schema for the dashboard verdict panel.
- `DECISION_LOG.md` — what was rejected and why (prevents re-investigation).
- `STRATEGY_UNIVERSE_SYNTHESIS.md` — digest of `ALL_STRATEGIES.md` + `BABY_STRATEGIES` + graveyard; explains why DARWIN/GP high-Sharpe artifacts and >3-parameter rules are rejected, and confirms the simple mean-reversion/low-parameter candidate set.

---

## 7. Immediate next actions

1. Add the proof-protocol gates to the BTC/GLD backtest (`experiments/crypto_sma200_oos_protocol.py` and a GLD analog) — run them.
2. Stand up the pre-registered forward clock for `vwap-reversion-scout` (qa_ledger-wired).
3. Wire `sma200_wealth_gate_backtest.json` into the audit dashboard verdict panel.
4. Do NOT enable live emission for any class yet.
