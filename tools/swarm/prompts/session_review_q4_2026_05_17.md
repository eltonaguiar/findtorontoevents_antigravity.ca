Senior quant review — 4 judgment calls from trading system session 2026-05-17. Answer each with a clear recommendation and confidence level.

CONTEXT: Multi-strategy alpha engine, asset classes CRYPTO/EQUITY/COMMODITY/FOREX/ETF/BOND. Charter: Tier 2 = PF>1.5, WR>50%, MDD<20%.

Q1 — OVER-EMISSION: smart_money_accumulation emitted 4 picks on same NIO signal in 6 hours (2026-05-13). Strategy is now blocked. Is this P1 systemic (all active strategies need cooldown guard) or historical artifact (no action needed)?

Q2 — COMMODITY CONFIDENCE FILTER: 0.60-0.70 confidence bucket = WR=79%, PF=5.63 (n=236) vs full COMMODITY cohort PF=1.78, WR=46.9% (n=750). Add confidence gate 0.60-0.80 for COMMODITY? Key concern: is the confidence field endogenous to pick quality?

Q3 — FOREX GATE: 30d PF=2.30 (above T2), recovery driven by cta_cross_asset_tsmom SHORT. FOREX_COPYTRADER_ENABLE gate currently OFF. Re-evaluate enabling it?

Q4 — DORMANT STRATEGY RETIREMENT: 153/209 strategies dormant. ml_enhanced_* superseded but still in closed_picks.json inflating confidence buckets. Add to BLOCKED_SOURCE_SYSTEMS?

Give 1-2 sentence verdict per question with a recommendation (YES/NO/WAIT) and confidence level (high/medium/low).
