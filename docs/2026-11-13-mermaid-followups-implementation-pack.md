# Implementation pack — the three follow-ups, fully specified (nothing here has been run)

**Status:** documentation only. No code in this file has been executed, no repo created, no deploy,
no workflow edited. **Date:** 2026-11-13.
**Parent documents:** `docs/2026-11-13-mermaid-pages-verification-design.md` (the design and its
gates), `updates/2026-11-13-freebuff-mermaid-bench-handoff.md` (what was measured).
**Coordination index:** `/tmp/freebuff.txt`, `SYNC 14`.

This pack exists so the three suggested follow-ups do not depend on me being available, and so
nobody has to re-derive the code. Each part ships the artifact in full, the exact commands, and the
acceptance test that proves it works. Where a value cannot be known without asking, it is a
parameter with a note, not a guess.

**Standing rule for every part:** the site pins mermaid **10.9.1**. A grader that runs 12.x
(`mmdc` here is 12.2.0, the repo detector 12.3.0) is measuring the wrong thing. All grading below
uses `validate.mjs` at 10.9.1.

---

# Part 1 — A1 attribution: which concrete model actually fixed the diagrams

## 1.1 What it answers

The benchmark scored router aliases. `ULTRA_PAID_MODE` maps to `openai/mimo-v2.5-pro` **and** falls
back to `ULTRA_FREE_CLOUD_LARGE` / `ULTRA_FREE_CLOUD`, so its 5/5 may have come from free
deployments. A1 removes the router from the path: one pinned model per provider, called directly, so
the answer to "which model, how often" is structural rather than inferred.

## 1.2 Prerequisites

- `/tmp/mm_bench/validate.mjs` + `/tmp/mm_bench/node/` (mermaid 10.9.1, jsdom) already exist.
  Recreate with: `mkdir -p /tmp/mm_bench/node && cd /tmp/mm_bench/node && npm init -y && npm i mermaid@10.9.1 jsdom@24`.
- Provider keys in `~/dbpasses.txt` or the environment. **Values are never printed, logged, or
  committed** — the helper below reads by name and raises on a miss.
- Model ids: take them from the consult tool already in use (`/consult-multi list`) rather than
  hardcoding. The script's first act is a **probe** call per target and it records the id the
  provider itself echoes — if that differs from the request, the echoed id wins.

## 1.3 `targets.json` — one entry per provider you intend to compare

```json
[
  {"name": "nvidia-deepseek",  "base": "https://integrate.api.nvidia.com/v1", "key_env": "NVIDIA_API_KEY",  "model": "<from consult-multi list>"},
  {"name": "groq-llama",       "base": "https://api.groq.com/openai/v1",      "key_env": "GROQ_API_KEY",    "model": "<from consult-multi list>"},
  {"name": "cerebras-qwen",    "base": "https://api.cerebras.ai/v1",          "key_env": "CEREBRAS_API_KEY","model": "<from consult-multi list>"},
  {"name": "gemini-flash",     "base": "https://generativelanguage.googleapis.com/v1beta/openai", "key_env": "GEMINI_API_KEY", "model": "<from consult-multi list>"},
  {"name": "xiaomi-mimo-pro",  "base": "https://token-plan-sgp.xiaomimimo.com/v1", "key_env": "XIAOMI_MIMO_TOKEN_PLAN", "model": "mimo-v2.5-pro"}
]
```

The `xiaomi-mimo-pro` row is the deployment behind `ULTRA_PAID_MODE` per `litellm_config.yaml`; it
is the row that settles the paid question. Add or drop rows freely — the script does not care how
many.

## 1.4 `attribute_models.py`

```python
#!/usr/bin/env python3
"""A1 attribution: pin one model per provider, run the 5-case corpus N times, grade at L0+L1.

Nothing is printed but names, verdicts and latencies. Keys are read by NAME and never echoed.
"""
import concurrent.futures as cf
import json, math, os, pathlib, re, subprocess, sys, time, urllib.request

BENCH = pathlib.Path("/tmp/mm_bench")
VALIDATOR = BENCH / "validate.mjs"
CASES = json.loads((BENCH / "corpus_cases.json").read_text())   # {"A": "flowchart TD\n...", ...}
ATTEMPTS = int(os.environ.get("ATTEMPTS", "10"))
NODE_RE = re.compile(r"(?<![A-Za-z0-9_])([A-Z][A-Za-z0-9_]*)\s*[\[\(\{]")
PROMPT = ("Fix this mermaid diagram. It fails to parse in mermaid.js 10.9.1.\n\n"
          "Return ONLY a fenced ```mermaid block containing the corrected diagram. No prose.\n"
          "Keep every node and edge that is already there.\n\n```mermaid\n{diagram}\n```")


def key(name: str) -> str:
    """Env first, then ~/dbpasses.txt by KEY=value or KEY: value. Never log the value."""
    if os.environ.get(name):
        return os.environ[name]
    for line in (pathlib.Path.home() / "dbpasses.txt").read_text(errors="ignore").splitlines():
        m = re.match(rf"\s*{re.escape(name)}\s*[=:]\s*(\S+)", line)
        if m:
            return m.group(1)
    raise SystemExit(f"missing key: {name}")


def call(t: dict, diagram: str, timeout: int = 90):
    body = json.dumps({"model": t["model"], "temperature": 0,
                       "messages": [{"role": "user", "content": PROMPT.format(diagram=diagram)}]}).encode()
    req = urllib.request.Request(f"{t['base'].rstrip('/')}/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {key(t['key_env'])}"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    return d["choices"][0]["message"]["content"], d.get("model", t["model"]), time.time() - t0


def extract(answer: str):
    m = re.search(r"```(?:mermaid)?\s*\n(.*?)```", answer, re.S)
    return (m.group(1) if m else answer).strip() or None


def grade(block: str, original: str):
    p = BENCH / f"cand_{abs(hash((block, time.time()))) % 10**12}.mmd"
    p.write_text(block)
    try:
        out = subprocess.run(["node", str(VALIDATOR), str(p)], capture_output=True, text=True,
                             timeout=60).stdout.strip()
        d = json.loads(out or '{"ok": false, "err": "no output"}')
    finally:
        p.unlink(missing_ok=True)
    missing = sorted(set(NODE_RE.findall(original)) - set(NODE_RE.findall(block)))
    return bool(d.get("ok") and not missing), d.get("err"), missing


def wilson(k: int, n: int):
    if not n:
        return (0.0, 0.0)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def one(t: dict, cid: str, diagram: str):
    rec = {"target": t["name"], "case": cid, "requested": t["model"]}
    try:
        answer, served, secs = call(t, diagram)
    except Exception as exc:                      # a provider failure is a datapoint, not a crash
        rec.update(ok=False, reason=f"call failed: {type(exc).__name__}", secs=0.0)
        return rec
    rec.update(served=served, secs=round(secs, 1))
    block = extract(answer)
    if not block:
        rec.update(ok=False, reason="empty answer")
        return rec
    ok, err, missing = grade(block, diagram)
    rec.update(ok=ok, err=err, missing=missing,
               reason="pass" if ok else ("parse error at 10.9.1" if err else f"dropped {missing}"))
    return rec


def main():
    targets = json.loads(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "targets.json").read_text())
    jobs = [(t, cid, d) for t in targets for cid, d in CASES.items() for _ in range(ATTEMPTS)]
    results = []
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for fut in cf.as_completed([ex.submit(one, t, cid, d) for t, cid, d in jobs]):
            r = fut.result()
            results.append(r)
            print(f"{'PASS' if r['ok'] else 'FAIL'} {r['target']:16s} {r['case']:3s} "
                  f"{r.get('served', '-'):28s} {r.get('secs', 0):5.1f}s {r.get('reason', '')}", flush=True)
    pathlib.Path("results_attrib.json").write_text(json.dumps(results, indent=2))

    print("\ntarget              pass     95% CI            fallbacks  latency")
    for t in targets:
        rs = [r for r in results if r["target"] == t["name"]]
        answered = [r for r in rs if not str(r.get("reason", "")).startswith("call failed")]
        k, n = sum(1 for r in answered if r["ok"]), len(answered)
        lo, hi = wilson(k, n)
        fb = sum(1 for r in answered if r.get("served") and r["served"] != r["requested"])
        lat = sum(r.get("secs", 0) for r in answered)
        print(f"{t['name']:18s} {k:2d}/{n:<2d}  {lo:4.0%}-{hi:4.0%}          {fb:3d}      {lat:6.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`corpus_cases.json` is the same five diagrams the benchmark used (A unquoted parens, B smart quotes,
C unclosed subgraph, D type not on line 1, E pipe in label) — copy them out of
`/tmp/mm_bench/corpus.md`, or from `bench.py`'s `CASES` list.

## 1.5 Run and acceptance

```bash
cd /tmp/mm_bench
ATTEMPTS=10 python3 attribute_models.py targets.json | tee attrib.log
```

| Gate | Assertion | How it fails loudly |
|---|---|---|
| A1-G1 | every answered call carries a non-empty `served` id | a target whose provider omits the field shows `-` in the column |
| A1-G2 | fallback count reported, not guessed | the `fallbacks` column, non-zero means the pinned id is not what answered |
| A1-G3 | new table supersedes the old; the old file is untouched | `results_attrib.json` is a new file; `results.json` is never edited |
| A1-G4 | control still passes | case `B` on any working provider must be PASS |
| A1-G5 | no key ever appears in output | `grep -c "$(…)` is not possible if you never store it; check `attrib.log` for the key prefix patterns |

**Interpretation guard:** with n=10 the Wilson CI is wide (±25 pts at 50%). Report the interval, not
just the fraction, or the table invites the same over-reading the 5-case run did.

**What must NOT change:** the router. A1 never edits `litellm_config.yaml` and never restarts the
proxy — that is the whole point of preferring it to A2.

---

# Part 2 — the fixture page and runner (built and proven locally, deployed only on a yes)

## 2.1 Files

```
mermaid-fixture/
  index.html
  cases/index.json        # ["N_control_bad","P_control_good","A","B","C","D","E","F_liquid"]
  cases/*.mmd             # one file per case id
  runner.py
  README.md
```

## 2.2 `index.html`

```html
<!doctype html>
<meta charset="utf-8">
<title>mermaid 10.9.1 fixture</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<body>
<div id="host"></div>
<script>
  // The site's shim rule: a block whose first non-blank line is not a diagram keyword is skipped
  // and rendered as raw text. Replicated on purpose so it is tested, not assumed.
  const KEYWORDS = ["flowchart","graph","sequenceDiagram","classDiagram","stateDiagram-v2",
    "erDiagram","gantt","pie","journey","mindmap","timeline","quadrantChart",
    "requirementDiagram","gitGraph","C4Context","sankey-beta","xychart-beta","block-beta"];

  window.__FIXTURE__ = [];
  window.__MERMAID_VERSION__ = (mermaid.mermaidAPI && mermaid.mermaidAPI.version)
                            || mermaid.version || "unknown";
  mermaid.initialize({ startOnLoad: false, securityLevel: "loose" });

  async function run() {
    const ids = await (await fetch("cases/index.json", { cache: "no-store" })).json();
    const host = document.getElementById("host");
    for (const id of ids) {
      const text = await (await fetch(`cases/${id}.mmd`, { cache: "no-store" })).text();
      const first = (text.split("\n").map(s => s.trim()).find(Boolean) || "");
      const rec = { case: id, shim: null, rendered: false, error: null };

      if (!KEYWORDS.some(k => first.startsWith(k))) {
        rec.shim = "skipped";                      // case D must land here
      } else {
        rec.shim = "ran";
        try { await mermaid.parse(text); }
        catch (e) { rec.error = String((e && e.message) || e).replace(/\s+/g, " ").slice(0, 300); }
        if (!rec.error) {
          try {
            const { svg } = await mermaid.render("d_" + id, text);
            host.insertAdjacentHTML("beforeend", svg);
            if (/Syntax error in text/i.test(svg)) rec.error = "svg contains Syntax error in text";
            else rec.rendered = true;
          } catch (e) { rec.error = String((e && e.message) || e).replace(/\s+/g, " ").slice(0, 300); }
        }
      }
      window.__FIXTURE__.push(rec);
    }
    document.title = `fixture done (${window.__FIXTURE__.length})`;
  }
  run();
</script>
```

The Liquid class (case `F_liquid`) goes in its own Jekyll page wrapped in `{% raw %}`; it is the one
case whose verdict comes from the **build**, not from the browser, so `runner.py` scores it from the
Pages build result rather than from `window.__FIXTURE__`.

## 2.3 Local preflight — no deploy, no permission needed

```bash
cd mermaid-fixture && python3 -m http.server 8099 &
python3 - <<'PY'
import asyncio, json
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        await pg.goto("http://localhost:8099/", wait_until="networkidle")
        await pg.wait_for_function("window.__FIXTURE__ && window.__FIXTURE__.length > 0")
        print(json.dumps({"version": await pg.evaluate("window.__MERMAID_VERSION__"),
                          "verdicts": await pg.evaluate("window.__FIXTURE__")}, indent=2))
        await b.close()
asyncio.run(main())
PY
```

Expected locally: `version == "10.9.1"`, `N_control_bad` rendered false with a parse error,
`P_control_good` rendered true, `D` shim `"skipped"`, `F_liquid` unverifiable locally (no Jekyll).

## 2.4 `runner.py`

```python
#!/usr/bin/env python3
"""Push one answer set into the fixture repo, wait for the Pages build, read the verdicts, score."""
import json, pathlib, subprocess, sys, time, urllib.request

REPO = "eltonaguiar/mermaid-fixture"      # placeholder — owner must confirm name + visibility
FIXTURE = pathlib.Path(__file__).resolve().parent
CASES = ["N_control_bad", "P_control_good", "A", "B", "C", "D", "E"]


def gh(path):
    out = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def commit_and_push(answers: pathlib.Path, run: str):
    for c in CASES:
        src = answers / f"{c}.mmd"
        if src.exists():
            (FIXTURE / "cases" / f"{c}.mmd").write_text(src.read_text())
    subprocess.run(["git", "-C", str(FIXTURE), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(FIXTURE), "commit", "-m", f"answers: {run}"], check=True)
    subprocess.run(["git", "-C", str(FIXTURE), "push"], check=True)
    return subprocess.run(["git", "-C", str(FIXTURE), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()


def wait_for_build(sha: str, timeout: int = 900):
    deadline = time.time() + timeout
    while time.time() < deadline:
        b = gh(f"repos/{REPO}/pages/builds/latest")
        if b.get("commit") == sha and b.get("status") == "built":
            return b
        if b.get("status") == "errored":
            raise SystemExit(f"Pages build errored: {b.get('error')}")
        time.sleep(10)
    raise SystemExit("Pages build did not finish inside 15 min")


def read_page(url: str):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto(url, wait_until="networkidle")
        pg.wait_for_function("window.__FIXTURE__ && window.__FIXTURE__.length > 0", timeout=60000)
        data = {"version": pg.evaluate("window.__MERMAID_VERSION__"),
                "verdicts": pg.evaluate("window.__FIXTURE__")}
        b.close()
    return data


def gates(data):
    v = {r["case"]: r for r in data["verdicts"]}
    checks = {
        "B-G1 negative control fails": v.get("N_control_bad", {}).get("rendered") is False,
        "B-G2 positive control passes": v.get("P_control_good", {}).get("rendered") is True,
        "B-G3 shim rule is live (case D skipped)": v.get("D", {}).get("shim") == "skipped",
        "B-G6 pinned version is 10.9.1": str(data.get("version")) == "10.9.1",
    }
    for k, ok in checks.items():
        print(("PASS  " if ok else "FAIL  ") + k)
    return all(checks.values())


if __name__ == "__main__":
    answers = pathlib.Path(sys.argv[1])
    sha = commit_and_push(answers, sys.argv[2] if len(sys.argv) > 2 else answers.name)
    print("pushed", sha)
    wait_for_build(sha)
    data = read_page(f"https://{REPO.split('/')[0]}.github.io/{REPO.split('/')[1]}/")
    pathlib.Path("results").mkdir(exist_ok=True)
    pathlib.Path(f"results/{sha[:8]}.json").write_text(json.dumps(data, indent=2))
    sys.exit(0 if gates(data) else 1)
```

## 2.5 Behaviour and limits

- **One commit per answer set**, not per case: `git add -A` then a single commit. Five models = five
  commits and five builds. Pages tolerates roughly ten builds per hour; batch accordingly and expect
  queueing, not failure.
- Poll `pages/builds/latest` comparing `commit` to the pushed sha — a status of `built` for an older
  commit is not your build.
- Local preflight already proves B-G1/B-G2/B-G3/B-G6; a deploy adds only **L4/L5 fidelity**. Do not
  deploy until the local run is green, otherwise you are debugging Pages and the page at once.
- Public repo required unless the account has Pages on private.
- `F_liquid` is scored from the build log: present without `{% raw %}` it must fail the build; with
  raw tags it must build. That is L5 and nothing else can test it.

---

# Part 3 — the retired-provider guard CI step (patch for whoever owns the workflow)

The guard shipped as `tools/check_retired_providers.py` on
`feat/retired-provider-guard-2026-11-12` (`58baed09b6aa`). Wiring it into CI is deliberately **not**
mine: workflow files are the peer's. This is the exact insert.

```yaml
      # after actions/checkout, before any build step
      - name: Retired provider guard
        run: python3 tools/check_retired_providers.py --quiet
```

That is the whole change: exit 0 = clean, exit 1 = a retired provider is referenced, exit 2 = the
guard itself could not run (treat 2 as a failure, not a pass).

## 3.1 Prove the gate actually bites (run before trusting it)

```bash
# 1. clean tree passes
python3 tools/check_retired_providers.py --quiet ; echo "clean rc=$?"        # expect 0

# 2. synthetic violation fails
printf 'PROVIDER = "inception"\n' > tools/_guard_probe.py
python3 tools/check_retired_providers.py --quiet ; echo "dirty rc=$?"        # expect 1
rm -f tools/_guard_probe.py

# 3. KNOWN FALSE POSITIVES must still pass (they are not retired providers)
printf 'python -m mercury2\ninception/mercury-2\n' > tools/_guard_probe.py
python3 tools/check_retired_providers.py --quiet ; echo "falsepos rc=$?"     # expect 0
rm -f tools/_guard_probe.py
```

If step 2 does not exit 1, the gate is decorative and must not be merged. If step 3 does not exit 0,
the guard's context rules regressed (the local strategy `mercury2`, the OpenRouter model id, and the
`inception_paper_trading.html` deploy entries are all known-good).

## 3.2 Suggested CI test file the peer can add

`tests/test_retired_provider_guard_ci.sh` containing exactly the three blocks above, `set -e` on 1 and
3, and `!` on 2. Ten lines, no dependencies, no network.

---

# Part 4 — Inception / Mercury cleanup runbook (revoke first, scrub second)

Vendor sunset **2026-12-28**. Ordering is not stylistic: a plaintext copy exists in the private
`hermesbackup` repo, so revoking access must precede any scrub, otherwise the cleanup is cosmetic.

## 4.1 Verified state, 2026-11-13

| Fact | Value |
|---|---|
| `tools/check_retired_providers.py --quiet` | rc=0 on the current tree |
| `~/dbpasses.txt` | 478 lines, **1** Inception mention, **0** Mercury; values never printed; file untouched per owner order |
| scrub | `scrub/inception-mercury-2026-11-12` @ `2c08a4bb1433`, 37 files, awaiting merge |
| guard | `feat/retired-provider-guard-2026-11-12` @ `58baed09b6aa`, merge requested (`SYNC 11`) |
| plaintext copy | `eltonaguiar/hermesbackup` (private) |

## 4.2 C1 — consumer audit (mine, no permission needed)

```bash
grep -rn --include=*.py --include=*.sh --include=*.yml --include=*.yaml --include=*.json \
  -iE "\binception\b|\bmercury\b" . \
  --exclude-dir={.git,node_modules,.venv,__pycache__}
```
Then subtract the three known-good classes (local strategy `mercury2`, the OpenRouter model id
`inception/mercury-2`, the `inception_paper_trading.html` deploy entries). Whatever remains is the
list that will start returning 401 the day the vendor turns the key off — and that is the point of
the audit: know which consumer breaks **before** the owner revokes.

Deliverable: a table of `file:line → expected behaviour after revocation (silent skip / logged
failure / hard error)`. Anything in the "hard error" column gets a guard first.

## 4.3 C2–C6, owner and peer

| Step | Owner | Command / action | Proof |
|---|---|---|---|
| C2 revoke | owner | vendor dashboard | a known request returns 401 |
| C3 rotate OpenRouter key | owner | provider dashboard | proxy still serves; old key rejected |
| C4 scrub plaintext | me, after C2 | `gh repo clone eltonaguiar/hermesbackup /tmp/hb && grep -rn -i inception /tmp/hb --exclude-dir=.git` | grep returns 0 |
| C5 merge scrub | peer/owner | merge `scrub/inception-mercury-2026-11-12` | guard rc=0 on `main` |
| C6 CI guard | peer | the 4-line step from Part 3 | synthetic violation fails the job |

History rewriting in `hermesbackup` is **not** required and not requested: revoking the key removes
the value of the old copy. Rewriting private history is a destructive operation that needs its own
decision — it is logged as held, not as planned.

---

# Part 5 — completeness matrix (what is documented where)

| Item | Documented in | State |
|---|---|---|
| Benchmark method, results, per-case failure detail | `updates/2026-11-13-…-handoff.md` §4 | measured |
| The paid-alias correction | handoff §1.1 / design §1.1 / `SYNC 13` | measured from config |
| A1 attribution: script, targets, gates | this pack Part 1 | ready to run, not run |
| A2 JSONL callback path + restart discipline | design §3.3 | documented, needs permission |
| Fixture page, shim rule, runner, local preflight | this pack Part 2 | ready to run, not run |
| Fixture deploy gates B-G1…B-G6 | design §4.5 + this pack §2.5 | documented |
| Guard CI step + false-positive tests | this pack Part 3 | patch, peer applies |
| Inception cleanup runbook | this pack Part 4 + design §5 | mine/owner split explicit |
| Post-validation gates for every component | design §§3.4, 4.5, 5.3 | documented |
| Eight open questions | design §6 + `SYNC 13` | awaiting answers |
| Decision log (13 skips/holds) | design §7 + `SYNC 13` | decided |
| Sequencing incl. the 2026-12-28 deadline | design §8 | documented |

Nothing in Parts 1–4 has been executed. When one is executed, the rule from design §3.4 applies:
produce a **new** results file and a short record under `updates/`, never edit the old table in place.

---

# Part 6 — what still cannot be documented away

Three things are decisions, not documentation, and no amount of specification substitutes for them:

1. the fixture repo's name and visibility (a deploy is an external publish);
2. whether the shared proxy may be reconfigured for logging at all;
3. the merge decisions on the five branches.

Everything else in this pack can be executed by whoever picks it up.
