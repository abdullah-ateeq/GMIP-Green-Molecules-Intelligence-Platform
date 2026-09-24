from __future__ import annotations

from gmip.intelligence.enums import EventType, IntelligenceType
from gmip.parsers.hintco_parser import HintcoParser

# Representative excerpt, structurally identical to real captured Hintco
# lot pages (see Data/Raw/hintco_hpa_auctions.txt) but trimmed down.
LOT_PAGE_TEXT = """
About Who we are The H2Global Mechanism Tenders HPA Auctions HSA Auctions News FAQ
HPA Auctions Through its purchase auctions, Hintco identifies the most
competitive suppliers of renewable hydrogen. Global Lot (GL) Products: RFNBO
hydrogen Region: All countries¹ Volume: EUR 597.9 million Tender 2 The
application phase for the Global Lot has ended African Lot (AFL) Products:
RFNBO ammonia, RFNBO hydrogen, RFNBO methanol Region: Africa¹ Volume: min.
EUR 587 million Access tender platform
"""

NEWS_PAGE_TEXT = """
About Who we are The H2Global Mechanism Tenders HPA Auctions HSA Auctions News FAQ
News Hintco boosts funding and extends contract timelines for H2Global tenders
Hamburg, 22 September 2025: Hintco has announced a series of updates across
its H2Global tenders that will increase funding and extend timelines. Read more
Hintco opens Application Phase for four regional lots Hamburg, 04 July, 2025 –
Hintco has entered the Application Phase for the regional lots of its 2025
competitive auction for renewable hydrogen. Read more
"""

FAQ_PAGE_TEXT = "Frequently asked questions about the Hintco tender process."


def _raw_record(source_id: str, text: str, source_type: str | None = None) -> dict:
    return {
        "title": f"Hintco {source_id}",
        "source_url": f"https://hintco.eu/{source_id}/",
        "source_id": source_id,
        "text": text,
        "metadata": {"source_type": source_type} if source_type else {},
    }


def test_can_parse_requires_title_and_url() -> None:
    parser = HintcoParser()

    assert parser.can_parse(
        {"title": "x", "source_url": "https://hintco.eu/"}
    ) is True
    assert parser.can_parse({"title": "x"}) is False


def test_lot_page_extracts_one_object_per_lot() -> None:
    parser = HintcoParser()
    raw_record = _raw_record(
        "hintco_hpa_auctions", LOT_PAGE_TEXT, "Supply-Side Auction"
    )

    results = parser.parse(raw_record)

    assert len(results) == 2

    global_lot, african_lot = results
    assert global_lot.title == "Global Lot (GL)"
    assert global_lot.products == ["RFNBO hydrogen"]
    assert global_lot.tender is not None
    assert global_lot.tender.region == "All countries"
    assert global_lot.tender.volume == "EUR 597.9 million"
    assert global_lot.tender.tender_status == "Closed"
    assert global_lot.tender_type == "Supply-Side Auction"
    assert global_lot.intelligence_type == IntelligenceType.TENDER

    assert african_lot.title == "African Lot (AFL)"
    assert sorted(african_lot.products) == [
        "RFNBO ammonia",
        "RFNBO hydrogen",
        "RFNBO methanol",
    ]
    assert african_lot.tender.tender_status == "Open"


def test_lot_page_does_not_fabricate_missing_deadline() -> None:
    parser = HintcoParser()
    raw_record = _raw_record("hintco_hpa_auctions", LOT_PAGE_TEXT)

    results = parser.parse(raw_record)

    for result in results:
        assert result.tender.deadline is None


def test_news_page_extracts_items_with_dates_and_events() -> None:
    parser = HintcoParser()
    raw_record = _raw_record("hintco_news", NEWS_PAGE_TEXT)

    results = parser.parse(raw_record)

    assert len(results) == 2

    funding_item, launch_item = results
    assert "boosts funding" in funding_item.title.lower()
    assert funding_item.published_at is not None
    assert funding_item.published_at.date().isoformat() == "2025-09-22"
    assert any(
        event.event_type == EventType.FUNDING_APPROVED
        for event in funding_item.events
    )

    assert "opens application phase" in launch_item.title.lower()
    assert launch_item.published_at.date().isoformat() == "2025-07-04"
    assert any(
        event.event_type == EventType.TENDER_LAUNCHED
        for event in launch_item.events
    )


def test_unrecognised_page_falls_back_to_whole_page_object() -> None:
    parser = HintcoParser()
    raw_record = _raw_record("hintco_general_faq", FAQ_PAGE_TEXT)

    results = parser.parse(raw_record)

    assert len(results) == 1
    assert results[0].intelligence_type == IntelligenceType.OTHER
    assert results[0].tender is None
