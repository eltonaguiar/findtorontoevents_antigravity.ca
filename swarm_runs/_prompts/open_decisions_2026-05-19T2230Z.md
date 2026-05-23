# Swarm consult — 2 open operator decisions

You are a quant-risk reviewer. Two decisions stand open; the operator wants a
multi-AI consensus before deciding. Provide a STRICT JSON verdict per decision
with evidence from the linked context, no filler.

## Context snapshot (verdict-grade)

- 18 pre-registered causal hypotheses, 0 admissible-under-canonical
  (`tools/edge_stability_harness.py is_admissible()` unmodified, `EFF_MIN=0.30`,
  `MIN_WINDOW_N=80`, `MIN_STABLE_WINDOWS=3`, same-sign required across all
  strong windows).
- Canonical ledger `audit_dashboard/data/pf_registry.json`
  `by_asset_class_policy_clean_net` (today, post-dedup, net-of-cost):
  CRYPTO PF 0.64 n=1116, FOREX PF 1.49 n=148, COMMODITY PF 1.42 n=55, others
  sub-floor n.
- Today: CRYPTO `ensemble` n=79 / PF 0.013 / pnl −56.3pp added to
  `BLOCKED_ASSET_STRATEGY_PAIRS` (commit `9834307`). Investigation doc
  `docs/STRATEGY_INVESTIGATION_ensemble_CRYPTO_2026-05-19.md`.
- H-037 VIX-carry: peer broadcast PASS via custom WF; canonical-harness
  audit (`reports/H037_CANONICAL_HARNESS_AUDIT_2026-05-19T2200Z.md`)
  REJECTED on densification (118/130 windows qualify, 64 NEG / 4 POS eff,
  sign-unstable + inverted direction-of-effect).
- 3-AI swarm (Grok+DeepSeek+xAI) earlier verdict on PF improvement plan:
  MAJOR_REVISION — same-sample re-aggregation = post-selection bias; all
  blocks gated on forward 200-close OR harness clearance.
- EMITTER_WHITELIST already wired by peer in **shadow** mode
  (`EMITTER_WHITELIST_ENFORCE=0`); operator's tentative flip date ~2026-05-26.

## Decision 1 — EMITTER_WHITELIST_ENFORCE flip timing

**Question:** Flip `EMITTER_WHITELIST_ENFORCE=0→1` immediately, on the
tentative ~2026-05-26 (7-day shadow review), or only after forward 200-close
verification of canonical PF lift from the recent block batch (ensemble +
copy_trader_intel + copy_trader_clones + rapid_fire + super_signals +
aggregated_picks CRYPTO; multi-asset_scanner FOREX; etc.)?

Each option:
- A: flip NOW — accept post-selection-bias risk; cuts toxic volume immediately
- B: flip on 2026-05-26 (7d shadow) — operator's current tentative plan
- C: flip only after forward 200-close clean window (~2-4 weeks)
- D: do not flip until at least one hypothesis is admissible-under-canonical

Provide verdict with evidence.

## Decision 2 — HARNESS_FDR_GATE implementation

**Question:** Cursor's `USB_MODEL_DEEP_DIVE_2026-05-19.md` recommends
`tools/fdr_control.py` (Benjamini-Hochberg / Romano-Wolf FDR) wired into
`tools/edge_stability_harness.py` so that 18-hypothesis batch p-values are
FDR-adjusted before any "proven" call. Should we implement now, and which
correction?

Each option:
- A: ship BH-FDR at q=0.10 NOW (lightweight, well-understood)
- B: ship Romano-Wolf (stronger family-wise control, more compute)
- C: ship both, gate switchable via env var
- D: defer — no admissible hypothesis exists, premature

Provide verdict with evidence and concrete wire targets.

## Output format (STRICT JSON)

```json
{
  "engine": "<your name>",
  "decision_1_whitelist_enforce": {
    "choice": "A|B|C|D",
    "rationale": "...",
    "risk_if_wrong": "...",
    "evidence_cited": "<canonical numbers, doc paths>"
  },
  "decision_2_fdr_gate": {
    "choice": "A|B|C|D",
    "rationale": "...",
    "risk_if_wrong": "...",
    "wire_target": "<exact file + function>"
  },
  "consensus_hint": "any single insight that should bind both decisions"
}
```

Be terse. Evidence-only.
