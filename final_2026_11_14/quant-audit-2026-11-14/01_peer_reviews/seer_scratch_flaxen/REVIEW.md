# Peer Review — hilarious-seer · scratch-hippodraco · flaxen-hair

**Verdict: CORROBORATED, with flaxen-hair contributing the single most actionable defect of the day.**

## hilarious-seer (`audit/hilarious-seer-quickwins-2026-11-14`, `updates/2026-11-14-hilarious-seer-audit-summary.md`)

- Verdict FAIL, consistent with everyone.
- Confirms: `hyro_pick_performance.json` 157h stale, `pick_funnel_snapshot` 404, crypto `active_raw`
  median age 89d (oldest 267d), inverse-mutation zombies since July, regime layer 21 vs 8,538 rows.
- Notes an `APIError 402` (negative balance −1.84) on `ai-gateway.kilo.ai` and a model-roster cleanup.
  **Not a trading finding** — I flag it only because a peer's research capacity degraded mid-audit,
  which is context for any thinner section of their work.
- Its proposed fixes are the same zombie-purge and freshness-guard items every peer proposed. Nothing
  to adjudicate statistically.

## scratch-hippodraco (`docs/scratch-hippodraco-audit-2026-11-14`, 12 files / 708 lines)

- Per-class quick wins (bond, commodity, crypto, equity, ETF, forex, futures, mutual funds) plus an
  overall and a peer-review file.
- **No statistical claims to test** — it is a triage checklist, and I accept it as advisory.
- Its structure (per-class folder + README + peer-review) is the cleanest of the small bundles and I
  used it as a formatting reference for this deliverable.

## flaxen-hair (`updates/2026-11-14-flaxen-hair.md`) — the important one

**Finding: `pnl_pct` / `realized_pnl_pct` are stored in mixed units — sometimes a decimal ratio
(−0.04 = −4%), sometimes a percent number (−0.7481 meaning −0.7481%) — in the same file, in the same
symbol, sometimes in the same strategy.**

They proved it by recomputation, and their worked example is decisive:

| `vix_reversal::SI=F::2026-03-11` | exit | stated | recomputed | ratio |
|---|---|---|---|---|
| row 1 | 85.0512 | −0.04244 | −0.0400 | ≈1× (ratio units) |
| row 2 | 85.3700 | −3.6402 | −0.036402 | **100× off** |
| row 3 | 85.5250 | −3.4652 | −0.034652 | **100× off** |
| row 4 | 85.7350 | −0.03228 | −0.03228 | ≈1× (ratio units) |

Why this matters beyond their own files: a 100× unit error in any input to an aggregate explains
**"impossible" numbers elsewhere in the ecosystem** — the 824× EURGBP price discrepancy deepAI found,
the `summary_picks` win rates above 100%, and any PnL-scaled size that looks absurd. It is the most
likely single cause of several defects that other peers attributed to separate bugs.

Also correct in their report:
- `institutional_picks.json` (2026-04-03) still OPEN after 7 months; `multi_asset_picks.json` all
  `forward_test_only=true` with `pnl_pct=null` — so **no verifiable live PnL exists there**.
- `confidence == ml_score` in every pick → the "ML score" is a copy, not an independent output.
- Duplicate `id` values across rows break pick-level joins.
- Empty tables in `meta_strategy.db` (`live_performance`, `walkforward_results`, `permutation_signals`,
  `meta_label_predictions`, `adversarial_compat`) while `permutation_results` holds 92,384 fresh rows —
  signal generated, outcomes never recorded. That is the same disease as `resolution_method: None`.
- **Self-retraction** of the "dbpasses.txt missing" claim (it is at `/home/eaguiar2015/dbpasses.txt`,
  outside the repo). Printing the retraction rather than silently editing is the behaviour I want to
  reward.

## What I'd add to flaxen-hair's fix list

1. Normalizing units is not enough — add a **CI assertion** that recomputes `pnl_pct` from
   entry/exit for every row and fails if `|stored − recomputed| > 1e-6` in either unit convention.
   Without the assert, the mix will return with the next writer.
2. Treat `confidence == ml_score` as a **data-integrity failure**, not a style issue: it means one of
   the two columns is decorative and the gate that consumes it is gating on nothing.
