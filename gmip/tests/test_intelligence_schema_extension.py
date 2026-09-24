from __future__ import annotations

from datetime import date

from gmip.intelligence.enums import IntelligenceType
from gmip.intelligence.intelligence_object import (
    IntelligenceObject,
    OfftakeDetails,
    TenderDetails,
)


def _base_kwargs() -> dict:
    return {
        "title": "Test object",
        "source_organisation": "Hintco",
        "source_id": "hintco",
        "source_url": "https://hintco.eu/hpa-auctions/",
        "intelligence_type": IntelligenceType.TENDER,
    }


def test_new_scalar_fields_default_to_none() -> None:
    obj = IntelligenceObject(**_base_kwargs())

    assert obj.capacity is None
    assert obj.capex is None
    assert obj.fid_date is None
    assert obj.cod_date is None
    assert obj.commercial_theme is None
    assert obj.policy_theme is None
    assert obj.tender_type is None
    assert obj.tender is None
    assert obj.offtake is None


def test_tender_details_round_trips_through_to_dict() -> None:
    obj = IntelligenceObject(
        **_base_kwargs(),
        tender=TenderDetails(
            buyer="Hintco",
            volume="EUR 587 million",
            region="Africa",
            deadline=date(2026, 11, 15),
            tender_status="Open",
        ),
    )

    result = obj.to_dict()

    assert result["tender"]["buyer"] == "Hintco"
    assert result["tender"]["deadline"] == "2026-11-15"
    assert result["tender"]["tender_status"] == "Open"


def test_offtake_details_round_trips_through_to_dict() -> None:
    obj = IntelligenceObject(
        **_base_kwargs(),
        offtake=OfftakeDetails(
            producer="ACWA Power",
            buyer="Fertiglobe",
            delivery_start=date(2028, 1, 1),
        ),
    )

    result = obj.to_dict()

    assert result["offtake"]["producer"] == "ACWA Power"
    assert result["offtake"]["delivery_start"] == "2028-01-01"


def test_fid_and_cod_dates_serialize_as_iso_strings() -> None:
    obj = IntelligenceObject(
        **_base_kwargs(),
        fid_date=date(2027, 3, 1),
        cod_date=date(2030, 6, 1),
    )

    result = obj.to_dict()

    assert result["fid_date"] == "2027-03-01"
    assert result["cod_date"] == "2030-06-01"


def test_content_hash_changes_when_tender_details_change() -> None:
    base = IntelligenceObject(**_base_kwargs())
    with_tender = IntelligenceObject(
        **_base_kwargs(),
        tender=TenderDetails(buyer="Hintco"),
    )

    assert base.content_hash != with_tender.content_hash


def test_object_without_tender_or_offtake_serializes_cleanly() -> None:
    obj = IntelligenceObject(**_base_kwargs())
    result = obj.to_dict()

    assert result["tender"] is None
    assert result["offtake"] is None

    # Must not raise even though there's nothing to serialize.
    obj.to_json()
