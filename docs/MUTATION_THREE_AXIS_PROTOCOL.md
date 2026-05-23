# Three-axis autopsy before kill (mutation-first)

**Last updated:** 2026-04-08  

This extends **`docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`**. Many “losing” systems are **misapplied**: same logic wins on a **subset** of symbols, directions, or timeframes. Prefer **gated mutations** (allowlist / direction-only / TF-only) and **SANDBOX** forward tests before any hard block.

## Step 0 — Run the data slice

From repo root, prefer **tracked** closed history (no manual export):

```bash
python tools/mutation_analysis.py --json
```

Or after exporting **closed picks** from the audit dashboard to `closed_picks.csv`:

```bash
python tools/mutation_analysis.py --csv closed_picks.csv
```

Optional: save a text report and a **system×symbol** matrix CSV (allowlist / blocklist input):

```bash
python tools/mutation_analysis.py --json -o mutation_artifacts/mutation_analysis_report.txt --matrix-csv mutation_artifacts/system_symbol_matrix.csv
```

**CI:** workflow `mutation-analysis-report.yml` runs weekly, uploads `compat_matrix.csv`, and diffs against the cached previous week via `tools/matrix_diff.py` (WR drop > 15pp → `matrix_wr_decay.txt`).

**Actionable slices** (CSV columns: `system`, `symbol`, `trades`, `wins`, `wr_pct`, …):

```bash
python tools/matrix_rules_from_csv.py -i mutation_artifacts/compat_matrix.csv -o alpha_engine/data/matrix_symbol_gates.json
```

Hard gates in `audit_trail/quality_gates.py` load `matrix_symbol_gates.json` (disable with `MATRIX_SYMBOL_GATES=0`). Regenerate JSON when `closed_picks.json` meaningfully changes, then commit.

Tune thresholds:

```bash
python tools/mutation_analysis.py --json --min-trades 5 --dir-spread 20 --tf-spread 15 --sym-spread 30
```

## Step 1 — Three-axis checklist (per underperforming system)

| Axis | Question | Mutation idea |
|------|-----------|----------------|
| **Symbol** | Which symbols does it win on? | Allowlist only winners; block chronic losers (min trades first). |
| **Direction** | LONG vs SHORT WR split? | `long_only` / `short_only` or inverse pipeline (`alpha_engine/strategy_mutator.py`). |
| **Timeframe** | SCALP vs SWING vs POSITION? | Gate picks to the TF bucket with edge. |
| **Threshold-normalization** *(research, 2026-05-16)* | Are entry thresholds (momentum, RSI bands, score cut) mis-scaled vs the class's native volatility? | Re-express the trigger in **ATR / realized-vol units** instead of raw price/percent. See Step 1b. |

If **any** axis shows a large, stable split (see script output), the system may be **rehabbed** instead of killed.

## Step 1b — Axis 4: volatility / threshold-normalization mutation (research-only)

**Provenance:** P4 of `DAILY_IDEAS_LLMARENA_May162026.MD` — extracted from the
LMArena Gemini-3.1-pro "Volatility-Scaled Momentum" algorithm and swarm-vetted
(kilo: confirmed a *distinct* axis, not covered by Symbol/Direction/Timeframe).

**Problem it targets:** the same momentum/RSI/score threshold is applied across
asset classes whose native volatility differs by ~8x (FOREX realized-vol ~0.005
vs CRYPTO ~0.04). A FOREX strategy that "loses" may simply have a trigger
calibrated for a higher-vol class — its momentum never reaches the raw cut-off.

**Mutation idea:** re-express the entry trigger in **ATR units** —
`momentum_in_atr = (close - close[-N]) / ATR(14)` — and re-test the existing
strategy logic with the volatility-normalized threshold. This is a
*re-parameterization of the same signal*, so it qualifies as a gated mutation,
NOT a new strategy.

**Hard rules (same as other axes):**
- Research / SANDBOX only. NO production wiring until it clears
  `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + Step 5 mutation-quality score.
- FOREX is the first candidate (sub-floor, mutate-before-kill active). The
  normalized variant must reach **PF > 1.0 and WR > 45% over 30 days** before
  any FOREX emission resumes — otherwise FOREX stays hard-disabled.
- Apply Step 5 curve-fit guard: the volatility-normalized winning subset must
  be ≥ ~10% of total closed trades for that system.

## Step 2 — Symbol × system compatibility (matrix)

For each **(source_system, symbol)** with enough closes:

- **ALLOW** if WR ≥ ~55% and trades ≥ ~10 (calibrate from your book).
- **BLOCK symbol for that system** if WR &lt; ~40% with ≥10 trades, or &lt; ~35% with ≥5 (obvious lemon).

This is not a new strategy — it is the **same signal** with a **smarter universe**. Aligns with `audit_trail/quality_gates.py` symbol penalties where applicable.

## Step 3 — Inverse protocol

When **one direction** is clearly bad and the other good:

1. Confirm the **economic story** still makes sense if flipped (momentum vs mean-reversion).
2. Run **`TESTING_PROTOCOL.MD` §7** inverse stage / `dna_mutation_engine` inverse mutation.
3. Deploy variant with lineage (`_inverse`, `_mut_`) and **SANDBOX** trust until forward sample.

## Step 4 — Cross-asset migration

Slice closes by **asset_class** (and for equities, **sector** if you have it). Example pattern: a system is “bad on forex” but “strong on energy equities” — mutation is **sector- or asset-gated**, not global kill.

## Step 5 — Mutation quality score (avoid curve-fit)

Before promoting a gated variant:

\[
\text{MutationQuality} \approx \frac{(\text{WR}_{\text{win subset}}) \times (\text{trades}_{\text{win subset}})}{\text{trades}_{\text{total system}}}
\]

Interpretation:

- If the “winning subset” is a **tiny** fraction of all trades, the gate may be **noise**.
- Rule of thumb: winning subset should be **≥ ~10% of total closed trades** for that system (adjust with sample size and CI).

Combine with walk-forward / hold-out per **`TESTING_PROTOCOL.MD`**.

## Concrete workflow (ranked)

1. **Export** closed CSV → run **`tools/mutation_analysis.py`**.
2. **Document** top splits in a short note (strategy name, axis, allowlist proposal).
3. **Open DNA ticket**: parent strategy, mutation type (`symbol_allowlist`, `long_only`, `scalp_only`, `energy_equity_only`, etc.).
4. **Implement gate** in scanner / quality pipeline with **`SANDBOX`** tier and min forward trades (e.g. 5–20).
5. **Only after failed rehab** → consider `BLOCKED_SOURCE_SYSTEMS` (see investigation doc).

## Repo touchpoints

| Piece | Location |
|-------|----------|
| Autopsy script | `tools/mutation_analysis.py` |
| Investigation ladder | `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` |
| Rehab stages | `TESTING_PROTOCOL.MD` §7 |
| Inverse / DNA | `alpha_engine/dna_mutation_engine.py`, `alpha_engine/auto_dna_mutator.py`, `alpha_engine/strategy_mutator.py` |
