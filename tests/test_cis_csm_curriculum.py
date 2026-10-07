import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


GUIDE = Path(__file__).resolve().parents[1] / "findtorontoevents.ca/CIS-CSM/index.html"
DOMAINS = {
    "domain-1": (27, ("business-models", "product-models", "install-base", "contracts-entitlements")),
    "domain-2": (38, ("csm-in-servicenow", "routing", "case-types", "channels")),
    "domain-3": (17, ("state-flows", "major-issue", "digests", "workspace", "actions-tasks-escalations")),
    "domain-4": (8, ("portals-catalog", "shn-sla-targeted", "analytics")),
    "domain-5": (10, ("architecture", "end-to-end", "project-scope", "knowledge")),
}


class GuideParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.domains = {}
        self.topics = {}
        self.current_domain = None
        self.current_topic = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
            if self.current_domain and attrs["href"].startswith("https://"):
                self.domains[self.current_domain]["sources"].append(attrs["href"])
        if tag == "section" and attrs.get("id") in DOMAINS:
            self.current_domain = attrs["id"]
            self.domains[self.current_domain] = {"text": [], "sources": []}
        if tag == "div" and "data-topic" in attrs:
            self.current_topic = attrs["data-topic"]
            self.topics[self.current_topic] = []

    def handle_endtag(self, tag):
        if tag == "div":
            self.current_topic = None
        if tag == "section":
            self.current_domain = None

    def handle_data(self, data):
        if self.current_domain:
            self.domains[self.current_domain]["text"].append(data)
        if self.current_topic:
            self.topics[self.current_topic].append(data)


class CurriculumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = GUIDE.read_text(encoding="utf-8")
        cls.parsed = GuideParser()
        cls.parsed.feed(cls.html)

    def test_all_domains_have_weights_lessons_and_official_sources(self):
        self.assertEqual(sum(weight for weight, _ in DOMAINS.values()), 100)
        for domain, (weight, topics) in DOMAINS.items():
            with self.subTest(domain=domain):
                self.assertIn(domain, self.parsed.domains)
                lesson = self.parsed.domains[domain]
                text = " ".join(lesson["text"])
                self.assertIn(f"{weight}%", text)
                self.assertGreater(len(text.split()), 220)
                self.assertGreaterEqual(len(lesson["sources"]), 1)
                self.assertIn("Practice", text)
                self.assertIn("Check your understanding", text)
                for topic in topics:
                    self.assertIn(topic, self.parsed.topics)
                    self.assertGreater(len(" ".join(self.parsed.topics[topic]).split()), 65)

    def test_navigation_and_html_integrity(self):
        for anchor in ("credential", "exam-facts", "curriculum-map", "data-model",
                       "getting-started", "implementation", "learning",
                       "related-credentials", "references"):
            self.assertIn(anchor, self.parsed.ids, anchor)
        self.assertEqual(len(self.parsed.ids), len(set(self.parsed.ids)))
        for href in self.parsed.links:
            if href.startswith("#"):
                self.assertIn(href[1:], self.parsed.ids, href)
            if href.startswith("https://"):
                host = urlparse(href).hostname or ""
                self.assertTrue(host == "servicenow.com" or host.endswith(".servicenow.com"), href)
        for domain in DOMAINS:
            self.assertIn(f"#{domain}", self.parsed.links)

    def test_practical_content_present(self):
        lowered = self.html.lower()
        for marker in (
            "guided setup",
            "$450",
            "60 questions",
            "pearson",
            "sn_customerservice_case",
            "tier 1",
            "tier 4",
            "micro-certification",
            "delta",
            "measureup",
            "now create",
            "does not replace entitlement checks",
        ):
            self.assertIn(marker, lowered, marker)


if __name__ == "__main__":
    unittest.main()
