# final_v2 — childlike-airport (Consolidated Review & Action Plan)

**Date:** 2026-11-14  
**Author:** Kilo (worktree `childlike-airport`)  
**Repository:** `eltonaguiar/findtorontoevents_antigravity.ca`  
**Purpose:** Peer-reviewed, per-asset-class profitability assessment and a statistically grounded implementation plan, consolidating `final_2026_11_14` findings, local audits, and new VWAP v12 results.

## TL;DR

- **Aggregate system: not profitable / not trustworthy** — severe data & PnL integrity failures (fake 0% P/L, understated losses, ~78.6% zombies, stale 172d DB, empty audit trail, broken sync/pricing, failing workflows).
- **Component-level profitable approaches exist** but are narrow and must be gated: **Vol-Targeted TSMOM (crypto, research-proven)**, **Regime-Filtered VWAP MR (crypto, basic-validated, core symbols)**, **Walk-Forward Variant C (equity/ETF, pilot)**, **mega_mutation (candidate, needs replication)**.
- **Do not deploy to live capital** until data remediation, independent reproduction, and strict statistical gates (incl. PBO<0.3, DSR>0.95, sufficient n, net-of-costs) pass in OOS + paper forward.

## Directory Index

| Path | Contents |
|---|---|
| `00_executive_summary/README.md` | Executive summary, peer consensus, top candidates, critical issues |
| `01_peer_review_synthesis/README.md` | Synthesis of deepAI, ITERATION-005, Grok, flaxen-hair, hilarious-seer, scratch-hippodraco, Kilo |
| `02_per_asset_class_profitability/stocks/README.md` | Stocks: Variant C pilot, Faber TAA build — recommendation |
| `02_per_asset_class_profitability/bonds/README.md` | Bonds: vol-targeted bond trend (build), sync/data gaps |
| `02_per_asset_class_profitability/etfs/README.md` | ETFs: Faber TAA / Variant C — recommendation |
| `02_per_asset_class_profitability/mutual_funds/README.md` | Mutual funds: build `MUTUAL_FUND` class + Faber TAA/NAV model |
| `02_per_asset_class_profitability/forex/README.md` | Forex: FX momentum + `fx_kill_switch.py` (build) |
| `02_per_asset_class_profitability/crypto/README.md` | Crypto: VWAP-MR v11/v12 + TSMOM + mega_mutation — primary opportunity |
| `02_per_asset_class_profitability/commodities/README.md` | Commodities: trend following after 98.4% zero-P/L fix |
| `03_profitable_approach_candidates/README.md` | Ranked candidate matrix, v11/v12 VWAP details, promotion criteria |
| `04_implementation_roadmap/README.md` | Phased plan: integrity → validate → paper → gated live + per-asset build-out |
| `05_data_quality_remediation/README.md` | P0 defects and fixes (PnL, sync, zombies, audit trail, regime, ops) with exit criteria |
| `06_statistical_validation_framework/README.md` | Mandatory gates/tiers/protocol/checklist (PF, Sharpe, PBO, DSR, MDD, n, costs) |

## Key Results (at a glance)

| Approach | Asset | Result | Tier |
|---|---|---|---|
| Vol-Targeted TSMOM (ITERATION-005) | Crypto | CAGR 23.0%, Sharpe 2.13, PF 1.40, MDD −17.4%, t=5.56, CI [1.25,3.25] (7.4y) | PROVEN (research) |
| Regime-Filtered VWAP MR v11 (Kilo) | Crypto core | n=65, PF 1.435, Sharpe 7.10, MDD 3.5%, PBO 0.480, P(SR>0)=1.000 | VALIDATED (basic) |
| Regime-Filtered VWAP MR v12 (Kilo, 2026-11-14) | Crypto 8-sym | n=129, PF 1.210, Sharpe 3.76, MDD 10.0%, PBO 0.489, P(SR>0)=1.000; core BTC/ETH/SOL/XRP/ADA profitable, DOGE/AVAX/LINK not | PROFITABLE (basic, selective) |
| Walk-Forward Variant C (deepAI) | Equity/ETF | PF 1.26, n=237, p<0.0013 | PILOT |
| mega_mutation_macd_rsi/ema_momentum (flaxen-hair) | Crypto | PF 3.12–5.816 BT, 8.32 FW, WR 84% | CANDIDATE |

## Action Plan (condensed)

1. **P0 Remediate data/PnL/ops** (`05`): fix sync & pricing code, reprice/resolve zombies, unify sources, restore audit trail/regime, stabilize workflows. *No performance claims until exit criteria met.*
2. **Reproduce & stress-test** (`06`): VWAP-MR on >730d exchange data (target PBO<0.3), TSMOM production spec, Variant C replication, mega_mutation OOS — all net-of-realistic costs.
3. **Paper/shadow deploy** top crypto candidates (VWAP-MR core + TSMOM) with monitoring and kill-switches.
4. **Build per-asset** (`02`,`04`): Faber TAA (stocks/ETFs/MF), vol-targeted bond trend, FX momentum+kill switch, commodity trend (post-fix).
5. **Gated live** only after strict gates pass in OOS + paper (PF≥1.5 target, Sharpe≥1.0, MDD<20%, PBO<0.3, DSR>0.95, sufficient n).

## Sources / Provenance
- Local audits: `updates/2026-11-14-ML-AUDIT-childlike-airport.md`, `updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/*`, `updates/2026-11-14-PROFITABLE-APPROACH-VWAP-MEAN-REVERSION.md` (repo).
- Prior consolidation: `final_2026_11_14/childlike-airport/**`.
- Peer artifacts: deepAI `origin/audit/live-audit-2026-11-14` (e.g. `2026-11-14/deepAI_final_audit_20261114_1809/*`), ITERATION-005 (`05a4ef3ff14`), Grok README, flaxen-hair `0473024f0d7`, hilarious-seer, scratch-hippodraco.
- New computation: `/tmp/kilo/regime_filtered_vwap_v12.py` → `/tmp/kilo/regime_filtered_vwap_v12_results.json` (2026-11-14).

*Component results do not imply end-to-end, live, net-of-all-costs profitability.*
