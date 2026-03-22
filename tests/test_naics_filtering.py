from __future__ import annotations

import unittest

from scraper.adapters import SourceAdapter
from scraper.models import Opportunity


class NaicsFilteringTests(unittest.TestCase):
    def test_naics_filter_does_not_exclude_rows(self) -> None:
        opportunities = [
            Opportunity(
                title="Road Resurfacing",
                agency="City",
                portal="Portal",
                location="Springfield, MO",
                due_date="",
                solicitation_type="Bid",
                source_type="live",
                url="https://example.test/1",
                naics_code="237310",
            ),
            Opportunity(
                title="Building Construction",
                agency="City",
                portal="Portal",
                location="Springfield, MO",
                due_date="",
                solicitation_type="Bid",
                source_type="live",
                url="https://example.test/2",
                naics_code="236220",
            ),
            Opportunity(
                title="General Services",
                agency="City",
                portal="Portal",
                location="Springfield, MO",
                due_date="",
                solicitation_type="Bid",
                source_type="live",
                url="https://example.test/3",
                naics_code="",
            ),
        ]

        filtered = SourceAdapter._apply_filters(
            opportunities,
            keyword=None,
            state="MO",
            location=None,
            naics_codes={"236220", "237310"},
        )

        self.assertEqual(3, len(filtered))
        self.assertEqual(["237310", "236220", ""], [item.naics_code for item in filtered])

    def test_keyword_filter_still_applies_when_naics_is_present(self) -> None:
        opportunities = [
            Opportunity(
                title="Construction Management",
                agency="City",
                portal="Portal",
                location="Springfield, MO",
                due_date="",
                solicitation_type="Bid",
                source_type="live",
                url="https://example.test/1",
                naics_code="236220",
                description="Vertical construction services",
            ),
            Opportunity(
                title="Construction Inspection",
                agency="City",
                portal="Portal",
                location="Springfield, MO",
                due_date="",
                solicitation_type="Bid",
                source_type="live",
                url="https://example.test/2",
                naics_code="541350",
                description="Inspection services",
            ),
        ]

        filtered = SourceAdapter._apply_filters(
            opportunities,
            keyword="construction",
            state="MO",
            location=None,
            naics_codes={"236220"},
        )

        self.assertEqual(2, len(filtered))

    def test_keeps_unknown_naics_when_naics_filter_is_present(self) -> None:
        opportunities = [
            Opportunity(
                title="Pavement Repair",
                agency="City",
                portal="Portal",
                location="Springfield, MO",
                due_date="",
                solicitation_type="Bid",
                source_type="live",
                url="https://example.test/1",
                naics_code="",
            ),
            Opportunity(
                title="Waterline Improvements",
                agency="City",
                portal="Portal",
                location="Springfield, MO",
                due_date="",
                solicitation_type="Bid",
                source_type="live",
                url="https://example.test/2",
                naics_code="237110",
            ),
        ]

        filtered = SourceAdapter._apply_filters(
            opportunities,
            keyword=None,
            state="MO",
            location=None,
            naics_codes={"236220"},
        )

        self.assertEqual(2, len(filtered))
        self.assertEqual("", filtered[0].naics_code)


if __name__ == "__main__":
    unittest.main()
