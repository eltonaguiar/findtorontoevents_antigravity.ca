# Strategy Performance Review — 2026-04-20 (cycle 7)

**Cycle:** 8h cron `870f36b0`, fired 20:13 UTC
**Inputs:** `audit_trail/data/dashboard_payload.json` (3,500 closed, 44 active, 27 HC-tier), `alpha_engine/data/strategy_performance.json` (182 entries)
**Previous:** [#1](perf_review_2026-04-18.md) · [#2](perf_review_2026-04-19_cycle2.md) · [#3](perf_review_2026-04-19_cycle3.md) · [#4](perf_review_2026-04-19_cycle4.md) · [#5](perf_review_2026-04-20_cycle5.md) · [#6](perf_review_2026-04-20_cycle6.md)

---

## TL;DR — 3 top findings

1. **Cycle 6 "recovery" was a mirage — drains came back with interest.** HC flags 4→0→2 (super_signal reappeared). Symbol drains 11→0→**9** (alt-coin regime blood bath: AVAXUSDT 14.9%, ADAUSDT 15.3%, SUIUSDT 18.1%, LINKUSDT 18.6%, DOGEUSDT 20.6%, LTCUSDT 22.6%, UNIUSDT 22.7%, APTUSDT 23.2%, OPUSDT 25.4%). 9 simultaneous alt-coin drains = regime signal, not strategy bugs.
2. **Track coverage hit new low: 8.8%** (cycle 5: 91.2% → 6: 12.1% → 7: 8.8%). Writer is completely broken. This is the third consecutive cycle of regression after the cycle-3 partial fix. 166 of 182 closed strategies have no tracked entry.
3. **`kimi_signal_tracking` reversed hard — alpha decay.** Cycle 1 had it as a PROMOTION candidate (n=31, WR 74%, PF 5.63). Cycle 7: n=41, WR **31.7%**, mean PnL **−209%**. Complete reversal in 3 days.

---

## 1. Strategy Drain Candidates (n≥20, WR<35%)

| Strategy | n | WR | PF | mean PnL% | Notes |
|---|---|---|---|---|---|
| `st_obv_support_divergence` | 89 | 24.7% | 0.22 | −90% | **NEW** on drain list (was cycle-1 promotion candidate) |
| `unknown` (no-strategy picks) | 54 | 25.9% | 0.43 | −73% | Data-quality issue; emitter writes blank `strategy` |
| `st_fear_greed_contrarian` | **641** | 26.2% | 0.54 | −41% | **LARGEST sample** on the drain list; still NOT tracked |
| `ensemble` | 31 | 29.0% | 1.65 | +65% | WR<35% but PF>1 (tail-heavy) — mutation not kill |
| `atr_regime_rsi` | 35 | 31.4% | 0.69 | −12% | NEW |
| `kimi_signal_tracking` | 41 | **31.7%** | 0.53 | **−209%** | CYCLE 1 PROMOTION CANDIDATE, now drain |
| `copy_hl_lb_None` | **278** | 32.0% | 0.56 | **−290%** | **STILL** emitting after 5 cycles of flagging |
| `cta_commodity_momentum_term` | 39 | 33.3% | 0.02 | −11% | Same as cycle 1; unchanged |
| `luxalgo_confluence` | 146 | 33.6% | 0.74 | −34% | NEW on drain list |
| `macd_rsi_confluence` | 46 | 34.8% | 0.53 | −83% | Same as cycle 2; unchanged |

## 2. Symbol Drains (n≥30, WR<30%) — 9 drains (REGIME SIGNAL)

| Symbol | n | WR | PF | mean PnL% |
|---|---|---|---|---|
| **AVAXUSDT** | 67 | **14.9%** | 0.33 | −80% |
| **ADAUSDT** | 59 | **15.3%** | 0.24 | −80% |
| **SUIUSDT** | 83 | 18.1% | 0.24 | −112% |
| LINKUSDT | 59 | 18.6% | 0.31 | −71% |
| DOGEUSDT | 63 | 20.6% | 0.21 | −77% |
| LTCUSDT | 31 | 22.6% | 0.46 | −41% |
| UNIUSDT | 44 | 22.7% | 0.10 | −103% |
| APTUSDT | 69 | 23.2% | 0.23 | −120% |
| OPUSDT | 67 | 25.4% | 0.19 | −166% |

**Note:** Cycle 4 showed 8 alts draining simultaneously; cycle 7 shows 9 with DEEPER losses (14.9%-25.4% WR range). This is a BTC dominance / alt-bleed regime. **Recommendation:** Apply a `alt_season_off` regime gate — pause alt-only LONG strategies when BTC.D > 58% and rising.

## 3. High-Conviction Pick Flags

2 HC picks flagged — **both are `super_signal` variants** (elite_score ≤ 39, confidence ≥ 0.814). Same structural issue flagged in cycle 5.

| HC Pick | Strategy | Symbol | elite | conf | Why flagged |
|---|---|---|---|---|---|
| #1 | `super signal (strong) via alpha_engine` | APTUSDT | 39 | 0.814 | APTUSDT on drain list (n=69, WR 23.2%) |
| #2 | `super signal (super) via kimi` | DOGEUSDT | 28 | 0.99 | DOGEUSDT on drain list (n=63, WR 20.6%) |

**Still need the symbol-quality guard I proposed in cycle 5:**
```python
# audit_trail/quality_gates.py passes_active_gate
if confidence >= 0.80 and symbol_historical_wr(symbol, n_min=30) < 0.30:
    return None  # symbol-quality override
```
This single line would reject both of the above.

## 4. Data-Flow Gap — P0 REGRESSED AGAIN

| Cycle | Tracked | Closed strats | Coverage |
|---|---|---|---|
| 1 | 13 | 193 | 6.7% |
| 2 | 5 | 206 | 2.4% |
| 3 | 163 | 206 | **79.1%** |
| 4 | 173 | 208 | 83.2% |
| 5 | 188 | 206 | **91.2%** |
| 6 | 178 | 206 | 12.1% |
| **7** | **182** | **182** | **8.8%** |

The writer was FIXED between cycles 2 and 3 (took coverage 2.4% → 79%). It has been regressing ever since. Most likely cause: a stale/broken code path re-introduced on the writer. Needs a root-cause fix, not another partial patch.

Top missing strategies: `st_fear_greed_contrarian` (641), `copy_hl_lb_None` (278), `luxalgo_confluence` (146), `st_obv_support_divergence` (89), `kimi_signal_tracking` (41).

## 5. DNA Mutation Proposals

### `kimi_signal_tracking` — inverse test first (alpha decay pattern)

| Axis | Current | Proposed |
|---|---|---|
| Parameter sweep | (unknown) | Snapshot current params; compare to cycle-1 params if available |
| Regime gate | none | BTC.D regime filter — long only when BTC.D < 56% |
| Inverse | LONG signals | **Test SHORT variant** on same symbols — 68.3% would-be wins |

### `st_fear_greed_contrarian` — regime + symbol pruning (largest drain)

| Axis | Current | Proposed |
|---|---|---|
| Parameter sweep | fear/greed thresholds | Scan 0.7× to 1.3× current threshold |
| Regime gate | none | Disable when VIX < 14 OR when BTC 4H trend is red |
| Symbol expansion | all-crypto | **Restrict to BTC/ETH** only until WR recovers to ≥45% |

### `copy_hl_lb_None` — EMITTER FIX, not mutation (5 cycles flagged)

Not a mutation candidate. The `_None` suffix is a parameter-serialization bug. **Engineer action:** Grep `copy_hl_lb` across emitters; find `f"copy_hl_lb_{lookback}"` where `lookback` is `None`; fix the caller.

### `luxalgo_confluence` — regime gate

| Axis | Current | Proposed |
|---|---|---|
| Parameter sweep | confluence count | Require ≥3 confluences instead of ≥2 |
| Regime gate | none | BTC.D gate same as above |
| Inverse | N/A | Skip; not a pure directional signal |

---

## Cross-cycle trend

| Metric | 1 | 2 | 3 | 4 | 5 | 6 | **7** |
|---|---|---|---|---|---|---|---|
| HC flags | 0 | 0 | 0 | 2 | 4 | 0 | **2** |
| Strat drains | 8 | 10 | 10 | 8 | 9 | 4 | **10** |
| Sym drains | 0 | 1 | 4 | 8 | 11 | 0 | **9** |
| Track cov % | 6.7 | 2.4 | 79.1 | 83.2 | 91.2 | 12.1 | **8.8** |

Three trends:
1. **HC flags oscillating** around super_signal — needs the symbol-quality guard landed.
2. **Symbol drains clustered in alt-coin regime** (zero on BTC/ETH both cycles).
3. **Track coverage has degraded 3 cycles in a row** after the cycle-3 partial fix. Writer regression is structural, not a one-off.

---

## Action Checklist

- [ ] **P0 — debug strategy_performance.json writer** (regression 3 cycles running; cycle-3 fix appears un-done)
- [ ] **P1 — land symbol-quality guard** (`confidence >= 0.80 && symbol_hist_wr < 0.30`) to kill super_signal HC leakage
- [ ] **P1 — fix copy_hl_lb_None emitter** (5 cycles of inaction)
- [ ] **P1 — alt-season regime gate** on 9-symbol drain cohort (pause LONGs when BTC.D > 58% and rising)
- [ ] **P2 — mutate kimi_signal_tracking** (inverse test first; cycle-1 WR 74% → cycle-7 WR 32% is clean alpha decay)

**Nothing in this PR modifies production strategy files.**
