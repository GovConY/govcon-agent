from __future__ import annotations

import re
from html import unescape
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import Opportunity, SourceReport

WORKING_LIVE_SOURCE = "working live source"
PARTIALLY_PARSED_SOURCE = "partially parsed source"
MANUAL_REVIEW_SOURCE = "source requiring manual review"
MOCK_SOURCE = "mock source"
USER_AGENT = "Mozilla/5.0 (compatible; govcon-agent/2.0)"


class SourceAdapter:
    source_key: str
    agency: str
    portal: str
    region: str
    source_url: str
    source_type: str = "live"

    def fetch(
        self,
        keyword: str | None = None,
        state: str | None = None,
        location: str | None = None,
    ) -> tuple[list[Opportunity], SourceReport]:
        raise NotImplementedError

    def _fetch_page(self, url: str) -> str:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8", "ignore")

    def _base_report(self, adapter_status: str, note: str, parsed_count: int = 0) -> SourceReport:
        return SourceReport(
            source_key=self.source_key,
            agency=self.agency,
            portal=self.portal,
            region=self.region,
            source_type=self.source_type,
            adapter_status=adapter_status,
            source_url=self.source_url,
            note=note,
            parsed_count=parsed_count,
        )

    @staticmethod
    def _apply_filters(
        opportunities: Iterable[Opportunity],
        keyword: str | None,
        state: str | None,
        location: str | None,
    ) -> list[Opportunity]:
        filtered = list(opportunities)

        if keyword:
            keyword_lower = keyword.lower()
            filtered = [
                item
                for item in filtered
                if keyword_lower in item.title.lower() or keyword_lower in item.description.lower()
            ]

        if state:
            state_upper = state.upper()
            filtered = [item for item in filtered if item.location.upper().endswith(state_upper)]

        if location:
            location_lower = location.lower()
            filtered = [
                item
                for item in filtered
                if location_lower in item.location.lower()
                or location_lower in item.agency.lower()
                or location_lower in item.description.lower()
                or location_lower in item.portal.lower()
            ]

        return filtered


class MockRegionalAdapter(SourceAdapter):
    source_key = "mock_regional"
    agency = "Regional Mock Data"
    portal = "Mock Procurement Sandbox"
    region = "Springfield, Greene County, Missouri statewide"
    source_url = "https://example.invalid/mock-data"
    source_type = "mock"

    def fetch(
        self,
        keyword: str | None = None,
        state: str | None = None,
        location: str | None = None,
    ) -> tuple[list[Opportunity], SourceReport]:
        opportunities = [
            Opportunity(
                title="City Utilities Network Hardware Refresh",
                agency="City of Springfield",
                portal="City of Springfield Bid Portal",
                location="Springfield, MO",
                due_date="2026-04-14",
                solicitation_type="Invitation for Bid",
                source_type="mock",
                url="https://example.invalid/mock/springfield-network-hardware",
                description="Utility division seeks switches, network monitoring, and installation support.",
                naics_code="334111",
                source_key=self.source_key,
                adapter_status=MOCK_SOURCE,
            ),
            Opportunity(
                title="Downtown Signal and Streetlight Maintenance",
                agency="City of Springfield",
                portal="City of Springfield Bid Portal",
                location="Springfield, MO",
                due_date="2026-04-18",
                solicitation_type="Invitation for Bid",
                source_type="mock",
                url="https://example.invalid/mock/springfield-streetlight-maintenance",
                description="Electrical maintenance, signal cabinet upgrades, and field engineering support.",
                naics_code="238210",
                source_key=self.source_key,
                adapter_status=MOCK_SOURCE,
            ),
            Opportunity(
                title="Justice Center Janitorial Services",
                agency="Greene County",
                portal="Greene County Procurement",
                location="Greene County, MO",
                due_date="2026-04-09",
                solicitation_type="Request for Proposal",
                source_type="mock",
                url="https://example.invalid/mock/greene-county-janitorial",
                description="Custodial and building cleaning services for justice facilities in the Springfield area.",
                naics_code="561720",
                source_key=self.source_key,
                adapter_status=MOCK_SOURCE,
            ),
            Opportunity(
                title="Fleet Parts and Service",
                agency="Greene County",
                portal="Greene County Procurement",
                location="Greene County, MO",
                due_date="2026-04-11",
                solicitation_type="Invitation for Bid",
                source_type="mock",
                url="https://example.invalid/mock/greene-county-fleet-service",
                description="Fleet maintenance, logistics coordination, and repair parts for county vehicles based in Springfield.",
                naics_code="811111",
                source_key=self.source_key,
                adapter_status=MOCK_SOURCE,
            ),
            Opportunity(
                title="Statewide IT Help Desk Support",
                agency="State of Missouri Office of Administration",
                portal="MissouriBUYS Statewide Portal",
                location="Jefferson City, MO",
                due_date="2026-04-21",
                solicitation_type="Request for Proposal",
                source_type="mock",
                url="https://example.invalid/mock/missouribuys-help-desk",
                description="Help desk operations supporting field offices including Springfield.",
                naics_code="541513",
                source_key=self.source_key,
                adapter_status=MOCK_SOURCE,
            ),
            Opportunity(
                title="Southwest Region Groundskeeping Services",
                agency="State of Missouri Office of Administration",
                portal="MissouriBUYS Statewide Portal",
                location="Springfield, MO",
                due_date="2026-04-25",
                solicitation_type="Invitation for Bid",
                source_type="mock",
                url="https://example.invalid/mock/missouribuys-groundskeeping",
                description="Groundskeeping and landscaping contract covering Springfield-area properties.",
                naics_code="561730",
                source_key=self.source_key,
                adapter_status=MOCK_SOURCE,
            ),
        ]
        filtered = self._apply_filters(opportunities, keyword=keyword, state=state, location=location)
        report = self._base_report(
            adapter_status=MOCK_SOURCE,
            note="Bundled regional mock records for testing and offline development.",
            parsed_count=len(filtered),
        )
        return filtered, report


class CivicPlusBidAdapter(SourceAdapter):
    no_bid_marker = "There are no open bid postings at this time."

    def fetch(
        self,
        keyword: str | None = None,
        state: str | None = None,
        location: str | None = None,
    ) -> tuple[list[Opportunity], SourceReport]:
        try:
            html = self._fetch_page(self.source_url)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            return [], self._base_report(
                adapter_status=MANUAL_REVIEW_SOURCE,
                note=f"Live page could not be fetched automatically: {exc}",
            )

        if self.no_bid_marker in html:
            return [], self._base_report(
                adapter_status=WORKING_LIVE_SOURCE,
                note="Live source reachable; no open bid postings were listed at fetch time.",
            )

        opportunities = self._parse_civicplus_rows(html)
        filtered = self._apply_filters(opportunities, keyword=keyword, state=state, location=location)
        if filtered:
            report = self._base_report(
                adapter_status=WORKING_LIVE_SOURCE,
                note="Parsed live CivicPlus bid postings.",
                parsed_count=len(filtered),
            )
            return filtered, report

        return [], self._base_report(
            adapter_status=PARTIALLY_PARSED_SOURCE,
            note="Source page loaded, but no structured bid rows were extracted from the current HTML.",
        )

    def _parse_civicplus_rows(self, html: str) -> list[Opportunity]:
        opportunities: list[Opportunity] = []
        heading_matches = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', html, flags=re.IGNORECASE)
        for href, title in heading_matches:
            clean_title = unescape(re.sub(r"\s+", " ", title)).strip()
            if not clean_title or clean_title.lower() in {"sign up", "home"}:
                continue
            if len(clean_title) < 6:
                continue
            opportunities.append(
                Opportunity(
                    title=clean_title,
                    agency=self.agency,
                    portal=self.portal,
                    location=self.region,
                    due_date="",
                    solicitation_type="",
                    source_type="live",
                    url=self._absolute_url(href),
                    description="Live bid extracted from official CivicPlus page; detail parsing is still limited.",
                    source_key=self.source_key,
                    adapter_status=WORKING_LIVE_SOURCE,
                )
            )
        return opportunities[:10]

    def _absolute_url(self, href: str) -> str:
        if href.startswith("http"):
            return href
        return self.source_url.rsplit("/", 1)[0] + "/" + href.lstrip("/")


class SpringfieldAdapter(CivicPlusBidAdapter):
    source_key = "springfield_city"
    agency = "City of Springfield"
    portal = "City of Springfield Bid Portal"
    region = "Springfield, MO"
    source_url = "https://www.springfieldmo.gov/Bids.aspx"


class OzarkAdapter(CivicPlusBidAdapter):
    source_key = "ozark_city"
    agency = "City of Ozark"
    portal = "City of Ozark Bid Postings"
    region = "Ozark, MO"
    source_url = "https://www.ozarkmissouri.com/Bids.aspx"


class RepublicAdapter(CivicPlusBidAdapter):
    source_key = "republic_city"
    agency = "City of Republic"
    portal = "City of Republic Bid Postings"
    region = "Republic, MO"
    source_url = "https://www.republicmo.com/Bids.aspx"


class MissouriBuysAdapter(SourceAdapter):
    source_key = "missouribuys"
    agency = "State of Missouri Office of Administration"
    portal = "MissouriBUYS Statewide Portal"
    region = "Missouri statewide"
    source_url = "https://missouribuys.mo.gov/bid-board"

    def fetch(
        self,
        keyword: str | None = None,
        state: str | None = None,
        location: str | None = None,
    ) -> tuple[list[Opportunity], SourceReport]:
        del keyword, state, location
        try:
            html = self._fetch_page(self.source_url)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            return [], self._base_report(
                adapter_status=MANUAL_REVIEW_SOURCE,
                note=f"MissouriBUYS landing page could not be fetched automatically: {exc}",
            )

        note = (
            "Official MissouriBUYS bid board page loaded, but the public landing page only links into the new/legacy bid systems;"
            " individual solicitations are not exposed in static HTML for reliable parsing yet."
        )
        return [], self._base_report(adapter_status=PARTIALLY_PARSED_SOURCE, note=note)


class GreeneCountyAdapter(SourceAdapter):
    source_key = "greene_county"
    agency = "Greene County"
    portal = "Greene County Procurement"
    region = "Greene County, MO"
    source_url = "https://greenecountymo.gov/purchasing/bids.php"

    def fetch(
        self,
        keyword: str | None = None,
        state: str | None = None,
        location: str | None = None,
    ) -> tuple[list[Opportunity], SourceReport]:
        del keyword, state, location
        try:
            html = self._fetch_page(self.source_url)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            return [], self._base_report(
                adapter_status=MANUAL_REVIEW_SOURCE,
                note=f"Official Greene County bidding page could not be fetched automatically: {exc}",
            )

        if "beaconbid" in html.lower() or "vendor registry" in html.lower():
            return [], self._base_report(
                adapter_status=PARTIALLY_PARSED_SOURCE,
                note="Official Greene County page loaded and points to its bidding platform, but bid details were not extracted yet.",
            )

        return [], self._base_report(
            adapter_status=MANUAL_REVIEW_SOURCE,
            note="Greene County page loaded, but the current structure is unsupported for automatic parsing.",
        )


class ChristianCountyAdapter(SourceAdapter):
    source_key = "christian_county"
    agency = "Christian County"
    portal = "Christian County Purchasing"
    region = "Christian County, MO"
    source_url = "https://www.christiancountymo.gov/bidding-opportunities/"

    def fetch(
        self,
        keyword: str | None = None,
        state: str | None = None,
        location: str | None = None,
    ) -> tuple[list[Opportunity], SourceReport]:
        del keyword, state, location
        try:
            html = self._fetch_page(self.source_url)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            return [], self._base_report(
                adapter_status=MANUAL_REVIEW_SOURCE,
                note=f"Official Christian County purchasing page could not be fetched automatically: {exc}",
            )

        if "ionwave" in html.lower() or "electronic bidding" in html.lower():
            return [], self._base_report(
                adapter_status=PARTIALLY_PARSED_SOURCE,
                note="Official county purchasing page loaded and references the live bidding portal, but portal listings are not parsed yet.",
            )

        return [], self._base_report(
            adapter_status=MANUAL_REVIEW_SOURCE,
            note="Christian County page loaded, but bidding information could not be extracted reliably.",
        )


class NixaAdapter(SourceAdapter):
    source_key = "nixa_city"
    agency = "City of Nixa"
    portal = "City of Nixa Purchasing"
    region = "Nixa, MO"
    source_url = "https://www.nixa.com/services-programs/"

    def fetch(
        self,
        keyword: str | None = None,
        state: str | None = None,
        location: str | None = None,
    ) -> tuple[list[Opportunity], SourceReport]:
        del keyword, state, location
        try:
            html = self._fetch_page(self.source_url)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            return [], self._base_report(
                adapter_status=MANUAL_REVIEW_SOURCE,
                note=f"Official Nixa services page could not be fetched automatically: {exc}",
            )

        if "online bidding system" in html.lower() or "ionwave" in html.lower():
            return [], self._base_report(
                adapter_status=PARTIALLY_PARSED_SOURCE,
                note="Official Nixa page loaded and confirms an online bidding system, but active bid records are not exposed in the page HTML.",
            )

        return [], self._base_report(
            adapter_status=MANUAL_REVIEW_SOURCE,
            note="Nixa page loaded, but purchasing details were not located reliably in the current HTML.",
        )


class OpportunityScraper:
    def __init__(self, source: str = "mock") -> None:
        self.source = source

    def fetch_opportunities(
        self,
        limit: int = 10,
        keyword: str | None = None,
        state: str | None = None,
        location: str | None = None,
    ) -> dict[str, list[dict[str, object]] | list[Opportunity] | list[SourceReport]]:
        adapters: list[SourceAdapter] = []
        if self.source in {"mock", "all"}:
            adapters.append(MockRegionalAdapter())
        if self.source in {"live", "all"}:
            adapters.extend(
                [
                    SpringfieldAdapter(),
                    GreeneCountyAdapter(),
                    MissouriBuysAdapter(),
                    ChristianCountyAdapter(),
                    NixaAdapter(),
                    OzarkAdapter(),
                    RepublicAdapter(),
                ]
            )

        opportunities: list[Opportunity] = []
        source_reports: list[SourceReport] = []

        for adapter in adapters:
            adapter_opportunities, report = adapter.fetch(keyword=keyword, state=state, location=location)
            opportunities.extend(adapter_opportunities)
            source_reports.append(report)

        opportunities = opportunities[:limit]
        return {
            "opportunities": opportunities,
            "source_reports": source_reports,
        }
