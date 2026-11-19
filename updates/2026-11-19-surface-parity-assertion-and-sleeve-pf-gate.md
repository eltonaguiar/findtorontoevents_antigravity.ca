# 2026-11-19 — surface-parity assertion + implausible-PF gate on sleeve ingestion

**Author:** Buffy (Freebuff), worktree `review-main`
**Type:** two code changes, both closing defects found by the COMS design debate
**Debate elements:** 13 (cross-surface reconciliation) and 5 (sleeve ingestion)

---

## Change 1 — `tools/assert_surface_parity.py` (new)

### What was broken

The same audit3 ledger was being served **twice by the same site, with different contents**:

| Path | Bytes | SHA-256 | `generated_at` | `n_rows` |
|---|---|---|---|---|
| `/audit/data/audit3_ledger.json` | 627,649 | `b0ca1de6…` | 18:32:40Z | 8,613 |
| `/audit3/audit3_ledger.json` | 665,028 | `557cb3f1…` | 21:02:25Z | 8,621 |

2h30m and 8 rows apart. Neither page disclosed which copy it rendered. **Provenance identifiers could
not catch this**, because both copies were internally consistent — each correctly described a
different population. Provenance answers "which population is this number from?"; it cannot answer
"why does the same filename have two populations on one host?"

### What changed

A committed assertion with an exit code, replacing hand-written reconciliation prose:

- Fetches `/audit/`, `/audit2/`, `/audit3/`, `/audit/data/audit3_ledger.json`,
  `/audit3/audit3_ledger.json`, `/audit/data/money_ready_verdict.json`.
- Asserts the two ledger copies are **byte-identical** (sha256).
- When they differ, asserts the build-time gap is within **one build cycle (70 min)** and the row
  counts agree — i.e. the difference is a rebuild in flight, not a divergent pipeline.
- Asserts `n_proven` / `n_candidate` agree across copies regardless of byte identity.
- Fails RED if the freshest ledger is older than 240 min, or a documented path 404s.
- Exit codes follow the repo's existing convention (`tools/db_freshness_check.py`):
  **0 GREEN / 1 YELLOW (transient) / 2 RED (divergent)**.
- `--allow-rows-diff N --why "<reason>"` whitelists a deliberate population difference, per the
  debate doc's rule: *if two surfaces are meant to serve different populations, the difference must be
  declared, not discovered.*

### Verified

`python3 tools/assert_surface_parity.py --out reports/surface_parity.json` →

```
SURFACE PARITY: RED (exit 2) at 2026-11-19T21:20:44Z
  - ROWS_DIVERGE: |8613-8621|=8 > 0 (whitelist)
  - BUILD_GAP_EXCEEDS_CYCLE: 150 min > 70 min tolerance — /audit renders a 150-minute-old ledger
  rows: /audit=8613  /audit3=8621
  build gap: 149.8 min
```

Exit code 2 as designed, and the two findings are exactly the two defects. This is a **live RED**, not
a hypothetical — the assertion is failing on the current production site.

---

## Change 2 — implausible-PF gate in sleeve ingestion (`alpha_engine/audit3_tribunal.py`)

### What was broken

`--sleeves` ingested `/audit`'s `top_sleeves` into the tribunal and flagged them `UNVERIFIED`, but
**still emitted them with their profit factors**, so nothing structurally prevented a sleeve from being
ranked or displayed as a "top sleeve". The values in question:

| Sleeve | PF | CRYPTO class aggregate PF |
|---|---|---|
| `AuditEnsemble_LONG` | **155.85** | 0.8383 |
| `CorrKama` | **111.81** | 0.8383 |
| `ADX Trend` | **56.73** | 0.8383 |
| `mega_mut_macd` | **49.37** | 0.8383 |
| `CorrVwapZscore` | **33.09** | 0.8383 |

A profit factor of 155 means the average win is 155× the average loss. No 1.67:1 reward:risk template
(measured median across 3,497 closed rows) can produce that; it is a **grading artefact** — near-zero or
resolver-fallback losses inside a self-graded single source. `tools/sleeve_reconciliation.py` confirmed
**0/10 sleeves verified against audit3 cells, 9/10 single-source**.

### What changed

Each ingested sleeve now carries four additional fields, computed from the tribunal's own rows:

- `class_pf` — the row-weighted profit factor of the class the sleeve claims to belong to.
- `pf_vs_class` — the sleeve's PF divided by that aggregate.
- `implausible_pf` — true when PF exceeds the **absolute ceiling of 25×**, or exceeds **5× its own
  class aggregate**.
- `rankable` — true only when the sleeve is `VERIFIED`, **not** single-source, `n ≥ 30`
  (`CANDIDATE_MIN_N`), and **not** implausible.
- `rank_exclusion_reason` — a human-readable reason whenever `rankable` is false.

Non-rankable sleeves also print a `WARNING:` line to stderr, so a pipeline that ingests them cannot do
so silently.

**Thresholds are constants, not tuned per run**: 25× absolute, 5× class-relative, n ≥ 30. They are
chosen so that a degenerate loss side is caught regardless of class, while a genuinely strong sleeve
(PF 2–3 in a class aggregating 0.8) survives.

### Verified

Synthetic fixtures (100 CRYPTO rows, #wins = #losses ⇒ class PF ≈ 1.0) with two sleeves — one honest
(PF 1.05) and one at the real anomalous value (PF 155.85) — through
`python -m alpha_engine.audit3_tribunal --picks … --sleeves …`:

- `REAL_ONE`: `pf=1.05`, `pf_vs_class≈1.0`, `implausible_pf=False`, **`rankable=True`**.
- `FANTASY`: `pf=155.85`, `implausible_pf=True`, **`rankable=False`**, reason
  *"pf 155.85 exceeds absolute ceiling 25"* and *"pf is 155.9x the class aggregate"*.

`python3 -m py_compile alpha_engine/audit3_tribunal.py` → OK.

---

## Not changed, and why

- **The divergent production ledgers were not repaired.** That is deploy-pipeline territory owned by
  others; my mandate is to detect and report, not to edit their deploy paths.
- **`/audit2`'s broken ledger fetch was not repaired.** Same reason. It is now detectable: the parity
  script records `has_ledger_marker` per page.
- **Thresholds were not exposed as CLI flags.** A tunable gate is a gate someone tunes until their
  sleeve passes. If a class genuinely needs a different ceiling, that is a constant change with a
  review, not a run-time argument.

## Limitation stated plainly

The parity assertion is only as good as its allowlist. A divergence that someone whitelists with
`--allow-rows-diff` and a plausible `--why` will pass. That is the intended trade-off — the alternative
is a check that fails on legitimate rebuilds until people start ignoring it — but it means the
whitelist itself must be reviewed, not just the check.
