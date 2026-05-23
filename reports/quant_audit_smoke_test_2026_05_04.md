# Quant-Audit Attachments — 3-Engine Smoke Test + Live Verification

**Date:** 2026-05-04 02:36 UTC
**Trigger:** user request to validate Kimi quant-audit attachments before deeper swarm pass.
**Engines tested:** Mercury (inception) + Grok (xai) + GitHub Copilot (npm/copilot) — copilot CLI hit Windows arg-length limit (44KB prompt > limit), substituted **openrouter / gpt-4o-mini** as Copilot stand-in for the third engine.

## Inputs

- `quant_audit_requirements.md` (483 lines / 30 KB) — master Kimi audit requirements
- `quant_audit_sec01.md` (88 lines / 12 KB) — Section 1 executive summary
- Prompt: `tmp/quant_audit_test/smoke_prompt_full.md` (44 KB, both attachments inline)

## Verdicts (3 engines, NEEDS_REVISION unanimous)

| Engine | Verdict | Top hallucination flagged |
|---|---|---|
| Mercury (inception) | NEEDS_REVISION | Equity OOS Sharpe **+3.527** unverified |
| Grok (xai) | NEEDS_REVISION | Same — Equity OOS Sharpe **+3.527** |
| openrouter (gpt-4o-mini, copilot stand-in) | NEEDS_REVISION | Meme coin "99.7% ruin probability" |

**Cross-engine consensus on coherence:** all 3 said "mostly" — sec01 covers high-level deliverables (E1, E2, E14-E16, I1-I4) but skips UI guidance (E3), HTML bug fix (E6), and exhaustive filter combination test (E25).

**Cross-engine consensus on top 3 gaps in our repo:**
1. **R:R 1.5-2.0 hard-gate not enforced in code** (C1) — 2/3 engines
2. **FOREX measurement artifacts** still present (C4) — 2/3 engines
3. **24-hour tracking window bias vs ≥120h actual resolve time** (C3) — Mercury only

## ✅ Live verification of Sharpe +3.527 against `audit_dashboard/data/dashboard_data.json`

**Direct hit:**

```
walkforward.by_class.EQUITY.oos_sharpe: 3.527
```

**Surrounding context (from same file, same EQUITY block):**

| Metric | Value | Notes |
|---|---|---|
| oos_sharpe | **3.527** | matches Kimi headline |
| oos_sharpe_std | 9.164 | wide fold-level dispersion |
| folds | 47 | reasonable sample |
| oos_wr | 57.9% | matches Kimi |
| oos_wr_std | 19.3% | wide |
| decay | 0.2 | low — good (matches Kimi) |
| consistency | 66.0% | matches Kimi |
| worst_fold_wr | 20.0% | matches Kimi |
| best_fold_wr | 90.0% | matches Kimi |

**Test-fold Sharpe distribution across 47 folds:** min = **-14.57**, max = **+23.99**, mean = +3.53 (matches headline).

**Statistical reading:**
- The +3.527 figure IS the mean Sharpe across 47 walk-forward folds (not a single point estimate).
- Fold-level Sharpe std = 9.164. Standard error of the mean ≈ 9.164 / √47 ≈ 1.34.
- **Approximate 95% CI on mean Sharpe: [0.84, 6.22]** (treating folds as IID).
- The lower bound is still positive but **the headline +3.527 understates the uncertainty**.

**Verdict on the "Equity is the only genuine edge" claim:**
- ✅ Direction is supported: mean fold Sharpe is positive across 47 folds with low decay (0.2) and 66% consistency.
- ⚠️ Magnitude is overstated: a single number "+3.527" without the std=9.164 / CI=[0.84, 6.22] context oversells the certainty.
- The swarm engines flagged this correctly. **Action:** any allocation decision derived from sec01 should use the lower-CI bound (~0.85) as the conservative Sharpe floor, not the headline +3.527.

## ✅ Live verification of "meme coin 99.7% ruin probability" claim

The openrouter engine flagged this. Quick check: the figure does not appear in `audit_dashboard/data/dashboard_data.json` (which is asset-class-level, not security-level for meme coins specifically). The 99.7% likely comes from cited external research (Pump.fun / Solana memecoin data) rather than our internal walkforward. **Status:** CITED EXTERNAL — needs verification against the original source citation in the Kimi audit; not a number we can cross-check from our own data.

## Engine performance notes

- **`copilot` CLI (npm/copilot) failed with WinError 206** — Windows command-line arg length limit. Same pattern that blocked kimi/kilo CLIs earlier this session. Consistent reproduction. **Recommendation:** for prompts >32 KB on Windows, fall back to API engines or pipe via stdin (`worker_runner.py` has a stdin path for opencode/kilo but not yet for copilot).
- **inception (Mercury)** — fast (2.79s), structured output, correct flag on Sharpe.
- **xai (Grok)** — fast (~3s), independently flagged the same Sharpe figure as Mercury — strong signal.
- **openrouter (gpt-4o-mini)** — coherent, picked a different hallucination (meme coin) — useful diversity.

## Recommended next step

Docs are READY for a deeper swarm pass with one mandatory caveat: **before any allocation decision derived from these attachments, compute the lower-CI bound for each headline figure.** A "+3.527 Sharpe" without "[0.84, 6.22] 95% CI" is the kind of number that walks people into bad decisions.

Recommended swarm composition for the deeper pass:
- `audit-resolver-v2` — verify resolver outputs match Kimi's fold-level claims
- `cross-asset-quant` — compute proper CIs with `bootstrap_ci.py`
- `forex-diagnostic-surgeon` — own the FOREX investigate-vs-kill decision (PF 0.27 / WR 46.4% / n=1169)
- `coordinator-synthesizer` — merge with explicit confidence intervals on every reported metric

🤖 Smoke test conducted by Claude Opus 4.7 (1M context); 2 of 3 engines independently flagged the same hallucination risk (Sharpe +3.527 unverified); live data verification confirmed the figure exists with wide fold-level dispersion warranting CI-based reporting.
