# FINAL NOTES — kilo (deepseek-flash via Kilo extension, Linux)

**Written:** 2026-11-20T02:20Z · **Seat:** `inbox/gx10-c9b9/vanilla-handsaw/kilo`
**Source repo:** `eltonaguiar/findtorontoevents_antigravity.ca` @ `main` (`515591f5d45` at write time)
**Review package:** `eltonaguiar/antigravity_review_Nov192026`, folder
`artifacts/2026-11-19T2308Z_linux-kilo-ext_deepseek-flash/`

---

## 1. Bottom line

The measurement layer is now auditable and the forward clock has started. **Nothing is
money-ready**: 0 proven cells, 0 candidates, selection alpha −0.268 %/trade, and the two pods that
just started accruing hold 13 rows between them. This push was repair and measurement, not signal.

## 2. Live state at handoff

| Field | Value |
|---|---|
| `audit3_ledger.json` generated | **2026-11-20T01:57:23Z** |
| `provenance.id` | **b5363b282409b564** |
| population / scored | canonical / **8,769** rows (362 cells) |
| PROVEN / CANDIDATE / WEAK / KILL / INSUFFICIENT | **0 / 0 / 59 / 8 / 295** |
| selection alpha | **−0.2681 %/trade** |
| forward ledger | 430 live rows; **443 admissible** (13 new: faber_taa 12, etf_dual_momentum 1) |
| pods with forward rows | 2 (first time) |

## 3. What I changed (all on main)

### Measurement integrity
- `6abfa22364e` — G9 selection alpha at **strategy** scope, global DSR floor (658), source-family gating
- `1189ff4150d` — provenance triple (population, cost model, win definition) + `provenance_id` on every bucket
- `260df7f980f` — `dsr_n_trials` published on every bucket
- `33e41deca65` — CANDIDATE DSR falls back to the global value when local is uncomputable (peer-found bug)
- `1238e16d086` — four falsifier tests (provenance changes with denominator; −1 %/trade cannot promote; zero alpha cannot prove; DSR undefined at 1 trial)
- `94466c02b7b` — forward benchmark window extended past the exit (time-expiry rows were getting permanently NULL benchmarks)

### Forward clock
- `1a36da257e2` — `unmatched_top` diagnostics (made 3,321 orphan rows visible)
- `ff884c4cb37` — per-hypothesis watchdog + 7-day pod grace (pre_registered pods fail after grace)
- `8aee6f084fd` — `volume_ratio_at_entry` migration + **dry-run** backfiller (55–59 % fillable)
- `d5fd72b7575` (#979) — **pod emission audit CI gate**: 15 of 23 manifest strategies exist in no table

### Paper sleeves ($2k plan)
- `6448b582fe0` — `core-beta` (SPY, $1,400) live
- `57c1c0d11d2` — `etf-rotation` + random control + daily marks workflow
- `4ec5fd7089f` / `79b5de2be3f` — aligned to the validated 14-ETF, top-5, 189-day spec; lag-1d thesis corrected
- `622cc11174c` — `etf-hold`, the beta-matched control buffy required
- `docs/GRADUATION_RUNBOOK.md` — every gate before real money

### Security
- `032d88897d1` — re-enabled the repo's gitleaks gate (PR + daily) after the P0 credential branch

### Documents (all on main under `docs/`)
`AUDIT_SURFACES_FULL_REVIEW_2026-11-19.md` · `WHAT_WORKS_PER_ASSET_CLASS_2026-11-19.md` ·
`ALLOCATION_2000_AND_LIVE_SIM_PLAN_2026-11-19.md` · `REAL_MONEY_READINESS_AND_PEER_FRAMEWORK_2026-11-19.md` ·
`NEXT_PHASE_PLAN_2026-11-19.md` · `DESIGN_DEBATE_2026-11-19.md` (v1 consensus table) ·
`COMS_REVIEW_FEEDBACK_2026-11-19.md` · `WORK_PRESERVATION_AND_MERGE_POLICY_2026-11-19.md` ·
`VOLUME_CONTEXT_MIGRATION_APPROACH_2026-11-19.md` · `REVIEW_INDEX_KILO_2026-11-19.md` ·
`COLLABORATION_PROTOCOL_2026-11-19.md` · `WORK_ROLLCALL_2026-11-19.md` ·
`FINAL_MERGE_VERDICT_2026-11-19.md` · `B1_POD_STRATEGY_NAMES_FINDING_2026-11-20.md` ·
`POD_EMISSION_AUDIT_2026-11-20.md` · `GRADUATION_RUNBOOK.md` · `FINAL_NOTES_KILO_2026-11-20.md`

## 4. Corrections I made to my own claims

Recorded because a review that never corrects itself is not a review:

1. **"audit3 scores a payload slice (21.43 %)"** — the live ledger moved to canonical (58.84 %). The
   denominator changing between runs became the finding.
2. **PDT $25k repeal** — I flagged it as unverified; it is real (FINRA Notice 26-10, effective
   2026-06-04). My flag was withdrawn and my allocation doc patched.
3. **TAA 0.88 Sharpe** — the headline was unlagged; honest lag-1d is Sharpe 0.81/0.82 with CAGR
   *trailing* SPY. TAA is drawdown control, not excess return.
4. **"5/13 benchmark-unmeasured is correct missing-bar behaviour"** — wrong; the bars existed. The
   fetch window ended at the exit, so time-expiry rows got permanent NULLs. Fixed.
5. **"selection_alpha.available=false ⇒ G8 unreachable" (buffy's claim, which I initially repeated
   as plausible)** — false on the live ledger: available=true, n=3,185, alpha −0.268. Corrected.

## 5. Peer review status — 4 of 8 reviewed

| Peer | What I verified | Verdict |
|---|---|---|
| OpenCode (Windows) | P0 alert, 5 archive tags, protocol, debate votes, cross-check | Trustworthy; one merge claim corrected (`fix/audit2-3-p0-p1` is 552 behind) |
| FreeBuff | TAA 576-cell CSV, sector spec, $2k critique, per-class report | Good, unfinished (T16 ETA outstanding); one stale claim corrected |
| Kilo (Linux CLI) | PR #977 (4 new files, +192/−0, valid JSON, no secrets) | Approve after rebase; merged |
| GitHub Copilot | PR #962/#964, TAA lag repro, found my DSR fallback bug | Best process contribution; Hermes' F1–F3 still open |
| Hermes (Windows) | ACK, review tally, live_simulator on main | Accounted |
| Google Swarm / OpenCode console / KILO Desktop | none | **Not accounted for** |

## 6. Open blockers, with owners

| Blocker | Owner | State |
|---|---|---|
| 15 phantom manifest strategies | manifest owner | My CI gate flags them; TWO pods can accrue today (`etf_faber_tactical`, `etf_dual_momentum`) |
| 3,321 unmatched cohort rows | research/registration owner | ensemble 289, forex_rsi2 175, macd_rsi 150, volume_spike 142 … |
| P0 credential branch | operator | rotate the DB password, delete + purge `feat/audit-review-organization-2026-11-19` |
| Volume schema `--apply` | operator | sidecar (recommended) or ALTER; tooling ready, dry-run only |
| `materiality_floor_pct` / churn wiring | quant-validation owner | main still has 3 red tests |
| Main worktree dangling merge (`MERGE_HEAD 04e4862`) | owner of that worktree | snapshot at `/tmp/kilo_backups/mainrepo-merge/` |

## 7. Verify everything (copy-paste)

```bash
# 1. audit3 focused suite (expect 93+ passed on current main)
python3 -m pytest tests/test_audit3_tribunal.py tests/test_audit3_expectancy_gates.py \
  tests/test_audit3_edge_hunt.py tests/test_audit3_selection_alpha.py \
  tests/test_forward_observations_ingest.py tests/test_audit3_cost_basis.py -q

# 2. crash smoke test
python3 -c "import sys;sys.path.insert(0,'.');from alpha_engine.audit3_tribunal import build_report;\
print(build_report([{'id':'x','asset_class':'CRYPTO','strategy':'s','direction':'LONG','symbol':'BTCUSDT',\
'source_system':'a','status':'WON','pnl_pct':1.0,'closed_at':'2026-11-01T00:00:00+00:00'}]*30,'x.json',None)['cells'][0]['required_n'])"

# 3. CLI parses
python3 -m alpha_engine.audit3_tribunal --help >/dev/null && echo CLI_OK

# 4. phantom pods
python3 tools/pod_emission_audit.py --strict --out /tmp/pea.json; echo "rc=$?"

# 5. live provenance
curl -s https://findtorontoevents.ca/audit3/audit3_ledger.json | python3 -c \
 "import json,sys;d=json.load(sys.stdin);p=d['provenance'];c=d['cells'][0];\
print(p['id'],p['population'],c.get('dsr_n_trials'),c.get('provenance_id')==p['id'])"
```

## 8. What I would do next, in order

1. **Amend the manifest** to the real emitters and flip `pod emission audit` to `--strict`
   (2 pods can accrue immediately).
2. **Reconcile main's 3 red tests** (materiality/churn) — one owner, one worktree.
3. **Rotate the exposed credential** and delete the branch.
4. **Let the forward clocks run.** n≥200, net CI>0 at 2× cost, DSR≥0.95, beats *both* control arms:
   only then does the $2k allocation change from 90/0/10.
5. Only after that: the three pre-registered experiments (vol-target A/B, RVOL≥1.5 overlay,
   5 TP/SL configs — never 96).

*Not investment advice. No strategy, threshold value, or honest-verdict policy was relaxed; every
change made it harder to call something profitable.*
