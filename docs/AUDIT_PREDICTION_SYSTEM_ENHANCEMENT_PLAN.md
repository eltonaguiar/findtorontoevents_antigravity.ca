# Enhancement plan — prediction system (Crypto / Forex / Equities / Commodities / Bonds)

**Status:** Merged roadmap (repo investigation + Mercury 2 + Gemini Hyro/dashboard validation).  
**Goal:** Align SMART semantics, recalibrate scoring, clarify trust tiers, tighten blocklist enforcement, and add regression/CI guardrails.

**Document map (keep in sync):**

| Artifact | Role |
|----------|------|
| **This file** (`docs/AUDIT_PREDICTION_SYSTEM_ENHANCEMENT_PLAN.md`) | **Canonical** plan: Grok review, Gemini/Hyro validation, phased tasks A–F, timelines, appendices. |
| **Cursor plan** (`%USERPROFILE%\.cursor\plans\audit_score_enhancements_c5a87edd.plan.md`) | **Executable snapshot**: YAML todos + shorter phase outline; should not contradict this doc. Update Cursor todos when phases complete. |
| **Antigravity `audit_analysis_report.md`** | External investigation: Hyro WR/EV, High Conviction vs Smart Picks vs Verified Alpha — summarized under [External validation](#external-validation-hyrotrader-data-and-main-audit-feeds-gemini-investigation). |
| **[Additional enhancements](AUDIT_ADDITIONAL_ENHANCEMENTS.md)** | Follow-on items: backfill/validation alignment, CI snapshots, test matrix, shared copy helpers — extends Phases A–F without replacing the canonical plan. |

**Implementation order (rationale):**

1. **Phase A** — Unify semantics (removes the largest downstream misinterpretation).
2. **Phase B** — Recalibrate scoring (core predictive signal).
3. **Phase E** — Blocklist and feed coverage (safety net before deeper model tweaks).
4. **Phases C & D** — Crypto segmentation and trust clarity (granularity and transparency).
5. **Phase F** — Regression/CI (lock in improvements).

---

## Peer review: Grok feedback (incorporated + corrections)

**What to adopt**

- **Fast-track timeline option** for A + B only (see [Estimated timeline](#estimated-timeline-and-resources-phase-a--phase-b-only)); useful if one senior owner is full-time and **A4 (UI)** is deferred.
- **Phase F sketches:** nightly/PR workflow running `analyze_audit_scores_vs_pnl.py` + quadrant script, upload artifacts, optional Slack on failure, and a small **`test_score_calibration`** module — align with [Phase F](#phase-f--regression--ci-guardrails) (tune thresholds after baseline; handle **download/pin failures** as warn vs fail).
- **Monotonicity helper:** stratified decile means are valuable; implement with **numpy** in the existing tool if **pandas** is not already a repo dependency (Grok’s snippet uses `pd.qcut`).

**Critical: do not merge Grok’s `classify_pick_quality_v2` as written**

1. **`if not passes_smart_gate: return "REJECTED"` is wrong.** `passes_smart_gate` is false both for **failed active gate** and for **active-but-not-smart** picks. The latter must be **`ACTIVE`**, not `REJECTED`. Correct logic remains **[Appendix A](#appendix-a--example-classify_pick_quality_v2-sketch):** `REJECTED` ⇔ `not passes_active_gate`; `SMART` ⇔ `passes_smart_gate`; else `ACTIVE`.
2. **Raw-score branches (`>= 80` / `>= 50`) contradict “single source of truth.”** If `passes_smart_gate` is the exclusive Smart predicate, **do not** re-bucket by raw `score` inside v2 — that reintroduces the bug Phase A removes.
3. **Docstring error:** Grok says “`if not passes_smart_gate`” then lists rules “already included” in `passes_smart_gate` — the control flow and narrative are inconsistent.

**Critical: do not replace `calculate_smart_score` with Grok’s wholesale rewrite**

- Production scoring lives in **`audit_trail/quality_gates.py`** and uses helpers such as **`_trade_rr`**, **`_effective_forward_wr_ratio`**, **`_wf_verdict`**, **`_concentration_penalty`**, etc. Grok’s version invents fields (`forward_win_rate`, `concentration_score`, …) that **do not match** pick payloads and would **drop or distort** existing bonuses.
- **Phase B** should change **only the base term** (piecewise / cap / copy multiplier on base), then **leave the rest of the function structure** intact unless a deliberate refactor is spec’d and regression-tested.
- **`_apply_crypto_confidence_adjustment` inside `calculate_smart_score`** is a **Phase C** concern; keep it out of the minimal B PR or gate behind a flag to avoid mixing calibration changes.

**Grok CI test snippet (`spearmanr` from SciPy)**

- The main audit tool avoids SciPy for portability; CI tests can use **numpy-only Spearman** (same as `tools/analyze_audit_scores_vs_pnl.py`) or add **scipy** only in test env if acceptable.

**“Ship A + B this week”**

- Credible only for **backend-only** scope (no A4/D2, no dual-trust columns, no registry automation). Add buffer for **code review**, **pinned snapshot** agreement, and **dashboard_generator** wiring.

---

## External validation: HyroTrader data and main audit feeds (Gemini investigation)

**Source:** Antigravity artifact `audit_analysis_report.md` (resolved), aligned with this repo’s JSON. **Key paths:** [`audit_dashboard/data/hyro_pick_performance.json`](audit_dashboard/data/hyro_pick_performance.json), [`audit_dashboard/data/hyrotrader_picks.json`](audit_dashboard/data/hyrotrader_picks.json), [`audit_dashboard/data/dashboard_data.json`](audit_dashboard/data/dashboard_data.json).

### HyroTrader challenge track (distinct from main audit firehose)

| Metric (per investigation; refresh from JSON) | Value |
|------------------------------------------------|--------|
| Total validated signals | 461 |
| Wins / losses | 225 / 120 |
| Expired / no action | 116 |
| Win rate (wins ÷ (wins + losses)) | **65.2%** |

**EV framing:** At 1:1 and 1:2 risk–reward, a ~65% win rate implies **positive per-trade expectancy** in a simplified R model (the external report cites ~**0.30R** at 1:1 and ~**0.96R** at 1:2 — re-validate whenever `hyro_pick_performance.json` is regenerated). **Caveats:** headline stats omit **fees, slippage, discretion, and correlation** across overlapping signals; they are **not** a performance guarantee.

**Plan implication:** Keep HyroTrader / playbook messaging **separate** from “main audit raw score” caveats in user-facing copy. Optional: document JSON refresh cadence next to the Hyro dashboard panel.

### Main audit dashboard: High Conviction vs Smart Picks vs Verified Alpha

The investigation supports the enhancement direction: **raw High Conviction (score-driven)** and **Smart Picks (`passes_smart_gate` + `smart_score`)** answer different questions. Example snapshot from the report (illustrative; counts drift over time): Top Scored **4**, Smart Picks **16**, Verified Alpha **10**, Extreme Conviction **3**.

| Feed / label | Role | Reliability vs realized PnL (qualitative) | Plan hook |
|----------------|------|---------------------------------------------|-----------|
| **High Conviction / extreme raw score** | Highlights **high display `score`** | **Weaker** — can be **misleading** when raw score is inflated or miscalibrated (prior audit study: top raw quintile not best mean PnL) | **Phase B** base-term + copy handling; **Phase A4** labels/tooltips |
| **Smart Picks** | **`passes_smart_gate`** + **`smart_score`** ordering | **Stronger** — uses per-asset floors, RR, exclusions, forward-WR gates where applicable | **Phase A** single source of truth for “SMART” |
| **Verified Alpha** | Audited / verified-alpha cohort | Strong **process** backing; **static registry “PROVEN”** can still **lag** recent drift (see Phase D) | **Phase D** registry vs strategy trust |

**Interim user guidance (before Phase A/B are deployed):** If **High Conviction / sort-by-score** disagrees with **Smart Picks**, **prefer Smart Picks** for interpreting “rigorous” gating. Surface this as **help text or tooltip** on `/audit` (documentation-only until A4 ships).

**Note on terminology:** External copy may conflate **Verified Alpha** with `stamp_pick_quality`; in code, **registry trust** (`get_tier` in [`cross_aggregation/system_trust_registry.py`](cross_aggregation/system_trust_registry.py)) and **stamp_pick_quality** outputs are related but not identical — **Phase D** dual columns resolve the ambiguity.

---

## Phase A — Unify “SMART” semantics (high impact, low ambiguity)

| Task | Description | Owner | Success metric |
|------|-------------|--------|----------------|
| **A1** | Make `passes_smart_gate(pick)` the **exclusive** boolean for “Smart Pick.” Remove or deprecate parallel bucket logic in `classify_pick_quality` that only uses raw `score`. | Lead engineer (audit) | All downstream UI/analytics use the same predicate as production Smart Picks. |
| **A2** | Implement **`classify_pick_quality_v2`**: thin wrapper that returns `REJECTED` if not `passes_active_gate`, else `SMART` if `passes_smart_gate` else `ACTIVE`. Preserves per-asset floors (`SMART_PICKS_MIN_SCORE_*`), crypto LONG-only, forex forward-WR, RR, SCALP/panic rules inside `passes_smart_gate`. | Core engineer | Unit-test coverage targets all asset classes (see F2); see Appendix A for sketch. |
| **A3** | Update **`tools/analyze_audit_scores_vs_pnl.py`** to use the v2 classifier. | Data/analytics | Reported SMART vs ACTIVE distribution matches production Smart list within **≤ 1%** on a pinned dashboard snapshot (document comparison procedure). |
| **A4** | UI/UX: rename or split columns so “SMART” is not ambiguous — e.g. `quality_tier` → **`score_bucket_tier`** (legacy) vs **`smart_gate_tier`** (v2), or add **`smart_gate_passed`** boolean. Tooltip: “SMART = passed `passes_smart_gate` (same as Smart Picks tab).” Add parallel tooltip for **High Conviction / top raw score**: not equivalent to Smart Picks (see [External validation](#external-validation-hyrotrader-data-and-main-audit-feeds-gemini-investigation)). | Front-end | Tooltips on `/audit`; no misleading “SMART” or “High Conviction = best EV” without context. |

**Code touchpoints:** [`audit_trail/quality_gates.py`](audit_trail/quality_gates.py) (`passes_smart_gate`, `classify_pick_quality`), [`audit_trail/dashboard_generator.py`](audit_trail/dashboard_generator.py) (payload + templates), [`audit_dashboard/index.html`](audit_dashboard/index.html) / template if columns are hardcoded.

---

## Phase B — Recalibrate raw-score contribution to `smart_score`

| Task | Description | Owner | Success metric |
|------|-------------|--------|----------------|
| **B1** | Extend analytics: mean `pnl_pct` per **raw-score decile**, stratified by `source_system` and **strategy family** (copy vs systematic, etc.). | Data scientist | Dashboard/plot: **≥ 80%** of deciles monotonic non-decreasing **or** documented exceptions per stratum. |
| **B2** | **Redesign base term** in `calculate_smart_score`: replace linear `min(base * 0.3, 30)` with **piecewise** mapping (example below) **or** `elite_score` blend for copy streams. Apply **after** validating on historical `dashboard_data.json`. | Scoring engineer | **Spearman(`smart_score`, `pnl_pct`)** improves by **≥ 0.05** on `recent_closed` holdout (same pipeline as `tools/analyze_audit_scores_vs_pnl.py`). |
| **B3** | **Preserve bonuses** additive: R:R, forward WR, WF verdict, concentration — computed **after** base term, not multiplied into it. | Scoring engineer | No unintended collapse of `smart_score` variance; distribution sanity checks in tests. |
| **B4** | **Copy-trader:** if `_is_copy_pick` and symbol is not a **BTC-major** (define allowlist), apply extra **0.8×** on the **base term only** (mirrors confidence caps in [`alpha_engine/elite_scorer.py`](alpha_engine/elite_scorer.py)). | Copy-trader engineer | Copy picks no longer dominate top quartile solely via inflated raw score when EV is negative. |

**Code touchpoints:** [`audit_trail/quality_gates.py`](audit_trail/quality_gates.py) (`calculate_smart_score`), optionally shared helpers for “is BTC major” and “is copy pick” to match elite scorer.

---

## Phase C — Crypto-specific confidence and elite adjustments

| Task | Description | Owner | Success metric |
|------|-------------|--------|----------------|
| **C1** | In [`alpha_engine/elite_scorer.py`](alpha_engine/elite_scorer.py) (or `audit_trail/crypto_scoring.py`), **crypto branch**: non-monotonic confidence mapping when empirical IC &lt; 0 on rolling audit JSON. | Crypto engineer | Crypto slice: Spearman(smart_score or composite, `pnl_pct`) **≥ 0.2** (target; validate on data). |
| **C2** | Add **`crypto_adjusted_confidence`** to audit payload (**debug / internal** column — not primary consumer UI). | Data engineer | Visible in audit tables or debug export only. |
| **C3** | **Quarterly** (or monthly) scheduled job: recompute crypto confidence curve from latest `dashboard_data.json`; alert on **&gt; 5%** drift vs prior curve. | DevOps | Job runs unattended; alerts routed to CI or notification channel. |

---

## Phase D — Trust-tier clarity and drift control

| Task | Description | Owner | Success metric |
|------|-------------|--------|----------------|
| **D1** | Dual columns on audit payload: **`registry_trust_tier`** (`get_tier` from [`cross_aggregation/system_trust_registry.py`](cross_aggregation/system_trust_registry.py)), **`strategy_trust_tier`** (from [`audit_trail/stamp_pick_quality.py`](audit_trail/stamp_pick_quality.py) / forward stats when available). | Trust engineer | Both available in JSON; UI can badge “Registry” vs “Strategy.” |
| **D2** | UI: replace ambiguous **PROVEN** with **`REGISTRY-PROVEN`** (or tooltip) — clarifies **system-level** registry, not pick win probability. | Front-end | Reduces misinterpretation of static tier vs realized outcome. |
| **D3** | **Automated registry refresh:** script ingests attribution / closed picks, applies demotion rules already documented in `system_trust_registry.py`, opens PR or updates data file (avoid hand-editing only). | DevOps | Stale tier entries **&lt; 7 days** behind data (target); document rollback. |

---

## Phase E — Blocklist and feed coverage

| Task | Description | Owner | Success metric |
|------|-------------|--------|----------------|
| **E1** | **Ingress audit:** all paths emitting picks (cron, [`copy_trader_intel/main.py`](copy_trader_intel/main.py), bridges, scanners) call [`sanitize_active_picks`](alpha_engine/feed_hygiene.py) / `is_valid_active_pick`. | Security / platform | Checklist: **0** un-sanitized paths (grep + manual review). |
| **E2** | **Historical:** `strategy_retired` (or blocklist tag) on closed rows when strategy ∈ blocklist ([`alpha_engine/strategy_blocklist.py`](alpha_engine/strategy_blocklist.py)). | Front-end | Past `copy_hl_lb_None` rows clearly marked as retired policy. |
| **E3** | **Docs:** `strategy_blocklist.md` section + `feed_hygiene` enforcement flow; link from investigation doc. | Docs | Reviewed with QA checklist. |

---

## Phase F — Regression / CI guardrails

| Task | Description | Owner | Success metric |
|------|-------------|--------|----------------|
| **F1** | **Scheduled job** (nightly or on PR): run `tools/analyze_audit_scores_vs_pnl.py` + quadrant script on **pinned or downloaded** snapshot. **Fail** if: Spearman(`smart_score`, `pnl_pct`) **&lt; 0.25**; **or** top raw-score decile mean `pnl_pct` ≤ mid-decile mean **two runs in a row** (calibration regression). Tune thresholds after baseline week. | CI engineer | Failed runs surface **clear log + artifact** (JSON metrics). |
| **F2** | **Unit tests:** v2 classifier vs `passes_smart_gate` for matrix: crypto LONG/SHORT, forex low forward WR, copy-trader, SCALP, panic. | QA / engineer | High coverage on gate matrix (target **≥ 90%** branch coverage on gate module if feasible). |
| **F3** | Optional: make regression workflow a **required check** on `main` once stable (may start as non-blocking). | DevOps | Document flake policy (network download failures vs real regression). |

### Monitoring and alerting (F1 / C3)

- **CI:** Upload `score_pnl_analysis.json` (or summary) as **workflow artifact**; use `GITHUB_STEP_SUMMARY` or annotations for Spearman and decile checks.
- **Schedules:** `workflow_dispatch` + `schedule` (nightly); on failure, notify via **GitHub Actions failure notification**, **Slack/email webhook** (if repo already uses), or issue auto-create.
- **Alert semantics:** Distinguish **data unavailable** (skip or warn) from **threshold breach** (fail). Pin dashboard URL + date in artifact.
- **KPI dashboard (human):** Weekly review of Spearman; monthly decile monotonicity; quarterly blocklist ingress audit.

---

## KPI table (targets)

| KPI | Target | Frequency |
|-----|--------|-----------|
| Spearman(`smart_score`, `pnl_pct`) | ≥ 0.30 (pool); tune per asset in appendix) | Weekly |
| Raw-score decile monotonicity (by stratum) | ≥ 80% deciles OK | Monthly |
| SMART classification alignment (script vs production) | ≤ 1% discrepancy | Per CI run / release |
| Blocklist ingress coverage | 100% paths sanitized | Quarterly audit |
| Regression job failures | 0 except intentional / known data gaps | Per run |

---

## Estimated timeline and resources (Phase A + Phase B only)

**Assumptions:** 1–2 senior engineers familiar with `quality_gates` / dashboard; no hard external dependency blockers; UI renames can ship in a second PR.

### Conservative estimate (includes review, validation, optional UI)

| Phase | Calendar (typical) | FTE effort (rough) | Notes |
|-------|-------------------|---------------------|--------|
| **A** | **2–3 weeks** | **~2–4 person-weeks** | A1–A3 are backend-heavy; A4 depends on audit UI surface area. |
| **B** | **3–5 weeks** | **~4–7 person-weeks** | B1 data work + B2–B4 require backtest/audit validation before merge. |
| **A + B (parallel where safe)** | **~5–7 weeks wall-clock** with overlap | **~6–11 person-weeks** total | B1 can start early; B2 should not ship until A2 stabilizes classifier labels for evaluation. |

### Grok fast-track estimate (backend-only A1–A3 + B; defer A4)

| Phase | Engineer-days (indicative) | Calendar (indicative) | Caveats |
|-------|-----------------------------|-------------------------|---------|
| **A** | **1–2 days** | **~1 day** wall-clock if one owner full-time | Excludes A4 (column rename/tooltips); still needs PR review + snapshot check for A3. |
| **B** | **2–3 days** | **~2 days** after A | Assumes piecewise base + copy multiplier only; no full rewrite of `calculate_smart_score`. |
| **A + B total** | **~3 engineer-days** | **~3–4 calendar days** one dev | Add **+1–2 days** if UI/analytics comparison (A3 “≤1%”) is strict or data is noisy. |

**Resource constraints:** If capacity is **one engineer half-time**, double calendar time. If **no front-end capacity**, ship A1–A3 + analytics first; defer A4/D2 to a follow-up sprint.

---

## Next steps

1. Kick-off: confirm owners, snapshot data access for CI, and whether audit UI changes ship with A or separately.
2. Branch strategy: e.g. `feature/smart-gate-unification` → `feature/smart-score-base-recalibration` (merge A before B2 lands).
3. Baseline: capture current Spearman/deciles from [`tools/analyze_audit_scores_vs_pnl.py`](tools/analyze_audit_scores_vs_pnl.py) + [`docs/AUDIT_SCORE_PNL_DEEP_DIVE_2026-04-19.md`](docs/AUDIT_SCORE_PNL_DEEP_DIVE_2026-04-19.md) metrics as pre-change reference.

---

## Appendix A — Example: `classify_pick_quality_v2` (sketch)

**Correct pattern (three mutually exclusive buckets):**

```python
# audit_trail/quality_gates.py — illustrative only; match real imports/signatures.

def classify_pick_quality_v2(pick: dict) -> str:
    """SMART / ACTIVE / REJECTED — aligned with production Smart Picks."""
    if not passes_active_gate(pick):
        return "REJECTED"
    if passes_smart_gate(pick):
        return "SMART"
    return "ACTIVE"
```

Deprecate `classify_pick_quality` or make it call v2 with a `legacy_score_bucket=False` flag if anything still needs raw-score-only buckets.

**Anti-pattern (reject):** `if not passes_smart_gate(pick): return "REJECTED"` — mislabels **active-but-not-smart** picks. **Anti-pattern:** extra **`if raw_score >= 80`** tiers inside v2 — that is **not** “single source of truth” for Smart.

---

## Appendix B — Example: piecewise base contribution (sketch)

Deciles computed **per stratum** (or globally first, then refine): map raw `score` (0–100) to `base_pts` (0–30) before R:R and other additive bonuses.

```python
def _base_points_from_display_score(score: float, decile: int) -> float:
    score = max(0.0, min(100.0, float(score)))
    if decile <= 3:
        w = 0.1
    elif decile <= 7:
        w = 0.2
    else:
        w = 0.3
    return min(score * w, 30.0)
```

**Note:** `decile` must come from **offline calibration table** or rolling quantiles stored in config, not hardcoded forever. Copy-trader: multiply **only** `_base_points_from_display_score(...)` by **0.8** when `_is_copy_pick and not _is_btc_major(symbol)`.

**Anti-pattern (reject):** Replacing the entire `calculate_smart_score` body with ad hoc `pick.get("risk_reward")` / `forward_win_rate` — use existing **`_trade_rr`**, **`_effective_forward_wr_ratio`**, **`_wf_verdict`**, **`_concentration_penalty`**, etc., from [`audit_trail/quality_gates.py`](audit_trail/quality_gates.py).

---

## Appendix C — CI / regression sketch (reference; align with Phase F)

Grok’s YAML idea is directionally right; adapt to this repo’s script flags and **pinned** `dashboard_data.json` path. Prefer **numpy Spearman** in tests to match [`tools/analyze_audit_scores_vs_pnl.py`](tools/analyze_audit_scores_vs_pnl.py). Slack step requires org secrets; treat as optional. On PR, **fail closed** only when metrics artifact exists and thresholds are breached — avoid failing every PR when snapshot download is blocked.

---

## Appendix D — File index

| Area | Primary files |
|------|----------------|
| Gates & smart score | [`audit_trail/quality_gates.py`](audit_trail/quality_gates.py) |
| Elite / confidence | [`alpha_engine/elite_scorer.py`](alpha_engine/elite_scorer.py) |
| Dashboard payload | [`audit_trail/dashboard_generator.py`](audit_trail/dashboard_generator.py) |
| Trust registry | [`cross_aggregation/system_trust_registry.py`](cross_aggregation/system_trust_registry.py) |
| Stamping | [`audit_trail/stamp_pick_quality.py`](audit_trail/stamp_pick_quality.py) |
| Feed safety | [`alpha_engine/feed_hygiene.py`](alpha_engine/feed_hygiene.py), [`alpha_engine/strategy_blocklist.py`](alpha_engine/strategy_blocklist.py) |
| Analytics | [`tools/analyze_audit_scores_vs_pnl.py`](tools/analyze_audit_scores_vs_pnl.py), [`tools/audit_score_pnl_quadrant_deep_dive.py`](tools/audit_score_pnl_quadrant_deep_dive.py) |
| HyroTrader performance JSON | [`audit_dashboard/data/hyro_pick_performance.json`](audit_dashboard/data/hyro_pick_performance.json), [`audit_dashboard/data/hyrotrader_picks.json`](audit_dashboard/data/hyrotrader_picks.json) |

---

*End of merged plan.*
