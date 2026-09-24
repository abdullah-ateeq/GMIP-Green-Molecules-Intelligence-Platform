from __future__ import annotations

from gmip.intelligence.enums import ConfidenceLevel, IntelligenceType
from gmip.parsers.h2_view_parser import H2ViewParser


def test_can_parse_requires_title_and_url() -> None:
    parser = H2ViewParser()

    assert parser.can_parse(
        {"title": "Some title", "source_url": "https://example.com/"}
    ) is True

    assert parser.can_parse({"title": "Some title"}) is False
    assert parser.can_parse({"source_url": "https://example.com/"}) is False


def test_parse_extracts_known_products_countries_companies() -> None:
    parser = H2ViewParser()

    raw_record = {
        "title": "ACWA Power advances green ammonia project in Saudi Arabia",
        "source_url": "https://www.h2-view.com/story/example/",
        "text": (
            "ACWA Power is progressing a green ammonia and green "
            "hydrogen project in Saudi Arabia."
        ),
        "published_at": "2026-09-20T10:00:00+00:00",
        "metadata": {"categories": ["Green Ammonia", "Projects"]},
    }

    results = parser.parse(raw_record)

    assert len(results) == 1

    intelligence_object = results[0]
    assert intelligence_object.products == ["Green Ammonia", "Green Hydrogen"]
    assert intelligence_object.countries == ["Saudi Arabia"]
    assert intelligence_object.companies == ["ACWA Power"]
    assert intelligence_object.confidence == ConfidenceLevel.MEDIUM
    assert intelligence_object.intelligence_type == IntelligenceType.NEWS
    assert intelligence_object.parser_name == "H2ViewParser"
    assert intelligence_object.source_organisation == "H2 View"


def test_parse_leaves_unmatched_fields_empty_not_fabricated() -> None:
    parser = H2ViewParser()

    raw_record = {
        "title": "A short industry update with no known entities",
        "source_url": "https://www.h2-view.com/story/other/",
        "text": "Something happened somewhere in the industry.",
    }

    results = parser.parse(raw_record)
    intelligence_object = results[0]

    assert intelligence_object.products == []
    assert intelligence_object.countries == []
    assert intelligence_object.companies == []
