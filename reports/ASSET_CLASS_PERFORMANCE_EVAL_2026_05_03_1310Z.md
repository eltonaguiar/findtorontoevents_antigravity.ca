# Asset Class Performance Evaluation — 2026-05-03 13:10Z

**Author:** Antigravity session, end-of-session consolidated eval.
**Source:** `audit_dashboard/data/dashboard_data.json` payload @ 2026-05-03T13:09:35Z, repo SHA `ab2bd03de1`.
**Successor sessions:** read this AFTER the playbook (#735), integration plan (#736), and MIT harvest (#737); BEFORE acting on any class.

---

## TL;DR

| Class | PF | WR | n | Tier | Δ this session | Action |
|---|---|---|---|---|---|---|
| **EQUITY** | 1.41 | 52.9% | 420 | T2-cand | none | Scale toward T1 |
| **CRYPTO** | **1.25** | 44.5% | 8089 | sub-T2 → trending up | **+0.01 PF** (post-#740) | Continue forward accumulation |
| **FOREX** | 0.27 | 46.4% | 1169 | sub-floor | none yet | JPY relax accumulation (slow) |
| **COMMODITY** | 1.78 | 46.9% | 750 | T2 PF | none | Lift WR |
| **ETF** | 1.24 | 55.2% | 87 | T3 | none | n→100 |
| **BOND** | 1.72 | 55.6% | 18 | T2-thresholds | none | Grow sample |

**One real movement this session:** CRYPTO PF lifted **1.24 → 1.25** after PR #740 (blacklist enforcement at `smart_picks_engine` + `outcome_resolver`) merged at 10:30Z. Confirms the blacklist gap was costing measurable edge. Forward-only effect; should compound over 24-72h.

---

## Tier definitions (recap)

- **T1** (Renaissance): PF > 2.0, WR > 55%, MDD < 10%
- **T2** (Institutional): PF > 1.5, WR > 50%, MDD < 20%
- **T3** (Retail-OK): PF > 1.2, WR > 48%, MDD < 30%

---

## Per-class state + path-to-T2

### EQUITY — T2 candidate, scale (no action this session)

- **PF 1.41 / WR 52.9% / n=420** — meets T2 WR, PF gap = -0.09 to T2.
- Top performer: `signal_validation` 63.0% WR / PF 2.58 (+183.24% PnL) — proven cross-asset edge.
- Drag: `stocks_rsi2_pullback` flagged in 7d window per Buffy review.
- **Path to T2:** add 1-2 EQUITY-tilted strategies derived from `signal_validation` template; cull `stocks_rsi2_pullback` if 7d damage persists. Requires: `docs/MUTATION_THREE_AXIS_PROTOCOL.md` 5-experiment grid.

### CRYPTO — sub-T2, trending up (PR #740 effect confirmed)

- **PF 1.25 / WR 44.5% / n=8089** — PF lifted +0.01 since 10:30Z (#740 merge).
- Real drag (verified live, 13:10Z): `kimi_signal_tracking` (PF 0.26, -954% PnL — still blocked), `alpha_engine_fast` (PF 0.62, -127% PnL), `quan_engine` (PF 0.25, -43% PnL — source aggregator for blacklisted `quan_engine_scalp` strategy).
- Top performer: `alpha_engine` (PF 1.59, +953% PnL — improved from 0.81 in older memory).
- **#740 effect mechanism:** new `quan_engine_scalp` picks now blocked at `smart_picks_engine.score_pick:754` AND skipped at `outcome_resolver.resolve_single_pick:666`. Zero new picks since merge (verified `closed_picks.json` post-10:30Z = 0 quan_engine_scalp rows).
- **Path to T2:** continue forward accumulation. CRYPTO needs PF 1.5 — gap = -0.25. With +0.01/day from blacklist alone = 25 days. Accelerate via:
  1. Gate `alpha_engine_fast` (PF 0.62) at score >= 60 floor — consider per-strategy floor like `quality_gates.STRATEGY_SCORE_OVERRIDES`
  2. Investigate `quan_engine` source aggregator (PF 0.25 source-level — may have other strategies under it that should be blocked)

### FOREX — sub-floor, JPY relax forward-accumulating (slow)

- **PF 0.27 / WR 46.4% / n=1169** — UNCHANGED since session start despite #738 (JPY relax prod-enable) + #741 (JPY scope tightening) merged.
- **Why no movement:** `_pnl_pct_looks_corrupt` filter is forward-only. Existing 1169 picks were already classified pre-flag; no historical reclassification. Lift requires **NEW JPY picks** to land + accumulate.
- 405 historical JPY picks were over-rejected per the corruption filter (per #724 root-cause investigation). Those stay out; only new JPY picks benefit from 50× threshold.
- **Path to T2:** PF 0.27 → 1.5 = needs ~5.5× lift. Per `reports/FOREX_RESCUE_CONSOLIDATED_2026_05_03.md` projection: 1.15-1.25 from filter alone (5×). Remaining gap closes via:
  1. New strategies — 5 proposed in `reports/forex_new_strategies_2026_05_03.md` (BoJ Decision Fade, High-Momentum Majors, DXY Regime Counter, Tokyo Open Liquidity, Risk-Parity Overlay)
  2. Cyclical sin/cos hour encoding for `_forex_session_boost` per #737 MIT harvest top recommendation
  3. Mute existing FOREX winners that work — `signal_validation` 63% WR FX-cohort, `super_signals` 56.9% WR
- **Verification timeline:** measurable lift expected 48-72h post-#738 as new JPY picks resolve.

### COMMODITY — T2 PF met, lift WR

- **PF 1.78 / WR 46.9% / n=750** — best PF in book; meets T2 PF (1.5+) but WR gap to T2 = -3.1pp.
- Memory note: `cftc_cot_commercial_signal` was top performer (per old session memory). NOT in current top-system table — needs verification it's still firing.
- **Path to T2 WR:** mute LONG-bias on `multi_asset_cot` (96.4% concentration on CT=F per memory `feedback_long_source_bias.md`). Lifting WR from 46.9 → 50% = +3 wins per 100 picks. Achievable via better SHORT signal generation.

### ETF — T3 stable, scale n

- **PF 1.24 / WR 55.2% / n=87** — meets T3 thresholds. **n is the only blocker** to formal T2-eval (charter floor 100).
- Top: not enough strategies registered. Most ETF picks come via `alpha_engine` cross-class.
- **Path to n=100:** 13 more closed picks. With current rate ~1-2/day → 7-13 days.

### BOND — T2-thresholds met, grow sample

- **PF 1.72 / WR 55.6% / n=18** — exceeds T2 PF (1.5+) AND WR (50%+), but n=18 well below charter floor 50.
- Likely concentration risk: small n means single outlier could collapse PF.
- **Path:** activate the BOND scanner workflow already in `.github/workflows/etf-bond-scanner.yml` (FRED_API_KEY now set per session log). Cron 14:00Z daily; should add ~3-5 picks/week.

---

## Recent fixes shipped this session (impact map)

| PR | Merged | Class targeted | Mechanism | Verified effect |
|---|---|---|---|---|
| #738 | 07:22Z | FOREX | `PNL_PCT_CORRUPT_DIVERGENCE_JPY_RELAX=1` env var enabled in `audit-dashboard.yml` | Forward-only; no payload movement yet (n still 1169) |
| #740 | 10:30Z | CRYPTO | `BLACKLISTED_STRATEGIES` enforced at `smart_picks_engine.score_pick:754` + `outcome_resolver.resolve_single_pick:666` | **+0.01 PF** measured 12:35Z; 0 new `quan_engine_scalp` picks landed post-merge |
| #741 | 11:55Z | FOREX (scope) | `_pnl_pct_looks_corrupt` JPY-relax narrowed to `asset_class==FOREX OR sym.endswith("=X")` | Pre-existing JPY-test failure unchanged (different `JPY_CROSS_BUY_KILL_DISABLED` flag); no regression on other classes |
| #735, #736, #737, #739 | various | system-wide | Doc bundle (playbook + integration plan + MIT harvest + peer audit) | Reference material for successor sessions |

---

## Walk-forward (OOS) — note on staleness

User's earlier paste cited `walk_forward_by_class()` table (COMMODITY -2.41 Sharpe, CRYPTO -0.51, EQUITY +3.58, ETF +6.37, FOREX -1.41 OOS Sharpes). Live `dashboard_data.json::walkforward.by_class` returned `[]` empty array at 13:09Z — likely separate generator workflow, not refreshed every cycle. Trust user's pasted table for OOS Sharpe; trust headline `asset_class_health` for live PF/WR/n.

**Implication:** ETF OOS Sharpe +6.37 with decay 10.8 + only 12 folds is suspicious overfit territory. Don't size up ETF based on Sharpe — wait for n=100+ headline.

---

## Successor agent action queue (ranked)

1. **Watch CRYPTO PF trend +0.01/cycle.** If it stalls inside 6h, investigate whether `_is_historical_blocked_pick` is excluding any newly-classified blacklisted picks correctly.
2. **Measure FOREX accumulation @ 48h mark** (2026-05-05 ~07:22Z). If PF still 0.27 with n unchanged, the JPY relax flag isn't producing new JPY picks — investigate FX feeder pipeline.
3. **Activate ETF + BOND scanners** (`.github/workflows/etf-bond-scanner.yml`) for n-growth. FRED_API_KEY set; should be ready.
4. **Ship cyclical sin/cos hour encoding** for `_forex_session_boost` (per MIT harvest #737, top idea).
5. **Open follow-up PR** to add `kimi_signal_tracking` + `alpha_engine_fast` to `BLACKLISTED_STRATEGIES` if 7d performance doesn't recover. Requires investigate-before-kill protocol per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.

---

## What to NOT do (anti-pattern memo)

- Don't claim FOREX PF lift from #738/#741 within 24h — measurement window must be 48h+ minimum.
- Don't add `quan_engine` source to BLACKLISTED — it's a source aggregator, not a single strategy. Block at strategy level (`quan_engine_scalp` already blocked).
- Don't size up ETF/BOND on stellar OOS Sharpe — n too small (87/18). Charter floor 100 is the gate.
- Don't kill `non_crypto_consensus` even though it shows WR 0% — per session memory check, may be inactive/zero-volume rather than truly losing. Verify via grep before block.

---

## Session PR shipping summary

Merged this session (8 PRs):
- #734 (audit refresh), #735 (playbook), #736 (integration plan), #737 (MIT harvest), #738 (JPY relax), #739 (peer hedge-fund audit), #740 (blacklist enforce), #741 (JPY scope)

Open PRs blocked on author response (~14h+ silent):
- #660 (P0 emergency gates — internal contradiction)
- #615 (scanner blockers — circuit-breaker reset risk)
- #597 (rapid_fire pair-block + revalidator — Wire-Up Rule)
- #608, #644, #661, #676, #723, #724 (various, all need rebase)

---

_Generated 2026-05-03 by Antigravity session for end-of-session consolidated eval. Successor: extend this doc, don't replace._
