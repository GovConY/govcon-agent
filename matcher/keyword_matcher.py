from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from scraper import Opportunity

TOKEN_PATTERN = re.compile(r"\b[a-z0-9]{3,}\b")


@dataclass(slots=True)
class SupplierProfile:
    name: str
    keywords: set[str]


class SupplierMatcher:
    def __init__(self, suppliers: Iterable[dict[str, object]]) -> None:
        self.suppliers = [
            SupplierProfile(
                name=str(supplier["name"]),
                keywords={keyword.lower() for keyword in supplier.get("keywords", [])},
            )
            for supplier in suppliers
        ]

    def match(self, opportunity: Opportunity) -> list[dict[str, object]]:
        opportunity_tokens = self._tokenize(
            f"{opportunity.title} {opportunity.description} {opportunity.naics_code} {opportunity.location}"
        )
        scored_matches = []

        for supplier in self.suppliers:
            hits = sorted(supplier.keywords.intersection(opportunity_tokens))
            if hits:
                scored_matches.append(
                    {
                        "supplier": supplier.name,
                        "score": len(hits),
                        "matched_keywords": hits,
                    }
                )

        return sorted(scored_matches, key=lambda item: (-int(item["score"]), str(item["supplier"])))

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        token_counts = Counter(TOKEN_PATTERN.findall(text.lower()))
        return {token for token, _count in token_counts.items()}
