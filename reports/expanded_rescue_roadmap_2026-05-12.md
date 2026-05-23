# Expanded Rescue Roadmap (Week-by-Week) — 2026-05-12

Builds on `reports/rescue_plan_per_asset_class_2026-05-12.md` with concrete
weekly tasks, owners, implementation notes, and gating success criteria.

## Week 1 — Foundations & immediate risk mitigation

| # | Task | Owner | Notes | Success criteria | Status |
|---|---|---|---|---|---|
| 1 | Data-pipeline integrity (zero-PnL, resolver sync) | data-engineer | ETL audit + checksum + dead-trade flag | <1% zero-PnL, <0.5% missing | ✓ filter shipped `dd8e8282537` |
| 2 | Dragger quarantine (kimi/crypto_soc/stale) | ML-Ops | quarantine table + orchestrator skip | 0 trades from quarantined in 48h | ✓ multi-commit (`597819d79c7`, `5c7a8c43a27`) |
| 3 | ML-staleness hard-fail watchdog | ML-engineer | drift via KL divergence; auto-disable >0.07 | All models pass drift ≥24h | ✓ mtime gate shipped `db5bcfa0f04` |
| 4 | Gate enforcement (PBO/DSR/CPCV) in CI | quant-dev | Fail build if any gate violated | No prod model w/o passing gates | PARTIAL — DSR cron-wired; PBO/CPCV orphan |
| 5 | Entry-point paper-pilot flag | orchestrator-lead | `mode=paper` config flag | New assets start in paper-pilot ≥1wk | ✓ active_picks_sync DRY-RUN cron (`9747f9594ec`) |

## Week 2 — Asset-class specific pilots

| Asset | Pilot | Features to add | Gate / metric | Status |
|---|---|---|---|---|
| COMMODITY | CT=F 4-week paper-pilot | COT regime gate (VIX, COT) + roll-yield + seasonality | Rolling Sharpe>0.8 + PBO<0.05 × 2 weeks | ✓ IN FLIGHT (paper_pilot.html SHADOW) |
| EQUITY | top-10% volatility-adjusted | PEAD + sector rotation + short-interest | Walk-forward ≥60% + DSR>0.95 | top_n_rank_backtest tool shipped; subset filter pending |
| ETF | universe to ≥150 | sector-momentum + risk-parity + NAV arb | n≥100 + T2 sustained 30d | QUEUED (emission audit first) |
| BOND | treasury+IG credit + FRED fix | duration + curve-steepener + carry + Black-Litterman | 30-day paper PF>1.5 | ✓ FRED fix shipped `293017a5cc9`; expansion queued |
| FOREX | SHORT-only + session 13-21 UTC | carry + DXY-beta + macro regime | PF≥0.8 on SHORT subset × 60d | QUEUED (deep-dive report done) |
| CRYPTO | aggressive quarantine + cal fix | on-chain funding-skew, OI-delta, perp-basis | Rolling Sharpe>0.5 + cal error<0.02 | ✓ ml_gatekeeper CRYPTO gate (`c778f8f1696`) |
| FUTURES | CT=F + GC=F COT scanner | FinRL-style deep RL for rollovers | 30d paper PF≥0.5 | CT=F SHIPPED; GC=F mutation queued |

## Week 3-4 — scale-up & continuous validation

1. **Shadow / paper-trading service** — unified service ingests all
   paper-pilot outputs; auto-rolls to live once gates met.
2. **Cross-class edge-stability dashboard** — Plotly-Dash real-time
   showing PF/WR/Sharpe/MDD/PBO/DSR per class; alerts on regression.
3. **Research orchestrator v3b** — see separate spec at
   `reports/v3b_signal_translator_spec_2026-05-12.md`.
4. **Full-cycle BT + live-paper transition** — any class meeting T2 for
   30 consecutive days → flip mode=live under controlled cap (5% start).

## Ongoing governance

| Item | Cadence | Owner | Action |
|---|---|---|---|
| Edge-stability report | weekly | quant-lead | review PF/WR trends; pause class deviating >10% from baseline |
| Gate review meeting | bi-weekly | ops-lead | verify PBO/DSR/CPCV still enforced in CI |
| Dragger blacklist refresh | monthly | ML-ops | add new toxic emitters; remove FPs after validation |
| Capital allocation committee | monthly | CFO + quant-lead | approve lift-off for any class passing 30-day T2 |

## Real-money rule

No capital until **≥2 classes** sustain T2 metrics (PF>1.5, WR>50%,
MDD<20%, n>100, PBO<0.05, WFE>60%) for 30 consecutive days on live/shadow.

## NFA

Research surface only. Real-money sizing gated on the 10-step Lopez de
Prado AFML readiness pipeline.

## Refs

- Grok roadmap 2026-05-12 (verbatim above with status tags)
- `reports/rescue_plan_per_asset_class_2026-05-12.md`
- `reports/grok_audit_red_team_synthesis_2026-05-12.md`
- This session: ~25 commits today on origin/main
