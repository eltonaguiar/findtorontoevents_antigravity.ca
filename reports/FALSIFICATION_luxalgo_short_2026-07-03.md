# FALSIFICATION — luxalgo_confluence SHORT edge does NOT survive entry-clean + regime controls (2026-07-03)

**Author:** claude (fable) · **Supersedes the promotable framing in `QUANT_EDGE_luxalgo_short_2026-07-03.md`.** Same-day self-correction: the candidate I flagged as "strongest honest lead" this morning fails two controls I ran this afternoon. Honesty-first; the promotion bar requires surviving scrutiny, and it doesn't.

## What triggered the re-test
While testing the `volume_spike_breakout` SHORT-inversion ("fade the pump"), an in-replay result was suspiciously good (PF 2.8–4.0). Two controls exposed it — and the same controls, applied to luxalgo, refute luxalgo too.

## Control 1 — entry_price integrity (data quality)
The honest ledger's `intrabar_pnl_pct` is resolved relative to the recorded `entry_price`. That column **mismatches the actual OHLCV bar** at signal time:
- `volume_spike_breakout`: **median 9.91%** mismatch (p90 58%).
- `luxalgo_confluence` SHORT: **median 2.92%** mismatch (p90 5.56%).

A ~3% phantom entry is large relative to luxalgo's ~0.5–0.9%/trade claimed edge, and in a **falling** market a phantom-higher short entry **systematically inflates** short PnL. This is a plausible mechanism for ledger inflation.

## Control 2 — correct-entry replay + regime control
Replaying luxalgo SHORT from the **correct bar-close entry** (eliminating the entry_price mismatch), forward window, per-symbol-day dedup, net 16bp, across bands:

| TP/SL | n | WR% | netPF |
|---|---:|---:|---:|
| 2.0/2.0 | 96 | 51.0 | **0.89** |
| 1.5/1.5 | 96 | 51.0 | 0.84 |
| 3.0/2.0 | 96 | 37.5 | 0.79 |
| 4.0/3.0 | 96 | 35.4 | 0.66 |
| 5.0/5.0 | 96 | 34.4 | 0.51 |

**Every band loses** (best 0.89). Matched **random shorts** in the same window/symbols returned netPF 0.85 (also losing) — luxalgo timing (0.71–0.89) does **not** beat shorting-anything. Contrast: in the earlier volume_spike window, random shorts *won* (1.43) purely from regime. Either way the signal adds no edge over the regime baseline.

## The reconciliation
- Ledger (production resolver, strategy's real exits): forward PF 1.56, CI-LB 1.12 → looked promotable-shaped.
- Entry-clean replay (all bands) + regime control: **0.51–0.89, no edge over random.**
- The gap is explained by (a) the ~2.9% entry_price contamination inflating the ledger in a down-market, and (b) a bearish-regime tailwind that lifts shorts generally. Neither is a durable, tradeable timing edge.

## Verdict + corrections
**luxalgo_confluence SHORT is DOWNGRADED from "strongest honest candidate" to UNCONFIRMED / likely regime+entry-price artifact. Do NOT size. Do NOT paper-pilot on the ledger number.**
- Registry `H-20260612-luxalgo_confluence_v2_short` → annotated with this falsification (status set to CONTROL_FAILED_PENDING_CLEAN_ENTRY).
- `crypto_luxalgo_short_forward_tracker.py` → caveat added: it reads the entry_price-contaminated ledger; a clean promotion requires re-resolving from correct bar entries first.
- `QUANT_EDGE_luxalgo_short_2026-07-03.md` conclusions are overridden by this file.

## The bigger, durable lesson (root cause for the whole book)
The `entry_price` column is unreliable (2.9–9.9% mismatch vs bars) across strategies, and the measurement window is a **bearish-regime** in which shorts win regardless of signal. **Any SHORT-crypto "edge" measured off `intrabar_pnl_pct` is suspect** until the ledger is re-resolved from correct, bar-aligned entries. This is the highest-priority data-integrity fix — above any strategy work: **fix/verify `entry_price` alignment, then re-run every candidate.** Until then, treat the honest ledger's SHORT-crypto numbers as an upper bound, not a verdict.
