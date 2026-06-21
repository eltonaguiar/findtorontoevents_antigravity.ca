# FRM / CFA Concepts → Can They Improve Our Predictions? (2026-06-20)
**Author:** claude-opus · **Method:** FRM repo-grep + CFA subagent + 3-model peer swarm (:4000) + 5-lane grounded concept-audit workflow · **Companion:** `reports/DEEP_DIVE_FLEET_SYNTHESIS_2026-06-19.md`, `reports/MONEY_READY_NEXT_STEPS_BUILD_PLAN_2026-06-19.md`

## The honest headline
The user's FRM/CFA framework (GARCH vol-TP/SL, CPCV, DSR/PSR, ES/CVaR, HRP, cointegration, vol-targeting, multiple-testing) is **directionally correct — and we already implement ~70% of it.** Repo-grep confirms in-tree: cluster-bootstrap PF CI-LB (`pf_ci_lower.py`), Deflated Sharpe + PBO (`deflated_sharpe.py`, `pbo.py`), White's reality check (`whites_reality_check.py`), CPCV (`build_cpcv_pbo_results.py`), GARCH (`garch_volatility.py`, **wired** into `forward_validator.py`), CVaR/MDD gate (`money_ready_verdict.py`), Kelly (wired in `production_scanner.py`), HRP/risk-parity (`hrp_allocator.py`, `risk_parity_allocator.py`), cointegration stat-arb (`crypto_pairs_arb.py`), factor model (`equity_factor_model.py`, wired), residualization, accruals, Piotroski/Beneish/Altman (UEPS).

**So the framework doesn't hand us a missing idea. The real gaps are three:**
1. **Wiring** — our strongest statistical-rigor tools (Deflated Sharpe, White's/SPA, factor attribution) are **ORPHANED**, not called by the live promotion gate (`verified_promotion_gate.py`).
2. **Integrity** — the multiple-testing machinery that IS reachable (`fdr_control.py`, `build_cpcv_pbo_results.py`) is fed the **BANNED daily-resolved PnL**, which inflates PF ~2-3×.
3. **One genuine new edge avenue** — cointegration pairs (`crypto_pairs_arb.py`) is wired into the registry but has **0 closed trades** — effectively untested.

**The reframing that matters:** with **0/10 classes promotable**, risk/portfolio concepts (HRP, vol-targeting, MPT, marginal-VaR, ES sizing) are **PREMATURE** — they improve the risk-adjusted return of edge that doesn't exist yet. The only FRM/CFA items that touch *prediction* right now are the ones that **find edge** or **validly reject false positives**.

## Grounded per-concept verdict
Cross-confirmed by the 3-model peer swarm and the grounded workflow (verbatim file evidence in each lane).

| Concept | Repo status | Prediction value | Premature? | Verdict |
|---|---|---|---|---|
| **Cointegration pairs** | `crypto_pairs_arb.py` (Engle-Granger, `_ols_hedge_ratio`/`_half_life`) — WIRED to registry, **0 closed trades** | **FINDS NEW EDGE** (market-neutral, orthogonal to stuck directional signals) | **No** | **#1 — run the honest backtest (in progress)** |
| **CPCV / purged CV** | `build_cpcv_pbo_results.py` — **already WIRED + already FAILING** (PBO 0.82 "overfit", 2026-06-10) | Only rejects false-pos; makes CI-LB *more* conservative → pushes leads further below 1.15 | Yes (for edge) | Don't build — **fix its data source** (reads banned daily PnL) |
| **ES / CVaR tail** | `money_ready_verdict.py` `_mdd_cvar_gate` (loss-tail) WIRED + enforced | Missing piece = **max-single-WIN-share gate** (would've killed myfxbook PF 3.79) | Yes | Add the cheap WIN-share gate (false-pos only) |
| **GARCH vol-TP/SL** | `garch_volatility.py` → `forward_validator.py:3436-3437` WIRED but **SYMMETRIC** | Can flip TP/SL hits — but H-130 failed on *drift*, not band width | No | Cheap sensitivity test; real lever is a **trend/drift gate** |
| **Multiple-testing (FDR/White's/DSR/PBO)** | all EXIST; DSR/White's **ORPHANED**; FDR reads daily PnL | Rejects false-pos (hardens the bar) | Partly | Wire honest-PnL versions into `verified_promotion_gate` |
| **HRP / risk-parity / vol-target / marginal-VaR** | `hrp_allocator.py` orphan; vol-target opt-in OFF; Kelly wired | Pure sizing/allocation | **Yes (unanimous)** | **Defer until ≥1 class promotable** |
| Factor models / attribution | `equity_factor_model.py` wired; `factor_attribution.py` orphan | Diagnose beta-vs-alpha on EQUITY reversal lead | No | Attribution-vet the leads (could change a verdict) |
| Bond term-structure / credit-spread | hypotheses pre-registered, no live picks | Real macro predictor for the cold BOND class | No (but slow forward-n) | Promote one bond curve/credit hypothesis to forward-shadow |
| Accruals (Sloan), behavioral priors | `short_side_screener.py`, `flow_behavioral_strategies.py` — orphan/opt-in | Weak/decayed equity tilt; behavioral = economic prior | No | Low priority |
| DCF / RIM / Black-Litterman / duration / GIPS / ethics | RIM + BL ABSENT; rest valuation/risk | None for prediction | — | Skip |

## Prioritized next steps (by leverage to a PROMOTABLE edge)
1. **Cointegration pairs honest backtest** — the only edge-opener. Pre-registered (M-107); running. *(this turn)*
2. **Integrity: feed honest net-first-touch PnL to `build_cpcv_pbo_results.py` + `fdr_control.py`** (they read banned daily-resolved `pnl_pct`). Cheap, fixes a real leak in the overfit/multiple-testing wall.
3. **Max-single-WIN-share gate** (`top_5_wins_share>0.70 → NOT_READY`) in `money_ready_verdict.py` — shadow-first; auto-rejects fat-tail false positives.
4. **Wire orphaned Deflated-Sharpe + White's/SPA into `verified_promotion_gate`** — hardens the bar with tools we already own.
5. **GARCH asymmetric-band sensitivity test** on the `crypto_rsi5070_us` cohort — cheap; expectation: confirms the real lever is a trend gate, not band width.
6. **Attribution-vet the two leads** (beta vs idiosyncratic alpha) — could promote a residualized variant or correctly kill a beta mirage.
- **DEFER (premature, unanimous):** HRP / risk-parity / vol-targeting / MPT / marginal-VaR — nothing to allocate at 0/10.

## The three offered buttons — straight answers
- **"Implement CPCV"** → It's **already implemented and already failing** (PBO 0.82). Implementing more won't help; it can only push the sub-bar leads *further* below 1.15. The valuable version is fixing it to run on honest (not daily-resolved) PnL. **Do the integrity fix, not a new build.**
- **"Explore HRP allocation"** → **Premature.** HRP allocates capital across *edges that pass the bar*; we have zero. Revisit once ≥1 class is promotable; then feed HRP's correlation step into the concentration gate, not capital sizing.
- **"GARCH-based TP/SL pseudocode"** → Provided below — with the caveat the swarm + our own memory flag: naive vol-scaled SL on 181 days is a **curve-fitting trap** (it can inflate PF like the banned daily metric). Use it only as a *sensitivity test* on an already-honest cohort, never as a promotion input.

```text
# GARCH asymmetric-band SENSITIVITY TEST (not a promotion input)
for each pick in honest_cohort:                     # e.g. crypto_rsi5070_us closed picks
    sigma = get_garch_forecast(trailing_closes)     # alpha_engine/garch_volatility.py
    SL = entry - k_sl * sigma                        # k_sl ~ 1.5  (TIGHTER)
    TP = entry + k_tp * sigma                        # k_tp ~ 3.0  (WIDER, k_tp > k_sl)
    outcome = replay_first_touch(entry, TP, SL, bars)  # tools/reresolve_intrabar.py replay() — SL-wins-ties, NO winsorize
compare net@cost PF / CI-LB / (TP_HIT vs SL_HIT) head-to-head vs the fixed-band baseline
# If trueWR & net-PF do NOT both rise -> the failure is DIRECTIONAL DRIFT, not band geometry
#   -> the real fix is a trend/drift filter, not SL width. (This was exactly H-130's failure mode.)
```

## Bottom line
FRM/CFA give us **rigor, not alpha** — and we already have most of the rigor (often more advanced than the curricula). The single highest-value FRM/CFA-inspired move is the one already running: **cointegration pairs**, because it can *open* edge rather than just better-reject false positives. Everything else is either already wired (fix its honesty), a cheap false-positive gate, or premature sizing to revisit after a class passes.
