# Renaissance LDP-Gate Prompt v1 — 2026-05-19 / 2026-05-20

**Source:** Operator-supplied seed (Grok share `bGVnYWN5LWNvcHk_0ca57b24-8c9a-4177-ad05-ba23a2c47f96`) + verbatim 4-prompt suite extracted from `bGVnYWN5LWNvcHk_3251982f-f5b3-41e8-846a-999e8d51b78e` via scrapling StealthyFetcher (commit `671f9b4` reports/GROK_SHARE_EXTRACTION).

**Use when:** harvesting Renaissance-grade quant-research insights against the repo. Run via `tools/swarm/swarm_run.py --prompt-file docs/swarm_prompts/RENAISSANCE_LDP_GATE_v1.md`, `wsl grok -p`, `tools/grok_share_fetcher.py`, or local Ollama (qwen2.5-coder:14b balanced; deepseek-r1:32b overnight).

---

## Prompt 1 — Full system audit (Lopez-de-Prado-level)

You are a world-class quant researcher (Lopez de Prado level). Audit this
entire repo: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/

Focus ONLY on the prediction pipeline (`alpha_engine`, `feature_store`,
`data_pipeline`, `backtest_results`, `audit_trail`).

Identify every source of:
- Lookahead bias
- Survivorship bias
- Data leakage
- Inverted confidence
- Strategy decay

Then propose concrete fixes + new validation gates (WFE, CPCV, DSR, PBO, MinTRL).

Output ONLY in this format:
1. **Leakage inventory** — `file:line` + 1-line description
2. **Confidence recalibration plan** — exact change to `audit_trail/quality_gates.py` + `alpha_engine/config.py`
3. **New readiness gates** — additions to `.github/workflows/audit-dashboard.yml`
4. **One new strategy skeleton per asset class** that would pass the new gates — entry/exit/feature list with no lookahead

## Prompt 2 — Strategy regeneration (Ring-2.6-1T / GLM-5.1)

Act as a senior quant PM. We have poor forward WR and inverted confidence
across asset classes. Using ONLY the data schema from `database/` and the
current `feature_store`, generate 3 new high-conviction strategy ideas
(one each for EQUITY, CRYPTO, COMMODITY) that **explicitly avoid the
failures in `failed_strategies/`** (the 18 pre-registered hypotheses that
failed canonical harness).

Per idea:
- Entry / exit rules
- Feature list (no lookahead — point-in-time enforcement required)
- Walk-forward test plan (purged + embargoed CPCV; `CPCV_EMBARGO_DAYS=2`
  minimum)
- Expected statistical edge (Sharpe target, MinTRL)
- Causal economic prior (1 sentence — what mechanism creates the edge)

## Prompt 3 — Confidence + scoring fix (MiMo / Claude)

Our `ml_score` is inverted (high score → low WR per `reports/PF_IMPROVEMENT_PER_CLASS_2026-05-19T2137Z.md`).

Fix the scoring booster in `alpha_engine/config.py` and `audit_trail/quality_gates.py`
so confidence becomes monotonic with forward performance.

Propose a new hybrid score:
- `hybrid_score = w1·ml_score + w2·regime_factor + w3·freshness + w4·forward_wr_30`
- Show the math: why each weight; how the components compose
- Code-ready Python signature compatible with `audit_trail/quality_gates.py::passes_active_gate`

(Grok-provided reference implementation in `reports/GROK_SHARE_EXTRACTION_2026-05-20T0110Z.md` §3 fix2.)

## Prompt 4 — GitHub Actions upgrade

Add automated gates to `.github/workflows/audit-dashboard.yml`:

1. Run full CPCV + DSR + PBO on every new pick batch
2. Auto-quarantine any strategy with forward WR <48% or PF <1.2 over rolling
   30 days
3. Alert on confidence inversion (`corr(ml_score, forward_wr) < 0` over n≥30)
4. Remove `continue-on-error: true` from critical-gate steps (resolver,
   A/B analysis, PF verify, zero-PnL detector); only allow on cosmetic /
   deploy steps

---

## Tier gates (institutional thresholds — non-negotiable)

| Gate | Tier-2 (Charter) | Tier-1 (Renaissance) |
|------|------------------|----------------------|
| Profit factor (net 30bps round-trip) | ≥ 1.5 | ≥ 2.0 |
| Win rate (canonical resolved) | ≥ 50% | ≥ 55% |
| Max drawdown (lifetime canonical) | < 20% | < 10% |
| n (clean post-dedup, post-policy-clean-net) | ≥ 100 | ≥ 500 |
| **Deflated Sharpe (DSR)** — López de Prado | > 0.95 | > 0.95 |
| **PBO** — probability of backtest overfitting (CSCV) | < 0.05 | < 0.05 |
| **WFE** — walk-forward efficiency (OOS Sharpe ÷ IS Sharpe) | > 60% | > 80% |
| **Edge stability `eff`** — same-sign across ≥3 of 5 14-day windows | ≥ 0.30 | unchanged |
| **FDR** — Benjamini-Hochberg across N-hypothesis batch | q ≤ 0.10 | q ≤ 0.05 |
| **Cost survival** (% gross retained after 30bps) | ≥ 60% | ≥ 70% |

**Acceptance for a class to clear: ALL of the above + forward 200-close clean
window with no regression.**

---

## Output rules (binding for every engine consult)

- **No filler.** No "consider X" or "you might want to" — production-ready
  code + numbers ONLY.
- **No general advice.** Every recommendation must cite a specific
  `file:line` or a `tools/...` path.
- **Refuse to fabricate.** If an engine cannot verify a claim against actual
  repo content, mark it `UNVERIFIABLE` and move on. The convergence trap
  (`feedback_multi_ai_convergence_trap.md`) is enforced: cross-engine
  agreement on a fabricated pattern is NOT verification.
- **Cite the canonical ledger.** `audit_dashboard/data/pf_registry.json`
  `by_asset_class_policy_clean_net` is verdict-grade. Raw dashboard tiles
  are inflated.
- **Honest framing on edge.** 18 pre-registered hypotheses tested → 0
  admissible-under-canonical. Paper-only is the honest default. Real capital
  waits on harness clearance + BH-FDR q=0.10 + forward 200-close window.

---

## Reference companions

- Tier-2 / Tier-1 charter: `reports/MONEY_MAKER_READYV2_NORTH_STAR_2026-05-19T2350Z.md`
- No-edge verdict: `reports/EDGE_VERDICT_2026-05-18.md`
- Hypothesis registry workflow: `.claude/skills/hypothesis-registry/SKILL.md`
- Canonical harness: `tools/edge_stability_harness.py::is_admissible()` (UNMODIFIED — M-107)
- Recent bug-fix batch (2026-05-20): DSR NaN-safe + PBO embargo env-configurable + resolver MySQL path live
  (commits b19d6d6, a58f20d, 632eca0, 5f8338b, f1370a3)
- Grok-supplied verbatim patches: `reports/GROK_SHARE_EXTRACTION_2026-05-20T0110Z.md` §3
  (`lopez_de_prado_gates()` + `hybrid_score()` ready-to-apply)

---

*Generated 2026-05-20T0345Z. Bind to commit at apply-time. M-107 binding:
the unmodified `is_admissible()` is the gate; any local custom walk-forward
that "passes" is M-107 drift and does not constitute admissibility (cf.
H-037 retest, `reports/H037_CANONICAL_HARNESS_AUDIT_2026-05-19T2200Z.md`).*
