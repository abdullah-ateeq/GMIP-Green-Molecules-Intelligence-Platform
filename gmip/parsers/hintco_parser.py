from __future__ import annotations

import re
from typing import Any

from dateutil import parser as date_parser

from gmip.intelligence.enums import EventType, IntelligenceType
from gmip.intelligence.intelligence_object import (
    EventReference,
    IntelligenceObject,
    TenderDetails,
)
from gmip.parsers.base_parser import BaseParser

# Source IDs whose page text is a list of tender "lots" (Products/Region/
# Volume per lot). See gmip/parsers/hintco_parser.py's module docstring
# analysis for the real captured layout these regexes are built against.
LOT_PAGE_SOURCE_IDS = {
    "hintco_hpa_auctions",
    "hintco_hsa_auctions",
    "hintco_tender_1",
    "hintco_tender_2",
}

LOT_HEADING_PATTERN = re.compile(
    r"((?:(?:[A-Z][a-zA-Z]*|&)\s+){1,4}Lot)\s*\(([A-Z]+)\)"
)

PRODUCTS_PATTERN = re.compile(
    r"Products?\s*:\s*(.*?)\s*Region\s*:", re.IGNORECASE | re.DOTALL
)
REGION_PATTERN = re.compile(
    r"Region\s*:\s*(.*?)\s*Volume\s*:", re.IGNORECASE | re.DOTALL
)
VOLUME_PATTERN = re.compile(
    r"Volume\s*:\s*((?:min\.?\s*)?EUR\s*[\d,.]+\s*"
    r"(?:million|billion)?)",
    re.IGNORECASE,
)

# Hintco's HPA/HSA auction lots are a small, fairly stable set. Preferring
# a canonical name by lot code avoids picking up unrelated preceding text
# (funding-body names, link labels, etc.) that happens to also be
# Title-Case and sit right before the heading in the extracted text.
# Unrecognised codes still fall through to the regex-captured name.
KNOWN_LOT_NAMES = {
    "GL": "Global Lot",
    "GML": "Global Methanol Lot",
    "AFL": "African Lot",
    "ASL": "Asian Lot",
    "SAL": "South American & Oceanian Lot",
    "NAL": "North American Lot",
}

MONTH_NAMES = (
    r"January|February|March|April|May|June|July|August|"
    r"September|October|November|December"
)

# News items on hintco_news carry a dateline somewhere near the start of
# the item, in either "DD Month[,] YYYY" or "Month DD, YYYY" order, with
# inconsistent punctuation around it (colon, en-dash, comma, or nothing).
# Matched loosely here; the exact date is then parsed with dateutil rather
# than hand-rolled month-name/order handling.
DATE_PATTERN = re.compile(
    rf"(?:\d{{1,2}}\s+(?:{MONTH_NAMES})\s*,?\s*\d{{4}})"
    rf"|(?:(?:{MONTH_NAMES})\s+\d{{1,2}},?\s+\d{{4}})",
    re.IGNORECASE,
)

# Chunks that are pagination/cookie-banner/footer noise rather than real
# news items — skipped outright rather than emitted as fake intelligence.
NEWS_JUNK_MARKERS = (
    "cookie consent",
    "manage consent",
    "view preferences",
    "{title}",
    "next »",
)

# Known boilerplate site navigation that leaks into the first extracted
# text chunk on every Hintco page — stripped before parsing.
NAV_BOILERPLATE = (
    "About Who we are The H2Global Mechanism Tenders "
    "HPA Auctions HSA Auctions News FAQ"
)

# Link/button labels that sometimes sit directly in front of a lot heading
# (e.g. "Fact Sheet African Lot (AFL)") and would otherwise be captured as
# part of the lot name.
LOT_NAME_STOPWORDS = {"fact", "sheet", "access", "download", "platform"}

NEWS_EVENT_PHRASES: list[tuple[str, EventType]] = [
    ("boosts funding", EventType.FUNDING_APPROVED),
    ("increases funding", EventType.FUNDING_APPROVED),
    ("opens application phase", EventType.TENDER_LAUNCHED),
    ("entered the application phase", EventType.TENDER_LAUNCHED),
    ("extends contract timelines", EventType.DEADLINE_EXTENDED),
    ("deadline extended", EventType.DEADLINE_EXTENDED),
    ("awarded", EventType.CONTRACT_AWARDED),
]

class HintcoParser(BaseParser):
    """
    Structured parser for Hintco tender pages.

    Replaces the generic keyword classification with real field extraction
    for the two page shapes Hintco actually uses: lot-listing pages
    (HPA/HSA auctions, tender pages) and the news list page. Every other
    Hintco page (FAQs, how-to-bid, homepage) falls back to a single
    whole-page NEWS/OTHER object rather than inventing structure that
    isn't there.
    """

    parser_name = "HintcoParser"
    source_organisation = "Hintco"
    source_id = "hintco"
    default_intelligence_type = IntelligenceType.TENDER

    def can_parse(self, raw_record: dict[str, Any]) -> bool:
        return bool(
            raw_record.get("title") and raw_record.get("source_url")
        )

    def parse(
        self,
        raw_record: dict[str, Any],
    ) -> list[IntelligenceObject]:
        page_source_id = raw_record.get("source_id", "")
        text = self._strip_nav_boilerplate(raw_record.get("text") or "")

        if self.is_soft_404(raw_record.get("title"), text):
            return []

        if page_source_id in LOT_PAGE_SOURCE_IDS:
            objects = self._parse_lots(raw_record, text)

            if objects:
                return objects

        if page_source_id == "hintco_news":
            objects = self._parse_news_items(raw_record, text)

            if objects:
                return objects

        return [self._build_fallback_object(raw_record, text)]

    # ------------------------------------------------------------
    # LOT PAGES
    # ------------------------------------------------------------

    def _parse_lots(
        self,
        raw_record: dict[str, Any],
        text: str,
    ) -> list[IntelligenceObject]:
        headings = list(LOT_HEADING_PATTERN.finditer(text))
        objects: list[IntelligenceObject] = []
        default_tender_type = self._source_type(raw_record)

        for index, match in enumerate(headings):
            lot_code = match.group(2)
            lot_name = KNOWN_LOT_NAMES.get(
                lot_code,
                self._clean_lot_name(self.clean_text(match.group(1))),
            )

            body_start = match.end()
            body_end = (
                headings[index + 1].start()
                if index + 1 < len(headings)
                else len(text)
            )
            body = text[body_start:body_end]

            products = self._extract_field(PRODUCTS_PATTERN, body)
            region = self._extract_field(REGION_PATTERN, body)
            volume = self._extract_field(VOLUME_PATTERN, body)
            tender_status = self._detect_lot_status(body)

            title = f"{lot_name} ({lot_code})"

            intelligence_object = self.build_intelligence_object(
                title=title,
                source_url=raw_record["source_url"],
                summary=self.clean_text(body)[:400] or None,
                collector_name="HintcoCollector",
                tender_type=default_tender_type,
                products=self._split_products(products),
                tender=TenderDetails(
                    buyer="Hintco",
                    opportunity_type=default_tender_type,
                    volume=volume,
                    region=region,
                    lot=lot_code,
                    tender_status=tender_status,
                ),
                metadata={"lot_code": lot_code},
            )

            if tender_status:
                event_type = (
                    EventType.TENDER_LAUNCHED
                    if tender_status == "Open"
                    else EventType.OTHER
                )
                intelligence_object.add_event(
                    EventReference(
                        event_type=event_type,
                        description=f"{title} status: {tender_status}.",
                    )
                )

            objects.append(intelligence_object)

        return objects

    @staticmethod
    def _clean_lot_name(raw_name: str) -> str:
        words = raw_name.split()
        last_stopword_index = -1

        for index, word in enumerate(words[:-1]):  # exclude "Lot" itself
            if word.lower() in LOT_NAME_STOPWORDS:
                last_stopword_index = index

        return " ".join(words[last_stopword_index + 1:])

    @staticmethod
    def _extract_field(pattern: re.Pattern, body: str) -> str | None:
        match = pattern.search(body)

        if not match:
            return None

        value = " ".join(match.group(1).split()).strip(" ¹²³.,")
        return value or None

    @staticmethod
    def _split_products(products_text: str | None) -> list[str]:
        if not products_text:
            return []

        return [
            part.strip()
            for part in products_text.split(",")
            if part.strip()
        ]

    @staticmethod
    def _detect_lot_status(body: str) -> str | None:
        lowered = body.lower()

        if "has ended" in lowered or "phase has ended" in lowered:
            return "Closed"

        if "access tender platform" in lowered:
            return "Open"

        return None

    @staticmethod
    def _source_type(raw_record: dict[str, Any]) -> str | None:
        metadata = raw_record.get("metadata") or {}
        source_type = metadata.get("source_type")
        return source_type if isinstance(source_type, str) else None

    # ------------------------------------------------------------
    # NEWS PAGE
    # ------------------------------------------------------------

    def _parse_news_items(
        self,
        raw_record: dict[str, Any],
        text: str,
    ) -> list[IntelligenceObject]:
        chunks = re.split(r"Read more", text, flags=re.IGNORECASE)
        objects: list[IntelligenceObject] = []
        seen_titles: set[str] = set()

        for chunk in chunks:
            chunk = chunk.strip()

            if not chunk or self._is_junk_chunk(chunk):
                continue

            title, published_at, body = self._split_news_chunk(chunk)

            if not title or title.casefold() in seen_titles:
                continue

            seen_titles.add(title.casefold())

            event = self._detect_news_event(f"{title} {body}")
            offtake = self.detect_offtake(f"{title} {body}")

            intelligence_object = self.build_intelligence_object(
                title=title,
                source_url=raw_record["source_url"],
                summary=self.clean_text(body)[:500] or None,
                published_at=published_at,
                collector_name="HintcoCollector",
                intelligence_type=(
                    IntelligenceType.OFFTAKE
                    if offtake is not None
                    else IntelligenceType.NEWS
                ),
                offtake=offtake,
            )

            if offtake is not None:
                intelligence_object.add_event(
                    EventReference(
                        event_type=EventType.OFFTAKE_SIGNED,
                        description=title,
                    )
                )
            elif event is not None:
                intelligence_object.add_event(
                    EventReference(
                        event_type=event,
                        description=title,
                    )
                )

            objects.append(intelligence_object)

        return objects

    def _split_news_chunk(
        self,
        chunk: str,
    ) -> tuple[str | None, str | None, str]:
        match = DATE_PATTERN.search(chunk)

        if match:
            title = self._clean_headline(chunk[: match.start()])
            body = chunk[match.end():].lstrip(" –-:,—")
            published_at = self._parse_dateline(match.group(0))

            if title:
                return title, published_at, body

        # No recognisable dateline, or nothing usable before it: fall back
        # to a short title heuristic and keep the whole chunk as the body.
        words = chunk.split()
        title = self.clean_text(" ".join(words[:12])) or None

        return title, None, chunk

    @staticmethod
    def _parse_dateline(date_text: str) -> str | None:
        try:
            parsed = date_parser.parse(date_text, fuzzy=True)
        except (ValueError, OverflowError):
            return None

        return parsed.date().isoformat()

    @classmethod
    def _clean_headline(cls, raw_headline: str) -> str | None:
        # Strip a trailing ", City" or "City" immediately before the date
        # (e.g. "...four regional lots Hamburg" -> "...four regional lots").
        headline = raw_headline.rstrip(" ,–-—")
        words = headline.split()

        if words and words[-1][:1].isupper() and len(words[-1]) < 20:
            # Only strip if what remains still reads as a real headline.
            if len(words) > 3:
                headline = " ".join(words[:-1])

        return cls.clean_text(headline) or None

    @staticmethod
    def _is_junk_chunk(chunk: str) -> bool:
        lowered = chunk.lower()
        return any(marker in lowered for marker in NEWS_JUNK_MARKERS)

    @staticmethod
    def _detect_news_event(text: str) -> EventType | None:
        lowered = text.lower()

        for phrase, event_type in NEWS_EVENT_PHRASES:
            if phrase in lowered:
                return event_type

        return None

    # ------------------------------------------------------------
    # FALLBACK (FAQ / how-to-bid / homepage / tenders overview)
    # ------------------------------------------------------------

    def _build_fallback_object(
        self,
        raw_record: dict[str, Any],
        text: str,
    ) -> IntelligenceObject:
        return self.build_intelligence_object(
            title=raw_record["title"],
            source_url=raw_record["source_url"],
            summary=self.clean_text(text)[:500] or None,
            collector_name="HintcoCollector",
            intelligence_type=IntelligenceType.OTHER,
        )

    @staticmethod
    def _strip_nav_boilerplate(text: str) -> str:
        if text.startswith(NAV_BOILERPLATE):
            return text[len(NAV_BOILERPLATE):].strip()

        return text
