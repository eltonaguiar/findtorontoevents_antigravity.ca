# Harvested Ideas — Forex

**Asset Class:** `FOREX`  
**Inventory Coverage (`00_inventory.csv`):** `193` pure `FOREX` files + `351+` cross-asset (`FOREX|CRYPTO`, `FOREX|COMMODITY_FUTURES`, `FOREX|ETF`).

---

## 1. What Was Already Tried in the Repo
- **Multi-Asset & Retail Sentiment Scanners:** `myfxbook_retail_contrarian`, `cta_cross_asset_tsmom`, `non_crypto_consensus`, `forex_copytrader_recovery_2026_05_17.md`, MQL5 copy-trader cards (`MEMORY.md:12`).
- **COT & Carry Strategies:** `ForexCOTReversalV1_6GateLead` (`KIMI_INTEGRATION_STATUS.md:61`), `tools/research/forex_carry.py` (`updates/index.html:43` G10 carry 2010–2026 claiming `n=197, WR=60.4%, PF=1.59`).
- **Kimi FX Research (`KIMI_STRATS_V3.MD:25`):** Tokyo Fix Squeeze, FX session breakouts.
- **Kill-Switch (`alpha_engine/config.py:329`):** `FOREX_HARD_DISABLE` (defaulted `"0"`—disabled—allowing live emission).

## 2. Observed Results & Suspected Failure Modes
- **Canonical Live Readiness (`TESTING_PROTOCOL.MD:22`):** `FOREX` (`n=29, WR=27.6%, PF=0.035, MDD=82.3%` -> `INSUFFICIENT_DATA`). `money_ready` `n=612` gave **PF = 0.66**; honest post-noise Kimi audit logged **PF = 0.27** (`KIMI_INTEGRATION_STATUS.md:15`).
- **Data-Join Contamination (`updates/index.html:89`):** `reports/deep_dive_forex_regime_2026-06-05.md` discovered that all 3 FOREX walk-forward "passes" were **data-join artifacts** (`88%` of `cta_cross_asset_tsmom` closes occurred in `2026-05+` where `alpha_macro` had ended).
- **Garbage Price Ingest (`memory/2026-11-14.md:78`):** `EURGBP=X` stored live entry at `688.17` vs true FX rate `0.835` (`824×` mis-scaled).
- **Failure Modes:** #4 Unrealistic Cost Model (~0 spread assumed on retail pip moves), #2 Data-Join Lookahead/Artifact, #7 Garbage Ingest, #5 Weak SNR.

## 3. Research Gap for Phase 3 (`Plan/forex/PLAN.md`)
- Audit the **realized `FOREX` closed trade cohort** in `live_dashboard_payload.json` with an **explicit retail spread + swap friction stress (1.5 pips / 3 bps RT + 2× stress)**, full **10-step proof gauntlet**, and **kill-or-cure formal adjudication** so FOREX is either rescued by verifiable G10 carry data or cleanly archived as `DEAD — retail spread wipes out edge`.

