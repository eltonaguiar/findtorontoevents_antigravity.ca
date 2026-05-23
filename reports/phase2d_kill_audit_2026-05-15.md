# Phase 2-D COMMODITY Kill Audit — 2026-05-15

## Purpose

The cotton autopsy (`reports/deep_dive_cotton_2026-05-15.md`, PR #1061) found the Phase 2-D CT=F kill was data-flawed. Recommendation #2 of that autopsy: audit the other 6 Phase 2-D sub-class kills. This document does that.

## Method

Source of truth: `audit_dashboard/data/dashboard_data.json::picks.recent_closed` (resolver-v2). For each blacklisted COMMODITY symbol, recompute n / WR / PF / sumPnL and compare to the figures cited in the Phase 2-D kill comment at `audit_trail/quality_gates.py:1254-1262`. Kill commit: `162d1d8286d` (PR #535, 2026-04-29 23:43 EDT).

## Result table

| Symbol | Blacklist comment cites | Resolver-v2 ledger (ALL) | Reconciles? |
|---|---|---|---|
| HG=F (copper) | n=168 WR 47.0% +6.64% — KEEP | not blacklisted | n/a (kept) |
| PL=F (platinum) | n=138 WR 44.9% +5.15% — KEEP | not blacklisted | n/a (kept) |
| GC=F (gold) | n=91 WR 39.6% -0.52% — KILL | **n=3** WR 0% -1.4% | ❌ n 91→3 |
| SI=F (silver) | n=181 WR 44.2% -4.47% — KILL | **n=3** WR 33.3% -3.9% | ❌ n 181→3 |
| CL=F (crude) | n=6 WR 16.7% -5.25% — KILL | n=4 WR 25.0% +0.3% | ❌ n 6→4, sum -5.25→+0.3 |
| CT=F (cotton) | n=12 WR 8.3% -8.41% — KILL | n=41 WR 82.9% +147.7% | ❌ (see cotton autopsy) |
| KC=F (coffee) | n=12 WR 8.3% -6.02% — KILL | n=2 WR 0% -5.9% | ❌ n 12→2 |
| ZS=F, ZW=F, NG=F, CL=F, etc. | (in blacklist, not individually cited) | ZS=F n=8 -17.1%; ZW=F n=10 -10.1%; NG=F n=1 +0.8% | mixed |

## Findings

### 1. The Phase 2-D panel's data source cannot be reconciled with the resolver-v2 ledger

GC=F was killed on a cited **n=91**; the resolver-v2 ledger holds only **n=3** GC=F picks. SI=F killed on cited **n=181**; ledger holds **n=3**. These are not rounding differences — they are different datasets.

Three possible explanations:
- (a) The panel used the 50webs MySQL `at_signal_outcomes` table — known ghost-infested at 0.08% real resolution (per `reports/deep_dive_cotton_2026-05-15.md`). A bad source.
- (b) The panel used a historical window (n=91/181) that has since rolled off the ~3500-row `recent_closed` window. Plausible for GC=F/SI=F — but then the kill is un-reproducible from any current artifact.
- (c) The numbers were partially fabricated or transcribed wrong.

**Whichever it is, the Phase 2-D kill verdicts are not reproducible from the current source of truth.** A kill that cannot be re-derived is not a defensible kill.

### 2. CT=F and KC=F cite IDENTICAL flawed stats — "n=12 WR 8.3%"

Both cotton and coffee were killed on the exact string "n=12 WR 8.3%" (only the sum differs: -8.41% vs -6.02%). An 8.3% win rate is exactly 1/12 — one win in twelve. Two unrelated agricultural futures producing the identical 1-of-12 outcome on the identical sample size is statistically near-impossible. This is a copy-paste error or a systematic resolver bug that mapped many picks to a single "1 win" bucket at panel time.

The CT=F autopsy already proved the n=12 figure wrong: those 12 pre-kill picks resolved to **66.7% WR**, not 8.3%. By the identical-citation pattern, KC=F's "n=12 WR 8.3%" is equally suspect — though KC=F has only n=2 in the current ledger, too thin to recompute.

### 3. Some kills are directionally defensible even if the cited numbers are wrong

- ZS=F: n=8, 0% WR, -17.1% — genuinely bad on the (small) ledger sample.
- ZW=F: n=10, 30% WR, -10.1% — genuinely weak.
- CL=F: n=4, +0.3% — marginal, NOT clearly a loser. Cited "-5.25%" not reproducible.
- GC=F / SI=F: n=3 each — too thin to verify either way.

So the COMMODITY blacklist is a mix: a few defensible kills (ZS=F, ZW=F on weak ledger data) and several un-verifiable ones (GC=F, SI=F, CL=F, CT=F, KC=F).

## Verdict

**The Phase 2-D COMMODITY kill panel cannot be reproduced and should not be trusted as-is.** This does not mean "unblock everything" — it means the kill verdicts have no verifiable basis and must be re-derived.

## Recommendations

1. **Do NOT mass-unblock** via `COMMODITY_SUBCLASS_KILL_DISABLED=1`. Several kills (ZS=F, ZW=F) are defensible; cotton needs the shadow-mode path per its autopsy.
2. **Locate the Phase 2-D panel's actual data source.** If it was the MySQL ghost table, every Phase 2-D verdict is void. If it was a rolled-off historical window, that window must be archived for reproducibility.
3. **Re-run the panel against resolver-v2** for all 7 sub-classes with a hard `n≥50` floor (cotton + coffee were killed on cited n=12; CL=F on n=6 — all below any sane kill threshold).
4. **This is the M-055 case study.** The Phase 2-D panel is a concrete instance of the kill-threshold mis-calibration the swarm + peers flagged: kills fired on tiny samples (n=6, n=12) with no statistical test, citing numbers that don't reconcile with the trustworthy ledger. M-055 (kill-threshold recalibration: walk-forward + min-n + binomial gate) should use Phase 2-D as its first regression test — "would M-055's gates have blocked these 7 kills?" If yes, M-055 is validated.
5. **Add a kill-provenance requirement**: every entry in any `*_BLACKLIST` must cite a reproducible query (file + commit + filter) so any future agent can re-derive the verdict. The current Phase 2-D comment cites bare numbers with no query — that is why this audit cannot confirm or refute most of them.

## Reproducer

```bash
python3 -c "
import json
d=json.load(open('audit_dashboard/data/dashboard_data.json'))
rc=d['picks']['recent_closed']
for s in ['GC=F','SI=F','CL=F','CT=F','KC=F','ZS=F','ZW=F']:
    ps=[p for p in rc if p.get('symbol')==s]
    w=sum(1 for p in ps if float(p.get('pnl_pct',0) or 0)>0)
    tot=sum(float(p.get('pnl_pct',0) or 0) for p in ps)
    print(f'{s}: n={len(ps)} W={w} sum={tot:+.1f}')
"
```

## Provenance

- Phase 2-D kill: `audit_trail/quality_gates.py:1250-1273`, commit `162d1d8286d` (PR #535)
- Data: `audit_dashboard/data/dashboard_data.json::picks.recent_closed` (resolver-v2)
- Parent autopsy: `reports/deep_dive_cotton_2026-05-15.md` (PR #1061)
- Related: M-055 kill-threshold recalibration (proposed, unassigned)
