from __future__ import annotations

import unittest

from main import _clean_live_description, enrich_results
from scraper.models import Opportunity, SourceReport


class FakeOpportunityScraper:
    def __init__(self, source: str = "live") -> None:
        self.source = source

    def fetch_opportunities(
        self,
        limit: int,
        keyword: str | None,
        state: str | None,
        location: str | None,
        naics_codes=None,
    ):
        del limit, keyword, state, location, naics_codes
        return {
            "opportunities": [
                Opportunity(
                    title="Janitorial Services",
                    agency="City of Example",
                    portal="Example Portal",
                    location="Example, MO",
                    due_date="2026-04-10",
                    solicitation_type="Request for Proposal",
                    source_type="live",
                    url="https://example.test/bid/1",
                    description="""
                        <script>console.log('noise')</script>
                        <div>Skip to Main Content</div>
                        <div>Create a Website Account</div>
                        <p>Provide janitorial services for municipal buildings.</p>
                        <footer>Privacy Policy</footer>
                    """,
                    source_key="example",
                    adapter_status="working live source",
                )
            ],
            "source_reports": [
                SourceReport(
                    source_key="example",
                    agency="City of Example",
                    portal="Example Portal",
                    region="Example, MO",
                    source_type="live",
                    adapter_status="working live source",
                    source_url="https://example.test",
                    note="ok",
                    parsed_count=1,
                )
            ],
        }


class OutputFormattingTests(unittest.TestCase):
    def test_clean_live_description_removes_html_and_boilerplate(self) -> None:
        cleaned = _clean_live_description(
            """
            <script>alert('x')</script>
            <div>Skip to Main Content</div>
            <p>Network equipment replacement for public safety systems.</p>
            <div>Powered by CivicPlus</div>
            """
        )

        self.assertEqual("Network equipment replacement for public safety systems.", cleaned)

    def test_compact_json_keeps_only_requested_fields(self) -> None:
        import main

        original_scraper = main.OpportunityScraper
        try:
            main.OpportunityScraper = FakeOpportunityScraper
            results = enrich_results(
                source="live",
                limit=10,
                top=None,
                keyword=None,
                state=None,
                location=None,
                compact_json=True,
            )
        finally:
            main.OpportunityScraper = original_scraper

        self.assertEqual(
            [
                "title",
                "agency",
                "portal",
                "location",
                "due_date",
                "solicitation_type",
                "source_type",
                "url",
                "match_score",
                "tier",
                "score_reasons",
                "supplier_matches",
            ],
            list(results["opportunities"][0].keys()),
        )


if __name__ == "__main__":
    unittest.main()
