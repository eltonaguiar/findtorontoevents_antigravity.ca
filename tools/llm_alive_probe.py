#!/usr/bin/env python3
"""
llm_alive_probe.py — probe every LiteLLM deployment and report which models are
actually ALIVE, then optionally rank them into routing weights.

Why this exists
---------------
`litellm_config.yaml` lists ~127 deployments across ~15 providers (free and paid).
Providers retire models, keys expire, quotas drain, and there is no single
"is it alive?" view. This probes each deployment **directly at the provider**
(bypassing the proxy, so `simple-shuffle` noise can't hide a dead model) and
writes a status report.

Usage
-----
  python3 tools/llm_alive_probe.py                    # probe all, print table
  python3 tools/llm_alive_probe.py --group free-mode  # one model_name group only
  python3 tools/llm_alive_probe.py --free-only        # free-*/hybrid-* groups only
  python3 tools/llm_alive_probe.py --failures         # print only non-alive rows
  python3 tools/llm_alive_probe.py --apply            # rank alive models via weights
  python3 tools/llm_alive_probe.py --status           # show last report, no probing
  python3 tools/llm_alive_probe.py --json             # machine-readable stdout

Output
------
  reports/llm_alive_status.json   status report consumed by --status / --apply

Prioritisation ("alive first")
------------------------------
`--apply` injects `weight: N` into every deployment's `litellm_params`:
  alive (fast -> slow)   100 / 70 / 40 / 20
  throttled (429)         10
  error (5xx/timeout)      3
  dead (retired/bad key)   0

NOTE on a `simple-shuffle` quirk: LiteLLM reads the weight *key name* from
`healthy_deployments[0]` and then collects that key from EVERY deployment in the
group, defaulting missing ones to 0. So `weight` must be applied to ALL
deployments or none -- a partial apply would silently zero out the rest.
That is why `--apply` always writes a weight for every entry.
"""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    import litellm  # type: ignore
    litellm.suppress_debug_info = True
    litellm.set_verbose = False
except Exception as exc:  # pragma: no cover
    print(f"FATAL: litellm not importable: {exc}", file=sys.stderr)
    raise SystemExit(2)

try:
    from tools.litellm_smart_cooldown import _classify as _classify  # type: ignore
except Exception:  # pragma: no cover
    def _classify(exc, api_base):  # type: ignore
        return ("other", 0)

CONFIG = REPO_ROOT / "litellm_config.yaml"
LAUNCHER = REPO_ROOT / "tools" / "start_litellm_proxy.sh"
REPORT = REPO_ROOT / "reports" / "llm_alive_status.json"

DEP_LINE_RE = re.compile(r'^\s*-\s*\{model_name:')
WEIGHT_IN_LP_RE = re.compile(r'(?<=[{,]\s)weight:\s*\d+\s*,\s*')

DEAD_CATEGORIES = {"dead_model", "dead_key", "quota", "daily_quota_cf", "monthly_quota_hf"}


# ---------------------------------------------------------------------------
# keys — reuse the launcher's label -> value parsing so we stay in sync
# ---------------------------------------------------------------------------
def _label_env_pairs() -> List[tuple]:
    try:
        return re.findall(r'parse_key\s+"([^"]+)"\s+([A-Z0-9_]+)', LAUNCHER.read_text())
    except Exception:
        return []


def load_keys() -> Dict[str, str]:
    keys_file = Path(os.environ.get("KEYS_FILE", str(Path.home() / "dbpasses.txt")))
    out: Dict[str, str] = {}
    if not keys_file.exists():
        return out
    lines = [x.strip() for x in keys_file.read_text(errors="ignore").splitlines()]
    for label, env in _label_env_pairs():
        try:
            i = lines.index(label)
        except ValueError:
            continue
        for ln in lines[i + 1:]:
            if not ln or re.fullmatch(r'[A-Z][A-Z0-9_]*', ln) or ln.endswith(":") \
               or ln.startswith("http") or re.match(r'^={2,}', ln):
                continue
            out[env] = ln
            break
    return out


def resolve_key(raw: Optional[str], keys: Dict[str, str]) -> Optional[str]:
    if not raw:
        return None
    if raw.startswith("os.environ/"):
        name = raw.split("/", 1)[1]
        return os.environ.get(name) or keys.get(name)
    return raw


# ---------------------------------------------------------------------------
# deployments (with line numbers, so --apply can edit surgically)
# ---------------------------------------------------------------------------
def load_deployments() -> List[Dict[str, Any]]:
    import yaml
    text = CONFIG.read_text()
    lines = text.splitlines()
    line_nos = [i for i, l in enumerate(lines) if DEP_LINE_RE.match(l)]
    model_list = yaml.safe_load(text).get("model_list", [])
    if len(line_nos) != len(model_list):
        raise SystemExit(
            f"config shape changed: {len(line_nos)} single-line entries vs "
            f"{len(model_list)} parsed deployments — refusing to guess"
        )
    deps = []
    for ln_no, dep in zip(line_nos, model_list):
        lp = dep.get("litellm_params") or {}
        deps.append({
            "line": ln_no,
            "group": dep.get("model_name"),
            "model": lp.get("model"),
            "api_base": lp.get("api_base"),
            "raw_key": lp.get("api_key"),
        })
    return deps


# ---------------------------------------------------------------------------
# probe
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Priority tiers
# ---------------------------------------------------------------------------
# Anything that has an ISSUE is pushed an order of magnitude (or more) below a
# validated-alive model, so the router strongly prefers models we have actually
# proven work -- while keeping broken ones reachable as a last resort.
#
#   P1 validated-alive   1000 / 500 / 200 / 100   (by latency)
#   P2 throttled            10   works, but quota-limited (429)
#   P3 error                 1   5xx / timeout, may be transient
#   P4 dead / no_key         0   retired model, dead key, no credential
TIER_WEIGHTS = {
    "alive": (1000, 500, 200, 100),
    "throttled": (10,),
    "error": (1,),
    "dead": (0,),
}
TIER_NAMES = {
    "alive": "P1-alive",
    "throttled": "P2-throttled",
    "error": "P3-error",
    "dead": "P4-dead",
}


def weight_for(status: str, latency_ms: int) -> int:
    if status == "alive":
        fast, mid, slow, crawl = TIER_WEIGHTS["alive"]
        if latency_ms <= 1500:
            return fast
        if latency_ms <= 4000:
            return mid
        if latency_ms <= 10000:
            return slow
        return crawl
    return TIER_WEIGHTS.get(status, (0,))[0]


def probe(dep: Dict[str, Any], keys: Dict[str, str], timeout: int) -> Dict[str, Any]:
    row = {k: dep[k] for k in ("group", "model", "api_base")}
    key = resolve_key(dep.get("raw_key"), keys)
    provider = str(dep.get("model") or "").split("/")[0]
    if not key:
        # Local servers (Ollama / vLLM) need no credential; anything else does.
        if provider in ("ollama", "ollama_chat", "hosted_vllm", "vllm"):
            key = "not-needed"
        else:
            row.update(status="dead", category="no_key", latency_ms=0,
                       detail=f"missing key: {dep.get('raw_key')}")
            return row

    t0 = time.time()
    try:
        resp = litellm.completion(
            model=dep["model"],
            api_key=key,
            api_base=dep.get("api_base"),
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=16,
            temperature=0,
            timeout=timeout,
            drop_params=True,
        )
        ms = int((time.time() - t0) * 1000)
        txt = ""
        try:
            txt = (resp.choices[0].message.content or "").strip()[:40]
        except Exception:
            pass
        row.update(status="alive", category="alive", latency_ms=ms,
                   detail=txt or "(empty but no error)")
    except Exception as exc:
        ms = int((time.time() - t0) * 1000)
        name = type(exc).__name__.lower()
        blob = f"{name} {exc}".lower()
        if "timeout" in name or "timed out" in blob:
            category = "timeout"
        else:
            category, _ = _classify(exc, dep.get("api_base"))
        if category == "rate_limit":
            status = "throttled"
        elif category in DEAD_CATEGORIES:
            status = "dead"
        else:
            status = "error"
        row.update(status=status, category=category, latency_ms=ms,
                   detail=str(exc)[:200].replace("\n", " "))
    return row


def run_probe_ordered(deps: List[Dict[str, Any]], keys: Dict[str, str],
                      timeout: int, concurrency: int) -> List[Dict[str, Any]]:
    """Probe concurrently, but keep results in config order (stable output)."""
    results: List[Optional[Dict[str, Any]]] = [None] * len(deps)
    with futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        fut_map = {pool.submit(probe, d, keys, timeout): i for i, d in enumerate(deps)}
        for fut in futures.as_completed(fut_map):
            results[fut_map[fut]] = fut.result()
    return [r for r in results if r is not None]


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
def save_report(rows: List[Dict[str, Any]], meta: Dict[str, Any]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({"meta": meta, "rows": rows}, indent=2, default=str))


def load_report() -> Optional[Dict[str, Any]]:
    try:
        return json.loads(REPORT.read_text())
    except Exception:
        return None


ICON = {"alive": "OK  ", "throttled": "THR ", "error": "ERR ", "dead": "DEAD"}


def print_table(rows: List[Dict[str, Any]], failures_only: bool = False) -> None:
    if failures_only:
        rows = [r for r in rows if r["status"] != "alive"]
    print(f"{'grp':<22} {'tier':<13} {'wt':>5} {'ms':>6}  {'category':<14} model")
    print("-" * 118)
    for r in rows:
        print(f"{str(r['group'])[:22]:<22} {TIER_NAMES.get(r['status'], r['status']):<13} "
              f"{weight_for(r['status'], r['latency_ms']):>5} {r['latency_ms']:>6}  "
              f"{str(r['category'])[:14]:<14} {r['model']}")


def summarize(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    summary: Dict[str, int] = {}
    for r in rows:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    return summary


def print_group_summary(rows: List[Dict[str, Any]]) -> None:
    by: Dict[str, Dict[str, int]] = {}
    for r in rows:
        g = by.setdefault(str(r["group"]), {})
        g[r["status"]] = g.get(r["status"], 0) + 1
    print(f"\n{'group':<24} {'alive':>5} {'thr':>4} {'err':>4} {'dead':>5}  {'total':>5}")
    print("-" * 54)
    for g in sorted(by):
        v = by[g]
        print(f"{g[:24]:<24} {v.get('alive', 0):>5} {v.get('throttled', 0):>4} "
              f"{v.get('error', 0):>4} {v.get('dead', 0):>5}  {sum(v.values()):>5}")


# ---------------------------------------------------------------------------
# --apply : write weights into the config (all entries, comment-preserving)
# ---------------------------------------------------------------------------
def apply_weights(rows: List[Dict[str, Any]], deps: List[Dict[str, Any]]) -> int:
    key_to_weight = {}
    for r in rows:
        w = weight_for(r["status"], r["latency_ms"])
        key_to_weight[(r["group"], r["model"], r.get("api_base"))] = w

    lines = CONFIG.read_text().splitlines(keepends=True)
    changed = 0
    for dep in deps:
        w = key_to_weight.get((dep["group"], dep["model"], dep.get("api_base")))
        if w is None:
            continue
        ln = dep["line"]
        line = lines[ln]
        lp_at = line.find("litellm_params: {")
        if lp_at == -1:
            continue
        head, tail = line[:lp_at], line[lp_at:]
        if "weight:" in tail:
            new_tail = re.sub(r'weight:\s*\d+\s*,?', f'weight: {w},', tail, count=1)
        else:
            brace = tail.index("{") + 1
            new_tail = tail[:brace] + f" weight: {w}, " + tail[brace:].lstrip()
        new_line = head + new_tail
        if new_line != line:
            lines[ln] = new_line
            changed += 1

    CONFIG.write_text("".join(lines))
    return changed


# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--group", help="only this model_name group")
    ap.add_argument("--free-only", action="store_true",
                    help="only free-* / hybrid-* groups")
    ap.add_argument("--failures", action="store_true", help="print only non-alive rows")
    ap.add_argument("--apply", action="store_true", help="write weights into the config")
    ap.add_argument("--status", action="store_true", help="show last report, no probing")
    ap.add_argument("--recheck", action="store_true",
                    help="re-probe ONLY the deployments that were not alive last time "
                         "(filters transient/concurrency noise)")
    ap.add_argument("--json", action="store_true", help="machine-readable stdout")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--concurrency", type=int, default=8)
    args = ap.parse_args(argv)

    if args.status:
        rep = load_report()
        if not rep:
            print(f"no report yet at {REPORT} — run without --status first")
            return 1
        rows = rep["rows"]
        meta = rep.get("meta") or {}
        print(f"report from {meta.get('probed_at_utc')} "
              f"({meta.get('total')} deployments, {meta.get('elapsed_s')}s)")
        print_table(rows, args.failures)
        print_group_summary(rows)
        s = summarize(rows)
        print("\nsummary:", ", ".join(f"{k}={v}" for k, v in sorted(s.items())))
        if args.apply:
            n = apply_weights(rows, load_deployments())
            print(f"\napplied weights to {n} deployment line(s) in "
                  f"{CONFIG.relative_to(REPO_ROOT)}")
            print("NOTE: restart the proxy to pick up new weights "
                  "(bash tools/start_ai_servers.sh restart)")
        return 0

    deps = load_deployments()
    if args.group:
        deps = [d for d in deps if d["group"] == args.group]
    elif args.free_only:
        deps = [d for d in deps if str(d["group"]).startswith(("free-", "hybrid-"))]
    elif args.recheck:
        prev = load_report()
        if not prev:
            print("no previous report to recheck — run a full probe first")
            return 1
        bad = {(r["group"], r["model"], r.get("api_base"))
               for r in prev["rows"] if r["status"] != "alive"}
        deps = [d for d in deps if (d["group"], d["model"], d.get("api_base")) in bad]
        print(f"rechecking {len(deps)} previously non-alive deployment(s)", file=sys.stderr)
    if not deps:
        print("no deployments matched")
        return 1

    keys = load_keys()
    print(f"probing {len(deps)} deployment(s), concurrency={args.concurrency}, "
          f"timeout={args.timeout}s ...", file=sys.stderr)
    t0 = time.time()
    rows = run_probe_ordered(deps, keys, args.timeout, args.concurrency)
    elapsed = round(time.time() - t0, 1)

    if args.recheck:
        # Merge the rechecked rows back into the previous full report, preserving order.
        prev_rows = (load_report() or {}).get("rows", [])
        upd = {(r["group"], r["model"], r.get("api_base")): r for r in rows}
        rows = [upd.get((r["group"], r["model"], r.get("api_base")), r) for r in prev_rows]

    meta = {
        "probed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total": len(rows),
        "elapsed_s": elapsed,
        "summary": summarize(rows),
        "timeout_s": args.timeout,
        "mode": "recheck" if args.recheck else "full",
    }
    save_report(rows, meta)

    if args.json:
        print(json.dumps({"meta": meta, "rows": rows}, indent=2))
    else:
        print_table(rows, args.failures)
        print_group_summary(rows)
        print("\nsummary:", ", ".join(f"{k}={v}" for k, v in sorted(meta["summary"].items())))
        print(f"elapsed {elapsed}s -> {REPORT.relative_to(REPO_ROOT)}")

    if args.apply:
        n = apply_weights(rows, deps)
        print(f"\napplied weights to {n}/{len(deps)} deployment line(s) in "
              f"{CONFIG.relative_to(REPO_ROOT)}")
        print("NOTE: restart the proxy to pick up new weights "
              "(bash tools/start_ai_servers.sh restart)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
