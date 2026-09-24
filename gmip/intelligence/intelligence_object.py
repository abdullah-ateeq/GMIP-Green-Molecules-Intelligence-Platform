from __future__ import annotations

import hashlib
import json
import uuid

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from gmip.intelligence.enums import (
    ConfidenceLevel,
    EventType,
    ImportanceLevel,
    IntelligenceStatus,
    IntelligenceType,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


@dataclass(slots=True)
class EntityReference:
    name: str
    entity_type: str
    canonical_name: str | None = None
    external_id: str | None = None
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.name = self.name.strip()

        if not self.name:
            raise ValueError("Entity name cannot be empty.")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "Entity confidence must be between 0.0 and 1.0."
            )


@dataclass(slots=True)
class EventReference:
    event_type: EventType
    description: str
    event_date: date | None = None
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.description = self.description.strip()

        if not self.description:
            raise ValueError("Event description cannot be empty.")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "Event confidence must be between 0.0 and 1.0."
            )


@dataclass(slots=True)
class RelationshipReference:
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.subject = self.subject.strip()
        self.predicate = self.predicate.strip()
        self.object = self.object.strip()

        if not all(
            (
                self.subject,
                self.predicate,
                self.object,
            )
        ):
            raise ValueError(
                "Relationship subject, predicate and object cannot be empty."
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "Relationship confidence must be between 0.0 and 1.0."
            )


@dataclass(slots=True)
class TenderDetails:
    """Structured tender/auction facts, for TENDER-type intelligence."""

    buyer: str | None = None
    opportunity_type: str | None = None
    volume: str | None = None
    region: str | None = None
    lot: str | None = None
    deadline: date | None = None
    tender_status: str | None = None


@dataclass(slots=True)
class OfftakeDetails:
    """Structured offtake-agreement facts (producer/buyer/volume/route)."""

    producer: str | None = None
    buyer: str | None = None
    product: str | None = None
    volume: str | None = None
    duration: str | None = None
    price: str | None = None
    delivery_start: date | None = None
    shipping_route: str | None = None
    receiving_terminal: str | None = None


@dataclass(slots=True)
class IntelligenceObject:
    title: str
    source_organisation: str
    source_id: str
    source_url: str
    intelligence_type: IntelligenceType

    intelligence_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    summary: str | None = None
    raw_text: str | None = None

    published_at: datetime | None = None
    collected_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    language: str = "en"
    status: IntelligenceStatus = IntelligenceStatus.NEW
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    importance: ImportanceLevel = ImportanceLevel.MEDIUM

    collector_name: str | None = None
    parser_name: str | None = None

    categories: list[str] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)
    companies: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    people: list[str] = field(default_factory=list)
    policies: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    entities: list[EntityReference] = field(default_factory=list)
    events: list[EventReference] = field(default_factory=list)
    relationships: list[RelationshipReference] = field(default_factory=list)

    capacity: str | None = None
    capex: str | None = None
    fid_date: date | None = None
    cod_date: date | None = None

    commercial_theme: str | None = None
    policy_theme: str | None = None
    tender_type: str | None = None

    tender: TenderDetails | None = None
    offtake: OfftakeDetails | None = None

    commercial_relevance: str | None = None
    why_it_matters: str | None = None
    recommended_action: str | None = None

    attachments: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    content_hash: str | None = None

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        self.source_organisation = self.source_organisation.strip()
        self.source_id = self.source_id.strip()
        self.source_url = self.source_url.strip()

        if not self.title:
            raise ValueError("Intelligence title cannot be empty.")

        if not self.source_organisation:
            raise ValueError("Source organisation cannot be empty.")

        if not self.source_id:
            raise ValueError("Source ID cannot be empty.")

        if not self.source_url.startswith(
            (
                "http://",
                "https://",
            )
        ):
            raise ValueError(
                "Source URL must begin with http:// or https://."
            )

        self._normalise_lists()

        if self.content_hash is None:
            self.content_hash = self.generate_content_hash()

    def _normalise_lists(self) -> None:
        list_fields = (
            "categories",
            "products",
            "countries",
            "companies",
            "projects",
            "technologies",
            "people",
            "policies",
            "certifications",
            "keywords",
            "attachments",
        )

        for field_name in list_fields:
            values = getattr(self, field_name)

            cleaned = sorted(
                {
                    value.strip()
                    for value in values
                    if isinstance(value, str) and value.strip()
                },
                key=str.casefold,
            )

            setattr(self, field_name, cleaned)

    def generate_content_hash(self) -> str:
        hash_payload = {
            "title": self.title,
            "summary": self.summary,
            "raw_text": self.raw_text,
            "source_organisation": self.source_organisation,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "published_at": (
                self.published_at.isoformat()
                if self.published_at
                else None
            ),
            "intelligence_type": self.intelligence_type.value,
            "categories": self.categories,
            "products": self.products,
            "countries": self.countries,
            "companies": self.companies,
            "projects": self.projects,
            "technologies": self.technologies,
            "people": self.people,
            "policies": self.policies,
            "certifications": self.certifications,
            "keywords": self.keywords,
            "metadata": self.metadata,
            "capacity": self.capacity,
            "capex": self.capex,
            "fid_date": self.fid_date,
            "cod_date": self.cod_date,
            "commercial_theme": self.commercial_theme,
            "policy_theme": self.policy_theme,
            "tender_type": self.tender_type,
            "tender": self.tender,
            "offtake": self.offtake,
        }

        serialised = json.dumps(
            hash_payload,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )

        return hashlib.sha256(
            serialised.encode("utf-8")
        ).hexdigest()

    def refresh_content_hash(self) -> str:
        self.content_hash = self.generate_content_hash()
        self.updated_at = utc_now()
        return self.content_hash

    def add_entity(
        self,
        entity: EntityReference,
    ) -> None:
        existing = {
            (
                item.name.casefold(),
                str(item.entity_type).casefold(),
            )
            for item in self.entities
        }

        key = (
            entity.name.casefold(),
            str(entity.entity_type).casefold(),
        )

        if key not in existing:
            self.entities.append(entity)

    def add_event(
        self,
        event: EventReference,
    ) -> None:
        self.events.append(event)

    def add_relationship(
        self,
        relationship: RelationshipReference,
    ) -> None:
        existing = {
            (
                item.subject.casefold(),
                item.predicate.casefold(),
                item.object.casefold(),
            )
            for item in self.relationships
        }

        key = (
            relationship.subject.casefold(),
            relationship.predicate.casefold(),
            relationship.object.casefold(),
        )

        if key not in existing:
            self.relationships.append(relationship)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)

        for key in (
            "intelligence_type",
            "status",
            "confidence",
            "importance",
        ):
            result[key] = enum_value(getattr(self, key))

        for key in (
            "published_at",
            "collected_at",
            "updated_at",
        ):
            value = getattr(self, key)
            result[key] = value.isoformat() if value else None

        for event in result["events"]:
            event["event_type"] = enum_value(
                event["event_type"]
            )

            if event["event_date"]:
                event["event_date"] = (
                    event["event_date"].isoformat()
                )

        for key in ("fid_date", "cod_date"):
            value = getattr(self, key)
            result[key] = value.isoformat() if value else None

        if result["tender"] and result["tender"]["deadline"]:
            result["tender"]["deadline"] = (
                self.tender.deadline.isoformat()
            )

        if result["offtake"] and result["offtake"]["delivery_start"]:
            result["offtake"]["delivery_start"] = (
                self.offtake.delivery_start.isoformat()
            )

        return result

    def to_json(
        self,
        indent: int = 2,
    ) -> str:
        return json.dumps(
            self.to_dict(),
            indent=indent,
            ensure_ascii=False,
            default=str,
        )

    def save_json(
        self,
        file_path: str,
    ) -> None:
        with open(
            file_path,
            "w",
            encoding="utf-8",
        ) as file:
            file.write(self.to_json())