#!/usr/bin/env python3
"""SubQ Decisions API client for the profitability framework.

Runs a fixed question set twice - once bare, once with measured evidence in the
`state` - so the probability delta shows whether the model is reasoning from the
data or from priors. That delta is the fact-check.

Auth: reads SUBQ_API_KEY from the environment, else the token labelled under
"SUBQ" in ~/dbpasses.txt. The key is never printed, logged, or written into the
repo.

Usage:
    python3 tools/subq_consult.py --questions <file.json> --out <dir>
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import sys

import requests

BASE_URL = "https://api.subq.ai/v1/systemone"
DEFAULT_MODEL = "subq-snap-1.2"
DBCREDS = pathlib.Path("/home/eaguiar2015/dbpasses.txt")


def resolve_key() -> str | None:
    """Env first, then the SUBQ-labelled block in dbpasses.txt."""
    env = os.environ.get("SUBQ_API_KEY", "").strip()
    if env:
        return env
    if not DBCREDS.exists():
        return None
    lines = DBCREDS.read_text(errors="ignore").splitlines()
    for i, line in enumerate(lines):
        if re.search(r"\bsubq\b", line, re.I) and not line.strip().startswith("#"):
            # token sits on the following non-empty line
            for nxt in lines[i + 1 : i + 4]:
                tok = nxt.strip()
                if tok.startswith("sk-"):
                    return tok
    return None


def ask(key: str, model: str, state: str, questions: dict) -> dict:
    payload = {"model": model, "state": state, "questions": questions}
    body = json.dumps(payload, sort_keys=True).encode()
    resp = requests.post(
        BASE_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=180,
    )
    record = {
        "requested_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "endpoint": BASE_URL,
        "model": model,
        "request_sha256": hashlib.sha256(body).hexdigest(),
        "state_chars": len(state),
        "n_questions": len(questions),
        "http_status": resp.status_code,
    }
    try:
        record["response"] = resp.json()
    except ValueError:
        record["response_text"] = resp.text[:2000]
    return record


def summarise(record: dict) -> list[str]:
    """Flatten answers into readable rows without assuming a shape."""
    out = []
    answers = (record.get("response") or {}).get("answers") or {}
    for name, ans in answers.items():
        if not isinstance(ans, dict):
            out.append(f"  {name:<24} {ans}")
            continue
        kind = ans.get("type")
        if kind == "noul":
            out.append(f"  {name:<24} P(yes)={ans.get('noul')}")
        elif kind == "choice":
            probs = ans.get("probabilities") or {}
            top = sorted(probs.items(), key=lambda kv: -kv[1])[:3]
            pretty = ", ".join(f"{k}={v:.3f}" for k, v in top)
            out.append(f"  {name:<24} {ans.get('choice')}  [{pretty}]  conf={ans.get('confidence')}")
        elif kind == "score":
            out.append(f"  {name:<24} score={ans.get('score')}  conf={ans.get('confidence')}")
        else:
            out.append(f"  {name:<24} {json.dumps(ans)[:120]}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True, help="JSON with bare/evidence state + questions")
    ap.add_argument("--out", required=True, help="directory for raw run artefacts")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    args = ap.parse_args()

    key = resolve_key()
    if not key:
        print("[error] no SubQ key: set SUBQ_API_KEY or add a SUBQ block to dbpasses.txt")
        return 2

    cfg = json.loads(pathlib.Path(args.questions).read_text())
    questions = cfg["questions"]
    runs = {}

    for arm in ("bare", "evidence"):
        state = cfg[arm]["state"]
        label = cfg[arm]["label"]
        print(f"\n=== {arm.upper()} — {label} ===")
        rec = ask(key, args.model, state, questions)
        print(f"  HTTP {rec['http_status']}  state_chars={rec['state_chars']}  sha={rec['request_sha256'][:12]}")
        if rec["http_status"] != 200:
            print("  body:", json.dumps(rec.get("response") or rec.get("response_text"))[:400])
            runs[arm] = rec
            continue
        usage = (rec.get("response") or {}).get("usage") or {}
        print(f"  usage: {usage}")
        for row in summarise(rec):
            print(row)
        runs[arm] = rec

    outdir = pathlib.Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = outdir / f"subq_run_{stamp}.json"
    path.write_text(json.dumps({"config": cfg, "runs": runs}, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {path}")
    ok = sum(1 for r in runs.values() if r.get("http_status") == 200)
    print(f"arms_ok={ok}/{len(runs)}")
    return 0 if ok == len(runs) else 1


if __name__ == "__main__":
    sys.exit(main())
