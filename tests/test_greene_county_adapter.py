from __future__ import annotations

import unittest
from urllib.error import URLError

from scraper import PARTIALLY_PARSED_SOURCE, WORKING_LIVE_SOURCE
from scraper.adapters import GreeneCountyAdapter, MANUAL_REVIEW_SOURCE


COUNTY_HTML = """
<html>
  <body>
    <p>Greene County uses Beacon Bid to share solicitations with suppliers.</p>
    <a href="https://www.beaconbid.com/register/greene-county-mo">Register for Alerts</a>
    <a href="https://www.beaconbid.com/solicitations/greene-county-mo/open">View Open Solicitations</a>
  </body>
</html>
"""


BEACON_JS_SHELL_HTML = """
<html>
  <body>
    <div>You need to enable JavaScript to access www.beaconbid.com</div>
  </body>
</html>
"""


BEACON_LISTINGS_HTML = """
<html>
  <body>
    <div class="solicitation-card">
      <a href="/solicitations/greene-county-mo/abc123/fleet-maintenance-services">
        Fleet Maintenance Services
      </a>
    </div>
    <div class="solicitation-card">
      <a href="/solicitations/greene-county-mo/def456/custodial-supplies">
        Custodial Supplies
      </a>
    </div>
  </body>
</html>
"""


class FakeGreeneCountyAdapter(GreeneCountyAdapter):
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


class GreeneCountyAdapterTests(unittest.TestCase):
    def test_identifies_beacon_bid_when_vendor_portal_is_js_only(self) -> None:
        adapter = FakeGreeneCountyAdapter(
            pages={
                "https://greenecountymo.gov/purchasing/bids.php": COUNTY_HTML,
                "https://www.beaconbid.com/solicitations/greene-county-mo/open": BEACON_JS_SHELL_HTML,
            }
        )

        opportunities, report = adapter.fetch()

        self.assertEqual([], opportunities)
        self.assertEqual(PARTIALLY_PARSED_SOURCE, report.adapter_status)
        self.assertIn("beacon bid", report.note.lower())
        self.assertIn("javascript-required shell", report.note.lower())

    def test_parses_real_beacon_listing_links_when_static_html_exposes_them(self) -> None:
        adapter = FakeGreeneCountyAdapter(
            pages={
                "https://greenecountymo.gov/purchasing/bids.php": COUNTY_HTML,
                "https://www.beaconbid.com/solicitations/greene-county-mo/open": BEACON_LISTINGS_HTML,
            }
        )

        opportunities, report = adapter.fetch()

        self.assertEqual(WORKING_LIVE_SOURCE, report.adapter_status)
        self.assertEqual(2, report.parsed_count)
        self.assertEqual(2, len(opportunities))
        self.assertEqual("Beacon Bid", opportunities[0].portal)
        self.assertEqual("Fleet Maintenance Services", opportunities[0].title)
        self.assertEqual(
            "https://www.beaconbid.com/solicitations/greene-county-mo/abc123/fleet-maintenance-services",
            opportunities[0].url,
        )

    def test_fetch_failure_is_marked_for_manual_review(self) -> None:
        adapter = FakeGreeneCountyAdapter(error=URLError("403 Forbidden"))

        opportunities, report = adapter.fetch()

        self.assertEqual([], opportunities)
        self.assertEqual(MANUAL_REVIEW_SOURCE, report.adapter_status)
        self.assertIn("could not be fetched", report.note.lower())


if __name__ == "__main__":
    unittest.main()
