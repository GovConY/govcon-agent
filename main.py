from __future__ import annotations

import argparse
import json
from typing import Any

from matcher import SupplierMatcher
from scraper import OpportunityScraper

DEFAULT_SUPPLIERS = [
    {
        "name": "Acme Cloud Solutions",
        "keywords": ["cloud", "software", "cybersecurity", "data", "network", "it", "support"],
    },
    {
        "name": "Patriot Construction Group",
        "keywords": ["construction", "facility", "renovation", "maintenance", "engineering", "public works"],
    },
    {
        "name": "BlueWave Medical Supply",
        "keywords": ["medical", "healthcare", "pharmaceutical", "laboratory", "clinic"],
    },
    {
        "name": "Liberty Logistics",
        "keywords": ["logistics", "transportation", "shipping", "warehouse", "freight", "fleet"],
    },
    {
        "name": "Ozark Civic Services",
        "keywords": ["janitorial", "grounds", "custodial", "landscaping", "building", "parks"],
    },
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape contract opportunities and match them to potential suppliers."
    )
    parser.add_argument(
        "--source",
        choices=["sam", "mock"],
        default="mock",
        help="Use live SAM.gov API data or bundled mock data.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of opportunities to retrieve.",
    )
    parser.add_argument(
        "--output",
        choices=["table", "json"],
        default="table",
        help="Output format.",
    )
    parser.add_argument(
        "--keyword",
        default=None,
        help="Optional keyword to pass through to the scraper.",
    )
    parser.add_argument(
        "--state",
        default=None,
        help="Optional two-letter state filter for SAM.gov requests or mock records.",
    )
    parser.add_argument(
        "--location",
        default=None,
        help="Optional city/county/location text filter such as 'Springfield' or 'Greene County'.",
    )
    return parser


def enrich_opportunities(
    source: str,
    limit: int,
    keyword: str | None,
    state: str | None,
    location: str | None,
) -> list[dict[str, Any]]:
    scraper = OpportunityScraper(source=source)
    matcher = SupplierMatcher(DEFAULT_SUPPLIERS)

    opportunities = scraper.fetch_opportunities(
        limit=limit,
        keyword=keyword,
        state=state,
        location=location,
    )
    results = []

    for opportunity in opportunities:
        opportunity_dict = opportunity.to_dict()
        opportunity_dict["supplier_matches"] = matcher.match(opportunity)
        results.append(opportunity_dict)

    return results


def render_table(results: list[dict[str, Any]]) -> str:
    headers = ["Title", "Portal", "NAICS", "Location", "Top Suppliers"]
    rows = []

    for item in results:
        supplier_names = ", ".join(match["supplier"] for match in item["supplier_matches"][:2]) or "No match"
        rows.append(
            [
                item["title"],
                item.get("source_portal") or item.get("source") or "N/A",
                item["naics_code"] or "N/A",
                item["location"] or "N/A",
                supplier_names,
            ]
        )

    column_widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            column_widths[index] = max(column_widths[index], len(str(value)))

    def format_row(row: list[str]) -> str:
        return " | ".join(str(value).ljust(column_widths[index]) for index, value in enumerate(row))

    separator = "-+-".join("-" * width for width in column_widths)
    table_lines = [format_row(headers), separator]

    if not rows:
        table_lines.append("No opportunities found for the selected filters.")
    else:
        table_lines.extend(format_row(row) for row in rows)

    return "\n".join(table_lines)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    results = enrich_opportunities(
        source=args.source,
        limit=args.limit,
        keyword=args.keyword,
        state=args.state,
        location=args.location,
    )

    if args.output == "json":
        print(json.dumps(results, indent=2))
    else:
        print(render_table(results))


if __name__ == "__main__":
    main()
