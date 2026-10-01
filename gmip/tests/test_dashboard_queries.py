from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import database  # noqa: E402
from gmip.intelligence.enums import EventType, IntelligenceType  # noqa: E402
from gmip.intelligence.intelligence_object import (  # noqa: E402
    EventReference,
    IntelligenceObject,
    TenderDetails,
)


def _tender(
    title: str,
    tender_status: str | None,
    identity_key: str | None = None,
    products=None,
    countries=None,
) -> IntelligenceObject:
    obj = IntelligenceObject(
        title=title,
        source_organisation="Hintco",
        source_id="hintco",
        source_url=f"https://hintco.eu/{title.lower().replace(' ', '-')}/",
        intelligence_type=IntelligenceType.TENDER,
        products=products or [],
        countries=countries or [],
        tender=TenderDetails(tender_status=tender_status),
        identity_key=identity_key,
    )
    return obj


def _setup_db(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()


def test_open_opportunities_excludes_closed(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)

    database.save_intelligence_object(_tender("Open Lot", "Open"))
    database.save_intelligence_object(_tender("Closed Lot", "Closed"))
    database.save_intelligence_object(_tender("Unset Status Lot", None))

    counts = database.get_open_opportunities_count()

    assert counts["open"] == 2  # Open + unset-status (not disqualified)
    assert counts["closed"] == 1


def test_event_type_count_matches_only_requested_types(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    offtake_obj = IntelligenceObject(
        title="Offtake deal",
        source_organisation="H2 View",
        source_id="h2_view",
        source_url="https://www.gasworld.com/story/offtake/1.article/",
        intelligence_type=IntelligenceType.OFFTAKE,
    )
    offtake_obj.add_event(
        EventReference(
            event_type=EventType.OFFTAKE_SIGNED,
            description="Offtake deal",
        )
    )

    report_obj = IntelligenceObject(
        title="A report",
        source_organisation="Hydrogen Council",
        source_id="hydrogen_council",
        source_url="https://hydrogencouncil.com/en/report/",
        intelligence_type=IntelligenceType.REPORT,
    )
    report_obj.add_event(
        EventReference(
            event_type=EventType.REPORT_PUBLISHED,
            description="A report",
        )
    )

    database.save_intelligence_object(offtake_obj)
    database.save_intelligence_object(report_obj)

    assert database.get_event_type_count({"offtake_signed"}) == 1
    assert database.get_event_type_count({"fid_reached"}) == 0


def test_business_kpis_reflect_real_data_not_legacy_snapshots(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    database.save_intelligence_object(_tender("Open Lot", "Open"))
    database.save_intelligence_object(_tender("Closed Lot", "Closed"))

    kpis = database.get_business_kpis()

    assert kpis["new_intelligence_total"] == 2
    assert kpis["open_opportunities"] == 1
    assert kpis["closed_opportunities"] == 1
    # No parser currently emits FID_REACHED — must honestly report 0,
    # never a fabricated placeholder value.
    assert kpis["fid_count_30d"] == 0
    assert kpis["offtake_count_30d"] == 0


def test_source_category_distribution_groups_by_registry_category(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    database.save_intelligence_object(_tender("Open Lot", "Open"))

    hc_obj = IntelligenceObject(
        title="HC article",
        source_organisation="Hydrogen Council",
        source_id="hydrogen_council",
        source_url="https://hydrogencouncil.com/en/article/",
        intelligence_type=IntelligenceType.NEWS,
    )
    database.save_intelligence_object(hc_obj)

    distribution = {
        row["source_category"]: row["total"]
        for row in database.get_source_category_distribution()
    }

    assert distribution["official_procurement"] == 1
    assert distribution["industry_body"] == 1


def test_opportunity_radar_excludes_closed_and_dedupes_by_identity(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    database.save_intelligence_object(
        _tender(
            "Lot A",
            "Open",
            identity_key="hintco:lot-a",
            products=["Green Hydrogen"],
            countries=["Germany"],
        )
    )
    database.save_intelligence_object(
        _tender("Closed Lot", "Closed", identity_key="hintco:closed-lot")
    )

    # A second, newer update to the same logical lot — same identity_key.
    updated = _tender(
        "Lot A",
        "Open",
        identity_key="hintco:lot-a",
        products=["Green Hydrogen", "Green Ammonia"],
        countries=["Germany"],
    )
    database.save_intelligence_object(updated)

    radar = database.get_opportunity_radar()

    assert len(radar) == 1
    assert radar[0]["title"] == "Lot A"
    assert radar[0]["product"] == "Green Ammonia" or radar[0]["product"] == (
        "Green Hydrogen"
    )
    assert radar[0]["country"] == "Germany"
    assert radar[0]["priority"] in {"High", "Medium", "Low"}


def test_opportunity_radar_returns_empty_without_fabricating(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    assert database.get_opportunity_radar() == []


def test_business_activity_series_groups_events_by_day_and_category(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    offtake_obj = IntelligenceObject(
        title="Offtake deal",
        source_organisation="H2 View",
        source_id="h2_view",
        source_url="https://www.gasworld.com/story/offtake/2.article/",
        intelligence_type=IntelligenceType.OFFTAKE,
    )
    offtake_obj.add_event(
        EventReference(
            event_type=EventType.OFFTAKE_SIGNED,
            description="Offtake deal",
        )
    )
    database.save_intelligence_object(offtake_obj)

    series = database.get_business_activity_series(days=30)

    assert len(series) == 1
    assert series[0]["offtake"] == 1
    assert series[0]["projects"] == 0
    assert series[0]["fid"] == 0


def test_market_signals_require_minimum_supporting_events(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    # Two offtake events in Germany — below the minimum threshold (3).
    for index in range(2):
        obj = IntelligenceObject(
            title=f"Offtake deal {index}",
            source_organisation="H2 View",
            source_id="h2_view",
            source_url=f"https://www.gasworld.com/story/offtake-{index}/{index}.article/",
            intelligence_type=IntelligenceType.OFFTAKE,
            countries=["Germany"],
        )
        obj.add_event(
            EventReference(
                event_type=EventType.OFFTAKE_SIGNED,
                description="Offtake deal",
            )
        )
        database.save_intelligence_object(obj)

    assert database.get_market_signals() == []

    # A third event crosses the threshold.
    obj = IntelligenceObject(
        title="Offtake deal 2",
        source_organisation="H2 View",
        source_id="h2_view",
        source_url="https://www.gasworld.com/story/offtake-2/2.article/",
        intelligence_type=IntelligenceType.OFFTAKE,
        countries=["Germany"],
    )
    obj.add_event(
        EventReference(
            event_type=EventType.OFFTAKE_SIGNED,
            description="Offtake deal",
        )
    )
    database.save_intelligence_object(obj)

    signals = database.get_market_signals()

    assert len(signals) == 1
    assert signals[0]["signal_type"] == "OFFTAKE MOMENTUM"
    assert signals[0]["region"] == "Germany"
    assert signals[0]["supporting_event_count"] == 3
