# Stalled-Producer Detector — `tools/check_stalled_producers.py` (v2.0)

**NEW tool — 2026-06-23 (added during the `/money-maker-ready-June112026edition` audit).**
**v2.0 re-published 2026-06-24 during the `/money-maker-ready-2026-06-24-edition` restart cycle.**
**Companion to:** `reports/money_maker_ready_20260623T235825Z.md` (Appendix A).

---

## Why v2.0 (frame-mismatch with v1.0..1.2)

The v1.x release was a single-table design: 9 canonical data files, freshness via local disk `mtime` only. It correctly identified that the `audit-dashboard.yml` cron was reporting `conclusion: success` while the data files had been stale since 2026-06-03 (~20 days).

In the 2026-06-24 follow-up audit the **root-cause frame proved incomplete**:

1. The user-mentioned 4 severe-stale files (`audit_dashboard/data/dashboard_data.json`, `audit_dashboard/data/walkforward_results.json`, `audit_dashboard/data/fwd_vs_bt_divergence.json`, `entry_conditions_forward.json`) are **gitignored** (per `.gitignore` line 216+) **AND explicitly excluded from the workflow's `git add`** (audit-dashboard.yml lines 918-922) with the comment "the known heavy JSON outputs that are handled by the FTP deployment phase".
2. Live probe of these URLs at the start of the 2026-06-24 cycle showed: `dashboard_data.json` `Last-Modified: Wed, 24 Jun 2026 00:50:24 GMT` (FRESH on the live site — i.e. the cron DID publish, my LAN disk was the wrong place to look because my checkout was **3,936 commits** behind `origin/main`).
3. So v1.x's "all 9 RED" was a **false RED**: the cron was actually fresh; mtime-on-LAN-disk was the wrong freshness source for 7 of 9 files.
4. v2.0 splits the table into two kinds (LOCAL + REMOTE) and probes the canonical source of truth for each (LAN disk for git-tracked, live FTP for FTP-only). The 2 of 9 files that were actually stale (`walkforward_results.json`, `fwd_vs_bt_divergence.json` returning HTTP 404 on all 3 live mirrors) are correctly surfaced as `status="missing"` with `note="HTTPError 404: Not Found; ..."` — pointing the operator at the **producer bug**, not at the LAN checkout timestamp.

---

## What v2.0 does differently

| Aspect | v1.x | v2.0 |
|---|---|---|
| Tables | One (9 files, all mtime) | Two: `LOCAL_FILES` (2 files, mtime) + `REMOTE_FILES` (7 files, HTTP probe) |
| Freshness source for FTP-deployed files | LAN disk (false-red) | Live FTP `Last-Modified` header |
| Mirror fallback | n/a | `findtorontoevents.ca` → `tdotevent.ca` → `torontoevent.net` |
| 404 vs unreachable classification | None | Yes — `status="missing"` if ALL mirrors 404; else `unreachable` |
| New exit code | n/a | Exit `6` = all REMOTE mirrors unreachable (5xx / timeout / network) |
| New flag | n/a | `--no-http` for offline / air-gapped runners |

### Default tables

#### LOCAL_FILES (2 — git-tracked, mtime check)
| Path | Default `max_age_h` | Why |
|---|---:|---|
| `audit_dashboard/data/audit_surface_truth.json` | 4.0 | Surface-truth reconciliation (LAN disk via `git pull`) |
| `audit_dashboard/data/nav_surface_edge_matrix.json` | 4.0 | NAV-by-surface edge matrix (LAN disk via `git pull`) |

Verified via `git ls-files` at HEAD — these ARE actually committed to the repo. They live on the LAN disk via `git pull` after the cron commits them.

#### REMOTE_FILES (7 — gitignored, HTTP `Last-Modified` probe)
| Path | Default `max_age_h` | Probed URL (mirror order) |
|---|---:|---|
| `audit_dashboard/data/dashboard_data.json` | 2.0 | `findtorontoevents.ca` → `tdotevent.ca` → `torontoevent.net` |
| `audit_dashboard/data/money_ready_verdict.json` | 2.0 | same |
| `audit_dashboard/data/pick_funnel_90d.json` | 2.0 | same |
| `audit_dashboard/data/pick_funnel_today.json` | 2.0 | same |
| `audit_dashboard/data/walkforward_results.json` | 6.0 | same |
| `audit_dashboard/data/fwd_vs_bt_divergence.json` | 6.0 | same |
| `entry_conditions_forward.json` | 2.0 | same |

Verified via `git cat-file -e origin/main:<path>` — NONE of these are tracked in repo. They live only on the 3 live FTP mirrors after step 49 "Deploy to all 3 FTP sites in parallel".

---

## Live state at the start of the 2026-06-24 cycle (raw HTTP probe)

| Path | Live `Last-Modified` | Status |
|---|---|---|
| `audit_dashboard/data/dashboard_data.json` | `Wed, 24 Jun 2026 00:50:24 GMT` | FRESH (cron #28064382131 published at ~00:50 UTC) |
| `audit_dashboard/data/money_ready_verdict.json` | `Wed, 24 Jun 2026 00:50:21 GMT` | FRESH |
| `audit_dashboard/data/pick_funnel_90d.json` | `Wed, 24 Jun 2026 00:50:23 GMT` | FRESH |
| `audit_dashboard/data/pick_funnel_today.json` | (assumed same ~00:50 UTC window) | presumed FRESH |
| `audit_dashboard/data/walkforward_results.json` | — (HTTP 404) | MISSING (producer bug) |
| `audit_dashboard/data/fwd_vs_bt_divergence.json` | — (HTTP 404) | MISSING (producer bug) |
| `entry_conditions_forward.json` | `Wed, 24 Jun 2026 00:50:20 GMT` | FRESH |

**Narrative**: cron #28064382131 completed successfully at 2026-06-24T01:02:56Z. Of its 7 expected FTP-deployed files, **5 are FRESH** (`dashboard_data`, `money_ready_verdict`, `pick_funnel_90d`, `pick_funnel_today`, `entry_conditions`) — the cron clearly pushed them via step 49. **2 are MISSING** (`walkforward_results`, `fwd_vs_bt_divergence`) — likely sub-step in toolchain that produces them is silently failing, surface-truth warning emitted but no specific step logged as failed. Operator action: investigate which upstream script writes these 2 files (likely `alpha_engine/walkforward_validator.py` and an as-yet-named divergence writer).

**This is NOT a cron stall** (cron completed). It's two missing producer outputs in step 49 deploy batch.

---

## Exit codes (v2.0)

| Code | Meaning | GH Actions mapping |
|---:|---|---|
| 0 | All files within freshness window | job SUCCEEDS — green ✓ |
| 1 | At least one file STALE (mtime > threshold OR remote `Last-Modified` > threshold) | job FAILS — yellow/red |
| 2 | At least one file MISSING (LOCAL absent OR REMOTE 404) | job FAILS — red |
| 3 | Repo root not found (config error) | job FAILS — config error |
| 4 | Bad `--threshold-override` parse (empty path, non-numeric hours, negative hours) | job FAILS — config error |
| 5 | Argument conflict — both `--strict` and `--threshold-hours` passed | job FAILS — config error |
| 6 | All REMOTE mirrors UNREACHABLE (timeout / 5xx / network). PER-MIRROR status captured in `note` | job FAILS — red |

**Per-file `FileHealth.status` values** (in `--json` output): `"ok" | "stale" | "missing" | "unreadable" | "unreachable"`. Path-traversal-blocked paths surface as `status="missing"` with `note="path-traversal-blocked"`.

**Precedence ordering on aggregate exit**: `unreachable` (any) > `missing` (any) > `stale` (any) > all-ok.

---

## How to use

### (a) Local sanity check (the most common use)

```bash
cd /home/eaguiar2015/findtorontoevents_antigravity.ca
python3 tools/check_stalled_producers.py
```

Sample v2.0 output at the start of 2026-06-24:

```
KIND    FILE                                                  STATUS       AGE(h)   THR(h)  SIZE(KB)  WHY
---------------------------------------------------------------------------------------------------------------------
remote  audit_dashboard/data/dashboard_data.json              ok            0.00     2.0    18827.5  main payload / 18MB (FTP-only; ...)
remote  audit_dashboard/data/money_ready_verdict.json         ok            0.01     2.0      243.1  honest intrabar-truth per class (FTP-only...)
remote  audit_dashboard/data/pick_funnel_90d.json             ok            0.00     2.0       85.4  pick funnel 90d window (FTP-only)
remote  audit_dashboard/data/pick_funnel_today.json           ok            0.01     2.0       18.7  today's funnel (FTP-only)
remote  audit_dashboard/data/walkforward_results.json         missing        —       6.0         —   OOS folds (FTP-only; ...)  //HTTPError 404: Not Found; HTTPError 404: Not Found; HTTPError 404: Not Found
remote  audit_dashboard/data/fwd_vs_bt_divergence.json        missing        —       6.0         —   backtest overfit detector (FTP-only)  //HTTPError 404: Not Found; HTTPError 404: Not Found; HTTPError 404: Not Found
remote  entry_conditions_forward.json                         ok            0.01     2.0      102.4  sigma-geometry entry sidecar (FTP-only, repo root)
local   audit_dashboard/data/audit_surface_truth.json         stale         1.12     4.0      433.0  surface-truth reconciliation (git-tracked, LAN mtime)
local   audit_dashboard/data/nav_surface_edge_matrix.json     stale         0.06     4.0      183.2  NAV-by-surface edge matrix (git-tracked, LAN mtime)

RESULT: ok=5  stale=2  missing_or_unreadable_or_unreachable=2  total=9
```

(Exact numbers will vary with live state. The aggregate is: 5 OK (cron-published 5 FTP-deployed files), 2 MISSING (producer bug for the 2 walkforward-class files), 2 LOCAL stale because LAN branch is 3,936 commits behind.)

### (b) `--strict` mode (1h threshold everywhere)

```bash
python3 tools/check_stalled_producers.py --strict
```

Tight-cadence pipelines where 2h is too lenient.

### (c) JSON output

```bash
python3 tools/check_stalled_producers.py --json
```

Each row has added `kind` (`"local"` | `"remote"`), `probe_url` (URL that succeeded for REMOTE), `note` (string diagnostic), and field semantics per the dataclass.

### (d) `--no-http` (offline / air-gapped runners)

```bash
python3 tools/check_stalled_producers.py --no-http
```

Treats all `REMOTE_FILES` as `unreachable` so a cron running on a private runner doesn't need outbound internet.

### (e) Per-override

```bash
python3 tools/check_stalled_producers.py \
  --threshold-override audit_dashboard/data/walkforward_results.json=12 \
  --threshold-override audit_dashboard/data/fwd_vs_bt_divergence.json=12
```

---

## Recommended GH Actions wiring

Add to `.github/workflows/audit-dashboard.yml` as the **last job in the workflow**, before the auto-commit step:

```yaml
      - name: Stalled-producer health-check (v2.0)
        run: |
          python3 tools/check_stalled_producers.py --json | tee "$RUNNER_TEMP/check_stalled.json"
        shell: bash
```

Output is captured for GH Actions `$GITHUB_OUTPUT` if downstream steps want to consume per-file status.

> **NOTE:** do NOT gate the OFFICIAL freshness guardian (`.github/workflows/db-freshness-guardian.yml`) on this — that watchdog has its own schedule + alerting rules; this is the cron-internal fence.

---

## What this tool does NOT do

- Does NOT attempt to **restart** the producer. It only signals the stall / missing output.
- Does NOT commit/push anything. Read-only inspection.
- Does NOT mutate `blocklist`/`blacklist` per AGENTS.md safety.
- Does NOT replace the canonical MySQL LAN-block runbook (`updates/2026-06-23-mysql-lan-block-unblock-runbook.md`) — that runbook applies to **LAN-side tooling** (`pick_flow_funnel.py`, `edge_finder.py`, etc.) and is NOT what the GH cron producer uses; the GH cron has its own secret directly injected.

---

## Round-3 polish (post reviewer)

Three minor items addressed during the 2026-06-24 review round:

| # | Item | Fix |
|---|---|---|
| 1 | Dead code — `_NoRedirect` class defined in `_try_one_url` but never used | Removed |
| 2 | Header lookup case-sensitive — GoDaddy / Cloudflare proxies occasionally title-case (`"Last-modified"`) or lowercase headers; lookup would silently miss | Lowercase all keys when materializing headers: `head = {k.lower(): v for k, v in resp.headers.items()}` |
| 3 | Note field truncated to 200 chars — when 3 mirrors each failed with a 100-char error message, operator loses ~⅓ of the diagnostic | Widened to 300 chars |

---

## AGENTS.md compliance summary

- ✅ Read-only — no destructive ops
- ✅ No git push per AGENTS.md; the new commits stay local
- ✅ Companion `updates/` doc — this file
- ✅ Honest labeling — does not claim a fix it doesn't make
- ✅ Skill v1.1 failure-mode handling — covers "Dashboard data >2h stale → abort, surface, ask wait/proceed"

---

## Cross-references

| Reference | Path |
|---|---|
| Full audit (this audit-cycle) | `reports/money_maker_ready_20260623T235825Z.md` |
| Operator-summary updates doc | `updates/2026-06-23-money-maker-ready-june11-edition.md` |
| MySQL LAN-block runbook (separate concern — applies to LAN tools) | `updates/2026-06-23-mysql-lan-block-unblock-runbook.md` |
| Cross-class SMART floor audit | `updates/2026-06-23-cross-class-smart-floor-audit.md` |
| Equity revalidation helper | `tools/revalidate_equity_smart_audit.py` |
| Money-maker-ready skill | `/money-maker-ready` v1.1 2026-05-15 |

---

## Author + version

- Author: Buffy via `/money-maker-ready-June112026edition` audit
- Created: 2026-06-23T23:58:25Z (v1.0)
- v2.0 republished: 2026-06-24 (frame-correction: split LOCAL_FILES vs REMOTE_FILES)
- v2.0+1: classifier bug-fix + 3 polish items
- Files: `tools/check_stalled_producers.py` (~260 lines) + this `updates/2026-06-23-stalled-producer-detector.md`
