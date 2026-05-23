# Plan-Vetting Briefing — for external AI reviewers (2026-05-18)

Self-contained. A reviewer can vet the plan from THIS doc alone — do **not** assume
DB access. Everything you need is below.

## 1. Prerequisite context (what the system is)

`findtorontoevents.ca/audit` is a quant pick dashboard. A pipeline emits trade
"picks" from ~100 strategies across 6 asset classes (CRYPTO, EQUITY, FOREX,
COMMODITY, ETF, BOND; plus FUTURES/MEMECOIN/PENNY). Picks flow:
**source emitter → JSON → MySQL `at_raw_picks` → gate stack → `at_consensus_picks`
→ outcome resolver → dashboard.**

### DB tables that matter (MySQL `ejaguiar1_stocks`) — you do NOT need to query them
- `at_raw_picks` — core ledger, every pick + lifecycle + close (`status`, `pnl_pct`).
- `at_filter_log` — every gate REJECTION (no PASS rows).
- `at_consensus_picks` — picks that survived multi-source agreement.
- `at_signal_outcomes` — resolved entry/exit/pnl.
- `trading_picks` — dashboard store with `elite_score`, `trust_score`.

### JSON files that matter
- `dashboard_data.json` — rendered payload (17 MB). Tiles computed from it are INFLATED.
- `pf_registry.json` — **policy-clean, verdict-grade** per-strategy PF/WR. Trust this.
- `money_ready_verdict.json` — per-class MONEY_READY/WATCH/NOT_READY verdict.
- `crypto_quarantine.json` — dynamically-quarantined strategy names.

### The gates (in `audit_trail/quality_gates.py`)
- `passes_active_gate` — dashboard-visibility admission (kill gate, quarantine,
  blacklists, magnitude-sanity, FOREX-LONG block, low-elite-score block).
- `passes_smart_gate` — active gate + per-class score/WR floors + `forward_validated`.
- `calculate_smart_score` — 0-100 ranking.
- `passes_high_conviction_pick` — Gates 1-9 (score floors, trust-tier blacklist,
  per-class forward-WR floors, regime, walk-forward, ≥3-signal consensus).
- `money_ready_verdict` — per-CLASS statistical verdict (n≥50, WR≥0.55, PF≥1.5,
  DSR≥0.95, PBO≤0.55).

### The edge harness (the ONLY admissibility verdict)
`tools/edge_stability_harness.py::is_admissible()` — a signal is admissible only if
effect size eff ≥ 0.30 with the SAME SIGN in ≥3 of 5 walk-forward windows.

### Current measured state (verdict-grade, not the inflated tiles)
- **CRYPTO** — only class with a real resolved sample. Sub-floor: WR ~33%, PF 0.17–0.41.
- **EQUITY / FOREX / FUTURES / ETF / BOND** — statistically invisible: the non-crypto
  outcome resolver closes picks with `pnl_pct = 0.0` placeholder. Real WR/PF unknown.
- **COMMODITY** — headline PF inflated by killed COT strategies (artifact).
- **8** leakage-controlled signal candidates rejected by the harness. No class money-ready.
- Most picks die to *plumbing* (staleness, no_consensus), not quality gates.

## 2. The plan under review

`reports/MASTER_ENHANCEMENT_PLAN_2026_05_18.md` — measurement-first, 6 phases:

- **Phase 0 (BLOCKER)** — fix the non-crypto outcome resolver; populate `closed_at`;
  normalize `status` enum. Until done, 5 of 6 classes are unmeasurable.
- **Phase 1** — fix the plumbing (staleness / no_consensus losses).
- **Phase 2** — per-class triage: cut CRYPTO sub-PF-1 source volume; gather n≥100 clean
  for other classes; FOREX/FUTURES stay hard-disabled.
- **Phase 3** — genuine new-input edge hunt, harness-gated only. Candidate: CRYPTO
  funding-rate/basis arbitrage (delta-neutral, structural — NOT directional).
- **Phase 4** — per-class money-ready promotion gate (n≥100, WR≥0.52, PF≥1.5,
  DSR≥0.95, PBO≤0.55, MDD<20%, ≥4-week forward record).
- **Phase 5** — UX: honest dashboard, fix the orphaned "Money Ready" button.

Core thesis: **the system is edge-dry and measurement-blind; the fix is plumbing +
subtraction, not more strategies.**

## 3. Debate questions for reviewers

1. Is measurement-first (Phase 0 as hard blocker) the correct sequencing, or is it an
   excuse to defer the edge problem?
2. After 8 harness kills, is "there may be no edge to find" the honest verdict — or is
   the harness itself too strict (it kills regime-dependent edge)?
3. Is "cut volume, don't add strategies" right, or does the system genuinely need new
   strategy *families* (not variants)?
4. Is CRYPTO funding-rate/basis arbitrage a sound single bet, or another dead end?
5. What is the plan MISSING — name the highest-impact item not in the 6 phases.
6. Biggest risk in the plan as written.

Answer concisely. Disagree where warranted. Flag anything factually wrong above.
