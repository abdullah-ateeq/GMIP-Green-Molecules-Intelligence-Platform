from __future__ import annotations

from gmip.intelligence.enums import EventType, IntelligenceType
from gmip.parsers.hydrogen_council_parser import HydrogenCouncilParser

# Representative excerpt, structurally identical to real captured pages
# (see Data/Raw/hydrogen_council_intelligence.txt) but trimmed down.
INTELLIGENCE_PAGE_TEXT = """
Intelligence Looking for the latest information, reports and data? Report
September 8, 2025 Global Hydrogen Compass Global Hydrogen Compass 2025 is a
new flagship publication that combines comprehensive industry data with
insights from Hydrogen Council members active in Saudi Arabia. Read More
Podcast October 19, 2023 Transformative hydrogen projects Join Hydrogen
Council and Wood plc as they discuss transformative green hydrogen projects.
Read More
"""

NEWSROOM_PAGE_TEXT = """
Latest News Media Release June 29, 2026 20+ associations endorse the
Call-to-Action: Hydrogen for a resilient world Last month, at the World
Hydrogen Summit in Rotterdam, we launched this call to action. Read More
Council Updates April 14, 2026 Seven New Companies Join the Hydrogen
Council, Strengthening the Global Industry Coalition Advancing Hydrogen
Solutions including ACWA Power. Read More
"""

HOME_PAGE_TEXT = "Hydrogen Council is a global CEO-led initiative."


def _raw_record(source_id: str, text: str) -> dict:
    return {
        "title": f"Hydrogen Council {source_id}",
        "source_url": f"https://hydrogencouncil.com/en/{source_id}/",
        "source_id": source_id,
        "text": text,
    }


def test_can_parse_requires_title_and_url() -> None:
    parser = HydrogenCouncilParser()

    assert parser.can_parse(
        {"title": "x", "source_url": "https://hydrogencouncil.com/"}
    ) is True
    assert parser.can_parse({"title": "x"}) is False


def test_intelligence_page_extracts_report_items() -> None:
    parser = HydrogenCouncilParser()
    raw_record = _raw_record(
        "hydrogen_council_intelligence", INTELLIGENCE_PAGE_TEXT
    )

    results = parser.parse(raw_record)

    assert len(results) == 2

    report, podcast = results
    assert report.title == "Global Hydrogen Compass"
    assert report.categories == ["Report"]
    assert report.intelligence_type == IntelligenceType.REPORT
    assert report.published_at.date().isoformat() == "2025-09-08"
    assert "Saudi Arabia" in report.countries
    assert any(
        event.event_type == EventType.REPORT_PUBLISHED
        for event in report.events
    )

    assert podcast.categories == ["Podcast"]
    assert podcast.published_at.date().isoformat() == "2023-10-19"


def test_newsroom_page_uses_strategic_categories_not_hintco_vocabulary() -> None:
    """
    Regression guard for the exact architecture drift flagged in the
    earlier audit: Hydrogen Council content must not be classified using
    Hintco's tender/auction vocabulary.
    """
    parser = HydrogenCouncilParser()
    raw_record = _raw_record("hydrogen_council_newsroom", NEWSROOM_PAGE_TEXT)

    results = parser.parse(raw_record)

    assert len(results) == 2

    media_release, council_update = results
    assert media_release.categories == ["Media Release"]
    assert media_release.intelligence_type == IntelligenceType.NEWS
    assert media_release.tender is None
    assert media_release.tender_type is None

    assert council_update.categories == ["Council Updates"]
    assert "ACWA Power" in council_update.companies


def test_whole_page_fallback_for_home_and_members() -> None:
    parser = HydrogenCouncilParser()
    raw_record = _raw_record("hydrogen_council_home", HOME_PAGE_TEXT)

    results = parser.parse(raw_record)

    assert len(results) == 1
    assert results[0].intelligence_type == IntelligenceType.COMPANY_UPDATE
