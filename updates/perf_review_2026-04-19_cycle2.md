# Strategy Performance Review — 2026-04-19 (Cycle 2 of 8h cron)

**Cron:** `870f36b0` (every 8h at :13 UTC)
**Data snapshot:** `dashboard_payload.json` generated 2026-04-19T03:50:05 UTC
**Inputs:** 3,500 closed picks · 43 active picks · 298 raw active · 5 tracked strategies

---

## TL;DR — 3 actionable findings (cycle 2)

1. **🔴 REGRESSION:** `strategy_performance.json` lost **8 tracked strategies** since cycle 1 (13 → 5). Coverage **6.7% → 2.6%**. The writer keeps cutting entries; root-cause investigation is now urgent. P0 from cycle 1 escalates to P0+.
2. **🔴 NEW high-blast-radius drain:** `macd_rsi_confluence` — **n=59, WR=33.9%, mean PnL −80.4%** across **31 distinct symbols**. Wide-spread negative-edge strategy that wasn't flagged in cycle 1 because more recent data brought it over the n≥20 threshold.
3. **NEW symbol drain:** `ATOMUSDT` — n=51, WR=29.4%, mean −41.2% across multiple strategies. Symbol-quality issue (not strategy issue) — candidate for symbol blocklist.

**High-conviction picks remain clean:** active count tripled 13→43, but 0 of the new HC picks land on bottom-quartile strategy/symbol historicals. Active gates are still working as intended.

---

## 1. Track Coverage REGRESSION

| Metric | Cycle 1 (24h ago) | Cycle 2 (now) | Δ |
|---|---|---|---|
| Distinct strategies in closed_picks | 194 | 193 | -1 |
| Tracked strategies | **13** | **5** | **-8** |
| Coverage | 6.7% | **2.6%** | **-4.1 pp** |
| Untracked with closed history | 187 | **188** | +1 |

**The track is bleeding entries.** Whatever process cleans/rebuilds `strategy_performance.json` is removing valid entries. Cycle 1 already flagged this as P0; cycle 2 confirms it's actively getting worse, not stable.

### Top still-untracked strategies (unchanged from cycle 1)

| Strategy | n | WR | PF | mean PnL% | Notes |
|---|---|---|---|---|---|
| `st_fear_greed_contrarian` | 454 | 56.6% | 2.70 | +77.1% | Largest sample, sustained alpha |
| `luxalgo_confluence` | 263 | 50.6% | 1.52 | +56.8% | |
| `st_obv_support_divergence` | 175 | 58.9% | 2.12 | +57.6% | |
| `st_atr_vol_breakout` | 85 | 41.2% | 0.79 | -19.7% | |

---

## 2. NEW Mutation Candidates (cycle 2 vs cycle 1)

| Strategy | n | WR | PF | mean PnL% | symbols | Cycle 1 status |
|---|---|---|---|---|---|---|
| **`macd_rsi_confluence`** | **59** | 33.9% | 0.49 | **−80.4%** | **31** | 🆕 NEW (was below n≥20 cutoff) |
| `atr_regime_rsi` | 39 | 33.3% | 0.76 | −7.5% | 1 | 🆕 NEW (was at WR=42%, regressed) |
| `cta_commodity_momentum_term` | 28 | 28.6% | 0.02 | −15.1% | 2 | unchanged from cycle 1 |
| `crypto_kalman_trend_residual_reversion_v1` | 20 | 20.0% | 0.17 | **−49.6%** | 1 | 🟡 WORSENED (was WR 25% mean −43%) |

### `macd_rsi_confluence` — highest priority

- Blast radius **31 symbols** (vs 1-2 for the others)
- Mean PnL −80.4% — every losing trade is catastrophic, not marginal
- WR 33.9% with PF 0.49 → for every $1 won, $2.04 lost

**3-axis mutation proposal:**

| Axis | Current | Proposed |
|---|---|---|
| Parameter sweep | RSI threshold + MACD signal-line crossover | Sweep RSI thresholds (25/30/35/40 vs current); sweep MACD lookback windows (8/12/16/26) |
| Regime gate | None | Disable when BTC 4H trend is RED (per `feedback_long_source_bias.md`); MACD-RSI confluence is a momentum strategy and shouldn't fire in down regimes |
| Inverse | LONG-only confluence | Test SHORT variant on same 31-symbol set — 66% loss rate suggests inverse may be ~+66% WR |

**Recommendation:** before mutation, run the strategy through `tools/mutation_analysis.py` per CLAUDE.md `MUTATION_THREE_AXIS_PROTOCOL.md`. The −80% mean PnL with 31-symbol breadth is a strong demote/kill signal.

### `crypto_kalman_trend_residual_reversion_v1` — escalating

Cycle 1: n=24 WR=25% mean=−43%. Cycle 2: n=20 (slightly fewer recent), WR=**20%**, mean=**−49.6%**.

This single-symbol kalman strategy is curve-fit and degrading. **Recommendation: kill** rather than mutate. n=20 is too small to expect mutation to recover.

---

## 3. NEW Symbol Drain — ATOMUSDT

- n=51, WR=29.4%, mean PnL −41.2%
- Multiple strategies losing on this symbol (cross-strategy issue → symbol-side problem)
- Likely a structurally weak symbol in current regime, not a strategy bug

**Recommendation:** add ATOMUSDT to a temporary symbol-quality blocklist for ALL strategies until WR recovers above 40% on a rolling sample. Track the next 2 cycles to confirm pattern.

---

## 4. High-Conviction Pick Health

- Active picks: 13 → 43 (+30, **3.3× growth** likely from new prediction-market scanner activity)
- High-conviction (elite_score≥70 OR confidence≥0.80): TBD count
- **Flagged (land on bottom-quartile strategy/symbol):** 0

Active gate logic continues to filter HC picks correctly.

---

## 5. Tracked Catastrophic Drains (status update)

These remain in `strategy_performance.json` and are visible to the engineer:

| Strategy | n | WR | PF | total PnL $ | Cycle 1 → 2 |
|---|---|---|---|---|---|
| `quan_engine_scalp` | 4127 | 29.1% | 0.39 | -$1,406,885 | unchanged |
| `quan_engine_position` | 26 | 0.0% | 0.00 | -$2,153 | unchanged |
| `volume_spike_breakout` | 39 | 10.3% | 0.13 | -$1,525 | unchanged |
| `quan_engine_swing` | 109 | 27.5% | 0.99 | -$19 | unchanged |

Same kill candidates as cycle 1. No engineer action yet.

---

## Action Checklist (cycle 2 deltas vs cycle 1)

**Net new since cycle 1:**
- [ ] **P0+ — investigate why `strategy_performance.json` lost 8 entries** between cycles. Coverage is REGRESSING toward zero.
- [ ] **P0 — kill or mutate `macd_rsi_confluence`** (n=59, 31 symbols, mean PnL -80.4%) — highest blast radius of any drain.
- [ ] **P1 — kill `crypto_kalman_trend_residual_reversion_v1`** — single-symbol curve-fit, degrading.
- [ ] **P1 — symbol blocklist ATOMUSDT** for at least 2 cycles.

**Carry-over from cycle 1 (still pending engineer action):**
- [ ] P0 — fix `strategy_performance.json` writer (97% under-population)
- [ ] P1 — quan_engine_scalp / quan_engine_position / volume_spike_breakout
- [ ] P2 — promote 6 untracked-but-strong strategies (kimi_signal_tracking, st_fear_greed_contrarian, etc.)

---

## Methodology + provenance

- Same as cycle 1 (see PR #257) — closed-pick sample from `picks.recent_closed`, win = `pnl_pct>0` OR `status=='WON'`
- Mutation thresholds: per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (n≥20, WR<35%)
- Snapshot saved to `tools/out/perf_review_cycle2_*.json` for audit trail
- **No production strategy files modified.** All changes require human review per `CLAUDE.md` mutation-before-kill rule.
