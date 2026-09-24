from __future__ import annotations

import re
from typing import Any

from dateutil import parser as date_parser

from gmip.intelligence.enums import EventType, IntelligenceType
from gmip.intelligence.intelligence_object import (
    EventReference,
    IntelligenceObject,
)
from gmip.parsers.base_parser import BaseParser

# Each Hydrogen Council source family lists its content as repeated
# "<Category> <Month Day, Year> <Title...> <Summary...> Read More" cards.
# Category values come directly from each page's own "Filter by:" facets
# (confirmed against real captured pages under Data/Raw/), sorted longest
# name first so e.g. "Media Release" matches before a shorter overlapping
# alternative would.
FAMILY_CATEGORIES: dict[str, list[str]] = {
    "hydrogen_council_intelligence": ["Report", "Podcast", "Paper"],
    "hydrogen_council_newsroom": [
        "Media Release",
        "Council Updates",
        "In the News",
        "Meet the Members",
    ],
    "hydrogen_council_hydrogen_in_action": [
        "Thought Leadership",
        "Industry Trends",
        "Social Content",
        "Case Study",
        "Hydrogen News",
        "Events",
        "Members",
        "Reports",
    ],
}

# Pages with no repeating card structure in the captured text (logos/JS
# member grids, a simple corporate homepage) — parsed as one whole-page
# object instead of inventing card structure that isn't there.
WHOLE_PAGE_SOURCE_IDS = {
    "hydrogen_council_home",
    "hydrogen_council_members",
}

CATEGORY_TO_INTELLIGENCE_TYPE: dict[str, IntelligenceType] = {
    "Report": IntelligenceType.REPORT,
    "Paper": IntelligenceType.REPORT,
    "Podcast": IntelligenceType.REPORT,
    "Reports": IntelligenceType.REPORT,
    "Media Release": IntelligenceType.NEWS,
    "In the News": IntelligenceType.NEWS,
    "Council Updates": IntelligenceType.NEWS,
    "Meet the Members": IntelligenceType.MEMBER_UPDATE,
    "Case Study": IntelligenceType.NEWS,
    "Hydrogen News": IntelligenceType.NEWS,
    "Industry Trends": IntelligenceType.NEWS,
    "Social Content": IntelligenceType.NEWS,
    "Thought Leadership": IntelligenceType.NEWS,
    "Events": IntelligenceType.OTHER,
    "Members": IntelligenceType.MEMBER_UPDATE,
}

REPORT_LIKE_CATEGORIES = {"Report", "Paper", "Podcast", "Reports"}

MONTH_NAMES = (
    r"January|February|March|April|May|June|July|August|"
    r"September|October|November|December"
)
DATE_PATTERN = rf"(?:{MONTH_NAMES})\s+\d{{1,2}},\s+\d{{4}}"

PRODUCT_CANDIDATES = [
    "Green Hydrogen",
    "Green Ammonia",
    "Blue Hydrogen",
    "Blue Ammonia",
    "Renewable Methanol",
    "e-Methanol",
    "RFNBO",
    "Electrolysis",
    "Fuel Cells",
]

COUNTRY_CANDIDATES = [
    "Saudi Arabia", "Germany", "Australia", "Oman", "Egypt", "Morocco",
    "Netherlands", "United States", "United Kingdom", "India", "Japan",
    "South Korea", "Namibia", "Chile", "Spain", "Africa",
]

COMPANY_CANDIDATES = [
    "ACWA Power", "Air Products", "ADNOC", "Aramco", "Masdar",
    "Fortescue", "Iberdrola", "TotalEnergies", "BP", "Shell", "Yara",
    "Fertiglobe", "Baker Hughes",
]


class HydrogenCouncilParser(BaseParser):
    """
    Structured parser for the Hydrogen Council's card-listing pages
    (Intelligence, Newsroom, Hydrogen in Action).

    Unlike the legacy classifier, this does not reuse Hintco's tender
    vocabulary — Hydrogen Council content is strategic/market
    intelligence, not procurement, so it gets its own category model
    (built from each page's own real "Filter by:" facets) and its own
    IntelligenceType/EventType mapping.
    """

    parser_name = "HydrogenCouncilParser"
    source_organisation = "Hydrogen Council"
    source_id = "hydrogen_council"
    default_intelligence_type = IntelligenceType.NEWS

    def can_parse(self, raw_record: dict[str, Any]) -> bool:
        return bool(
            raw_record.get("title") and raw_record.get("source_url")
        )

    def parse(
        self,
        raw_record: dict[str, Any],
    ) -> list[IntelligenceObject]:
        page_source_id = raw_record.get("source_id", "")
        text = raw_record.get("text") or ""

        if page_source_id in WHOLE_PAGE_SOURCE_IDS:
            return [self._build_whole_page_object(raw_record, text)]

        categories = FAMILY_CATEGORIES.get(page_source_id)

        if categories:
            objects = self._parse_cards(raw_record, text, categories)

            if objects:
                return objects

        return [self._build_whole_page_object(raw_record, text)]

    # ------------------------------------------------------------
    # CARD-LISTING FAMILIES (intelligence / newsroom / hydrogen_in_action)
    # ------------------------------------------------------------

    def _parse_cards(
        self,
        raw_record: dict[str, Any],
        text: str,
        categories: list[str],
    ) -> list[IntelligenceObject]:
        category_alternation = "|".join(
            re.escape(category)
            for category in sorted(categories, key=len, reverse=True)
        )
        card_pattern = re.compile(
            rf"(?P<category>{category_alternation})\s+"
            rf"(?P<date>{DATE_PATTERN})",
        )

        matches = list(card_pattern.finditer(text))
        objects: list[IntelligenceObject] = []
        seen: set[tuple[str, str]] = set()

        for index, match in enumerate(matches):
            category = match.group("category")
            date_text = match.group("date")

            body_start = match.end()
            body_end = (
                matches[index + 1].start()
                if index + 1 < len(matches)
                else len(text)
            )
            body = text[body_start:body_end].strip()

            title = self._derive_title(body)
            dedupe_key = (title.casefold(), date_text)

            if not title or dedupe_key in seen:
                continue

            seen.add(dedupe_key)

            published_at = self._parse_date(date_text)
            intelligence_type = CATEGORY_TO_INTELLIGENCE_TYPE.get(
                category, IntelligenceType.NEWS
            )

            intelligence_object = self.build_intelligence_object(
                title=title,
                source_url=raw_record["source_url"],
                summary=self.clean_text(body)[:600] or None,
                published_at=published_at,
                collector_name="HydrogenCouncilCollector",
                intelligence_type=intelligence_type,
                categories=[category],
                products=self.extract_keywords(body, PRODUCT_CANDIDATES),
                countries=self.extract_keywords(body, COUNTRY_CANDIDATES),
                companies=self.extract_keywords(body, COMPANY_CANDIDATES),
            )

            if category in REPORT_LIKE_CATEGORIES:
                intelligence_object.add_event(
                    EventReference(
                        event_type=EventType.REPORT_PUBLISHED,
                        description=title,
                    )
                )

            objects.append(intelligence_object)

        return objects

    @classmethod
    def _derive_title(cls, body: str) -> str | None:
        words = body.split()

        if not words:
            return None

        # Titles are frequently duplicated verbatim right into the summary
        # (e.g. "Global Hydrogen Compass Global Hydrogen Compass 2025 is a
        # new..."). Detect a repeated leading phrase (2-8 words) and use it
        # as the title instead of an arbitrary word-count cut.
        for length in range(min(8, len(words) // 2), 1, -1):
            candidate = words[:length]

            if words[length:length * 2] == candidate:
                return cls.clean_text(" ".join(candidate)) or None

        return cls.clean_text(" ".join(words[:12])) or None

    @staticmethod
    def _parse_date(date_text: str) -> str | None:
        try:
            return date_parser.parse(date_text).date().isoformat()
        except (ValueError, OverflowError):
            return None

    # ------------------------------------------------------------
    # WHOLE-PAGE FALLBACK (home / members / unrecognised family)
    # ------------------------------------------------------------

    def _build_whole_page_object(
        self,
        raw_record: dict[str, Any],
        text: str,
    ) -> IntelligenceObject:
        return self.build_intelligence_object(
            title=raw_record["title"],
            source_url=raw_record["source_url"],
            summary=self.clean_text(text)[:600] or None,
            collector_name="HydrogenCouncilCollector",
            intelligence_type=IntelligenceType.COMPANY_UPDATE,
            products=self.extract_keywords(text, PRODUCT_CANDIDATES),
            countries=self.extract_keywords(text, COUNTRY_CANDIDATES),
            companies=self.extract_keywords(text, COMPANY_CANDIDATES),
        )
