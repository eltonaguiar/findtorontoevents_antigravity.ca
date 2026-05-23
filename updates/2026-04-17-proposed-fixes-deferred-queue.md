# Proposed Fixes: 6 Deferred Items (v2 — 3-AI reviewed)

**Author:** Claude Opus 4.7 (overnight autonomous, post-policy v1.1)
**Date:** 2026-04-17
**Status:** v2 — incorporates DeepSeek + Inception mercury-2 + Ollama Cloud kimi-k2.5 review consensus. Awaiting user approval to execute.
**Governing policy:** `docs/STRATEGY_LIFECYCLE_POLICY.md` v1.1

## Consensus from 3-AI review

| Fix | DeepSeek | Inception | Ollama | Final verdict |
|---|---|---|---|---|
| 1 quan inverse SANDBOX | APPROVE | REVISE (add slippage limits) | APPROVE | **APPROVE** with slippage gate added |
| 2 TV account reroute | REVISE (find router first) | APPROVE | APPROVE | **APPROVE** — clarified as manual op |
| 3 kimi_signal_tracking block | APPROVE | APPROVE | APPROVE | **APPROVE** unanimously |
| 4 ALPHA ENGINE merge fix | REVISE (locking + pruning) | REVISE (atomic + prune) | REVISE (locking) | **REVISE** — file lock + 30d prune mandatory |
| 5 Node 20→24 | APPROVE (Option A env var) | APPROVE (Option A) | APPROVE with caution | **APPROVE** — Option A first, B later |
| 6 Binance fallback chain | APPROVE | REVISE (schema verification) | partial | **REVISE** — add schema validation tests |

**Top 2 cross-fix risks (consensus):**
1. **Hot-path file race condition (Fix #4)** — DeepSeek + Inception both flagged unbounded growth + concurrent-write corruption.
2. **New strategy live behavior (Fix #1)** — Inception flagged slippage/fill rate may differ from backtest; Ollama-Kimi noted no forward record yet.

## Revisions applied to v2

- **Fix #1:** Added max-slippage cap (0.3% per fill) + max-fill-rate guard (reject if fill spans > 1.5× ATR)
- **Fix #4:** REQUIRES (a) `fcntl.flock` (Linux) / `msvcrt.locking` (Windows) atomic write, (b) prune entries with no closed_picks update in 30 days, (c) backup file before each rewrite
- **Fix #6:** REQUIRES per-API schema validator + integration test that asserts ticker fields match normalized format

---

This document specifies WHAT to change, WHERE (file:line), WHY, and the RISK profile of each. The next step is multi-AI critique then revised execution.

---

## 1. Deploy `quan_engine_scalp_hybrid_inverse` SANDBOX

### What
Create a new strategy file `alpha_engine/quan_engine_scalp_hybrid_inverse.py` based on the M_HYBRID variant from the mutation investigation. Wire it into the strategy registry. Initial sandbox deployment.

### Source
`updates/2026-04-17-quan-engine-scalp-mutation-investigation.md` (commit `9645899b09`).

### Logic
- Inherit entry/exit math from `quan_engine_scalp` (same R:R, same hold)
- Per-symbol direction override:
  - **Native LONG:** TRXUSDT, TAOUSDT (only 2 symbols where parent wins)
  - **Inverted to SHORT:** the 9 chronic losers (SOLUSDT, ICPUSDT, DOTUSDT, BTCUSDT, ETHUSDT, etc.)
  - **BLOCKED outright:** MATICUSDT (117/117 historical losses)
- Sizing: 0.25× per Strategy Lifecycle Policy v1.1 sandbox phase
- Promotion criteria: 200 forward trades + WR≥60% Wilson 95% CI lower≥55% + PF≥2.0

### Files
| File | Change |
|---|---|
| `alpha_engine/quan_engine_scalp_hybrid_inverse.py` | NEW — strategy implementation |
| `alpha_engine/scanner.py` | wire into CRYPTO_STRATEGIES registry |
| `alpha_engine/non_crypto_policy.py` (or crypto equivalent) | sandbox sizing + probation thresholds |

### Risk
Medium. New strategy = no historical forward record. The mutation MD shows 71.26% WR PF 2.89 on n=414 backtest, but live behavior may differ (slippage, partial fills, microstructure).

### Estimated impact
+50 PnL pts/quarter if sandbox metrics confirm backtest.

---

## 2. Reroute TV paper account `HIGHFWWRABV55_SCOREABOVE50_V3` → `HIGHFWWRABV70`

### What
Change TV paper account routing rules so the existing account (or a new V4 account) uses `strat_fwd_wr >= 70` instead of `>= 55`, and excludes `claude_gainer_st` strategy.

### Source
`updates/2026-04-17-edge-deepscan-2-filter-combos.md` finding: "WR jumps non-linearly from 61.0% (fwd>=55) → 74.6% (fwd>=70). claude_gainer_st (403/561 picks, 57.8% WR) is the underperformer dragging the account; super_signals (102 picks, 73.5% WR) is the actual edge."

### Files
**Note:** TV account routing has no code home in this repo (per deepscan-5 finding: account names like `HIGHFWWRABV55_SCOREABOVE50_V3` have zero hits in the codebase — they are free-form labels in TradingView paper portfolios).

So this isn't a code change — it's an OPERATIONAL change executed via TradingView UI:
- Either rebuild the existing portfolio with new selection rules
- Or create a new portfolio `HIGHFWWRABV70_SCOREABOVE50_V4` and let the old one wind down

The router on our side (the agent emitting picks to TV) needs filter logic updated. Need to find where picks get routed to TV paper:

```bash
grep -rln "HIGHFWWR\|SCOREABOVE\|tv_paper.*account\|paper_account_filter" --include="*.py" .
```

If no router exists yet, the routing happens manually via the `tv-paper-trade` skill — in which case the operator (you) just changes which picks get pushed.

### Risk
Low. Active positions on the old account are untouched; only NEW picks routed differently.

### Estimated impact
Stops the active bleed (8/8 red positions reported earlier) once existing positions close out.

---

## 3. Block `kimi_signal_tracking` source

### What
Add `"kimi_signal_tracking"` to `BLOCKED_SOURCE_SYSTEMS` in `audit_trail/quality_gates.py`. Distinct from `kimi_riseoftheclaw` which is healthy.

### Source
`updates/2026-04-17-kimi-signal-tracking-investigation.md` (commit `2e4ba8c268`). 26 of 34 picks have data-layer corruption: `direction=BUY` (wrong vocab), `confidence=9.9999` (10× scale bug), empty strategy field, missing rr_ratio. 38.5% WR, -52.6% PnL.

### Files
| File | Change |
|---|---|
| `audit_trail/quality_gates.py:888` (BLOCKED_SOURCE_SYSTEMS set) | add `"kimi_signal_tracking"` |

### Pre-block check (per policy)
Before blocking, query active picks to count what would be orphaned:
```python
import json
d = json.load(open('alpha_engine/data/active_picks.json'))
picks = d.get('picks', d) if isinstance(d, dict) else d
n = sum(1 for p in picks if 'kimi_signal_tracking' in str(p.get('source_system','')))
print(f"Active picks at risk: {n}")
```

### Risk
Low — source has been broken for weeks; blocking won't change much in production. Reversible by removing the entry.

### Estimated impact
+53 PnL pts (per deepscan-4).

---

## 4. Fix ALPHA ENGINE `strategy_performance.json` overwrite bug

### What
Modify the dump function to MERGE existing entries with current scan output, instead of OVERWRITING with only scan-cycle entries.

### Source
`updates/2026-04-17-alpha-engine-data-loss-bug.md` (commit `1ff7ba6fa7`). Each scan run drops 111 of 161 strategies from the file (mostly `closed_picks=1` ml_enhanced variants), keeping only 50 currently-scanned ones.

### Files
First need to locate the dump function. Likely in:
- `alpha_engine/production_scanner.py` (most likely — writes premium_signals.json + strategy_performance.json)
- `alpha_engine/strategy_performance_tracker.py` (if exists)
- A `_save_strategy_performance` helper somewhere

Find with: `grep -rn "strategy_performance.json" alpha_engine/ | grep -i 'dump\|write\|save'`

### Code change
```python
# BEFORE (likely):
with open(SP_PATH, 'w') as f:
    json.dump(current_run_strategies, f)

# AFTER (proposed):
existing = {}
if SP_PATH.exists():
    try:
        with open(SP_PATH) as f:
            existing = json.load(f)
    except (json.JSONDecodeError, OSError):
        existing = {}
existing.update(current_run_strategies)  # current run wins on conflict
with open(SP_PATH, 'w') as f:
    json.dump(existing, f, indent=2)
```

Optionally add a `last_seen` timestamp + prune stale entries (>30 days) to prevent unbounded growth.

### Risk
Medium. Touches a hot-path data file. Need to verify:
- Race condition (two scan runs writing simultaneously) — may need file lock
- Disk usage growth (without pruning, file grows ~2k lines/week)
- Backward compat with downstream consumers

### Estimated impact
Restores trend-tracking for 111 hidden strategies. Reduces git churn from 354k deletions/run to <1k. Not a direct PnL fix but enables better disable/mutate decisions.

---

## 5. Node.js 20 → 24 upgrade across workflows

### What
Bulk-update `actions/checkout@v4` and `actions/setup-python@v5` references where they pull Node.js 20 actions. Per GitHub: Node.js 20 deprecated June 2026; default flips Sept 2026.

### Source
Visible warning across all GHA runs:
> Node.js 20 actions are deprecated... actions/checkout@v4, actions/setup-python@v5... starting June 2nd, 2026.

### Files
534 occurrences of `actions/checkout@v` or `actions/setup-python@v` across `.github/workflows/*.yml`. Need a sweep.

### Approach
Two options:

**Option A (immediate, opt-in):** add `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` env var per-workflow at the top level. Quick, but workflow-by-workflow.

**Option B (clean):** wait for `actions/checkout@v5` and `actions/setup-python@v6` releases (or check if already available) and bulk-bump versions. More work, more durable.

### Risk
Low if Option A. Medium if Option B (action API may have changed).

### Estimated impact
None today. Prevents breakage at June 2026 deadline.

---

## 6. Fix `winner_reverse_engineer.py` Binance-only fallback chain

### What
Extend `fetch_all_tickers()` to fall through to CoinGecko, KuCoin, CryptoCompare per the project memory rule "API Failover: Never single Binance endpoint; always 3+ fallback chain. Binance mirrors → CoinGecko → KuCoin → CryptoCompare".

### Source
Hourly tick #5 spot-check found `[ERROR] Could not fetch tickers from any API endpoint` in `hindsight-learner` SUCCESS run — workflow exits "successful" with empty output when all 3 Binance endpoints geo-block (HTTP 451).

### Files
| File | Change |
|---|---|
| `alpha_engine/winner_reverse_engineer.py:97-116` (fetch_all_tickers) | add 3 fallback fetchers |
| `alpha_engine/winner_reverse_engineer.py:119-134` (fetch_klines) | same expansion |

### Code change
```python
COINGECKO_TICKER = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=volume_desc&per_page=250&page=1"
KUCOIN_TICKER = "https://api.kucoin.com/api/v1/market/allTickers"
CRYPTOCOMPARE_TICKER = "https://min-api.cryptocompare.com/data/top/totalvolfull?limit=100&tsym=USD"

def fetch_all_tickers():
    # Existing 3 Binance attempts
    for url, name in [(BINANCE_FUTURES_TICKER, "futures"),
                      (BINANCE_SPOT_TICKER, "spot"),
                      (BINANCE_MIRROR_TICKER, "mirror")]:
        data = _api_get(url)
        if data and isinstance(data, list) and len(data) > 10:
            return data, name
    # NEW: non-Binance fallbacks (need format normalization)
    for url, name, normalize in [
        (COINGECKO_TICKER, "coingecko", _normalize_coingecko),
        (KUCOIN_TICKER, "kucoin", _normalize_kucoin),
        (CRYPTOCOMPARE_TICKER, "cryptocompare", _normalize_cryptocompare),
    ]:
        data = _api_get(url)
        if data:
            try:
                normalized = normalize(data)
                if normalized and len(normalized) > 10:
                    return normalized, name
            except Exception as e:
                print(f"  [warn] {name} normalize failed: {e}")
    return [], "none"
```

Plus 3 normalizer functions to convert each non-Binance API's schema to Binance ticker format.

### Risk
Medium. Each new API has different rate limits, auth requirements, schema. Normalization can subtly change downstream calculations.

### Estimated impact
Hindsight Learner workflow stops silently failing. Recovers `winner_history.json` updates that have been blank during geo-block windows.

---

## Summary

| # | Change | Risk | Est. PnL impact | Files |
|---|---|---|---|---|
| 1 | quan inverse SANDBOX | medium | +50 pts/Q | 3 |
| 2 | TV account reroute | low | stops bleed | operational |
| 3 | Block kimi_signal_tracking | low | +53 pts | 1 |
| 4 | ALPHA ENGINE merge fix | medium | trend-track recovery | 1 |
| 5 | Node 20→24 | low | future-proof | 534 lines |
| 6 | Binance fallback chain | medium | hindsight recovery | 1 |

**Total estimated +PnL: ~+103 pts/quarter** (plus quality-of-life from #4, #5, #6).

---

## Open questions for review

1. **#1 quan inverse:** Should we deploy native (mathematical inverse of every signal) OR hybrid (M_HYBRID with per-symbol overrides)? The MD recommends hybrid; mathematical-pure inverse is simpler but less optimized.
2. **#2 TV account:** Is there a router file I'm missing, or is this entirely manual via the tv-paper-trade skill?
3. **#3 kimi_signal_tracking:** Should we attempt to FIX the upstream Kimi ingest first (option B in the investigation MD), or block immediately (option A)?
4. **#4 strategy_performance.json:** What's the right pruning policy? 30 days no-activity? Last 200 strategies by trade count? No pruning?
5. **#5 Node:** Option A (opt-in env var) per-workflow OR Option B (bulk version bump)? The opt-in approach is faster but creates 534 cleanup tasks for later.
6. **#6 fallback chain:** Should we add a circuit-breaker around the new APIs (don't retry KuCoin if it failed in last 5 min)? Adds complexity but prevents cascade timeouts.
