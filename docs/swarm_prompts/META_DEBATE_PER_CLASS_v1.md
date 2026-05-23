# Meta-debate: top-10 strategies per asset class (v1)

You are **three roles in one response** — debate yourself briefly, then synthesize:

1. **Prosecutor** — argues each strategy should stay **killed/quarantined** given registry PF, toxic flags, and 11/11 killed daily-bar harness.
2. **Defense** — argues how to **rescue** (mutation, isolate slice, intraday re-register) without recycling killed families.
3. **Judge** — picks the winning side per strategy rank with **one falsifiable 30-day test**.

## Ground truth

- Canonical: `pf_registry.json` → `by_asset_class_policy_clean_net`
- Paper-only until harness admits n≥100 clean per class
- `EMITTER_WHITELIST_ENFORCE=0` (shadow) — debate should say when to flip enforce=1
- No invented workflow filenames

## Configuration spec + top-10 tables

{{TOP10_STRATEGIES_MD}}

---

## Required output

### A) Per asset class (CRYPTO, EQUITY, COMMODITY, ETF, FOREX, BOND)

For **ranks 1–3 only** (highest PF in table), write a 3-line debate block:

```
### <CLASS> rank N: `<strategy>`
Prosecutor: ...
Defense: ...
Judge: VERDICT [RESCUE|KILL|SHADOW] — test: ...
```

### B) Meta-prompt recommendations

Produce **5 meta-prompt templates** we should reuse in future local/cloud runs, e.g.:

| meta_id | when_to_use | inject_variables | success_signal |
|---------|-------------|------------------|----------------|

Each must reference a **real repo path** and **acceptance metric** (PF, WR, harness eff, n).

### C) Cross-class synthesis

| Class | Best rescue strategy (from table) | Worst drag strategy | Flip enforce whitelist? (Y/N + why) |
|-------|-----------------------------------|---------------------|-------------------------------------|

### D) Top 5 information-gain questions (new, not in rescue round)

Creative, falsifiable, tied to a specific rank/strategy in the tables above.

**Forbidden:** live-ready claims; daily-bar COT/funding/PEAD as *new* primary families.
