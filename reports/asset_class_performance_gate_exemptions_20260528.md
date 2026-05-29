# Asset-Class Performance Review + Safety-Gate Exemption Analysis

**Date:** 2026-05-28 ~21:30 UTC  
**Analyst:** Cursor Composer  
**Sources (live, curl-verified):**
- `https://findtorontoevents.ca/audit/data/dashboard_data.json` — `generated_at` 2026-05-28T20:26:51Z (~1h fresh)
- `https://findtorontoevents.ca/audit/data/pf_registry.json` — `generated_utc` 2026-05-28T20:26:50Z
- `https://findtorontoevents.ca/audit/data/money_ready_verdict.json` — `generated_at` 2026-05-28T07:41:15Z (**13h stale** — use embedded `money_ready_verdicts` in dashboard for gates)
- `https://findtorontoevents.ca/audit/data/pick_summary_stats_48h.json` — 2026-05-28T05:26:56Z
- `https://findtorontoevents.ca/audit/data/pick_summary_stats_2w.json` — 14d window
- Code: `audit_trail/quality_gates.py`, `docs/PERFORMANCE_CHARTER.md` §2

**Charter tiers (verdict-grade n≥100 for classification):** T2 = PF≥1.5, WR≥50%, MDD≤20%, n≥100.

---

## Executive summary

| Class | Verdict n | WR | PF (policy-clean-net) | Charter tier | `sizing_allowed` | Gate state |
|-------|----------:|---:|----------------------:|--------------|------------------|------------|
| CRYPTO | 522 | 35.4% | 0.86 | **SUB_T2** | False | MONITORING |
| EQUITY | 21 | 28.6% | 0.05 | **INSUFF-N** | False | MONITORING |
| FOREX | 16 | 25.0% | 0.84 | **INSUFF-N** | False | **DISABLED** |
| COMMODITY | 5 | 40.0% | 2.20 | **INSUFF-N** | False | MONITORING |
| ETF | 3 | 33.3% | 0.19 | **INSUFF-N** | False | MONITORING |
| FUTURES | 11 | 9.1% | 0.48 | **INSUFF-N** | False | MONITORING |
| BOND | 0 | — | — | **INSUFF-N** | False | MONITORING |

**Money-ready shortlist:** `summary.money_ready: []` (standalone JSON) — **no class is money-ready.**

**Exemption verdict:** **0 asset classes** merit a **sizing / safety-gate exemption** for real money. **2 code-level exemptions** should be **revoked or narrowed** (COMMODITY FV exempt for falsified COT sources). **3 exemptions** are **defensible only as admission-calibration** (BOND/ETF elite_grade; narrow COMMODITY source list), not as proof of edge.

---

## 1. Per-class performance + improvement areas

### CRYPTO (CRYPTO | n=522 | 90d+ledger)

| Metric | Value | Source |
|--------|------:|--------|
| WR | 35.4% | `performance.asset_class_health` |
| PF | 0.86 | policy-clean-net |
| Expectancy | −0.012 | `money_ready_verdicts.CRYPTO` |
| DSR | 0.0 (fail) | embedded verdict |
| PBO | 0.21 (pass) | embedded verdict |
| 48h closed | **0** | `pick_summary_stats_48h` |
| 14d PF | 0.67 | `pick_summary_stats_2w` |
| Smart picks live | **0** | `smart_picks_by_asset.CRYPTO` |

**Improvements (ranked):**
1. **P0 — Recency collapse:** 48h zero closes while 522 all-time resolved → do not cite 78.9% nav surfaces; enforce pick_funnel DISPUTED banner before any promo.
2. **P0 — Sub-T2 PF/WR:** Mutate-before-kill per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`; target WR≥50%, PF≥1.5 on **policy-clean** cohort only.
3. **P1 — Resolver hygiene:** EXPIRED→WON mislabels + duplicate signal-ts groups (per funnel audit) inflate historical WR.
4. **P1 — Negative expectancy** with n_ok=True → gates correctly block sizing; no exemption warranted.

**Exemption request?** **DENIED** — fails WR, PF, DSR, expectancy, MDD/CVaR gates.

---

### EQUITY (EQUITY | n=21 | ledger)

| Metric | Value | Notes |
|--------|------:|-------|
| WR / PF | 28.6% / **0.05** | Catastrophic PF on clean net |
| 48h | n_closed=126, pf≈0.09 | **100% single_source via AlphaEngine** — not diversified edge |
| 14d raw | n=8435, pf=5.39 | **Not policy-clean** — do not use for exemptions |
| Circuit 30d WR | 44.9% (n=89) | Disagrees with verdict n=21 → different windows/filters |

**Improvements:**
1. **P0 — Insufficient clean n:** Need ≥100 resolved policy-clean before any Tier discussion.
2. **P1 — Source concentration:** 48h panel is one emitter; prove multi-source replication before trust-tier relief.
3. **P2 — Scoring calibration:** `ASSET_CLASS_SMART_THRESHOLDS.EQUITY.min_score=40` is intentional; pair with `long_deadzone_exempt_equity_forward_proven` only when forward-proven helper returns true (see tests).

**Exemption request?** **DENIED** for sizing. **CONDITIONAL** for `long_deadzone_exempt_equity_forward_proven` score penalty only — per-pick, test-gated.

---

### FOREX (FOREX | n=16 | ledger)

| Metric | Value | Notes |
|--------|------:|-------|
| WR / PF | 25.0% / 0.84 | Below WR floor |
| `mdd_ok` / `cvar_ok` | **True** | Tail risk pass on tiny n |
| `gate_state` | **DISABLED** | readiness.by_class |
| 48h | n=23, pf=1.47 | 100% AlphaEngine concentration |
| Raw `by_asset_class` | closed=90, pf=0.98 | **Not verdict n** (includes noise) |

**Improvements:**
1. **P0 — Keep class DISABLED** until clean n≥100 and WR≥50% on FwdWR-gated cohort (PR #191 pattern).
2. **P1 — Do not treat mdd_ok=True as exemption** — partial gate pass on n=16 is not edge proof.
3. **P1 — Re-block destructive pairs** already in `BLOCKED_ASSET_STRATEGY_PAIRS` (e.g. `myfxbook_retail_contrarian`).

**Exemption request?** **DENIED** — mdd/CVaR pass is necessary but not sufficient; WR/expectancy/dsr fail.

---

### COMMODITY (COMMODITY | n=5 | ledger)

| Metric | Value | Notes |
|--------|------:|-------|
| WR / PF | 40.0% / **2.20** | Looks strong but **n=5** |
| Expectancy | +0.015 (ok) | embedded verdict |
| 30d circuit WR | **9.1%** (n=11) | Conflicts with headline 40% — recency worse |
| COT falsification | 6.33× over-emission | `cot_paper_pilot` / template disclaimer |

**Improvements:**
1. **P0 — Revoke FV exemption** for `multi_asset_cot` + `multi_asset_copytrader` (see §3).
2. **P1 — Accumulate clean n≥100** before Tier-2 promotion; current PF is not statistically supported.
3. **P2 — Keep narrow elite_grade exempt** only for `commodity_cot_contrarian` + `cta_replicator` (aligned with 2026-05-16 swarm).

**Exemption request?** **DENIED** for sizing (n≪100). **PARTIAL** for admission-only elite_grade on **two named sources** only.

---

### ETF / BOND / FUTURES / PENNY

| Class | n | PF | Improvement focus |
|-------|--:|---:|-------------------|
| ETF | 3 | 0.19 | Expand emitter; `_ETF_FV_EXEMPT` cold-start must expire when n≥20 |
| BOND | 0–2 | ~0 | Hold; elite_grade exempt is scoring-only |
| FUTURES | 11 | 0.48 | WR 9% — no exemption; `cta_replicator` only commodity-style carve-out |
| PENNY | 1 | 0.0 | Block until n≥30 |

---

## 2. Quality-gate inventory (safety vs calibration)

| Gate / exemption | Location | Purpose | Sizing impact |
|------------------|----------|---------|---------------|
| `passes_active_gate` | quality_gates.py | Hard reject bad geometry / blocks | Blocks bad picks |
| `passes_smart_gate` | quality_gates.py | Score + FwdWR + forward_validated | Smart Picks admission |
| `clone_safety_mode=EXEMPT_FROM_SAFETY_GATES` | ~7587 | **Hard reject** (defense in depth) | Cannot bypass |
| BOND/ETF `elite_grade` F/D exempt | ~7663 | Scoring calibration | Admission only |
| COMMODITY/FUTURES source elite exempt | ~7669 | `commodity_cot_contrarian`, `cta_replicator` only | Admission only |
| `_COMMODITY_FV_EXEMPT` | ~9004 | Skip `forward_validated` | **High risk** if sources falsified |
| `_ETF_FV_EXEMPT` / `_EQUITY_FV_EXEMPT` | ~9011 | Cold-start trap | Time-boxed admission |
| `long_deadzone_exempt_equity_forward_proven` | ~4665 | Score penalty relief | Per-pick proof required |
| `NON_CRYPTO_TRUST_EXEMPT_CLASSES` | ~1336 | Trust tier (env-gated) | Monitor abuse |
| `ASSET_CLASS_SMART_THRESHOLDS` | ~488 | Per-class min_score/FWR | COMMODITY min_trades=0 is loose |

---

## 3. Exemption claims — prove or deny

### DENY (no safety-gate exemption for real money)

| Claim | Why denied | Evidence |
|-------|------------|----------|
| CRYPTO sizing despite PF 0.86 | Sub-T2, DSR=0, negative expectancy | `money_ready_verdicts`, pf_registry |
| COMMODITY PF 2.2 → go live | n=5 ≪ charter n≥100 | pf_registry policy_clean_net |
| FOREX `mdd_ok=True` → relax WR | Partial pass; WR 25%, n=16 | embedded verdict |
| EQUITY 14d pf=5.39 | Not policy-clean; source concentration | pick_summary_stats_2w + 48h caveats |
| Any `EXEMPT_FROM_SAFETY_GATES` pick | Explicit hard-reject | quality_gates.py:7587, tests |

### REVOKE (code contradicts own falsification notes)

| Exemption | Action | Evidence |
|-----------|--------|----------|
| `_COMMODITY_FV_EXEMPT` includes `multi_asset_cot`, `multi_asset_copytrader` | **Remove from frozenset** | Lines 7665–7667 document falsified PF/WR; lines 9004–9006 still exempt FV |

**Proposed patch:**
```python
_COMMODITY_FV_EXEMPT = frozenset({
    "commodity_cot_contrarian",  # CFTC-backed; kept post-dedup review
    # REMOVED 2026-05-28: multi_asset_cot, multi_asset_copytrader (6.33x over-emission falsified)
})
```

### CONDITIONAL KEEP (admission calibration only — not sizing)

| Exemption | Conditions to remain | Proof required |
|-----------|---------------------|----------------|
| BOND/ETF elite_grade F/D | Until non-crypto score calibration ships | TLT/LQD live PF with n≥30 post-calibration |
| `commodity_cot_contrarian` + `cta_replicator` elite_grade | Per-source n≥30 clean closed | Export CSV + `tools/mutation_analysis.py` |
| `_ETF_FV_EXEMPT` / `stocksunify2` | Auto-expire at first 20 clean closes OR 2026-08-18 | Dashboard counter in readiness |
| `long_deadzone_exempt_equity_forward_proven` | Only when helper returns True | Existing unit tests |

### CANNOT PROVE (insufficient data — do not grant)

- **Hot-streak exemption** (incidents feed backlog) — no implementation; no bounded audit trail.
- **Pair exception carve-out** (`should_pair_exception_pass`) — case-by-case; requires per-pair closed CSV + DSR≥0.95.

---

## 4. Best-possible actions (P0–P3)

| Pri | Action | Class | Expected impact |
|-----|--------|-------|-----------------|
| P0 | Remove falsified sources from `_COMMODITY_FV_EXEMPT` | COMMODITY | Stops unvalidated smart-pick admission |
| P0 | Refresh `money_ready_verdict.json` on dashboard cron | ALL | Removes 13h stale standalone vs embed |
| P1 | CRYPTO: 14d/48h panel on audit index (link pick_funnel) | CRYPTO | Prevents sizing on stale WR |
| P1 | FOREX: keep DISABLED until clean n≥100 | FOREX | Prevents false tail-risk narrative |
| P1 | EQUITY: cap AlphaEngine-only 48h burst from tier messaging | EQUITY | Stops misleading pf=5.39 citations |
| P2 | COMMODITY: pilot only `commodity_cot_contrarian` with n≥30 proof | COMMODITY | Path to T3 paper |
| P2 | ETF: sunset `_ETF_FV_EXEMPT` when sector rotation has 20 closes | ETF | Ends cold-start bypass |
| P3 | Implement bounded hot-streak exemption spec from incidents feed | ALL | Future — needs contract |

---

## 5. Verifiable commands

```bash
# Freshness
curl -sS 'https://findtorontoevents.ca/audit/data/dashboard_data.json' | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['generated_at'])"

# Policy-clean per class
curl -sS 'https://findtorontoevents.ca/audit/data/pf_registry.json' | python3 -c "
import sys,json
for r in json.load(sys.stdin)['by_asset_class_policy_clean_net']:
    print(r['asset_class'], r['n'], r['win_rate_pct'], r['profit_factor'])"

# Gate failures
curl -sS 'https://findtorontoevents.ca/audit/data/dashboard_data.json' | python3 -c "
import sys,json
d=json.load(sys.stdin)
for c,v in d.get('money_ready_verdicts',{}).items():
    bad=[k for k,x in v.items() if k.endswith('_ok') and x is False]
    if bad: print(c, bad[:6])
"
```

---

---

## 6. Peer review (swarm consensus-3)

**Tool:** `/PeerReviewSwarmOptions` → `tools/swarm/swarm_run.py --preset consensus-3`  
**Output:** `swarm_runs/asset-class-exemptions-20260528T210955Z/`  
**Engines:** deepseek (valid JSON), kilo (non-JSON — ignored)

| Claim | DeepSeek status |
|-------|-----------------|
| No class merits sizing exemption | **confirmed** |
| REVOKE multi_asset_cot/copytrader FV exempt | **confirmed** (live code bug) |
| DENY FOREX mdd-only exemption | **confirmed** |
| BOND/ETF elite_grade = calibration only | **confirmed** |
| COMMODITY PF 2.2 / n=5 not for promotion | **confirmed** |

**Swarm verdict:** `needs_changes` (high confidence) — agrees with exemption table.  
**P0 action taken in-repo:** `_COMMODITY_FV_EXEMPT` narrowed to `commodity_cot_contrarian` only (`quality_gates.py`).

**Recommended follow-up P0s (not yet coded):**
- Automated test: frozenset must not contain sources named in falsification comments
- Sync `money_ready_verdict.json` generation with dashboard hourly build
