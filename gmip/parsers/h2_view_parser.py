from __future__ import annotations

from typing import Any

from gmip.intelligence.enums import ConfidenceLevel, IntelligenceType
from gmip.intelligence.intelligence_object import IntelligenceObject
from gmip.parsers.base_parser import BaseParser

# Deliberately conservative and small: RSS summaries are short, so only
# match well-known green-molecule products and major countries/companies
# that appear in GMIP's own vision doc. Anything not matched here is left
# out rather than guessed at.
PRODUCT_CANDIDATES = [
    "Green Hydrogen",
    "Green Ammonia",
    "Blue Hydrogen",
    "Blue Ammonia",
    "Renewable Methanol",
    "e-Methanol",
    "RFNBO",
    "Sustainable Aviation Fuel",
]

COUNTRY_CANDIDATES = [
    "Saudi Arabia",
    "Germany",
    "Australia",
    "Oman",
    "Egypt",
    "Morocco",
    "Netherlands",
    "United States",
    "United Kingdom",
    "India",
    "Japan",
    "South Korea",
    "Namibia",
    "Chile",
    "Spain",
]

COMPANY_CANDIDATES = [
    "ACWA Power",
    "Air Products",
    "ADNOC",
    "Aramco",
    "Masdar",
    "Fortescue",
    "Iberdrola",
    "TotalEnergies",
    "BP",
    "Shell",
    "Yara",
    "Fertiglobe",
    "Plug Power",
    "Nel",
    "thyssenkrupp nucera",
    "Siemens Energy",
    "Cummins",
]


class H2ViewParser(BaseParser):
    """
    Conservative first new-media parser (Section 20 of the phase brief).

    Extracts only what an RSS summary reliably provides. Does not infer or
    fabricate structured facts (capacity, CAPEX, FID, etc.) that a short
    feed summary cannot actually support.
    """

    parser_name = "H2ViewParser"
    source_organisation = "H2 View"
    source_id = "h2_view"
    default_intelligence_type = IntelligenceType.NEWS

    def can_parse(self, raw_record: dict[str, Any]) -> bool:
        return bool(
            raw_record.get("title") and raw_record.get("source_url")
        )

    def parse(
        self,
        raw_record: dict[str, Any],
    ) -> list[IntelligenceObject]:
        combined_text = " ".join(
            [
                str(raw_record.get("title", "")),
                str(raw_record.get("text", "") or ""),
            ]
        )

        products = self.extract_keywords(
            combined_text,
            PRODUCT_CANDIDATES,
        )

        countries = self.extract_keywords(
            combined_text,
            COUNTRY_CANDIDATES,
        )

        companies = self.extract_keywords(
            combined_text,
            COMPANY_CANDIDATES,
        )

        categories = raw_record.get("metadata", {}).get("categories") or []

        intelligence_object = self.build_intelligence_object(
            title=raw_record["title"],
            source_url=raw_record["source_url"],
            summary=raw_record.get("text"),
            published_at=raw_record.get("published_at"),
            collector_name="H2ViewCollector",
            confidence=ConfidenceLevel.MEDIUM,
            products=products,
            countries=countries,
            companies=companies,
            categories=categories,
            metadata={"discovery_source": True},
        )

        return [intelligence_object]
