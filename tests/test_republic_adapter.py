from __future__ import annotations

import unittest
from urllib.error import URLError

from scraper import PARTIALLY_PARSED_SOURCE, WORKING_LIVE_SOURCE
from scraper.adapters import MANUAL_REVIEW_SOURCE, RepublicAdapter


NO_OPEN_BIDS_HTML = """
<html>
  <body>
    <p>The following is a listing of various bid postings.</p>
    <p>There are no open bid postings at this time.</p>
  </body>
</html>
"""


ACTIVE_BIDS_HTML = """
<html>
  <body>
    <table>
      <tr>
        <th>Category</th>
        <th>Bid Title</th>
        <th>Closing Date</th>
        <th>Bid Number</th>
      </tr>
      <tr>
        <td>Request for Proposal</td>
        <td><a href="/DocumentCenter/View/1234/Water-Treatment-Controls-RFP">Water Treatment Controls Upgrade</a></td>
        <td>05/15/2026 02:00 PM</td>
        <td>RFP-2026-07</td>
      </tr>
    </table>
  </body>
</html>
"""


class FakeRepublicAdapter(RepublicAdapter):
    def __init__(self, html: str | None = None, error: Exception | None = None) -> None:
        super().__init__()
        self.html = html
        self.error = error

    def _fetch_page(self, url: str) -> str:
        if self.error is not None:
            raise self.error
        if self.html is None:
            raise AssertionError("html fixture is required when no error is provided")
        return self.html


class RepublicAdapterTests(unittest.TestCase):
    def test_reports_no_open_bids_as_working_live(self) -> None:
        adapter = FakeRepublicAdapter(html=NO_OPEN_BIDS_HTML)

        opportunities, report = adapter.fetch()

        self.assertEqual([], opportunities)
        self.assertEqual(WORKING_LIVE_SOURCE, report.adapter_status)
        self.assertIn("no open bid postings", report.note.lower())

    def test_parses_structured_bid_rows(self) -> None:
        adapter = FakeRepublicAdapter(html=ACTIVE_BIDS_HTML)

        opportunities, report = adapter.fetch()

        self.assertEqual(WORKING_LIVE_SOURCE, report.adapter_status)
        self.assertEqual(1, report.parsed_count)
        self.assertEqual(1, len(opportunities))

        opportunity = opportunities[0]
        self.assertEqual("Water Treatment Controls Upgrade", opportunity.title)
        self.assertEqual("City of Republic", opportunity.agency)
        self.assertEqual("City of Republic Bid Postings", opportunity.portal)
        self.assertEqual("Republic, MO", opportunity.location)
        self.assertEqual("05/15/2026 02:00 PM", opportunity.due_date)
        self.assertEqual("Request for Proposal", opportunity.solicitation_type)
        self.assertEqual("live", opportunity.source_type)
        self.assertEqual(
            "https://www.republicmo.com/DocumentCenter/View/1234/Water-Treatment-Controls-RFP",
            opportunity.url,
        )

    def test_fetch_failure_is_marked_for_manual_review(self) -> None:
        adapter = FakeRepublicAdapter(error=URLError("403 Forbidden"))

        opportunities, report = adapter.fetch()

        self.assertEqual([], opportunities)
        self.assertEqual(MANUAL_REVIEW_SOURCE, report.adapter_status)
        self.assertIn("could not be fetched", report.note.lower())

    def test_partial_parse_when_rows_are_not_structured_bid_rows(self) -> None:
        adapter = FakeRepublicAdapter(html="<html><body><table><tr><td>Footer link</td></tr></table></body></html>")

        opportunities, report = adapter.fetch()

        self.assertEqual([], opportunities)
        self.assertEqual(PARTIALLY_PARSED_SOURCE, report.adapter_status)
        self.assertIn("no structured bid rows", report.note.lower())


if __name__ == "__main__":
    unittest.main()
