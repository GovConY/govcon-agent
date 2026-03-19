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

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "naics_code": self.naics_code,
            "location": self.location,
            "description": self.description,
            "solicitation_number": self.solicitation_number,
            "source": self.source,
        }


class OpportunityScraper:
    def __init__(self, source: str = "mock", api_key: str | None = None) -> None:
        self.source = source
        self.api_key = api_key or os.getenv("SAM_API_KEY")

    def fetch_opportunities(
        self,
        limit: int = 5,
        keyword: str | None = None,
        state: str | None = None,
    ) -> list[Opportunity]:
        if self.source == "sam" and self.api_key:
            try:
                opportunities = self._fetch_from_sam(limit=limit, keyword=keyword, state=state)
                if opportunities:
                    return opportunities
            except Exception:
                pass

        return self._fetch_mock(limit=limit, keyword=keyword, state=state)

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
        opportunities = []
        for notice in notices:
            opportunities.append(
                Opportunity(
                    title=notice.get("title") or notice.get("noticeTitle") or "Untitled opportunity",
                    naics_code=str(notice.get("naicsCode") or ""),
                    location=self._build_location(notice),
                    description=notice.get("description") or notice.get("summary") or "",
                    solicitation_number=notice.get("solicitationNumber") or "",
                    source="sam",
                )
            )
        return opportunities

    def _fetch_mock(
        self,
        limit: int,
        keyword: str | None,
        state: str | None,
    ) -> list[Opportunity]:
        opportunities = [
            Opportunity(
                title="Cloud Hosting Modernization Support",
                naics_code="541512",
                location="Washington, DC",
                description="Migration of legacy systems to a secure cloud environment with cybersecurity controls.",
                solicitation_number="MOCK-001",
            ),
            Opportunity(
                title="Medical Supply Distribution Services",
                naics_code="423450",
                location="San Diego, CA",
                description="Provide warehousing and distribution of laboratory and medical consumables to regional clinics.",
                solicitation_number="MOCK-002",
            ),
            Opportunity(
                title="Federal Building Renovation Project",
                naics_code="236220",
                location="Denver, CO",
                description="Renovation and facility maintenance for a federal office building, including engineering support.",
                solicitation_number="MOCK-003",
            ),
            Opportunity(
                title="Freight and Logistics Coordination",
                naics_code="488510",
                location="Norfolk, VA",
                description="Coordinate freight movement, shipment tracking, and warehouse routing for defense cargo.",
                solicitation_number="MOCK-004",
            ),
            Opportunity(
                title="Data Analytics Platform Integration",
                naics_code="541511",
                location="Austin, TX",
                description="Implement data pipelines, dashboarding, and software integration for agency reporting systems.",
                solicitation_number="MOCK-005",
            ),
        ]

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
            filtered = [item for item in filtered if item.location.endswith(state_upper)]

        return filtered[:limit]

    @staticmethod
    def _build_location(notice: dict[str, Any]) -> str:
        city = notice.get("placeOfPerformanceCity") or notice.get("city") or ""
        state = notice.get("placeOfPerformanceState") or notice.get("state") or ""
        if city and state:
            return f"{city}, {state}"
        return city or state or ""
