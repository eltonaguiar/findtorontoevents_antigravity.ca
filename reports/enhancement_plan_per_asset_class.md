# Enhancement Plan per Asset Class (2026-05-15)

## EQUITY

- **M-009 PEAD Strategy on EQUITY top-100**  
  - Scaffold `alpha_engine/strategies/pead_equity.py`.  
  - Define 2‑day post‑earnings window, backtest against n≈447 equities.  
  - Wire into `score_pick` reporting and `passes_active_gate`.  

- **M-026 EQUITY day‑of‑week tilt (Tue/Wed long bias)**  
  - Add environment flag `EQUITY_DOW_TILT=1` in `alpha_engine/config.py`.  
  - Enable tilt in `score_booster.py` when flag is set.  
  - Validate via telemetry that bias improves WR ≥0.5 pp on live tape.  

- **M-013 ConcentrationChecker production wire‑up (5 %/symbol hard‑cap)**  
  - Integrate `ConcentrationChecker` into `passes_active_gate`.  
  - Enforce 5 % per‑symbol cap; block sizing on violation.  
  - Deploy via PR #885 author; monitor dashboard for cap activations.  

- **M-006 HIGH_CONVICTION dashboard swap (confidence → trust_score)**  
  - Update `audit_dashboard/template.html` JS filter to use `trust_score >= 0.6`.  
  - Smoke‑test on UX; ensure HC panel delta ≤10 % in n.  
  - Deploy as part of P0 UX sprint.  

- **M-036 ETF universe expansion (XLF/XLE/XLK to n→150)**  
  - Add tickers to `alpha_engine/config.py` symbols list.  
  - Emit new symbols via `dashboard_generator`.  
  - Size at Rung‑5 (0.1 % per symbol) until PF >1.5.  

- **M-023 sector_dual_momentum_12_1 (ETF)**  
  - Implement research module `tools/research/sector_dual_momentum.py`.  
  - Offer as opt‑in side‑car; require “## Wiring Plan” in PR.  

- **M-017 Position sizer rebuild (stand‑alone)**  
  - Re‑implement `alpha_engine/position_sizer.py` without PR #1017 dependencies.  
  - Add vol‑target + max‑per‑name logic.  
  - Wire into `score_pick` reporting.  

## COMMODITY

- **M-021 COT lag‑corrected re‑run + paper‑pilot (≥75 % on n=100)**  
  - Apply 3‑day publication lag to COT data in `audit_trail/universal_pick_resolver.py`.  
  - Re‑run historical analysis; if WR ≥50 % on paper pilot, promote to live.  

- **M-039 Cross‑commodity spread (crude/natgas pair) research module**  
  - Develop `tools/research/commodity_carry_momo.py` for double‑sort spread.  
  - Validate against live data; gate behind concentration check.  

- **M-050 Cotton (CT=F) live‑pilot — 30 picks @ projected PF on live tape**  
  - Charter Stage F entry; daily reconciliation of picks vs PnL.  
  - Require 30‑day rolling PF >1.5 and WR >50 % before scaling.  

- **M-048 Frontend Binance API‑call ban + audit**  
  - Search `audit_dashboard/` for `binance.com` / `api.binance.com` fetches.  
  - Replace with backend proxy; add CORS and rate‑limit safeguards.  

- **M-052 PBO/CPCV harness per Lopez de Prado**  
  - Implement PBO/CPCV per‑strategy harness; run against COMMODITY first.  
  - Surface edges that survive structural overfitting; add to `asset_class_analysis_results.json`.  

- **M-051 Multi‑model swarm ensemble (Sonnet/Haiku/Grok/DeepSeek/Claude)**  
  - Swap one persona to Sonnet; measure WR delta.  
  - Deploy as opt‑in side‑car; require “## Wiring Plan”.  

## CRYPTO

- **M-001 BTC UTC‑hour death‑zone filter (reject 08‑09 Z, boost 22 Z)**  
  - Add `_hour_filter()` to `alpha_engine/score_booster.py`.  
  - Gate via `CRYPTO_HOUR_FILTER=1`.  
  - Telemetry: 8‑hour rejection cuts drawdown ≥10 % on live tape.  

- **M-004 CRYPTO drag autopsy + auto‑quarantine (>40 % vol & PF<1)**  
  - Add quarantine routine to `quality_gates.py`.  
  - Write probation JSON when vol>40 % && PF<1.  
  - Auto‑exclude from sizing until WR recovers.  

- **M-034 Confidence‑inversion gate (cloud‑agent +56 lines)**  
  - Implement gate that inverts confidence when `cloud_agent_claims_validation` fails.  
  - Wire at `passes_active_gate`; block low‑confidence picks.  

- **M-027 FUTURES Thursday short momentum (+2.56 % n=9)**  
  - Add DOW gate; require n>30 before sizing.  
  - Deploy as opt‑in side‑car; track WR on live tape.  

- **M-028 Drift‑pause auto‑flip dry‑run (Phase 4.1)**  
  - Add drift‑pause logic to `audit_trail/quality_gates.py`.  
  - Dry‑run mode; flip `sizing_allowed` flag on breach.  

- **M-049 Kill‑switch RED → physical halt verification audit**  
  - Verify `performance_alerts[].action=HALT` actually refuses fills.  
  - Add audit test to CI; flag any deviation.  

## FOREX

- **M-007 FOREX_HARD_DISABLE env switch (default ON)**  
  - Add flag in `alpha_engine/config.py` to disable FOREX trading.  
  - Wire into `passes_active_gate`; emissions become 0 when enabled.  
  - Document override condition (carry PF>1.0 && WR>45 % on 30‑day roll).  

## ETF

- **M-036 ETF universe expansion** – already listed under EQUITY (shared).  

## BOND

- **M-020 Walkforward validator output path**  
  - Mirror PR #940 COMMODITY pattern; add path for BOND results.  
  - Enable downstream consumption by dashboard.  

- **M-024 `ust_tsmom_level` BOND TSMOM**  
  - Implement TSMOM on TLT/IEF/SHY; backtest against live data.  

- **M-013 ConcentrationChecker** – also applies to BOND (shared).  

- **M-032 FRED macro filter wire‑up (regime context)**  
  - Add FRED_API_KEY secret; read regime context into `alpha_engine/config.py`.  
  - Use for regime‑specific gating.  

## CROSS‑ASSET / INFRASTRUCTURE

- **M-002 DB Freshness Guardian GH workflow**  
  - Create `.github/workflows/db-freshness-guardian.yml`.  
  - Use `tools/db_freshness_check.py` to read `ejaguiar1_stocks` & `ejaguiar1_backtests`.  
  - Emit `audit_dashboard/data/db_freshness.json`; alert if staleness >60 min.  

- **M-005 Cross‑DB strategy/system key consistency audit**  
  - Run `tools/cross_db_consistency.py` daily at 06:00 Z.  
  - Verify consistency across asset‑class DB schemas; flag mismatches.  

- **M-014 Confidence schema 0‑1 normalizer (clamp pending)**  
  - Add clamp at `dashboard_generator._normalize_pick`.  
  - Deploy after calibrator wired (partial‑PR‑1026).  

- **M-042 Cursor verification‑matrix scaffold**  
  - Build `tools/build_verification_matrix.py` → `reports/verification_matrix.json`.  
  - Include fields: item_id, claimed_status, evidence_found, verification_command, result, confidence, blocker.  

- **M-044 Canonical gate‑policy parity test (extend PR #1030 P0.2)**  
  - Extend test suite to cover all gate‑config readers.  
  - Ensure no drift between config sources.  

- **M-045 Pre‑work observability PR (caller‑wiring for PR #1026 scaffolds)**  
  - Wire `slippage_validator`, `safety_status`, `protocol_state` callers.  
  - Add observability fields to payload.  

- **M-046 Validation‑harness PR (payload schema + gate parity + freshness preconditions)**  
  - Build deterministic pass/fail commands in `tools/validation/`.  
  - Align with PR #1030 P0.2.  

- **M-047 Sprint‑sizing correction: resolver backfill = 2‑week, not weekend**  
  - Update effort label from M to L in master TODO.  
  - Communicate revised timeline to operator.  

- **M-043 DB credentials env‑var‑only enforcement (secret‑scan in GHA)**  
  - Add `gitleaks` or `trufflehog` job to PR‑validation workflow.  
  - Fail on secret exposure; rotate compromised PATs.  

- **M-041 Slippage validator + safety_status + protocol_state wire‑in**  
  - Add callers in `score_pick` / `passes_active_gate`.  
  - Deploy scaffolds from PR #1026.  

- **M-030 last_signal_date in `systems` payload**  
  - Field write in `dashboard_generator`.  
  - Enable staleness detection on /audit.  

- **M-031 readiness.by_class payload (Codex state‑machine fields)**  
  - Add payload key; consumer on /audit.  

- **M-049 Kill‑switch RED → physical halt verification** – cross‑asset (shared).  