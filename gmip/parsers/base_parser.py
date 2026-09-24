from __future__ import annotations

import html
import logging
import re

from abc import ABC, abstractmethod
from datetime import date, datetime, timezone
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

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
        tender: TenderDetails | None = None,
        offtake: OfftakeDetails | None = None,
        commercial_relevance: str | None = None,
        why_it_matters: str | None = None,
        recommended_action: str | None = None,
        metadata: dict[str, Any] | None = None,
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

    def normalize_url(
        self,
        url: Any,
    ) -> str:
        """
        Convert relative URLs to absolute URLs and validate the result.
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

        return cleaned_url

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
        """
        cleaned_text = cls.clean_text(text).casefold()

        if not cleaned_text:
            return []

        matches = []

        for keyword in candidate_keywords:
            cleaned_keyword = cls.clean_text(keyword)

            if (
                cleaned_keyword
                and cleaned_keyword.casefold() in cleaned_text
            ):
                matches.append(cleaned_keyword)

        return cls.normalize_string_list(matches)

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