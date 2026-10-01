from __future__ import annotations

from typing import Any

from gmip.intelligence.enums import IntelligenceType
from gmip.intelligence.intelligence_object import IntelligenceObject
from gmip.parsers.base_parser import BaseParser


class _DummyParser(BaseParser):
    source_id = "dummy"

    def can_parse(self, raw_record: dict[str, Any]) -> bool:
        return True

    def parse(self, raw_record: dict[str, Any]) -> list[IntelligenceObject]:
        return []


# ------------------------------------------------------------
# is_soft_404
# ------------------------------------------------------------


def test_soft_404_detected_from_error_title() -> None:
    assert _DummyParser.is_soft_404(
        "404 - Page Not Found | Example Site", "Some text."
    ) is True


def test_soft_404_detected_from_short_body_error_phrase() -> None:
    assert _DummyParser.is_soft_404(
        "Example Site",
        "The page you requested could not be found.",
    ) is True


def test_long_real_article_mentioning_not_found_is_not_a_soft_404() -> None:
    """
    A genuine, long article that happens to contain removal-adjacent
    phrasing must not be rejected — the brief explicitly requires
    conservative rules here.
    """
    long_body = (
        "Regulators said the missing shipment documentation could not be "
        "found during the audit, raising questions about compliance at "
        "the terminal. " * 5
    )
    assert _DummyParser.is_soft_404("Audit raises compliance questions", long_body) is False


def test_normal_article_is_not_a_soft_404() -> None:
    assert _DummyParser.is_soft_404(
        "170 firms urge EU to preserve binding green hydrogen targets",
        "A group of 170 European energy sector firms has urged the "
        "European Commission to maintain the binding green hydrogen "
        "transport mandates.",
    ) is False


# ------------------------------------------------------------
# normalize_url
# ------------------------------------------------------------


def test_normalize_url_resolves_relative_to_absolute() -> None:
    parser = _DummyParser(base_url="https://example.test/en/")
    assert parser.normalize_url("/story/example/") == (
        "https://example.test/story/example/"
    )


def test_normalize_url_strips_tracking_params() -> None:
    parser = _DummyParser()
    result = parser.normalize_url(
        "https://example.test/story/example/?utm_source=newsletter&utm_medium=email&id=42"
    )
    assert result == "https://example.test/story/example/?id=42"


def test_normalize_url_strips_fragment() -> None:
    parser = _DummyParser()
    result = parser.normalize_url(
        "https://example.test/story/example/#comments"
    )
    assert result == "https://example.test/story/example/"


def test_normalize_url_keeps_non_tracking_query_params() -> None:
    parser = _DummyParser()
    result = parser.normalize_url(
        "https://example.test/search?query=green+hydrogen&page=2"
    )
    assert result == (
        "https://example.test/search?query=green+hydrogen&page=2"
    )


def test_normalize_url_rejects_non_http_scheme() -> None:
    parser = _DummyParser()
    assert parser.normalize_url("javascript:alert(1)") == ""
