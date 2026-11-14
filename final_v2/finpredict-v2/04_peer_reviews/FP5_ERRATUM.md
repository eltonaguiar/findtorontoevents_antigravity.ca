# FP5 Erratum — final_v2 corrections

The following corrections supersede statements in `FP5_peer_final_folders.md` and the
`final_2026_11_14` synthesis.

1. **`exit_reason`, not `resolution_method`.** The 3,500-row ledger has a populated `exit_reason`
   (SL_HIT 1,468 / TP_HIT 873 / FORCE_CLOSED 615 / TIME_EXIT 517 / UNKNOWN 22 / EXPIRED 5). The
   defect is **fill fidelity**, not exit taxonomy.
2. **PnL-unit scope.** The 100× unit-mix bug is not in the 3,500-row dashboard ledger (3,500/3,500
   within 0.05 pp). It is real in MySQL/sidefiles (17,632 percent vs 6,306 fraction rows).
3. **Stop-fill defect (new C6).** Crypto stops planned at 1.919% risk, realized 2.990%; overshoot
   +828.0 pp = 98.8% of the −837.8 pp class loss; fill-at-stop moves PF 0.768 ≈ 1.00.
4. **170-ledger benchmark.** 4 pass at 95% vs 8.5 expected by chance.
5. **FOREX counts.** 49/277 non-spot-FX (44 currency ETFs + 5 EURUSDT); 105 date-only; 44
   EST-unparseable; allowlist appears once.
6. **BOND cohort.** n=35: 34.3% WR under `status=WON`, 37.1% under `pnl_pct>0`.
7. **Peer final_v2 coverage.** `final_v2/{finpredict,finpredict-v3,flaxen-hair}` now exist on main;
   reviewed in `FP6_final_v2_peers.md`.

See `01_audit/CORRECTIONS_v2.md` for the full scope.
