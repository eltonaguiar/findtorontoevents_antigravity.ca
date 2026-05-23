# Cross-Asset Strategy Matrix

**Source**: Mimo agent analysis (2026-04-12), verified by Claude Opus 4.6
**Purpose**: Map which proven strategies should be deployed to which asset classes

## The Matrix

| Strategy | Crypto | Forex | Stocks | Futures | Commodities |
|---|---|---|---|---|---|
| Connors RSI-2 | NEW (code ready) | NEW | Proven | 75.7% WR | NEW |
| Drawdown Recovery RSI | Kelly +100% | NEW | NEW | NEW | NEW |
| Multi-Period RSI Confluence | Kelly +53% | NEW | NEW | NEW | NEW |
| VWAP Deviation Reversion | Kelly +35% | N/A (no VWAP) | NEW | N/A | N/A |
| Z-Score 200d Fade | NEW | 68.3% WR | NEW | NEW | NEW |
| Funding Rate Carry | Kelly +7% | N/A | N/A | N/A | N/A |
| EMA Stack Momentum | BTC only | NEW | NEW | Tested | NEW |
| Cross-Sectional RS | NEW | NEW | CAN SLIM | NEW | NEW |
| Keltner Compression | BTC only (72%) | Unlikely | Unlikely | Unlikely | Unlikely |
| Session Time Filter | NEW | NEW | NEW | NEW | NEW |

Legend:
- **Proven** / **Kelly +X%** / **X% WR** = live or backtested results exist
- **NEW** = strategy code exists, data available, just needs backtest on this asset class
- **N/A** = structurally incompatible (e.g., no VWAP on forex)
- **Unlikely** = tested and failed on this asset class (e.g., Keltner on altcoins)
- **BTC only** = works on BTC but failed on other crypto symbols

## 8 Unbuilt Features (Full Code Exists in Brainstorm)

| Feature | Source Doc | Expected Impact |
|---|---|---|
| Multi-Timeframe Alignment Score | STRATEGY_BRAINSTORM.md | Reclassify 30% of MIXED_ADAPTIVE |
| Pullback-to-Structure Detection | STRATEGY_BRAINSTORM.md | Reclassify 20% of MIXED_ADAPTIVE |
| Funding Rate Context | STRATEGY_BRAINSTORM.md | FUNDING_CONTRARIAN > 60% WR |
| Open Interest Surge Detection | STRATEGY_BRAINSTORM.md | Momentum vs range classification |
| VWAP Displacement + OBV Slope | STRATEGY_BRAINSTORM.md | Institutional entry detection |
| Session Win-Rate Decomposition | STRATEGY_BRAINSTORM.md | Time-of-day filtering |
| Pairwise Agreement Matrix | STRATEGY_BRAINSTORM.md | Trader pair synergy |
| Exponential Time-Decayed Trust | STRATEGY_BRAINSTORM.md | Kill stale trader performance |

## Execution Plan Reference

See cursor's plan: `.cursor/plans/cross-asset-strategy-enhancement_7c3441d8.plan.md`
See Google Antigravity's plan: `.gemini/antigravity/brain/02e663e6.../implementation_plan.md`

## Key Guardrails

- All new asset-class deployments start in SHADOW mode (observe only)
- Minimum 20 trades before guard decisions, 30 for tier promotion
- Symbol-lock policy: strategies proven on specific symbols stay locked (e.g., Keltner = BTC only)
- Walk-forward validation required before production promotion

---

## Review feedback — Cursor agent (2026-04-19)

1. **Evidence labels:** Several cells say “Proven” or “Kelly +X%” — add **as-of date + evidence file** per cell on the next refresh, or newcomers treat 2026-04-12 snapshots as eternal.
2. **BTC-only rows:** Align with recent baby-strategy findings (some templates work on BTC but fail on ETH) — symbol-lock policy is not just Keltner.
3. **Orthogonality:** “Pairwise agreement” in the unbuilt-features list should reference **quantified ρ thresholds** and [correlation_prune_strategies.py](../baby_strategies/correlation_prune_strategies.py) when implemented.
4. **Factory:** Cross-check matrix against [STRATEGY_FACTORY_V1_PROPOSAL.md](STRATEGY_FACTORY_V1_PROPOSAL.md) Tier 1–4 — avoid deploying Tier-2 regime gates as standalone emitters.
5. **Audit artifact index:** See **Strategy audit directories** below.

### Strategy audit directories (repo inventory)

| Path | Contents (2026-04-19) |
|------|------------------------|
| `docs/strategy_audits/` | e.g. `toxic_systems_block_2026-04-15.md`, `stocks_competition_2026-04-14.md` |
| `docs/strategy_reviews/` | e.g. `2026_04_13_inbound_strategies.md` |
| `docs/strategy_phase1/` | `README.md`, `phase1_gate_backtest_report.txt` |
| `docs/strategy_phase2/` | `SYNTHESIS.md` |

Expand this table as new audits land; prefer linking from the audit PR to the exact file.
