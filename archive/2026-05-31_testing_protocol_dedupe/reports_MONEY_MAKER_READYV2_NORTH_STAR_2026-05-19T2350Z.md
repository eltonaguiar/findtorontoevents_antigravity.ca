# /money-maker-readyv2 — North-Star Upgrade — 2026-05-19T2350Z

**Stamped:** Project north star (CLAUDE.md MAJOR GOALS + memory
`user_north_star_hf_edge_per_asset.md`). Verbatim:

> Hedge-fund / quant-grade statistical edge per asset class on
> `findtorontoevents.ca/audit`. **Tier-2 charter minimum:** PF≥1.5, WR≥50%,
> MDD<20%, n≥100 clean post-dedup. **Tier-1 long-run (Renaissance):** PF≥2,
> WR≥55%, MDD<10%. Every commit is tested against this. Goal-mismatched PRs
> rejected unless P0 prod-protect.

This document upgrades `/money-maker-readyv2` (`.claude/skills/money-maker-readyv2/SKILL.md`)
with the multi-AI harvest from session 2026-05-19, the canonical hypothesis
registry state, and a Renaissance-grade prompt template.

---

## 1. Tier-gate (institutional thresholds, non-negotiable)

| Gate | Tier-2 | Tier-1 (Renaissance) |
|------|--------|----------------------|
| Profit factor (net 30bps round-trip) | ≥ 1.5 | ≥ 2.0 |
| Win rate (canonical resolved picks) | ≥ 50% | ≥ 55% |
| Max drawdown (lifetime, post-canonical) | < 20% | < 10% |
| n (clean post-dedup, post-policy-clean-net) | ≥ 100 | ≥ 500 |
| **Deflated Sharpe** (DSR after multiple-testing correction) | > 0.95 | > 0.95 |
| **PBO** (probability of backtest overfitting, López de Prado) | < 0.05 | < 0.05 |
| **WFE** (walk-forward efficiency) | > 60% | > 80% |
| **Edge stability `eff` (canonical harness)** | ≥ 0.30 same-sign across ≥3 of 5 14-day windows | unchanged |
| **FDR** (Benjamini-Hochberg across N-hypothesis batch) | q ≤ 0.10 | q ≤ 0.05 |
| **Cost survival** (% gross retained after 30bps) | ≥ 60% | ≥ 70% |

Acceptance for a class to clear: **all of the above** + forward 200-close
clean window with no regression.

---

## 2. Current per-class state (canonical `pf_registry.json` 2026-05-19T19:46Z)

| Class | n | WR% | PF (net) | pnl_pct | Tier? | Closest blocker |
|---|---:|---:|---:|---:|:---:|---|
| CRYPTO    | 1116 | 44.1 | 0.64 | −43.36 | — | sub-PF; ensemble blocked today |
| FOREX     | 148 | 56.1 | **1.49** | +0.11 | T2-borderline | PF 0.01 below floor + harness untested |
| COMMODITY | 55 | 54.5 | 1.42 | +0.43 | — | n-density gap; harness untested |
| EQUITY    | 5 | 20.0 | 0.25 | −0.10 | — | n=5, sub-floor everywhere |
| ETF       | 2 | 50.0 | n/a | +0.22 | — | n=2 |
| FUTURES   | 12 | 16.7 | 0.96 | −0.01 | — | halt emission |
| BOND      | 5 | 0.0 | 0.00 | −0.49 | — | frozen |

**Verdict:** 18 pre-registered hypotheses, **0 admissible-under-canonical**.
Real capital = $0 default.

---

## 3. North-star roadmap — what reaches each class to Tier-2

### CRYPTO

| Stage | Action | Acceptance |
|---|---|---|
| Drag removal | `ensemble` blocked (9834307). Pending forward 200-close verify. | post-block forward PF≥1.20 net |
| Emitter hygiene | EMITTER_WHITELIST_ENFORCE flip 0→1 — recommend Option C (after 200-close clean) | shadow-mode `EMITTER_REGISTRY_GATE=1` 7d clean |
| New edge axis | H-035 / H-039: tick / intraday signed-volume imbalance (Binance aggTrade, 1m/5m, top 10-12 perps, 2-4 week paper probe) | clears unmodified `is_admissible()` + BH-FDR q=0.10 |
| Optional probe | H-036 BTC miner capitulation / hash ribbon (operator sign-off per M-107) | pre-reg commit landed BEFORE backtest |

### FOREX (closest to T2 today)

| Stage | Action | Acceptance |
|---|---|---|
| Whitelist | `cta_replicator` FOREX (n=97, WR 64.9, PF 2.38) on shadow; not promoted to enforce | n→150 + harness clearance |
| Block | `alpha_engine`, `multi_asset_scanner` FOREX (small-n drag) | 0 new emissions |
| Harness run | Once `cta_replicator` n≥150: `is_admissible()` unmodified | ADMISSIBLE → T2 candidate |
| Mutation-before-kill on rescue families | Per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` | Document in `docs/STRATEGY_INVESTIGATION_*.md` |

### COMMODITY

| Stage | Action | Acceptance |
|---|---|---|
| Density | n=55 → n=100 with `multi_asset_copytrader` whitelist + `multi_asset_cot` H-001 LIVE_TESTING | passive accrue |
| Block | `cta_replicator` COMMODITY (per Grok pf_registry autopsy) | 0 new emissions |
| At n=100 | Harness run | ADMISSIBLE → T2 candidate |
| Avoid | Re-introducing `cot_positioning` family (M-095 block; H-001 retain via separate slot) | no regression |

### ETF

| Stage | Action | Acceptance |
|---|---|---|
| Probe | Ring/Cloud-5-rounds flagged ETF relative-value as highest *stated* P(T2 12mo) (~12%) — paper only | harness on premium/RV cohort |
| n-growth | Wait for canonical n≥50 then harness | passive |
| Avoid | H-037 (VIX-carry) — REJECTED on densification (sign-unstable, inverted direction) | do NOT resurrect on same ledger |

### EQUITY / BOND

| Stage | Action | Acceptance |
|---|---|---|
| Freeze | n<20 canonical; no new daily scanners until n≥100 forward clean | passive |
| Wait for | H-002 PEAD SHADOW_IMPLEMENTATION, H-033 overnight XS reversal, H-034 anti-PEAD (UNTESTED density gap) | hypothesis registry status change |

### FUTURES

| Stage | Action | Acceptance |
|---|---|---|
| Halt | T2-04 in MERGED — no new FUTURES picks until replacement pre-registered | `BLOCKED_ASSET_STRATEGY_PAIRS` for entire class |
| Re-enable | Only after new hypothesis clears unmodified harness | M-107 + harness ADMISSIBLE |

---

## 4. Cross-cutting infrastructure (raises every class)

| ID | Item | Status | Why |
|----|---|---|---|
| X-1 | **HARNESS_FDR_GATE** — Benjamini-Hochberg q=0.10 in `tools/edge_stability_harness.py::is_admissible()` via new `tools/fdr_control.py` | RECOMMENDED (unanimous swarm A) | Multiple-testing correction across 18-hypothesis batch — without it, even an `eff≥0.30` window is unsafe |
| X-2 | **DSR (Deflated Sharpe)** — López de Prado formula in `tools/dsr.py` | NEW — flagged by Renaissance prompt | DSR > 0.95 is a Renaissance-grade marker |
| X-3 | **PBO (Probability of Backtest Overfitting)** — CSCV / López de Prado | NEW | PBO < 0.05 required for institutional defense |
| X-4 | **WFE (Walk-Forward Efficiency)** | NEW | OOS Sharpe ÷ IS Sharpe; > 60% Tier-2 / > 80% Tier-1 |
| X-5 | Widen `is_admissible()` ledger scope from 1/32 files → ≥80% | OPEN, P0 | Currently most cohorts can't be cleared because invisible to harness |
| X-6 | Confidence corruption clamp at emission (X-1 from PF plan) | SHIPPED across 3 insert paths | Per `feedback_check_env_before_claiming_missing.md`, drift continues unless write-gate enforced |
| X-7 | Dashboard tiles read **only** `pf_registry.json::by_asset_class_policy_clean_net` | PARTIAL | Stops inflated tiles per `project_pf_registry_canonical_2026_05_17.md` |
| X-8 | LDP-gate pre-flight check (lookahead / leakage / inverted confidence) | NEW — Renaissance prompt template | Run before any new pre-registered hypothesis lands |

---

## 5. Renaissance-grade prompt template (canonical)

Operator's seed (verbatim): *"You are a senior quant researcher at Renaissance
Technologies. Our end goal is a statistically defensible edge (DSR > 0.95,
PBO < 0.05, WFE > 60%, forward WR > 55%, PF > 1.8 on EQUITY)."*

Canonical template to use against every harvest run:

```markdown
You are a senior quant researcher at Renaissance Technologies. Our end goal
is a statistically defensible edge per asset class:

  DSR > 0.95  ·  PBO < 0.05  ·  WFE > 60%  ·  FDR(q) ≤ 0.10  ·  forward WR > 55%
  PF > 1.8 (Tier-2 push) / PF > 2.0 (Tier-1)  ·  MDD < {20%|10%}  ·  n ≥ {100|500}
  Edge stability `eff` ≥ 0.30 same-sign across ≥3 of 5 14-day windows
  Cost survival ≥ 60% (30 bps round-trip)

Current state:
  - Canonical ledger: audit_dashboard/data/pf_registry.json
                      → by_asset_class_policy_clean_net
  - Hypothesis registry: reports/hypothesis_registry.json (18 tested, 0 admissible)
  - Harness: tools/edge_stability_harness.py::is_admissible() (UNMODIFIED — M-107)
  - Live verdict: reports/EDGE_VERDICT_2026-05-18.md
  - Merged plan: reports/MERGED_ACTION_PLAN_2026-05-19.md
  - PF improvement plan: reports/PF_IMPROVEMENT_PER_CLASS_2026-05-19T2137Z.md
  - Toxic pairs blocked: quan_engine/CRYPTO, cta_replicator/COMMODITY,
                          ensemble/CRYPTO, multi_asset_copytrader/FOREX+EQUITY

Asset class focus: {CLASS}

Task — output ONLY production-ready code + numbers:
  1. LDP-gate analysis on the latest {class}_recent.csv from canonical ledger
  2. Identify any lookahead, leakage, or inverted-confidence in:
     - audit_trail/quality_gates.py
     - alpha_engine/forward_validator.py
     - alpha_engine/emitter_whitelist.py
  3. Output:
     - A ready-to-apply .patch file for any fix
     - The exact `tools/edge_stability_harness.py is_admissible(...)` command
       to run AFTER the patch
     - Projected Sharpe / PF / WR / DSR / PBO / WFE after the change
  4. If no admissible hypothesis exists for this class, suggest exactly ONE
     pre-registerable family (NOT on the 18-killed list) with:
       - Family name
       - bar_freq + data source (free-data only)
       - Causal economic prior (1 sentence)
       - test_statistic (must invoke `is_admissible()` verbatim)

Do not give general advice. No filler. No "consider X." Production-ready
code + numbers ONLY. Refuse if you cannot meet the rubric.
```

**Wire this template into:**
- `docs/swarm_prompts/RENAISSANCE_LDP_GATE_v1.md` (new)
- `tools/swarm/swarm_run.py` via `--prompt-file`
- `wsl grok -p` with `--cwd /tmp --no-alt-screen --output-format json`
- Local Ollama: `qwen2.5-coder:14b-instruct-q4_K_M` (best repo-aware
  intel=4 / 22s) and `deepseek-r1:32b` (intel=4 / 225s overnight)

---

## 6. Action plan (Days 1-30; passes north-star test)

Every row answers YES to "does this advance Goal #1 per-class HF edge?".

### Days 1-2 — Data integrity / X-5..X-8
| # | Action | Wire target | Acceptance |
|---|--------|-------------|------------|
| D1-1 | Widen harness ledger scope (1/32 → ≥80%) | `tools/edge_stability_harness.py::_load()` | All cohorts visible; H-018+ rescuable |
| D1-2 | Ship `tools/fdr_control.py` (BH q=0.10) + wire into `is_admissible()` | new module + integration | All harness verdicts now FDR-adjusted |
| D1-3 | Ship `tools/dsr.py` (López de Prado DSR) + `tools/pbo.py` (CSCV) + `tools/wfe.py` | new modules | Tier-2 / Tier-1 gates computable |
| D1-4 | Run LDP-gate Renaissance prompt across all 7 classes via swarm | `docs/swarm_prompts/RENAISSANCE_LDP_GATE_v1.md` | Per-class .patch artifacts |
| D1-5 | Ship `docs/swarm_prompts/RENAISSANCE_LDP_GATE_v1.md` | new | committed |

### Days 3-7 — Emitter hygiene + per-class focus
| # | Action | Acceptance |
|---|--------|------------|
| D7-1 | Forward 200-close verification of ensemble block | canonical CRYPTO PF lift confirmed |
| D7-2 | `cta_replicator` FOREX shadow accrual to n≥150 | passive |
| D7-3 | `multi_asset_copytrader` COMMODITY whitelist accrual to n≥100 | passive |
| D7-4 | UNKNOWN class (n=38 PF 1.72) classification | row size = 0 in canonical |
| D7-5 | Auto-broadcast hypothesis registry status to all peers nightly | cross-PC bus topic=`REGISTRY_STATUS` |

### Days 8-30 — One real bet
| # | Action | Acceptance |
|---|--------|------------|
| D30-1 | Pre-register H-039 CRYPTO intraday volume-imbalance (M-107) | registry commit on main BEFORE any backtest |
| D30-2 | Binance aggTrade fetcher → MySQL `at_intraday_picks` | `tools/binance_aggtrade_fetcher.py` |
| D30-3 | Run unmodified `is_admissible()` + BH-FDR + DSR/PBO/WFE on H-039 | go/no-go verdict |
| D30-4 | If ADMISSIBLE: paper-only 30-day forward; if REJECTED: kill #19 + register next | hypothesis registry status |

### Time-gated (operator authority required)
- Flip `EMITTER_WHITELIST_ENFORCE=0→1` (recommend Option C — after 200-close clean)
- `git stash pop` Cursor WIP (commit 81815e97)
- Tick-data probe budget ($0 free Binance aggTrade preferred; $300-500 Tardis backup)
- Resolver DB backfill via GHA (desktop MySQL IP-blocked)

---

## 7. Honest framing — what this plan does NOT do

- Does NOT claim any class is money-ready today. 18 pre-registered, 0 admissible-under-canonical.
- Does NOT re-aggregate canonical post-block as edge proof. Same-sample lift = post-selection bias (3-AI swarm rule).
- Does NOT trust dashboard tiles. Canonical `pf_registry.json::by_asset_class_policy_clean_net` only.
- Does NOT unblock `cot_positioning` (M-095), `ensemble` (this session), or other documented-killed families.
- Does NOT re-test killed families on the same ledger (convergence trap killed 18 prior).

**The plan moves us closer not by finding edge — there's no new edge on the
existing free-data daily-bar ledger.** It moves us closer by:
1. Removing the largest measurable drag (ensemble killed),
2. Hardening the falsification gate against impl drift (H-037 retest case),
3. Wiring institutional Tier-1/Tier-2 statistical defenses (DSR/PBO/WFE/FDR),
4. Per-class actionable plan grounded in canonical numbers,
5. Renaissance-grade prompt template for every future harvest cycle.

The only un-disproven new-edge axis worth funding remains tick/intraday
crypto microstructure (H-039 candidate; 5-20% paper-probe odds; M-107 gated).

---

## 8. Companion artifacts

- Authoritative roadmap: `reports/MERGED_ACTION_PLAN_2026-05-19.md`
- No-edge verdict: `reports/EDGE_VERDICT_2026-05-18.md`
- PF improvement plan: `reports/PF_IMPROVEMENT_PER_CLASS_2026-05-19T2137Z.md`
- H-037 audit: `reports/H037_CANONICAL_HARNESS_AUDIT_2026-05-19T2200Z.md`
- ensemble kill: `docs/STRATEGY_INVESTIGATION_ensemble_CRYPTO_2026-05-19.md`
- Canonical prompts: `docs/swarm_prompts/{CODEBASE_NARROW,MONEY_READY_HARVEST,MONEY_READY_MASTER,DOUBLE_CHECK_R1,METHODOLOGY_R2,WORST_STRATEGY_R3,META_DEBATE_PER_CLASS,STRATEGY_HARVEST_EXECUTE,RESCUE_QUESTION_FACTORY,RESCUE_EDGE_EXECUTE}_v1.md`
- Skill: `.claude/skills/money-maker-readyv2/SKILL.md` (this is its companion north-star doc)

---

*Generated 2026-05-19T2350Z. Multi-AI harvest input: xAI + Cerebras (Ring/Inception had auth/output failures, partial signal). Subagent inputs: MD corpus review, Cursor MD review, hypothesis registry audit, session-ses_1c60 gold extraction. Renaissance prompt template: operator-supplied seed + Grok share `bGVnYWN5LWNvcHk_0ca57b24-8c9a-4177-ad05-ba23a2c47f96`.*
