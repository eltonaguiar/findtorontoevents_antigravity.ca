# Elite Score Recalibration for Non-Crypto — Plan

**Date:** 2026-04-17  **Step:** 2 of non-crypto supply pipeline investigation
**Parent:** `updates/2026-04-17-non-crypto-supply-pipeline-investigation.md` §5 item #2
**Owner:** alpha_engine  **Risk profile:** MED (pipeline-widening, reversible via env flag)

Synthetic ETF/Bond/Commodity picks with `conf=0.65, rr=2.0` score 12/12/23 in `compute_elite_score` vs 38 for a BTCUSDT pick — a 3×+ gap driven almost entirely by crypto-calibrated components that go to zero (or negative) for non-crypto classes. Result: agents emit `quality=0` every run, the 50-floor never lets anything through, and the feed is chicken-and-egg starved.

---

## 1. Diagnosis — component-by-component audit of `alpha_engine/elite_scorer.py`

Read end-to-end (lines 1568–3061). Each component's range and asset-class behavior:

| # | Component | Range | Crypto-biased? | Evidence |
|---|---|---|---|---|
| 1 | `ml_score` (1666-1691) | 0 → +25 | **YES (structural)** | ML models exist only for crypto (`ml_enhanced_FETUSDT` etc., `ML_PROVEN_STRATEGIES` @ 227-235 — 6/7 are USDT). Non-crypto picks have no `ml_score` field → 0. |
| 1b | `confidence_score` (1695-1711) | 0 → +20 | NEUTRAL | Pure conf band 0.60–0.85. |
| 2 | `forward_wr + track_record` (1718-1888) | −5 → +40 | **YES (data-gated)** | Dominant single component. Requires `forward_wr` and `forward_trades` or `strategy_performance.json` entry. Non-crypto strategies were registered recently → zero entries → baseline 5 pts only. |
| 2b | `source_system` (1894) | 0 | zeroed | Safe. |
| 3 | `confluence` (1906-1923) | −20 → 0 | **YES** | Crypto gets 10+ source systems per symbol; non-crypto gets 1–2. Non-crypto never triggers −20 (good) but also never gets the historical +5 it once offered. Neutral today. |
| 3b | `kol_consensus` (1935-1966) | 0 → +15 | **YES** | `predictions/data/kol_consensus_picks.json` is crypto-only. Non-crypto always 0. |
| 3c | `regime_bonus` (1989-2105) | 0 → +20 | **PARTIALLY FIXED** | Non-crypto already hard-coded to `10` (line 2040). OK but below crypto's peak 20. |
| 4 | `risk_reward` (2128) | 0 | zeroed | Safe (IC=-0.127 on crypto; may be +ve for non-crypto — see Option B). |
| 4b | `symbol_edge` (2141-2154) | 0 → +5 | **YES** | Hard-coded to 9 crypto tickers (FETUSDT, RENDERUSDT, …). Non-crypto always 0. |
| 4b2 | `market_cap_tier` (2162, via 142-161) | −5 → +10 | **FIXED** | Non-crypto category returns 0 (line 152). OK. |
| 4c | `expectancy` (2173-2195) | −5 → +8 | **YES (data-gated)** | Requires `strategy_performance.json` with 10+ closed picks. Non-crypto strategies don't have that yet. |
| 4c1b | `source_direction_adj` (2204-2238) | −14 → +5 | NEUTRAL | Penalties target crypto sources (alpha_engine, ml_crypto_pred, quan_engine). Non-crypto always 0. |
| 4c2 | `volatility_predictability` (2266-2278, via 164-219) | −10 → +10 | **FIXED (well)** | Per-class thresholds (forex/equity/etf branches). OK. |
| 4d | `strategy_momentum` (2284-2294) | −2 → +3 | data-gated | Needs `last_outcome` in strategy_perf. Non-crypto: 0. |
| 4e | `time_of_day` (2302-2310) | −2 → +3 | **YES** | Hour table calibrated on crypto 24/7 UTC. FX has sessions; equities 14:30-21:00 only. Asymmetric. |
| 6 | `volume` (2336-2350) | −8 → +5 | class-agnostic formula, but `volume_ratio` is **rarely populated** for non-crypto picks → 0. |
| 7 | `signal_quality` (2355-2391) | −5 → +10 | class-agnostic but **data-gated** — needs `pattern_predicted_wr`, `entry_zone_score`, `net_edge_bps`. Non-crypto enrichers don't write these. 0. |
| 11 | `risk_warning_penalty` (2493-2501) | −3 or 0 | crypto-only lookup (from `CRYPTO_SYMBOLS` config). Non-crypto 0. |
| 12 | `technical_alignment` (2515-2541) | −30 → +5 | data-gated (`technical_alignment`, `technical_buy_tfs`). Non-crypto: 0 (absent). |
| 12b | low-sample cap @ 75 (2548-2550) | cap | **YES** | Kills anything with `<15` closed trades. Every non-crypto strategy fails this. |
| 12c | `technical_confirmation` (2560-2562, via 296+) | −5 → +9 | data-gated on crypto indicator PP table. Non-crypto 0. |
| 12b2 | `btc_lead_causal` (2573-2582) | −5 → +3 | **YES** | BTC Granger-causality — meaningless for TLT or GC=F. 0. |
| post | `quan_engine_tier_boost` (2643-2645) | +45 | **YES** | Source `quan_engine` is crypto only. |
| post | `proven_symbol_{TAO,HYPE,TRX}` (2648-2656) | +15 each | **YES** | 3 crypto tickers. |
| post | overconfidence cap @ 60 if `_strat_closed<10` (2678-2681) | cap | **YES** | Every new non-crypto strategy hits this. |
| post | super-signal cap @ 52 (2689-2702) | cap | mostly-crypto (strategy naming). |
| post | `equity_macro_cap` @ 60 (2728-2740) | cap | NEUTRAL for non-crypto equity (intentional). |
| normalize | divisor 90 (line 2638) | /90 × 100 | **YES** | Theoretical max derived from the crypto-rich component set. Non-crypto's achievable max is ~35 pre-normalize → ~39/100 post. |

**Summary:** 13 components are crypto-biased (structurally or data-gated), totalling ~93 of the ~118 achievable pre-normalize pts. Non-crypto picks realistically access only ~35–40 pre-normalize pts (conf 20 + regime 10 + vol_predict 10 + confluence 0 + baseline fwd 5). After /90 normalization → ~39-44. Below the 50 floor. **Confirmed root cause.**

---

## 2. Measurement — one-shot diagnostic

**Path:** `tools/elite_score_class_distribution.py`

**Inputs:**
- `audit_trail/data/closed_picks.json` (ledger, ~3,500 rows)
- `audit_dashboard/data/dashboard_data.json` → `active_raw` (pre-gate, ~189 picks)
- `strategy_performance.json` (for recompute)

**Logic:**
1. For each pick in closed + active_raw, recompute `elite_score` via `compute_elite_score(pick)` (fresh, not trusting stored).
2. Group by `asset_class` (normalize: `crypto`, `equity`, `forex`, `commodity`, `etf`, `bond`, `futures`).
3. Report per class: `n, mean, median, p25, p50, p75, p90, pct_ge_50, pct_ge_40, pct_ge_55`.
4. **Gate attribution** (closed picks only, filter `outcome == "won"`): of would-be-winners per class, what fraction was killed by:
   - `elite_score < floor` (50 for most, 55 for equities)
   - `confidence < 0.50` (or 0.55 equities)
   - `risk_reward < floor` (1.00 forex → 1.20 etf)
   - combinations (Venn).
5. Output: stdout table + `tools/out/elite_score_class_distribution_{date}.json`.

**Expected finding** (hypothesis): >70% of winning non-crypto picks gated by score, <10% by RR, <20% by confidence. Confirms score floor is the dominant gate.

---

## 3. Fix — two options

### Option A (RECOMMENDED — ship first) — Asset-class-specific floors

Lower the per-class floor in each agent YAML to match that class's `p50` of closed-pick elite scores:

| Class | Today | Proposed | Rationale |
|---|---|---|---|
| CRYPTO | 50 (implicit) | 50 | unchanged |
| EQUITY | 55 | 50 | small reduction, high-volume class |
| COMMODITY | 50 | **40** | only profitable non-crypto (55.6% WR / PF 1.06) — de-risk first |
| ETF | 50 | **42** | 42.6% WR, 61 closed — moderate |
| BOND | 50 | **42** | 47.1% WR, 17 closed — small n, risk-managed by low symbol count |
| FOREX | 50 | **45** | 27.6% WR — widening feed not urgent, but −5 is modest |
| FUTURES | 50 | 45 | |

Keep `confidence >= 0.50` and per-class `risk_reward` floors **unchanged** (§2 validates they're not the blocker).

**Pros:** surgical, ~10 lines edited, reverses in one revert, doesn't touch scorer logic or crypto picks.
**Cons:** doesn't fix the structural bias; crypto-biased bonuses still distort relative rankings across classes.

### Option B (DEFERRED — "consider later" gate)

Rewrite `compute_elite_score` to branch on `asset_class`:
- `crypto`: existing formula.
- non-crypto: asset-class-neutral scorer using only: `confidence` (25), `regime_bonus` (10, already fixed), `volatility_predictability` (10, already per-class), `rr_quality` (15 — un-zero R:R for non-crypto; the −0.127 IC was measured on crypto), `strategy_momentum` when data available (5), `volume_ratio` when populated (5), `signal_quality` (10). Target max ~80 pre-normalize.

**Gate for Option B:** only greenlight after Option A has produced ≥30 days of non-crypto closed picks AND Option A WR-lift is insufficient (<45% WR non-crypto) AND §2 diagnostic shows the structural-bias theory persists post-floor-fix.

**Recommendation:** ship Option A this week; revisit B after 30-day non-crypto sample.

---

## 4. Validation — chronological split

**Method:** "shadow" deploy for 72h before activating. Patch writes `elite_score_v2` alongside `elite_score`, agents still gate on v1. Diagnostic computes what the v2-gated pick set would have looked like. Then flip the flag.

**Acceptance criteria (all must pass):**

1. **Non-crypto supply:** active picks/day across {COMMODITY, BOND, ETF} rise from ~1 to **≥5** within first 72h; ≥10 within 7d.
2. **Crypto non-degradation:** crypto active-pick WR on the first 200 picks post-change does not drop >3 pp vs trailing 200 pre-change (baseline ~50-55%). Kill-switch trips at −5 pp.
3. **Non-crypto quality floor:** commodity closed-pick WR stays ≥45% (current 55.6%) on ≥20 new closed picks; bonds ≥40% on ≥10.
4. **No score inversion:** top-decile WR > bottom-decile WR per class (re-run `decile_test.py` equivalent per class at 7d).
5. **No gate stacking:** confidence + RR drops <5% of picks each after score gate loosens (measured by §2 Venn).

**Rollback trigger:** criterion #2 fails, OR non-crypto 7d closed-pick PF <0.85, OR error spikes in agent logs.

---

## 5. Rollout — exact edits

**Env/config kill-switch** (add to repo-root `.env.example` and read in `elite_scorer.py` or quality_gates):
```
ELITE_SCORE_CLASS_FLOORS_ENABLED=1   # 0 = old behavior (50 floor everywhere)
```

### 5.1 File edits

| File | Line(s) | Change |
|---|---|---|
| `.github/workflows/commodities-agent.yml` | 114 | `elite_score >= 50` → `elite_score >= 40` (also read `$COMMODITY_ELITE_FLOOR` env var with fallback 40) |
| `.github/workflows/bond-agent.yml` | 101 | `elite_score >= 50` → `elite_score >= 42` |
| `.github/workflows/etf-agent.yml` | 98 | `elite_score >= 50` → `elite_score >= 42` |
| `.github/workflows/forex-agent.yml` | 99 | `elite_score >= 50` → `elite_score >= 45` |
| `.github/workflows/futures-agent.yml` | 101 | `elite_score >= 50` → `elite_score >= 45` |
| `.github/workflows/equities-agent.yml` | 103 | `elite_score >= 55` → `elite_score >= 50` |
| `alpha_engine/elite_scorer.py` | 2678-2681 | overconfidence cap (`score>85 & strat_closed<10 → 60`) — **exempt non-crypto classes** (add `and not _is_non_crypto_class`). Prevents the cap from killing every new non-crypto strategy by default. |
| `alpha_engine/elite_scorer.py` | 2548-2550 | low-sample cap at 75 — apply only to crypto (same exemption guard). |
| `audit_trail/quality_gates.py` | 224-241 | `SMART_PICKS_MIN_SCORE_*` — align with new per-class floors (COMMODITY 40, BOND 42, ETF 42, EQUITY 50, FOREX 45, FUTURES 45) so the downstream filter does not re-gate what agents emit. |
| `alpha_engine/elite_scorer.py` | NEW at ~2790 | guard `if not ELITE_SCORE_CLASS_FLOORS_ENABLED: pass` (reads `os.environ.get`, defaults to 1). Env=0 reverts cap changes. |

### 5.2 Deploy order

1. Land the two `elite_scorer.py` cap exemptions (no behavior change to crypto; loosens cap for non-crypto). Push.
2. Run §2 diagnostic against last 7d. If class medians are as predicted, proceed.
3. Land the 6 YAML edits in a single commit, single PR.
4. Monitor GHA run outputs for 24h: `commodities-agent` `quality=N` must go from 0 to >0. If not, raise floor back 5 pts.
5. 72h check against criteria §4 #1-#5. Flip `ELITE_SCORE_CLASS_FLOORS_ENABLED=0` if any fails.

---

## 6. Risk list

| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| Non-crypto active picks flood (>100/day from universe expansion + lower floors) | MED | MED | Per-class top-N cap in `quality_gates.py:3509` — add `MAX_ACTIVE_PER_CLASS = {COMMODITY:15, ETF:15, BOND:8, FOREX:20, FUTURES:10, EQUITY:20}`. |
| Crypto WR drops because low-quality picks start competing for portfolio slots | LOW | HIGH | Option A touches only **non-crypto YAML gates**, does not alter crypto scorer. Crypto floor unchanged at 50. Kill-switch env var. |
| New non-crypto picks have 20-30% WR (true quality issue, not gate issue) | MED | MED | Criterion §4 #3 auto-rollback at <45% WR. Investigation path: `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`. |
| Score-floor lowering masks real strategy failure (non-crypto strategies genuinely broken) | MED | MED | §2 Venn diagnostic must show winners being gated. If diagnostic shows losers disproportionately passing, abort Option A. |
| quality_gates.py SMART_PICKS floors out-of-sync with YAML floors | HIGH (without §5.1) | LOW | Explicitly bundled in the rollout checklist. |
| `overconfidence_cap` exemption lets a truly bad new non-crypto strategy score 90+ | LOW | MED | Criterion §4 #4 decile test per class catches this at 7d. |
| Option A never gets replaced by Option B (plan rot) | MED | LOW | Explicit 30-day review date in issue tracker; gate criteria pre-defined above. |

**Worst case:** non-crypto feed floods the dashboard with 50+ sub-40% WR picks, crypto portfolio slots get diluted → portfolio PF drops. Recovery: set `ELITE_SCORE_CLASS_FLOORS_ENABLED=0` in repo secrets (or revert one commit). ≤ 5 min rollback.

---

## Summary (for caller relay)

Root cause confirmed: 13 of ~20 scoring components are crypto-biased (structurally via lookup tables, or data-gated via crypto-only sidecar files). Non-crypto ceiling is ~40/100 post-normalize. Fix via **Option A (per-class floors 40-45)** plus two cap exemptions in `elite_scorer.py:2548-2681`. Reversible via env var. Validation at 72h/7d against 5 criteria. Option B (full scorer rewrite) deferred behind a 30-day data gate.
