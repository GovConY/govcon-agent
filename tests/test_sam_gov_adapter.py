from __future__ import annotations

import os
import unittest
from datetime import date
from urllib.error import HTTPError

from scraper import PARTIALLY_PARSED_SOURCE, WORKING_LIVE_SOURCE
from scraper.adapters import SamGovAdapter


class FakeSamGovAdapter(SamGovAdapter):
    def __init__(self, responses: dict[str, dict[str, object]]) -> None:
        super().__init__()
        self.responses = responses

    def _fetch_json(self, url: str) -> dict[str, object]:
        if url not in self.responses:
            raise AssertionError(f"missing JSON fixture for {url}")
        return self.responses[url]

    def _date_range(self):
        return date(2026, 2, 20), date(2026, 3, 22)


class SamGovAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_key = os.environ.get("SAM_GOV_API_KEY")
        os.environ["SAM_GOV_API_KEY"] = "demo-key"

    def tearDown(self) -> None:
        if self.original_key is None:
            os.environ.pop("SAM_GOV_API_KEY", None)
        else:
            os.environ["SAM_GOV_API_KEY"] = self.original_key

    def test_reports_missing_api_key(self) -> None:
        os.environ.pop("SAM_GOV_API_KEY", None)
        adapter = FakeSamGovAdapter({})

        opportunities, report = adapter.fetch()

        self.assertEqual([], opportunities)
        self.assertEqual(PARTIALLY_PARSED_SOURCE, report.adapter_status)
        self.assertIn("sam_gov_api_key", report.note.lower())

    def test_normalizes_paginated_results(self) -> None:
        adapter = FakeSamGovAdapter(
            responses={
                "https://api.sam.gov/opportunities/v2/search?api_key=demo-key&postedFrom=02%2F20%2F2026&postedTo=03%2F22%2F2026&limit=100&offset=0&state=MO": {
                    "totalRecords": 2,
                    "opportunitiesData": [
                        {
                            "title": "Network Operations Support",
                            "fullParentPathName": "DEPARTMENT OF THE AIR FORCE.AIR FORCE MATERIEL COMMAND",
                            "responseDeadLine": "2026-04-15",
                            "type": "Solicitation",
                            "uiLink": "https://sam.gov/opp/abc/view",
                            "naicsCode": "541513",
                            "placeOfPerformance": {
                                "city": {"name": "Springfield"},
                                "state": {"code": "MO"},
                                "zip": "65806",
                            },
                            "solicitationNumber": "FA0001-26-R-0001",
                        }
                    ],
                },
                "https://api.sam.gov/opportunities/v2/search?api_key=demo-key&postedFrom=02%2F20%2F2026&postedTo=03%2F22%2F2026&limit=100&offset=1&state=MO": {
                    "totalRecords": 101,
                    "opportunitiesData": [
                        {
                            "title": "Custodial Services",
                            "department": "GENERAL SERVICES ADMINISTRATION",
                            "subtier": "PUBLIC BUILDINGS SERVICE",
                            "office": "PBS R7",
                            "reponseDeadLine": "2026-04-20",
                            "baseType": "Combined Synopsis/Solicitation",
                            "additionalInfoLink": "https://sam.gov/opp/def/additional",
                            "officeAddress": {
                                "city": "Kansas City",
                                "state": "MO",
                                "zipcode": "64106",
                            },
                            "solicitationNumber": "47PK0226R0005",
                        }
                    ],
                },
            }
        )

        opportunities, report = adapter.fetch(state="MO")

        self.assertEqual(WORKING_LIVE_SOURCE, report.adapter_status)
        self.assertEqual(2, report.parsed_count)
        self.assertEqual(2, len(opportunities))
        self.assertEqual("Network Operations Support", opportunities[0].title)
        self.assertEqual("DEPARTMENT OF THE AIR FORCE.AIR FORCE MATERIEL COMMAND", opportunities[0].agency)
        self.assertEqual("Springfield, MO", opportunities[0].location)
        self.assertEqual("Solicitation", opportunities[0].solicitation_type)
        self.assertEqual("https://sam.gov/opp/abc/view", opportunities[0].url)
        self.assertEqual("GENERAL SERVICES ADMINISTRATION / PUBLIC BUILDINGS SERVICE / PBS R7", opportunities[1].agency)
        self.assertEqual("2026-04-20", opportunities[1].due_date)
        self.assertEqual("Combined Synopsis/Solicitation", opportunities[1].solicitation_type)
        self.assertEqual("https://sam.gov/opp/def/additional", opportunities[1].url)

    def test_normalizes_rows_when_fields_are_nested_or_scalar(self) -> None:
        adapter = FakeSamGovAdapter(
            responses={
                "https://api.sam.gov/opportunities/v2/search?api_key=demo-key&postedFrom=02%2F20%2F2026&postedTo=03%2F22%2F2026&limit=100&offset=0&state=MO": {
                    "totalRecords": 1,
                    "opportunitiesData": [
                        {
                            "data": {
                                "title": "Emergency Generator Replacement",
                                "fullParentPathName": "DEPARTMENT OF VETERANS AFFAIRS",
                                "placeOfPerformance": {
                                    "city": "Springfield",
                                    "state": "MO",
                                },
                                "responseDeadLine": "2026-04-30",
                                "type": "Solicitation",
                                "links": [
                                    {
                                        "rel": "self",
                                        "href": "https://api.sam.gov/prod/opportunities/v1/search?noticeid=abc123&limit=1",
                                    }
                                ],
                                "solicitationNumber": "36C25526R0001",
                                "naicsCode": "238290",
                            }
                        }
                    ],
                }
            }
        )

        opportunities, report = adapter.fetch(state="MO", location="Springfield")

        self.assertEqual(WORKING_LIVE_SOURCE, report.adapter_status)
        self.assertEqual(1, report.parsed_count)
        self.assertEqual(1, len(opportunities))
        self.assertEqual("Emergency Generator Replacement", opportunities[0].title)
        self.assertEqual("DEPARTMENT OF VETERANS AFFAIRS", opportunities[0].agency)
        self.assertEqual("Springfield, MO", opportunities[0].location)
        self.assertEqual("2026-04-30", opportunities[0].due_date)
        self.assertEqual("Solicitation", opportunities[0].solicitation_type)
        self.assertEqual(
            "https://api.sam.gov/prod/opportunities/v1/search?noticeid=abc123&limit=1",
            opportunities[0].url,
        )

    def test_builds_documented_search_url(self) -> None:
        adapter = FakeSamGovAdapter({})

        url = adapter._build_search_url(
            api_key="demo-key",
            posted_from=date(2026, 2, 20),
            posted_to=date(2026, 3, 22),
            page_index=0,
            keyword="network support",
            state="MO",
        )

        self.assertEqual(
            "https://api.sam.gov/opportunities/v2/search?"
            "api_key=demo-key&postedFrom=02%2F20%2F2026&postedTo=03%2F22%2F2026&"
            "limit=100&offset=0&title=network+support&state=MO",
            url,
        )

    def test_http_404_is_treated_as_no_data(self) -> None:
        class MissingDataSamGovAdapter(FakeSamGovAdapter):
            def _fetch_json(self, url: str) -> dict[str, object]:
                raise HTTPError(url, 404, "Not Found", hdrs=None, fp=None)

        adapter = MissingDataSamGovAdapter({})

        opportunities, report = adapter.fetch(state="MO")

        self.assertEqual([], opportunities)
        self.assertEqual(WORKING_LIVE_SOURCE, report.adapter_status)
        self.assertIn("returned no opportunities", report.note.lower())


if __name__ == "__main__":
    unittest.main()
