from __future__ import annotations

import argparse
import re
import json
from collections import defaultdict
from html import unescape
from typing import Any

from matcher import SupplierMatcher
from scraper import (
    MANUAL_REVIEW_SOURCE,
    MOCK_SOURCE,
    PARTIALLY_PARSED_SOURCE,
    WORKING_LIVE_SOURCE,
    OpportunityScraper,
)
from scraper.models import Opportunity

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

SCRIPT_PATTERN = re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
STYLE_PATTERN = re.compile(r"<style\b[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
TAG_PATTERN = re.compile(r"<[^>]+>")
WHITESPACE_PATTERN = re.compile(r"\s+")
BOILERPLATE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bskip to main content\b",
        r"\bcreate a website account\b",
        r"\bwebsite account\b",
        r"\bsign in\b",
        r"\bsign up\b",
        r"\bloading\b",
        r"\bpowered by civicplus\b",
        r"\bcopyright\b",
        r"\ball rights reserved\b",
        r"\bjavascript\b",
        r"\bhome\b",
        r"\bgovernment\b",
        r"\bdepartments\b",
        r"\bfooter\b",
        r"\bsite map\b",
        r"\bprivacy policy\b",
        r"\bcontact us\b",
    ]
]
COMPACT_OPPORTUNITY_FIELDS = [
    "title",
    "agency",
    "portal",
    "location",
    "due_date",
    "solicitation_type",
    "source_type",
    "url",
    "match_score",
    "tier",
    "score_reasons",
    "supplier_matches",
]
SCORING_WEIGHTS = {
    "keyword_title": 10,
    "keyword_solicitation_type": 5,
    "keyword_description": 3,
    "title_airport": 12,
    "title_construction": 10,
    "title_landscape": 6,
    "title_janitorial": 6,
    "title_maintenance": 5,
    "naics_exact": 15,
    "naics_prefix": 8,
    "location_springfield": 8,
    "location_greene_county": 6,
    "location_secondary_city": 4,
    "solicitation_ifb": 5,
    "solicitation_rfq": 4,
    "solicitation_rfp": 3,
    "adapter_working_live": 5,
    "adapter_partially_parsed": 2,
}


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
        "--top",
        type=int,
        default=None,
        help="After scoring and sorting, return only the top N opportunities.",
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
    parser.add_argument(
        "--naics",
        default=None,
        help="Optional comma-separated NAICS code filter, such as 236220 or 236220,237310.",
    )
    parser.add_argument(
        "--compact-json",
        action="store_true",
        help="When used with --output json, return compact opportunity rows without debug-only fields.",
    )
    return parser


def enrich_results(
    source: str,
    limit: int,
    top: int | None,
    keyword: str | None,
    state: str | None,
    location: str | None,
    naics_codes: set[str] | None = None,
    compact_json: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    scraper = OpportunityScraper(source=source)
    matcher = SupplierMatcher(DEFAULT_SUPPLIERS)
    raw_results = scraper.fetch_opportunities(
        limit=limit,
        keyword=keyword,
        state=state,
        location=location,
        naics_codes=naics_codes,
    )

    opportunities = []
    for opportunity in raw_results["opportunities"]:
        normalized_opportunity = _clean_output_opportunity(opportunity)
        scored_opportunity = _score_opportunity(
            normalized_opportunity,
            keyword=keyword,
            naics_codes=naics_codes,
        )
        opportunity_dict = scored_opportunity.to_dict()
        opportunity_dict["supplier_matches"] = matcher.match(scored_opportunity)
        if compact_json:
            opportunity_dict = {field: opportunity_dict[field] for field in COMPACT_OPPORTUNITY_FIELDS}
        opportunities.append(opportunity_dict)

    opportunities.sort(key=lambda item: (-int(item["match_score"]), str(item["title"])))
    final_count = top if top is not None else limit
    opportunities = opportunities[:final_count]

    source_reports = [report.to_dict() for report in raw_results["source_reports"]]
    return {
        "opportunities": opportunities,
        "source_reports": source_reports,
    }


def _clean_output_opportunity(opportunity: Opportunity) -> Opportunity:
    description = opportunity.description
    if opportunity.source_type == "live":
        description = _clean_live_description(description)

    return Opportunity(
        title=opportunity.title,
        agency=opportunity.agency,
        portal=opportunity.portal,
        location=opportunity.location,
        due_date=opportunity.due_date,
        solicitation_type=opportunity.solicitation_type,
        source_type=opportunity.source_type,
        url=opportunity.url,
        description=description,
        naics_code=opportunity.naics_code,
        source_key=opportunity.source_key,
        adapter_status=opportunity.adapter_status,
        match_score=opportunity.match_score,
        score_reasons=list(opportunity.score_reasons or []),
        tier=opportunity.tier,
    )


def _clean_live_description(description: str) -> str:
    if not description:
        return ""

    text = SCRIPT_PATTERN.sub(" ", description)
    text = STYLE_PATTERN.sub(" ", text)
    text = TAG_PATTERN.sub(" ", text)
    text = unescape(text)
    text = text.replace("\r", "\n")

    cleaned_lines: list[str] = []
    for raw_line in text.splitlines():
        line = WHITESPACE_PATTERN.sub(" ", raw_line).strip()
        if not line:
            continue
        if any(pattern.search(line) for pattern in BOILERPLATE_PATTERNS):
            continue
        cleaned_lines.append(line)

    cleaned_text = " ".join(cleaned_lines)
    cleaned_text = WHITESPACE_PATTERN.sub(" ", cleaned_text).strip()
    return cleaned_text


def _parse_naics_codes(raw_value: str | None) -> set[str] | None:
    if not raw_value:
        return None

    codes = {part.strip() for part in raw_value.split(",") if part.strip()}
    return codes or None


def _score_opportunity(
    opportunity: Opportunity,
    keyword: str | None,
    naics_codes: set[str] | None,
) -> Opportunity:
    score = 0
    reasons: list[str] = []

    keyword_lower = (keyword or "").strip().lower()
    if keyword_lower:
        if keyword_lower in opportunity.title.lower():
            score += SCORING_WEIGHTS["keyword_title"]
            reasons.append(f'keyword match in title (+{SCORING_WEIGHTS["keyword_title"]})')
        if keyword_lower in opportunity.solicitation_type.lower():
            score += SCORING_WEIGHTS["keyword_solicitation_type"]
            reasons.append(
                f'keyword match in solicitation type (+{SCORING_WEIGHTS["keyword_solicitation_type"]})'
            )
        if keyword_lower in opportunity.description.lower():
            score += SCORING_WEIGHTS["keyword_description"]
            reasons.append(f'keyword match in description (+{SCORING_WEIGHTS["keyword_description"]})')

    title_lower = opportunity.title.lower()
    title_boosts = [
        ("airport", "title_airport", "airport contract profile"),
        ("construction", "title_construction", "construction contract profile"),
        ("landscape", "title_landscape", "landscape contract profile"),
        ("janitorial", "title_janitorial", "janitorial contract profile"),
        ("maintenance", "title_maintenance", "maintenance contract profile"),
    ]
    for needle, weight_key, label in title_boosts:
        if needle in title_lower:
            score += SCORING_WEIGHTS[weight_key]
            reasons.append(f'{label} (+{SCORING_WEIGHTS[weight_key]})')

    if naics_codes and opportunity.naics_code:
        if opportunity.naics_code in naics_codes:
            score += SCORING_WEIGHTS["naics_exact"]
            reasons.append(f'exact NAICS match ({opportunity.naics_code}) (+{SCORING_WEIGHTS["naics_exact"]})')
        else:
            best_prefix_length = _best_naics_prefix_length(opportunity.naics_code, naics_codes)
            if best_prefix_length > 0:
                score += SCORING_WEIGHTS["naics_prefix"]
                reasons.append(
                    f'NAICS prefix match ({opportunity.naics_code[:best_prefix_length]}) '
                    f'(+{SCORING_WEIGHTS["naics_prefix"]})'
                )

    location_lower = opportunity.location.lower()
    if "springfield" in location_lower:
        score += SCORING_WEIGHTS["location_springfield"]
        reasons.append(f'Springfield location relevance (+{SCORING_WEIGHTS["location_springfield"]})')
    elif "greene county" in location_lower:
        score += SCORING_WEIGHTS["location_greene_county"]
        reasons.append(f'Greene County location relevance (+{SCORING_WEIGHTS["location_greene_county"]})')
    elif any(city in location_lower for city in ("ozark", "republic", "nixa")):
        score += SCORING_WEIGHTS["location_secondary_city"]
        reasons.append(f'Ozark/Republic/Nixa location relevance (+{SCORING_WEIGHTS["location_secondary_city"]})')

    solicitation_lower = opportunity.solicitation_type.lower()
    if "ifb" in solicitation_lower or "invitation for bid" in solicitation_lower:
        score += SCORING_WEIGHTS["solicitation_ifb"]
        reasons.append(f'IFB solicitation relevance (+{SCORING_WEIGHTS["solicitation_ifb"]})')
    elif (
        "rfq" in solicitation_lower
        or "request for qualifications" in solicitation_lower
        or "request for quote" in solicitation_lower
    ):
        score += SCORING_WEIGHTS["solicitation_rfq"]
        reasons.append(f'RFQ solicitation relevance (+{SCORING_WEIGHTS["solicitation_rfq"]})')
    elif "rfp" in solicitation_lower or "request for proposal" in solicitation_lower:
        score += SCORING_WEIGHTS["solicitation_rfp"]
        reasons.append(f'RFP solicitation relevance (+{SCORING_WEIGHTS["solicitation_rfp"]})')

    if opportunity.adapter_status == WORKING_LIVE_SOURCE:
        score += SCORING_WEIGHTS["adapter_working_live"]
        reasons.append(f'working live source confidence (+{SCORING_WEIGHTS["adapter_working_live"]})')
    elif opportunity.adapter_status == PARTIALLY_PARSED_SOURCE:
        score += SCORING_WEIGHTS["adapter_partially_parsed"]
        reasons.append(f'partially parsed source confidence (+{SCORING_WEIGHTS["adapter_partially_parsed"]})')

    score = min(score, 50)

    return Opportunity(
        title=opportunity.title,
        agency=opportunity.agency,
        portal=opportunity.portal,
        location=opportunity.location,
        due_date=opportunity.due_date,
        solicitation_type=opportunity.solicitation_type,
        source_type=opportunity.source_type,
        url=opportunity.url,
        description=opportunity.description,
        naics_code=opportunity.naics_code,
        source_key=opportunity.source_key,
        adapter_status=opportunity.adapter_status,
        match_score=score,
        score_reasons=reasons,
        tier=_classify_tier(score),
    )


def _best_naics_prefix_length(naics_code: str, requested_codes: set[str]) -> int:
    best = 0
    for requested in requested_codes:
        max_length = min(len(naics_code), len(requested))
        current = 0
        while current < max_length and naics_code[current] == requested[current]:
            current += 1
        if current > best:
            best = current
    return best if best >= 2 else 0


def _classify_tier(score: int) -> str:
    if score >= 30:
        return "HIGH PRIORITY"
    if score >= 20:
        return "MEDIUM PRIORITY"
    return "LOW PRIORITY"


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
    headers = [
        "Title",
        "Agency",
        "Portal",
        "Location",
        "Due Date",
        "Solicitation Type",
        "Tier",
        "Source Type",
        "URL",
    ]
    rows = [
        [
            item["title"],
            item["agency"],
            item["portal"],
            item["location"] or "N/A",
            item["due_date"] or "N/A",
            item["solicitation_type"] or "N/A",
            item["tier"],
            item["source_type"],
            item["url"] or "N/A",
        ]
        for item in opportunities
    ]

    if not rows:
        rows = [["No opportunities found", "", "", "", "", "", "", "", ""]]

    return render_table(rows, headers)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    naics_codes = _parse_naics_codes(args.naics)

    results = enrich_results(
        source=args.source,
        limit=args.limit,
        top=args.top,
        keyword=args.keyword,
        state=args.state,
        location=args.location,
        naics_codes=naics_codes,
        compact_json=args.compact_json,
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
