from __future__ import annotations

import unittest
from urllib.error import URLError

from scraper import PARTIALLY_PARSED_SOURCE, WORKING_LIVE_SOURCE
from scraper.adapters import MANUAL_REVIEW_SOURCE, SpringfieldAdapter


LISTING_HTML = """
<html>
  <body>
    <div class="bid-postings">
      <div class="bid-item">
        <a href="/Bids.aspx?bidID=1410">TECHNICAL TRAINING SERVICES</a>
      </div>
      <div class="bid-item">
        <a href="/Bids.aspx?bidID=1411">JANITORIAL SERVICES</a>
      </div>
    </div>
  </body>
</html>
"""


DETAIL_1410_HTML = """
<html>
  <body>
    <div>Bid Number: | 017-2026IFB</div>
    <div>Bid Title: | TECHNICAL TRAINING SERVICES</div>
    <div>Category: | All Notifications - Division of Purchases</div>
    <div>Status: | Open</div>
    <div>
      Description:
      LEGAL NOTICE: INVITATION FOR BID #017-2026
      The City of Springfield will accept electronically submitted bids.
      Bids must be received electronically by 3:00 P.M. (CST), on THURSDAY, APRIL 16, 2026.
    </div>
  </body>
</html>
"""


DETAIL_1411_HTML = """
<html>
  <body>
    <div>Bid Number: | 018-2026RFP</div>
    <div>Bid Title: | JANITORIAL SERVICES</div>
    <div>Category: | All Notifications - Division of Purchases</div>
    <div>Status: | Open</div>
    <div>
      Description:
      LEGAL NOTICE: REQUEST FOR PROPOSAL #018-2026
      The City of Springfield will electronically accept submitted proposals.
      Proposals must be received electronically by 2:00 P.M. (CST), on FRIDAY, APRIL 17, 2026.
    </div>
  </body>
</html>
"""


class FakeSpringfieldAdapter(SpringfieldAdapter):
    def __init__(self, pages: dict[str, str] | None = None, error: Exception | None = None) -> None:
        super().__init__()
        self.pages = pages or {}
        self.error = error

    def _fetch_page(self, url: str) -> str:
        if self.error is not None:
            raise self.error
        if url not in self.pages:
            raise AssertionError(f"missing html fixture for {url}")
        return self.pages[url]


class SpringfieldAdapterTests(unittest.TestCase):
    def test_parses_bid_links_instead_of_table_rows(self) -> None:
        adapter = FakeSpringfieldAdapter(
            pages={
                "https://www.springfieldmo.gov/Bids.aspx": LISTING_HTML,
                "https://www.springfieldmo.gov/Bids.aspx?bidID=1410": DETAIL_1410_HTML,
                "https://www.springfieldmo.gov/Bids.aspx?bidID=1411": DETAIL_1411_HTML,
            }
        )

        opportunities, report = adapter.fetch()

        self.assertEqual(WORKING_LIVE_SOURCE, report.adapter_status)
        self.assertEqual(2, report.parsed_count)
        self.assertEqual(2, len(opportunities))

        first = opportunities[0]
        self.assertEqual("TECHNICAL TRAINING SERVICES", first.title)
        self.assertEqual("City of Springfield", first.agency)
        self.assertEqual("City of Springfield Bid Portal", first.portal)
        self.assertEqual("Springfield, MO", first.location)
        self.assertEqual("Thursday, April 16, 2026 3:00 P.M. (CST)", first.due_date)
        self.assertEqual("Invitation for Bid", first.solicitation_type)
        self.assertEqual("https://www.springfieldmo.gov/Bids.aspx?bidID=1410", first.url)

        second = opportunities[1]
        self.assertEqual("Request for Proposal", second.solicitation_type)
        self.assertEqual("Friday, April 17, 2026 2:00 P.M. (CST)", second.due_date)

    def test_partial_parse_when_listing_has_no_bid_detail_links(self) -> None:
        adapter = FakeSpringfieldAdapter(
            pages={
                "https://www.springfieldmo.gov/Bids.aspx": "<html><body><div><a href='/contact'>Contact</a></div></body></html>"
            }
        )

        opportunities, report = adapter.fetch()

        self.assertEqual([], opportunities)
        self.assertEqual(PARTIALLY_PARSED_SOURCE, report.adapter_status)
        self.assertIn("no bid detail links matching bids.aspx?bidid", report.note.lower())

    def test_fetch_failure_is_marked_for_manual_review(self) -> None:
        adapter = FakeSpringfieldAdapter(error=URLError("403 Forbidden"))

        opportunities, report = adapter.fetch()

        self.assertEqual([], opportunities)
        self.assertEqual(MANUAL_REVIEW_SOURCE, report.adapter_status)
        self.assertIn("could not be fetched", report.note.lower())


if __name__ == "__main__":
    unittest.main()
