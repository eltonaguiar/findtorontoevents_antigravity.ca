# FOREX ATR-Normalized Momentum Mutation Analysis (Action Item A4)

**Date:** 2026-05-17
**Author:** Claude Code (agent worktree, branch `fix/etf-scanner-chunked-retry-fetch-2026-05-17`)
**Scope:** Research / report only. No production scanner changes, no FOREX emission enabled.
**Protocol:** `docs/MUTATION_THREE_AXIS_PROTOCOL.md` Step 1b (Axis 4: volatility / threshold-normalization) + Step 5 (mutation-quality / curve-fit guard).
**Goal served:** #1 — phenomenal performance across all asset classes on `/audit`.

---

## TL;DR — VERDICT

**NO-VIABLE-SUBSET for ATR-normalized momentum. Keep FOREX hard-disabled.**

The Axis-4 hypothesis — *"FOREX momentum strategies lose because their entry threshold is mis-scaled vs FOREX's low native volatility"* — is **not supported by the closed-trade evidence**. ATR / volatility-ratio normalization of the momentum signal **does not improve win/loss separation** on either FOREX momentum strategy that carries the required fields; on the worse one it slightly *degrades* it.

A **separate, non-ATR** finding does survive the Step-5 quality bar: `cta_cross_asset_tsmom` SHORT-only (n=117, WR 65.8%, PF 2.89) is a genuine direction-axis rehab candidate — but that is Axis 2 (Direction), already covered, and is *not* what A4 was chartered to test. It is recorded here only so the signal is not lost.

---

## 1. Data slice

Source: `alpha_engine/data/closed_picks.json` (8,421 total closed trades; field `asset_class == "FOREX"`).

| Metric | Value |
|---|---|
| FOREX closed trades | **932** |
| FOREX overall WR | **25.6%** |
| FOREX overall PF | **0.35** |
| FOREX cumulative PnL% | **-2.13%** |
| Step-5 10%-of-book floor | ≥ 93 trades |
| Charter n-floor (vetted-plan add) | ≥ 100 trades |

This confirms the CLAUDE.md status line: FOREX is genuinely sub-floor. The aggregate here (WR 25.6% / PF 0.35) is *worse* than the `asset_class_health` snapshot (PF 0.27 / WR 46.4% / n=1169) because that snapshot draws from a slightly different (larger, partly differently-resolved) ledger window; either way FOREX is far below the Tier-2 floor (PF>1.5 / WR>50).

Reproduce:
```bash
python tools/mutation_analysis.py --json
python tools/forex_atr_mutation_helper.py
```

---

## 2. `tools/mutation_analysis.py --json` — FOREX-relevant output

**Axis 2 (Direction) — FOREX strategies that flip WR by direction:**

| Strategy | SHORT | LONG | Spread |
|---|---|---|---|
| `ig_contrarian_sentiment` | 61.4% WR (n=57) | 16.8% WR (n=197) | 45pp |
| `myfxbook_retail_contrarian` | 50.0% WR (n=14) | 13.8% WR (n=123) | 36pp |
| `quan_engine_swing` | 60.0% WR (n=5) | 26.0% WR (n=104) | 34pp |
| `forex_rsi2_mean_reversion` | 34.8% WR (n=23) | 7.4% WR (n=108) | 27pp |
| `cta_cross_asset_tsmom` | 52.4% WR (n=164*) | 29.8% WR (n=84*) | 23pp |

\*direction counts in `mutation_analysis.py` include non-FOREX symbols this system also trades; FOREX-only counts are in §3.

**Axis 3 (Symbol) — `alpha_engine` FOREX symbol spread 67pp:** AUDUSD=X 66.7% / USDJPY=X 60% vs GBPJPY=X 0% / NZDUSD=X 12.5% — but every bucket is n≤8, far below the n-floor.

**Axis 1 (Timeframe):** no FOREX timeframe flips reported.

The mutation_analysis tool surfaces **Direction** as the only large, stable FOREX axis. It does not test Axis 4 — that requires the per-pick volatility fields analyzed below.

---

## 3. FOREX per-symbol WR

| Symbol | n | WR% | PF | avg PnL% |
|---|---:|---:|---:|---:|
| USDCHF=X | 11 | 81.8 | 11.87 | +0.0059 |
| EURGBP=X | 49 | 71.4 | 3.56 | +0.0017 |
| GBPUSD=X | 34 | 67.6 | 2.89 | +0.0033 |
| AUDUSD=X | 35 | 42.9 | 1.77 | +0.0016 |
| USDCAD=X | 32 | 37.5 | 0.82 | -0.0005 |
| USDJPY=X | 251 | 34.7 | 0.40 | -0.0018 |
| NZDUSD=X | 127 | 27.6 | 0.44 | -0.0015 |
| GBPJPY=X | 97 | 10.3 | 0.15 | -0.0039 |
| CADJPY=X | 41 | 9.8 | 0.13 | -0.0039 |
| AUDJPY=X | 91 | 6.6 | 0.11 | -0.0041 |
| EURJPY=X | 162 | 2.5 | 0.03 | -0.0050 |

(Singleton symbols NG=F / ZW=F / SI=F / EURUSD=X omitted — mis-tagged or n=1.)

**No single symbol clears the quality bar.** The only symbols above WR 50% (USDCHF, EURGBP, GBPUSD) are all n<100. The JPY crosses (EURJPY, AUDJPY, GBPJPY, CADJPY) are a 391-trade graveyard at 2.5–10% WR — that is a *carry-unwind / trend-following* failure, not a threshold-scaling failure.

---

## 4. FOREX per-strategy WR (and direction split)

| Strategy | n | WR% | PF | Has fields for ATR test? |
|---|---:|---:|---:|---|
| `cta_cross_asset_tsmom` | 177 | 57.6 | 2.04 | yes — `own_ret_1m`, `vol_target` |
| `fx_smart_forex_rsi2_mean_reversion` | 11 | 54.5 | 1.86 | partial — `atr_14` |
| `combined_confidence` | 12 | 41.7 | 0.70 | no extra fields |
| `ig_contrarian_sentiment` | 253 | 26.5 | 0.46 | `rsi14`, `atr` (not momentum) |
| `fx_smart_carry_trade_momentum` | 28 | 25.0 | 0.59 | `atr_14` |
| `myfxbook_retail_contrarian` | 135 | 17.8 | 0.21 | `rsi14`, `atr` |
| `forex_rsi2_mean_reversion` | 131 | 12.2 | 0.16 | `rsi14`, `atr`, `rsi2` |
| `forex_carry_momentum` | 178 | 5.1 | 0.08 | **yes — `momentum_20d`, `vol_ratio`** |

Direction split (FOREX-only):

| Strategy / Dir | n | WR% | PF |
|---|---:|---:|---:|
| `cta_cross_asset_tsmom` SHORT | 117 | 65.8 | 2.89 |
| `cta_cross_asset_tsmom` LONG | 60 | 41.7 | 1.07 |
| `ig_contrarian_sentiment` SHORT | 57 | 61.4 | 2.24 |
| `ig_contrarian_sentiment` LONG | 196 | 16.3 | 0.21 |
| `forex_carry_momentum` LONG | 178 | 5.1 | 0.08 |
| `forex_rsi2_mean_reversion` LONG | 108 | 7.4 | 0.12 |

`forex_carry_momentum` is **100% LONG** (n=178) — there is no SHORT subset to compare, so a direction mutation cannot rescue it; a *re-parameterization* (Axis 4) is the only mutation available to it. That makes it the primary A4 test subject.

---

## 5. Axis-4 test: does volatility-normalizing the momentum signal help?

The Axis-4 mutation re-expresses the entry trigger as `momentum / volatility` instead of raw momentum. To test it honestly, a strategy must carry **both** a momentum field and a volatility field per pick. Two FOREX strategies qualify:

### 5a. `forex_carry_momentum` (n=178, WR 5.1% — the worst FOREX strategy)

Fields: `momentum_20d` (20-day return) + `vol_ratio` (current vol / reference vol). The Axis-4 proxy is `momentum_20d / vol_ratio`.

| Signal | Winners (median) | Losers (median) | Separation P[win > loss] |
|---|---:|---:|---:|
| raw `momentum_20d` | +0.0276 | +0.0124 | **0.720** |
| `vol_ratio` | +1.071 | +0.903 | — |
| vol-normalized `momentum/vol_ratio` | +0.0258 | +0.0150 | **0.684** |

**Result: normalization DEGRADES separation (0.684 < 0.720).**

Two facts directly contradict the Axis-4 hypothesis:
1. Winners had *higher* raw momentum than losers — the raw signal already discriminates (0.72). Re-scaling it can only blur a signal that is already monotone.
2. Winners had *higher* `vol_ratio` (1.07) than losers (0.90). The hypothesis predicts the opposite: it claims FOREX *under*-fires because vol is too low. Here the profitable picks fired in *higher*-vol conditions. Dividing momentum by vol therefore *penalizes* exactly the winners.

The strategy's 5.1% WR is not a "momentum never reaches the threshold" problem — it fired 178 times, with a momentum signal that *does* rank winners above losers — it is a strategy that loses anyway (PF 0.08). The threshold is not the defect.

### 5b. `cta_cross_asset_tsmom` (n=177, WR 57.6% — the best FOREX strategy)

Fields: `own_ret_1m` (1-month return / momentum) + `vol_target`. Axis-4 proxy `own_ret_1m / vol_target`.

| Signal | Separation P[win > loss] |
|---|---:|
| raw `own_ret_1m` | 0.373 |
| vol-normalized `own_ret_1m / vol_target` | 0.372 |

Normalization changes nothing (0.372 vs 0.373). More tellingly, separation is **below 0.5** — *lower* momentum predicts wins here, and 66% of this strategy's FOREX wins are SHORTs. Its edge is direction (fade / mean-reversion-like), not momentum magnitude, and certainly not a vol-scaled momentum threshold. Median `vol_target` for winners (0.080) is *lower* than for losers (0.100) — again the opposite of the Axis-4 prediction.

### 5c. Data limitation (honest note)

- `atr_14` is populated for only **42/932** FOREX picks (`fx_smart_*` strategies, all n≤28 — below the n-floor). A true ATR(14)-unit re-test on a meaningful sample is **not possible from stored fields**; it would require a yfinance bar-data backfill keyed on each pick's `entry_date`.
- `vol_ratio` and `vol_target` are the best available proxies for "FOREX native volatility regime" and they are populated on the two large momentum strategies — which is why the test above is still meaningful. Both proxies point the same way: winners fired in *higher*-relative-vol conditions, so vol-scaling down the threshold would have *removed winners*, not added them.
- Per-pick realized ATR in price units is absent; the analysis cannot rule out a more sophisticated ATR formulation, but it can and does rule out the specific `momentum / vol` re-parameterization the protocol describes, on the only two strategies with the data to test it.

---

## 6. Step-5 mutation-quality guard

Bar (per Step 1b + vetted-plan n-floor): a candidate winning subset must be **WR ≥ 50%, n ≥ 100, AND n ≥ 10% of the FOREX book (≥ 93)**.

| Candidate subset | n | WR% | PF | Clears bar? |
|---|---:|---:|---:|:--:|
| ATR-normalized `forex_carry_momentum` | — | — | — | **NO** — normalization degrades the signal; no winning subset exists |
| ATR-normalized `cta_cross_asset_tsmom` | — | — | — | **NO** — normalization is signal-neutral; edge is not momentum-magnitude |
| Any single FOREX symbol WR ≥ 50% | ≤49 | 67–82 | — | **NO** — all n < 100 |
| `cta_cross_asset_tsmom` (strategy, all dir) | 177 | 57.6 | 2.04 | clears bar — **but Axis 2/3, not Axis 4** |
| `cta_cross_asset_tsmom` SHORT-only | 117 | 65.8 | 2.89 | clears bar — **but Axis 2 (Direction), not Axis 4** |

**No ATR-normalized (Axis-4) variant clears the quality bar.** The only subsets that clear it are direction/strategy gates that were already discoverable from Axis 2 and do not depend on volatility normalization at all.

---

## 7. Verdict

### A4 (ATR-normalized momentum): **NO-VIABLE-SUBSET**

ATR / volatility-ratio normalization of the FOREX momentum trigger is **not a viable rehab variant**. Evidence:
- On `forex_carry_momentum` (the worst strategy, 100% LONG, the cleanest A4 test), vol-normalization *reduces* winner/loser separation 0.72 → 0.68.
- On `cta_cross_asset_tsmom` (the best strategy), it is signal-neutral (0.372 vs 0.373) and the edge is not momentum magnitude.
- On both strategies, winners fired in *higher*-volatility conditions — the exact inverse of the Axis-4 premise that FOREX loses because its low native vol keeps momentum below the threshold.

FOREX should **stay hard-disabled**. The Step-1b acceptance gate (normalized variant must reach PF > 1.0 and WR > 45% over 30 days) is not approached by any ATR-normalized subset, so no FOREX emission resumes.

### Incidental finding (NOT A4, do not act on it under this ticket)

`cta_cross_asset_tsmom` **SHORT-only** clears the quality bar (n=117, WR 65.8%, PF 2.89) and `ig_contrarian_sentiment` **SHORT-only** is borderline (n=57, WR 61.4%, PF 2.24, below n-floor). These are **Axis-2 (Direction)** candidates. They should be routed through the normal Direction-axis mutation path (`docs/MUTATION_THREE_AXIS_PROTOCOL.md` Step 3, DNA ticket, SANDBOX tier) and `STRATEGY_INVESTIGATION_BEFORE_KILL.md` — separately from A4. They are recorded here so the signal is not lost, but A4's charter is the volatility-normalization axis and that axis is closed: negative.

### Recommended next step for A4 closure

If the team wants a *definitive* kill of the Axis-4 hypothesis (vs the "stored fields are too thin" caveat in §5c), the single remaining experiment is a **yfinance ATR(14) backfill** keyed on `entry_date` for the 178 `forex_carry_momentum` picks, then re-run the separation test in true ATR units. Until then, this report's evidence (two independent strategies, both negative, both contradicting the premise's vol-direction) is sufficient to keep FOREX disabled and to **deprioritize** further ATR-normalization work.

---

## Appendix — reproducer

```bash
# 3-axis autopsy (Direction / Timeframe / Symbol)
python tools/mutation_analysis.py --json

# FOREX-only slice + Axis-4 field audit + Step-5 guard
python tools/forex_atr_mutation_helper.py
```

Helper script: `tools/forex_atr_mutation_helper.py` (this PR). `py_compile`-clean. Read-only — no production wiring, consistent with the Wire-Up Rule exemption for research/sidecar tooling.
