# Quant edge hunt — the strongest honest candidate: `luxalgo_confluence` SHORT (CRYPTO)

**Author:** claude (fable) · 2026-07-03 · **Method:** vol-conditional cell mining → strategy attribution → pre-registered forward test → operationalized tracker. **Verdict: FORWARD-PARTIAL** (meets WR/PF + all robustness checks; under-powered on n). **Do NOT size yet.**

## How I got here (quant chain, honest-first)
1. **Vol-conditional cell mining** on the honest intrabar CRYPTO cohort (n=1514; reconstructed 24h realized-vol at each entry from `crypto_ohlcv`, no look-ahead; per-symbol-day dedup; net 16bp). Result: LONG cells lose (netPF 0.35–0.64, CI-LB <0.4). **Both SHORT cells positive** (volhigh 1.42 / vollow 1.32) but each under-powered (21–24 symbols, CI-LB <0.9). The vol split was **not** the real axis.
2. **Pooled SHORT crypto** (n=157, 30 symbols): netPF 1.40, symbol-cluster CI-LB **1.04**, both halves >1, HHI 0.058, robust to top-symbol removal. But per-strategy attribution showed the edge is **concentrated in one strategy**: `luxalgo_confluence` (n=94, WR 59.6%, netPF 2.00); the other SHORT strategies lose. So the candidate is the *strategy*, not "short crypto."
3. **`luxalgo_confluence` SHORT — full cohort** (n=98): netPF 1.98, symbol-cluster CI-LB **1.44**, both halves >1, HHI 0.069, top-day profit share 0.15, leave-one-symbol-out worst 1.84. Clears the full battery — **but this is in-sample + strategy-selected** (data-snooping risk).
4. **Liveness + span check** (kills the "6-day snapshot" fear): picks span **2026-05-27 → 2026-07-02** (23 distinct days, top day only 17%); strategy is **live**, 114 SHORT emissions in the last 10 days, latest 2026-07-03. ~7-day hold (168 bars).
5. **Gold-standard pre-registered forward test.** The candidate was already pre-registered **2026-06-12** as `H-20260612-luxalgo_confluence_v2_short` (gate: WR≥50 / PF≥1.5 / n≥80 on post-2026-06-12 entries only). Evaluating exactly that window (zero look-ahead, zero selection):

| metric | forward value | gate |
|---|---|---|
| n (dedup) | **56** | ≥80 ✗ |
| WR | **50.0%** | ≥50 ✓ |
| net PF (16bp) | **1.56** | ≥1.5 ✓ |
| symbol-cluster CI-LB (5%) | **1.12** | >1.15 ✗ (a hair short) |
| both time-halves PF | **1.77 / 1.35** | both >1 ✓ |
| single-name HHI | **0.076** | <0.15 ✓ |
| top winning-day profit share | **0.32** | <0.50 ✓ |

## Honest verdict
`luxalgo_confluence` SHORT (CRYPTO) is the **program's strongest honest candidate**: on the clean pre-registered forward window it **meets WR≥50 + PF≥1.5 and passes every robustness check** (both-half, diversification, not crash-driven). It is **not yet promotable** — forward n=56 (< 80) and CI-LB 1.12 (< 1.15). The eye-catching in-sample CI-LB 1.44 (n=98) was inflated by discovery-window data; the forward-only number is the honest one. **Economic prior:** systematic SHORT of pumped alts (JUP/AVAX/RENDER/SOL/XRP…) — mean-reversion of crowded longs; structurally plausible, diversified across 15 names.

## What I implemented (the only honest deployment: FORWARD-lane)
- **Operationalized the candidate:** `tools/crypto_luxalgo_short_forward_tracker.py` — read-only sidecar that recomputes the promotion-gate battery (net-PF symbol-cluster CI-LB, both-halves, HHI, crash-fade) on the pre-registered forward window every run, writes `audit_dashboard/data/crypto_luxalgo_short_forward_status.json`, and flips to `PROMOTABLE_PROBATION` only when n≥80 **and** CI-LB>1.15 **and** the 3 robustness gates hold. Current: `SHADOW_TRACKING`, failing only `n_ge_80` + `ci_lb_gt_1_15`.
- **Updated the registry** entry `H-20260612-luxalgo_confluence_v2_short` with the forward result + verdict.

## Next gate
At the current emission rate, forward n should reach 80 in ~2–3 weeks (~mid/late-July). When the tracker flips to `PROMOTABLE_PROBATION`, re-falsify (fresh symbol-bootstrap + a swarm adversarial pass), then a small **paper** pilot — never size on this in-sample/forward-partial state. Suggested wiring: add the tracker to the hourly audit-dashboard workflow next to `crypto_rsi5070_forward_tracker.py`.
