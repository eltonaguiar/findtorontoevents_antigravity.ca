# Rescue Question Factory — creative diagnostics per asset class (v1)

You are a **senior quant + forensic data scientist** helping rescue a **failing multi-asset pick pipeline** (`findtorontoevents.ca/audit`).

## Ground truth (non-negotiable)

- **11/11** pre-registered **daily-bar causal** hypotheses **KILLED** by `tools/edge_stability_harness.py`.
- Canonical performance: `audit_dashboard/data/pf_registry.json` → `by_asset_class_policy_clean_net`.
- **Tier-2 charter:** PF≥1.5, WR≥50%, MDD<20%, **n≥100 clean** post-dedup.
- **Today:** paper-only; emitter whitelist in **shadow** (`alpha_engine/emitter_whitelist.py`).
- **Toxic pairs:** `quan_engine`/CRYPTO, `cta_replicator`/COMMODITY, `multi_asset_copytrader`/FOREX,EQUITY.

## Failing-prediction snapshot

| Class | Failure | Best known slice |
|-------|---------|------------------|
| CRYPTO | Class WR&lt;50; drag volume | `crypto_rsi_whaleconfirmed_v1`, elite systems masked |
| EQUITY | T2 aggregate; confidence inverts | `aggregated_picks`; PEAD partial |
| COMMODITY | CT=F concentration; dedup risk | `multi_asset_cot` pending verify |
| ETF | n&lt;100, borderline PF | premium arb unproven |
| FOREX | PF~0.27 | `cta_replicator` slice only (paper) |
| BOND | n=11 | not statistically viable yet |

## Daily-ideas context (summarized)

Multi-agent daily ideas (19 files) emphasize: emitter hygiene &gt; new scanners; CRYPTO intraday (H-035); COMMODITY verify COT; FOREX carry/isolate signal_validation; EQUITY trust_score/PEAD; infrastructure (DB freshness, dedup, schema drift).

Full digest: `reports/DAILY_IDEAS_DIGEST_FOR_RESCUE_2026-05-19.md`

---

## Your task — invent **creative diagnostic questions**

For **each** asset class (CRYPTO, EQUITY, COMMODITY, ETF, FOREX, BOND), produce:

### A) Three “rescue questions” (must be creative + falsifiable)

Each question must:
- Target **why our prediction fails** (not generic “improve ML”)
- Be answerable with **repo data** (`ejaguiar1_stocks`, `ejaguiar1_backtests`, `pf_registry.json`, harness) OR **named free APIs**
- Include a **falsification criterion** (“if X then abandon this rescue path”)
- Avoid killed hypothesis families (COT directional daily, funding arb, PEAD as primary, on-chain counts)

Format per question:
```
Q-ID: RESCUE_<CLASS>_01
Question: ...
Why creative: ...
Data needed: table/API ...
Falsify if: ...
```

### B) One “moonshot” question per class

A high-risk/high-reward question that could unlock Tier-2 **if true** — still must be pre-registerable (hypothesis_id + bar_freq).

### C) Cross-class meta-question

One question about **shared infrastructure** (resolver, dedup, harness, GHA) that might explain **multiple** class failures.

---

## Output rules

- **Do NOT** claim any class is live money-ready.
- **Do NOT** invent file paths — only cite paths you are confident exist (`alpha_engine/`, `audit_trail/`, `tools/edge_stability_harness.py`, `.github/workflows/audit-dashboard.yml`).
- Rank your top **5 questions across all classes** by expected information gain (1–5 list at end).
