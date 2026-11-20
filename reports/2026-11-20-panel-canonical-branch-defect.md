# Defect: the `/audit2` per-class panel can never read the canonical sidecar in CI

**Status: NOT FIXED.** This document records a defect. It does not fix it.

**Date:** 2026-11-20
**Discovered during:** P2-2 verification (panel render at two widths)

## The defect

The panel-builder step in `.github/workflows/audit3-ledger.yml` is written to prefer the
canonical resolved view when it exists:

`.github/workflows/audit3-ledger.yml:262` — the conditional:

```yaml
rows_arg=""
if [ -f /tmp/audit3/resolved_closed_picks_net.json ]; then
  rows_arg="--rows /tmp/audit3/resolved_closed_picks_net.json"
fi
python3 tools/build_audit2_per_class_panel.py \
  --ledger audit_dashboard/data/audit3_ledger.json \
  --payload /tmp/audit3/dashboard_data.json $rows_arg
```

But the earlier fetch step hard-fails unless the payload is present:
`.github/workflows/audit3-ledger.yml:44` writes `/tmp/audit3/dashboard_data.json`, and
`.github/workflows/audit3-ledger.yml:48-51` exits 1 when the live payload is unreachable
("live dashboard_data.json unreachable"). So in CI the `/tmp/audit3/` directory is populated
from the payload, and the `--payload` argument is always passed — the `--rows` branch, even
when taken, never changes what the panel reads the canonical book from, because the panel is
always invoked in a run whose inputs were derived from the payload.

The consequence: the per-class panel always describes the payload slice (3,500 rows), never
the canonical book (8,769 rows). That is precisely the defect P1-4 was supposed to fix.

## Why it matters

The panel's numbers — per-class counts, verdicts, denominators — describe 3,500 payload-slice
rows, not the 8,769-row canonical book. Its verdicts are therefore not the book's verdicts.
A class that looks thin or over-represented in the slice can look different in the book, and
the panel gives no signal that it is speaking about a different population.

## Compounding factor: provenance leak

The ledger's `source` field is `/tmp/audit3/dashboard_data.json` — an absolute temp path
(confirmed in `audit_dashboard/data/audit3_ledger.json`). Even the claim "this is the canonical
book" cannot be verified from a checkout: the path is not repo-relative, does not exist on a
developer machine, and carries no hash of the payload it named. So the panel's input is
unverifiable from the repository alone.

## What a fix would need

1. `audit_trail/dashboard_generator.py` must write the sidecar to a **repo-relative** path
   (not `/tmp/audit3/...`), and that path must be committed or uploaded/downloaded as a CI
   artifact so the panel step can read it deterministically.
2. The panel step must be shown to take the `--rows` branch **in a real run** — with the
   run's log or the panel's own output showing the canonical row count — not asserted from
   reading the YAML. Reading the YAML is exactly what produced the false confidence here.
3. Ideally the panel emits which branch it took and the row count it read, so a mismatch is
   visible in the artifact rather than inferred.

## Related observations (measured, same session)

- `per_class_verdicts` occurs **0 times** in the on-disk `audit_dashboard/data/audit3_ledger.json`,
  so the P2 render used a synthesized payload.
- `audit_dashboard/audit2.html` had a real mobile overflow defect (scrollWidth 680 at a 375px
  viewport), fixed with `overflow-x:auto` on `.card` and re-verified (mobile 375, desktop 1280
  unchanged).
