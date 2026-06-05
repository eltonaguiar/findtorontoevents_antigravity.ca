# High-Quality Picks Plan — 2026-06-05

Operator ask: "get us some proper high-quality picks, or set a plan to get us there."

## TL;DR

After yesterday's bias scrutiny (cta_trend × COMMODITY 86.7% WR = WINDOW_ARTIFACT), we now have a 3-stage filter and **12 high-quality picks survive ALL filters**. The plan: track these forward, validate over 4 weeks, then promote to live capital.

## 3-stage filter logic (`tools/mlflow_high_quality_picks.py`)

| Stage | Filter | Drops |
|---|---|---|
| 1 — cell-level | persona × class must have n≥15, WR≥55%, sym_HHI<0.5, fam_HHI<0.5, replay<25%, ≥3 symbols, ≥3 model families | 35 of 42 cells (cta_trend × COMMODITY caught here) |
| 2 — symbol-level | within survivor cells, sym × dir must have n≥5, WR≥60% | most direction-mixed cells |
| 3 — open consensus | optional: ≥2 models currently OPEN today on the same direction | filters down to live candidates |

## Top 12 high-quality picks (post 3-stage filter)

| Persona | Class | Symbol | Dir | n | WR | avg pnl | Currently open |
|---|---|---|---|---:|---:|---:|---|
| momentum_breakout | ETF | **SPY** | LONG | 8 | **100%** | +2.02% | — |
| **carry_trade** | **FOREX** | **USDCAD** | **LONG** | **16** | **87.5%** | **+0.87%** | — |
| carry_trade | COMMODITY | ZS=F | LONG | 6 | 83.3% | +2.34% | — |
| risk_parity | BOND | SHY | SHORT | 5 | 80% | +1.89% | **4 models @ $81.88** |
| risk_parity | BOND | TLT | SHORT | 5 | 80% | +1.86% | — |
| deep_value | ETF | IWM | LONG | 8 | 75% | +1.05% | **2 models @ $280.20** |
| risk_parity | BOND | **BND** | LONG | **26** | 69.2% | +0.52% | **3 models @ $71.69** |
| risk_parity | BOND | SHY | LONG | 21 | 66.7% | +0.5% | **6 models @ $81.05** ⚠ |
| carry_trade | FOREX | NZDUSD | SHORT | 6 | 66.7% | -0.36% | 2 models @ $0.59 |
| deep_value | ETF | SPY | LONG | 6 | 66.7% | +0.93% | **2 models @ $747.93** |
| momentum_breakout | ETF | IWM | LONG | 5 | 60% | -0.45% | — |
| carry_trade | COMMODITY | GC=F | LONG | 5 | 60% | +0.19% | 1 model @ $4450.99 |

⚠ **Conflict detected (INCIDENT #97)**: risk_parity × BOND × SHY has 6 models open LONG @ $81.05 AND 4 models open SHORT @ $81.88 simultaneously. Same persona, same symbol, near-identical entry. Either intentional sub-strategy split or emitter bug.

## Plan: 4-week paper-pilot then promote

### Week 1 (this week)
- Track top 5 OPEN-consensus picks: BND LONG, SHY LONG, IWM LONG, SPY LONG, SHY SHORT
- Daily mlflow log: hist_n, hist_wr, current_open_models, current_avg_entry
- Investigate INCIDENT #97 — is SHY LONG vs SHORT a real conflict or sub-strategy?

### Week 2
- Resolve any picks that close; verify WR ≥60% holds on the next ~5 trades
- Re-run `tools/mlflow_bias_detector.py` — flag any cell that drifts to bias_score >0.5

### Week 3-4
- Build a `tools/promote_to_paper_pilot.py` that writes promoted picks to `verified_strategies/paper_pilot/<persona_class_symbol>_state.json`
- Wire to existing `bootstrap_forward_stats` pipeline so the dashboard shows them

### Week 5+
- If 3 of 5 survivors maintain bias-survivor status, promote to live capital at quarter-Kelly sizing

## Tracking

Enhancements filed via `cli_track`:
- **ENHANCEMENT #119**: Promote top 5 bias-survivor picks to paper-pilot tracking
- **ENHANCEMENT #120**: Wire auto-bias-scrutiny to nightly incidents workflow
- **INCIDENT #97 (P1)**: SHY LONG vs SHORT conflict — operator decision needed

Visible on `https://findtorontoevents.ca/audit/incidents.html` after next nightly regen.

## Files shipped

- `tools/mlflow_high_quality_picks.py` (this turn) — 3-stage filter pipeline, 12 picks logged to mlflow.db
- `tools/mlflow_bias_detector.py` (2026-06-04) — composite bias scoring
- `tools/mlflow_persona_edge_scan.py` (2026-06-04) — raw persona × class scan
- `tools/forecast_consensus_picks.py` (2026-06-04) — ARIMA 30d bands per ticker
- `tools/mlflow_verified_strategies_log.py` (2026-06-04) — verified-strategy WR/PF logging

mlflow.db: now 80+ runs across 5 experiments. View: `mlflow ui --backend-store-uri sqlite:///mlflow.db`
