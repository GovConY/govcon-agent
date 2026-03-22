from __future__ import annotations

import unittest

from main import _classify_tier, _score_opportunity, enrich_results
from scraper.models import Opportunity, SourceReport


class FakeScoringScraper:
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
                    title="Construction Management Services",
                    agency="City of Springfield",
                    portal="Portal",
                    location="Springfield, MO",
                    due_date="2026-04-10",
                    solicitation_type="Request for Proposal",
                    source_type="live",
                    url="https://example.test/1",
                    description="Construction support for downtown improvements.",
                    naics_code="236220",
                    adapter_status="working live source",
                ),
                Opportunity(
                    title="Office Supplies",
                    agency="City of Ozark",
                    portal="Portal",
                    location="Ozark, MO",
                    due_date="2026-04-11",
                    solicitation_type="Bid",
                    source_type="live",
                    url="https://example.test/2",
                    description="General office products.",
                    naics_code="339940",
                    adapter_status="partially parsed source",
                ),
            ],
            "source_reports": [
                SourceReport(
                    source_key="a",
                    agency="A",
                    portal="P",
                    region="R",
                    source_type="live",
                    adapter_status="working live source",
                    source_url="https://example.test",
                    note="ok",
                    parsed_count=2,
                )
            ],
        }


class ScoringTests(unittest.TestCase):
    def test_score_opportunity_adds_expected_reasons(self) -> None:
        opportunity = Opportunity(
            title="Construction Management Services",
            agency="City of Springfield",
            portal="Portal",
            location="Springfield, MO",
            due_date="2026-04-10",
            solicitation_type="Request for Proposal",
            source_type="live",
            url="https://example.test/1",
            description="Construction support for downtown improvements.",
            naics_code="236220",
            adapter_status="working live source",
        )

        scored = _score_opportunity(opportunity, keyword="construction", naics_codes={"236220"})

        self.assertGreater(scored.match_score, 0)
        self.assertIn("keyword match in title (+10)", scored.score_reasons)
        self.assertIn("construction contract profile (+10)", scored.score_reasons)
        self.assertIn("keyword match in description (+3)", scored.score_reasons)
        self.assertIn("exact NAICS match (236220) (+15)", scored.score_reasons)
        self.assertIn("Springfield location relevance (+8)", scored.score_reasons)
        self.assertIn("RFP solicitation relevance (+3)", scored.score_reasons)
        self.assertIn("working live source confidence (+5)", scored.score_reasons)
        self.assertEqual("HIGH PRIORITY", scored.tier)

    def test_title_type_boosts_stack_with_keyword_scoring(self) -> None:
        opportunity = Opportunity(
            title="Airport Construction Maintenance Services",
            agency="City of Springfield",
            portal="Portal",
            location="Springfield, MO",
            due_date="2026-04-10",
            solicitation_type="Invitation for Bid",
            source_type="live",
            url="https://example.test/1",
            description="Construction support for airport facilities.",
            naics_code="236220",
            adapter_status="working live source",
        )

        scored = _score_opportunity(opportunity, keyword="construction", naics_codes=None)

        self.assertIn("keyword match in title (+10)", scored.score_reasons)
        self.assertIn("airport contract profile (+12)", scored.score_reasons)
        self.assertIn("construction contract profile (+10)", scored.score_reasons)
        self.assertIn("maintenance contract profile (+5)", scored.score_reasons)

    def test_classify_tier_thresholds(self) -> None:
        self.assertEqual("HIGH PRIORITY", _classify_tier(30))
        self.assertEqual("MEDIUM PRIORITY", _classify_tier(20))
        self.assertEqual("LOW PRIORITY", _classify_tier(19))

    def test_match_score_is_capped_at_50(self) -> None:
        opportunity = Opportunity(
            title="Airport Construction Maintenance Services",
            agency="City of Springfield",
            portal="Portal",
            location="Springfield, MO",
            due_date="2026-04-10",
            solicitation_type="Invitation for Bid",
            source_type="live",
            url="https://example.test/1",
            description="Construction maintenance support for airport facilities and related work.",
            naics_code="236220",
            adapter_status="working live source",
        )

        scored = _score_opportunity(opportunity, keyword="construction", naics_codes={"236220"})

        self.assertEqual(50, scored.match_score)

    def test_results_are_sorted_by_highest_score_first(self) -> None:
        import main

        original_scraper = main.OpportunityScraper
        try:
            main.OpportunityScraper = FakeScoringScraper
            results = enrich_results(
                source="live",
                limit=10,
                top=None,
                keyword="construction",
                state=None,
                location=None,
                naics_codes={"236220"},
            )
        finally:
            main.OpportunityScraper = original_scraper

        self.assertEqual("Construction Management Services", results["opportunities"][0]["title"])
        self.assertGreater(
            results["opportunities"][0]["match_score"],
            results["opportunities"][1]["match_score"],
        )

    def test_top_flag_limits_results_after_sorting(self) -> None:
        import main

        original_scraper = main.OpportunityScraper
        try:
            main.OpportunityScraper = FakeScoringScraper
            results = enrich_results(
                source="live",
                limit=10,
                top=1,
                keyword="construction",
                state=None,
                location=None,
                naics_codes={"236220"},
            )
        finally:
            main.OpportunityScraper = original_scraper

        self.assertEqual(1, len(results["opportunities"]))
        self.assertEqual("Construction Management Services", results["opportunities"][0]["title"])


if __name__ == "__main__":
    unittest.main()
