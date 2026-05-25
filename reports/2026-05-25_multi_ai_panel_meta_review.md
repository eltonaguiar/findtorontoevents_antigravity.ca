# Multi-AI Panel Meta-Review — 2026-05-25

**TL;DR:** Two parallel multi-AI panels reached **opposite verdicts on the same COMMODITY question.** The difference was prompt grounding, not model capability. A 5-engine NVIDIA NIM panel (working from pre-dedup numbers) called COMMODITY the system's #1 alpha; a 3-engine codex/grok/gemini panel (shown the same numbers PLUS the leakage signals) classified it `DATA_QUALITY_LEAKAGE` at ~90% confidence. **Independent in-house verification confirmed the leakage panel.** This is the most important lesson of the session: multi-AI consensus is only as good as the prompt grounding.

---

## The two panels

### Panel A — NVIDIA NIM 5-model (DeepSeek/Roo session, 2026-05-25)

Engines: Kimi K2.6, GPT-OSS-120B, GLM-5.1, Nemotron Super 49B, Mistral Nemotron.
Prompt: per-class WR/PF/Sharpe + 7d/30d/90d windows, **without** leakage signals or dedup history.
Verdict: **5/5 agreed COMMODITY is #1 alpha, allocate 20-30%.**
Report: [`reports/2026-05-25_asset_class_edge_audit_deepseek_session.md`](2026-05-25_asset_class_edge_audit_deepseek_session.md) (Roo's audit).

### Panel B — Codex / Grok / Gemini (this session, also 2026-05-25)

Engines: OpenAI Codex, xAI Grok, Google Gemini.
Prompt: same JSON cell **PLUS** the leakage concerns (single-symbol concentration, train_pf vs holdout_pf discontinuity, source-system mechanics, prior 2026-05-16 autopsy).
Verdict: **3/3 agreed `DATA_QUALITY_LEAKAGE`, ~90% confidence**, recognized as residue from already-rejected H-001 (CFTC COT publication-lag look-ahead, REJECTED 2026-05-20 under M-095).
Reports: [`reports/2026-05-25_commodity_cot_edge_triangulation.md`](2026-05-25_commodity_cot_edge_triangulation.md) + per-engine consult files.

---

## In-house ground-truth verification

Three independent investigations (committed `28d221116` / `406661cf9` / `a93dec2af`) confirmed Panel B:

1. **DB trade-level forensics:** 87.6% (120/137) of the headline cell is one symbol (CT=F cotton); other 17 trades are wheat/soybean losses. 136 of 137 trades fall in the last 30 days, 0 in 60-90d. Mean win is +0.0255%/trade via PRICE_RESOLVED intraday drift — realistic CT=F round-trip cost (~2-4 bp) wipes the edge. Effective independent Bonferroni tests ≈ 7, not 200 (25 cells share identical trade-id sets).
2. **Filter pipeline tracing:** `top_edges.py` runs no dedup; the same source/cell collapsed PF 20.54 → 0.17 after 72h COT dedup in a 2026-05-16 swarm autopsy (cited in `quality_gates.py:5575-5581`).
3. **Merged-cohort `build_pf_registry` rerun** (the new MySQL flag `PF_REGISTRY_INCLUDE_DB=1` from `a93dec2af`): COMMODITY by_asset_class_policy_clean_net PF moves from 0.18 → **0.937** when DB is merged — well under T2's 1.5 bar, matching Panel B's prediction range of 0.3-1.0.

**The "edge" was already known-bad as of 2026-05-20.** Panel A reconstituted it from ungrounded numbers.

---

## What Panel A got right anyway

Roo's session surfaced one striking finding that does NOT depend on the COMMODITY cell and is worth following up:

> **648 un-gated picks went 0-for-648 over the 6-day window (2026-05-16 → 21), destroying −825% PnL.**
> - `moderate_confidence`: 455 picks, 0.0% WR, −1.47%/pick avg
> - `low_confidence`: 193 picks, 0.0% WR, −0.82%/pick avg
> - Meanwhile 300 gated picks (elite_a + profitable_tp) generated +994%.

If real, this is the single most powerful filter in the system — gating alone would flip aggregate PnL from −825% to +994% on the same emission. **But** the same scientific standard that debunked COMMODITY applies here:

- 0-for-455 on `moderate_confidence` is statistically implausible (p ≈ 0.5^455) on *honest* trades; the bucket may be **defined by what falls through all gates**, i.e., circular by construction.
- Need to verify whether the live system actually allocates capital to those buckets or just labels them — if they're already filtered upstream, "gate them" is a no-op.

**Action queued (NOT yet executed):** drop a verification agent on the quality-tier definition + verify the 0-for-648 claim against `audit_dashboard/data/dashboard_data.json::picks.recent_closed` filtered to 2026-05-16..21.

Roo also re-confirmed (in agreement with the .md sweep this session):
- `regime_adaptive × ETF` is the only persona×asset pair passing all statistical gates (Wilson CI 49.7–91.8%).
- `kimi_signal_tracking` is the top source-system by total PnL over the 6-day window (168 picks, WR 53.6%, +257.34%).
- `aggregated_picks` shows 74.1% WR at n=58 — interesting but underpowered for Bonferroni.

These three findings deserve verification with the same rigor that killed the COMMODITY claim.

---

## Lessons

1. **Prompt grounding is the variable, not model count.** Both panels used reputable models. The 5-engine panel reached a wrong consensus because it never saw the leakage evidence. Future multi-AI consults must include all known leakage signals + a sentence: *"Be skeptical; if the data suggests one symbol/source dominates, flag concentration risk."*
2. **Multi-AI consensus does not increase signal-to-noise on ungrounded prompts.** It compounds whatever bias is in the prompt by averaging plausible-sounding fabrications.
3. **The H-001 rejection on 2026-05-20 was real progress** — the system *had* this lesson on file. It just didn't propagate to Panel A's prompt context. The fix is operational, not statistical: when running `consult-nvidia-models` or `consult-cloudflare-models`, mandate inclusion of `reports/hypothesis_registry.json` rejected-hypothesis entries that intersect the prompt's asset class.
4. **The `build_pf_registry` MySQL extension (`a93dec2af`) is the load-bearing infrastructure fix here.** It collapsed two divergent cohorts (top_edges raw n=1219 vs verdict policy-clean n=28) into one dedup+policy+NET pipeline. Future "edge claims" can be A/B'd against the merged cohort by toggling `PF_REGISTRY_INCLUDE_DB=1`.

---

## Action list

| # | Action | Owner | Status |
|---|---|---|---|
| 1 | Save Roo's session report to canonical `reports/` path | session | DONE — `reports/2026-05-25_asset_class_edge_audit_deepseek_session.md` |
| 2 | Write this meta-review reconciling the two panels | session | DONE — this file |
| 3 | Add an `updates/index.html` card | session | DONE — same commit |
| 4 | Add incident "Multi-AI panel grounding failure" + 2 enhancements to seed_incidents_enhancements.py | session | DONE — same commit |
| 5 | Verify the 0-for-648 quality-gate claim against raw DB cohort | follow-up agent | OPEN |
| 6 | Verify `regime_adaptive × ETF` Wilson CI 49.7-91.8% claim | follow-up agent | OPEN |
| 7 | Verify `kimi_signal_tracking` / `aggregated_picks` per-source claims | follow-up agent | OPEN |
| 8 | Update CLAUDE.md guardrail to require leakage-context in multi-AI prompts | session | OPEN |

---

## Related artifacts

- Roo's original report: `audit_reports/ASSET_CLASS_EDGE_AUDIT_2026-05-25.md` and the canonical copy at `reports/2026-05-25_asset_class_edge_audit_deepseek_session.md`
- Codex/Grok/Gemini panel synthesis: `reports/2026-05-25_commodity_cot_edge_triangulation.md`
- Per-engine consult files: `reports/2026-05-25_commodity_cot_edge_consult_{codex,gemini,grok}.md`
- DB-level forensics: `reports/2026-05-25_commodity_cot_edge_deep_dive.md`
- Filter-pipeline tracing: `reports/2026-05-25_policy_clean_vs_top_edges_funnel.md`
- Pre-registered hypothesis H-101 with kill criteria: `reports/hypothesis_registry.json`
- MySQL registry extension: `tools/build_pf_registry.py` (gated by `PF_REGISTRY_INCLUDE_DB=1`)
