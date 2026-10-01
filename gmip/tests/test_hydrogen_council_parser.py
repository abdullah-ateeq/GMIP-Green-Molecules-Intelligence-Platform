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

# WordPress wraps each card's headline in an <a> to the real article — see
# gmip/parsers/hydrogen_council_parser.py's _extract_article_links().
INTELLIGENCE_PAGE_HTML = """
<html><body>
<a href="https://hydrogencouncil.com/en/global-hydrogen-compass-2025/">
  Global Hydrogen Compass
</a>
<p>Report September 8, 2025 Global Hydrogen Compass Global Hydrogen Compass
2025 is a new flagship publication that combines comprehensive industry
data with insights from Hydrogen Council members active in Saudi Arabia.</p>
<a href="https://hydrogencouncil.com/en/global-hydrogen-compass-2025/">Read More</a>
<a href="https://hydrogencouncil.com/en/podcast-transformative-hydrogen-projects/">
  Transformative hydrogen projects
</a>
<p>Podcast October 19, 2023 Transformative hydrogen projects Join Hydrogen
Council and Wood plc as they discuss transformative green hydrogen projects.</p>
<a href="https://hydrogencouncil.com/en/podcast-transformative-hydrogen-projects/">Read More</a>
</body></html>
"""


def _raw_record(source_id: str, text: str, html: str | None = None) -> dict:
    return {
        "title": f"Hydrogen Council {source_id}",
        "source_url": f"https://hydrogencouncil.com/en/{source_id}/",
        "source_id": source_id,
        "text": text,
        "html": html,
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


def test_card_gets_exact_article_link_when_html_available() -> None:
    """
    Regression guard for a real user-reported bug: without HTML, every
    card's link fell back to the listing page instead of the actual
    article. With HTML, the real per-article URL (from the headline's own
    <a> tag) must be used instead.
    """
    parser = HydrogenCouncilParser()
    raw_record = _raw_record(
        "hydrogen_council_intelligence",
        INTELLIGENCE_PAGE_TEXT,
        html=INTELLIGENCE_PAGE_HTML,
    )

    results = parser.parse(raw_record)

    assert len(results) == 2

    report, podcast = results
    assert report.source_url == (
        "https://hydrogencouncil.com/en/global-hydrogen-compass-2025/"
    )
    assert podcast.source_url == (
        "https://hydrogencouncil.com/en/podcast-transformative-hydrogen-projects/"
    )


def test_card_falls_back_to_listing_url_without_html() -> None:
    """Backward-compatible: no html means the old listing-page fallback."""
    parser = HydrogenCouncilParser()
    raw_record = _raw_record(
        "hydrogen_council_intelligence", INTELLIGENCE_PAGE_TEXT
    )

    results = parser.parse(raw_record)

    assert all(
        r.source_url == raw_record["source_url"] for r in results
    )


def test_home_and_members_pages_produce_no_intelligence_objects() -> None:
    """
    Pure navigation/landing pages (corporate homepage, members grid) are
    discovery input, not business intelligence — they stay RawDocuments
    (collected, change-detected) but must never become a "Homepage |
    Hydrogen Council"-style IntelligenceObject in Latest Intelligence
    (provenance-quality brief, section 13-17).
    """
    parser = HydrogenCouncilParser()
    raw_record = _raw_record("hydrogen_council_home", HOME_PAGE_TEXT)

    results = parser.parse(raw_record)

    assert results == []


def test_region_mentions_go_to_regions_not_countries() -> None:
    """
    "Africa" (and other continents) must never populate `countries` —
    that's what corrupted the dashboard's Top Countries table with a
    region pretending to be a country (provenance-quality brief, section
    19-20).
    """
    parser = HydrogenCouncilParser()
    raw_record = _raw_record(
        "hydrogen_council_newsroom",
        "Media Release June 29, 2026 Hydrogen momentum builds across "
        "Africa New projects are advancing hydrogen deployment across "
        "Africa this year. Read More",
    )

    results = parser.parse(raw_record)
    assert len(results) == 1

    assert "Africa" not in results[0].countries
    assert "Africa" in results[0].regions


def test_404_page_produces_no_intelligence_object() -> None:
    parser = HydrogenCouncilParser()
    raw_record = _raw_record(
        "hydrogen_council_newsroom",
        "404 Page Not Found We could not find the page you requested.",
    )
    raw_record["title"] = "404 - Page Not Found | Hydrogen Council"

    results = parser.parse(raw_record)

    assert results == []


def test_card_extracts_real_company_mentions_and_excludes_self() -> None:
    """
    Company candidates are drawn from the shared entity seed list
    (gmip/entities/seed.py) so HydrogenCouncilParser recognizes the same
    companies as every other parser — but "Hydrogen Council" itself is
    excluded, since every HC article would otherwise self-tag as
    mentioning its own publisher.
    """
    parser = HydrogenCouncilParser()
    raw_record = _raw_record(
        "hydrogen_council_intelligence",
        "Report March 11, 2025 Hydrogen: Closing the cost gap The "
        "Hydrogen: Closing the Cost Gap report, developed with the "
        "analytical support of McKinsey & Company, highlights progress "
        "by the Hydrogen Council. Read More",
    )

    results = parser.parse(raw_record)
    assert len(results) == 1

    assert "McKinsey & Company" in results[0].companies
    assert "Hydrogen Council" not in results[0].companies
