# Peer Review R2 — Archive B (scratch-hippodraco quick-wins)

**Archive:** `.kilo/worktrees/scratch-hippodraco/2026-11-14/scratch-hippodraco-quick-wins/`
**Date:** 2026-11-14 · **Status (README.md:3):** PROPOSALS ONLY — no code changed, nothing run against production; folder + source `../../scratch-hippodraco.MD` **untracked, not committed/pushed**.
**Reviewer:** R2 peer-review subagent (read-only).

---

## 1. Inventory

11 entries: `README.md` (index + top-10 + rollout), `overall/OVERALL.md`, per-class `crypto/CRYPTO.md`, `forex/FOREX.md`, `equity-stocks/EQUITY.md`, `etf/ETF.md`, `bond/BOND.md`, `futures/FUTURES.md`, `commodity/COMMODITY.md`, `mutual-funds/MUTUAL_FUNDS.md`, `peer-review/PEER_REVIEW.md`. All 11 read.

## 2. Key claims (quoted, sourced)

- **Verdict recap** (`README.md:7`): "Headline PnL is not trustworthy: mixed `pnl_pct` units (percent vs 0.01× fraction, 6,306 rows), resolver stalled ~7.5h while dashboard said fresh, 90,588 zombie OPEN picks, walkforward frozen 2026-04-15, no class money-ready on intrabar truth (CRYPTO PF 0.92, EQUITY 0.94, FOREX 0.66, ETF 0.02, BOND 0.39), mutual funds phantom."
- **Top-10 quick wins** (`README.md:25-37`): freshness badge/kill stale-green (ALL-1), PnL unit contract + guarded backfill (ALL-2), one clamp at write + reject 999,999% rows (ALL-3), zombie OPEN drain with NULL tombstone (ALL-4), reconcile active counts 20/158/4,148 + quarantine `active_raw` (ALL-5), artifact max-age stamps (ALL-6), intrabar-primary PF on cards (ALL-7), BOND gate honesty minTrades=0→insufficient (ALL-9), CI contract tests (ALL-8).
- **Overall platform QWs** (`overall/OVERALL.md`): ALL-1 `_compute_data_freshness()` (`audit_trail/dashboard_generator.py:3187-3227`) only checks active-picks mtime; ALL-2 `dashboard_generator.py:8065-8072` "heals" with `if abs(pnl)<0.10: pnl*=100` (converts +0.08%→+8%); ALL-4 90,567 OPEN + 21 ACTIVE (86,064 >7d); ALL-5 `active=20` vs sum 158 vs `active_raw=4,148`; ALL-3 COMMODITY `MAX|pnl|=999,999.9999`; ALL-7 13/20 picks current==entry; ALL-9 `alpha_engine/audit_sync.py:595` accepts only WON/LOST/EXPIRED, TP_HIT/SL_HIT silently dropped.
- **Per-class honest numbers** (each §4.1): CRYPTO intrabar PF 0.92 / WR 35.9% (n=3,705) NOT_READY (`CRYPTO.md:2`); EQUITY published PF **8.86 on n=8** vs window PF 1.15 (n=738) vs intrabar PF 0.94 / WR 59.2% (n=250) NOT_READY (`EQUITY.md:2`); ETF daily-bar PF 1.84 / WR 73.3% vs intrabar PF 0.02 / WR 2.2% (n=45) (`ETF.md:2`); BOND published PF 0.06 (n=3) vs window PF 0.59 (n=35) vs intrabar PF 0.39 / WR 7.7% (n=26) INSUFFICIENT_DATA (`BOND.md:2`); COMMODITY intrabar PF 1.03 / WR 40.2% (n=229) WATCH, DB stale since 2026-10-22 (`COMMODITY.md:2`); FOREX recent_closed PF 0.63, intrabar PF 0.66 / WR 32.2% (n=612) NOT_READY, expectancy ≈ −0.34%/trade, 43,056 OPEN (`FOREX.md:2`); FUTURES intrabar PF 1.09 / WR 42.3% (n=52) INSUFFICIENT_DATA, DB stale since 2026-10-31 (`FUTURES.md:2`); MUTUAL FUNDS phantom (`MUTUAL_FUNDS.md:2`).
- **Peer review** (`peer-review/PEER_REVIEW.md:16-23`): unit bug, staleness, fund gap are **three-way corroborated** (scratch/childlike/flaxen/hilarious); flaxen's ID-duplication and ml_score-coupling adopted. Ratings: childlike-airport **SOLID-WITH-CORRECTIONS** (`:27`), flaxen-hair **SOLID, most complete peer** (`:31`), hilarious-seer **WEAK on per-class depth** (5–6-line stubs; per-class claims non-citable) (`:41-43`).

## 3. Strengths

- **Most implementation-ready of the peers reviewed:** every fix carries a verified `file:line` target, effort class (S/M/L), a concrete verify step, and dry-run-first/backfill discipline. Subagent-refined sections supersede estimates with exact code locations.
- **Explicit three-way corroboration + adopt/reject traceability** (`peer-review/PEER_REVIEW.md:51-62`): what was taken from each peer and what was rejected and why (e.g. flaxen's ratio-convention and magnitude normaliser rejected → QW-ALL-2 recompute-or-NULL; `pnl_pct=0` fabrication snippets rejected → NULL tombstone).
- **Honesty engineering is excellent:** "keep dark / INSUFFICIENT_DATA rather than promote" policy in EQUITY/BOND/COMMODITY/FUTURES/MF; no DROP (quarantine); no destructive cleanup; requires republishing worse numbers as "the truth arriving."
- **Retire-vs-build decision for mutual funds is logically clean** (`MUTUAL_FUNDS.md`): EOD-NAV incompatible with intraday TP/SL engine; build = new product, not a quick win.
- **Covers the whole requested scope** (stocks/bonds/ETFs/MF/forex/crypto + commodity/futures).

## 4. Weaknesses / gaps

- **Nothing is implemented or tested** — status is "PROPOSALS ONLY", untracked, uncommitted. Effort estimates and `file:line` targets are unverified against a running build.
- **Primary evidence source (`../../scratch-hippodraco.MD`) is outside this subfolder and not read in this review** — the per-class numbers are attributed to that parent audit, not independently re-derived here.
- **Cross-class duplication is heavy:** the same-bar TP-before-SL fix and freshness-guardian extension recur in ETF/FUTURES/CRYPTO/FOREX; no single consolidated dependency list beyond the README top-10, so overlap risk across parallel implementation is real.
- **The over-strong rating of a peer (hilarious WEAK) is itself a claim to carry carefully** — the master plan should consume it as an opinion, not authority, and re-verify hilarious's per-class content.
- **Safe-rule examples sometimes leave a small honesty gap:** e.g. EQUITY/ETF display rules reference `money_ready_verdicts` logic that itself needs the PnL unit fix to be trustworthy (ordering dependency).

## 5. Recommend for master plan

- **Adopt QW-ALL-1..9 as the platform-level spine** and map each per-class QW onto it as a scoped execution (they share the same code root causes).
- **Adopt the PnL unit contract first** (percent-only + `pnl_source`, delete the generator ×100 guess, recompute-or-NULL): it is the highest-correctness single change and matches finpredict-v2's E-statistical/crypto findings on the same unit bug.
- **Adopt the NULL-tombstone zombie drain (ALL-4)** and the one-clamp-at-write + quarantine rules (ALL-3) — directly consistent with finpredict-v2's zombie quarantine recommendation.
- **Adopt min-n display floors and intrabar-primary cards** (EQUITY/ETF/BOND/FUTURES) so inflated `performance` PF numbers (8.86, 1.84 daily) never headline.
- **Adopt mutual-fund retirement + quarantine; adopt the credibility/exposure classification (GC=F vs GLD) work.**
- **Before merging, commit the archive on a clean branch** (per AGENTS.md convention) and re-verify the parent-audit numbers it restates; reconcile overlap with finpredict-v2's master plan so the two don't duplicate implementation.
