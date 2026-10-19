# EQUITY SMART-Gate Re-Audit Helper — Companion Doc

**Date:** 2026-06-23
**Companion to:** `tools/revalidate_equity_smart_audit.py` (~225 lines, Python 3.10+)
**Decision-context:** PHASE 1C.d discovered EQUITY 7× SMART-gate disparity; full audit doc at `updates/2026-06-23-equity-smart-gate-7x-disparity-audit.md`.

---

## TL;DR

`tools/revalidate_equity_smart_audit.py` is a **read-only conditional-action helper** that fires when gh run #28051310550 commits and `pick_funnel_90d.json` refreshes. It extracts CRYPTO + EQUITY scanned/smart/va/hc/proven/wr_pct, computes `(CRYPTO_smart_pct / EQUITY_smart_pct)`, and classifies against the user's 5×–10× threshold band:

| Ratio band | Verdict | Action |
| --- | --- | --- |
| `<5.0×` | `SOFT_DRIFT` — EQUITY may be over-suppressed | Apply remediation R1 (hard floor → soft penalty) + R2 (n-sample dynamic flooring) from audit doc |
| `5.0×–10.0×` (inclusive both) | `ROBUST` — PHASE 1C.d structural finding holds | No action; elite_score ≥ 55 floor calibration is empirically sound |
| `>10.0×` | `SEVERE_DRIFT` — floor is starving EQUITY throughput | Apply R1 + R3 (macro-stress linkage) URGENT |

Default thresholds: `--threshold-soft 5.0` and `--threshold-robust 10.0`. Both inclusive at the boundary.

---

## 1. Why this script was written

The PHASE 1C.d audit established that EQUITY's 1.4% SMART-gate pass rate is **structurally** driven by the hard `elite_score ≥ 55` kill-switch at `audit_trail/quality_gates.py:7938` (not by random data). The structural finding cannot shift unless someone edits the source code. **Decimal findings CAN shift** when `pick_funnel_90d.json` refreshes — that refresh happens via GH Actions cron, and the most recent cron run is run #28051310550.

If the decimals shift, this helper is the canonical re-audit.

---

## 2. Usage

```bash
# Default run (5x/10x thresholds)
python3 tools/revalidate_equity_smart_audit.py

# Tighter band (3x/12x) — should still classify the canonical ~6.78x as ROBUST
python3 tools/revalidate_equity_smart_audit.py --threshold-soft 3.0 --threshold-robust 12.0

# Wider band (3x/15x) — same ROBUST classification
python3 tools/revalidate_equity_smart_audit.py --threshold-soft 3.0 --threshold-robust 15.0

# Extreme narrow band (10x/20x) — the canonical 6.78x becomes SOFT_DRIFT under this band
python3 tools/revalidate_equity_smart_audit.py --threshold-soft 10.0 --threshold-robust 20.0

# Point at a custom snapshot
python3 tools/revalidate_equity_smart_audit.py --snapshot /path/to/another.json
```

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | OK — printed verdict + freshness caveat |
| `2` | Snapshot file not found |
| `3` | snapshot's `funnel_by_class` lacks CRYPTO or EQUITY block |

---

## 3. Sample output

```text
=== revalidate_equity_smart_audit.py ===
  snapshot:               audit_dashboard/data/pick_funnel_90d.json
  snapshot_mtime_epoch:   1780496590
  snapshot_window_days:   90

  CRYPTO: scanned= 15139 smart_pass= 1478 (9.764%) va=698 hc=1 proven=1 | WR=45.43% n=3665
  EQUITY: scanned=  2153 smart_pass=   31 (1.440%) va=2   hc=0 proven=0 | WR=48.46% n=130

  ratio CRYPTO_smart_pct / EQUITY_smart_pct = 9.764% / 1.440% = **6.780x**

  verdict: ROBUST ratio=6.78x ∈ [5.0x, 10.0x] — PHASE 1C.d structural finding holds;
           the elite_score>=55 floor (quality_gates.py:7938) calibration is empirically sound

  freshness: snapshot last modified 1780496590 (epoch); CRYPTO/EQUITY ratios are robust
             to drift but decimals will refresh once #28051310550 auto-commits land.
```

When combinations of CRYPTO + EQUITY scanned < 1000 picks, a low-volume advisory:
```text
  NOTE: combined scan volume <1000 picks — ratios carry high variance;
        consider widening threshold band by 2-3x before drawing conclusions.
```

---

## 4. What it does NOT do (intentional non-features)

- **Does not write back** to `pick_funnel_90d.json`. Pure read-only.
- **Does not commit to git**. No auto-commit.
- **Does not apply remediation R1/R2/R3**. The verdict message names them, but invoking them requires human judgment (those remediations are code changes to `audit_trail/quality_gates.py`).
- **Does not call MySQL**. Works entirely off the cron-snapshotted JSON.
- **Does not require network**. `gh run` polling is optional; the helper works on whatever state the snapshot is currently in.

---

## 5. Maturity notes

- **py_compile verified PASS** (multiple iterations through post-fix).
- **Live run on current (still 2026-06-03) snapshot** confirmed: ratio=6.78×, ROBUST verdict, freshness caveat printed, low-volume advisory correctly suppressed (combined scanned = 17,292 > 1000).
- **Threshold adaptivity verified**: tighter band (3×/12×) keeps ROBUST; narrow band (10×/20×) re-classifies to SOFT_DRIFT.
- **Edge cases handled**:
  - Snapshot missing → exit 2
  - CRYPTO/EQUITY block missing → exit 3
  - smart_pct = 0 (division-by-zero) → prints "undefined" + INSUFFICIENT_DATA verdict
  - File-not-readable → exception propagates + exit 2

---

## 6. Files touched this turn

| Path | Action |
| --- | --- |
| `tools/revalidate_equity_smart_audit.py` | NEW FILE ~225 lines, `gitignored`-friendly (per AGENTS.md "every script that touches data should be self-contained so cron/orchestrator can call it") |
| `updates/2026-06-23-tools-revalidate-equity-smart-audit-helper.md` | NEW FILE this doc |
| `audit_trail/quality_gates.py` | NOT modified — only referenced at L7938 in messages |
| `audit_dashboard/data/pick_funnel_90d.json` | NOT modified — read-only |

---

## 7. Once `#28051310550` commits

Re-running on fresh data is mechanical:

```bash
# poll
gh run view 28051310550 --json status,conclusion | grep -E '"status"|"conclusion"'

# confirm freshness
stat -c '%y' audit_dashboard/data/pick_funnel_90d.json

# re-audit
python3 tools/revalidate_equity_smart_audit.py
```

If the ratio falls **outside** the 5×–10× band, escalate to remediation R1/R2/R3 per the audit doc (§7 of `updates/2026-06-23-equity-smart-gate-7x-disparity-audit.md`).

---

## 8. Why this is preserved (avoiding orphaned helper)

Per AGENTS.md doc discipline: "Every code fix you make MUST be documented in a `.MD` file." This helper is documented here so future maintainers / cron-orchestrators can run it without re-reading the 225-line source. The doc also serves as the contract that future ratio-shifts (if any) will be classified by the same threshold framework — preserving the PHASE 1C.d → this-helper → R1/R2/R3 chain.

If a future change to `audit_trail/quality_gates.py:7938` lifts the EQUITY floor, this helper still works because:

1. The post-floor-pass-through classes will be EQUITY (scanned unchanged) → smart_pass can jump → ratio CRYPTO_smart_pct / EQUITY_smart_pct can drop below 5× → verdict SOFT_DRIFT.
2. The script auto-adapts because it reads from the snapshot, not from source-code expectations.
