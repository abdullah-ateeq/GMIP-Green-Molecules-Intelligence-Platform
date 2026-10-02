from __future__ import annotations

import html
import logging
import re

from abc import ABC, abstractmethod
from datetime import date, datetime, timezone
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from gmip.intelligence.enums import (
    ConfidenceLevel,
    ImportanceLevel,
    IntelligenceStatus,
    IntelligenceType,
)
from gmip.intelligence.intelligence_object import (
    IntelligenceObject,
    OfftakeDetails,
    TenderDetails,
)

# Multi-word phrases that reliably signal a real offtake/supply agreement
# in this industry's reporting, as opposed to generic project news. Kept
# narrow and specific (no bare "supply" or "purchase") to avoid false
# positives on unrelated project-update text.
OFFTAKE_SIGNAL_PHRASES = (
    "offtake agreement",
    "offtake deal",
    "offtake contract",
    "offtaker",
    "supply agreement",
    "supply contract",
    "purchase agreement",
    "sales agreement",
    "sale and purchase agreement",
    "agreed to supply",
    "agreed to purchase",
    "signed a deal to supply",
    "signed an agreement to supply",
    "locks in",
    "secures supply",
)

# Mechanical quantity-and-unit extraction (e.g. "40,000 tonnes per year",
# "1.2 MTPA") — not an attempt to parse full sentence structure.
_OFFTAKE_VOLUME_PATTERN = re.compile(
    r"\b[\d][\d,.]*\s*"
    r"(?:tonnes?|tons?|mtpa|ktpa|kt|mt|gwh|mwh|mw)\b"
    r"(?:\s*(?:per\s+year|/\s*year|annually|p\.?a\.?))?",
    re.IGNORECASE,
)

_OFFTAKE_DURATION_PATTERN = re.compile(
    r"\b(?:over\s+a\s+decade|a\s+decade|\d{1,2}[-\s]?years?)\b",
    re.IGNORECASE,
)


class ParserError(Exception):
    """Base exception for GMIP parser failures."""


class ParserValidationError(ParserError):
    """Raised when raw source data fails parser validation."""


class BaseParser(ABC):
    """
    Abstract base class for every GMIP source parser.

    Each source-specific parser must implement:
        - can_parse()
        - parse()
    """

    parser_name = "BaseParser"
    source_organisation = "Unknown"
    source_id = "unknown"
    default_intelligence_type = IntelligenceType.OTHER

    def __init__(
        self,
        base_url: str | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.base_url = base_url
        self.logger = logger or logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )

    @abstractmethod
    def can_parse(self, raw_record: dict[str, Any]) -> bool:
        """
        Return True when this parser supports the supplied raw record.
        """

    @abstractmethod
    def parse(
        self,
        raw_record: dict[str, Any],
    ) -> list[IntelligenceObject]:
        """
        Convert one raw collector record into one or more
        IntelligenceObject instances.
        """

    def parse_many(
        self,
        raw_records: Iterable[dict[str, Any]],
        skip_invalid: bool = True,
    ) -> list[IntelligenceObject]:
        """
        Parse several raw records.

        When skip_invalid is True, unsupported or invalid records are logged
        and skipped. When False, the first error is raised.
        """
        intelligence_objects: list[IntelligenceObject] = []

        for index, raw_record in enumerate(raw_records, start=1):
            try:
                self.validate_raw_record(raw_record)

                if not self.can_parse(raw_record):
                    raise ParserValidationError(
                        f"{self.parser_name} cannot parse record {index}."
                    )

                parsed_objects = self.parse(raw_record)

                if not isinstance(parsed_objects, list):
                    raise ParserError(
                        f"{self.parser_name}.parse() must return a list."
                    )

                for intelligence_object in parsed_objects:
                    self.validate_intelligence_object(
                        intelligence_object
                    )

                intelligence_objects.extend(parsed_objects)

            except Exception as error:
                if not skip_invalid:
                    raise

                self.logger.warning(
                    "Skipping record %s because parsing failed: %s",
                    index,
                    error,
                )

        return intelligence_objects

    def validate_raw_record(
        self,
        raw_record: dict[str, Any],
    ) -> None:
        """Perform basic validation before source-specific parsing."""
        if not isinstance(raw_record, dict):
            raise ParserValidationError(
                "Raw parser input must be a dictionary."
            )

        if not raw_record:
            raise ParserValidationError(
                "Raw parser input cannot be empty."
            )

    def validate_intelligence_object(
        self,
        intelligence_object: IntelligenceObject,
    ) -> None:
        """Validate the output returned by a source parser."""
        if not isinstance(
            intelligence_object,
            IntelligenceObject,
        ):
            raise ParserError(
                "Parser output must contain IntelligenceObject instances."
            )

        if not intelligence_object.title.strip():
            raise ParserError(
                "Parsed intelligence object has no title."
            )

        if not intelligence_object.source_url.strip():
            raise ParserError(
                "Parsed intelligence object has no source URL."
            )

    def build_intelligence_object(
        self,
        *,
        title: str,
        source_url: str,
        intelligence_type: IntelligenceType | None = None,
        summary: str | None = None,
        raw_text: str | None = None,
        published_at: datetime | date | str | None = None,
        collector_name: str | None = None,
        status: IntelligenceStatus = IntelligenceStatus.NEW,
        confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
        importance: ImportanceLevel = ImportanceLevel.MEDIUM,
        language: str = "en",
        categories: Iterable[str] | None = None,
        products: Iterable[str] | None = None,
        countries: Iterable[str] | None = None,
        regions: Iterable[str] | None = None,
        companies: Iterable[str] | None = None,
        projects: Iterable[str] | None = None,
        technologies: Iterable[str] | None = None,
        people: Iterable[str] | None = None,
        policies: Iterable[str] | None = None,
        certifications: Iterable[str] | None = None,
        keywords: Iterable[str] | None = None,
        attachments: Iterable[str] | None = None,
        capacity: str | None = None,
        capex: str | None = None,
        fid_date: datetime | date | str | None = None,
        cod_date: datetime | date | str | None = None,
        commercial_theme: str | None = None,
        policy_theme: str | None = None,
        tender_type: str | None = None,
        project_stage: str | None = None,
        tender: TenderDetails | None = None,
        offtake: OfftakeDetails | None = None,
        commercial_relevance: str | None = None,
        why_it_matters: str | None = None,
        recommended_action: str | None = None,
        metadata: dict[str, Any] | None = None,
        raw_document_id: str | None = None,
        identity_key: str | None = None,
    ) -> IntelligenceObject:
        """
        Construct a standardized IntelligenceObject.

        Source parsers should normally use this method instead of creating
        IntelligenceObject directly.
        """
        cleaned_title = self.clean_text(title)

        if not cleaned_title:
            raise ParserValidationError(
                "An intelligence object cannot be created without a title."
            )

        normalized_url = self.normalize_url(source_url)

        if not normalized_url:
            raise ParserValidationError(
                "An intelligence object cannot be created without a valid URL."
            )

        return IntelligenceObject(
            title=cleaned_title,
            source_organisation=self.source_organisation,
            source_id=self.source_id,
            source_url=normalized_url,
            intelligence_type=(
                intelligence_type
                or self.default_intelligence_type
            ),
            summary=self.clean_optional_text(summary),
            raw_text=self.clean_optional_text(raw_text),
            published_at=self.parse_datetime(published_at),
            language=language.strip().lower() or "en",
            status=status,
            confidence=confidence,
            importance=importance,
            collector_name=collector_name,
            parser_name=self.parser_name,
            categories=self.normalize_string_list(categories),
            products=self.normalize_string_list(products),
            countries=self.normalize_string_list(countries),
            regions=self.normalize_string_list(regions),
            companies=self.normalize_string_list(companies),
            projects=self.normalize_string_list(projects),
            technologies=self.normalize_string_list(technologies),
            people=self.normalize_string_list(people),
            policies=self.normalize_string_list(policies),
            certifications=self.normalize_string_list(
                certifications
            ),
            keywords=self.normalize_string_list(keywords),
            attachments=self.normalize_string_list(attachments),
            capacity=self.clean_optional_text(capacity),
            capex=self.clean_optional_text(capex),
            fid_date=self.parse_date(fid_date),
            cod_date=self.parse_date(cod_date),
            commercial_theme=self.clean_optional_text(commercial_theme),
            policy_theme=self.clean_optional_text(policy_theme),
            tender_type=self.clean_optional_text(tender_type),
            project_stage=self.clean_optional_text(project_stage),
            tender=tender,
            offtake=offtake,
            commercial_relevance=self.clean_optional_text(
                commercial_relevance
            ),
            why_it_matters=self.clean_optional_text(
                why_it_matters
            ),
            recommended_action=self.clean_optional_text(
                recommended_action
            ),
            metadata=metadata or {},
            raw_document_id=raw_document_id,
            identity_key=identity_key,
        )

    @staticmethod
    def clean_text(value: Any) -> str:
        """
        Convert a value to clean plain text.

        Handles:
            - HTML entities
            - simple HTML tags
            - repeated whitespace
            - leading and trailing whitespace
        """
        if value is None:
            return ""

        text = html.unescape(str(value))
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    @classmethod
    def clean_optional_text(
        cls,
        value: Any,
    ) -> str | None:
        cleaned = cls.clean_text(value)
        return cleaned or None

    @classmethod
    def normalize_string_list(
        cls,
        values: Iterable[Any] | Any | None,
    ) -> list[str]:
        """
        Clean, deduplicate, and sort a collection of string values.

        A single string is treated as one value rather than as an iterable
        of individual characters.
        """
        if values is None:
            return []

        if isinstance(values, str):
            values = [values]

        cleaned_values: dict[str, str] = {}

        for value in values:
            cleaned = cls.clean_text(value)

            if not cleaned:
                continue

            cleaned_values.setdefault(
                cleaned.casefold(),
                cleaned,
            )

        return sorted(
            cleaned_values.values(),
            key=str.casefold,
        )

    # Tracking parameters that are safe to drop without changing which
    # resource a URL points to — never strips params that could be part
    # of the resource's actual identity (e.g. a real query-string-based
    # article ID).
    _TRACKING_PARAM_PREFIXES = ("utm_",)
    _TRACKING_PARAM_NAMES = {
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
        "igshid",
        "ref",
        "ref_src",
    }

    def normalize_url(
        self,
        url: Any,
    ) -> str:
        """
        Convert relative URLs to absolute URLs and validate the result.

        The single shared URL-cleanup path for every parser (section 3 of
        the provenance-quality brief: one centralized utility, not
        per-source cleanup scattered across parser files). Handles
        relative -> absolute resolution, HTML-escaped/whitespace-padded
        URLs (via clean_text), fragment stripping, and known tracking
        parameters — never touches the path or any other query parameter,
        so it can't accidentally change which resource a URL identifies.
        """
        cleaned_url = self.clean_text(url)

        if not cleaned_url:
            return ""

        if self.base_url:
            cleaned_url = urljoin(
                self.base_url,
                cleaned_url,
            )

        parsed_url = urlparse(cleaned_url)

        if parsed_url.scheme not in {"http", "https"}:
            return ""

        if not parsed_url.netloc:
            return ""

        kept_query_params = [
            (key, value)
            for key, value in parse_qsl(parsed_url.query, keep_blank_values=True)
            if key.lower() not in self._TRACKING_PARAM_NAMES
            and not key.lower().startswith(self._TRACKING_PARAM_PREFIXES)
        ]

        normalized = parsed_url._replace(
            query=urlencode(kept_query_params),
            fragment="",
        )

        return urlunparse(normalized)

    @staticmethod
    def parse_datetime(
        value: datetime | date | str | None,
    ) -> datetime | None:
        """
        Convert common date values to a timezone-aware datetime.

        ISO formats supported include:
            2026-07-24
            2026-07-24T10:30:00
            2026-07-24T10:30:00Z
            2026-07-24T10:30:00+00:00
        """
        if value is None:
            return None

        if isinstance(value, datetime):
            parsed_datetime = value

        elif isinstance(value, date):
            parsed_datetime = datetime(
                year=value.year,
                month=value.month,
                day=value.day,
                tzinfo=timezone.utc,
            )

        elif isinstance(value, str):
            cleaned_value = value.strip()

            if not cleaned_value:
                return None

            if cleaned_value.endswith("Z"):
                cleaned_value = (
                    cleaned_value[:-1] + "+00:00"
                )

            try:
                parsed_datetime = datetime.fromisoformat(
                    cleaned_value
                )
            except ValueError as error:
                raise ParserValidationError(
                    f"Unsupported datetime value: {value}"
                ) from error

        else:
            raise ParserValidationError(
                f"Unsupported datetime type: {type(value).__name__}"
            )

        if parsed_datetime.tzinfo is None:
            parsed_datetime = parsed_datetime.replace(
                tzinfo=timezone.utc
            )

        return parsed_datetime

    @classmethod
    def parse_date(
        cls,
        value: datetime | date | str | None,
    ) -> date | None:
        """Like parse_datetime(), but returns a plain date (or None)."""
        parsed = cls.parse_datetime(value)
        return parsed.date() if parsed else None

    @classmethod
    def extract_keywords(
        cls,
        text: str | None,
        candidate_keywords: Iterable[str],
    ) -> list[str]:
        """
        Find configured keywords inside supplied text.

        This is deterministic keyword matching, not AI extraction.
        Matches on whole-word boundaries, not bare substrings — short
        candidates (company tickers/abbreviations like "BP", "Nel", "AG")
        would otherwise false-positive inside unrelated words ("panel"
        contains "nel", "ABP" contains "BP"). See the entity-extraction
        brief, section 10.
        """
        cleaned_text = cls.clean_text(text)

        if not cleaned_text:
            return []

        matches = []

        for keyword in candidate_keywords:
            cleaned_keyword = cls.clean_text(keyword)

            if not cleaned_keyword:
                continue

            pattern = r"\b" + re.escape(cleaned_keyword) + r"\b"

            if re.search(pattern, cleaned_text, re.IGNORECASE):
                matches.append(cleaned_keyword)

        return cls.normalize_string_list(matches)

    @classmethod
    def detect_offtake(
        cls,
        text: str | None,
        products: Iterable[str] | None = None,
    ) -> OfftakeDetails | None:
        """
        Conservative, deterministic offtake-agreement detection.

        Returns None unless a known signal phrase (see
        OFFTAKE_SIGNAL_PHRASES) is present — this is keyword/pattern
        matching, not inference. Only mechanically-extractable facts are
        populated (a quantity-and-unit volume, a duration phrase, the
        first already-matched product); producer/buyer roles are
        deliberately left unset rather than guessed from word order,
        since which company is the seller vs. the buyer is not reliably
        determinable from text alone.
        """
        cleaned_text = cls.clean_text(text)
        lowered = cleaned_text.casefold()

        if not any(
            phrase in lowered for phrase in OFFTAKE_SIGNAL_PHRASES
        ):
            return None

        volume_match = _OFFTAKE_VOLUME_PATTERN.search(cleaned_text)
        duration_match = _OFFTAKE_DURATION_PATTERN.search(cleaned_text)
        product_list = list(products) if products else []

        return OfftakeDetails(
            product=product_list[0] if product_list else None,
            volume=(
                " ".join(volume_match.group(0).split())
                if volume_match
                else None
            ),
            duration=(
                " ".join(duration_match.group(0).split())
                if duration_match
                else None
            ),
        )

    # (verb phrase, relationship_type, subject_appears_first). A passive
    # form ("developed by") puts the real subject (the company) on the
    # right, so subject_appears_first=False swaps which side the pattern
    # expects the company name on.
    _COMPANY_PROJECT_RELATIONSHIP_PATTERNS: tuple[tuple[str, str, bool], ...] = (
        (r"is\s+developing", "develops", True),
        (r"develops", "develops", True),
        (r"developed\s+by", "develops", False),
        (r"operates", "operates", True),
        (r"operated\s+by", "operates", False),
        (r"invests?\s+in", "invests_in", True),
        (r"is\s+investing\s+in", "invests_in", True),
        (r"supplies", "supplies_to", True),
        (r"off-?takes?\s+from", "offtakes_from", True),
    )

    _RELATIONSHIP_GAP = r".{0,60}?"

    @classmethod
    def detect_relationships(
        cls,
        text: str | None,
        companies: Iterable[str],
        projects: Iterable[str],
    ) -> list[dict[str, str]]:
        """
        Conservative, deterministic relationship extraction (section 14-16
        of the entity-extraction brief): a relationship is only recorded
        when an explicit verb phrase connects two names ALREADY confirmed
        present in this same card's own extracted companies/projects —
        never inferred from two names merely co-occurring in the same
        article. Returns dicts ready to store in IntelligenceObject
        metadata and later resolved to real entity_ids during entity
        resolution (relationship creation needs canonical entity_ids,
        which only exist after resolution — see
        gmip.entities.backfill.resolve_mentions_for_object()).
        """
        cleaned = cls.clean_text(text)
        company_list = list(dict.fromkeys(companies))
        project_list = list(dict.fromkeys(projects))

        if not cleaned or not company_list:
            return []

        results: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()

        for company in company_list:
            for project in project_list:
                for (
                    verb_pattern,
                    relationship_type,
                    subject_first,
                ) in cls._COMPANY_PROJECT_RELATIONSHIP_PATTERNS:
                    left, right = (
                        (company, project) if subject_first else (project, company)
                    )
                    pattern = (
                        re.escape(left)
                        + cls._RELATIONSHIP_GAP
                        + r"\b" + verb_pattern + r"\b"
                        + cls._RELATIONSHIP_GAP
                        + re.escape(right)
                    )

                    if re.search(pattern, cleaned, re.IGNORECASE):
                        key = (company, relationship_type, project)

                        if key not in seen:
                            seen.add(key)
                            results.append(
                                {
                                    "subject": company,
                                    "subject_type": "COMPANY",
                                    "relationship_type": relationship_type,
                                    "object": project,
                                    "object_type": "PROJECT",
                                }
                            )

                        break

        for index, company_a in enumerate(company_list):
            for company_b in company_list[index + 1 :]:
                pattern = (
                    re.escape(company_a)
                    + cls._RELATIONSHIP_GAP
                    + r"\bpartners?\s+with\b"
                    + cls._RELATIONSHIP_GAP
                    + re.escape(company_b)
                )

                if re.search(pattern, cleaned, re.IGNORECASE):
                    results.append(
                        {
                            "subject": company_a,
                            "subject_type": "COMPANY",
                            "relationship_type": "partners_with",
                            "object": company_b,
                            "object_type": "COMPANY",
                        }
                    )

        return results

    # Title text that reliably indicates an error/removed page rather than
    # real content. Deliberately specific phrases (not a bare "not found",
    # which is too generic and would false-positive on legitimate titles).
    _SOFT_404_TITLE_PHRASES = (
        "404",
        "page not found",
        "article not found",
    )

    # Body phrases only trusted as a soft-404 signal when the surrounding
    # body text is itself very short (see is_soft_404) — a long, real
    # article that happens to quote one of these phrases must not be
    # rejected.
    _SOFT_404_BODY_PHRASES = (
        "page you requested could not be found",
        "page you are looking for",
        "page could not be found",
        "doesn't exist",
        "does not exist",
        "has been removed",
        "no longer available",
        "content unavailable",
        "article has been removed",
        "this content is no longer",
    )

    _SOFT_404_SHORT_BODY_LENGTH = 300

    @classmethod
    def is_soft_404(
        cls,
        title: str | None,
        text: str | None,
    ) -> bool:
        """
        Conservative detection of a page that returned HTTP 200 but is
        actually an error/removed-content page (section 6 of the
        provenance-quality brief). Two independent, narrow signals:

        - the page's own <title> is itself an error title (e.g. "404 -
          Page Not Found | Example"), or
        - the body is very short AND contains one of a small set of
          specific removal/error phrases.

        Deliberately does NOT trigger on a bare "not found" appearing
        anywhere in a long, real article — that would reject legitimate
        content. Used to stop a 404/removed page's own text from being
        parsed into a fabricated IntelligenceObject.
        """
        cleaned_title = cls.clean_text(title).casefold()
        cleaned_text = cls.clean_text(text)

        if cleaned_title and any(
            phrase in cleaned_title for phrase in cls._SOFT_404_TITLE_PHRASES
        ):
            return True

        if len(cleaned_text) <= cls._SOFT_404_SHORT_BODY_LENGTH:
            lowered_text = cleaned_text.casefold()

            if any(
                phrase in lowered_text
                for phrase in cls._SOFT_404_BODY_PHRASES
            ):
                return True

        return False

    @classmethod
    def first_non_empty(
        cls,
        *values: Any,
    ) -> str | None:
        """Return the first supplied value containing meaningful text."""
        for value in values:
            cleaned = cls.clean_optional_text(value)

            if cleaned:
                return cleaned

        return None