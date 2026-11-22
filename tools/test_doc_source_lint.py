#!/usr/bin/env python3
"""Unit tests for tools/doc_source_lint.py. Run: python3 tools/test_doc_source_lint.py"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from doc_source_lint import bare_numbers, lint_text, HEADINGS  # noqa: E402

GOOD = """# 01 CRYPTO

## 1 Identity
Class CRYPTO: symbols like BTC, ETH.
## 2 What the class is
Momentum and mean-reversion are the structural candidates.
## 3 Measured state
- PF net 0.7886 at n 6,926 [SRC: manifest:classes.CRYPTO.pf]
- net expectancy -0.4183 pct, CI [-0.699, -0.1602] [SRC: manifest:classes.CRYPTO.net_ci_pct]
- 2x stress: UNMEASURED
## 4 Contradictions
/audit says PF 0.2621 [SRC: _raw/audit_data_money_ready_verdict.json:1] while /audit3 says 0.7886 [SRC: _raw/audit3_audit3_ledger.json:1].
## 5 Data integrity
Coverage 59.19 pct of closed picks [SRC: manifest:coverage].
## 6 Cost reality
Flat constant 0.0996 pct used [SRC: _raw/audit3_audit3_ledger.json:1].
## 7 What would change the verdict
One experiment: 900 forward rows, gate PF CI-LB above one [SRC: forward_gate.rule].
## 8 Blunt answer
NOT PROVEN.
## Provenance
- model: none (measured by hand)
- prompt: none
- snapshot: ledger 2026-11-22T06:35:41Z

Least survivable number: the CRYPTO class PF [SRC: manifest:classes.CRYPTO.pf], because the
class bucket mixes symbol cells with different cost models.
"""

BAD_BARE = GOOD.replace(
    "- PF net 0.7886 at n 6,926 [SRC: manifest:classes.CRYPTO.pf]",
    "- PF net 0.7886 at n 6,926",
).replace(
    "Least survivable number: PF 0.7886 at n 6,926, because the class bucket mixes 68 symbol cells.",
    "Least survivable number: PF 0.7886, because the class bucket mixes 68 symbol cells.",
)

BAD_NO_HEADING = GOOD.replace("## 5 Data integrity\nCoverage 59.19 pct of closed picks [SRC: manifest:coverage].\n", "")

BAD_NO_PROVENANCE = GOOD.split("## Provenance")[0] + "## Provenance\n- model: x\n"

BAD_NO_LEAST = GOOD.split("Least survivable number")[0]


class TestBareNumbers(unittest.TestCase):
    def test_good_has_no_bare_numbers(self):
        self.assertEqual(bare_numbers(GOOD.splitlines()), [])

    def test_unmarked_number_is_flagged(self):
        got = bare_numbers(BAD_BARE.splitlines())
        self.assertTrue(got, "expected a bare number")
        self.assertIn("0.7886", [t for _, t in got])

    def test_unmeasured_token_satisfies(self):
        lines = ["- 2x stress: UNMEASURED"]
        self.assertEqual(bare_numbers(lines), [])

    def test_marker_on_previous_line_covers_table_row(self):
        lines = ["[SRC: manifest:x]", "| 0.79 | 6926 |"]
        self.assertEqual(bare_numbers(lines), [])

    def test_code_span_and_dates_are_not_claims(self):
        lines = ["see `audit3.v1` and 2026-11-22T06:35:41Z"]
        self.assertEqual(bare_numbers(lines), [])

    def test_heading_ordinal_is_not_a_claim(self):
        self.assertEqual(bare_numbers(["## 3 Measured state"]), [])

    def test_hex_sha_is_not_a_claim(self):
        self.assertEqual(bare_numbers(["88606e1ec2e9a0bab4e4d59a8830f24e880a3de4"]), [])


class TestShape(unittest.TestCase):
    def test_good_passes(self):
        self.assertEqual(lint_text(GOOD, "good.md"), [])

    def test_missing_heading_fails(self):
        errs = lint_text(BAD_NO_HEADING, "x.md")
        self.assertTrue(any("## 5 Data integrity" in e for e in errs))

    def test_missing_provenance_fails(self):
        errs = lint_text(BAD_NO_PROVENANCE, "x.md")
        self.assertTrue(any("Provenance" in e for e in errs))

    def test_missing_least_survivable_fails(self):
        errs = lint_text(BAD_NO_LEAST, "x.md")
        self.assertTrue(any("least survivable" in e.lower() for e in errs))

    def test_all_headings_defined(self):
        self.assertEqual(len(HEADINGS), 9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
