# Asset-Class Rescue — State + Next Leverage (2026-05-03 05:10Z)

Single-page status of where each asset class stands toward CLAUDE.md Goal #1 (Tier-2 PF>1.5 / WR>50 / MDD<20 across ALL classes).

For diagnostic protocol see `CLAUDE_DEBUGGING_GUIDE.MD` (already on main — do NOT duplicate).

## Live state (asset_class_health 2026-05-03T00:06Z, post-resolver-v2)

| Class | PF | WR | n | PnL% | Tier verdict | Trend |
|---|---:|---:|---:|---:|---|---|
| EQUITY | 1.41 | 52.7% | 421 | +268 | T2 candidate | scale |
| COMMODITY | 1.78 | 46.9% | 750 | +167 | meets T2 PF | lift WR |
| BOND | 1.72 | 55.6% | 18 | +3 | T2 thresholds met | n→100 |
| ETF | 1.24 | 55.2% | 87 | +24 | T3-borderline | n→100 |
| CRYPTO | 1.25 | 44.6% | 8067 | +2084 | sub-T2 | drag-cut |
| FOREX | 0.27 | 46.4% | 1169 | -986 | sub-floor | rescue active |

## Today's shipped fixes (PR# / commit / live impact)

| PR | Fix | Status | Class impact |
|---|---|---|---|
| #717 | Drop `_scoreBreakdown` duplicate (-4.4 MB) | MERGED | mobile load |
| #718 | Apache gzip via `.htaccess` (-80% wire) | MERGED | mobile load |
| Phase 1 (e079f98) | Score floors lowered FOREX 55→40, COMMODITY 60→40, BOND 60→35, FUTURES 65→45, ETF 60→40 | MERGED | unblocks all non-crypto |
| Phase 2 (5a126e8 4a0a1c2) | etf_scanner.py + bond_scanner.py emitter pipelines | MERGED | n-growth ETF + BOND |
| Phase 3 (cd9bc85) | STRATEGY_SCORE_OVERRIDES (16 proven non-crypto strategies, floors 28-35) | MERGED | per-strategy floor unlock |
| Phase 3 (06a41a8) | non_crypto_boosters (session-aware FX, COT commodity, momentum ETF, yield curve BOND, equity sector) | MERGED | +0..+15 boost non-crypto |
| Phase 3 (673f998) | Universal data validator | MERGED | direction normalization |
| 5a4c852 | Unblock 10 non-crypto strats + ban `cta_commodity_momentum_term` (PF 0.02) | MERGED | 6 BOND + 4 FOREX strats now emit |
| 9c7c0f3 | BOND/ETF elite_grade D/F exemption | MERGED | TLT/IEF/LQD passes gate |
| **#727** | **WIRE-UP**: get_effective_min_score → passes_smart_gate; compute_non_crypto_boost → compute_elite_score | **MERGED** | closes Phase-3 orphan gap |
| **#729** | JPY-aware corruption-filter divergence threshold (opt-in) | MERGED | FOREX measurement A/B |
| **#730** | Per-class MAX_HOLD_HOURS (FOREX 120h, BOND 336h, etc.) + ETF/BOND workflow activation | MERGED | unblocks FOREX/BOND TIME_EXIT bias + cron schedule |
| **#731** | Cherry-pick 58 pytest tests + design doc | MERGED | regression coverage |

Pre-condition for next CI cycle: **user must add `FRED_API_KEY` to GH Actions secrets** before next 14:00 UTC bond_scanner cron.

## Highest-leverage UNSHIPPED items (ranked)

Per cavecrew-investigator scan of all flagship .md docs:

1. **Pip-as-percent feeder normalization** — REAL FOREX rescue lever. Fix at `outcome_resolver.py` / `copy_trader` ingestion layer (not the corruption filter). Could move FOREX PF 0.27 → 1.0+ if pipe-vs-percent confusion is the root.

2. **5 new FOREX strategies in shadow mode** — `forex_cb_event_fade`, `forex_momentum_majors` (USDCAD/USDCHF only no JPY), `forex_dxy_regime_counter`, `forex_tokyo_open_breakout`, `forex_risk_parity_overlay`. Documented in `reports/forex_new_strategies_2026_05_03.md`. No code shipped yet. Behind `FOREX_NEW_STRATEGIES_ENABLED` flag.

3. **Transaction cost model** — proposed in PEER_BROADCAST + Phase 4. ~0.03-0.05% per-class slippage. Would unmask true COMMODITY/BOND profitability.

4. **R:R ceiling (max 2.0)** — prevents asymmetric-risk catastrophic losers. Smart-gate one-liner.

5. **BOND position cap** — reviewer flagged on PR #730: 336h hold without per-class notional cap means stuck BOND pick costs opportunity for 14 days. Add to `portfolio_manager.py`.

6. **RAPID_FIRE_MAX_HOLD_HOURS unification** — extract shared constant module so `outcome_resolver.py:152` (24h) and `universal_pick_resolver.py` per-class map share source of truth.

7. **CRYPTO drag fix** — `alpha_engine` 29.5% volume @ PF 0.81 + `baby_strats_forward` 15.5% @ PF 1.03 dragging system-wide. Mutate-before-kill per CLAUDE.md. Cap volume share to 10% as shadow experiment.

8. **EQUITY size-up** — already T2 candidate (PF 1.41). Charter says "size up" — needs portfolio sizer config change.

## Asset-class outlook 30-day

| Class | Action | Predicted T2 ETA |
|---|---|---|
| EQUITY | Size-up Phase | already meets, ship sizer config |
| COMMODITY | Lift WR via regime-gate (item 3+regime sizing) | 14d if WR moves 47→50 |
| BOND | n-growth via cron + new universe (TLT/IEF/SHY/LQD/HYG) | 30d to n=100 |
| ETF | n-growth via cron | 14d to n=120 |
| CRYPTO | Drag-cut via volume cap on alpha_engine + baby_strats_forward | 30d to PF 1.4 |
| FOREX | Pip normalization + 5 new strats shadow | 60d to PF 1.0+; 90d to T3 |

## Acceptance criteria recap (Goal #1 charter)

- T1 Renaissance: PF>2 / WR>55 / MDD<10
- T2 Institutional: PF>1.5 / WR>50 / MDD<20 (sizing floor)
- T3 Retail-OK: PF>1.2 / WR>48 / MDD<30

No class clears all 3 T2 legs yet. EQUITY closest. BOND meets (n<100 charter floor blocks).

## Hourly cron monitor

`trig_0119HU5VfusFrJF5bw5x9HYA` fires :10 each hour — auto-triages new PRs + writes per-asset health delta to `reports/hourly_progress/`.

## Methodology

Per `CLAUDE_DEBUGGING_GUIDE.MD` (already on main):
1. Define failure thresholds → 2. Verify data integrity → 3. Segment failure → 4. Leakage audit → 5. Model vs execution → 6. Ablation/mutation → 7. Kill vs mutate governance → 8. Guardrails → 9. Forward proof → 10. Document.

Repo's existing playbook is the canonical version — agents writing duplicate playbooks add noise, not leverage. This doc reports STATE, not protocol.
