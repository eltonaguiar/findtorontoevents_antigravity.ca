# /money-maker-readyv2 — Addendum + TODO list — 2026-05-19T0010Z (next-day UTC)

Companion to `reports/MONEY_MAKER_READYV2_NORTH_STAR_2026-05-19T2350Z.md`.

Mining input: 4-AI transcript-review swarm (xAI/Cerebras/Inception/Ring),
20+ MASTER_ACTION_PLAN / FOOLPROOF / SUPREME / PRIORITIZED / EXPERT_FEEDBACK
files, hypothesis registry audit, session-ses_1c60.md gold extraction,
Cursor 3 deep-dive MDs.

Grok share URL `bGVnYWN5LWNvcHk_0ca57b24-8c9a-4177-ad05-ba23a2c47f96` =
HTTP 403 unauth-gated (only operator excerpt usable, already embedded in
north-star MD).

---

## NEW prompt patterns (NOT already in `docs/swarm_prompts/`)

| ID | Pattern | Source plan | When to use |
|----|---------|-------------|-------------|
| P-1 | **V-gate executable smoke suite** (V1..V10 PASS/FAIL/PARTIAL) | `reports/ACTION_PLAN_V2_EVALUATION_2026-05-15.md` | Post-PR regression: concept_family coverage, UEPS picks, penny skyrocket cron, PEAD cache |
| P-2 | **5-Gate hierarchy** (paper-cut → slippage → safety → micro-deploy → expansion) | `FOOLPROOF_ACTION_PLAN.md` | Real-money progression checkpoints |
| P-3 | **Shadow-mode protocol with acceptance thresholds** (P0-A conf 0.90 cap, P0-B BUY block, P0-C ml_score floor 0.65) | `reports/expert_feedback_action_plan_2026-05-17.md` | Any new gate before enforce |
| P-4 | **Statistical kill-gate** (min-n + binomial p-value + Wilson CI) | `reports/SUPREME_PLAN_90days.md` M-055/56/57 | Replace pure-PF kills with stats-defensible kills |
| P-5 | **Verdict dashboard format** (T1=PF>2/WR>55, T2=PF>1.5/WR>50, explicit blocker per class) | `reports/MASTER_ACTION_PLAN_2026-05-18.md` | /audit money-ready tiles |
| P-6 | **Threshold-only fixes spec** (BLOCK_CRYPTO_SHORTS, BLOCK_SCALP_MODE, ml_score inversion 0.58/0.70, elite_score removal, before/after WR target) | `GOLDEN_STANDARD_ACTION_PLAN.md` | Zero-code regression-safe gate flips |
| P-7 | **Cross-swarm priority synthesis** (expert WR/PF baseline → ranked P0/P1/P2 per class, "highest leverage" frame) | `reports/PRIORITIZED_ACTION_PLAN_2026-05-17.md` | After any multi-AI consult |

Action: codify P-1..P-7 as new `docs/swarm_prompts/` templates if missing.

---

## NEW per-class TODO items beyond MERGED_ACTION_PLAN_2026-05-19

### CRYPTO
- C-INV-1 STRATEGY_INVESTIGATION `quan_engine` (WR audit, 90d backtest) [MASTER_2026-05-18 C-005] — ETA 2026-05-20
- C-INV-2 STRATEGY_INVESTIGATION `rapid_fire` — DONE this session (blocked, commit 9834307 lineage)
- C-CAP-1 Per-strategy concentration cap on `luxalgo_filters` (17.5% vol drag at PF 1.12) [FOOLPROOF]
- C-CONF-1 Hard-cap `confidence >0.90` (14.4% WR overfit cliff per EXPERT_FEEDBACK) — P0 gate

### COMMODITY
- K-COT-1 COT lag correction + CT=F hard-block >40% weekly rolling [MASTER M-001/M-002]
- K-DIV-1 Diversify universe to GC/SI/HG/CL/NG/ZW/ZC/ZS (7+ underliers) [MASTER M-003/M-004]
- K-INCU-1 Wire SUPREME M-055/56/57 statistical kill-gate into Phase 2-D replay (incubator path)

### EQUITY
- Q-SYNC-1 MySQL sync import n=400+ from production DB [MASTER Q-001]
- Q-BUG-1 Fix `timeframe=None` stamping (26 EQUITY picks broken) [ACTION_PLAN_V2 V2-FAIL]
- Q-RES-1 Backtest `vix_regime_4h` + `sector_rotation_longonly` (T2-borderline candidates)

### ETF
- E-N-1 Accumulate n≥100 (currently n≈75 dashboard / n=2 canonical — investigate gap) [MASTER E-001]
- E-VIX-1 VIX<25 gate (block new positions if VIX≥25 @ 09:35 ET) [MASTER E-005]
- E-ROT-1 Sector rotation (12-1 momentum on 9 SPDR) — research [PRIORITIZED]

### FOREX
- F-CARRY-1 G10 carry backtest (long AUD/NZD, short JPY/CHF) + trend overlay [MASTER F-004/F-005]
- F-SHORT-1 SHORT-only gate + COT reversal signal [EXPERT_FEEDBACK / Grok+Kimi]

### BOND
- B-FRED-1 Fix FRED_API_KEY secret to unblock credit-spread data [FOOLPROOF]
- B-UNI-1 Expand universe beyond TLT/IEF (currently 75% TLT concentration on n=2/14 symbols emitting)

### FUTURES
- FU-CLS-1 Fix `=F` → COMMODITY classification bug (4 strategies coded but n=0 emit) [FOOLPROOF]

### Infrastructure (raises every class)
- I-VGATE-1 Wire V-gate suite (V1..V10) into nightly CI [P-1]
- I-FDR-1 Ship `tools/fdr_control.py` (BH q=0.10) [unanimous swarm A]
- I-DSR-1 Ship `tools/dsr.py` + `tools/pbo.py` + `tools/wfe.py`
- I-LDP-1 Ship `docs/swarm_prompts/RENAISSANCE_LDP_GATE_v1.md`
- I-HARN-1 Widen `is_admissible()` ledger scope 1/32 → ≥80%
- I-AUTOBROAD-1 Auto-broadcast hypothesis_registry status nightly via cross-PC bus

---

## HYPOTHESIS REGISTRY — current status snapshot

- 18 pre-registered tested, **0 admissible-under-canonical**
- LIVE_TESTING: H-001 COT_positioning COMMODITY
- SHADOW_IMPLEMENTATION: H-002 PEAD, H-003 cross-sectional momentum
- PRE_REGISTERED (untested): H-018 SOPR realized-profit, E-ANON-001 short_term_momentum
- UNTESTED_DATA_GAP: H-017 funding-settlement-liquidation-cascade, H-028v2 insider-EDGAR, H-031 harvest-seasonality, H-034 anti-PEAD
- **Drift flags (M-107 violations confirmed):** H-037 (vix_term_carry — custom WF, NOT canonical harness; densification probe REJECTED), H-017 (custom WF)
- Next free ID: **H-039**

H-039 candidate (per all 30+ consults converging): CRYPTO intraday
signed-volume imbalance / liquidation reversion at tick resolution. Binance
aggTrade. 5-20% P(admissible). 2-4 week paper probe.

---

## TODO list (executable, next sessions)

1. **[P0]** Wire HARNESS_FDR_GATE: `tools/fdr_control.py::benjamini_hochberg(q=0.10)` + integration into `tools/edge_stability_harness.py::is_admissible()`. ~30 lines + tests. Unanimous swarm A.
2. **[P0]** Wire DSR / PBO / WFE: López de Prado `tools/dsr.py` + `tools/pbo.py` + `tools/wfe.py`. Render in `pf_registry.json` per class.
3. **[P0]** Widen harness ledger scope (1/32 → ≥80%) in `tools/edge_stability_harness.py::_load()`. Per merged plan T1-05.
4. **[P0]** Ship `docs/swarm_prompts/RENAISSANCE_LDP_GATE_v1.md` (template from north-star MD §5).
5. **[P0]** Fix `=F` → COMMODITY classification bug (FUTURES emits 0 picks despite 4 strategies coded) [FU-CLS-1].
6. **[P0]** Fix `timeframe=None` stamping for 26 EQUITY picks [Q-BUG-1].
7. **[P1]** STRATEGY_INVESTIGATION `quan_engine` CRYPTO with mutation-3-axis [C-INV-1].
8. **[P1]** Classify UNKNOWN class (n=38 PF 1.72) — find why these rows lack asset_class.
9. **[P1]** Confidence cap >0.90 at emission [C-CONF-1].
10. **[P1]** Wire V-gate suite (V1..V10) into nightly CI [I-VGATE-1].
11. **[P1]** Codify P-1..P-7 as new `docs/swarm_prompts/` templates.
12. **[P2]** Pre-register H-039 CRYPTO intraday volume-imbalance (M-107: registry commit BEFORE backtest).
13. **[P2]** Binance aggTrade fetcher → `tools/binance_aggtrade_fetcher.py` → MySQL `at_intraday_picks`.
14. **[P2]** Auto-broadcast hypothesis_registry status nightly [I-AUTOBROAD-1].
15. **[Time-gated]** EMITTER_WHITELIST_ENFORCE flip per Option C (after 200-close clean).
16. **[Time-gated]** `cta_replicator` FOREX harness run at n≥150.
17. **[Operator]** `git stash pop` Cursor WIP 81815e97.
18. **[Operator]** FRED_API_KEY GH secret for BOND credit-spread data.

---

## Companion docs (commit chain)

- `reports/MONEY_MAKER_READYV2_NORTH_STAR_2026-05-19T2350Z.md` (eb1053a) — main north-star upgrade
- `reports/MERGED_ACTION_PLAN_2026-05-19.md` — authoritative roadmap
- `reports/EDGE_VERDICT_2026-05-18.md` — no-edge verdict
- `reports/EXECUTIVE_SUMMARY_2026-05-19T2240Z.md` (ab266e9) — session-end exec summary
- `reports/PF_IMPROVEMENT_PER_CLASS_2026-05-19T2137Z.md` — per-class drag plan
- `reports/H037_CANONICAL_HARNESS_AUDIT_2026-05-19T2200Z.md` — M-107 impl-drift case study

---

*Generated 2026-05-19T2358Z. Input: 4-AI transcript review + 4-subagent
corpus mining + 1-subagent MASTER plan mining + 1-subagent Grok share fetch
(403). All references verified against canonical `pf_registry.json`
2026-05-19T19:46Z snapshot. No fabrication.*
