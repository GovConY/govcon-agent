from __future__ import annotations

import unittest

from scraper import PARTIALLY_PARSED_SOURCE, WORKING_LIVE_SOURCE
from scraper.adapters import OzarkAdapter


ACTIVE_BIDS_HTML = """
<html>
  <body>
    <a href="#maincontent">Skip to Main Content</a>
    <a href="/MyAccount">Create a Website Account</a>
    <a href="/living-in-ozark">Living in Ozark</a>
    <a href="/Bids.aspx?bidID=212">Downtown Streetscape Improvements</a>
    <a href="/DocumentCenter/View/901/Water-Meter-RFP">Water Meter Replacement RFP</a>
    <a href="/DocumentCenter/View/902/parks-master-plan">Parks Master Plan</a>
    <a href="/Government/City-Council">City Council</a>
  </body>
</html>
"""


class FakeOzarkAdapter(OzarkAdapter):
    def __init__(self, html: str) -> None:
        super().__init__()
        self.html = html

    def _fetch_page(self, url: str) -> str:
        return self.html


class OzarkAdapterTests(unittest.TestCase):
    def test_filters_navigation_and_non_bid_links(self) -> None:
        adapter = FakeOzarkAdapter(ACTIVE_BIDS_HTML)

        opportunities, report = adapter.fetch()

        self.assertEqual(WORKING_LIVE_SOURCE, report.adapter_status)
        self.assertEqual(2, len(opportunities))
        self.assertEqual(2, report.parsed_count)
        self.assertEqual("Downtown Streetscape Improvements", opportunities[0].title)
        self.assertEqual("https://www.ozarkmissouri.com/Bids.aspx?bidID=212", opportunities[0].url)
        self.assertEqual("Water Meter Replacement RFP", opportunities[1].title)
        self.assertEqual(
            "https://www.ozarkmissouri.com/DocumentCenter/View/901/Water-Meter-RFP",
            opportunities[1].url,
        )
        self.assertEqual("Request for Proposal", opportunities[1].solicitation_type)

    def test_partial_parse_when_no_bid_like_links_exist(self) -> None:
        adapter = FakeOzarkAdapter(
            "<html><body><a href='/living-in-ozark'>Living in Ozark</a><a href='/Government'>Government</a></body></html>"
        )

        opportunities, report = adapter.fetch()

        self.assertEqual([], opportunities)
        self.assertEqual(PARTIALLY_PARSED_SOURCE, report.adapter_status)


if __name__ == "__main__":
    unittest.main()
