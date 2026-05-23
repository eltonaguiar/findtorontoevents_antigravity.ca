# Executive summary — where we stand (2026-05-19)

**North star:** Tier-2 per class (PF≥1.5, WR≥50%, MDD<20%, **n≥100 clean**). **Paper-only** until harness admits edge.

---

## 1. Canonical performance (`pf_registry` → `policy_clean_net`)

| Class | n | PF | WR% | Status |
|-------|---|-----|-----|--------|
| **CRYPTO** | 1127 | **0.66** | 44% | Losing at class level; elite strategies masked by volume/dedup |
| **COMMODITY** | 55 | **1.42** | 55% | Best rescue candidate (`multi_asset_cot`); not yet n≥100 |
| **FOREX** | 150 | 1.40* | 56%* | *Slice only* — class **blocked** (0% risk cap); copytrader drag |
| **EQUITY** | 5 | 0.25 | 20% | **Broken flow** — almost no clean picks |
| **ETF** | 2 | — | 50% | Not operable |
| **BOND** | 5 | 0.00 | 0% | Freeze |

**Settled:** 11/11 daily-bar causal hypotheses **KILLED** (`edge_stability_harness.py`). Registry PF ≠ admissible edge.

---

## 2. Root cause (why months of AI runs didn’t fix profit)

| Layer | Problem |
|-------|---------|
| **Measurement** | Raw / deduped / policy_clean / per-symbol ML disagree — teams optimized wrong PF |
| **Emission** | `quan_engine` drag, toxic pairs, whitelist **shadow-only** (`ENFORCE=0`) |
| **Hypotheses** | Recycling killed families (daily COT, funding, generic PEAD) |
| **AI loop** | Great diagnostics; weak closure (harness + wire_target often not shipped) |
| **Thin books** | EQUITY/BOND/ETF barely emit into canonical ledger |

**Not the bottleneck:** lack of Grok vs Ollama vs bigger GPU for brainstorming.

---

## 3. What this session shipped

| Track | Artifacts |
|-------|-----------|
| **Rescue round** | `tools/rescue_edge_round.py`, RESCUE prompts, `reports/RESCUE_*` — **committed** `3cfec787883` |
| **Strategy harvest** | `tools/build_top10_strategies_per_class.py`, `strategy_harvest_round.py`, TOP10 MD, meta-debate, synthesis — **local, commit pending** |
| **Peer (Opus)** | Ensemble CRYPTO blocked; H-037 canonical **REJECT**; see `reports/EXECUTIVE_SUMMARY_2026-05-19T2240Z.md` |

**Weekly loop:** `build_top10` → `strategy_harvest_round.py --phase all` → **one** harness pre-reg per class.

---

## 4. Multi-AI consensus (your decisions)

### GX10 investment

| Model | Vote | Hardware-alone fixes classes |
|-------|------|------------------------------|
| Grok (WSL) | **B** — no hardware, fix pipeline | 10% |
| DeepSeek | **B** | 15% |
| xAI API | **C** — fixes 60d, then GX10 if tick fine-tune | 15% |

**Autonomous consensus:** **B now** (equivalent to **C** with 60-day gate). **Do not buy GX10** until pipeline Tier 1–2 green and you have a **daily tick fine-tune** workload. Cloud + RTX 5070 14B is **enough for debate/harvest**.

### EMITTER_WHITELIST_ENFORCE

Peer Opus swarm: **Option C** — forward **200-close clean window** before enforce=1.  
Align: measure CRYPTO elite-only WR lift in shadow, then flip enforce.

### H-037

Peer Opus: **REJECT** under canonical harness (not live-shadow). Do not promote from registry PASS alone.

---

## 5. P0 next 14 days (engineering, not hardware)

1. **Tier-1 data integrity** — dedup, confidence clamp, dashboard reads only `policy_clean_net`  
2. **Emitter hygiene** — block `quan_engine`/ensemble drag; path to **ENFORCE=1** with forward window  
3. **Per-class bets** — CRYPTO H-035 **tick**; COMMODITY `multi_asset_cot` verify; FOREX isolated `cta_replicator` paper only  
4. **Freeze** EQUITY/ETF/BOND new emissions (90d) except PEAD/trust_score  
5. **Commit** strategy harvest tools to `main` when ready  

---

## 6. Key files

- `reports/TOP10_STRATEGIES_PER_ASSET_CLASS_2026-05-19.md`
- `reports/META_PROMPTS_RECOMMENDATIONS_2026-05-19.md`
- `reports/MERGED_ACTION_PLAN_2026-05-19.md`
- `audit_dashboard/data/pf_registry.json`
- `alpha_engine/emitter_whitelist.py`

---

## 7. Decisions needing you (pre-filled by swarm)

| Decision | Swarm recommendation | Your call |
|----------|---------------------|-----------|
| Buy GX10 in 90d | **No** — revisit after 60d pipeline + tick jobs | ☐ Agree / ☐ Disagree |
| `EMITTER_WHITELIST_ENFORCE=1` | **After** 200-close forward clean window | ☐ Approve timeline |
| Tick data budget | Tardis vs free Binance aggTrade (peer Opus) | ☐ Authorize |
| Commit strategy harvest batch | 8 files + reports | ☐ Commit to main |
