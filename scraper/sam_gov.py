from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

SAM_GOV_ENDPOINT = "https://api.sam.gov/prod/opportunities/v2/search"
DEFAULT_TIMEOUT = 20


@dataclass(slots=True)
class Opportunity:
    title: str
    naics_code: str
    location: str
    description: str
    solicitation_number: str = ""
    source: str = "mock"
    source_portal: str = "Mock Portal"

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "naics_code": self.naics_code,
            "location": self.location,
            "description": self.description,
            "solicitation_number": self.solicitation_number,
            "source": self.source,
            "source_portal": self.source_portal,
        }


class OpportunityScraper:
    def __init__(self, source: str = "mock", api_key: str | None = None) -> None:
        self.source = source
        self.api_key = api_key or os.getenv("SAM_API_KEY")

    def fetch_opportunities(
        self,
        limit: int = 10,
        keyword: str | None = None,
        state: str | None = None,
        location: str | None = None,
    ) -> list[Opportunity]:
        if self.source == "sam" and self.api_key:
            try:
                opportunities = self._fetch_from_sam(limit=limit, keyword=keyword, state=state)
                if opportunities:
                    return self._apply_filters(opportunities, keyword=keyword, state=state, location=location)
            except Exception:
                pass

        mock_opportunities = self._mock_opportunities()
        filtered = self._apply_filters(mock_opportunities, keyword=keyword, state=state, location=location)
        return filtered[:limit]

    def _fetch_from_sam(
        self,
        limit: int,
        keyword: str | None,
        state: str | None,
    ) -> list[Opportunity]:
        params = {
            "api_key": self.api_key,
            "limit": limit,
            "postedFrom": "01/01/2024",
        }
        if keyword:
            params["keyword"] = keyword
        if state:
            params["state"] = state

        import requests

        response = requests.get(SAM_GOV_ENDPOINT, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        payload = response.json()

        notices = payload.get("opportunitiesData", [])
        return [
            Opportunity(
                title=notice.get("title") or notice.get("noticeTitle") or "Untitled opportunity",
                naics_code=str(notice.get("naicsCode") or ""),
                location=self._build_location(notice),
                description=notice.get("description") or notice.get("summary") or "",
                solicitation_number=notice.get("solicitationNumber") or "",
                source="sam",
                source_portal="SAM.gov",
            )
            for notice in notices
        ]

    def _mock_opportunities(self) -> list[Opportunity]:
        return [
            Opportunity(
                title="City Utilities Network Hardware Refresh",
                naics_code="334111",
                location="Springfield, MO",
                description="City of Springfield utility division seeks switches, network monitoring, and installation support.",
                solicitation_number="SGF-001",
                source_portal="City of Springfield Bid Portal",
            ),
            Opportunity(
                title="Downtown Signal and Streetlight Maintenance",
                naics_code="238210",
                location="Springfield, MO",
                description="Springfield public works bid for electrical maintenance, signal cabinet upgrades, and field engineering.",
                solicitation_number="SGF-002",
                source_portal="City of Springfield Bid Portal",
            ),
            Opportunity(
                title="Greene County Fleet Parts and Service",
                naics_code="811111",
                location="Greene County, MO",
                description="Greene County seeks fleet maintenance, logistics coordination, and repair parts for county vehicles based in Springfield.",
                solicitation_number="GC-001",
                source_portal="Greene County Procurement",
            ),
            Opportunity(
                title="Greene County Justice Center Janitorial Services",
                naics_code="561720",
                location="Greene County, MO",
                description="Custodial and building cleaning services for county justice facilities in the Springfield area.",
                solicitation_number="GC-002",
                source_portal="Greene County Procurement",
            ),
            Opportunity(
                title="Missouri Statewide IT Help Desk Support",
                naics_code="541513",
                location="Jefferson City, MO",
                description="Missouri statewide portal opportunity for help desk operations supporting field offices including Springfield.",
                solicitation_number="MO-001",
                source_portal="MissouriBUYS Statewide Portal",
            ),
            Opportunity(
                title="Missouri Parks Groundskeeping - Southwest Region",
                naics_code="561730",
                location="Springfield, MO",
                description="Statewide groundskeeping and landscaping contract covering Springfield-area park properties.",
                solicitation_number="MO-002",
                source_portal="MissouriBUYS Statewide Portal",
            ),
            Opportunity(
                title="Cloud Hosting Modernization Support",
                naics_code="541512",
                location="Washington, DC",
                description="Migration of legacy systems to a secure cloud environment with cybersecurity controls.",
                solicitation_number="MOCK-001",
                source_portal="Federal Mock Portal",
            ),
            Opportunity(
                title="Medical Supply Distribution Services",
                naics_code="423450",
                location="San Diego, CA",
                description="Provide warehousing and distribution of laboratory and medical consumables to regional clinics.",
                solicitation_number="MOCK-002",
                source_portal="Federal Mock Portal",
            ),
        ]

    def _apply_filters(
        self,
        opportunities: list[Opportunity],
        keyword: str | None,
        state: str | None,
        location: str | None,
    ) -> list[Opportunity]:
        filtered = opportunities

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
                or location_lower in item.description.lower()
                or location_lower in item.source_portal.lower()
            ]

        return filtered

    @staticmethod
    def _build_location(notice: dict[str, Any]) -> str:
        city = notice.get("placeOfPerformanceCity") or notice.get("city") or ""
        state = notice.get("placeOfPerformanceState") or notice.get("state") or ""
        if city and state:
            return f"{city}, {state}"
        return city or state or ""
