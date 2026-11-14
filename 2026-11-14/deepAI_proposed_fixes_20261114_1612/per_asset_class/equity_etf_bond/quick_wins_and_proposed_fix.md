# EQUITY / ETF / BOND (+ mutual funds) — quick wins + proposed fix (deepAI, 2026-11-14)

Base f54efb3b4a (re-verify anchors). Evidence: `evidence_live_audit.json`, `cross_check_and_merge.md`.
Peer corroboration: `reports/asset_class_90day_plan_BOND_2026-05-15.md`,
`asset_class_90day_plan_ETF_2026-05-15.md`, `2026-05-25_etf_golden_long_audit.md`,
`PR-02-etf-vix-gate.md`, `PAPER_PILOT_RESOLVER_FAIL_2026-06-05.md`,
`zero_pnl_data_pipeline_audit_2026-06-05.md`.

## Quick win 1 — PASS (peer-validated): BOND — retire the sizing path, keep research-only
- **Mine:** 15 active rows all ~25h old; newest closed 98h (4.1 days); money_ready n=1 (WR 0, PF 0);
  registry n=2. Per peer zero-PnL table, BOND is 89.1% zero-resolved.
- **Peer:** "BOND is not a money-maker and should be de-prioritized for any real-money sizing ...
  n=11, PF 0.66 ... 2-symbol (TLT 79% share) concentration ... elite_score floor unreachable for
  low-vol bond ETFs ... dedicated bond emitter produces ~10 raw signals/day but 0 quality."
- **Change:** mark BOND class `RESEARCH_ONLY` in the asset-class summary; hide it from live-pick
  surfaces; keep the daily agent for data. Reuse peer's existing 90-day plan; don't reinvent.
- **Risk:** low (display + gating).

## Quick win 2 — PASS (peer-validated): ETF — contradiction must be resolved by intrabar
- **Mine:** registry ETF PF 1.84 (n=15) vs money_ready PF 0.0216 / WR 2.2% (n=45) vs 14d 0.928 (n=37).
- **Peer:** ETF was PF 1.48 / WR 58.5% / n=106 on 2026-05-15 (90-day plan) — so the Nov 2.2% is
  either a real regression or the intrabar correction of previously-nominal numbers.
  Peer `PAPER_PILOT_RESOLVER_FAIL_2026-06-05.md` proves nominal TP stats were inflated materially.
- **Change:** run the intrabar ledger (see `fixspec_single_canonical_ledger.md`) and publish ONE ETF
  number with a resolver-version tag. Until then, badge ETF "SURFACES DISAGREE".
- **Merge:** cite peer `PR-02-etf-vix-gate.md` (VIX<25 gate) as the ETF money-ready path — do not
  author a competing plan.
- **Also:** peer `2026-05-25_etf_golden_long_audit.md` found the "golden" glow is
  `display_tier='ELITE'` row styling (`template.html:8786`) applied independent of statistical edge
  — remove that cascade so styling can't imply edge.

## Quick win 3 — PASS (data verified): normalize STOCKS → EQUITY label
- Live data has both `STOCKS` (48 rows, WR 6.2%, PF 0.08) and `EQUITY` as separate classes, splitting
  sample sizes on two panels. Peer class tables also carry a separate `STOCKS` row (n=82, WR 52.4%,
  PF 0.59). Merge into one canonical `EQUITY` class (label mapping in
  `audit_dashboard/database_consolidation.py` style mapping — verify exact function on rebase).

## Quick win 4 — PASS (verified vaporware): mutual funds — remove claim or build
- No live mutual-fund picks; `alpha_engine/mutual_fund_ranker.py` absent. Options in
  `fixspecs/fixspec_mutual_fund_vaporware.md`.

## Quick win 5 — FAIL (shared): zombie purge + zero-resolve re-run for equity/ETF
- EQUITY/ETF are 79.5% / 83.1% zero-resolved (peer). Needs the shared generator filter +
  re-resolution of `backfill_widened/updated` — no class-specific quick win. See
  `fixspecs/fixspec_spot_flicker_resolver.md` (corrected to TIME_EXPIRED mark computation).

---

# Proposed fix (deeper) — ETF class surgery (universe + resolver + VIX gate)

1. **Universe:** keep the canonical `ETF_SYMBOLS` frozenset but exclude leveraged/inverse
   (SQQQ/TQQQ/UVXY) from the *headline* class stat — they distort WR/PF and are not "ETFs" in the
   money-ready sense. Report them as a separate `LEVERAGED` bucket.
2. **Resolver:** force intrabar fill assumption (SL-first when both hit in a bar) for all ETF picks;
   tag each closed row with `resolver_version`. Retire `NOMINAL_TP_LEGACY` numbers entirely.
3. **Regime gate:** implement peer `PR-02-etf-vix-gate.md` (VIX<25) — already specified.
4. **Sizing gate:** no ETF sizing until intrabar-truth n≥100 with PF>1.3 and binomial p<0.05
   (mirror peer `per_class_scrutiny` axes).

**Acceptance test:** one ETF PF number on the page (intrabar, resolver-tagged); ETF badge clears
only when n≥100 intrabar rows pass; leveraged bucket reported separately.
