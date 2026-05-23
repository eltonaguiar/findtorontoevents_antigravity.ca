# Round 2 — Converge on Money-Ready Gate Design (2026-05-19)

You are a senior quant reviewer. Round 1 (3 engines) reached strong structural
agreement but two quantitative points still differ. Converge or defend dissent.

## Round-1 consensus (agreed by all 3 — treat as settled)

**Q1:** Replace the hard `wr_ok` AND-term in `_verdict()` (money_ready_verdict.py
line 628/629) with: (a) a LOW WR sanity floor (~40% for COMMODITY/FOREX/FUTURES,
50-52% for EQUITY/CRYPTO), AND (b) a net-of-slippage expectancy hard gate, keeping
`pf_ok` (PF>=1.5) and the DSR/SPA/PBO terms unchanged. Expectancy formula:
`E = WR*(avg_win - slip) - (1-WR)*(avg_loss + slip)`, slip = per-class SLIPPAGE_BPS
(round-trip), identical to the existing shadow `_expectancy_gate()` at line 650-673.
Target: `_verdict()` ~line 628 + `CLASS_WR_FLOORS` line 169.

**Q2:** Compute MDD in `tools/build_pf_registry.py` and persist key
`max_drawdown_pct` (fraction, 0.20=20%) into every `by_asset_class_policy_clean_net`
row of `pf_registry.json`, computed from the SAME per-pick NET return series that
feeds the row's PF/WR (`aggregate(..., net=True)`). `money_ready_verdict._mdd_cvar_gate()`
keeps recomputing the live snapshot but should prefer the registry value with a
recompute fallback. Downstream: `dashboard_generator._registry_backed_ac_breakdown()`
passes it through to `asset_class_health`.

## Two OPEN points — converge in round 2

### OPEN-1: Expectancy threshold — `E > 0` or `E >= 0.5%` per trade?
- xai + kilo: `E > 0` (strictly positive, net-of-cost).
- deepseek: `E >= 0.005` (0.5% per trade) as a margin-of-safety buffer.
Decide ONE. State the exact numeric threshold the code should ship. Consider: the
gate already requires PF>=1.5 AND DSR/SPA — is an additional 0.5% expectancy floor
redundant safety or necessary buffer against estimation noise? Should it be a
fraction (0.005) or basis points?

### OPEN-2: Does COMMODITY (PF 1.78 / WR 46.9% / n=750) actually PASS the new gate?
Kilo worked an example with avg_win=1.33%, avg_loss=2.10% and got E = -6 bps
(NEGATIVE) — which would still BLOCK COMMODITY, defeating the purpose. But PF 1.78
with WR 46.9% mathematically constrains the avg_win/avg_loss ratio:
  PF = (WR * avg_win) / ((1-WR) * avg_loss)  =>  avg_win/avg_loss = PF*(1-WR)/WR
  => avg_win/avg_loss = 1.78 * 0.531 / 0.469 = 2.016
So avg_win is ~2.0x avg_loss, NOT 1.52x. Recompute E for COMMODITY with the
PF-implied ratio (slip = 12bps round-trip = 0.0012). Pick a representative avg_loss
(e.g. 1.0%, 1.5%, 2.0%) and show whether E is positive. Confirm: does the new gate
let the genuinely-healthy COMMODITY book through, while still blocking FOREX
(PF 0.27, WR 46.4%)? If COMMODITY does NOT pass at E>0, the gate design is wrong —
say so and propose the fix.

## Output (concise)
- OPEN-1: one threshold, with one-line justification.
- OPEN-2: the COMMODITY expectancy arithmetic, PASS/FAIL verdict, and FOREX cross-check.
- If you change any round-1 consensus point, flag it explicitly.
