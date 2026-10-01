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


def test_update_source_availability_persists_result(
    tmp_path, monkeypatch
) -> None:
    import datetime

    _setup_db(tmp_path, monkeypatch)

    obj = _tender("Open Lot", "Open")
    database.save_intelligence_object(obj)

    checked_at = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    database.update_source_availability(
        intelligence_id=obj.intelligence_id,
        available=False,
        status="UNAVAILABLE",
        http_status=404,
        checked_at=checked_at,
    )

    rows = database.get_recent_intelligence_objects(source_id="hintco")
    assert rows[0]["source_available"] == 0
    assert rows[0]["source_status"] == "UNAVAILABLE"
    assert rows[0]["source_http_status"] == 404
    assert rows[0]["last_source_checked_at"] == checked_at.isoformat()


def test_objects_needing_source_check_excludes_already_checked(
    tmp_path, monkeypatch
) -> None:
    import datetime

    _setup_db(tmp_path, monkeypatch)

    checked_obj = _tender("Checked Lot", "Open")
    unchecked_obj = _tender("Unchecked Lot", "Open")
    database.save_intelligence_object(checked_obj)
    database.save_intelligence_object(unchecked_obj)

    database.update_source_availability(
        intelligence_id=checked_obj.intelligence_id,
        available=True,
        status="AVAILABLE",
        http_status=200,
        checked_at=datetime.datetime.now(datetime.timezone.utc),
    )

    pending = database.get_intelligence_objects_needing_source_check()
    pending_ids = {row["intelligence_id"] for row in pending}

    assert checked_obj.intelligence_id not in pending_ids
    assert unchecked_obj.intelligence_id in pending_ids


def test_reclassify_region_mentions_moves_region_out_of_countries(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    obj = IntelligenceObject(
        title="Hydrogen momentum builds across Africa",
        source_organisation="Hydrogen Council",
        source_id="hydrogen_council",
        source_url="https://hydrogencouncil.com/en/africa-momentum/",
        intelligence_type=IntelligenceType.NEWS,
        countries=["Africa", "Germany"],
    )
    database.save_intelligence_object(obj)

    corrected = database.reclassify_region_mentions_as_regions()
    assert corrected == 1

    rows = database.get_recent_intelligence_objects(source_id="hydrogen_council")
    import json as json_module

    assert json_module.loads(rows[0]["countries"]) == ["Germany"]

    payload = json_module.loads(rows[0]["payload_json"])
    assert payload["countries"] == ["Germany"]
    assert "Africa" in payload["regions"]


def test_reclassify_region_mentions_is_idempotent(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)

    obj = IntelligenceObject(
        title="A clean record",
        source_organisation="Hydrogen Council",
        source_id="hydrogen_council",
        source_url="https://hydrogencouncil.com/en/clean/",
        intelligence_type=IntelligenceType.NEWS,
        countries=["Germany"],
    )
    database.save_intelligence_object(obj)

    assert database.reclassify_region_mentions_as_regions() == 0
    assert database.reclassify_region_mentions_as_regions() == 0


def test_delete_non_intelligence_records_removes_exact_match_only(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    homepage_obj = IntelligenceObject(
        title="Homepage | Hydrogen Council",
        source_organisation="Hydrogen Council",
        source_id="hydrogen_council",
        source_url="https://hydrogencouncil.com/en/",
        intelligence_type=IntelligenceType.COMPANY_UPDATE,
    )
    real_obj = IntelligenceObject(
        title="Six new members join Hydrogen Council",
        source_organisation="Hydrogen Council",
        source_id="hydrogen_council",
        source_url="https://hydrogencouncil.com/en/six-new-members/",
        intelligence_type=IntelligenceType.NEWS,
    )
    database.save_intelligence_object(homepage_obj)
    database.save_intelligence_object(real_obj)

    deleted = database.delete_non_intelligence_records(
        "hydrogen_council", "Homepage | Hydrogen Council"
    )
    assert deleted == 1

    remaining = database.get_recent_intelligence_objects(
        source_id="hydrogen_council"
    )
    assert len(remaining) == 1
    assert remaining[0]["title"] == "Six new members join Hydrogen Council"


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
