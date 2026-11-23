#!/usr/bin/env python3
"""I10/O2: schema-drift gate for reports/fund_deep_dive.json.

The report once quoted figures the tool did not produce, and the payload grew
fields while the document kept quoting the old ones. This pins the CONTRACT.

Run by .github/workflows/fund-deep-dive.yml, but also runnable by hand:

    python3 tools/fund_deep_dive.py --out /tmp/fresh.json
    python3 tools/check_fund_schema.py /tmp/fresh.json reports/fund_deep_dive.json

Exit codes: 0 ok, 1 drift detected.
"""
import json
import sys

EXPECTED_SCHEMA = 2

TOP_KEYS = {
    "schema_version", "generated_at", "source", "period", "n_days",
    "corrections", "rebalancing", "funds", "paired_diffs", "subperiods",
    "portfolios", "rebalance_sensitivity", "forward_anchors",
}
FUND_KEYS = {
    "cagr_pct", "net_cagr_pct", "vol_pct", "max_dd_pct", "n", "ret_vol",
    "sharpe", "sortino", "sortino_legacy", "rf_pct", "bootstrap",
}
PAIRED_KEYS = {
    "point_pct", "ci_pct", "distinguishable_from_zero", "fee_advantage_pct",
    "net_point_pct", "net_ci_pct",
}


def check(payload, problems):
    if payload.get("schema_version") != EXPECTED_SCHEMA:
        problems.append(
            f"schema_version {payload.get('schema_version')!r} != {EXPECTED_SCHEMA}; "
            "bump the gate deliberately and update gen_corrected_table.py"
        )

    missing = TOP_KEYS - set(payload)
    if missing:
        problems.append(f"missing top-level keys: {sorted(missing)}")

    for name, m in payload.get("funds", {}).items():
        miss = FUND_KEYS - set(m)
        if miss:
            problems.append(f"funds[{name}] missing {sorted(miss)}")

    for name, m in payload.get("paired_diffs", {}).items():
        miss = PAIRED_KEYS - set(m)
        if miss:
            problems.append(f"paired_diffs[{name}] missing {sorted(miss)}")

    # gross/net must never collapse: confusing the two is exactly what produced
    # a false "non-deterministic CAGRs" report.
    for name, m in payload.get("funds", {}).items():
        if "net_cagr_pct" in m and "cagr_pct" in m:
            if m["net_cagr_pct"] > m["cagr_pct"] + 1e-9:
                problems.append(
                    f"funds[{name}] net CAGR exceeds gross - fee applied backwards?"
                )

    # a zero-fee fund must be unchanged by the fee step
    fz = payload.get("funds", {}).get("FZROX_adj")
    if fz and abs(fz["cagr_pct"] - fz["net_cagr_pct"]) > 5e-3:
        problems.append("FZROX_adj has a 0.00% MER but gross != net")

    return problems


def load(path):
    with open(path) as fh:
        return json.load(fh)


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    fresh_path, tracked_path = argv[1], argv[2]

    problems = []
    fresh = load(fresh_path)
    check(fresh, problems)

    # reproducibility: compare against a second generation if provided
    tracked = load(tracked_path)
    fresh_cmp = dict(fresh)
    tracked_cmp = dict(tracked)
    fresh_cmp.pop("generated_at", None)
    tracked_cmp.pop("generated_at", None)
    content_matches = fresh_cmp == tracked_cmp
    if not content_matches:
        problems.append(
            f"{tracked_path} is STALE vs the generator "
            "(regenerate with: python3 tools/fund_deep_dive.py)"
        )

    if problems:
        print("SCHEMA DRIFT DETECTED")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("schema OK")
    print(f"tracked artifact is current ({tracked_path})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
