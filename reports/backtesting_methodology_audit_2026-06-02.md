# Backtesting Methodology Audit (2026-06-02) — MISSING, restored as stub

**Status:** ORIGINAL FILE ABSENT ON DISK. This stub replaces the missing `reports/backtesting_methodology_audit_2026-06-02.md` so citations in docs/BACKTEST_ADMISSIBILITY_STANDARD.md, updates/EAGLE_JUNE2_GPT-5.4.MD, reports/EAGLE_JUNE2_GROK.md, reports/quant_strategy_root_cause_review_2026-06-02.md, and reports/EAGLE_JUNE2_COMPOSER.md do not 404.

**What was in the original (per citations):** An audit of backtesting engine fragmentation — ~80% of academic strategies use `real_data_backtest.py` without purge/embargo/DSR; promotion labels on lab files do not apply to tournament + mercury2 + battleground volume; engine bifurcation between rigorous and non-rigorous backtest paths.

**Current canonical replacement:** See `docs/BACKTEST_ADMISSIBILITY_STANDARD.md` (M-108 admissibility standard) and `alpha_engine/audit3_tribunal.py` (the audit3 decision ledger, which subsumes this methodology audit). The per-asset-class harness results live in `reports/hypothesis_registry.json` and `alpha_engine/audit3_edge_hunt.py`.

**Why missing:** The original file was removed or never committed; the M-108 admissibility standard (docs/BACKTEST_ADMISSIBILITY_STANDARD.md) supersedes it. Do not cite this stub as evidence — cite docs/BACKTEST_ADMISSIBILITY_STANDARD.md instead.

**M-108 gate:** Any hypothesis claiming an edge must pass edge_stability_harness.is_admissible() UNMODIFIED + post-cost gate before promotion. No hypothesis in the current registry clears all six repo gates for live capital.
