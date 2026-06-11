# Money-Maker-Ready Audit — 2026-06-11 (focus: forward-tested performance + integrity gaps)

## 0. Freshness preflight
Live `dashboard_data.json` 1.8h old — PASS. Intrabar ledger + entry-conditions lane current. Loop heartbeats GREEN ×15 prior.

## 1. Forward-tested performance (the honest surfaces)
| Surface | State | Verdict |
|---|---|---|
| Intrabar ledger (canonical) | CRYPTO n=1154 32.4%/PF0.73 · EQUITY n=107 34.6%/0.47 · COMMODITY n=90 41.1%/1.39 · FOREX n=88 42.0%/1.13 · MEMECOIN 26%/0.58 · ETF 0/16 | **0/9 money-ready; 2 classes at n≥100 both FAIL** |
| Entry-conditions forward lane | crypto_rsi5070_us (CRYPTO\|108\|since 05-27) 47.2%/PF1.54, 30d 48.3%/1.45 — below 50% bar; luxalgo_short (CRYPTO\|38\|30d) 71.1%/2.21 recency-bound; forex_trend_aligned (FOREX\|14) 64.3%/4.74 small-n | tracked, none promotable |
| Strategy-sweep forward-observation | crypto_eu_us_handoff LONG (CRYPTO\|536\|5mo replay) PF1.38 net — re-test ~2026-07-09 on post-06-10 entries only | pre-registered |
| Tournament (per-model) | NOW honest at source: 1,453 legacy re-resolved 06-11 (paired WR 50.9→41.2); REPLAY-only holds (0 regressions across 15 checks) | fixed this session |
| **Walk-forward suite** | **generated 2026-04-15 — TWO MONTHS STALE** (predates honest resolver, kills, caps) | **GAP — incident #132 (P1)** |
| fwd_vs_bt_divergence | 0 rows (not computed on current cohort) | unverifiable — recompute with WF refresh |
| concept_drift | **drift_alert TRUE** (detail fields absent in payload) | flag — investigate with WF refresh |

## 2. Integrity gaps found (the operator's exact question — and yes, they were there)
1. **(FIXED) Backfill resurrected corrupt-exit rows** — the 06-10 NULL-pnl recovery recomputed pnl from corrupt exit prices: (FOREX|1|06-06) AUDUSD=X exit 663.13 on 0.70 entry = **+93,965% TP_HIT**; (EQUITY|1|06-06) SOFI +2,280%; (CRYPTO|~80|Mar-Apr) TRXUSDT exits pinned at stale 0.06697. Sign-coherence passed them (corrupt LOSSes are sign-coherent). **87 rows re-quarantined** (backup `tp_xsym_contam_q2_20260611T214419Z`); price-sanity guard added to `backfill_resolved_pnl.py` (0b0106c34c). Incident #130 (P1) stays OPEN for the upstream exit-price writer (mirror of the entry-scale guard af1794dfc2 needed at resolution-write).
2. **(OPEN #131, P2) Terminal NULL-pnl regrowing**: 737 rows (was 131 post-recovery); active writers multi_asset_copytrader (19:13 today), alpha_engine, cta_replicator close picks without pnl.
3. **(OPEN, noted) Duplicate emissions**: 2,585 dup rows beyond (sym,strat,dir,day) in 7d — signal-week dedup covers gated callers only; ungated writers keep inflating correlated n. Analytics dedup protects verdicts; emission hygiene remains leaky.
4. **Reverse-split skew**: registry working — no NEW unguarded split rows in 30d closes beyond the corrupt-exit class above (UNH 99.5/NVDA 80.3 are vol-window TIME_EXIT marks, not splits). The 06-06 SOFI/AUDUSD rows were wrong-symbol feeds, not splits.
5. **Layer-A optimism quantified**: ETF health 69.6%/PF2.93 (n=23) vs intrabar **0 TPs in 16** — never cite Layer A for ETF; intrabar is canonical.

## 3. Best-Possible-Actions (ranked)
| P | Action | Why |
|---|---|---|
| P0 | Exit-price ratio guard at resolution-write (incident #130) | kills the corruption class at the source; one writer bug can flip class verdicts |
| P1 | Re-run walk-forward on the honest cohort + freshness gate (#132) | forward verification currently unusable |
| P1 | Fix the 3 NULL-pnl writer paths (#131) + cron the guarded backfill | stops the silent PF/WR blind spot |
| P2 | Investigate concept_drift alert detail with the WF refresh | drift TRUE with no D detail = unactionable today |
| P2 | Extend signal-week dedup to ungated writers | emission hygiene |
| OPERATOR | rotate 50webs pw · FRED/CFTC keys in CI · #129 test-discipline policy | unchanged |

## 4. Verifiable claims log
Quarantine: `ejaguiar1_backups.tp_xsym_contam_q2_20260611T214419Z` (87 rows). Guard: tools/backfill_resolved_pnl.py @ 0b0106c34c. Incidents #130/#131/#132 live on /audit/incidents.html. Probes reproducible via the SQL in this session's MASTER_PROGRESS log. Intrabar: `python3 tools/build_intrabar_truth_by_class.py --stdout`.
