# Money-Ready Harvest (compact) — for fast/local models

**Context:** Multi-asset pick system on findtorontoevents.ca/audit. **11/11** pre-registered daily-bar causal hypotheses **KILLED** by `tools/edge_stability_harness.py` (eff≥0.30, same sign ≥3/5 windows, net 30bps). Canonical ledger: `audit_dashboard/data/pf_registry.json` → `by_asset_class_policy_clean_net` (NOT raw dashboard tiles).

**Tier-2 charter per class:** PF≥1.5, WR≥50%, MDD<20%, n≥100 clean post-dedup.

**Task:** For each class (CRYPTO, EQUITY, COMMODITY, ETF, FOREX, BOND):
1. Money-ready for **live** capital today? **Y/N** (brutal honesty)
2. **ONE** minimum change to deserve 90-day **paper** capital
3. Realistic **P(Tier-2 in 12mo)** as %

Then list **exactly 3 harvest ideas** each with:
- `id` (SCREAMING_SNAKE)
- `wire_target` (repo path, e.g. `ml_consensus/consensus.py`)
- `acceptance_test` (numeric, 60d horizon)

**Forbidden:** Re-run killed families (COT directional, funding-rate directional, roll-yield, PEAD, on-chain counts, exchange net-flow, cross-exchange premium, options-flow). No generic "use ML/meta-labeling" without MySQL table + harness gate.

**Known toxic pairs (Grok pf_registry):** `quan_engine`/CRYPTO, `cta_replicator`/COMMODITY, `multi_asset_copytrader`/FOREX,EQUITY.
