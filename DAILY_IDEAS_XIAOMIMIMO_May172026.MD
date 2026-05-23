# DAILY IDEAS — Xiaomi MiMo Audit + Independent Verification — 2026-05-17

Xiaomi MiMo (real repo clone, 21,156 files) produced a detailed `/audit`
audit + a "holy grail" claim: **two asset classes can reach institutional
grade NOW with one filter each**. This document records MiMo's claims AND the
result of independent verification subagents — because the holy-grail claim
**does not survive verification**.

## MiMo's "holy grail" claims

| Claim | MiMo's pitch |
|---|---|
| **CRYPTO** | gate `ml_enhanced_* + confidence >= 0.6` → n=242, WR 60.7%, PF 3.82 → "institutional" (or `conf>=0.8` → n=126, WR 61.1%, PF 3.67) |
| **FOREX** | block `multi_asset_copytrader` → `cta_replicator` only → n=179, WR 58.1%, PF 2.20 → "institutional" |
| COMMODITY | COT WR 76.5% PF 4.58 — flagged by MiMo itself as leakage-suspect |
| EQUITY | data problem — 44 repo picks vs 393 dashboard |

MiMo also supplied two copy-paste `quality_gates.py` edits (CRYPTO min-conf
gate, FOREX source-system block).

## Independent verification — subagents recomputed from `closed_picks.json`

### FOREX cta_replicator subset — REFUTED as "institutional"
- Raw numbers reproduce (cta_replicator n=179 WR 58.1% PF 2.20) — BUT:
- **177/179 rows are `SL_HIT_REPLAY`/`TP_HIT_REPLAY`** — resolver-replayed against
  yfinance spot, NOT live closes. The WR is resolver-manufactured
  (`feedback_noncrypto_resolver_live_close_bug`).
- `strategy_performance.json` says `cta_cross_asset_tsmom` is **PF 0.38, WR 44.8%,
  LOST** once its COMMODITY rows are included — the FOREX-only slice is cherry-picked.
- "PF 2.20" is a fixed 0.3%-TP / 0.2%-SL grid × 59% hit-rate; **total realized
  PnL is +0.18%** across 168 deduped trades. Not discovered alpha.
- All edge is SHORT-side; LONG is break-even. 3 symbols only (USDJPY 111/168).
- **Verdict: NOT a trustworthy live edge.** Do not gate FOREX to it.

### CRYPTO conf>=0.8 cohort — REFUTED as generalizable edge
- conf>=0.8 n=126 WR 61.1% PF 3.67 reproduces — BUT:
- **87% of the cohort is 2 symbols (RENDERUSDT 48 + FETUSDT 44)**; 110/126 is
  3 single-symbol ML strategies (`ml_enhanced_RENDER/FET/BNB`). All LONG-only.
- It is **3 ML models fitted to 3 AI-narrative tokens in a 2024 up-leg** — not
  a confidence effect. Effective independent sample ≈ 3, not 126.
- MiMo's `conf>=0.7 & no-quan_engine` n=191 is **wrong — true n=119**.
- **Verdict: PARTIAL — cohort exists in-data but is concentration-fragile,
  overfit, not generalizable.** A blanket `confidence>=0.60` crypto gate selects
  on a metric the repo's own audit proves ANTI-predictive (conf 0.7 → 21% WR).

## Code-block verdict

| MiMo block | Verdict |
|---|---|
| **Block 1 — CRYPTO `confidence < 0.60` reject gate** | ❌ **DO NOT APPLY.** Gates on a contradicted metric. The conf>=0.8 "edge" is 3 overfit ML models, not a confidence threshold — a class-wide conf>=0.6 reject would cut volume on a false premise. |
| **Block 2 — FOREX block `multi_asset_copytrader`** | 🟡 **Block itself is defensible** — `multi_asset_copytrader` IS a verified FOREX drag (n=696, WR 16.5%, PF 0.23). Removing a proven-losing source system is sound. But it does NOT make FOREX "institutional" — the residual `cta_replicator` is replay-resolved fixed-grid (see above). Apply as drag-removal only, NOT as an institutional-grade unlock. |

## What IS verified + actionable

1. `multi_asset_copytrader` is a genuine FOREX drag — blocking it per-asset-class is a legit quality improvement (NOT an edge unlock).
2. `quan_engine_scalp` (70% of the CRYPTO ledger, PF 0.38) is **already blocked** in 9+ structures in `quality_gates.py` — the −960% is dead historical data, not live bleed.
3. `cot_paper_pilot_status.json` still falsely claims `DSR=1.0 / TIER_1_RENAISSANCE` — fix built (`fix/cot-paper-pilot-overemission-dedup`: dedup-by-release-week → tier `SHADOW_INSUFFICIENT_N`).

## Bottom line
MiMo did real, careful work and correctly found the aggregate poisons
(`multi_asset_copytrader`, `quan_engine`). But its "two classes institutional
NOW" headline is **not supported** — both "edges" are resolver-replay artifacts
/ overfit-concentration. No asset class is real-money ready. Do not adjust the
high-conviction filter on these claims. The honest next steps are the
verified-but-modest ones: drop the FOREX `multi_asset_copytrader` drag, keep
`quan_engine_scalp` blocked, ship the COT-status falsification fix.

*Verified by 2 independent recomputation subagents, 2026-05-17. See also
`reports/CLOUD_AGENT_AUDIT_VERIFICATION_PROMPT.md` §0b (inverse-projection rule)
and §0c (recency-window rule).*
