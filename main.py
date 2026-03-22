from __future__ import annotations

import argparse
import json
from collections import defaultdict
from typing import Any

from matcher import SupplierMatcher
from scraper import (
    MANUAL_REVIEW_SOURCE,
    MOCK_SOURCE,
    PARTIALLY_PARSED_SOURCE,
    WORKING_LIVE_SOURCE,
    OpportunityScraper,
)

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

STATUS_ORDER = [
    WORKING_LIVE_SOURCE,
    PARTIALLY_PARSED_SOURCE,
    MANUAL_REVIEW_SOURCE,
    MOCK_SOURCE,
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect regional procurement opportunities for Springfield, Missouri and nearby official public sources."
    )
    parser.add_argument(
        "--source",
        choices=["mock", "live", "all"],
        default="mock",
        help="Use bundled mock data, live official source adapters, or both.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of opportunity rows to return.",
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
        help="Optional keyword filter applied to titles and descriptions.",
    )
    parser.add_argument(
        "--state",
        default=None,
        help="Optional state filter, such as MO.",
    )
    parser.add_argument(
        "--location",
        default=None,
        help="Optional city/county/location filter such as Springfield or Greene County.",
    )
    return parser


def enrich_results(
    source: str,
    limit: int,
    keyword: str | None,
    state: str | None,
    location: str | None,
) -> dict[str, list[dict[str, Any]]]:
    scraper = OpportunityScraper(source=source)
    matcher = SupplierMatcher(DEFAULT_SUPPLIERS)
    raw_results = scraper.fetch_opportunities(limit=limit, keyword=keyword, state=state, location=location)

    opportunities = []
    for opportunity in raw_results["opportunities"]:
        opportunity_dict = opportunity.to_dict()
        opportunity_dict["supplier_matches"] = matcher.match(opportunity)
        opportunities.append(opportunity_dict)

    source_reports = [report.to_dict() for report in raw_results["source_reports"]]
    return {
        "opportunities": opportunities,
        "source_reports": source_reports,
    }


def render_table(rows: list[list[str]], headers: list[str]) -> str:
    column_widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            column_widths[index] = max(column_widths[index], len(str(value)))

    def format_row(row: list[str]) -> str:
        return " | ".join(str(value).ljust(column_widths[index]) for index, value in enumerate(row))

    separator = "-+-".join("-" * width for width in column_widths)
    lines = [format_row(headers), separator]
    lines.extend(format_row(row) for row in rows)
    return "\n".join(lines)


def render_source_report_table(source_reports: list[dict[str, Any]]) -> str:
    grouped_reports: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for report in source_reports:
        grouped_reports[str(report["adapter_status"])].append(report)

    sections = []
    for status in STATUS_ORDER:
        reports = grouped_reports.get(status, [])
        if not reports:
            continue

        rows = [
            [
                report["agency"],
                report["portal"],
                report["region"],
                str(report["parsed_count"]),
                report["note"],
                report["source_url"],
            ]
            for report in reports
        ]
        headers = ["Agency", "Portal", "Region", "Rows", "Notes", "URL"]
        sections.append(status.upper())
        sections.append(render_table(rows, headers))

    return "\n\n".join(sections)


def render_opportunity_table(opportunities: list[dict[str, Any]]) -> str:
    headers = ["Title", "Agency", "Portal", "Location", "Due Date", "Solicitation Type", "Source Type", "URL"]
    rows = [
        [
            item["title"],
            item["agency"],
            item["portal"],
            item["location"] or "N/A",
            item["due_date"] or "N/A",
            item["solicitation_type"] or "N/A",
            item["source_type"],
            item["url"] or "N/A",
        ]
        for item in opportunities
    ]

    if not rows:
        rows = [["No opportunities found", "", "", "", "", "", "", ""]]

    return render_table(rows, headers)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    results = enrich_results(
        source=args.source,
        limit=args.limit,
        keyword=args.keyword,
        state=args.state,
        location=args.location,
    )

    if args.output == "json":
        print(json.dumps(results, indent=2))
        return

    print("SOURCE ADAPTER STATUS")
    print(render_source_report_table(results["source_reports"]))
    print()
    print("OPPORTUNITY RESULTS")
    print(render_opportunity_table(results["opportunities"]))


if __name__ == "__main__":
    main()
