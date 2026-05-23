# Unified copy-trade candidate list

## Purpose

Operators need one JSON that **aggregates** existing in-repo feeds (Hyperliquid qualified, Polymarket profiles, trusted registry) without manual copy-paste. No invented trader stats — only merged fields from source files.

## Generator

```bash
python tools/build_unified_copytrade_candidates.py
```

**Output:** `copy_trader_intel/data/unified_copytrade_candidates.json`

## Sources

| File | Contents |
|------|----------|
| `copy_trader_intel/data/qualified_traders.json` | HL-style addresses, WR, PF, edge_score |
| `copy_trader_intel/data/polymarket_trader_profiles.json` | `qualified_traders` from leaderboard + API enrichment |
| `copy_trader_intel/data/trusted_traders.json` | Strategy-prefix trust from `trusted_trader_tracker.py` |
| `copy_trader_intel/data/gate_trader_profiles.json` | Gate.io copy-trading leader profiles |

Full map (PM, exchanges, sentiment): **`docs/DATA_SOURCES_INTEGRATION.md`**.

## Hyro / audit

- Main audit: use **HIGH CONVICTION** (`hc_filter.js`) for gated picks.  
- Hyro page (`audit/hyrotrader/`): crypto execution research; cross-reference **wallet archetypes** in Polymarket rows when evaluating prediction-market alignment.  
- **Not financial advice** — candidates are for monitoring and pipeline QA.
