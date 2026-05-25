# COMMODITY COT Edge — Multi-AI Triangulation

**Date:** 2026-05-25
**Cell under review:** `conf=C0.60-0.70 & rr=RR1.0-1.5 & source=multi_asset_copytrader`
**Source JSON:** `audit_dashboard/data/top_edges_per_class.json::by_class.COMMODITY`
**Headline stats:** n=137, wr=70.07%, wr_shrunk=67.52%, PF=3.274, train_pf=24.272 (n=36), holdout_pf=2.307 (n=101), holdout_pass=true, bonferroni_pass=true (alpha=7.43e-5)
**Source/family:** `multi_asset_copytrader` + `cot` (Commitment of Traders, CFTC weekly)
**Direction:** SHORT, **Score decile:** S20

---

## TL;DR

**Consensus verdict (3/3 engines):** `DATA_QUALITY_LEAKAGE` — the candidate edge is most likely residual contamination from the same look-ahead bug that killed hypothesis H-001 on 2026-05-20. Mean confidence ~90%. **Do NOT size with real money.** One ~45-minute experiment will decisively disambiguate.

## Why this is suspicious (operator brief)

- Same `source + family + direction` as **H-001**, which was **REJECTED 2026-05-20** (rule M-095) for CFTC COT publication-lag look-ahead. Pre-fix WR 78.4% collapsed to **WR 30%, PF 0.51** after the publication-lag guard. 85% of picks were a single underlying (CT=F cotton).
- The 90-day window for the candidate edge **straddles the fix date** — so its aggregate stats average a pre-fix leaky regime with a post-fix unknown.
- The "second cell" with `trust=UNK` has **byte-for-byte identical** n=137, wins=96, PF=3.274 — it is the same trade set, confirming the 71/200 Bonferroni passes are highly correlated rather than independent discoveries.
- Under a true null, 200 tests at α=7.43e-5 should produce **0.015 false positives**, not 71. 71/200 implies the effective test count is closer to ~5-10, i.e. the Bonferroni denominator is the wrong correction.
- `multi_asset_copytrader` is an **external-scraper copy-trading source**, not a live market feed — execution slippage in copy-trading commodity futures is materially higher than a back-test assumes.

## Per-engine verdicts

| Engine | Verdict | Conf | Money rec | Key insight |
|---|---|---|---|---|
| **OpenAI Codex** (`codex exec`) | DATA_QUALITY_LEAKAGE | 90% | PAPER_ONLY | "71/200 cells passing is not 71 independent discoveries — labels share leaked information." Suggested haircut: PF 3.27 → 1.5-2.2 before leakage adjustment; expected <1.0 after. |
| **Google Gemini** | DATA_QUALITY_LEAKAGE | 95% | NO | Calls it a "data spill, not a gold mine." "When tests are perfectly correlated the effective n of the search is 1, not 200." Slippage estimate: PF 3.27 → ~1.40 live. |
| **xAI Grok** | DATA_QUALITY_LEAKAGE | 87% | NO | "Recycled leakage from a hypothesis rejected three days after registration on the identical source." Slippage estimate: 150-300 bps PF degradation; live PF often <1.0. |

Full replies: `reports/2026-05-25_commodity_cot_edge_consult_{codex,gemini,grok}.md`.

## Consensus call

**`DATA_QUALITY_LEAKAGE`, ~90% confidence, 3/3 engines.**

All three independent models converged on the same diagnosis without prompting in that direction: the headline numbers are an artifact of (a) including pre-2026-05-20 picks that were generated with look-ahead COT data, and (b) treating 200 highly-correlated cells as independent tests.

## Dissenting view

There is **no dissent on the verdict**. There is a quantitative disagreement on the slippage haircut (Codex 50-150 bps, Gemini implies ~190 bps to land PF at 1.40, Grok 150-300 bps), but all three agree the post-fix net-of-slippage PF is plausibly < 1.0.

## The single sharpest disambiguating experiment

All three engines independently proposed essentially the same test. Synthesized canonical form:

> **Time-partitioned attribution.** For the exact 137 trades in the cell, pull `signal_time`, `cot_asof`, `underlying`, `entry_time`, `pnl`. Compute four buckets crossed: (pre-fix vs post-fix 2026-05-20) × (publication-lag < 3 days vs ≥ 3 days). Report n, WR, PF per bucket plus per-underlying breakdown. **Decision rule:** if the post-fix AND lag≥3 bucket has n < 30, or PF < 1.10, or single-underlying share > 50% → REJECT. If it has n ≥ 50 and PF ≥ 1.50 and no single underlying > 25% → escalate to paper-money walk-forward.

Estimated effort: ~45 minutes of analyst time, zero capital.

## Recommendations

- **Paper money:** PAPER_ONLY contingent on post-fix subset passing the time-partitioned test above. No paper-trading on the aggregate cell as-is.
- **Real money:** **NO** until (a) the disambiguating test passes, (b) at least 60 days of *new* post-fix forward-paper picks reproduce PF > 1.30 net of realistic slippage, (c) single-underlying share < 25%, (d) timestamp audit confirms zero picks with `signal_time < cot_asof + 3 days`.
- **Process fix:** the `top_edges_per_class.json` generator should be patched to either (i) exclude pre-M-095-fix picks from the analysis window, or (ii) annotate each cell with a `pre_fix_share` field so operators can see at a glance how much of an edge predates a known leakage fix.

## Registered hypothesis pointer

Pre-registered as **H-101** in `reports/hypothesis_registry.json` per M-107 rule, status `PRE-REGISTERED`, registered_at 2026-05-25 (UTC). Predecessor: H-001. The harness `tools/audit/replay_cell_with_pubguard.py` is the only tool that may produce a verdict on this hypothesis; results must be appended to the H-101 entry, never overwritten in place.

## Coordination notes

Two parallel agents are checking adjacent dimensions of this same edge:
- **a972ec…** — statistical sanity / data quality
- **a4fa75…** — filter pipeline

When their results land, they should be cross-referenced inside the H-101 entry's `consult_panel_inputs` / new `internal_audit_inputs` section before any backtest is executed against the registered filter. This document deliberately does **not** duplicate their DB-level work; it is the external-triangulation leg only.
