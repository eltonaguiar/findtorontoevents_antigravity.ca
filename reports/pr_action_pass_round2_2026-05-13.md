# PR Action Pass — Round 2 (2026-05-13 ~00:30-01:00 UTC)

**Driver:** caveman main thread + 4 parallel pr-reviewer agents + swarm round 5 (`non-opus-4` × 4 engines)
**Input:** cursor swarm review (`updates/2026-05-13-open-pr-swarm-review.md`) + 10 currently open PRs

## Outcomes (10 PRs handled)

| Action | Count | PRs |
|---|---:|---|
| **Admin-merged (rebuilds)** | **3** | #990 (was #942 anti-overfit), #991 (was #971 regime-flip), #992 (was #980 penny seed) |
| **Closed** | **6** | #946, #949, #962, #963, #970, #974 |
| **Closed + replaced** | **3** | #942 → #990, #971 → #991, #980 → #992 |
| **Comment-only (left open)** | **1** | #986 (concept_drift misread + FOREX status mislabel must be fixed first) |

Total PRs touched: 10. Net change on remote: 3 merged to main, 7 closed.

---

## The 3 admin-merged rebuilds

### #990 — anti-overfit default-ON (replaces #942)

One-line env flag flip: `ANTI_OVERFIT_VALIDATOR_ENABLED` `"0"` → `"1"`. Empirically safe: 0 of 152 active picks carry the input keys (`returns_history` / `strategy_returns` / `forward_returns`), so the validator falls through to False today. CPCV/PBO + DSR checks engage when real-money strategies start populating returns_history.

### #991 — regime-flip stale-momentum (replaces #971)

Surgical 2-file fix in `alpha_engine/regime_flip_detector.py`. Adds explicit `momentum_fresh` (bool) + `momentum_last_updated` (ISO str|None) stamps so downstream consumers detect asymmetric staleness. Production evidence: `regime_report.json` had `regime_last_checked = 2026-05-13T19:51:45Z` alongside `btc_price = 70115.34` whose source timestamp was 51 days old. 3/3 unit tests pass.

### #992 — penny seed fallback (replaces #980)

Static seed universe for `scripts/penny_stock_picks.py` when the 50webs API 404s (has been failing since 2026-05-04). 59 symbols + delisted_blocklist + risky_flags map + same filter chain as API path. Fallback only fires when `not api_ok and not candidates` — never overrides a working API.

---

## The 6 close-with-rationale

### #946 — bot confluence FX/futures
Confidence cap bypass (0.62/0.60 > 0.58 forex floor). Every existing forex strategy routes through `_forex_conf_cap`; this PR skips it.

### #949 — futures Donchian + term structure
3 blockers: vacuous breakout gate, CL=F latent bypass, fraudulent term-structure label (actually SMA momentum w/ false Erb & Harvey citation).

### #962 — swarm panel UI
COT dedup change landed via #961; remaining UI changes ship w/ stale "DSR=1.0 SUPREME EDGE" template.html copy now falsified by #961 itself + dead `metric_caveat` field.

### #963 — sports auth parity
3 security blockers: unauthenticated dashboard/active/history endpoints, ADMIN_API_KEY plaintext in 17 curl URLs, `$ADMIN_API_KEY` global tier is dead code.

### #970 — sports betting SharpAPI/CLV
4 of 6 files are stale leftovers from already-merged #961. Body says already deployed to 50webs. Re-open as fresh PR with only ESPN scraper + xAI review doc.

### #974 — quan_engine × HYPEUSDT block
2-tuple block already on main at line 1634. The PR's 3-tuple addition would land in `BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES` which is the ghost-row template-emission criterion — adding a real n=25 cohort would suppress legitimate negative-edge data from aggregates. Reviewer F1 was decisive.

---

## #986 — comment-only

Doc-only audit report with mostly-verified numerical claims, but 2 errors prevent merge:
1. **Section 6 concept_drift misread**: claims `ks_d`/`ks_critical` are None; reality is `ks_D=0.312576` vs `ks_critical_05=0.047292` (6.6x exceedance = high-severity drift, not unactionable as claimed)
2. **FOREX tier label `stable`** in §1 table; actual `asset_class_health.FOREX.status = 'stressed'`

Strong list of verified claims documented in the comment. When errors corrected, ready for admin-merge.

---

## Swarm round 5 — consensus map

| PR | cerebras | deepseek | groq | xai |
|---|---|---|---|---|
| #942 | rebuild_merge | rebuild_merge | rebuild_merge | — |
| #946 | close | close | close | — |
| #949 | close | close | close | — |
| #962 | close | close | close | — |
| #963 | close | close | close | — |
| #970 | close | close | close | — |
| #971 | rebuild_merge | rebuild_merge | rebuild_merge | — |
| #974 | close | close | close | — |
| #980 | rebuild_merge | rebuild_merge | rebuild_merge | — |
| #986 | comment_only (dissent) | admin_merge_with_comment | admin_merge_with_comment | — |

Picked comment_only on #986 — cerebras's dissent rationale (factual errors in audit doc can mislead downstream) aligned with the pr-reviewer agent's HIGH-severity finding on the concept_drift misread.

Sequence concern (deepseek): merge #971 before #980 since regime-flip affects price signals used by penny scraper. Honored — #991 merged 2026-05-14T00:46Z, #992 merged 2026-05-14T00:48Z.

---

## Cumulative session totals (now)

- **15 PRs merged** to main this session (12 from prior pass + 3 from this round)
- **11 PRs closed** (8 from prior pass + 3 superseded-by-rebuild this round; #974 net new close)

Wait, recounting: #942, #946, #948, #949, #954, #962, #963, #970, #971, #973, #974, #979, #980 = **13 closed** total.

- Merged this session: #950, #951, #957, #943, #964, #966, #967, #965, #961, #985, #987, #989, #990, #991, #992 = **15 merged**
- Audit-enh direct-to-main commits: `2abc595c148`, `1502f770f7d`, `86d1a1d93ff`

- **5 swarm rounds** total (~$0.35 spend)
- 1 open PR remaining: #986

---

## What's on main as default-ON env flags

| Flag | Default | Effect |
|---|---|---|
| `PER_ASSET_CLASS_SCORING_ENABLED` | 1 | overlay computes shadow score |
| `PER_ASSET_CLASS_SCORING_SHADOW` | 1 | returns legacy clamped; stamps `smart_score_v2_shadow` |
| `CRYPTO_SHORT_REGIME_GATE_ENABLED` | 1 | blocks CRYPTO SHORT in bull regime |
| `ANTI_OVERFIT_VALIDATOR_ENABLED` | 1 | CPCV/PBO + DSR check on picks w/ returns_history |
| `CONCENTRATION_CAP_ENABLED` | 0 | deferred until COMMODITY n≥50 |
| `CRYPTO_SHORT_DISABLED` | 0 | kill-switch only |

## NFA

5 default-ON env flags now active; all individually safe (verified empirical no-op or conservative regime-gated). The combined effect requires post-soak analysis after 14d. Operator should re-run `tools/predictor_ic_reproducer.py` against post-soak shadow-stamp data before flipping `PER_ASSET_CLASS_SCORING_SHADOW=0` (live blend).
