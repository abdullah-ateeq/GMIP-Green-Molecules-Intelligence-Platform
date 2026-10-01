from __future__ import annotations

from gmip.intelligence.enums import EventType, IntelligenceType
from gmip.parsers.base_parser import BaseParser
from gmip.parsers.h2_view_parser import H2ViewParser
from gmip.parsers.hintco_parser import HintcoParser
from gmip.parsers.hydrogen_council_parser import HydrogenCouncilParser


class _DummyParser(BaseParser):
    source_id = "dummy"

    def can_parse(self, raw_record):
        return True

    def parse(self, raw_record):
        return []


def test_detect_offtake_returns_none_without_a_signal_phrase() -> None:
    result = _DummyParser.detect_offtake(
        "Masdar leaves OMV sole project owner of a green hydrogen plant."
    )
    assert result is None


def test_detect_offtake_ignores_generic_supply_language() -> None:
    """
    "will supply" alone is too generic (e.g. a plant supplying the grid) —
    must not fire without one of the specific signal phrases.
    """
    result = _DummyParser.detect_offtake(
        "The plant will supply electricity to the national grid next year."
    )
    assert result is None


def test_detect_offtake_extracts_volume_and_duration() -> None:
    result = _DummyParser.detect_offtake(
        "Uniper locks in 40,000 tonnes per year of e-SAF for over a decade.",
        products=["Sustainable Aviation Fuel"],
    )

    assert result is not None
    assert result.volume == "40,000 tonnes per year"
    assert result.duration == "over a decade"
    assert result.product == "Sustainable Aviation Fuel"
    assert result.producer is None
    assert result.buyer is None


def test_detect_offtake_matches_explicit_offtake_agreement_phrase() -> None:
    result = _DummyParser.detect_offtake(
        "ACWA Power signed an offtake agreement for 1.2 MTPA of green "
        "ammonia.",
        products=["Green Ammonia"],
    )

    assert result is not None
    assert result.volume == "1.2 MTPA"
    assert result.product == "Green Ammonia"


def test_detect_offtake_handles_singular_tonne_without_duration() -> None:
    result = _DummyParser.detect_offtake(
        "Poland's ELQ enters 2,180 tonne hydrogen offtake deal."
    )

    assert result is not None
    assert result.volume == "2,180 tonne"
    assert result.duration is None


def test_hydrogen_council_card_offtake_gets_offtake_intelligence_type() -> None:
    parser = HydrogenCouncilParser()
    raw_record = {
        "source_id": "hydrogen_council_newsroom",
        "source_url": "https://hydrogencouncil.com/en/newsroom/",
        "title": "Hydrogen Council Newsroom",
        "text": (
            "Media Release September 10, 2026 "
            "ACWA Power signs offtake agreement for 1.2 MTPA green ammonia "
            "ACWA Power has signed an offtake agreement with a European "
            "buyer for 1.2 MTPA of green ammonia from its Saudi Arabia "
            "project. Read More"
        ),
    }

    results = parser.parse(raw_record)
    assert len(results) == 1

    offtake_object = results[0]
    assert offtake_object.intelligence_type == IntelligenceType.OFFTAKE
    assert offtake_object.offtake is not None
    assert offtake_object.offtake.volume == "1.2 MTPA"
    assert any(
        event.event_type == EventType.OFFTAKE_SIGNED
        for event in offtake_object.events
    )


def test_h2_view_card_offtake_gets_offtake_intelligence_type() -> None:
    parser = H2ViewParser()
    html = """
    <html><body>
    <div class="card">
      <a href="https://www.gasworld.com/story/uniper-locks-in-e-saf/2260404.article/">
        Uniper locks in 40,000 tonnes per year of e-SAF for over a decade
      </a>
      Mobility 3 days ago 1 min read
    </div>
    </body></html>
    """
    raw_record = {
        "title": "H2 View | gasworld",
        "source_url": "https://www.gasworld.com/h2-view/",
        "html": html,
        "collected_at": "2026-09-19T12:00:00+00:00",
    }

    results = parser.parse(raw_record)
    assert len(results) == 1

    offtake_object = results[0]
    assert offtake_object.intelligence_type == IntelligenceType.OFFTAKE
    assert offtake_object.offtake is not None
    assert offtake_object.offtake.volume == "40,000 tonnes per year"
    assert offtake_object.offtake.duration == "over a decade"
    assert any(
        event.event_type == EventType.OFFTAKE_SIGNED
        for event in offtake_object.events
    )


def test_hintco_news_item_offtake_gets_offtake_intelligence_type() -> None:
    parser = HintcoParser()
    raw_record = {
        "source_id": "hintco_news",
        "source_url": "https://hintco.eu/news/",
        "title": "Hintco News",
        "text": (
            "A producer signed an offtake agreement for 50,000 tonnes per "
            "year of green ammonia with a European importer. 12 March, 2026 "
            "Read more"
        ),
    }

    results = parser.parse(raw_record)
    assert len(results) == 1

    offtake_object = results[0]
    assert offtake_object.intelligence_type == IntelligenceType.OFFTAKE
    assert offtake_object.offtake is not None
    assert any(
        event.event_type == EventType.OFFTAKE_SIGNED
        for event in offtake_object.events
    )
