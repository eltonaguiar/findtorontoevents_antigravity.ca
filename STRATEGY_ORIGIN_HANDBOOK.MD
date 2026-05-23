# Strategy Origin Handbook (v1.0) 📘

This handbook serves as the definitive reference for understanding the trading strategy taxonomy within the Antigravity ecosystem. Use this to avoid duplicated efforts in ingestion and analysis.

---

## 🏛 CORE SYSTEMS (The ROOTs)

| ROOT Origin | Source System | Primary Asset | Typical Latency | Key Methodology |
| :--- | :--- | :--- | :--- | :--- |
| **Alpha Engine** | `ml_crypto_predictor` | Crypto | 15 min | Multi-factor ML (XGBoost/LightGBM) with 400+ features. |
| **Sentiment** | `fear_greed_contrarian` | Crypto | 1 hour | Contrarian trading based on social exhaustion & F&G Index. |
| **DNA / Genome** | `dna_mutation_engine` | All | Real-time | Parameter-evolved variants of parent strategies. |
| **Institutional** | `quant_institutional` | Stocks/Futures | End of Day | VWAP, Connors RSI, and mean-reversion artifacts. |
| **Copy Intelligence** | `copy_trader_intel` | Crypto/Forex | Variable | Signal scraping from verified top-performing traders. |

---

## 🧠 STRATEGY TAGS & NOMENCLATURE

- `winner_pattern_*`: A strategy that has been identified as a persistent performer through the **Winner Predictor** engine.
- `contrarian_*`: A strategy that is currently betting against short-term trend exhaustion or liquidity grabs.
- `ml_enhanced_*`: A base indicator strategy (e.g., RSI) that has been filtered by a secondary ML layer.
- `ss_*`: (Super Signal) A confluence of 3+ systems agree on signal direction.

---

## ⚠️ RISK CATEGORIES

| Category | Risk Profile | Slippage Exposure | Recommended Max Cap |
| :--- | :--- | :--- | :--- |
| **Elite ML** | Low | Low (High Liquidity) | 10.0% of Portfolio |
| **DNA Mutations** | Medium | Medium | 5.0% of Portfolio |
| **Low-Cap Growth** | High | **CRITICAL** | 2.5% of Portfolio |
| **Copy-Trader** | High | Variable | 5.0% of Portfolio |

---

## 🛠 HOW TO ADD A NEW ROOT

1.  **Register ID** in `systems_manifest.json` under the `systems` array.
2.  **Define Endpoints** for active and closed picks (must return standard JSON schema).
3.  **Update `update_audit_dashboard.py`** to include your new system in the aggregation cycle.
4.  **Add inline comments** to your ingestion script with the `@origin` tag.
