from __future__ import annotations

from typing import Any

from gmip.intelligence.enums import IntelligenceType
from gmip.intelligence.intelligence_object import IntelligenceObject
from gmip.parsers.base_parser import BaseParser


class ExampleHydrogenParser(BaseParser):
    parser_name = "ExampleHydrogenParser"
    source_organisation = "Hydrogen Council"
    source_id = "hydrogen_council_test"
    default_intelligence_type = IntelligenceType.REPORT

    def can_parse(
        self,
        raw_record: dict[str, Any],
    ) -> bool:
        return bool(
            raw_record.get("title")
            and raw_record.get("url")
        )

    def parse(
        self,
        raw_record: dict[str, Any],
    ) -> list[IntelligenceObject]:
        combined_text = " ".join(
            [
                str(raw_record.get("title", "")),
                str(raw_record.get("summary", "")),
            ]
        )

        products = self.extract_keywords(
            combined_text,
            [
                "Green Hydrogen",
                "Green Ammonia",
                "Methanol",
            ],
        )

        intelligence_object = self.build_intelligence_object(
            title=raw_record["title"],
            source_url=raw_record["url"],
            summary=raw_record.get("summary"),
            published_at=raw_record.get("published_at"),
            collector_name="HydrogenCouncilCollector",
            products=products,
            countries=raw_record.get("countries"),
            companies=raw_record.get("companies"),
            keywords=[
                "hydrogen",
                "investment",
                "market report",
            ],
            metadata={
                "test_record": True,
            },
        )

        return [intelligence_object]


def test_base_parser() -> None:
    print("=" * 70)
    print("GMIP BASE PARSER TEST")
    print("=" * 70)

    parser = ExampleHydrogenParser(
        base_url="https://hydrogencouncil.com"
    )

    raw_record = {
        "title": (
            "  Hydrogen Council publishes "
            "<strong>Green Hydrogen</strong> report  "
        ),
        "url": "/en/intelligence/",
        "summary": (
            "The report examines green hydrogen "
            "and green ammonia investment."
        ),
        "published_at": "2026-07-24",
        "countries": [
            "Saudi Arabia",
            "Germany",
            "Saudi Arabia",
        ],
        "companies": [
            "ACWA Power",
            " ACWA Power ",
        ],
    }

    results = parser.parse_many(
        [raw_record],
        skip_invalid=False,
    )

    assert len(results) == 1

    intelligence_object = results[0]

    assert intelligence_object.title == (
        "Hydrogen Council publishes Green Hydrogen report"
    )

    assert intelligence_object.source_url == (
        "https://hydrogencouncil.com/en/intelligence/"
    )

    assert intelligence_object.parser_name == (
        "ExampleHydrogenParser"
    )

    assert intelligence_object.products == [
        "Green Ammonia",
        "Green Hydrogen",
    ]

    assert intelligence_object.countries == [
        "Germany",
        "Saudi Arabia",
    ]

    assert intelligence_object.companies == [
        "ACWA Power",
    ]

    print(intelligence_object.to_json())

    print("=" * 70)
    print("TEST PASSED")
    print(f"Parser: {intelligence_object.parser_name}")
    print(f"Title: {intelligence_object.title}")
    print(f"URL: {intelligence_object.source_url}")
    print("=" * 70)


if __name__ == "__main__":
    test_base_parser()