# perf-review: 8h cycle 2026-04-21 (cycle 10) — 48h vs 14d truth tells different stories

**Author:** Claude Opus 4.7 (1M context)
**Generated:** 2026-04-21 ~20:15 UTC
**Source:** `audit_trail/data/dashboard_payload.json` (3,500 closed, 60 active picks)
**Tracking:** `alpha_engine/data/strategy_performance.json` (~187 keys)
**Cycle:** 10 of recurring 8-hour perf-review series
**Related:** PR #297 (cycle 8), PR #299 (cycle 9), PR #310 (Ollama fact-check)

---

## TL;DR — the bombshell from the verification work

The 48h-window bounce-bias I documented in PR #310 + verified in the 14d window (PR #311 comment thread) is now the dominant context for this cycle:

| Window | n | WR | PF | cum PnL% |
|---|---|---|---|---|
| **48 hours** | 638 | 39.3% | 1.35 | **+111.91** ← bounce-day biased |
| **7 days** | 2,216 | 26.3% | 0.61 | **−1,232.69** |
| **14 days** | 2,518 | 26.1% | 0.65 | **−1,169.12** |
| Full ~21d | 3,500 | 31.1% | 0.72 | −1,134.17 |

**At any window ≥ 7 days, we're catastrophically negative.** Cycle 8/9 perf-reviews + 6-peer chaos was largely chasing the 48h bounce-day signal. The system's true edge over 7-14d is negative.

## Cycle 9 → Cycle 10 delta

| Metric | Cycle 9 | Cycle 10 | Δ |
|---|---|---|---|
| Active book | 30 | **60** | **+30 (doubled)** |
| HC picks | 14 | 30 | +16 |
| HC flagged on bottom-quartile sym | 1 | 3 | +2 |
| Mutation candidates (n≥20, WR<35%, PF<1) | 12 | 10 | −2 |
| `copy_hl_lb_None` cum | −806% | −806% | unchanged (zombie) |
| `st_fear_greed_contrarian` cum | −359% | −359% | unchanged (zombie) |
| Naming-mismatch silent failure | 87% | **91%** (166/182) | +4pp worse |

**Active book DOUBLED.** Cycle 9 reported 30 active picks; cycle 10 has 60. Either gate enforcement loosened or emission picked up. Concerning given 14d cum is -1169%.

## §1 — Per-strategy mutation candidates (n ≥ 20, WR < 35%, PF < 1)

10 strategies meet refined threshold (added `PF < 1.0` per PR #310 caveat to exclude TP-skew positives like `forex_rsi2_mean_reversion` PF 3.71).

| Strategy | n | WR | PF | cum% | Notes |
|---|---|---|---|---|---|
| `non_crypto_consensus` | 88 | 0.0% | n/a | +0.01 | resolver flat-close (already retired in PR #302) |
| `cta_commodity_momentum_term` | 46 | 8.7% | 0.01 | −4.29 | mutate (regime gate) |
| `ensemble` | 24 | 16.7% | 0.64 | −9.02 | dispatcher mislabel — investigate |
| `atr_regime_rsi` | 29 | 17.2% | 0.26 | −10.38 | mutate |
| `st_atr_vol_breakout` | 27 | 22.2% | 0.27 | −21.55 | mutate |
| **`st_fear_greed_contrarian`** | 627 | 24.6% | 0.37 | **−358.82** | **ZOMBIE — retired but emitting** |
| `kimi_signal_tracking` | 36 | 27.8% | 0.45 | −97.81 | escalating (was −107 in cycle 9) |
| `macd_rsi_confluence` | 48 | 29.2% | 0.42 | −50.49 | new mutation candidate |
| `unknown` | 49 | 30.6% | 0.72 | −15.60 | tagging gap — investigate |
| **`copy_hl_lb_None`** | 278 | 32.0% | 0.56 | **−806.39** | **ZOMBIE — retired but emitting** |

**Combined drag from these 10: −1,374% cum PnL.** Two zombie strategies (`copy_hl_lb_None`, `st_fear_greed_contrarian`) own −1,165 of that — same as cycles 3-9 reported.

## §2 — Per-symbol block candidates (n ≥ 30, WR < 30%)

23 symbols meet threshold. Top losers by cum PnL:

| Symbol | Class | n | WR | cum% |
|---|---|---|---|---|
| `OPUSDT` | CRYPTO | 62 | 19.4% | **−117.99** |
| `SUIUSDT` | CRYPTO | 79 | 20.3% | −88.24 |
| `APTUSDT` | CRYPTO | 66 | 22.7% | −82.58 |
| `AVAXUSDT` | CRYPTO | 67 | 16.4% | −50.49 |
| `LINKUSDT` | CRYPTO | 57 | 17.5% | −42.23 |
| `DOGEUSDT` | CRYPTO | 65 | 23.1% | −47.40 |
| `ADAUSDT` | CRYPTO | 62 | 22.6% | −38.15 |
| `EURJPY=X` | FOREX | 43 | 7.0% | −13.72 |
| `EURUSD=X` | FOREX | 70 | 18.6% | −10.84 |

The 7 crypto altcoins (OP/SUI/APT/AVAX/LINK/DOGE/ADA) match my earlier symbol-block list from PR #305 (closed) and PR #311's separate concern set. **But per PR #310/PR #305-close lesson: hard-block was wrong because these print on bounce days. Regime-conditional gate (PR #309) is the right tool.**

## §3 — High-conviction cross-reference (elite_score ≥ 70 OR confidence ≥ 0.80)

30 active HC picks. **3 flagged on bottom-quartile symbols:**

| Symbol | Strategy | elite | conf | Flag |
|---|---|---|---|---|
| OPUSDT | super signal (super) via claude_gainer_st | 48 | **0.99** | sym-block-cand WR=19.4% n=62 |
| LINKUSDT | super signal (super) via kimi | 34 | **0.99** | sym-block-cand WR=17.5% n=57 |
| DOGEUSDT | super signal (super) via kimi | 48 | **0.99** | sym-block-cand WR=23.1% n=65 |

Pattern: super-signal composites at conf 0.99 + low elite_score (34-48) on bottom-quartile symbols. Same pattern flagged in PR #285/#287/#294 cycles. **Recommend reactive emergency block** for the next cycle until conf 0.99 + elite < 70 + sym_wr < 0.30 gate ships.

## §4 — Data-flow gap (closed picks vs strategy_performance.json)

| Metric | Cycle 9 | Cycle 10 |
|---|---|---|
| Closed strategies in `recent_closed` | 191 | **182** |
| Tracked in `strategy_performance.json` | 185 | **187** |
| **Closed → not tracked** | **166 (87%)** | **166 (91%)** |
| Tracked → never closed | 160 | ~169 |

**Naming-mismatch silent failure rate worsened from 87% to 91%.** PR #289 diagnostic still applies.

## §5 — DNA mutation suggestions

See `mutations/proposed_2026-04-21_cycle10.yaml`.

## §6 — Action items (priority order)

### P0 — Investigate active book doubling (30 → 60)

In 8 hours, active book grew 100%. Either a gate was disabled, a new emitter came online, or the flush logic broke. Check `audit_dashboard/template.html` rendering vs source pick count, and check if any of the recent peer PRs (#306, #307, #311) accidentally relaxed a gate.

### P1 — Apply Cycle 10's HC emergency-block gate

3 active picks flagged with conf 0.99 + low elite_score on bottom-quartile crypto. Add gate:
```python
if asset_class == "CRYPTO" and confidence >= 0.95 and elite_score < 70 and \
   symbol_historical_wr(symbol, n_min=30) < 0.30:
    return None  # reject
```

### P2 — Plug the zombie leak (copy_hl_lb_None + st_fear_greed_contrarian)

Combined −1,165 cum PnL across cycles 3-10. Both are in `_RETIRED_STRATEGIES` but still close 989 picks across 14d. **The retirement gate isn't covering all emitters.** Cycle 9 P0; still unresolved.

### P3 — Stop drawing conclusions from 48h windows

The 48h bounce profit (+115%) is regime artifact, not edge. PR #310 + Ollama models warned. Don't approve PR #311's confidence-cap-at-0.7 (Kimi tweak) or block-shorts (Kimi+Roocode tweak) — both refuted by 14d data. See PR #311 comment thread.

### P4 — Continue PR #289 alias backfill

87% → 91% silent failure is getting worse, not better.

### P5 — Investigate `non_crypto_consensus` resolver bug

Already retired in PR #302 but the underlying bug (TP-at-entry / pnl=0) is unfixed and will affect any new strategy with similar TP/SL setup.

## Acceptance

**Nothing in this PR modifies production files.** The 60-active-pick state of cycle 10 is concerning enough to warrant an immediate engineer look at the active-book doubling AND the conf=0.99 HC bypass, BEFORE merging any other peer PRs.
