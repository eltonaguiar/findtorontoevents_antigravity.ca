# EAGLE2 Value-Add Findings — 2026-06-02 Live Data Analysis
## Deep-dive into concentration, edge decay, tournament rankings, and strategy gaps

---

## 1. SECURITY FINDING: Killed Strategy Still Emitting

**Kimi Signal Tracking has 134 active picks (12.6% of book)** despite being on
`BLACKLISTED_STRATEGIES` in `config.py`. This means either:
1. The emitter discipline gate isn't catching source-system-level picks (only strategy-level)
2. `kimi_signal_tracking` is emitting via a different source name that bypasses the check

**Action:** The `emitter_discipline.py` source-system check needs to cover full
match, and we should add `kimi_signal_tracking` to `HARD_KILL_STRATEGIES` in
both `config.py` and `emitter_discipline.py`.

---

## 2. CRYPTO EDGE DECAY PATTERN (CRITICAL)

| Window | WR | PF | n | Verdict |
|--------|-----|-----|-----|---------|
| 7-day | 59.3% | 2.98 | 214 | EXCELLENT short-term |
| 30-day | 46.1% | 1.39 | 1142 | Marginal, decaying |
| 90-day | 49.0% | 0.97 | 4101 | Dead |
| All-time | 48.6% | 0.97 | 4160 | Dead |

**Interpretation:** CRYPTO strategies work short-term (PF 2.98 over 7 days) but
the edge rots rapidly. After 30 days, PF drops to 1.39 — barely above
breakeven. The decay from 7d to 90d is 67% PF loss.

**Root cause:** Picks are held too long. The current CRYPTO max-hold is 48 hours
in `universal_pick_resolver.py` — yet the 7d window still shows PF 2.98. This
suggests the problem isn't hold time per se, but that the signal quality of
active picks degrades over time — older picks that haven't resolved are simply
bad picks.

**Value-add action:** Implement a **signal freshness decay** — picks older than
48h that haven't hit TP/SL should be force-closed regardless. This is already
in the resolver (48h TIME_EXIT for CRYPTO) but the data shows picks are
lingering beyond that.

---

## 3. TOURNAMENT RANKINGS: n-SAMPLE FILTER REVEALS TRUE LEADERS

### Raw PF ranking (MISLEADING — tiny samples dominate):

| Model | PF | WR | n | Real? |
|-------|-----|-----|-----|-------|
| fireworks_qwen | 24.34 | 88.9% | **9** | NO — n=9 |
| groq_kimi_k2 | 11.23 | 85.7% | **7** | NO — n=7 |
| gpt4o_mini | 10.50 | 80.0% | **10** | NO — n=10 |

### n≥30 filtered ranking (TRUSTWORTHY):

| Model | PF | WR | n | Tier |
|-------|-----|-----|-----|------|
| **deepseek_v4** | 3.46 | 57.7% | 208 | **T1** |
| **gpt4o** | 3.14 | 59.7% | 134 | **T1** |
| **deepseek_r1** | 2.93 | 62.9% | 132 | **T1** |
| **grok3** | 2.29 | 55.8% | 303 | **T1** |
| grok4_3 | 1.22 | 45.0% | 129 | T2 |

**Value-add action:** The tournament leaderboard at
`/audit/ai-tournament.html` must show n (sample size) prominently and
filter/deprioritize models with n<30. Currently the PF-sorted view shows
tiny-n models at the top, misleading users.

---

## 4. FOREX 90d PF ANOMALY

FOREX shows PF 2.5 at 90d (n=1658) but PF 0.3 at 30d (n=?) and WR 22.4%.
This is the classic "high WR, terrible PF" pattern reversed — good historical
PF but current collapse.

The 90d PF of 2.5 on n=1658 suggests FOREX USED TO work. The 30d collapse to
PF 0.3 with WR 22.4% suggests either:
1. A regime change (strong dollar cycle broke mean-reversion strategies)
2. The resolver contamination fix (Phase 1) removed fake wins — revealing the
   true, terrible performance
3. Both

**Value-add action:** Run a cohort analysis on FOREX: split picks into pre-fix
(before 2026-06-02 TIME_EXIT unification) vs post-fix. If PF drops from 2.5
to 0.3, the "edge" was entirely resolver contamination. This would confirm
the quant verdict and justify the hard-disable.

---

## 5. CRYPTO SOURCE CONCENTRATION — MONEY-READY BLOCKER

The money_ready_verdict.json for CRYPTO shows:
- Top source: 55.1% of picks from ONE source
- Source concentration CAPPED (exceeded threshold)
- DSR: 0.0001 (essentially zero — massive overfitting signal)
- PBO: 0.1197 (barely passed)
- SPA: p=0.608 (failed)
- MDD: 100% (complete wipeout at some point)

**This is the statistical proof of what the quant report said:** CRYPTO's
aggregate production book has NO real edge. The apparently decent surface
stats (PF 0.92, WR 36%) are driven by one dominant source that has failed
every multiple-testing correction.

---

## 6. CONCENTRATION MONITOR — LIVE DATA

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Symbol HHI | 0.0193 | 0.25 | ✅ Healthy |
| Source HHI | 0.1488 | 0.25 | ✅ Healthy |
| Top source share | 33.5% (signal_validation) | 40% | ⚠️ Approaching |
| Kimi (killed) share | 12.6% | — | ❌ Should be 0% |

**Finding:** Symbol concentration is excellent (BTC, ETH, SOL each ~4-5%).
Source concentration is healthy but `signal_validation` at 33.5% is worth
watching. The `kimi_signal_tracking` presence is a bug.

---

## 7. LiteLLM STRATEGY BRAINSTORM SYNTHESIS

### FOREX (from scratch — current book disabled):
1. **Volatility-Adjusted Carry Trade** — AUD/JPY, NZD/USD. Entry: 20d low USD funding + VIX<15 + 50d momentum. Hold 60-120d. Expected PF 1.4-1.6.
2. **Central Bank Divergence Mean Reversion** — EUR/USD, USD/CAD. Entry: RSI(14)<30 for 3 days + rate differential >50bps. Hold 15-45d. Expected PF 1.3-1.5.
3. **Real Yield Differential Rebalancing** — USD/CHF, EUR/USD. Entry: yield gap >2σ + converging inflation. Hold 30-90d. Expected PF 1.2-1.4.

### COMMODITY / FUTURES / BOND (from scratch):
Ideas from agent brainstorming pending retry (timeout on `paid-mode`).

### Statistical Methodology Gaps (LiteLLM consensus):
The agent confirmed our arsenal is strong but identified walk-forward
optimization as the #1 most important test — above Bonferroni — because it
simulates real re-optimization cycles. We have WFO in 3 different modules
but it's not the DEFAULT gate. The admissibility pipeline already puts
purged-embargoed WF as Step 3, which is correct.

**Missing from our arsenal:**
1. **Walk-Forward EFFICIENCY metric** (already in pipeline Step 3 but not
   used as a decision gate elsewhere)
2. **Regime-conditional Sharpe** (breakdown by VIX quartile — we have regime
   classifier but it's not producing per-regime Sharpe reports)
3. **Live/paper tracking decay** — comparing per-period PF against backtest
   PF, flagging when live drops below 80% of expected

---

## 8. IMMEDIATE ACTION ITEMS (PRIORITIZED)

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 1 | Fix kimi_signal_tracking emission (12.6% of book from killed source) | HIGH | Low |
| 2 | Add n≥30 filter to tournament leaderboard display | HIGH | Low |
| 3 | Implement signal freshness decay for CRYPTO (force-close >48h unresolved) | MEDIUM | Low |
| 4 | Cohort analysis: FOREX pre-fix vs post-fix PF to confirm contamination hypothesis | HIGH | Medium |
| 5 | Wire WFO efficiency as decision gate in strategy_promotion_pipeline | MEDIUM | Medium |
| 6 | Create FOREX carry trade + mean reversion strategy specs from LiteLLM ideas | MEDIUM | High |
| 7 | Add per-regime Sharpe breakdown to edge stability reports | LOW | Medium |
