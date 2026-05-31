# Tick21 — Reconcile buffy's claimed conflicts (FOREX whitelist + PR #162/#210)

**Date:** 2026-05-31
**Agent:** claude-tick21-buffy-conflict-reconcile
**Verdict:** Both claimed conflicts are **non-issues** — the premises that drove the task are incorrect.

---

## Conflict 1 — "FOREX whitelist already includes `cta_cross_asset_tsmom` SHORT"

### Premise (from task)
> buffy's session decided FOREX whitelist includes cta_cross_asset_tsmom SHORT
> (confirmed loser per live data)

### Ground truth (verbatim from `alpha_engine/non_crypto_policy.py` HEAD)

`grep -n cta_cross_asset_tsmom alpha_engine/non_crypto_policy.py` → **zero matches**.

The strategy is **NOT** registered in `NON_CRYPTO_STRATEGY_POLICY`. There is no `_FOREX_ALLOWED` constant in the codebase (`grep -rn "_FOREX_ALLOWED" alpha_engine/ tools/` → empty).

The closest landed entries in the FOREX section of the dict are:
- `forex_rsi2_mean_reversion` (line 240)
- `inverse_carry_contrarian` (line 260)
- `carry_trade_momentum` (line 269)
- `forex_carry_ppp` (line 280)

### Where buffy's claim came from

Commit `5676eace2` "fix(forex): register cta_cross_asset_tsmom in non_crypto policy for consolidation" exists in the repo, but:

- `git merge-base --is-ancestor 5676eace2 HEAD` → **NOT ANCESTOR**
- Lives only on branches: `fix/incidents-p0-batch-2026-05-31`, `fix/incidents-signal-time-forex-2026-05-31`, `pr126`, `qwen-review/pr-126`.
- Container PR **#126 is CLOSED, not merged.**

So buffy's whitelist change was authored but **never landed on main**. There is nothing to revert.

### Live data on the strategies (verified against `mysql.50webs.com / ejaguiar1_stocks.trading_picks`, 2026-05-31)

`cta_cross_asset_tsmom` FOREX, status NOT IN (OPEN/ACTIVE/PENDING):

| Window | n | WR | PF | LONG | SHORT |
|---|---:|---:|---:|---:|---:|
| 30d total | 163 | 39.9% | **2.58** | 13 | 150 |
| 30d SHORT | 150 | 38.7% | **2.53** | — | — |
| 30d LONG | 13 | 53.8% | 3.13 | — | — |
| 90d total | 852 | 11.9% | **0.81** | — | — |

`dxy_trend_filter`: **n=0 in 30d and 90d** — not emitting. `grep -rn "def dxy_trend_filter"` → no definition anywhere in repo. **It is not a registered strategy.** The task's framing of "dxy_trend_filter is the correct candidate" has no codebase grounding.

### Interpretation

- 30d PF=2.58 is consistent with the recent FOREX resolver clamp (PR #120) and sign-based integrity (PR #210) fixing the historical loss distortion. Recent SHORT performance is actually mildly **positive** by PF, not the "confirmed loser" the task claims.
- 90d still shows PF=0.81 because pre-fix rows are not retroactively repaired in trading_picks (only `tools/repair_data_integrity.py` from PR #162 does that, and only for sign-flips).
- This is the classic "mutate before kill" case — recency improving, history bad. Concentration on SHORT (92% of n) + USDJPY-heavy admission gate from buffy's draft was probably correct in spirit.

### Recommendation — Conflict 1

**No PR action. Status quo is correct.** Buffy's whitelist change is not on main, so nothing to revert. If anyone wants to actually land it, they should:

1. Re-open or re-author from `5676eace2` (the +11 line dict entry).
2. Pair it with the SHORT-only admission gate buffy mentioned in the commit body (currently not in `evaluate_non_crypto_candidate`).
3. Use a tighter `min_forward_wr` (e.g. 0.40) given 90d WR=11.9%.

But that's a forward-edit decision, **not a conflict to reconcile**.

---

## Conflict 2 — "PR #162 overlaps PR #210"

### PR #162 (MERGED 2026-05-31T05:32:11Z)
- Title: `fix(repair): PR #8 — PnL sign-flip + status mismatch repair + tiered pnl_integrity`
- Files: `tools/repair_data_integrity.py` (+705 / -0)
- Adds `_repair_pnl_sign_flip`, `_repair_pnl_status_mismatch`, and a tiered CTE classifier for sign_flip / moderate / noise tiers.

### PR #210 (MERGED 2026-05-31T07:02:43Z)
- Title: `fix(db-integrity): sign-based pnl_integrity (leverage-agnostic) + canonical status writer`
- Files: `alpha_engine/mysql_trading_sync.py` (+42/-12), `tools/db_health_check.py` (+44/-17)
- Replaces magnitude-based `pnl_integrity` with sign-only check in `db_health_check.py` and makes `mysql_trading_sync.pick_to_row` emit canonical statuses only.

### Overlap analysis

- **Different files.** No edit collision.
- **Complementary, not redundant:**
  - #162 = forward-rewrites bad historical rows (a repair tool).
  - #210 = changes the health-check threshold semantics + stops the writer from re-emitting legacy `WON` status.
- Both shipped, both merged, no observed breakage on `audit_dashboard/data/db_health.json` (`pnl_integrity` reads green 0.54% per #210 body, consistent with #162 having already cleaned the small sign-flip tier).

### Recommendation — Conflict 2

**No PR action. Both already merged, no conflict to reconcile.** If buffy's "PR #162 overlaps #210" comment was forward-looking (i.e. before #210 merged), it is now stale.

---

## Output packet

| Item | Action | Rationale | Operator command |
|---|---|---|---|
| FOREX whitelist `cta_cross_asset_tsmom` SHORT | **none** | Never landed on main; nothing to revert. | `git merge-base --is-ancestor 5676eace2 HEAD; echo $?` → non-zero |
| `dxy_trend_filter` as alternative | **drop the suggestion** | No such strategy exists in the codebase. | `grep -rn "def dxy_trend_filter" alpha_engine/ tools/` → empty |
| PR #162 | **already merged**, no action | Different files than #210, complementary. | `gh pr view 162 --json state,mergedAt` |
| PR #210 | **already merged**, no action | Sign-based pnl_integrity is live. | `gh pr view 210 --json state,mergedAt` |
| Peer message to buffy | yes | Explain both premises are wrong; no further work. | — |

---

## Red-team self-check

- ✅ Verbatim grep on `alpha_engine/non_crypto_policy.py` — no `cta_cross_asset_tsmom`.
- ✅ Verbatim `git merge-base --is-ancestor` confirms commit not on main.
- ✅ Verbatim `gh pr view 162/210 --json state` confirms both MERGED.
- ✅ Live DB query (mysql.50webs.com) — actual numbers cited, not hallucinated.
- ⚠️ The premise "confirmed loser" is contradicted by 30d data; only 90d still looks bad. Mutation, not kill, would be the right call IF anyone wanted to land buffy's whitelist — but that's a separate decision.

## Return signal

`BUFFY_RECONCILE:forex_conflict=resolved:pr162_verdict=already_merged:peer_msgs_sent=0:PR=docs_only`
