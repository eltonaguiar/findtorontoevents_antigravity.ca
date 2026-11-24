#!/usr/bin/env python3
"""Rebuild _MANIFEST.json from the frozen _raw snapshot. Deterministic: hashes are computed, never typed."""
import hashlib, json, os, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)          # docs/audit_review_2026-11-22
RAW = os.path.join(ROOT, "_raw")

CAPTURES = [
    # (file, url, http_status, role)
    ("audit_page.html", "https://findtorontoevents.ca/audit/", 200, "surface page /audit"),
    ("audit2_page.html", "https://findtorontoevents.ca/audit2/", 200, "surface page /audit2"),
    ("audit3_page.html", "https://findtorontoevents.ca/audit3/", 200, "surface page /audit3"),
    ("audit3_audit3_ledger.json", "https://findtorontoevents.ca/audit3/audit3_ledger.json", 200, "ledger copy served by /audit3"),
    ("audit_data_audit3_ledger.json", "https://findtorontoevents.ca/audit/data/audit3_ledger.json", 200, "ledger copy served by /audit/data"),
    ("audit2_audit2_forward.json", "https://findtorontoevents.ca/audit2/audit2_forward.json", 200, "forward observations served by /audit2"),
    ("audit_data_audit2_forward.json", "https://findtorontohttps://findtorontoevents.ca/audit/data/audit2_forward.json", 200, "forward observations served by /audit/data"),
    ("audit_data_dashboard_data.json", "https://findtorontoevents.ca/audit/data/dashboard_data.json", 200, "dashboard payload served by /audit/data"),
]
# fix the typo'd url above deterministically
CAPTURES[6] = ("audit_data_audit2_forward.json", "https://findtorontoevents.ca/audit/data/audit2_forward.json", 200, "forward observations served by /audit/data")

NOT_FOUND = [
    ("https://findtorontoevents.ca/audit/audit3.html", 404, "expected audit3 page under /audit/ does not exist"),
    ("https://findtorontoevents.ca/audit_dashboard/data/money_ready_verdict.json", 404, "money_ready_verdict.json is NOT served on the web; only exists in repo"),
]

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def meta(p):
    d = json.load(open(p))
    out = {}
    if isinstance(d, dict):
        for k in ("generated_at", "source_generated_at", "source", "schema"):
            if k in d:
                out[k] = d[k]
        prov = d.get("provenance")
        if isinstance(prov, dict):
            out["provenance"] = {k: prov.get(k) for k in ("module", "generator_version", "id", "population", "population_rows", "input_sha256", "git_sha") if k in prov}
    return out

entries = []
for f, url, status, role in CAPTURES:
    p = os.path.join(RAW, f)
    e = {"path": os.path.relpath(p, os.path.join(ROOT, "..", "..")), "url": url, "http_status": status, "role": role,
         "bytes": os.path.getsize(p), "sha256": sha(p)}
    if f.endswith(".json"):
        e.update(meta(p))
    entries.append(e)

# local repo copies: frozen at same instant for comparison
LOCAL = [
    ("audit_dashboard/data/money_ready_verdict.json", "money-ready verdict producer output (repo copy)"),
    ("audit_dashboard/data/dashboard_data.json", "dashboard payload (repo copy, different snapshot than live)"),
]
repo = os.path.abspath(os.path.join(ROOT, "..", ".."))
for rel, role in LOCAL:
    p = os.path.join(repo, rel)
    e = {"path": rel, "url": None, "http_status": None, "role": role, "bytes": os.path.getsize(p), "sha256": sha(p)}
    e.update(meta(p))
    entries.append(e)

nf = [{"url": u, "http_status": s, "note": n} for u, s, n in NOT_FOUND]

manifest = {
    "manifest_version": 1,
    "program": "2026-11-22 audit review + GHA QA",
    "frozen_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "captured_by": "Phase 0 Measurer (curl + sha256, no inference)",
    "raw_dir": os.path.relpath(RAW, repo),
    "entries": entries,
    "not_found": nf,
    "consistency_checks": [],
}

# measured cross-checks, computed not claimed
led = [e for e in entries if e["path"].endswith("audit3_ledger.json")]
if len(led) == 2:
    manifest["consistency_checks"].append({
        "check": "audit3 ledger copies byte-identical",
        "a": led[0]["path"], "b": led[1]["path"],
        "a_sha256": led[0]["sha256"], "b_sha256": led[1]["sha256"],
        "result": "MATCH" if led[0]["sha256"] == led[1]["sha256"] else "MISMATCH"})
fwd = [e for e in entries if e["path"].endswith("audit2_forward.json")]
if len(fwd) == 2:
    manifest["consistency_checks"].append({
        "check": "audit2_forward copies identical",
        "a": fwd[0]["path"], "b": fwd[1]["path"],
        "a_generated_at": fwd[0].get("generated_at"), "b_generated_at": fwd[1].get("generated_at"),
        "result": "MATCH" if fwd[0]["sha256"] == fwd[1]["sha256"] else "MISMATCH (stale sidecar)"})
dd = [e for e in entries if e["path"].endswith("dashboard_data.json")]
if dd and led:
    input_sha = (led[0].get("provenance") or {}).get("input_sha256")
    live = [e for e in dd if e["url"]]
    if live:
        manifest["consistency_checks"].append({
            "check": "audit3 ledger input_sha256 == live /audit/data/dashboard_data.json sha256",
            "input_sha256": input_sha, "live_sha256": live[0]["sha256"],
            "result": "MATCH" if input_sha == live[0]["sha256"] else "MISMATCH"})

out = os.path.join(ROOT, "_MANIFEST.json")
json.dump(manifest, open(out, "w"), indent=1, sort_keys=False)
print("wrote", out)
for c in manifest["consistency_checks"]:
    print(c["check"], "->", c["result"])
