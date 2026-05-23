# Worst-Strategy R3 — Mutate or kill toxic emitters

## Toxic pairs (clean registry, May 2026)

| Pair | Problem |
|------|---------|
| `quan_engine` / CRYPTO | High volume, PF~0.70 — drags class |
| `cta_replicator` / COMMODITY | PF<1 on COMMODITY despite ok elsewhere |
| `multi_asset_copytrader` / FOREX, EQUITY | Negative contribution |

## Whitelist seeds (do not block)

- `crypto_rsi_whaleconfirmed_v1` / CRYPTO (PF~1.58 clean n~89)
- `multi_asset_cot` / COMMODITY
- `cta_replicator` / FOREX only (micro-slice PF~3.17 n~103)

## Task

For **each toxic pair**:
1. Root-cause hypothesis (why it fails — not "bad market")
2. **Mutated strategy** proposal (new name, changed universe/horizon/filter) per MUTATION three-axis
3. Pre-registration sketch (hypothesis_id placeholder, data source, bar_freq)
4. Harness expectation: will it likely pass sign-stability? Y/N + 1 sentence

Then: **one** integration design for `EMITTER_WHITELIST_FROM_REGISTRY` — pseudocode or bullet steps in `ml_consensus/consensus.py` + `alpha_engine/forward_validator.py`.

No code — architecture only. Under 700 words.
