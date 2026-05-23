# Audit fleet review — cross-asset picks, Smart, Verified Alpha, hedge-fund gap analysis

**Date:** 2026-04-07 UTC  
**Scope:** `findtorontoevents.ca/audit` (source: [eltonaguiar/findtorontoevents_antigravity.ca](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca)) + user exports `antigravity_*_2026-04-06.csv` + repo `dashboard_data.json` analysis JSON.  
**Method:** Parallel codebase reads (`quality_gates`, `dashboard_generator`) + CSV aggregation + closed-book exit mix.

---

## 1. Pick volumes by asset class (user export `antigravity_*_2026-04-06.csv`)

| Asset class | Closed (n) | Active snapshot (export) | Notes |
|-------------|------------|--------------------------|--------|
| CRYPTO | 2,820 | 58 | Dominates book and history |
| EQUITY | 465 | 47 | Large in export vs small **gated** active in live JSON snapshots (often 1–few pass `passes_active_gate`) |
| FOREX | 139 | 4 | Thin active; **SMART floor 75** in code |
| COMMODITY | 12 | — | Tiny **n** — research only |
| ETF | 12 | — | Tiny **n** |
| FUTURES | 3 | — | Tiny **n** |
| SPORTS | — | 1 | Separate lane |

**Implication:** HF-style risk budgeting should **weight CRYPTO + VA** heavily; treat EQUITY/FOREX/COMM/ETF/FUTURES as **low-capacity** until closed-book mean PnL and **n** justify expansion (see `docs/AUDIT_PICKS_EDGE_ANALYSIS_2026-04-06.md`).

---

## 2. Closed-trade exit mix (same export — top reasons)

Rough mix shows **stops and expiry** dominating **TP**:

| Exit bucket (raw labels) | Approx count |
|--------------------------|--------------|
| SL / SL_HIT | ~1,230+ |
| EXPIRED / TIME / TIME_EXIT | ~900+ |
| TP / TP_HIT | ~720+ |

**Implication:** Not “coin flip” on direction alone — **geometry and horizon** dominate realized outcomes. Unify TP/SL between `dashboard_generator._vol_aware_tp_sl` and `universal_pick_resolver` fallbacks (`docs/AUDIT_CRYPTO_PREDICTION_TP_SL_QUALITY_2026-04-02.md`), then re-bucket outcomes by **vol tier / mode**.

---

## 3. Smart Picks vs Active vs Verified Alpha (code + live JSON)

- **Smart (`picks.smart_picks`):** Built only from **post-gate `active`** rows that pass `passes_smart_gate`, then top 50 by `smart_score` (`dashboard_generator.py` ~11699–11723). If **zero** rows pass → **empty Smart tab** (common when anti-overfit + score + forward_wr + crypto trust stack fails).
- **Active:** `passes_active_gate` + scoring; optional `active_raw` is larger pool in UI.
- **Verified Alpha:** Separate cohort via `_is_verified_alpha_pick` (PM / copy / forward-history / score-trust / WF p-value paths) — `verified_alpha` summary in payload (`dashboard_generator.py` ~4465+).

**Local `tools/data/audit_active_book_analysis.json` (regenerated from `audit_dashboard/data/dashboard_data.json`):** example snapshot — **58** actives, **0** smart picks, **51** VA actives, **0** VA smart; aggregate unrealized sum negative on that slice.

---

## 4. Per–asset-class gates (repo truth)

Defined in `audit_trail/quality_gates.py`:

- **Smart score floors:** `SMART_PICKS_MIN_SCORE` (crypto default 60), `SMART_PICKS_MIN_SCORE_EQUITY` 50, **FOREX 75**, COMMODITY 60, BOND 40, FUTURES 60, ETF 40 — then **sandbox floor 75** (62 for some non-crypto consensus lanes), proven **−10** discount.
- **Active:** Non-crypto trust **< 4** reject; raw score **< 55** for many non-crypto rows; crypto raw display floor **30**; blocked source/strategy pairs; optional **GC=F** bad-entry reject.
- **Crypto-only Smart blocks:** sandbox strategy, trust, overconfidence, consensus-without-edge, etc.

**Bug-class note:** `classify_pick_quality` uses a **single** threshold (60) for labels; **real** Smart eligibility is only `passes_smart_gate` — do not use the label alone for research.

---

## 5. User CSV vs “hedge fund” bar (what looks like coin-flip)

From `antigravity_active_picks_2026-04-06.csv` rows:

- **Consensus inflation:** “36 systems agree” while **strategy forward** remains weak (e.g. `quan_engine` with **SANDBOX** trust and **~37%** Bayesian WR on thousands of trades) — **agreement count ≠ edge**.
- **Confidence vs trust:** **99% confidence** with **PROBATION** / **50% forward** on **16 trades** — high UI conviction without institutional sample depth.
- **Regime-direction conflict:** SHORTs in **BULLISH** regime still appear (penalized but not always hard-blocked) — HF books usually **flip off** or **severely size down**.
- **Paper-trading orders CSVs:** several files in Downloads were **empty** on read — reconcile export job vs DB; without fills alignment, TCA and realized slippage stay blind.

---

## 6. Moving from coin-flip to HF-grade (prioritized)

| P0 | Action |
|----|--------|
| 1 | **Narrow live surface:** default risk to **SMART + VA + proven battleground** until pool metrics recover; keep `active_raw` for research only (`HEDGE_FUND_ENHANCEMENT_PLAN.md`, `EDGE_ADDENDUM.md`). |
| 2 | **Anti-overfit + promotion:** expand registry or cap **SANDBOX** emission; do not let mass forward-test strategies dominate active count without walk-forward pass. |
| 3 | **Single TP/SL module** shared by dashboard + resolver; calibrate SL/TP from closed **exit-reason** histogram. |
| 4 | **Score–trust–forward consistency:** cap display score when `trust_tier` is SANDBOX and `strat_fwd_wr` &lt; 50% with **n ≥ 30** (already partially via penalties — tighten promotion). |

| P1 | Action |
|----|--------|
| 5 | **DSR / FDR / purged CV** automation per `HEDGE_FUND_ENHANCEMENT_PLAN.md` §1. |
| 6 | **Non-crypto:** allowlist strategies only; do not lower FOREX **75** floor without closed-book proof. |
| 7 | **Paper vs audit:** join paper-trading fills to pick IDs for **realized** slippage and holding time — fix empty CSV exports. |

| P2 | Action |
|----|--------|
| 8 | **ejaguiar1_stocks** SQL extract (`ejaguiar1_stocks_apr62026_extract.sql`, ~4.2GB): map `alpha_*` / `at_*` tables to dashboard keys for second truth layer — use streaming tools / `docs/EJAGUIAR1_STOCKS_SQL_EXTRACT_2026-04-06.md`; not fully scanned in this review. |

---

## 7. Commands

```bash
python tools/analyze_audit_active_book.py
python tools/analyze_audit_scores_vs_pnl.py
python tools/audit_smart_gate_funnel.py audit_dashboard/data/dashboard_data.json
python tools/fetch_audit_dashboard_snapshot.py
```

---

## 8. References

- [GitHub: findtorontoevents_antigravity.ca](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca)
- `HEDGE_FUND_ENHANCEMENT_PLAN.md`, `EDGE_ADDENDUM.md`
- `docs/AUDIT_PICKS_EDGE_ANALYSIS_2026-04-06.md`
- `docs/AUDIT_CRYPTO_PREDICTION_TP_SL_QUALITY_2026-04-02.md`
- `TRACE_LOG.MD`, `docs/REDIS_BUS_CHANGELOG.md`
