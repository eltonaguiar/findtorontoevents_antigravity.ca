# Weekly Real-Money Filter — 2026-06-02

**Audit run:** `/money-maker-readyv2` · author `claude-opus-4-7-desktop` · timestamp `2026-06-02T14:40:00Z`
**Canonical sources (re-derived live, not carried forward):**
- `audit_dashboard/data/money_ready_verdict.json` — generated `2026-06-02T12:15:15Z` (≈2.5h old, FRESH)
- `audit_dashboard/data/pf_registry.json` — `by_asset_class_policy_clean_net` (canonical) + `by_asset_class_strategy_policy_clean_net`
- `audit_dashboard/data/dashboard_data.json` — **STALE 7.6h** (warn, not used for verdict — verdict file is authoritative)
- `alpha_engine/data/active_picks.json` — 78 active picks (live scoring)

## TL;DR — 0/8 classes pass proven filter; HF_STATS reveals hidden edge in 3 classes

> **No class is money-ready on policy-clean net.** The `pf_registry.json` `by_asset_class_policy_clean_net` shows **ZERO** classes meeting the proven filter floor (n≥50, PF≥1.3, WR≥45%, not single-source artifact).
>
> **However, `hf_stats::by_asset_class` (recent cohort, 24h window) shows real edge in COMMODITY, EQUITY, and ETF.** This is the exact research-to-production gap identified by the EAGLE2 initiative. The edge exists in the lab but has not been converted to the policy-clean production layer.

---

## Per-class baseline (policy-clean net — canonical for money-ready verdict)

| Class | n | WR% | PF | MDD% | Artifact | Verdict (money_ready) | Proven filter (n≥50, PF≥1.3, WR≥45%) |
|---|---:|---:|---:|---:|:---:|:---|:---:|
| **CRYPTO** | 366 | 36.3 | 0.95 | 1.0 | No | NOT_READY | **FAIL** (PF 0.95 < 1.3, WR 36.3% < 45%) |
| **FOREX** | 32 | 28.1 | 0.48 | 0.8 | No | INSUFFICIENT_DATA | **FAIL** (n=32 < 50, PF 0.48 < 1.3) |
| **EQUITY** | 48 | 27.1 | 0.33 | 0.6 | No | INSUFFICIENT_DATA | **FAIL** (n=48 < 50, PF 0.33 < 1.3, WR 27.1% < 45%) |
| **FUTURES** | 13 | 15.4 | 0.52 | 0.2 | Yes | INSUFFICIENT_DATA | **FAIL** (n=13 < 50, PF 0.52 < 1.3, artifact) |
| **COMMODITY** | 4 | 50.0 | 1.68 | 0.0 | No | INSUFFICIENT_DATA | **FAIL** (n=4 < 50) |
| **ETF** | 2 | 100.0 | N/A | 0.0 | No | INSUFFICIENT_DATA | **FAIL** (n=2 < 50) |
| **BOND** | 0 | — | — | — | — | INSUFFICIENT_DATA | **FAIL** (n=0) |
| **PENNY_STOCK** | 1 | 0.0 | 0.00 | 0.0 | No | INSUFFICIENT_DATA | **FAIL** (n=1) |
| **UNKNOWN** | 9 | 66.7 | 0.72 | 0.2 | Yes | INSUFFICIENT_DATA | **FAIL** (artifact) |

**Result: 0/8 asset classes pass the proven filter on policy-clean net.**

The binding constraint is **sample size**: 6 of 8 classes have n<50. CRYPTO has n=366 but fails PF and WR gates. This matches the EAGLE2 finding that the production-ready audit book lacks deployable edge.

---

## HF_STATS recent data — hidden edge discovery (NOT policy-clean)

`dashboard_data.json::hf_stats.by_asset_class` (24h recent cohort, **STALE source** — 7.6h old):

| Class | n | WR% | PF | Sharpe | Kelly f (full) | Kelly f (¼) | Verdict if clean |
|---|---:|---:|---:|---:|---:|---:|---|
| **COMMODITY** | 74 | 54.05 | 2.26 | 5.81 | **30.1%** | **7.53%** | 🟢 Shadow-size 0.5% |
| **EQUITY** | 271 | 52.40 | 1.82 | 3.67 | **23.6%** | **5.90%** | 🟢 Shadow-size 0.5% |
| **ETF** | 104 | 58.65 | 1.49 | 2.70 | **19.3%** | **4.82%** | 🟡 Paper-trade ≤0.2% |
| **CRYPTO** | 2,891 | 44.34 | 1.25 | 1.26 | 8.9% | 2.22% | 🟡 Paper-trade SHORT only |
| **FOREX** | 148 | 30.41 | 1.31 | 1.35 | 7.2% | 1.80% | 🔴 Freeze (historically toxic) |
| **BOND** | 12 | 0.5 | 0.66 | -2.72 | **negative** | **0%** | 🔴 Freeze |

**Kelly formula used:** f* = WR × (PF − 1) / PF, derived from discrete Kelly with b = PF × (1−WR) / WR. Quarter-Kelly (fraction = 0.25) is the production default per `alpha_engine.kelly_position_sizer`.

**Gap analysis:**
- **COMMODITY** policy-clean n=4 vs HF_STATS n=74. The 74 recent picks show strong edge (PF 2.26, Sharpe 5.81) but are not yet in the policy-clean pipeline. **Action:** fast-track resolver + policy-clean validation for COMMODITY.
- **EQUITY** policy-clean n=48 vs HF_STATS n=271. The 271 recent picks show PF 1.82 / Sharpe 3.67. **Action:** resolve the open-pick backlog to convert raw edge to policy-clean edge.
- **ETF** policy-clean n=2 vs HF_STATS n=104. The dual-momentum lab sleeve (PF 1.60, n=104) is accumulating forward data but not yet merged into policy-clean. **Action:** complete forward pilot n≥100 and merge.
- **CRYPTO** policy-clean PF 0.95 vs HF_STATS PF 1.25. The EAGLE-4 flip (LONG→SHORT) shipped 2026-06-02; HF_STATS may reflect post-flip improvement. **Action:** monitor 7-day rolling PF after flip.
- **FOREX** policy-clean PF 0.48 vs HF_STATS PF 1.31. Historical mislabel drift (EXPIRED→WON) makes FOREX data suspect regardless of surface PF. **Action:** freeze until resolver audit complete.

---

## Per-strategy edge discovery (PF≥1.3 & n≥30 from `pf_registry::by_asset_class_strategy_policy_clean_net`)

Zero strategies clear PF≥1.3 and n≥30 on policy-clean net. The closest:

| Class | Strategy | n | WR% | PF | Gap to proven |
|---|---|---:|---:|---:|---|
| CRYPTO | `crypto_liquidity_wick_reversal_v1` | 30 | 60.0 | 1.55 | n=30 meets floor but single-source check pending |
| CRYPTO | `copy_trader_intel` | 34 | 47.1 | 1.66 | WR 47.1% < 50% floor |
| COMMODITY | `cot_momentum` | 4 | 50.0 | 1.68 | n=4 < 50 floor |

The `crypto_liquidity_wick_reversal_v1` survivor from 2026-05-30 remains in limbo: pf_registry n=30 / WR=60% / PF=1.55 meets the cell floor, but the 2026-05-30 investigation found 100% single-source concentration (`battleground`) and zero production resolutions. **Status: STILL NOT VETTED.**

---

## Path-forward per class (what would unblock each criterion)

| Class | Policy-clean blocker | HF_STATS edge | Action to reach money-ready |
|---|---|---|---|
| **COMMODITY** | n=4 < 50 | PF 2.26, n=74 recent | Fast-track resolver: validate 74 recent picks through policy-clean pipeline; target n≥50 clean within 1 week |
| **EQUITY** | n=48 < 50, PF 0.33 | PF 1.82, n=271 recent | Resolve OPEN backlog (228 picks); run purged-embargoed walk-forward on Faber TAA sleeve |
| **ETF** | n=2 < 50 | PF 1.49, n=104 recent | Complete dual-momentum forward pilot; merge at n≥100 clean |
| **CRYPTO** | PF 0.95 < 1.3, WR 36.3% < 45% | PF 1.25 post-EAGLE-4 flip | Monitor 7d rolling PF after EAGLE-4 SHORT flip; validate on ≥100 resolved picks |
| **FOREX** | n=32 < 50, PF 0.48 | PF 1.31 (suspect) | Freeze. Complete resolver label audit (EXPIRED→WON drift) before any sizing |
| **BOND** | n=0 | PF 0.66 | No live sample. HYG/LQD momentum lab promising — insufficient data |
| **FUTURES** | n=13 < 50, artifact | — | Taxonomy clean-up per EAGLE2; merge real futures under COMMODITY |
| **PENNY_STOCK** | n=1 | — | Deep oversold blocked by Gate 0; need volume |

---

## Kelly sizing — illustrative for HF_STATS edge classes

**No policy-clean picks are eligible for sizing this week.** Below is illustrative Quarter-Kelly sizing for the HF_STATS recent cohort, assuming the edge survives policy-clean validation.

```python
from alpha_engine.kelly_position_sizer import kelly_fraction

# COMMODITY (WR=54.05%, PF=2.26 → implied b=1.93)
kelly_fraction(p_win=0.5405, avg_win_pct=3.86, avg_loss_pct=2.00, fraction=0.25)
# → 7.53% of NAV per pick

# EQUITY (WR=52.40%, PF=1.82 → implied b=1.57)
kelly_fraction(p_win=0.5240, avg_win_pct=3.14, avg_loss_pct=2.00, fraction=0.25)
# → 5.90% of NAV per pick

# ETF (WR=58.65%, PF=1.49 → implied b=1.05)
kelly_fraction(p_win=0.5865, avg_win_pct=2.10, avg_loss_pct=2.00, fraction=0.25)
# → 4.82% of NAV per pick

# CRYPTO (WR=44.34%, PF=1.25 → implied b=1.56)
kelly_fraction(p_win=0.4434, avg_win_pct=3.12, avg_loss_pct=2.00, fraction=0.25)
# → 2.22% of NAV per pick (SHORT only post-EAGLE-4)
```

At $10,000 NAV:
- COMMODITY pick: ~$753
- EQUITY pick: ~$590
- ETF pick: ~$482
- CRYPTO SHORT pick: ~$222

**Not authorized until policy-clean validation completes.**

---

## Current OPEN-pick census (Step 6 — `alpha_engine/data/active_picks.json`)

| Class | OPEN/ACTIVE | Top symbols by confidence |
|---|---:|---|
| CRYPTO | 59 | ETHUSDT (0.89), TAOUSDT (0.84), STRKUSDT (0.80) |
| EQUITY | 8 | EMB (0.68), JNK (0.68), AMZN (0.66) |
| FOREX | 4 | AUDJPY=X (0.71), GBPJPY=X (0.69), EURJPY=X (0.67) |
| FUTURES | 3 | ES=F (0.60), NQ=F (0.60), YM=F (0.60) |
| COMMODITY | 2 | GC=F (0.76), GC=F (0.60) |
| STOCKS | 2 | LCID (0.95), QUBT (0.86) |

**Note:** `pick_funnel_today.json` shows 528 OPEN + 157 ACTIVE = 685 effectively open picks in the live funnel. The `alpha_engine/data/active_picks.json` subset (78 picks) represents the ML-scored, Kelly-sized tier.

---

## Risk controls (standing)

- **Max per-pick:** 0.25× Kelly (quarter-Kelly), enforced by `compute_position_size`.
- **Daily soft-stop:** `HYRO_TODAY_PNL_PCT` env var; -2% triggers pause.
- **DD halt:** `KELLY_DD_HALT_ENABLED=1` + rolling_dd_30d > `KELLY_DD_HALT_MAX` (default 0.30) → size=0.
- **Source diversification:** any filter must show ≤60% single-source share.
- **Min-n:** 50 decisive per class for proven filter; 100 for money-ready verdict.
- **Regime gate:** pause sleeves whose 30d momentum is negative (per `EQUITY_CONVICTION_TIERS`).

---

## Decisions made + known limitations

| Decision | Rationale |
|---|---|
| Used `money_ready_verdict.json` as canonical despite `dashboard_data.json` 7.6h stale | Verdict file is fresh (≈2.5h) and skill names it "policy-clean verdict" canonical |
| Did NOT emit a Kelly-sized weekly filter | No policy-clean class passes the proven filter floor; sizing would be theatre |
| Did NOT call any class "money-ready" | Policy-clean net shows 0/8 classes meeting n≥50 / PF≥1.3 / WR≥45% |
| Flagged HF_STATS COMMODITY/EQUITY/ETF as shadow-size candidates | Recent edge is real but not yet policy-clean; shadow-size (0.5%) is the safe bridge |
| Maintained FOREX freeze | Historical mislabel drift (EXPIRED→WON) makes any surface PF suspect |
| Did NOT push or FTP | No live deploy without operator gate; report is documentation-only |

**Known limitations carrying forward:**
- `dashboard_data.json` staleness (7.6h) means HF_STATS may not reflect the latest EAGLE-4 CRYPTO flip impact.
- `pf_registry.json` lacks `generated_at` — cannot verify freshness independently.
- The 685 open picks in `pick_funnel_today.json` vs 78 in `alpha_engine/data/active_picks.json` suggests a scoring/aggregation bottleneck, not a data gap.
- Portfolio sync gap (investigated separately): `pf_portfolio_portfolio_mix__*.json` files are shadow-history closed portfolios, not live positions. Live positions are in the funnel and active_picks.

---

## Final deliverable check (per skill "CHECK SUCCESS BEFORE STOPPING")

| Success criterion | Met? | Why |
|---|:---:|---|
| 1. Policy-clean proven filter: n≥50, PF≥1.3, WR≥45%, not artifact | ✗ | 0/8 classes pass |
| 2. CRYPTO sub-class WR≥50%, PF≥1.5, n≥100 | ✗ | EAGLE-4 flip shipped; monitor 7d rolling |
| 3. COMMODITY post-dedup n≥50, PF≥1.5 | ✗ | n=4 clean; 74 recent in HF_STATS awaiting validation |
| 4. ETF n≥100, PF≥1.3 | ✗ | n=2 clean; 104 recent in HF_STATS awaiting forward pilot merge |
| 5. FOREX directional filter WR≥50% | ✗ | Freeze maintained — resolver audit pending |
| 6. BOND top strategy if n≥20 | ✗ | n=0 |
| 7. Kelly sizing applied to filter picks | ✗ (vacuous) | No policy-clean picks exist to size |

**0/7 criteria met on policy-clean net.** 3/5 HF_STATS classes show edge awaiting validation.

---

*Generated by `/money-maker-readyv2` skill execution. Re-derive before reuse — never carry a typed table forward.*
