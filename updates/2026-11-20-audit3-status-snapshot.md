# audit3 / audit2 status snapshot — 2026-11-20T04:00Z

Single authoritative view of what is live, what is measured, what is blocked, and
how to verify each claim. Every number below was read from the live artifacts at
the timestamp shown.

---

## 1. Live surfaces

| Surface | State | Data source |
|---|---|---|
| `findtorontoevents.ca/audit3/` | 200 | `audit3_ledger.json` |
| `findtorontoevents.ca/audit2/` | 200 | `audit3_ledger.json`, `audit2_forward.json`, `audit2_pods.json` |
| `findtorontoevents.ca/audit/` | 200 | `dashboard_data.json` + sidecars |
| Canonical ledger | `generated_at 2026-11-20T03:56:27Z` | sidecar sha256 verified |

## 2. The book (audit3)

```
coverage.mode           canonical
scored / valid          8,769 / 8,769   (basis: canonical_kept_rows, share 100.0)
verdicts                PROVEN 0 · CANDIDATE 0 · WEAK 59 · KILL 8
kill classes            CRYPTO, FOREX, COMMODITY
persistence             on (2 consecutive runs required, 444 cells tracked)
verdict churn           0 / 444
denylist hits           55 (CRYPTO 33, COMMODITY 8, …)
```

Gates in force on every cell: net-expectancy bootstrap CI, 2× cost stress
(**required for PROVEN_T2**; failing it caps at CANDIDATE), cost-scaled
materiality floor (max(0.05%, 0.5×cost)), split-half stability, recency (trailing
window mean ≥ 0), DSR at the **global** trial count, BH FDR, concentration caps,
and selection alpha where a sidecar exists.

## 3. Forward clock (the only path to PROVEN)

```
ledger rows             430 (H-119 only; idempotent since 2026-11-19)
hypotheses listed       10 (H-119 + 9 pods, 0-row pods included by design)
gate                    enforced
H-119 blocking clauses  PF CI-LB 0.9213 ≤ 1.0 and IR 0.043 < 0.5
                        benchmark coverage 0.798 < 0.90
next ingest             06:41 UTC (every 6h, offset from the ledger's :23)
```

Ingest conditions were wired on 2026-11-20 for the three pods whose strategies
actually emit — `etf_faber_tactical` (468 picks), `etf_dual_momentum` (393),
`contango_roll_yield` (10) — and all six pod hypothesis ids were verified present
in the registry, so the 06:41 run is the first that can add rows.

## 4. Enforcement

`denylist_hits` is written by the scanner into
`alpha_engine/data/audit3_denylist_hits.jsonl`, committed by
`alpha-engine-live.yml`, summarised in the ledger and on `/audit3`, and reviewed
automatically by `audit3-health.yml`. First measured review (27 denials, all
KILL-class aggregates) is recorded in
`updates/2026-11-19-denylist-first-review.md`.

## 5. Guards added after the 2026-11-19 outage

| Guard | File |
|---|---|
| CLI smoke (parser, kwargs, constants) | `tests/test_audit3_cli_smoke.py` |
| End-to-end ledger canary (real flags) | `tests/test_audit3_ledger_e2e.py` |
| Hypothesis status normaliser | `alpha_engine/hypothesis_status.py` |
| Denylist hit log + review CLI | `alpha_engine/audit3_denylist_hits.py` |
| Ledger freshness alarm (12h warn / 24h fail) | `.github/workflows/audit3-health.yml` |
| Denylist staleness watchdog (3-day fail) | `.github/workflows/audit3-denylist-watchdog.yml` |
| Pod emission audit (15/23 phantom today) | `tools/pod_emission_audit.py` |
| Strategy freeze gate | `tools/strategy_freeze_gate.py` |

## 6. Blocked on credentials — exact commands

```bash
# 1. Price backfill (enables FX/equity selection alpha)
python3 tools/fx_backfill.py --dry-run          # already verified: 15 pairs × 203d
python3 tools/fx_backfill.py --apply            # needs DB creds
python3 tools/backfill_daily_ohlcv.py --symbols BBAI,CHPT,CLSK,NIO,SNAP --apply

# 2. Source mislabel (NZDUSD=X stored as CRYPTO)
#    fix the row in bt_backtest_runs, then re-run the evidence registry

# 3. Benchmark coverage for H-119 (0.798 → ≥0.90)
#    needs price joins for ~87 rows; no code change required
```

## 7. Blocked on a human decision

- **Rotate the FMP key** removed from `audit_dashboard/template.html`.
- The **strategy freeze** stays on until E11/E13/E14 close; `forward-test-new-strategies` is therefore red by design.
- 15 of 23 manifest strategies emit nothing: implement, rename to a real emitter, or retire. `tools/pod_emission_audit.py --strict` is ready to enforce once the manifest is amended.

## 8. How to verify everything here

```bash
pytest tests/test_audit3_*.py tests/test_forward_observations*.py \
       tests/test_audit2_forward_summary.py tests/test_strategy_freeze_gate.py -q
python3 -m alpha_engine.audit3_tribunal --picks /tmp/audit3/dashboard_data.json \
  --out /tmp/audit3/ledger.json
python3 -m alpha_engine.audit3_denylist_hits
```

*Not investment advice. Nothing here is a promotion; 0 PROVEN / 0 CANDIDATE.*
