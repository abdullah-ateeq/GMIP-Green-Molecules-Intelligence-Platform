from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from gmip.config.access_mode import SourceAccessMode, SourceCategory


def _clean(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()
    return cleaned or None


def _validate_url(value: str | None, field_name: str) -> str | None:
    cleaned = _clean(value)

    if cleaned is None:
        return None

    if not cleaned.startswith(("http://", "https://")):
        raise ValueError(
            f"SourceDefinition.{field_name} must begin with http:// or https://."
        )

    return cleaned


@dataclass(slots=True)
class SourceDefinition:
    """
    Describes one GMIP intelligence source and how GMIP is allowed to
    access it.

    This does not replace config.HINTCO_SOURCES / HYDROGEN_COUNCIL_SOURCES,
    which the live collectors still consume unchanged. It is a richer,
    additive descriptive layer used for source health, the Source Monitor
    UI, and routing new sources through the ParserRegistry. No credentials
    are stored here — those belong in .env.
    """

    source_id: str
    source_name: str
    organization: str
    source_category: SourceCategory
    access_mode: SourceAccessMode

    source_family: str | None = None

    base_url: str | None = None
    feed_url: str | None = None
    api_endpoint: str | None = None

    requires_auth: bool = False
    license_required: bool = False
    enabled: bool = True

    priority: int = 3
    authority_level: str | None = None
    intelligence_role: str | None = None

    parser_id: str | None = None
    collector_id: str | None = None
    collection_frequency: str | None = None

    terms_note: str | None = None
    last_verified_at: date | None = None

    def __post_init__(self) -> None:
        self.source_id = self.source_id.strip()
        self.source_name = self.source_name.strip()
        self.organization = self.organization.strip()

        if not self.source_id:
            raise ValueError("SourceDefinition.source_id cannot be empty.")

        if not self.source_name:
            raise ValueError("SourceDefinition.source_name cannot be empty.")

        if not self.organization:
            raise ValueError("SourceDefinition.organization cannot be empty.")

        if not 1 <= self.priority <= 5:
            raise ValueError(
                "SourceDefinition.priority must be between 1 and 5."
            )

        self.source_family = _clean(self.source_family)
        self.authority_level = _clean(self.authority_level)
        self.intelligence_role = _clean(self.intelligence_role)
        self.parser_id = _clean(self.parser_id)
        self.collector_id = _clean(self.collector_id)
        self.collection_frequency = _clean(self.collection_frequency)
        self.terms_note = _clean(self.terms_note)

        self.base_url = _validate_url(self.base_url, "base_url")
        self.feed_url = _validate_url(self.feed_url, "feed_url")
        self.api_endpoint = _validate_url(
            self.api_endpoint, "api_endpoint"
        )

    @property
    def is_active(self) -> bool:
        """True when this source is enabled and not blocked on a licence."""
        return (
            self.enabled
            and self.access_mode != SourceAccessMode.DISABLED_PENDING_LICENSE
        )
