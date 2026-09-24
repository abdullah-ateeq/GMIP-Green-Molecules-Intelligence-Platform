from datetime import datetime, timezone

from gmip.intelligence.enums import (
    EventType,
    IntelligenceType,
)
from gmip.intelligence.intelligence_object import (
    EntityReference,
    EventReference,
    IntelligenceObject,
    RelationshipReference,
)


def test_intelligence_object() -> None:
    intelligence = IntelligenceObject(
        title="Hydrogen Council publishes new market report",
        summary=(
            "A strategic report assessing global hydrogen "
            "investment and project development."
        ),
        source_organisation="Hydrogen Council",
        source_id="hydrogen_council_intelligence",
        source_url="https://hydrogencouncil.com/en/intelligence/",
        intelligence_type=IntelligenceType.REPORT,
        collector_name="HydrogenCouncilCollector",
        parser_name="HydrogenCouncilIntelligenceParser",
        published_at=datetime(
            2026,
            7,
            24,
            tzinfo=timezone.utc,
        ),
        products=[
            "Green Hydrogen",
            "Green Ammonia",
            "Green Hydrogen",
        ],
        countries=["Germany", "Saudi Arabia"],
        companies=["ACWA Power"],
        keywords=[
            "investment",
            "hydrogen projects",
            "market outlook",
        ],
    )

    intelligence.add_entity(
        EntityReference(
            name="ACWA Power",
            entity_type="company",
        )
    )

    intelligence.add_entity(
        EntityReference(
            name="Saudi Arabia",
            entity_type="country",
        )
    )

    intelligence.add_event(
        EventReference(
            event_type=EventType.REPORT_PUBLISHED,
            description="Hydrogen Council published a new market report.",
        )
    )

    intelligence.add_relationship(
        RelationshipReference(
            subject="ACWA Power",
            predicate="operates_in",
            object="Saudi Arabia",
        )
    )

    print("=" * 70)
    print("GMIP INTELLIGENCE OBJECT TEST")
    print("=" * 70)
    print(intelligence.to_json())
    print("=" * 70)
    print("TEST PASSED")
    print(f"Intelligence ID: {intelligence.intelligence_id}")
    print(f"Content Hash: {intelligence.content_hash}")


if __name__ == "__main__":
    test_intelligence_object()