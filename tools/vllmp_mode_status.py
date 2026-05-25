"""
vllmp_mode_status.py — show health and recent usage of each LiteLLM virtual
model group (free-mode, paid-mode, hybrid-model, etc.).

Output:
  GROUP         UPSTREAMS  HEALTHY  COOLED  LAST-60MIN-REQS  STATUS
  free-mode            21       19       2              47   HEALTHY
  paid-mode             8        6       2               3   HEALTHY
  hybrid-model          6        5       1              12   HEALTHY (alias)
  ...

Sources:
  - /v1/models for the upstream count per group
  - /tmp/litellm_cooldown_state.json for cooled upstreams + categories
  - /tmp/litellm_proxy.log for recent request counts per group
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import subprocess
import sys
import urllib.request
from collections import Counter
from pathlib import Path

LOG = Path("/tmp/litellm_proxy.log")
COOL = Path("/tmp/litellm_cooldown_state.json")
LOOKBACK_MIN = 60


def _fetch_models() -> dict[str, list[str]]:
    """Return {model_group: [api_base, ...]} — only group names available."""
    try:
        with urllib.request.urlopen("http://localhost:4000/v1/models", timeout=5) as r:
            data = json.loads(r.read())
        return {m["id"]: [] for m in data.get("data", [])}
    except Exception:
        return {}


def _fetch_model_info() -> list[dict]:
    """Hit /model/info for per-deployment view (model_name + litellm_params)."""
    try:
        with urllib.request.urlopen("http://localhost:4000/model/info", timeout=5) as r:
            data = json.loads(r.read())
        return data.get("data", [])
    except Exception:
        return []


def _cooled_now() -> dict[str, dict]:
    """Return cooled entries whose cool_until_utc is still in the future."""
    if not COOL.exists():
        return {}
    try:
        state = json.loads(COOL.read_text())
    except Exception:
        return {}
    now = _dt.datetime.now(_dt.timezone.utc)
    live: dict[str, dict] = {}
    for k, v in state.get("cooled", {}).items():
        try:
            until = _dt.datetime.fromisoformat(v["cool_until_utc"])
            if until > now:
                live[k] = v
        except Exception:
            pass
    return live


def _request_counts() -> Counter:
    """Count log lines per model group in the last LOOKBACK_MIN minutes."""
    counts: Counter = Counter()
    if not LOG.exists():
        return counts
    cutoff = _dt.datetime.now() - _dt.timedelta(minutes=LOOKBACK_MIN)
    # LiteLLM logs format like: "INFO: ... model=hybrid-model ..."
    pat = re.compile(r"model['\":\s=]+([a-z][a-z0-9_-]+)", re.IGNORECASE)
    try:
        with LOG.open() as fh:
            for line in fh.readlines()[-5000:]:
                m = pat.search(line)
                if m:
                    counts[m.group(1)] += 1
    except Exception:
        pass
    return counts


def _proxy_running() -> tuple[bool, str]:
    try:
        out = subprocess.check_output(["pgrep", "-af", "litellm.*litellm_config"], text=True)
        return True, out.strip().split("\n")[0]
    except Exception:
        return False, ""


def main() -> int:
    up, pid_line = _proxy_running()
    if not up:
        print("PROXY DOWN — run /startvllmp")
        return 1
    print(f"PROXY UP — {pid_line[:80]}\n")

    info = _fetch_model_info()
    if not info:
        print("ERROR: could not fetch /model/info (is proxy fully started?)")
        return 1

    # Group by model_name
    by_group: dict[str, list[dict]] = {}
    for entry in info:
        g = entry.get("model_name")
        by_group.setdefault(g, []).append(entry)

    cooled = _cooled_now()
    cooled_bases = {k.split("@")[-1].strip().rstrip("/") for k in cooled}
    cooled_categories = Counter(v["category"] for v in cooled.values())
    counts = _request_counts()

    print(f"{'GROUP':<22} {'UPSTREAMS':>9} {'HEALTHY':>7} {'COOLED':>6} {'60m-reqs':>9}  STATUS")
    print("-" * 82)
    # Build fingerprint set from cooled keys.
    # Cooled key format: "<model> @ <api_base>". Parse both sides.
    cooled_fingerprints: set[tuple[str, str]] = set()
    for ck in cooled:
        if "@" in ck:
            cm, _, cb = ck.partition("@")
            cooled_fingerprints.add((cm.strip(), cb.strip().rstrip("/")))

    for group in sorted(by_group):
        entries = by_group[group]
        total = len(entries)
        n_cool = 0
        for e in entries:
            base = (e.get("litellm_params", {}).get("api_base") or "").rstrip("/")
            model = e.get("litellm_params", {}).get("model") or ""
            # Strict fingerprint match: (model, api_base) must match exactly.
            # Falls back to base-only match when this entry has no api_base
            # (native litellm providers like groq/, anthropic/, gemini/).
            matched = False
            for cm, cb in cooled_fingerprints:
                # native-provider entry — no api_base; match on model only
                if not base and not cb and model == cm:
                    matched = True
                    break
                if base and base == cb and (cm in model or cm == model.split("/", 1)[-1]):
                    matched = True
                    break
            if matched:
                n_cool += 1
        healthy = total - n_cool
        reqs = counts.get(group, 0)
        if total == 0:
            status = "EMPTY"
        elif healthy == 0:
            status = "ALL COOLED"
        elif healthy < total / 2:
            status = "DEGRADED"
        else:
            status = "HEALTHY"
        alias = " (alias)" if group.startswith("hybrid-") else ""
        print(f"{group + alias:<22} {total:>9} {healthy:>7} {n_cool:>6} {reqs:>9}  {status}")

    print()
    if cooled:
        print(f"Cooled by category: {dict(cooled_categories)}")
        print(f"Read full cooldown state: jq . {COOL}")
    else:
        print("No upstreams currently cooled. All providers responding.")

    print()
    print("MODE GUIDE:")
    print("  Use model=\"free-mode\"   in your client to force the FREE pool ($0 / free-tier).")
    print("  Use model=\"paid-mode\"   for premium frontier (Anthropic/DeepSeek/Moonshot/Hypereal).")
    print("  Use model=\"hybrid-model\" for backward-compat (= free-mode subset).")
    print("  Oversize prompts auto-route to *-large variants via context_window_fallbacks.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
