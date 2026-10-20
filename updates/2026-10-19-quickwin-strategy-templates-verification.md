# Quick-Win Strategy Templates — Verification & Persistence (2026-10-19)

**What:** The "Quick-Win Symbols & Strategy Templates by Asset Class" task output (pasted from a
prior session) was continued here: every factual claim was traced to a repo source, errors were
corrected, current gate status was measured, and the result was persisted as
`reports/QUICKWIN_STRATEGY_TEMPLATES_2026-10-19.md`.

**Why:** The draft mixed two ledger rows (its "forex PF 0.460" is actually the EQUITY row), cited
a non-existent Santiment integration, and described an ETF TAA rule (top-3 / SHY-TLT / 12 ETFs)
that does not match the tracked implementation (top-5 / AGG / 14 ETFs). Shipping it unverified
would have put wrong numbers in front of the operator.

## Corrections made (5 factual, 2 stale)

1. **FOREX "ledger PF 0.460" → wrong class.** PF 0.460 = EQUITY (n=119, June 13 run,
   `reports/weekly_cycle_output.md` L32). FOREX honest ledger: 1.102 (n=95, Jun 13) → 1.169
   (n=101, Jun 21) → 0.611 (n=547, 2026-10-19 verdicts).
2. **FOREX "blocked until n≥100" → stale.** n cleared months ago; the real blocker is
   `reports/FOREX_NETCOST_CILB_SENSITIVITY_2026-06-13.md` — gross PF 1.79 / CI-LB 1.35 dies at
   ~1bp cost (net PF 0.46 @ 5bp). Binding gate = net CI-LB ≥ 1.15.
3. **"Santiment" stable-coin flow → doesn't exist here.** On-chain momentum is Glassnode free
   tier (MVRV-Z, active addresses, exchange balance), `alpha_engine/crypto_onchain_momentum.py`,
   BTC/ETH, default-OFF. No Santiment code in `alpha_engine/`.
4. **ETF TAA rule mismatch.** Universe is 14 ETFs (not 12), rule is top-5 (not top-3), cash slot
   is AGG (not SHY/TLT) — `tools/tactical_rotation_tracker.py` (`UNIVERSE`, `TOP_N`,
   `CASH_ASSET`). Sharpe 0.88 / MaxDD −19% claim itself ✅ verified (report L48, top5-6m row).
5. **"Filters 1–4" → the mandatory list is 1–6** plus the WR>52% EXPIRED-inclusive money-ready
   bar (`.claude/skills/money-maker-readyv2/SKILL.md`).
6. **Stale cohort claims:** EQUITY already n=229 (not "once UEPS reaches n≥100") — PF 0.837 is
   the binding failure; BOND n=0 in the current payload (was 6).

## Verified as accurate

- Tier gates PF≥1.5 / WR≥50% / MDD≤20% / n≥100 = Tier 2 of
  `alpha_engine/value_backtest.py::classify_tier` (L388).
- CRYPTO WR 32.4% / PF 0.727 (n=1155) — frozen ledger matches.
- `alpha_engine/value_screener.py` SafetyGate (Altman Z''≥1.10, Beneish M≤−1.78) and
  `alpha_engine/long_term_pick_contract.py` thesis-break rules exist as described (both opt-in
  sidecars).
- `funding_rate_arb.py::MIN_FUNDING_THRESHOLD = 0.0005` (0.05%/8h) matches the draft.
- "Only ETF TAA is money-ready" — true for the TAA *backtest track*; the ETF *pick class* is
  n=15 (INSUFFICIENT_N) and 0/9 classes pass Tier-2.

## Verification run (2026-10-19)

- `classify_tier()` executed over all 9 classes of `audit_dashboard/data/intrabar_truth_by_class.json`
  (generated 2026-06-21) → **0/9 pass** (every class `"below"`; gate-by-gate table in the report §1a).
- Live verdicts extracted from local `audit_dashboard/data/dashboard_data.json` (generated
  2026-10-18T08:34Z, then refreshed from the live site via `tools/refresh_local_audit_mirror.py`
  to the 2026-10-19T06:55Z payload — identical n/WR/PF for all 9 classes; only MDD float drift)
  → **0/9 money-ready**; EQUITY n_ok+wr_ok but pf_ok/mdd_ok fail; ETF
  pf_ok+wr_ok but n=15 (§1b).
- Implementation existence greps: `commodity_basis_carry.py`, `funding_rate_arb.py`,
  `forex_carry_*`, `bond_yield_curve_slope` emitter — all present; proposed-only rules (2s10s
  >50bp + VIX<20, 10% vol-target, yield≥2.5%/beta≤0.8 hard gates) flagged as NOT implemented.

## Artifacts

- `reports/QUICKWIN_STRATEGY_TEMPLATES_2026-10-19.md` — the verified template set (six classes,
  gates, current status, claim-by-claim audit table).
- This file — the fix log. Research/documentation only; no existing code modified.

## Follow-up (same session, "proceed on next steps")

1. **Fresh data:** ran `tools/refresh_local_audit_mirror.py` (8 payloads from
   findtorontoevents.ca, exit 0). The 2026-10-19T06:55Z payload has identical n/WR/PF for all
   9 classes vs the 2026-10-18T08:34Z copy; only MDD float drift (COMMODITY 0.16→0.1703,
   FOREX 0.985→0.9855). Report §1b updated to exact 4-dp payload values + fresh timestamp.
   Conclusion unchanged: **0/9 money-ready**.
2. **Machine-readable registry:** `reports/quickwin_strategy_templates.json`
   (`quickwin_strategy_templates/v1`) — universes, entry rules tagged implemented/partial
   with code pointers, proposed-only rules separated, evidence, track/paper-only flags.
3. **Gate-check tool:** `tools/quickwin_template_gate_check.py` — gates every template against
   live verdicts + frozen ledger via `classify_tier`; writes
   `reports/quickwin_template_gate_status.json`.
   Verified: py_compile OK; `--stdout` and write modes exit 0; missing-input path exits 1 with
   a clear ERROR (asserted); summary assertions 6/5/0/5 = templates/ledger-gated/live-pass/
   paper-only match the report. Last run: 0/5 ledger-gated pass, ETF TAA = backtest-track.
