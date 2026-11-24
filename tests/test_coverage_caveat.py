"""Every audit surface must carry the coverage caveat, not just the dossier.

Numbers are frozen to the 2026-11-24 measurement in CONTEST/ROUND_01_2026-11-23/COVERAGE_BIAS.md.
If the payload moves, update the banner and this test together; a silent drift is the failure.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["audit_dashboard/audit3.html", "audit_dashboard/template.html"]
REQUIRED = ["coverage-caveat", "21.27%", "59.25%", "5,696", "BIASED", "COVERAGE_BIAS.md"]


def test_audit_pages_carry_coverage_caveat():
    for rel in PAGES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        for needle in REQUIRED:
            assert needle in text, f"{rel} missing {needle!r}"


def test_caveat_does_not_replace_verdict_text():
    for rel in PAGES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        # The caveat is additive: the page must still contain its normal shell.
        assert "<body" in text and "</html>" in text
