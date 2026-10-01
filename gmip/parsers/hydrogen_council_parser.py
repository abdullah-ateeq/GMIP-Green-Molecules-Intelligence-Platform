from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup
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

# Anchor text this short is reliably site navigation ("Become a Member" is
# 15 chars, "Hydrogen in Action" is 18) — set comfortably above those but
# below the shortest real headlines seen in practice (e.g. "Global Hydrogen
# Compass" at 23 chars).
MIN_HEADLINE_LENGTH = 20


def _extract_article_links(html: str | None) -> list[tuple[str, str]]:
    """
    Collect each real article headline and its actual detail-page URL, as
    (headline, url) pairs ordered longest-headline-first.

    WordPress renders each card's headline itself as
    <a href="...the real article...">Headline text</a> — reading that is
    far more reliable than trying to positionally match card order against
    "Read More" links, since listing pages often repeat some cards in both
    a "featured" section and the full list below. Returns an empty list
    (silently) if html is missing or unparseable; callers already fall
    back to the listing page URL when no match is found here, so nothing
    is fabricated.
    """
    if not html:
        return []

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        return []

    seen_titles: set[str] = set()
    links: list[tuple[str, str]] = []

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        text = anchor.get_text(strip=True)

        if not text or text.casefold() == "read more":
            continue

        if len(text) < MIN_HEADLINE_LENGTH:
            continue

        if "hydrogencouncil.com/en/" not in href:
            continue

        # First occurrence wins (e.g. a "featured" section before the full
        # list) — both point to the same real article either way.
        if text.casefold() in seen_titles:
            continue

        seen_titles.add(text.casefold())
        links.append((text, href))

    # Longest headline first: our derived title is often "the real
    # headline plus some of the following body text" (see _derive_title),
    # so matching the longest true headline first avoids a shorter,
    # unrelated headline matching as a false prefix.
    links.sort(key=lambda pair: len(pair[0]), reverse=True)

    return links


def _match_article_link(
    derived_title: str,
    article_links: list[tuple[str, str]],
) -> tuple[str, str] | None:
    """
    Find the real (headline, url) pair for a card's derived title.

    _derive_title() sometimes returns the true headline verbatim,
    sometimes the headline with trailing body text merged in (longer than
    the real headline), and sometimes a 12-word truncation that cuts the
    real headline short (shorter than it) — so this matches in either
    prefix direction rather than requiring an exact string match.
    """
    lowered = derived_title.casefold()

    for headline, url in article_links:
        headline_lowered = headline.casefold()

        if lowered.startswith(headline_lowered):
            return headline, url

        # Reverse direction only for a reasonably specific derived title —
        # guards against a very short/generic fragment loosely prefix-
        # matching an unrelated, longer headline.
        if len(lowered) >= MIN_HEADLINE_LENGTH and headline_lowered.startswith(
            lowered
        ):
            return headline, url

    return None


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
        article_links = _extract_article_links(raw_record.get("html"))

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
            body = self._strip_trailing_noise(body)

            title = self._derive_title(body)

            if not title:
                continue

            # Prefer the real headline + real article URL when we can
            # match one (WordPress links the headline itself); otherwise
            # keep the heuristic title and fall back to the listing page
            # rather than guessing a URL.
            matched = _match_article_link(title, article_links)

            if matched:
                title, article_url = matched
            else:
                article_url = raw_record["source_url"]

            dedupe_key = (title.casefold(), date_text)

            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)

            published_at = self._parse_date(date_text)
            intelligence_type = CATEGORY_TO_INTELLIGENCE_TYPE.get(
                category, IntelligenceType.NEWS
            )
            products = self.extract_keywords(body, PRODUCT_CANDIDATES)
            offtake = self.detect_offtake(
                f"{title} {body}", products=products
            )

            if offtake is not None:
                intelligence_type = IntelligenceType.OFFTAKE

            intelligence_object = self.build_intelligence_object(
                title=title,
                source_url=article_url,
                summary=self.clean_text(body)[:600] or None,
                published_at=published_at,
                collector_name="HydrogenCouncilCollector",
                intelligence_type=intelligence_type,
                categories=[category],
                products=products,
                countries=self.extract_keywords(body, COUNTRY_CANDIDATES),
                companies=self.extract_keywords(body, COMPANY_CANDIDATES),
                offtake=offtake,
            )

            if offtake is not None:
                intelligence_object.add_event(
                    EventReference(
                        event_type=EventType.OFFTAKE_SIGNED,
                        description=title,
                    )
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

    @staticmethod
    def _strip_trailing_noise(body: str) -> str:
        """
        Strip "Read More" and any trailing pagination controls
        ("1 2 3 ... Next") that leak into the last card on a listing page.
        """
        body = re.sub(r"Read [Mm]ore\s*", "", body).strip()
        body = re.sub(
            r"\s*(?:\d+\s+){2,}(?:Next\s*)?$", "", body
        ).strip()
        return body

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
