from __future__ import annotations

from gmip.intelligence.enums import EventType, IntelligenceType
from gmip.intelligence.intelligence_object import IntelligenceObject

REQUIRED_INTELLIGENCE_TYPES = {
    "report", "news", "tender", "project", "policy", "offtake",
    "investment", "market_metric", "company_update", "technology",
    "funding", "port_infrastructure", "other",
}

REQUIRED_EVENT_TYPES = {
    "tender_launched", "tender_updated", "new_lot", "deadline_changed",
    "eligibility_changed", "amendment", "tender_cancelled",
    "future_auction_announced", "contract_awarded",
    "new_report", "report_updated", "new_intelligence_item",
    "pdf_added", "pdf_replaced", "project_milestone", "policy_update",
    "market_statistic_update", "membership_signal", "partnership_signed",
    "fid_reached", "cod_reached", "offtake_signed", "other",
}


def test_intelligence_type_covers_required_values() -> None:
    actual = {member.value for member in IntelligenceType}
    missing = REQUIRED_INTELLIGENCE_TYPES - actual
    assert not missing, f"Missing IntelligenceType values: {missing}"


def test_event_type_covers_required_values() -> None:
    actual = {member.value for member in EventType}
    missing = REQUIRED_EVENT_TYPES - actual
    assert not missing, f"Missing EventType values: {missing}"


def test_project_stage_and_raw_document_id_are_settable() -> None:
    obj = IntelligenceObject(
        title="NEOM Green Hydrogen reaches FID",
        source_organisation="Hydrogen Council",
        source_id="hydrogen_council",
        source_url="https://hydrogencouncil.com/en/intelligence/",
        intelligence_type=IntelligenceType.PROJECT,
        project_stage="FID",
        raw_document_id="doc-123",
    )

    assert obj.project_stage == "FID"
    assert obj.raw_document_id == "doc-123"

    result = obj.to_dict()
    assert result["project_stage"] == "FID"
    assert result["raw_document_id"] == "doc-123"
