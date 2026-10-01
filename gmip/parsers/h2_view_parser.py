from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from gmip.entities.seed import COMPANY_NAME_CANDIDATES
from gmip.intelligence.enums import ConfidenceLevel, EventType, IntelligenceType
from gmip.intelligence.intelligence_object import (
    EventReference,
    IntelligenceObject,
)
from gmip.parsers.base_parser import BaseParser

# Deliberately conservative and small: article summaries are short, so only
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

# Drawn from the shared canonical-company seed (gmip/entities/seed.py) so
# every parser recognizes the same companies instead of maintaining
# separate near-duplicate candidate lists.
COMPANY_CANDIDATES = list(COMPANY_NAME_CANDIDATES)

# gasworld.com/h2-view/ (the page H2 View now publishes as) renders each
# article as <a href=".../story/<slug>/<id>.article/">Real headline</a> —
# reading that directly (as HydrogenCouncilParser does for hydrogencouncil.com)
# is far more reliable than reconstructing titles from flowing text.
ARTICLE_HREF_MARKER = "/story/"
ARTICLE_HREF_SUFFIX = ".article"
MIN_HEADLINE_LENGTH = 15

# Every card on the page ends with "<Category> <date> <N> min read", where
# date is either a relative "<N> day(s) ago" or an absolute "DD Mon YYYY".
# This is a reliable, self-contained boundary marker: matching it lets us
# recover each card's category/date/read-time without needing to know the
# site's full category vocabulary up front (categories are numerous and
# change over time, unlike Hydrogen Council's small fixed facet list).
_CATEGORY_WORD = r"(?:[A-Z][a-zA-Z]*|&)"
_CATEGORY_PATTERN = rf"{_CATEGORY_WORD}(?:\s+{_CATEGORY_WORD}){{0,3}}"
_DATE_PATTERN = r"(?:\d+\s+days?\s+ago|\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4})"
CARD_END_PATTERN = re.compile(
    rf"(?P<category>{_CATEGORY_PATTERN})\s+"
    rf"(?P<date>{_DATE_PATTERN})\s+"
    rf"(?P<mins>\d+)\s+min read"
)

# Strips a leading "By <Author Name>" byline off a card's body text so it
# doesn't leak into the summary. Author names are matched conservatively
# (Capitalized-word tokens only) so a summary that happens to start with a
# single capitalized word (e.g. "A group of...") is never eaten by mistake.
BYLINE_PATTERN = re.compile(r"^By\s+(?:[A-Z][a-z]+\s*){1,3}")

# Every real article URL ends in a stable numeric ID (".../<id>.article/")
# regardless of which domain/slug it's served under — this is the most
# robust identity signal available without live redirect-following, so
# the same story never becomes duplicate intelligence just because the
# site migrated from h2-view.com to gasworld.com or re-slugged a title.
ARTICLE_ID_PATTERN = re.compile(r"/(\d+)\.article/?")


def _article_id(url: str) -> str | None:
    match = ARTICLE_ID_PATTERN.search(url)
    return match.group(1) if match else None


def _extract_article_links(html: str | None) -> list[tuple[str, str]]:
    """
    Collect each real article headline and its actual article-page URL, as
    (headline, url) pairs in document order. Returns an empty list (silently)
    if html is missing or unparseable — callers fall back to a whole-page
    object rather than fabricating anything.
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

        if not text or len(text) < MIN_HEADLINE_LENGTH:
            continue

        if ARTICLE_HREF_MARKER not in href or ARTICLE_HREF_SUFFIX not in href:
            continue

        # Accept both the current domain and the legacy one (section 10
        # of the access-resilience brief) — the same article's numeric ID
        # is what actually dedupes it (see _article_id()), not the host.
        if not any(domain in href for domain in ("gasworld.com", "h2-view.com")):
            continue

        # First occurrence wins (the same story sometimes appears in both a
        # "Top Stories" carousel and a "Recent stories"/"Most read" list).
        if text.casefold() in seen_titles:
            continue

        seen_titles.add(text.casefold())
        links.append((text, href))

    return links


def _flatten_text(html: str) -> str:
    """
    Full flattened page text, used to recover each card's category/date/
    read-time. Deliberately not raw_record["text"] — that comes from the
    project's shared extract_page_text() helper, which targets a page's
    <main>/<article> element and on this page's layout captures only a
    small widget, missing most of the real article grid.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        return ""

    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()

    return soup.get_text(" ", strip=True)


def _parse_published_at(
    date_text: str,
    reference: datetime,
) -> str | None:
    relative_match = re.match(r"(\d+)\s+days?\s+ago", date_text)

    if relative_match:
        days = int(relative_match.group(1))
        return (reference - timedelta(days=days)).date().isoformat()

    try:
        return date_parser.parse(date_text).date().isoformat()
    except (ValueError, OverflowError):
        return None


class H2ViewParser(BaseParser):
    """
    Structured parser for H2 View's channel page on gasworld.com
    (h2-view.com and its RSS feed are both dead — see
    gmip/config/sources_registry.py for the migration note).

    Mirrors HydrogenCouncilParser's approach: real headlines/URLs come from
    the page's own <a href> structure, and per-card metadata (category,
    publish date, read time, summary) is recovered from the page's flattened
    text using the "<Category> <date> <N> min read" marker that ends every
    card. Secondary discovery media, so confidence stays MEDIUM and nothing
    a short summary can't actually support (capacity, CAPEX, FID, etc.) is
    invented.
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
        if self.is_soft_404(
            raw_record.get("title"), raw_record.get("text")
        ):
            return []

        html = raw_record.get("html")
        article_links = _extract_article_links(html)

        if not article_links:
            # The landing page itself is discovery input only — never an
            # IntelligenceObject on its own (section 8 of the access-
            # resilience brief). It's already collected as a RawDocument
            # for change detection/source health; nothing further to do
            # here if no real article cards were found on it.
            return []

        text = _flatten_text(html)
        reference = self._resolve_reference_time(raw_record)

        objects: list[IntelligenceObject] = []
        search_from = 0

        for title, url in article_links:
            title_index = text.find(title, search_from)

            if title_index == -1:
                # Headline came from this same page's HTML, so this
                # shouldn't normally happen — still produce a minimal,
                # non-fabricated object rather than silently dropping it.
                objects.append(
                    self._build_card_object(title, url, None, None, None)
                )
                continue

            body_start = title_index + len(title)
            card_match = CARD_END_PATTERN.search(text, body_start)

            if not card_match:
                objects.append(
                    self._build_card_object(title, url, None, None, None)
                )
                search_from = body_start
                continue

            middle = text[body_start:card_match.start()].strip()
            summary = BYLINE_PATTERN.sub("", middle).strip() or None
            category = card_match.group("category").strip()
            published_at = _parse_published_at(
                card_match.group("date"), reference
            )

            objects.append(
                self._build_card_object(
                    title, url, category, published_at, summary
                )
            )
            search_from = card_match.end()

        return objects

    @staticmethod
    def _resolve_reference_time(raw_record: dict[str, Any]) -> datetime:
        """
        "X days ago" needs a reference point to resolve to a real date —
        the moment this page was collected, not the moment it's parsed
        (those can differ if parsing happens later from stored raw HTML).
        """
        collected_at = raw_record.get("collected_at")

        if isinstance(collected_at, datetime):
            return collected_at

        if isinstance(collected_at, str) and collected_at:
            try:
                return date_parser.parse(collected_at)
            except (ValueError, OverflowError):
                pass

        return datetime.now(timezone.utc)

    def _build_card_object(
        self,
        title: str,
        url: str,
        category: str | None,
        published_at: str | None,
        summary: str | None,
    ) -> IntelligenceObject:
        combined_text = " ".join(filter(None, [title, summary]))
        products = self.extract_keywords(combined_text, PRODUCT_CANDIDATES)
        offtake = self.detect_offtake(combined_text, products=products)

        article_id = _article_id(url)

        intelligence_object = self.build_intelligence_object(
            title=title,
            source_url=url,
            summary=summary,
            published_at=published_at,
            collector_name="H2ViewCollector",
            confidence=ConfidenceLevel.MEDIUM,
            intelligence_type=(
                IntelligenceType.OFFTAKE if offtake is not None else None
            ),
            products=products,
            countries=self.extract_keywords(combined_text, COUNTRY_CANDIDATES),
            companies=self.extract_keywords(combined_text, COMPANY_CANDIDATES),
            categories=[category] if category else [],
            offtake=offtake,
            # Stable across a domain migration (h2-view.com -> gasworld.com)
            # or a re-slugged title — falls back to the default
            # source_id:title identity when no article ID is extractable.
            identity_key=f"h2_view:{article_id}" if article_id else None,
            metadata={"discovery_source": True},
        )

        if offtake is not None:
            intelligence_object.add_event(
                EventReference(
                    event_type=EventType.OFFTAKE_SIGNED,
                    description=title,
                )
            )

        return intelligence_object
