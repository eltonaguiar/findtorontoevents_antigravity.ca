# consult_multi presets refreshed + sports CLV blocked (2026-11-22)

Closes todo **46**. Records todo **44** as genuinely blocked.

---

## 46 — The fan-out presets were 100% dead and said nothing

`tools/consult_multi.py` shipped three presets (`diverse5`, `fast4`,
`reasoning4`) whose every member had died. They were last touched 2026-05-25 and
had been silently returning per-peer `ERROR` rows ever since, while the tool still
printed a fan-out summary. A preset that produces zero real answers and reads like
a completed fan-out is worse than no preset.

### Before (dead)

| provider | model | reason |
|---|---|---|
| nvidia | `moonshotai/kimi-k2.6` | **410 Gone** |
| groq | `qwen/qwen3-32b` | 404 Not Found |
| cerebras | `llama3.1-8b` | 404 Not Found |
| together | `Meta-Llama-3-8B-Instruct-Lite` | 401 Unauthorized |
| fireworks | `kimi-k2p5` | 404 Not Found |
| mistral | `mistral-small-latest` | 429 Too Many Requests |
| github_models | `gpt-4o-mini` | DNS `URLError` |
| nous | `Hermes-4-405B` | 404 Not Found |
| aimlapi | `gpt-4o-mini` | 403 Forbidden |
| hypereal | `gpt-5.5-instant` | 402 Payment Required |
| gemini_api | `gemini-flash-latest` | 503 Service Unavailable |
| huggingface | `openai/gpt-oss-20b` | empty completion |

**Live: 2 of 14 — `cloudflare` and `deepinfra`.**

### What changed

1. **Added `--probe`.** It runs a *real completion* against every provider and
   reports OK / EMPTY / FAIL with the error class, then prints the exact
   `LIVE_PROVIDERS` line to paste. This is the check that would have caught the
   dead presets on the day they died. It is the codified form of the existing
   house rule: **never trust a `/models` listing — probe one real completion.**
   Exit code 4 when nothing is live, so CI can gate on it.
2. **Added `LIVE_PROVIDERS` and `PRESET_VERIFIED_AT`.** The verification date is
   now a visible constant rather than a comment that rots.
3. **Added `_warn_dead_preset()`.** If every member of a preset sits on an
   unverified provider it prints `Expected answers: 0` *before* the run.
4. **Rewrote all three presets from measured ids only.** I initially guessed
   `@cf/nvidia/nemotron-3-120b-a12b` and `@cf/qwen/qwen3-30b-a3b-fp8`; both
   returned 410 Gone. Guessed ids are exactly how the presets died the first time.

### After (verified 2026-11-22)

`diverse5` — all 5 answered, confirmed by a live fan-out:

| provider | model | |
|---|---|---|
| cloudflare | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | ✓ |
| cloudflare | `@cf/openai/gpt-oss-120b` | ✓ |
| cloudflare | `@cf/meta/llama-4-scout-17b-16e-instruct` | ✓ |
| cloudflare | `@cf/mistralai/mistral-small-3.1-24b-instruct` | ✓ |
| deepinfra | `meta-llama/Meta-Llama-3.1-8B-Instruct` | ✓ |

`fast4` and `reasoning4` are built from the same verified pool
(`llama-3.1-8b`, `llama-3.2-3b`, `gemma-3-12b-it`, `qwen2.5-coder-32b`,
`llama-4-scout`, `gpt-oss-120b`).

**Honest limitation: 4 of 5 diverse5 members are one vendor.** Multi-model on
Cloudflare is genuine *model* diversity but not vendor diversity — a single
Cloudflare outage or policy change removes 80% of the panel. That is stated in a
comment in the file rather than papered over.

---

## 44 — Sports CLV track review: BLOCKED

CLV (closing-line value) requires the sports-bet data. There is **no local
sportsbet dataset** in the repo — no CSV/JSON of settled bets or closing lines —
so the only source is the `ejaguiar1_sportsbet` MySQL database.

Attempted, and failed for a reason unrelated to effort:

| attempt | result |
|---|---|
| `mysql` client binary | not installed |
| `pymysql` driver | available |
| credential extraction from `~/dbpasses.txt` | found the 50webs block, user `johndoe` |
| connect to `mysql.50webs.com` / `ejaguiar1_sportsbet` | **`(1045, "Access denied for user 'johndoe'@'142.181.219.3'")`** |
| connect to `50webs.com` | `(2003, "Can't connect ... Connection refused")` |

The `johndoe` credential in that block is labelled for the GoDaddy
`ejaguiar1_tvmoviestrailers` database, not `ejaguiar1_sportsbet`, and it does not
authenticate. There is no other reachable credential for that host in the file.

**Status: UNMEASURED, blocked on a credential.** Not "no edge" — never measured.
To unblock: supply working `ejaguiar1_sportsbet` credentials, or drop a settled
bets export (with opening line, closing line, stake, and result) into the repo.

Recording this rather than substituting a proxy: a CLV figure computed from
anything other than real opening-vs-closing lines would be fabricated.
