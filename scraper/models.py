from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Opportunity:
    title: str
    agency: str
    portal: str
    location: str
    due_date: str
    solicitation_type: str
    source_type: str
    url: str
    description: str = ""
    naics_code: str = ""
    source_key: str = ""
    adapter_status: str = ""
    match_score: int = 0
    score_reasons: list[str] | None = None
    tier: str = "LOW PRIORITY"

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "agency": self.agency,
            "portal": self.portal,
            "location": self.location,
            "due_date": self.due_date,
            "solicitation_type": self.solicitation_type,
            "source_type": self.source_type,
            "url": self.url,
            "description": self.description,
            "naics_code": self.naics_code,
            "source_key": self.source_key,
            "adapter_status": self.adapter_status,
            "match_score": self.match_score,
            "score_reasons": self.score_reasons or [],
            "tier": self.tier,
        }


@dataclass(slots=True)
class SourceReport:
    source_key: str
    agency: str
    portal: str
    region: str
    source_type: str
    adapter_status: str
    source_url: str
    note: str
    parsed_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_key": self.source_key,
            "agency": self.agency,
            "portal": self.portal,
            "region": self.region,
            "source_type": self.source_type,
            "adapter_status": self.adapter_status,
            "source_url": self.source_url,
            "note": self.note,
            "parsed_count": self.parsed_count,
        }
