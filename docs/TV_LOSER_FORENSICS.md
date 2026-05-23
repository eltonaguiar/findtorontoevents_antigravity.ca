# TV Paper Trading Loser Forensics — 2026-04-04

**Author:** claude-bus-setup + subagent (general-purpose)
**Source data:** `audit_dashboard/data/dashboard_data.json`, `alpha_engine/smart_picks_engine.py`, live TV paper portfolios
**Goal:** understand why losers shipped, propose scoring fixes

---

## The losers (what shipped, what happened)

| Symbol/Dir | Score | Conf | Grade | Strategy | Historical | Verdict |
|---|---|---|---|---|---|---|
| **ALGOUSDT LONG** | **79** (#1 rank) | 0.78 | C | enhanced_ml_A_xgboost | 22 trades, **50% WR, +0.69% avg** | Coin-flip, ranked #1 on confidence fallback |
| **AVAXUSDT SHORT** | **0** | 0.82 | D | contrarian_consensus_flip | 5 trades, **20% WR** | Shipped despite score=0, against 92% LONG consensus |
| **DOGEUSDT SHORT** | 10 / 0 | 0.81 / 0.68 | B / B | kalshi + prediction_market | — | Against 76% LONG consensus, grade B anyway |
| **LINKUSDT SHORT** | n/a | — | — | — | Sparse | Can't find in active picks |

## The winner we almost missed

| FETUSDT LONG | Score | Conf | Strategy | Historical |
|---|---|---|---|---|
| | **43-59** (ranked lower than ALGO!) | 0.81-0.92 | super_signals (alpha_engine + ml_crypto_pred) | **83% WR, +2.20% avg across 6 trades** |

**FET scored LOWER than ALGO despite 83% WR and multi-system consensus.** This is the scoring bug in one sentence.

---

## Common failure patterns

All 4 losers share:

1. **Strategy isolation** — single-source picks. No `agreeing_systems`, no multi-system confluence. Winners (FET) came from "strong consensus (alpha_engine, ml_crypto_pred)".
2. **Direction against trust-weighted consensus** (AVAX-S, DOGE-S) — `conflicts` block already flagged these but nothing blocks them.
3. **Null ml/elite scores** → ranker falls back to `confidence * 0.8` which has weak PnL correlation.
4. **Confidence 0.78-0.82 "sweet spot"** — skill doc claims 87% WR, but these all sat in that range and lost.
5. **No concentration cap** — ALGO in 3 portfolios simultaneously; dedup only works within one publishing run.

---

## Code-level fixes (6 concrete, line-numbered)

### P0 #1 — Penalize ml_composite fallback
**File:** `alpha_engine/smart_picks_engine.py:24-44` (`_compute_ml_composite`)
**Fix:** When `ml_score is None`, downrank by `conf * 0.5` or require minimum `agreeing_systems` count.
**Impact:** Would demote ALGO-L from #1 rank (it has null elite_score AND null ml_score).

### P0 #2 — Consensus-conflict hard gate
**File:** `alpha_engine/smart_picks_engine.py:~1147` (new insert)
**Fix:** Load `dashboard_data.conflicts` and hard-reject picks whose direction opposes `recommended_direction` when `confidence_delta > 0.25 AND is_real_conflict=true`.
**Impact:** Would have killed AVAX-S (score=0) and DOGE-S (score=10) before they shipped to portfolios.

### P1 #3 — Cross-portfolio concentration cap
**File:** `alpha_engine/smart_picks_engine.py:1169-1180` (extend dedup)
**Fix:** After dedup, track `symbol_exposure_count` across sibling paper books. Flag symbols already in ≥2 portfolios.
**Impact:** Prevents the "ALGO in 3 portfolios all losing" scenario.

### P1 #4 — Strategy-WR Bayesian prior
**File:** `alpha_engine/smart_picks_engine.py:1163-1165` (primary sort)
**Fix:** Strategies with <30 historical trades get `ml_composite` shrunk toward 0 (Bayesian prior).
**Impact:** Demotes `enhanced_ml_A_xgboost` (50% WR on ALGO) and `contrarian_consensus_flip` (untrained on pair).

### P1 #5 — Audit problematic strategies
**File:** `alpha_engine/smart_picks_engine.py:85` (BANNED_SYSTEMS)
**Fix:** Run global WR check on `enhanced_ml_A_xgboost` + `contrarian_consensus_flip`. If WR<52% or PF<1.1 add to BANNED_SYSTEMS.

### P2 #6 — Recalibrate confidence buckets
**Fix:** Rebuild WR-by-0.01-conf-bucket lookup from 2026-01-01 to present. Current "0.75-0.79 = 87% WR" claim in skill doc may be stale.

### Policy #7 — Position-size caps in skill doc
**File:** `.claude/skills/tv-paper-trade/SKILL.md:159-189`
**Fix:** Add "Max 10% equity per symbol, max 20% per direction-side, max 2 portfolios holding the same symbol-direction."

---

## Backtest recommendations

1. **Single-strategy vs consensus** — split last 90d picks by `len(agreeing_systems)`. Hypothesis: single-strategy picks underperform by ≥50bps/trade with 10pp lower WR. If true → hard-require ≥2 agreeing_systems for score ≥50.
2. **Consensus-opposition replay** — every pick where conflicts flagged opposition with `confidence_delta > 0.25`. Calibrate fix #2 threshold.
3. **enhanced_ml_A_xgboost global audit** — all symbols last 60d. Candidate for BANNED_SYSTEMS.
4. **Confidence-bucket recalibration** — dashboard WR by 0.01 buckets 2026-01-01 to present.
5. **Concentration simulation** — "same symbol in N portfolios" → cumulative PnL correlation.

---

## Bus tasks filed (6)

All pushed to `bus:tasks:pending` with priorities P0-P2. See `agent_bus.py log` for broadcast.

Assignee: `claude-opus-scoring` (has scoring pipeline context, confirmed willing earlier in bus thread).
