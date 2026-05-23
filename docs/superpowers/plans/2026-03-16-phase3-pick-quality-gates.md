# Phase 3: Pick Quality Gates — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop bad picks at the gate. Fix 6 root causes killing WR: KIMI leakage, unvalidated systems, low consensus threshold, stale pick contamination, missing beta gate, and no funding rate filter.

**Architecture:** All changes in `cross_aggregation/aggregator.py` and `cross_aggregation/system_trust_registry.py`. No new modules — just tightening the existing consensus pipeline. Estimated WR impact: +7-12% from filtering alone.

**Tech Stack:** Python. No new dependencies.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `cross_aggregation/aggregator.py` | MODIFY | Beta gate, KIMI enforcement, unvalidated system gate, stale purge |
| `cross_aggregation/system_trust_registry.py` | MODIFY | Register unknown systems, enforce dynamic tiers |
| `updates/index.html` | MODIFY | Document quality gate changes |

---

## Task 1: Beta Gate Filter in Aggregator

**Files:**
- Modify: `cross_aggregation/aggregator.py`

The single highest-impact change: discard low-confluence picks BEFORE they reach Discord/dashboard.

- [ ] **Step 1: Find where aggregated picks are finalized**

After `aggregated.append(unified)` (~line 1259), there's likely a loop that sends picks to Discord or writes output. Find it.

- [ ] **Step 2: Add beta gate filter after the aggregation loop**

After the aggregation loop builds the `aggregated` list, filter it:

```python
    # Phase 3: Beta gate — remove low-confluence picks
    if _HAS_BETA_SCORER:
        pre_filter_count = len(aggregated)
        aggregated = [p for p in aggregated if p.get("beta_score") is None or p.get("beta_score", 0) >= 40]
        filtered_count = pre_filter_count - len(aggregated)
        if filtered_count > 0:
            print(f"[BETA GATE] Filtered {filtered_count}/{pre_filter_count} picks with beta_score < 40", file=sys.stderr)
```

Note: Using 40 (not 50) as initial gate to avoid being too aggressive. Can tighten later.

- [ ] **Step 3: Verify and commit**

```bash
python -c "import py_compile; py_compile.compile('cross_aggregation/aggregator.py', doraise=True)"
git add cross_aggregation/aggregator.py
git commit -m "feat: add beta gate filter — discard picks with beta_score < 40"
```

---

## Task 2: Enforce KIMI as Confirmer-Only

**Files:**
- Modify: `cross_aggregation/aggregator.py`

KIMI (36.7% WR, -219% PnL) is marked CONFIRMER_ONLY but still appears as sole source in picks.

- [ ] **Step 1: Find the CONFIRMER_ONLY enforcement logic**

Search for `CONFIRMER` or `confirmer` in aggregator.py. Find where confirmer-only systems are handled during consensus building.

- [ ] **Step 2: Add strict enforcement**

In the consensus building loop, where systems vote on direction, add:

```python
        # Strict CONFIRMER_ONLY enforcement: skip system entirely if it's the only non-confirmer
        confirmer_only_systems = {"kimi"}  # systems that can only confirm, never lead
        non_confirmer_longs = [s for s in long_systems if s not in confirmer_only_systems]
        non_confirmer_shorts = [s for s in short_systems if s not in confirmer_only_systems]

        # If all systems on the winning side are confirmer-only, skip this symbol entirely
        if chosen_dir == "LONG" and len(non_confirmer_longs) < 1:
            continue  # no real system supports this direction
        if chosen_dir == "SHORT" and len(non_confirmer_shorts) < 1:
            continue
```

Also add to the vote weighting: confirmer-only systems get 0.0 vote weight (can't trigger consensus):

```python
        # Confirmer-only systems get 0 vote weight for triggering consensus
        for sys_name in confirmer_only_systems:
            if sys_name in system_votes:
                system_votes[sys_name]["vote_weight"] = 0.0
```

- [ ] **Step 3: Verify and commit**

```bash
python -c "import py_compile; py_compile.compile('cross_aggregation/aggregator.py', doraise=True)"
git add cross_aggregation/aggregator.py
git commit -m "fix: enforce KIMI confirmer-only — cannot lead consensus, 0 vote weight"
```

---

## Task 3: Gate Unvalidated Systems

**Files:**
- Modify: `cross_aggregation/system_trust_registry.py`
- Modify: `cross_aggregation/aggregator.py`

`rapid_fire` (230 picks), `incubator_gainer` (198 picks), `claude_gainer_st` (25 picks) have ZERO performance history but are contributing to consensus at full vote weight.

- [ ] **Step 1: Add unknown systems to registry as UNTRUSTED**

In `system_trust_registry.py`, find the system registry dict. Add:

```python
    # Unvalidated systems — gate at UNTRUSTED until proven
    "rapid_fire": {"tier": "UNTRUSTED", "forward_wr": None, "total_pnl": 0, "closed_trades": 0,
                   "notes": "New system, no performance data. Auto-UNTRUSTED until 10+ closed trades."},
    "incubator_gainer": {"tier": "UNTRUSTED", "forward_wr": None, "total_pnl": 0, "closed_trades": 0,
                         "notes": "Incubator system, not yet validated."},
    "claude_gainer_st": {"tier": "UNTRUSTED", "forward_wr": None, "total_pnl": 0, "closed_trades": 0,
                         "notes": "Short-term gainer, not yet validated."},
```

- [ ] **Step 2: Add minimum-trade gate in aggregator**

In aggregator.py, in the system processing loop, add a gate for systems with < 10 closed trades:

```python
        # Phase 3: Minimum trade gate — systems with <10 closed trades get halved vote weight
        sys_trades = system_info.get("closed_trades", 0)
        if sys_trades < 10:
            vote_weight *= 0.3  # heavily discount unproven systems
```

- [ ] **Step 3: Verify and commit**

```bash
python -c "import py_compile; py_compile.compile('cross_aggregation/system_trust_registry.py', doraise=True)"
python -c "import py_compile; py_compile.compile('cross_aggregation/aggregator.py', doraise=True)"
git add cross_aggregation/system_trust_registry.py cross_aggregation/aggregator.py
git commit -m "feat: gate unvalidated systems — UNTRUSTED tier + 0.3x vote weight for <10 trades"
```

---

## Task 4: Purge Stale Picks from Banned Systems

**Files:**
- Modify: `cross_aggregation/aggregator.py`

`predictions` and `multi_asset` picks are still in consensus_outcomes from before they were banned.

- [ ] **Step 1: Add banned system purge at start of aggregation**

At the beginning of the aggregation function, after loading picks from all systems, add:

```python
    # Phase 3: Purge picks from banned systems
    BANNED_SYSTEMS = {"ml_bg_a", "ml_bg_b", "ml_bg_c", "ml_bg_ensemble",
                      "multi_asset", "multi_asset_institutional", "crypto_winners",
                      "predictions"}
    for symbol in list(symbol_picks.keys()):
        symbol_picks[symbol] = [p for p in symbol_picks[symbol]
                                 if p.get("source_system", "") not in BANNED_SYSTEMS]
        if not symbol_picks[symbol]:
            del symbol_picks[symbol]
```

- [ ] **Step 2: Verify and commit**

```bash
python -c "import py_compile; py_compile.compile('cross_aggregation/aggregator.py', doraise=True)"
git add cross_aggregation/aggregator.py
git commit -m "fix: purge stale picks from banned systems at aggregation start"
```

---

## Task 5: Add Funding Rate Filter for Crypto

**Files:**
- Modify: `cross_aggregation/beta_confluence_scorer.py`

Use existing `coinalyze_client.py` funding rate data to penalize longs when funding is extreme.

- [ ] **Step 1: Add funding rate to market_context**

In `build_market_context()`, after the order book block, add:

```python
        # Funding rate (from Binance)
        try:
            import requests as _req
            r = _req.get("https://fapi.binance.com/fapi/v1/premiumIndex",
                         params={"symbol": "BTCUSDT"}, timeout=5)
            if r.status_code == 200:
                funding = float(r.json().get("lastFundingRate", 0))
                ctx["btc_funding_rate"] = funding
            else:
                ctx["btc_funding_rate"] = 0
        except Exception:
            ctx["btc_funding_rate"] = 0
```

Also add `"btc_funding_rate": 0` to the default ctx dict.

- [ ] **Step 2: Add funding rate penalty to _score_structure()**

In `_score_structure()`, after the volatility regime scoring, add:

```python
        # Funding rate penalty for crypto (0 to -3 pts)
        if is_crypto:
            funding = ctx.get("btc_funding_rate", 0)
            if is_long and funding > 0.001:  # >0.1% = overleveraged longs
                score -= 3
            elif is_long and funding > 0.0005:  # >0.05%
                score -= 1
            elif not is_long and funding < -0.001:  # overleveraged shorts
                score -= 3
            elif not is_long and funding < -0.0005:
                score -= 1
```

- [ ] **Step 3: Verify and commit**

```bash
python -c "import py_compile; py_compile.compile('cross_aggregation/beta_confluence_scorer.py', doraise=True)"
git add cross_aggregation/beta_confluence_scorer.py
git commit -m "feat: add BTC funding rate to market context + penalty in structure pillar"
```

---

## Task 6: Dynamic Beta Threshold (Percentile-Based)

**Files:**
- Modify: `cross_aggregation/aggregator.py`

Instead of hard 70 threshold, use the 80th percentile of current run's beta scores.

- [ ] **Step 1: After beta scoring all picks, compute percentile**

After the aggregation loop and beta gate filter, add:

```python
    # Phase 3: Dynamic beta threshold — top 20% of picks are "qualified"
    beta_scores = [p["beta_score"] for p in aggregated if p.get("beta_score") is not None]
    if len(beta_scores) >= 5:
        beta_scores_sorted = sorted(beta_scores)
        percentile_80 = beta_scores_sorted[int(len(beta_scores_sorted) * 0.8)]
        dynamic_threshold = max(60, min(80, percentile_80))  # clamp between 60-80
        for p in aggregated:
            if p.get("beta_score") is not None:
                p["beta_qualified"] = p["beta_score"] >= dynamic_threshold
        print(f"[BETA] Dynamic threshold: {dynamic_threshold:.1f} (80th pctl of {len(beta_scores)} picks)", file=sys.stderr)
```

- [ ] **Step 2: Verify and commit**

```bash
python -c "import py_compile; py_compile.compile('cross_aggregation/aggregator.py', doraise=True)"
git add cross_aggregation/aggregator.py
git commit -m "feat: dynamic beta threshold — 80th percentile, clamped 60-80"
```

---

## Task 7: Update updates page

**Files:**
- Modify: `updates/index.html`

- [ ] **Step 1: Insert Phase 3 entry at top of March section**

```html
<div class="update-entry" style="--dot-color: #ef4444;" data-tags="cross-aggregation,audit-dashboard" data-category="trading" data-types="fix,improvement">
  <div class="update-date">Mar 16, 2026</div>
  <div class="update-title">
    <span class="badge badge-feature">Critical</span>
    Phase 3: Quality Gates — Beta Filter, KIMI Lockout, Funding Rate
  </div>
  <div class="update-body">
    <h4>Pick Quality Gates (est. +7-12% WR)</h4>
    <ul>
      <li><strong>Beta gate filter:</strong> Picks with beta_score &lt; 40 are now discarded before reaching Discord/dashboard</li>
      <li><strong>KIMI lockout:</strong> Strict confirmer-only enforcement — KIMI can never lead consensus (0 vote weight), requires 1+ non-KIMI system</li>
      <li><strong>Unvalidated system gate:</strong> Systems with &lt;10 closed trades get 0.3x vote weight (rapid_fire, incubator_gainer, claude_gainer_st)</li>
      <li><strong>Banned system purge:</strong> Stale picks from banned systems (predictions, multi_asset, etc.) removed at aggregation start</li>
      <li><strong>BTC funding rate:</strong> Penalizes longs when funding &gt;0.1% (overleveraged market), penalizes shorts when funding &lt;-0.1%</li>
      <li><strong>Dynamic beta threshold:</strong> 80th percentile of current run (clamped 60-80) replaces hard 70 cutoff</li>
    </ul>

    <h4>Root Causes Fixed</h4>
    <table>
      <tr><th>Issue</th><th>Impact</th><th>Fix</th></tr>
      <tr><td>KIMI solo picks</td><td>36.7% WR contaminating consensus</td><td>0 vote weight, can't lead</td></tr>
      <tr><td>Unvalidated systems</td><td>453 picks with zero history</td><td>UNTRUSTED tier, 0.3x votes</td></tr>
      <tr><td>Banned system leakage</td><td>17 stale picks from blocked systems</td><td>Purge at aggregation start</td></tr>
      <tr><td>No quality floor</td><td>Low-confluence picks published</td><td>Beta gate at 40/100</td></tr>
    </table>

    <h4>Affected Dashboards</h4>
    <ul>
      <li><a href="https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/monitor/">Cross-Aggregation Monitor</a> — cleaner picks, fewer false signals</li>
    </ul>
  </div>
</div>
```

- [ ] **Step 2: Commit**

```bash
git add updates/index.html
git commit -m "feat: add Phase 3 update entry — quality gates, KIMI lockout, funding rate"
```
