# Asset-class research orchestrator — design + PR 1 ship

**Date:** 2026-05-11
**Owner:** Claude Opus 4.7 (1M)
**Branch:** `feat/audit-dashboard-enhancements-hermes-2026-05-09`
**Trigger:** user request — multi-AI consensus research swarms per asset class, sourced + backtested + cross-tested picks published as HTML pages on `/audit`.

---

## What shipped in PR 1

**Goal:** prove the end-to-end loop with one real artifact today; defer paid swarm calls until budget green-light.

| File | Role |
|---|---|
| `tools/research/__init__.py` | package marker + 5-pass protocol docstring |
| `tools/research/schemas.py` | stable JSON contracts (`SCHEMA_VERSION=v1`): Citation, StrategySpec, BacktestResult, CrossTestResult, SynthesisRow, RunSummary |
| `tools/research/textbook_bond_strategies.py` | 3 seed BOND strategies cited from Cochrane-Piazzesi 2005, Fleckenstein-Longstaff-Lustig 2014, Frazzini-Pedersen 2014 |
| `tools/research/p3_backtest_runner.py` | v1 STUB — deterministic metrics from spec_id hash. Marked clearly in `BacktestResult.notes`. PR 2 replaces with `alpha_engine.backtest.engine.BacktestEngine`. |
| `tools/research/p4_cross_test.py` | overlap ρ + symbol Jaccard vs shipped strategies in `audit_dashboard/data/dashboard_data.json::systems`. Verdict thresholds: ρ>0.7 + overlap>60% = DUPLICATE; ρ>0.5 + overlap>40% = OVERLAP_WARNING; else INDEPENDENT. |
| `tools/research/verify_citations.py` | HEAD-check URLs, downgrade hallucinated engines (>25% bad → 0.5x weight; >50% → 0x). Not yet wired into orchestrator (v2). |
| `tools/research/render_html.py` | renders one run to standalone `index.html` |
| `tools/research/build_research_index.py` | scans all runs, writes `audit_dashboard/research_index.html` (linked from `/audit/` nav) |
| `tools/research/orchestrator.py` | CLI: `python -m tools.research.orchestrator --class <class>` — runs P3+P4 today, scaffolds P1/P2/P5 swarm hooks for PR 2 |
| `research/domain_allowlist.txt` | known-real domains for citation trust scoring |
| `research/asset_class/bond/run_2026-05-11T17-46-50Z/` | first real run — index.html + 5 JSON artifacts |
| `audit_dashboard/research_index.html` | static listing of all runs across all classes |
| `audit_dashboard/template.html` | +1 `<a href="research_index.html">` nav link beside "Jump to Active Picks" |

**Run today:** `python -m tools.research.orchestrator --class bond` → 3 candidates, all INDEPENDENT, MIXED verdict, $0 cost, ~0.5s wall.

---

## 5-pass protocol (sourced from Agent design)

| Pass | Mandate | Actor | v1 status |
|---|---|---|---|
| **P1 LITERATURE** | swarm gathers cited sources (URL + access_date + claim); HEAD-check rejects hallucinated URLs | swarm | scaffolded; orchestrator uses 3 hand-curated bond citations as placeholder |
| **P2 CANDIDATES** | swarm proposes ≥5 backtestable strategy specs referencing P1 citations | swarm | scaffolded; uses textbook seeds (3 bond strategies) |
| **P3 BACKTEST** | walk-forward backtest per spec, emit PF/WR/MDD/Sharpe/n | orchestrator | **STUB** — deterministic from spec_id hash; replace with `BacktestEngine` in PR 2 |
| **P4 CROSS-TEST** | ρ + symbol overlap vs `dashboard_data.json::systems`, verdict DUPLICATE / OVERLAP_WARNING / INDEPENDENT | orchestrator | works against current production payload (3 independent candidates today) |
| **P5 SYNTHESIS** | swarm votes go/no-go, drafts Wiring Plan, renders HTML | swarm + orchestrator | deterministic seed (T2 floor check + cross-test verdict); swarm voting in PR 2 |

---

## Pilot selection — BOND (justified)

- **BOND meets T2 PF (1.72) + WR (55.6%) but n=18 — only sample size blocks the verdict.** A research round that lifts n→100 with publishable strategies gives a *real* asset-class-proven banner on `/audit` fastest. Banner already shows BOND under MAJOR GOAL section.
- **Lowest negative-result risk.** Bond literature (TIPS, duration-carry, value/momentum in govt + IG credit, AQR's *Value & Momentum Everywhere*) is dense + replicable.
- **Cheapest data.** Daily bars + spreads from FRED + Treasury Direct, no minute-bar storage cost.
- **FOREX 2nd.** Once orchestrator proven on BOND (positive case), point at FOREX as the negative-finding stress test (CLAUDE.md mutate-before-kill mandate). Don't pilot on FOREX — too many ways v1 looks broken when the class is genuinely sub-floor.

---

## Cost model

3 swarm passes × 4 engines × ~10k in / 5k out per pass ≈ **$4-13 per class** depending on engine mix (cheap: deepseek+gemini+cerebras+1 premium → $4-6; top-shelf → $13). PR 2 wires hard caps via `--budget-class 10.00` + `--budget-session 50.00`. P3 + P4 cost $0 (pure Python).

---

## Negative-finding protocol

A NO_EDGE run is shipped as a first-class deliverable. `index.html` template branches on `summary.verdict`:
- **NO_EDGE page** must include: all citations (future agents inherit lit review), all P2 candidates with P3 fail reasons, "Retry conditions" callout with explicit regime triggers (e.g., "retry FOREX when DXY 30d realized vol > 8%"), "What we tried" table.
- Orchestrator REFUSES to write `verdict=GO` when any candidate has `PF<1.5 OR n<50 OR cross_test=DUPLICATE`.

---

## What's NEXT (PR 2 → PR 5)

| PR | Scope |
|---|---|
| **PR 2** | Wire `alpha_engine.backtest.engine.BacktestEngine` into `p3_backtest_runner.py` (replace stub). Wire `tools/swarm/swarm_run.py` into orchestrator P1+P2+P5 paths with `--enable-swarm` flag. Wire `verify_citations.py` into P1 post-processing. Cost-tracking + budget cap. Re-run BOND with real numbers + real swarm output. |
| **PR 3** | FOREX stress-test (negative finding likely). Validates NO_EDGE protocol produces useful artifact. |
| **PR 4** | Remaining 5 classes (equity, crypto, etf, futures, commodity) + cron `.github/workflows/research-orchestrator.yml` (weekly cadence). |
| **PR 5** | CPCV upgrade (close `project_cpcv_gap_2026_04_28.md`) — swap walk-forward for CPCV in `p3_backtest_runner`. |
| **PR 6** | Production wire-in. For any candidate with GO verdict, follow `## Wiring Plan` + add caller in `alpha_engine/baby_strats/` per CLAUDE.md strategy factory S4 path. |

---

## Wire-Up Rule compliance (CLAUDE.md)

- **Orchestrator is wired:** `audit_dashboard/template.html` nav links to `research_index.html`; `research_index.html` links to per-run pages; per-run pages reference real backtest + cross-test numbers from real shipped strategies. Not orphan.
- **P3 STUB is clearly marked:** every BacktestResult.notes field warns the numbers are deterministic stubs until PR 2.
- **Wiring Plan section (per Wire-Up Rule)** — applies when a candidate moves to production:
  > Stage `<spec_id>` in `alpha_engine/baby_strats/`. After 30d paper-test + forward-validation: promote to active emission with `quality_gates.trust_score` initialized at 4. Caller: `alpha_engine.smart_picks_engine` via existing strategy registry — no new orchestrator needed.

---

## Acceptance criteria for PR 1 → close-out

- [x] `python -m tools.research.orchestrator --class bond` runs successfully on a clean checkout
- [x] BOND run produces `index.html` linked from `/audit/research_index.html` linked from `/audit/`
- [x] All schemas frozen at `SCHEMA_VERSION=v1`; future renames trip JSON readers
- [x] STUB nature of P3 + P5 v1 metrics is explicit in HTML + JSON + this doc
- [ ] Live swarm pass on BOND with at least 2 engines (deepseek + cerebras) producing real P1/P2/P5 output — **PR 2**
- [ ] Real BacktestEngine wired — **PR 2**
- [ ] BOND verdict transitions from MIXED stub to a real GO / MIXED / NO_EDGE — **PR 2**

---

## Files referenced

- `tools/swarm/swarm_run.py` — multi-engine fan-out, ready for P1/P2/P5 calls
- `tools/swarm/examples/asset_class_audit.yaml` — template for P1/P2 YAML configs
- `alpha_engine/backtest/engine.py::BacktestEngine` — real backtest harness for PR 2
- `tools/walk_forward_validate.py` — walk-forward folds for PR 2
- `audit_dashboard/data/dashboard_data.json::systems[*]` — shipped-strategies list for P4 cross-test
- `CLAUDE.md` Wire-Up Rule — production-caller requirement
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — for FOREX stress test in PR 3
- `project_cpcv_gap_2026_04_28.md` — known gap for PR 5
